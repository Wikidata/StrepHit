#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import

import logging
import json

import click

from strephit.commons import wikidata, parallel

logger = logging.getLogger(__name__)


class ClassificationSerializer:
    def __init__(self, fe_to_wid, url_to_wid, language):
        self.fe_to_wid = fe_to_wid
        self.url_to_wid = url_to_wid
        self.language = language
        self.subject_fes = {'Participant'}  # TODO add other FE that denote the subject of statements

    def get_subject(self, data):
        """ Returns the wikidata id of the subject of the statements
        """

        # first, try to see if there is one (and exactly one) FE of one of the
        # types that can be subjects
        candidates = [fe for fe in data['fes'] if fe['fe'] in self.subject_fes]
        if len(candidates) == 1:
            return wikidata.resolver_with_hints(
                'P1559', candidates[0]['chunk'], self.language
            ) or None

        # if this fails, assume the subject is the main subject of the article
        # from which this sentence was extracted
        elif data['url'] in self.url_to_wid:
            return self.url_to_wid[data['url']]
        else:
            name = data.get('name')
            if not name:
                return None

            return wikidata.resolver_with_hints('P1559', name, self.language) or None

    def serialize_numerical(self, subj, fe, url):
        """ Serializes a numerical FE found by the normalizer
        """
        literal = fe['literal']
        if 'year' in literal or 'month' in literal or 'day' in literal:
            value = wikidata.format_date(**literal)
            yield wikidata.finalize_statement(subj, 'P585', value, self.language, url,
                                              resolve_property=False, resolve_value=False)
        else:
            if 'start' in literal:
                value = wikidata.format_date(**literal['start'])
                yield wikidata.finalize_statement(subj, 'P580', value, self.language, url,
                                                  resolve_property=False, resolve_value=False)

            if 'end' in literal:
                value = wikidata.format_date(**literal['end'])
                yield wikidata.finalize_statement(subj, 'P580', value, self.language, url,
                                                  resolve_property=False, resolve_value=False)

    def to_statements(self, data, input_encoded=True):
        """ Converts the classification results into quick statements
        """
        data = json.loads(data) if input_encoded else data

        url = data.get('url')
        if not url:
            logger.warn('skipping item without url')
            return

        subj = self.get_subject(data)
        if not subj:
            logger.warn('could not resolve subject, skipping sentence')
            return

        for fe in data['fes']:
            if fe['fe'] == 'Time':
                for each in self.serialize_numerical(subj, fe, url):
                    yield each
            else:
                prop = self.fe_to_wid.get(fe['fe'])

                if not prop and fe['fe'] != 'Duration':
                    logger.warn('unknown fe type %s, skipping', fe['fe'])
                    continue

                # TODO augment the resolver so as to take advantage of the dbpedia data available for linked entities
                yield wikidata.finalize_statement(subj, prop, fe['chunk'], self.language, url,
                                                  resolve_property=False, resolve_value=True)


def map_url_to_wid(semistructured):
    """ Read the quick statements generated from the semi structured data
        and build a map associating url to wikidata id
    """

    # urls are not primary keys, so skip urls with more than one subject
    banned_urls = set()

    url_to_wid = {}
    for row in semistructured:
        parts = row[:-1].split('\t')
        wid, url = parts[0], parts[-1]
        if url in url_to_wid and url_to_wid[url] != wid:
            url_to_wid.pop(url)
            banned_urls.add(url)
        elif url not in banned_urls:
            url_to_wid[parts[-1]] = parts[0]

    return url_to_wid


@click.command()
@click.argument('classified', type=click.File('r'))
@click.argument('frame-data', type=click.File('r'))
@click.argument('output', type=click.File('w'))
@click.argument('language')
@click.option('--semistructured', type=click.File('r'))
@click.option('--processes', '-p', default=0)
def main(classified, frame_data, output, language, semistructured, processes):
    """ Serialize classification results into quickstatements
    """

    if semistructured:
        url_to_wid = map_url_to_wid(semistructured)
        logger.info('used semi structured dataset to infer %d wikidata ids',
                    len(url_to_wid))
    else:
        url_to_wid = {}
        logger.info('TIP: using the semi structured dataset could help in '
                    'resolving the wikidata id of more subjects')

    frame_data = json.load(frame_data)
    fe_to_wid = {}
    for data in frame_data.values():
        for fe in data.get('core_fes', []) + data.get('extra_fes', []):
            if 'id' in fe:
                fe_to_wid[fe['fe']] = fe['id']

    count = 0
    serializer = ClassificationSerializer(fe_to_wid, url_to_wid, language)
    for statement in parallel.map(serializer.to_statements, classified,
                                  processes=processes, flatten=True):
        output.write(statement)
        output.write('\n')

        count += 1
        if count % 1000 == 0:
            logger.info('produced %d statements', count)

    logger.info('Done, produced %d statements', count)
