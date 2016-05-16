# -*- encoding: utf-8 -*-
import click
import csv
import logging
from strephit.commons import wikidata, cache
from collections import defaultdict

logger = logging.getLogger(__name__)


COLUMN_TO_PROPERTY = {
    'localit&agrave;': 'P131',
    'Prov': 'P131',
    'indirizzo': 'P969',
    'proprieta': 'P127',
    'WLMID': 'P2186',
}

@cache.cached
@wikidata.resolver('P127', 'P131')
def place_resolver(property, value, language, **kwargs):
    types = [
        3146899,      # diocese of the Catholic Church
        747074,      # comune of Italy
        515,         # city
        15089,       # province of Italy
    ]

    value = value.lower()
    if 'com.' in value or 'comune' in value:
        value = value.replace('com.', '').replace('comune', '').strip()
        types = [747074]
    elif 'prov.' in value or 'provincia' in value:
        value = value.replace('prov.', '').replace('provincia', '').strip()
        types = [15089]

    results = wikidata.search(value, language, type_=types)
    if results:
        res = results[0]['id']
        logger.debug('resolved "%s" to %s', value, res.encode('utf8'))
        return res
    else:
        logger.debug('could not resolve "%s"', value)
        return ''


@wikidata.resolver('P2186')
def wlmid_resolver(property, value, language, **kwargs):
    return value


@cache.cached
@wikidata.resolver('P969')
def indirizzo_resolver(property, value, language, **kwargs):
    return '%s@"%s"' % (language, value)


def process_row(data):
    subject = data['emergenza']

    resolved = defaultdict(lambda: [])
    for k, v in data.iteritems():
        if COLUMN_TO_PROPERTY.get(k):
            v = wikidata.resolve(COLUMN_TO_PROPERTY[k], v.decode('utf8'), 'it')
            if v:
                resolved[COLUMN_TO_PROPERTY[k]].append(v)

    info = {k: v for k, v in resolved.iteritems()}

    subject = wikidata.resolver_with_hints('ddd', subject, 'it', **info)
    if subject:
        statements = []
        for property, value in resolved.iteritems():
            stmt = wikidata.finalize_statement(subject, property, value,
                                               'it', resolve_property=False,
                                               resolve_value=False)
            if stmt is not None:
                statements.append(stmt)
    else:
        logger.warn('could not find the wikidata id of "%s"' % data['emergenza'])
        statements = None
    return statements


@click.command()
@click.argument('input', type=click.File('r'))
@click.argument('output', type=click.File('w'))
@click.option('--skipped', type=click.File('w'), help='save the ids of un-resolved monuments')
def main(input, output, skipped):
    rows = count = skipped_count = 0
    for row in csv.DictReader(input):
        rows += 1
        statements = process_row(row)
        if statements is None:
            skipped_count += 1
            if skipped:
                skipped.write(row['WLMID'])
                skipped.write('\n')
        else:
            for each in statements:
                count += 1
                output.write(each.encode('utf8'))
                output.write('\n')

    logger.info('Processed %d items (skipped %d), produced %d statements',
                rows, skipped_count, count)
