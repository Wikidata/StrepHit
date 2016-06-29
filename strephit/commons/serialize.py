# -*- encoding: utf-8 -*-
from __future__ import absolute_import

import logging
import json

import click
from collections import defaultdict
from strephit.commons import wikidata, parallel, text

logger = logging.getLogger(__name__)


class ClassificationSerializer:
    def __init__(self, language, frame_data, url_to_wid=None):
        self.url_to_wid = url_to_wid or {}
        self.language = language
        self.frame_data = frame_data
        self.process_frame_data(self.frame_data)

    def process_frame_data(self, frame_data):
        lu_fe_to_wid = {}
        lu_fe_to_qualifiers = {}

        for data in frame_data.values():
            lu = data['lu'].split('.')[0]
            for fe in data.get('core_fes', []) + data.get('extra_fes', []):
                if 'id' in fe['mapping']:
                    key = lu, fe['fe']
                    lu_fe_to_wid[key] = fe['mapping']['id']
                    lu_fe_to_qualifiers[key] = fe.get('qualifiers', [])
                else:
                    logger.debug("Dropping FE '%s' because no Wikidata property mapping is specified",
                                 fe['fe'])

        logger.info('got %d frame elements', len(lu_fe_to_wid))
        self.lu_fe_to_wid = lu_fe_to_wid
        self.lu_fe_to_qualifiers = lu_fe_to_qualifiers

    def get_subjects(self, data):
        """ Finds all subjects of the frame assigned to the sentence

            :param dict data: classification results
            :return: all subjects as tuples (chunk, wikidata id)
            :rtype: generator of tuples
        """

        if data['lu'] not in self.frame_data:
            logger.debug('sentence with a LU not contained in the lexical database')
            logger.debug(data)
            subjects = []
        else:
            frame = self.frame_data[data['lu']]
            subjects = [fe for fe in data['fes'] if fe['fe'] in frame['core_fes']]

        if subjects:
            for each in subjects:
                name = each['chunk']
                wid = wikidata.resolver_with_hints(
                    'P1559', text.fix_name(name)[0], self.language
                )
                yield name, wid
        else:
            # if this fails, assume the subject is the main subject of the
            # article from which this sentence was extracted
            if data['url'] in self.url_to_wid:
                name = None
                wid = self.url_to_wid[data['url']]
            else:
                name = data.get('name')
                wid = wikidata.resolver_with_hints(
                    'P1559', text.fix_name(name)[0], self.language
                ) or None if name else None

            yield name, wid

    def serialize_numerical(self, subj, fe, data):
        """ Serializes a numerical FE found by the normalizer
        """
        literal = fe['literal']
        wikidata_property = self.lu_fe_to_wid.get((data['lu'], fe['fe']))
        if not wikidata_property:
            logger.debug('skipping *numerical* FE of type "%s" and lu "%s"',
                         fe['fe'], data['lu'])
            return

        if fe['fe'] == 'Time':
            value = wikidata.format_date(**literal)
            yield wikidata.finalize_statement(subj, wikidata_property, value, self.language, data['url'],
                                              resolve_property=False, resolve_value=False)
        elif fe['fe'] == 'Duration':
            if 'start' in literal:
                value = wikidata.format_date(**literal['start'])
                yield wikidata.finalize_statement(subj, wikidata_property, value, self.language, data['url'],
                                                  resolve_property=False, resolve_value=False)

            if 'end' in literal:
                value = wikidata.format_date(**literal['end'])
                yield wikidata.finalize_statement(subj, wikidata_property, value, self.language, data['url'],
                                                  resolve_property=False, resolve_value=False)

    def find_qualifiers(self, fes):
        """ Finds all FEs that could serve as qualifiers instead of full statements
        """

        qualifiers = defaultdict(list)
        for fe in fes:
            if fe['fe'] == 'Time':
                literal = fe['literal']
                value = wikidata.format_date(**literal)
                qualifiers['P585'].append(value)
            elif fe['fe'] == 'Duration':
                literal = fe['literal']
                if 'start' in literal:
                    value = wikidata.format_date(**literal['start'])
                    qualifiers['P580'].append(value)

                if 'end' in literal:
                    value = wikidata.format_date(**literal['end'])
                    qualifiers['P580'].append(value)
            elif fe['fe'] == 'Place':
                value = None
                if 'link' in fe:
                    value = wikidata.wikidata_id_from_wikipedia_url(fe['link']['uri'])

                if not value:
                    value = wikidata.resolve('P276', fe['chunk'], self.language)

                if value:
                    qualifiers['P276'].append(value)

        return qualifiers

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

        for name, subj in self.get_subjects(data):
            if not subj:
                logger.warn("Could not resolve Wikidata Item ID of subject '%s'", name)
                yield False, {'chunk': name, 'additional': {'sentence': data['text'], 'url': url}}
                continue

            all_qualifiers = self.find_qualifiers(data['fes'])
            for fe in data['fes']:
                if fe['chunk'] == name:  # do not add a statement for the current subject
                    continue

                if fe['fe'] in ['Time', 'Duration']:
                    for each in self.serialize_numerical(subj, fe, data):
                        yield True, each
                else:
                    prop = self.lu_fe_to_wid.get((data['lu'], fe['fe']))
                    if not prop:
                        logger.debug('unknown fe type %s for LU %s, skipping', fe['fe'], data['lu'])
                        continue

                    val = None
                    if 'link' in fe:
                        uri = fe['link']['uri']
                        val = wikidata.wikidata_id_from_wikipedia_url(uri)

                    if not val:
                        val = wikidata.resolve(prop, fe['chunk'], self.language)

                    if not val:
                        val = 'Q19798648'
                        logger.debug('could not resolve chunk "%s" of fe %s (property is %s), '
                                     'using default value of %s',
                                     fe['chunk'], fe['fe'], prop, val)

                    stmt_qualifiers = []
                    for qualifier_property in self.lu_fe_to_qualifiers.get((data['lu'], fe['fe']), []):
                        for qualifier_value in all_qualifiers.get(qualifier_property, []):
                            stmt_qualifiers.extend((qualifier_property, qualifier_value))

                    yield True, wikidata.finalize_statement(
                        subj, prop, val, self.language, url, qualifiers=stmt_qualifiers,
                        resolve_property=False, resolve_value=False
                    )


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
@click.argument('lexical-db', type=click.File('r'))
@click.argument('language')
@click.option('--outfile', '-o', type=click.File('w'), default='output/serialized.qs')
@click.option('--semistructured', type=click.File('r'))
@click.option('--processes', '-p', default=0)
@click.option('--dump-unresolved', type=click.File('w'))
def main(classified, lexical_db, outfile, language,
         semistructured, processes, dump_unresolved):
    """ Serialize classification results into quickstatements
    """

    if semistructured:
        url_to_wid = map_url_to_wid(semistructured)
        logger.info('Used semi-structured dataset to infer %d Wikidata Item IDs',
                    len(url_to_wid))
    else:
        url_to_wid = {}
        logger.info('TIP: using the semi-structured dataset could help in '
                    'resolving the Wikidata Item ID of more subjects')

    lexical_db = json.load(lexical_db)

    count = skipped = 0
    serializer = ClassificationSerializer(language, lexical_db, url_to_wid)
    for success, item in parallel.map(serializer.to_statements, classified,
                                      processes=processes, flatten=True):
        if success:
            outfile.write(item.encode('utf8'))
            outfile.write('\n')

            count += 1
        else:
            skipped += 1
            if dump_unresolved:
                dump_unresolved.write(json.dumps(item))
                dump_unresolved.write('\n')

        if count % 1000 == 0 and count > 0:
            logger.info('Produced %d statements so far, skipped %d names', count, skipped)

    logger.info('Done, produced %d statements, skipped %d names', count, skipped)
    logger.info("Dataset serialized to '%s'" % outfile.name)
    if dump_unresolved:
        logger.info("Unresolved entities dumped to '%s'" % dump_unresolved.name)
