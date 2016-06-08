# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import json
import logging
from collections import defaultdict

import click

from strephit.commons import io, wikidata, parallel, text

logger = logging.getLogger(__name__)


class SemistructuredSerializer:
    def __init__(self, language, sourced_only):
        self.language = language
        self.sourced_only = sourced_only

    def serialize_item(self, item):
        """ Converts an item to quick statements.
            :param item: Scraped item, either str (json) or dict
            :returns: tuples <success, item> where item is an entity which
             could not be resolved if success is false, otherwise it is a
             <subject, property, object, source> tuple
            :rtype: generator
        """

        if isinstance(item, basestring):
            item = json.loads(item)

        name = item.pop('name')
        other = item.pop('other', {})
        url = item.pop('url', '')

        if self.sourced_only and not url:
            logger.debug('item %s has no url, skipping it')
            return

        if not name:
            logger.debug('item %s has no name, skipping it')
            return

        data = {}
        try:
            data = json.loads(other)
        except ValueError:
            pass
        except TypeError:
            if isinstance(other, dict):
                data = other
            else:
                return

        name, honorifics = text.fix_name(name)
        data.update(item)
        data.pop('bio', None)

        # the name will be the last one to be resolved because it is the hardest
        # one to get right, so we will use all the other statements to help
        statements = defaultdict(list)

        for key, value in data.iteritems():
            if not isinstance(value, list):
                value = [value]

            strings = []
            for val in value:
                if isinstance(val, basestring):
                    strings.append(val)
                elif isinstance(val, dict):
                    strings.extend(val.keys())
                    strings.extend(val.values())

            for val in strings:
                if not val:
                    continue
                elif not isinstance(val, basestring):
                    logger.debug('skipping value "%s" because it is not a string', val)
                    continue

                property = wikidata.PROPERTY_TO_WIKIDATA.get(key)
                if not property:
                    logger.debug('cannot resolve property %s, skipping', key)
                    continue

                info = dict(data, **statements)  # provide all available info to the resolver
                resolved = wikidata.resolve(property, val, self.language, **info)
                if not resolved:
                    logger.debug('cannot resolve value %s of property %s, skipping', val, property)
                    yield False, val
                    continue

                statements[property].append(resolved)

        info = dict(data, **statements)  # provide all available info to the resolver
        info['type_'] = 5  # Q5 = human
        wid = wikidata.resolver_with_hints('P1559', name, self.language, **info)

        if not wid:
            logger.debug('cannot find wikidata id of "%s" with properties %s, skipping',
                         name, repr(info))
            yield False, name
            return

        # now that we are sure about the subject we can produce the actual statements
        yield True, (wid, 'P1559', '%s:"%s"' % (self.language, name.title()), url)
        for property, values in statements.iteritems():
            for val in values:
                yield True, (wid, property, val, url)

        for each in honorifics:
            hon = wikidata.resolve('P1035', each, self.language)
            if hon:
                yield True, (wid, 'P1035', hon, url)
            else:
                yield False, each

    def process_corpus(self, items, output_file, dump_unresolved_file=None, genealogics=None, processes=0):
        count = skipped = 0

        genealogics_url_to_id = {}
        for success, item in parallel.map(self.serialize_item, items, processes, flatten=True):
            if success:
                subj, prop, val, url = item
                statement = wikidata.finalize_statement(
                    subj, prop, val, self.language, url,
                    resolve_property=False, resolve_value=False
                )

                if not statement:
                    continue

                output_file.write(statement.encode('utf8'))
                output_file.write('\n')

                if genealogics and url.startswith('http://www.genealogics.org/'):
                    genealogics_url_to_id[url] = subj

                count += 1
                if count % 10000 == 0:
                    logger.info('Produced %d statements so far, skipped %d names', count, skipped)
            else:
                skipped += 1
                if dump_unresolved_file:
                    dump_unresolved_file.write(json.dumps(item))
                    dump_unresolved_file.write('\n')

        logger.info('Done, roduced %d statements so far, skipped %d names', count, skipped)
        return genealogics_url_to_id, count, skipped

    def resolve_genealogics_family(self, input_file, url_to_id):
        """ Performs a second pass on genealogics to resolve additional family members
        """
        family_properties = {
            'Family': 'P1038',
            'Father': 'P22',
            'Married': 'P26',
            'Mother': 'P25',
            u'Children\xa0': 'P40',
        }

        for row in input_file:
            data = json.loads(row)

            if 'url' not in data or data['url'] not in url_to_id:
                continue

            subj = url_to_id[data['url']]

            for key, value in data.get('other', {}).iteritems():
                if key in family_properties:
                    prop = family_properties[key]

                    if not isinstance(value, list):
                        logger.debug('unexpected value "%s", property "%s" subject %s',
                                     value, key, subj)
                        continue

                    for member in value:
                        for name, url in member.iteritems():
                            if url in url_to_id:
                                val = url_to_id[url]
                                logger.debug('resolved "%s", %s of/with %s to %s',
                                             name.strip(), key, subj, val)

                                statement = wikidata.finalize_statement(
                                    subj, prop, val, self.language, data['url'],
                                    resolve_property=False, resolve_value=False
                                )

                                yield True, statement
                            else:
                                logger.debug('skipping "%s" (%s), %s of/with %s',
                                             name.strip(), url, key, subj)
                                yield False, name


@click.command()
@click.argument('corpus-dir', type=click.Path())
@click.argument('out-file', type=click.File('w'))
@click.option('--genealogics', type=click.File('r'))
@click.option('--sourced-only/--allow-unsourced', default=True)
@click.option('--language', default='en', help='The names are searched in this language')
@click.option('--processes', '-p', default=0)
@click.option('--dump-unresolved', type=click.File('w'))
def process_semistructured(corpus_dir, out_file, language, processes,
                           sourced_only, genealogics, dump_unresolved):
    """ Processes the corpus and extracts semistructured data serialized into quick statements
        Needs a second pass on genealogics to correctly resolve family members
    """

    resolver = SemistructuredSerializer(language, sourced_only, )

    genealogics_url_to_id, count, skipped = resolver.process_corpus(
        io.load_scraped_items(corpus_dir), out_file, dump_unresolved, genealogics, processes
    )

    logger.info('Done, produced %d statements, skipped %d names', count, skipped)
    if not genealogics:
        return

    logger.info('Starting second pass on genealogics')
    genealogics_data = resolver.resolve_genealogics_family(genealogics, genealogics_url_to_id)
    for success, item in genealogics_data:
        if success:
            out_file.write(item.encode('utf8'))
            out_file.write('\n')

            count += 1
            if count % 10000 == 0:
                logger.info('Produced %d statements so far, skipped %d names', count, skipped)
        else:
            skipped += 1
            if dump_unresolved:
                dump_unresolved.write(json.dumps(item))
                dump_unresolved.write('\n')

    logger.info('Done, produced %d statements, skipped %d names', count, skipped)
