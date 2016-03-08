#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from __future__ import absolute_import

import click
import logging
import json
from sys import exit
from nltk.data import load
from strephit.commons.io import load_corpus
from strephit.commons import parallel


logger = logging.getLogger(__name__)


class SentenceSplitter():
    """ Sentence splitting splits a natural language text into sentences """
    
    # Pre-trained models available as NLTK language resources
    model_path = 'tokenizers/punkt/%s.pickle'
    supported_models = {
        'cz': model_path % 'czech',
        'da': model_path % 'danish',
        'nl': model_path % 'dutch',
        'en': model_path % 'english',
        'et': model_path % 'estonian',
        'fi': model_path % 'finnish',
        'fr': model_path % 'french',
        'de': model_path % 'german',
        'el': model_path % 'greek',
        'it': model_path % 'italian',
        'no': model_path % 'norwegian',
        'pl': model_path % 'polish',
        'pt': model_path % 'portuguese',
        'sl': model_path % 'slovene',
        'es': model_path % 'spanish',
        'sv': model_path % 'swedish',
        'tr': model_path % 'turkish'
    }
    
    def __init__(self, language):
        """
        :param str language: ISO 639-1 language code. See https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
        """
        self.language = language
        model = self.supported_models.get(language)
        if model:
            self.splitter = load(model)
        else:
            raise ValueError("Invalid or unsupported language: '%s'. Please use one of the currently supported ones: %s" % (language, self.supported_models.keys()))

    def split(self, text):
        """
        Split the given text into sentences.
        Leading and trailing spaces are stripped.
        Newline characters are first interpreted as sentence boundaries.
        Then, the sentence splitter is run.
        :param str text: Text to be split
        :return: a list of sentences
        :rtype: list
        """
        sentences = []
        logger.debug("Splitting text into sentences: %s" % text)
        sentences_by_newline = text.strip().split('\n')
        logger.debug("%d sentences split by the newline character: %s" % (len(sentences_by_newline), sentences_by_newline))
        for each in sentences_by_newline:
            split = self.splitter.tokenize(each)
            for sentence in split:
                sentences.append(sentence)
        logger.debug("%d total sentences: %s" % (len(sentences), sentences))
        return sentences


@click.command()
@click.argument('input-dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('document-key')
@click.argument('language-code')
@click.option('--output-file', '-o', type=click.File('w'), default='-')
@click.option('--processes', '-p', default=0)
def main(input_dir, document_key, language_code, output_file, processes):
    """ Split an input corpus into sentences """
    corpus = load_corpus(input_dir, document_key, text_only=True)
    s = SentenceSplitter(language_code)
    logger.info("Starting sentence splitting of the input corpus ...")

    for sentences in parallel.map(lambda (i, text): json.dumps({i: s.split(text)}), enumerate(corpus), processes):
        output_file.write(sentences)
        output_file.write('\n')

    return 0


if __name__ == '__main__':
    exit(main())
