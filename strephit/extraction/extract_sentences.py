#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
from strephit.commons.io import load_dumped_corpus
from strephit.commons.tokenize import Tokenizer
from sys import exit

logger = logging.getLogger(__name__)


def extract_sentences(corpus, document_key, language, matches):
    """
    Extract sentences from the given corpus by matching tokens against a given set.
    :param corpus: Iterable of documents containing text and metadata
    :param str document_key: dict key to get the text documents
    :param str language: language code used for tokenization and sentence splitting
    :param dict matches: Dict with corpus lemmas as keys and tokens to be matched as values
    :return: the corpus, updated with the extracted sentences
    :rtype: dict
    """
    sentence_id = 0
    for item in corpus:
        extracted = 0
        item['sentences'] = []
        # Each input item should always contain text documents
        # Raise KeyError otherwise
        document = item[document_key]
        # TODO inject sentence splitter here
        sentence = document
        tokenizer = Tokenizer(language)
        # Remember to lowercase
        sentence_tokens = [token.lower() for token in tokenizer.tokenize(document)]
        for lemma, match_tokens in matches.iteritems():
            # Remember to lowercase
            if any(match.lower() in sentence_tokens for match in match_tokens):
                # logger.debug("Token '%s' appears in sentence '%s'" % (match, sentence))
                extracted += 1
                matched_sentence = {
                    'id': sentence_id,
                    'lu': lemma,
                    'text': sentence
                }
                item['sentences'].append(matched_sentence)
                sentence_id += 1
        yield item, extracted


@click.command()
@click.argument('corpus', type=click.File())
@click.argument('document_key')
@click.argument('language_code')
@click.argument('matches', type=click.File())
@click.option('--output', '-o', type=click.File('w'), default='sentences.jsonlines')
def main(corpus, document_key, language_code, matches, output):
    """ Extract corpus sentences containing at least one token in the given set. """
    loaded = load_dumped_corpus(corpus, document_key)
    updated = extract_sentences(loaded, document_key, language_code, json.load(matches))
    total = 0
    for item, extracted in updated:
        total += extracted
        output.write(json.dumps(item) + '\n')
    logger.info("Total sentences extracted: %d" % extracted)
    return 0

    
if __name__ == '__main__':
    exit(main())
