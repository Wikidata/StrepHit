#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging
import json
import random
from collections import defaultdict

import click

from strephit.commons.date_normalizer import normalize_numerical_fes
from strephit.commons import scoring, pos_tag, parallel
from strephit.commons.stopwords import StopWords
from strephit.commons.classification import apply_custom_classification_rules

logger = logging.getLogger(__name__)


class RuleBasedClassifier:
    """ A simple rule-based classifier

        The frame is recognized solely based on the lexical unit
        and frame elements are assigned to linked entities with
        a suitable type
    """
    def __init__(self, frame_data, language):
        self.tagger = pos_tag.TTPosTagger(language)
        self.language = language
        self.frame_data = frame_data

        for lu, frame in self.frame_data.iteritems():
            ontology_to_fe = defaultdict(list)
            frame['fes'] = {}
            for fe in frame['extra_fes'] + frame['core_fes']:
                frame['fes'][fe['fe']] = fe
                if fe.get('dbpedia_classes'):
                    for each in fe['dbpedia_classes']:
                        ontology_to_fe[each].append(fe)
            frame['ontology_to_fe'] = dict(ontology_to_fe)

    def assign_frame_elements(self, linked, frame):
        """ Try to assign a frame element to each of the linked entities
            based on their ontology type(s)

            :param linked: Entities found in the sentence
            :param frame: Frame data
            :return: List of assigned frames
        """

        assigned_fes = []

        # greedy best-effort FE assignment:
        # try to assign a FE to entities with fewer available types first
        by_count = sorted(linked, key=lambda e: len(e['types']), reverse=True)
        for entity in by_count:
            if entity['chunk'].lower() in StopWords.words(self.language):
                continue

            if not entity['types']:
                logger.debug('entity "%s" has no types attached, skipping',
                             entity['chunk'])
                continue

            assigned = False
            for type_uri in entity['types']:
                dbpedia_class = type_uri[len('http://dbpedia.org/ontology/'):]
                if dbpedia_class not in frame['ontology_to_fe']:
                    logger.debug('no FE of type %s in frame %s',
                                 dbpedia_class, frame['frame'])
                    continue

                # if more than one FE with that type choose randomly
                # and give core FEs precedence over extra FEs
                available = set(fe['fe'] for fe in frame['ontology_to_fe'][dbpedia_class]
                                if fe['type'] == 'Core')
                if not available:
                    available = set(fe['fe'] for fe in frame['ontology_to_fe'][dbpedia_class])

                if available:
                    chosen = frame['fes'][random.choice(list(available))]
                    assigned_fes.append({
                        'fe': chosen['fe'],
                        'fe_type': chosen['type'],
                        'entity_type': type_uri,
                        'chunk': entity['chunk'],
                        'uri': entity['uri'],
                        'score': entity['confidence']
                    })
                    logger.debug('assigned FE %s of frame %s to chunk "%s" of type %s',
                                 chosen['fe'], frame['frame'], entity['chunk'], dbpedia_class)
                    assigned = True
                    break
                else:
                    # we could back-track and change some past assignments
                    logger.debug('could not assign a FE to chunk "%s" of type %s',
                                 entity['chunk'], dbpedia_class)

            if not assigned:
                logger.debug('skipping entity "%s"', entity['chunk'])

        return assigned_fes

    def label_sentence(self, sentence, normalize_numerical, score_type, core_weight):
        """ Labels a single sentence

            :param sentence: Sentence data to label
            :param normalize_numerical: Automatically normalize numerical FEs
            :param score_type: Which type of score (if any) to use to
             compute the classification confidence
            :param core_weight: Weight of the core FEs (used in the scoring)
            :return: Labeled data
        """
        logger.debug('processing sentence "%s"', sentence['text'])
        if not sentence.get('url'):
            logger.warn('a sentence is missing the url, skipping it')
            return None
        elif not sentence.get('text', '').strip():
            return None

        tagged = sentence['tagged'] if 'tagged' in sentence else self.tagger.tag_one(sentence['text'])

        # Normalize + annotate numerical FEs
        numerical_fes = []
        if normalize_numerical:
            numerical_fes.extend(list(normalize_numerical_fes(self.language, sentence['text'])))

        for token, pos, lemma in tagged:
            if lemma not in self.frame_data or not pos.startswith(self.frame_data[lemma]['pos']):
                continue

            frame = self.frame_data[lemma]
            if not frame['ontology_to_fe'].keys():
                logger.debug('missing FE types for frame %s, skipping',
                             frame['frame'])
                continue

            logger.debug('trying frame %s with FE of types %s', frame['frame'],
                         frame['ontology_to_fe'].keys())

            assigned_fes = self.assign_frame_elements(sentence['linked_entities'], frame)
            all_fes = numerical_fes + assigned_fes
            if assigned_fes or numerical_fes:
                logger.debug('assigning frame: %s and FEs %s', frame['frame'], all_fes)
                labeled = {
                    'name': sentence['name'],
                    'url': sentence['url'],
                    'text': sentence['text'],
                    'linked_entities': sentence['linked_entities'],
                    'frame': frame['frame'],
                    'fes': all_fes,
                    'lu': lemma,
                }
                break
            else:
                logger.debug('no FEs assigned for frame %s, trying another one', frame['frame'])
        else:
            logger.debug('did not assign any frame to sentence "%s"', sentence['text'])
            return None

        if score_type:
            labeled['score'] = scoring.compute_score(labeled,
                                                     score_type,
                                                     core_weight)

        assert 'lu' in labeled and labeled['fes']

        final = apply_custom_classification_rules(labeled, self.language)
        return final

    def label_sentences(self, sentences, normalize_numerical, score_type, core_weight,
                        processes=0, input_encoded=False, output_encoded=False):
        """ Process all the given sentences with the rule-based classifier,
            optionally giving a confidence score

            :param sentences: List of sentence data
            :param normalize_numerical: Whether to automatically
             normalize numerical expressions
            :param score_type: Which type of score (if any) to use to
             compute the classification confidence
            :param core_weight: Weight of the core FEs (used in the scoring)
            :param processes: how many processes to use to concurrently label sentences
            :param input_encoded: whether the corpus is an iterable of dictionaries or an
             iterable of JSON-encoded documents. JSON-encoded documents are preferable
             over large size dictionaries for performance reasons
            :param output_encoded: whether to return a generator of dictionaries or a generator
             of JSON-encoded documents. Prefer encoded output for performance reasons
            :return: Generator of labeled sentences
        """

        def worker(item):
            if input_encoded:
                item = json.loads(item)

            labeled = self.label_sentence(item, normalize_numerical,
                                          score_type, core_weight)

            if labeled:
                return json.dumps(labeled) if output_encoded else labeled

        for each in parallel.map(worker, sentences, processes):
            yield each


@click.command()
@click.argument('sentences', type=click.File('r'))
@click.argument('frame-data', type=click.File('r'))
@click.argument('language')
@click.option('--outfile', '-o', type=click.File('w'), default='output/rule_based_classified.jsonlines')
@click.option('--processes', '-p', default=0)
@click.option('--score-type', type=click.Choice(scoring.AVAILABLE_SCORES))
@click.option('--core-weight', default=2)
@click.option('--normalize-numerical', is_flag=True, default=True)
def main(sentences, frame_data, language, outfile, score_type, core_weight,
         normalize_numerical, processes):
    """ Rule-based role labeling
    """

    frame_data = json.load(frame_data)

    labeled = RuleBasedClassifier(frame_data, language).label_sentences(
        sentences, normalize_numerical, score_type, core_weight, processes,
        input_encoded=True, output_encoded=True
    )

    count = 0
    for i, each in enumerate(labeled):
        outfile.write(each)
        outfile.write('\n')

        count = i + 1
        if count % 1000 == 0:
            logger.info('Labeled %d sentences', count)
    
    if count > 0:
        logger.info("Dumped labeled sentences to '%s'" % outfile.name)
    logger.info('Done, labeled %d sentences', count)
