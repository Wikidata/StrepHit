# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import json
import logging
from collections import defaultdict

import click

from strephit.commons import io, wikidata, parallel, text

logger = logging.getLogger(__name__)


def serialize_item((i, item, language, sourced_only)):
    """ Converts an item to quick statements. Takes a single tuple as parameter
        and returns generator of tuples <subject, property, object, source>
        with already resolved items
    """
    _id = item.pop('id', i)
    name = item.pop('name')
    other = item.pop('other', {})
    url = item.pop('url', '')

    if sourced_only and not url:
        logger.debug('item %s has no url, skipping' % _id)
        return

    if not name:
        logger.debug('item %s has no name, skipping' % _id)
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

        for val in value:
            if not val:
                continue

            property = wikidata.PROPERTY_TO_WIKIDATA.get(key)
            if not property:
                logger.debug('cannot resolve property %s, skipping', key)
                continue

            info = dict(data, **statements)  # provide all available info to the resolver
            resolved = wikidata.resolve(property, val, language, **info)
            if not resolved:
                logger.debug('cannot resolve value %s of property %s, skipping', val, property)
                continue

            statements[property].append(resolved)

    info = dict(data, **statements)  # provide all available info to the resolver
    info['type_'] = 5  # Q5 = human
    wid = wikidata.resolver_with_hints('P1559', name, language, **info)

    if not wid:
        logger.debug('cannod find wikidata id for item %s (%s) with properties %s, skipping',
                     _id, name, repr(info))
        return

    # now that we are sure about the subject we can produce the actual statements
    yield wid, 'P1559', '"%s"' % name.title(), url
    for property, values in statements.iteritems():
        for val in values:
            yield wid, property, val, url

    for each in honorifics:
        hon = wikidata.resolve('P1035', each, language)
        if hon:
            yield wid, 'P1035', hon, url


def resolve_genealogics_family(input_file, url_to_id):
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
                            yield subj, prop, val, data['url']
                        else:
                            logger.debug('skipping "%s" (%s), %s of/with %s',
                                         name.strip(), url, key, subj)


@click.command()
@click.argument('corpus-dir', type=click.Path())
@click.argument('out-file', type=click.File('w'))
@click.option('--genealogics', type=click.File('r'))
@click.option('--sourced-only/--allow-unsourced', default=True)
@click.option('--language', default='en', help='The names are searched in this language')
@click.option('--processes', '-p', default=0)
def process_semistructured(corpus_dir, out_file, language, processes, sourced_only, genealogics):
    """ Processes the corpus and extracts semistructured data serialized into quick statements
        Needs a second pass on genealogics to correctly resolve family members
    """

    genealogics_url_to_id = {}

    params = ((i, item, language, sourced_only)
              for i, item in enumerate(io.load_scraped_items(corpus_dir)))

    count = 0
    for subj, prop, val, url in parallel.map(serialize_item, params,
                                             processes, flatten=True):
        statement = wikidata.finalize_statement(subj, prop, val, language, url,
                                                resolve_property=False, resolve_value=False)
        if not statement:
            continue

        out_file.write(statement.encode('utf8'))
        out_file.write('\n')

        if genealogics and url.startswith('http://www.genealogics.org/'):
            genealogics_url_to_id[url] = subj

        count += 1
        if count % 10000 == 0:
            logger.info('Produced %d statements so far' % count)

    logger.info('Produced %d statements' % count)

    if genealogics:
        logger.info('Starting second pass on genealogics')
        for subj, prop, val, url in resolve_genealogics_family(genealogics, genealogics_url_to_id):
            statement = wikidata.finalize_statement(subj, prop, val, language, url,
                                                    resolve_property=False, resolve_value=False)
            if not statement:
                continue

            out_file.write(statement.encode('utf8'))
            out_file.write('\n')

            count += 1
            if count % 10000 == 0:
                logger.info('Produced %d statements so far' % count)

        logger.info('Done, produced %d statements' % count)
    else:
        logger.info('skipping genealogics pass')
