#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import click
import json
import os
import logging


logger = logging.getLogger(__name__)


def load_scraped_items(items_dir):
    """ Loads all the items from a directory. All the files in that directory
        should contain JSON-serialized items, one per line.
        :param str items_dir: Local path containing the data files.
    """
    for name in os.listdir(items_dir):
        if name.endswith('.jsonl') or name.endswith('.jsonlines'):
            f = os.path.join(items_dir, name)
            with open(f) as source:
                logger.info("Loaded input file '%s'" % name)
                for n, line in enumerate(source):
                    logger.debug("Processing item #%d ..." % n)
                    try:
                        yield json.loads(line)
                    except ValueError:
                        logger.warn('cannot load item at row %d of file %s' % (n, name))


def load_corpus(items_dir, document_key):
    """Load an input corpus from a directory with scraped items, in a memory-efficient way.
       Each input file must contain one JSON object per line.
       :param str document_key: a scraped item dictionary key holding textual documents
    """
    for item in load_scraped_items(items_dir):
        document = item.get(document_key)
        if document:
            yield document
        else:
            logger.warning("Skipped item with no textual document")
            logger.debug("Item: '%s'. Provided item key: '%s'" % (item, document_key))


@click.command()
@click.argument('corpus-dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('output-dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('document-key')
@click.option('--items-per-file', '-i', default=10000)
@click.option('--min-length', '-l', default=50)
def preprocess_corpus(corpus_dir, document_key, output_dir, items_per_file, min_length):
    """ Remove items without text documents or whose text document is too short """
    filename = 'corpus-%d.jsonlines'
    count = 0
    current_file = open(os.path.join(output_dir, filename % 0), 'w')

    for item in load_scraped_items(corpus_dir):
        if document_key in item and len(item[document_key]) >= min_length:
            count += 1
            if count % items_per_file == 0:
                fname = filename % (count / items_per_file)
                logger.info('processed %d items so far, continuing in %s' % (count, fname) )
                current_file.close()
                current_file = open(os.path.join(output_dir, fname), 'w')
            json.dump(item, current_file)
            current_file.write('\n')
