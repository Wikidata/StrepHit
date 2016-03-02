# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import click
import json
import logging
from strephit.commons import io, wikidata, parallel, text


logger = logging.getLogger(__name__)


def serialize_item((i, item, cache, language, sourced_only)):
    """ Converts an item to quick statements. Takes a single tuple as parameter
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
    wid = wikidata.name_resolver('P1477', name, language)
    if not wid:
        logger.debug('cannod find wikidata id for item %s (%s), skipping' % (
            _id, name)
        )
        return

    data.update(item)
    data['name'] = name  # use the fixed name

    for key, value in data.iteritems():
        if not isinstance(value, list):
            value = [value]

        for val in value:
            statement = wikidata.finalize_statement(wid, key, val, language, url)
            if statement:
                yield statement
            else:
                logger.debug('skipped property %s of %s (%s): %s' % (key, _id, name, val))

    for each in honorifics:
        statement = wikidata.finalize_statement(wid, 'honorific', each, language, url)
        if statement:
            yield statement


@click.command()
@click.argument('corpus-dir', type=click.Path())
@click.argument('out-file', type=click.File('w'))
@click.option('--cache/--no-cache', default=True, help='Cache HTTP requests')
@click.option('--sourced-only/--allow-unsourced', default=True)
@click.option('--language', default='en', help='The names are searched in this language')
@click.option('--processes', '-p', default=0)
def process_semistructured(corpus_dir, out_file, cache, language, processes, sourced_only):
    """ Processes the corpus and extracts semistructured data serialized into quick statements
    """

    params = ((i, item, cache, language, sourced_only)
              for i, item in enumerate(io.load_scraped_items(corpus_dir)))
    for i, statement in enumerate(parallel.map(serialize_item, params, processes, flatten=True)):
        out_file.write(statement.encode('utf8'))
        out_file.write('\n')

        if (i + 1) % 10000 == 0:
            logger.info('Produced %d statements so far' % (i + 1))

    logger.info('Produced %d statements' % (i + 1))