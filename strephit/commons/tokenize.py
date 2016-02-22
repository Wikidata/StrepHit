#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import

import click
import logging
import regex
from sys import exit
from strephit.commons.io import load_corpus


logger = logging.getLogger(__name__)


class Tokenizer():
    """ Tokenization splits a natural language utterance into words (tokens) """
    
    # Lookup the tokenization regex given the language code
    tokenization_regexps = {
        'en': ur'[^\p{L}\p{N}]+'
    }
    
    def __init__(self, language):
        self.language = language
        tokenization_regex = self.tokenization_regexps.get(self.language)
        if tokenization_regex:
            self.tokenization_regex = tokenization_regex
        else:
            raise ValueError("Invalid or unsupported language: '%s'. Please use one of the currently supported languages: %s" % (language, self.tokenization_regexps.keys()))
        

    def tokenize(self, sentence):
        """ Tokenize and normalize (lowercase) the given sentence.
            You can also pass a generic text, but you will lose the sentence segmentation.
            :param str sentence: a natural language sentence or text to be tokenized
            :return: the list of tokens
            :rtype: list
        """
        tokens = regex.split(self.tokenization_regex, unicode(sentence.lower()))
        logger.debug("'%s' tokenized into %s using regex %s" % (sentence, tokens, self.tokenization_regex))
        # Skip empty tokens
        return [token for token in tokens if token]


@click.command()
@click.argument('input-dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('document-key')
@click.argument('language-code')
@click.option('-o', '--output-file', type=click.File('w'), default='tokenized.json')
def main(input_dir, document_key, language_code, output_file):
    """ Tokenize an input corpus.
        Sentence splitting is not performed.
    """
    corpus = load_corpus(input_dir, language_code)
    t = Tokenizer(language_code)
    logger.info("Starting Tokenization of the input corpus ...")
    for i, document in enumerate(corpus):
        tokens = t.tokenize(document)
        output_file.write(json.dumps({i: tokens}, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    exit(main())
