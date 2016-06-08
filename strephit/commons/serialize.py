# -*- encoding: utf-8 -*-
from __future__ import absolute_import

import logging
import json

import click

from strephit.commons import wikidata, parallel

logger = logging.getLogger(__name__)


class ClassificationSerializer:
    def __init__(self, fe_to_wid, url_to_wid, language, subject_fes):
        self.fe_to_wid = fe_to_wid
        self.url_to_wid = url_to_wid
        self.language = language
        self.subject_fes = subject_fes

    def get_subject(self, data):
        """ Returns the wikidata id of the subject of the statements
        """

        # first, try to see if there is one (and exactly one) FE of one of the
        # types that can be subjects
        candidates = [fe for fe in data['fes'] if fe['fe'] in self.subject_fes]
        if len(candidates) == 1:
            name = candidates[0]['chunk']
            wid = wikidata.resolver_with_hints(
                'P1559', name, self.language
            )
        # if this fails, assume the subject is the main subject of the article
        # from which this sentence was extracted
        elif data['url'] in self.url_to_wid:
            name = None
            wid = self.url_to_wid[data['url']]
        else:
            name = data.get('name')
            wid = wikidata.resolver_with_hints('P1559', name, self.language) or None if name else None

        return name, wid

    def serialize_numerical(self, subj, fe, url):
        """ Serializes a numerical FE found by the normalizer
        """
        literal = fe['literal']
        if fe['fe'] == 'Time':
            value = wikidata.format_date(**literal)
            yield wikidata.finalize_statement(subj, 'P585', value, self.language, url,
                                              resolve_property=False, resolve_value=False)
        elif fe['fe'] == 'Duration':
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
            :param data: Data from the classifier. Can be either str or dict
            :param bool input_encoded: Whether data is a str or a dict
            :returns: Tuples <success, item> where item is a statement if success
             is true else it is a named entity which could not be resolved
            :type: generator
        """
        data = json.loads(data) if input_encoded else data

        url = data.get('url')
        if not url:
            logger.warn('skipping item without url')
            return

        name, subj = self.get_subject(data)
        if not subj:
            logger.warn('could not resolve wikidata id of subject "%s", skipping sentence', name)
            yield False, name
            return

        for fe in data['fes']:
            if fe['fe'] in ['Time', 'Duration']:
                for each in self.serialize_numerical(subj, fe, url):
                    yield True, each
            else:
                prop = self.fe_to_wid.get(fe['fe'])
                if not prop:
                    logger.debug('unknown fe type %s, skipping', fe['fe'])
                    continue

                val = wikidata.resolve(prop, fe['chunk'], self.language)
                if val:
                    yield True, wikidata.finalize_statement(
                        subj, prop, val, self.language, url,
                        resolve_property=False, resolve_value=False
                    )
                else:
                    logger.debug('could not resolve chunk "%s" of fe %s (property is %s)',
                                 fe['chunk'], fe['fe'], prop)
                    yield False, fe['chunk']


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
@click.option('--dump-unresolved', type=click.File('w'))
def main(classified, frame_data, output, language,
         semistructured, processes, dump_unresolved):
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
                if fe['fe'] not in fe_to_wid:
                    fe_to_wid[fe['fe']] = fe['id']
                else:
                    # FIXME the check fails for an odd number of occurrences, but it shouldn't happen right?
                    logger.warn('the FE %s has been assigned two different wikidata properties: %s and %s, '
                                'it will be skipped altogether', fe['fe'], fe_to_wid['fe'], fe['id'])
                    fe_to_wid.pop(fe['fe'])
            else:
                logger.warn('dropping FE %s because no wikidata property is specified',
                            fe['fe'])

    # these FEs can act as subject of the statements produced from a frame
    # if none of these  (or more than one) is found, then the subject is
    # taken to be the subject of the article from which the sentence was extracted
    subject_fes = {u'Agent',
                   u'Author',
                   u'Elected_person',
                   u'Entity',
                   u'Exhibitor',
                   u'Individual',
                   u'New_member',
                   u'Participant',
                   u'Player',
                   u'Producer',
                   u'Visitor'}

    count = skipped = 0
    serializer = ClassificationSerializer(fe_to_wid, url_to_wid, language, subject_fes)
    for successs, item in parallel.map(serializer.to_statements, classified,
                                       processes=processes, flatten=True):
        if successs:
            output.write(item.encode('utf8'))
            output.write('\n')

            count += 1
        else:
            skipped += 1
            if dump_unresolved:
                dump_unresolved.write(json.dumps(item))
                dump_unresolved.write('\n')

        if count % 1000 == 0:
            logger.info('produced %d statements, skipped %d names', count, skipped)

    logger.info('Done, produced %d statements, skipped %d names', count, skipped)
