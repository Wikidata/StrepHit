#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
from commons.logger import logger
from sys import exit
from time import time
from nltk import pos_tag, word_tokenize
from treetaggerwrapper import TreeTagger, make_tags


def tag(text, tt_home):
    # Default NLTK's tokenizer
    # TreebankWordTokenizer + PunktSentenceTokenizer
    nltk_start = time()
    tokens = word_tokenize(text)
    # Default NLTK's POS tagger
    # ?
    # Use tagset='universal' for universal tagset
    nltk_tagged = pos_tag(tokens)
    nltk_end = time()
    nltk_execution = nltk_end - nltk_start
    logger.info("NLTK took %f seconds" % nltk_execution)

    # TreeTagger wrapper
    # Tokenization: ?
    # Default language: English
    # English: trained on Penn treebank
    # Default flags: -token -lemma -sgml -quiet -no-unknown
    tt_start = time()
    tt = TreeTagger(TAGDIR=tt_home)
    raw_tags = tt.tag_text(text)
    tt_end = time()
    tt_execution = tt_end - tt_start
    tt_tagged = make_tags(raw_tags)
    logger.info("TreeTagger took %f seconds" % tt_execution)
    return (nltk_tagged, nltk_execution), (tt_tagged, tt_execution)


@click.command()
@click.argument('input-file', type=click.File('rb'))
@click.option('--output-file', type=click.File('wb'), default='tagged.json')
@click.option('--tt-home')
def main(input_file, output_file, tt_home):
    output = []
    source = json.load(input_file)
    logger.info("Loaded input file '%s'" % input_file.name)
    nltk_total_execution = float()
    tt_total_execution = float()
    for item in source:
        output_item = item
        text = item.get('bio')
        if not text:
            logger.info("No bio for '%s'. Skipping ..." % item.get('name'))
            continue
        else:
            (nltk_tagged, nltk_execution), (tt_tagged, tt_execution) = tag(text, tt_home)
            nltk_total_execution += nltk_execution
            tt_total_execution += tt_execution
            logger.debug("NLTK output: %s" % nltk_tagged)
            logger.debug("TreeTagger output: %s" % tt_tagged)
            output_item['nltk'] = nltk_tagged
            output_item['TreeTagger'] = tt_tagged
            output.append(output_item)
            
    json.dump(output, output_file, indent=2)
    logger.info("Tagged data dumped to '%s'" % output_file.name)
    logger.info("Total items = %d" % len(source))
    logger.info("NLTK total execution time = %f seconds" % nltk_total_execution)
    logger.info("TreeTagger total execution time = %f seconds" % tt_total_execution)
    return 0

    
if __name__ == '__main__':
    exit(main())
