# -*- encoding: utf-8 -*-
import os
import json
import logging
import hashlib

import click

from strephit.commons.io import load_scraped_items

logger = logging.getLogger(__name__)


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
        if item.get(document_key) and len(item[document_key]) > min_length:
            count += 1
            if count % items_per_file == 0:
                fname = filename % (count / items_per_file)
                logger.info('processed %d items so far, continuing in %s' % (count, fname))
                current_file.close()
                current_file = open(os.path.join(output_dir, fname), 'w')
            item['id'] = hashlib.sha1(item[document_key].encode('utf8')).hexdigest()
            json.dump(item, current_file)
            current_file.write('\n')
