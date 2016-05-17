#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging
import json
import random
from collections import defaultdict

import click

from strephit.commons.date_normalizer import DateNormalizer
from strephit.commons import scoring
from strephit.commons.stopwords import StopWords

logger = logging.getLogger(__name__)


class RuleBasedClassifier:
    def __init__(self, frame_data, language):
        self.language = language
        self.frame_data = frame_data
        for lu, frame in self.frame_data.iteritems():
            frame['ontology_to_fe'] = defaultdict(list)
            frame['fes'] = {}
            for fe in frame['extra_fes'] + frame['core_fes']:
                frame['fes'][fe['fe']] = fe
                if fe.get('dbpedia_classes'):
                    for each in fe['dbpedia_classes']:
                        frame['ontology_to_fe'][each].append(fe)

    def assign_frame_elements(self, linked, frame):
        """ Try to assign a frame element to each of the linked entities
            based on their ontology type(s)
            :param linked: Entities found in the sentence
            :param frame: Frame data
            :return: List of assigned frames
        """

        assigned_fes = {}

        # greedy best-effort FE assignment:
        # try to assign a FE to entities with fewer available types first
        by_count = sorted(linked, key=lambda e: len(e['types']), reverse=True)
        for entity in by_count:
            if entity['chunk'].lower() in StopWords.words(self.language):
                continue

            for type_uri in entity['types']:
                dbpedia_class = type_uri[len('http://dbpedia.org/ontology/'):]

                # if more than one FE with that type choose randomly
                # but do not consider already picked FEs
                available = set(fe['fe'] for fe in frame['ontology_to_fe'][dbpedia_class])
                available.difference_update(set(assigned_fes))

                if available:
                    chosen = frame['fes'][random.choice(list(available))]
                    assigned_fes[chosen['fe']] = {
                        'fe': chosen['fe'],
                        'type': chosen['type'],
                        'chunk': entity['chunk'],
                        'uri': entity['uri'],
                        'score': entity['confidence']
                    }
                    logger.debug('assigned FE %s of frame %s to chunk "%s" of type %s',
                                 chosen['fe'], frame['frame'], entity['chunk'], dbpedia_class)
                else:
                    # we could back-track and change some past assignments
                    logger.debug('could not assign a FE to chunk "%s" of type %s',
                                 entity['chunk'], dbpedia_class)

        return assigned_fes

    def label_sentence(self, sentence, normalize_numerical):
        """ Labels a single sentence
            :param sentence: Sentence data to label
            :param normalize_numerical: Automatically normalize numerical FEs
            :return: Labeled data
        """
        labeled = {
            'sentence': sentence['text'],
            'FEs': defaultdict(list),
        }

        for token, pos, lemma in sentence['tagged']:
            for frame in self.frame_data.get(lemma, []):
                if pos.startswith(frame['pos']):
                    logger.debug('trying frame %s' % frame['frame'])
                    assigned_fes = self.assign_frame_elements(sentence['linked_entities'], frame)

                    # Continue to next frame if NO core FE was found
                    # TODO strict assignment: ALL core FEs must be found
                    # TODO best-effort assignment: the one with most FEs wins
                    if not any(fe['type'] == 'Core' for fe in assigned_fes):
                        logger.debug('no core FEs found for frame "%s": skipping' % frame['frame'])
                    else:
                        logger.debug('assigning frame: %s', frame['frame'])
                        logger.debug('assigning FEs: %s', assigned_fes)

                        # If at least 1 core FE is detected in multiple frames then assign randomly
                        current_frame = frame['frame']
                        previous_frame = labeled.get('frame')
                        if previous_frame:
                            choice = random.choice([previous_frame, current_frame])
                            logger.debug('core FEs for multiple frames detected; '
                                         'assigning (randomly) to: %s', choice)

                            if choice == current_frame:
                                labeled['frame'] = current_frame
                                labeled['FEs'] = assigned_fes
                        else:
                            labeled['frame'] = current_frame
                            labeled['FEs'] = assigned_fes

        # Normalize + annotate numerical FEs (only if we could disambiguate the sentence)
        if labeled.get('frame') and normalize_numerical:
            normalizer = DateNormalizer()

            logger.debug('labeling and normalizing numerical FEs ...')
            for (start, end), tag, norm in normalizer.normalize_many(sentence):
                chunk = sentence[start:end]
                logger.debug('Chunk [%s] normalized into [%s], tagged as [%s]' % (chunk, norm, tag))
                fe = {  # All numerical FEs are extra ones and their values are literals
                        'chunk': chunk,
                        'FE': tag,
                        'type': 'extra',
                        'literal': norm,
                        'score': 1.0
                        }
                labeled['FEs'].append(fe)

        if 'lu' in labeled and labeled['FEs']:
            return labeled
        else:
            return None

    def label_sentences(self, sentences, normalize_numerical, score_type, core_weight):
        """ Process all the given sentences with the rule-based classifier,
            optionally giving a confidence score
            :param sentences: List of sentence data
            :param normalize_numerical: Whether to automatically
             normalize numerical expressions
            :param score_type: Which type of score (if any) to use to
            compute the classification confidence
            :param core_weight: Weight of the core FEs (used in the scoring)
            :return: Generator of labeled sentences
        """

        for each in sentences:
            labeled = self.label_sentence(each, normalize_numerical)
            if labeled is None:
                continue

            if score_type:
                labeled['score'] = scoring.compute_score(labeled,
                                                         score_type,
                                                         core_weight)

            yield labeled


@click.command()
@click.argument('sentences', type=click.File('r'))
@click.argument('language')
@click.argument('output', default='dev/labeled.jsonlines')
@click.option('--frame-data', type=click.File('r'), default='dev/framenet_lus.json')
@click.option('--score-type', type=click.Choice(scoring.AVAILABLE_SCORES))
@click.option('--core-weight', default=2)
@click.option('--normalize-numerical', is_flag=True, default=True)
def main(sentences, language, output, frame_data, score_type, core_weight, normalize_numerical):
    """ Rule-based role labeling
    """

    def _flatten(iterable):  # Good job, itertools
        for x in iterable:
            for y in x:
                yield y

    frame_data = json.load(frame_data)
    sentences = _flatten(json.loads(row)['sentences'] for row in sentences)

    labeled = RuleBasedClassifier(frame_data, language).label_sentences(
        sentences, normalize_numerical, score_type, core_weight
    )

    count = 0
    for i, each in enumerate(labeled):
        output.write(json.dumps(each))
        output.write('\n')

        count = i + 1
        if count % 1000 == 0:
            logger.info('Labeled %d sentences', count)

    logger.info('Done, labeled %d sentences', count)
