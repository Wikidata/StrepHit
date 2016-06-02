#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import

import logging
import json
from sys import exit

import click
import requests

from strephit.commons import secrets, cache, parallel

logger = logging.getLogger(__name__)


@cache.cached
def link(text, min_confidence, language):
    """
     Run entity linking on the given text using Dandelion APIs.
     Raise any HTTP error that may occur.

     :param str text: The text used to perform linking
     :return: The linked entities
     :rtype: list
    """

    logger.debug("Will run entity linking on: %s" % text)
    nex_data = {
        'text': text,
        '$app_id': secrets.NEX_ID,
        '$app_key': secrets.NEX_KEY,
        'include': 'types,alternate_labels',
        'min_confidence': min_confidence,
        'lang': language,
    }
    r = requests.post(secrets.NEX_URL, data=nex_data)
    r.raise_for_status()
    response = r.json()
    logger.debug("Response: %s " % response)
    return extract_entities(response)


def extract_entities(response_json):
    """
        Extract the list of entities from the Dandelion Entity Extraction API JSON response.

        :param dict response_json: JSON response returned by Dandelion
        :return: The extracted entities, with the surface form, start and end indices URI, and ontology types
        :rtype: list
    """
    entities = []

    for annotation in response_json['annotations']:
        entity = {
            'chunk': annotation.get('spot'),
            'start': annotation.get('start'),
            'end': annotation.get('end'),
            'uri': annotation.get('uri'),
            'confidence': annotation.get('confidence'),
            'types': annotation.get('types'),
            'alternate_names': annotation.get('alternateLabels')
        }
        logger.debug("Linked entity: %s" % entity)
        entities.append(entity)
    return entities


@click.command()
@click.argument('sentences', type=click.File('r'))
@click.argument('language')
@click.option('--processes', '-p', default=0)
@click.option('--output', '-o', type=click.File('w'), default='dev/entity_linked.json')
@click.option('--confidence', '-c', default=0.25, help='Minimum confidence score, defaults to 0.25.')
def main(sentences, language, output, confidence, processes):
    """ Perform entity linking over a set of input sentences.
        The service is Dandelion Entity Extraction API:
        https://dandelion.eu/docs/api/datatxt/nex/v1/ .
        Links having confidence score below the given
        threshold are discarded.
    """

    def worker(row):
        sentence = json.loads(row)
        text = sentence.get('text')
        if text:
            sentence['linked_entities'] = link(text, confidence, language)
            return json.dumps(sentence)

    count = 0
    for each in parallel.map(worker, sentences, processes):
        output.write(each)
        output.write('\n')

        count += 1
        if count % 1000 == 0:
            logger.info('linked %d sentences', count)
    logger.info('done, linked %d sentences')
