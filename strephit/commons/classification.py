# -*- encoding: utf-8 -*-

from __future__ import absolute_import
import json
import logging

from strephit.commons.date_normalizer import normalize_numerical_fes

logger = logging.getLogger(__name__)


def apply_custom_classification_rules(classified, language, overwrite=False):
    """ Implements simple custom, classifier-agnostic rules for
        recognizing some frame elements

        :param dict classified: an item produced by the classifier
        :param str language: Language of the sentence
        :param bool overwrite: Tells the priority in case the rules assign a
         role to the same chunk recognized by the classifier
        :return: The same item with augmented FEs
    """

    chunk_to_fe = {fe['chunk']: fe for fe in classified['fes']}

    # if not already done, normalize numerica FEs
    if not any(fe['fe'] in ['Time', 'Duration'] for fe in classified['fes']):
        numerical = normalize_numerical_fes(language, classified['text'])
        for each in numerical:
            old = chunk_to_fe.get(each['chunk'])

            if old is None:
                chunk_to_fe[each['chunk']] = each
            elif overwrite:
                chunk_to_fe[each['chunk']] = each
                logger.debug('chunk "%s" was assigned role %s, assigning %s instead',
                             old['chunk'], old['fe'], each['fe'])

    # all places recognized by the entity linker are FEs
    for entity in classified.get('linked_entities', []):
        typeof_place = 'http://dbpedia.org/ontology/Place'
        if typeof_place in entity['types']:
            fe = {
                'fe': 'Place',
                'chunk': entity['chunk'],
                'score': entity['confidence'],
                'link': entity,
            }

            old = chunk_to_fe.get(entity['chunk'])
            if old is None:
                chunk_to_fe[fe['chunk']] = fe
            elif overwrite or typeof_place not in old.get('link', {}).get('types', []):
                chunk_to_fe[fe['chunk']] = fe
                logger.debug('chunk "%s" was assigned role %s, assigning %s instead',
                             old['chunk'], old['fe'], 'Place')

    classified['fes'] = chunk_to_fe.values()

    # check that no chunk is assigned more than one role
    assert len(set(fe['chunk'] for fe in classified['fes'])) == len(classified['fes'])

    return classified


def reverse_gazetteer(gazetteer):
    """ Reverses the gazetteer from feature -> chunks to chunk -> features

        :param dict gazetteer: Gazetteer associating chunks to features
        :return: An equivalent gazetteer associating features to chunks
        :rtype: dict
    """
    reversed = {}
    if gazetteer:
        for feature, chunks in gazetteer.iteritems():
            for each in chunks:
                if each not in reversed:
                    reversed[each] = []
                reversed[each].append(feature)
    return reversed
