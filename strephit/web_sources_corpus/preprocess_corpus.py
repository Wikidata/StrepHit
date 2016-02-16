# -*- encoding: utf-8 -*-
import os
import json
import click
import logging
from strephit.commons.io import load_scraped_items


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
