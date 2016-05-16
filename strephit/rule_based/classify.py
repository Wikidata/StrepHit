#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging
from sys import exit

import os


import click
import codecs
import json
import random
from collections import defaultdict
from urllib import quote
from rfc3987 import parse  # URI/IRI validation
from resources.frame_repo import FRAME_REPO
from strephit.commons.date_normalizer import DateNormalizer
from strephit.commons.scoring import compute_score, AVAILABLE_SCORES
from strephit.commons.stopwords import StopWords
from strephit.commons.tokenize import Tokenizer


logger = logging.getLogger(__name__)

NORMALIZER = DateNormalizer()


def label_sentence(sentence, links, debug, numerical):
    labeled = {}
    labeled['sentence'] = sentence
    labeled['FEs'] = defaultdict(list)
    # Tokenize by splitting on spaces
    t = Tokenizer('it')
    sentence_tokens = t.tokenize(sentence)
    logger.debug('SENTENCE: %s' % sentence)
    logger.debug('TOKENS: %s' % sentence_tokens)
    frames = []
    for lu in FRAME_REPO:
        lu_tokens = lu['lu']['tokens']
        # Check if a sentence token matches a LU token and assign frames accordingly
        for sentence_token in sentence_tokens:
            if sentence_token in lu_tokens:
                logger.debug('TOKEN "%s" MATCHED IN LU TOKENS' % sentence_token)
                labeled['lu'] = lu['lu']['lemma']
                frames = lu['lu']['frames']
                logger.debug('LU LEMMA: %s' % labeled['lu'])
                logger.debug('FRAMES: %s' % [frame['frame'] for frame in frames])
                # Frame processing
                for frame in frames:
                    FEs = frame['FEs']
                    types_to_FEs = frame['DBpedia']
                    logger.debug('CURRENT FRAME: %s' % frame['frame'])
                    logger.debug('FEs: %s' % FEs)
                    core = False
                    assigned_fes = []
                    for diz in val:
                        spot = diz.get('spot', diz.get('nc:spot'))
                        assert spot, diz
                        if spot.lower() in StopWords.words('italian'):
                            continue

                        uri = diz.get('uri')
                        if not uri:
                            uri = 'https://atoka.io/azienda/-/' + diz['nc:acheneID']

                        chunk = {
                            'chunk': spot,
                            'uri': uri,
                            'score': diz.get('confidence', diz.get('nc:confidence'))
                        }

                        types = diz.get('types', diz.get('nc:types'))
                        #### FE assignment ###
                        for t in types:
                            for mapping in types_to_FEs:
                                # Strip DBpedia ontology namespace
                                looked_up = mapping.get(t[28:])
                                if looked_up:
                                    logger.debug('Chunk "%s" has an ontology type "%s" that maps to FE "%s"' % (chunk['chunk'], t[28:], looked_up))
                                    ### Frame disambiguation strategy, part 1 ###
                                    # LAPSE ASSIGNMENT
                                    # If there is AT LEAST ONE core FE, then assign that frame
                                    # TODO strict assignment: ALL core FEs must be found
                                    # Will not work if the FEs across competing frames have the same ontology type
                                    # e.g., Attività > Squadra and Partita > [Squadra_1, Squadra_2]

                                    # Check if looked up FE is core
                                    for fe in FEs:
                                        if type(looked_up) == list:
                                            for shared_type_fe in looked_up:
                                                shared_fe_type = fe.get(shared_type_fe)
                                                # TODO overwritten value
                                                if shared_fe_type:
                                                    chunk['type'] = shared_fe_type
                                                if shared_fe_type == 'core':
                                                    logger.debug('Mapped FE "%s" is core for frame "%s"' % (shared_type_fe, frame['frame']))
                                                    core = True
                                        else:
                                            fe_type = fe.get(looked_up)
                                            if fe_type:
                                                chunk['type'] = fe_type
                                            if fe_type == 'core':
                                                logger.debug('Mapped FE "%s" is core for frame "%s"' % (looked_up, frame['frame']))
                                                core = True
                                    ### FE disambiguation strategy ###
                                    # If multiple FEs have the same ontology type, e.g., [Vincitore, Perdente] -> Club
                                    # BASELINE = random assignment
                                    # Needs to be adjusted by humans
                                    if type(looked_up) == list:
                                        chosen = random.choice(looked_up)
                                        chunk['FE'] = chosen
                                        # Avoid duplicates
                                        if chunk not in assigned_fes:
                                            assigned_fes.append(chunk)
                                    else:
                                        chunk['FE'] = looked_up
                                        # Avoid duplicates
                                        if chunk not in assigned_fes:
                                            assigned_fes.append(chunk)
                    # Continue to next frame if NO core FE was found
                    if not core:
                        logger.debug('No core FE for frame "%s": skipping' % frame['frame'])
                        continue
                    # Otherwise assign frame and previously stored FEs
                    else:
                        logger.debug('ASSIGNING FRAME: %s' % frame['frame'])
                        logger.debug('ASSIGNING FEs: %s' % assigned_fes)
                        ### Frame disambiguation strategy, part 2 ###
                        # If at least 1 core FE is detected in multiple frames:
                        # BASELINE = random assignment
                        # Needs to be adjusted by humans
                        current_frame = frame['frame']
                        previous_frame = labeled.get('frame')
                        if previous_frame:
                            previous_FEs = labeled['FEs']
                            choice = random.choice([previous_frame, current_frame])
                            logger.debug('CORE FES FOR MULTIPLE FRAMES WERE DETECTED. MAKING A RANDOM ASSIGNMENT: %s' % choice)
                            if choice == current_frame:
                                labeled['frame'] = current_frame
                                labeled['FEs'] = assigned_fes
                        else:
                            labeled['frame'] = current_frame
                            labeled['FEs'] = assigned_fes

    # Normalize + annotate numerical FEs (only if we could disambiguate the sentence)
    if labeled.get('frame') and numerical:
        logger.debug('LABELING AND NORMALIZING NUMERICAL FEs ...')
        for (start, end), tag, norm in NORMALIZER.normalize_many(sentence):
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


def process_dir(sentences, debug, numerical):
    processed = []
    with open(sentences) as f:
        for row in f:
            data = json.loads(row)
            for each in data['sentences']:
                labeled = label_sentence(each['text'], each['links'],
                                         debug, numerical)
                if labeled is not None:
                    print labeled
                    processed.append(labeled)
    return processed


@click.command()
@click.argument('sentences', type=click.Path(exists=True, file_okay=True))
@click.argument('labeled_out', default='labeled.json')
@click.option('--score', type=click.Choice(['arithmetic-mean', 'weighted-mean',
                                            'f-score', '']))
@click.option('--core-weight', default=2)
@click.option('--score-fes/--no-score-fes', help='Score individual FEs')
@click.option('--debug/--no-debug', default=False)
@click.option('--numerical/--no-numerical', default=True)
def main(sentences, labeled_out, score, core_weight, score_fes, debug, numerical):
    """
    Rule-based classifier
    """
    labeled = process_dir(sentences, debug, numerical)

    if score:
        for sentence in labeled:
            sentence['score'] = compute_score(sentence, score, core_weight)
            if not score_fes:
                [fe.pop('score') for fe in sentence['FEs']]

    with codecs.open(labeled_out, 'w', 'utf8') as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)
    return 0

if __name__ == '__main__':
    exit(main())
