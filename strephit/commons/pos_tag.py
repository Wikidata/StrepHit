#!/usr/bin/env python
# -*- encoding: utf-8 -*-   
from __future__ import absolute_import

import click
import json
import logging
from sys import exit
from strephit.commons.io import load_corpus
from treetaggerwrapper import TreeTagger, make_tags
from treetaggerpoll import TaggerProcessPoll
from treetaggerwrapper import make_tags, NotTag
from nltk import pos_tag, word_tokenize, pos_tag_sents


logger = logging.getLogger(__name__)


class NLTKPosTagger():
    """part-of-speech tagger implemented using the NLTK library"""
    
    def __init__(self, language):
        self.language = language

    def tag_many(self, documents, batch_size=None, tagset=None):
        """ POS-Tag many documents. """
        return pos_tag_sents((word_tokenize(d) for d in documents), tagset)

    def tag_one(self, text, tagset):
        """ POS-Tags the given text """
        return pos_tag(word_tokenize(text, tagset))


class TTPosTagger():
    """ part-of-speech tagger implemented using tree tagger and treetaggerwrapper """

    def __init__(self, language, tt_home=None, **kwargs):
        self.language = language
        self.tt_home = tt_home
        self.tagger = TreeTagger(TAGLANG=language, TAGDIR=tt_home, **kwargs)

    def tag_one(self, text, **kwargs):
        """ POS-Tags the given text """
        return make_tags(self.tagger.tag_text(text))

    def tag_many(self, documents, batch_size=10000, **kwargs):
        """ POS-Tags many text documents. Use this for massive text tagging """
        tt_pool = TaggerProcessPoll(TAGLANG=self.language, TAGDIR=self.tt_home)
        try:
            jobs = []
            for i, text in enumerate(documents):
                jobs.append(tt_pool.tag_text_async(text, **kwargs))
                if i % batch_size == 0:
                    for each in self._finalize_batch(jobs):
                        yield each
                    jobs = []
            for each in self._finalize_batch(jobs):
                yield each
        finally:
            tt_pool.stop_poll()

    def _finalize_batch(self, jobs):
        for job in jobs:
            job.wait_finished()
            tags = []
            tagged = make_tags(job.result)
            # TreeTagger may find non-tags, probably some scraped garbage
            # Skip them, but keep a trace in the log
            for tag in tagged:
                if type(tag) == NotTag:
                    logger.warn("Non-tag found: '%s'. Skipping ..." % tag)
                else:
                    tags.append(tag)
            yield tags


def get_pos_tagger(language, **kwargs):
    """ Returns an initialized instance of the preferred POS tagger for the given language """
    return TTPosTagger(language, **kwargs)


@click.command()
@click.argument('input-dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('document-key')
@click.argument('language-code')
@click.option('-t', '--tagger', type=click.Choice(['tt', 'nltk']), default='tt')
@click.option('-o', '--output-file', type=click.File('wb'), default='pos_tagged.json')
@click.option('--tt-home', type=click.Path(exists=True, dir_okay=True, resolve_path=True), help="home directory for TreeTagger")
@click.option('--batch-size', '-b', default=10000)
def main(input_dir, document_key, language_code, tagger, output_file, tt_home, batch_size):
    """ Perform part-of-speech (POS) tagging over an input corpus.
    """
    if tagger == 'tt':
        pos_tagger = TTPosTagger(language_code, tt_home)
    else:
        pos_tagger = NLTKPosTagger(language_code)

    corpus = load_corpus(input_dir, document_key)
    for i, tagged_document in enumerate(pos_tagger.tag_many(corpus, batch_size)):
        output_file.write(json.dumps(tagged_document) + '\n')
    return 0


if __name__ == '__main__':
    exit(main())
