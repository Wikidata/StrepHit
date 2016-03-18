#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import

import click
import logging
import json
import requests
from strephit.commons import secrets, cache
from sys import exit


logger = logging.getLogger(__name__)

# Data to be POSTed to Dandelion APIs
NEX_DATA = {}


@cache.cached
def link(text):
    """
     Run entity linking on the given text using Dandelion APIs.
     Raise any HTTP error that may occur.
     :param str text: The text used to perform linking
     :return: The linked entities
     :rtype: list
    """
    logger.debug("Will run entity linking on: %s" % text)
    NEX_DATA['text'] = text
    r = requests.post(secrets.NEX_URL, data=NEX_DATA)
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
@click.argument('input_file', type=click.File())
@click.argument('language')
@click.option('--output', '-o', type=click.File('w'), default='entity_linked.json')
@click.option('--confidence', '-c', default=0.25, help='Minimum confidence score, defaults to 0.25.')
def main(input_file, language, output, confidence):
    """ Perform entity linking over a set of input sentences.
        The service is Dandelion Entity Extraction API:
        https://dandelion.eu/docs/api/datatxt/nex/v1/ .
        Links having confidence score below the given
        threshold are discarded.
    """
    NEX_DATA['$app_id'] = secrets.NEX_ID
    NEX_DATA['$app_key'] = secrets.NEX_KEY
    NEX_DATA['include'] = 'types,alternate_labels'
    NEX_DATA['min_confidence'] = confidence
    NEX_DATA['lang'] = language
    logger.info("Will perform entity linking over '%s' sentences" % input_file.name)
    for line in input_file:
        item = json.loads(line)
        sentences = item.get('sentences')
        if sentences:
            logger.debug("Sentences: %s" % sentences)
            for sentence in sentences:
                text = sentence.get('text')
                if text:
                    sentence['linked_entities'] = link(text)
                else:
                    logger.warn("No text for sentence #%d: skipping ..." % sentence['id'])
        else:
            logger.warn("No sentences to link for item with URL '%s': skipping ..." % item['url'])
        json.dump(item, output, indent=2)
    logger.info("Linked entities added, will dump to '%s'" % output.name)
    return 0


if __name__ == '__main__':
    exit(main())
