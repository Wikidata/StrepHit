#!/usr/bin/env python
# -*- encoding: utf-8 -*-   
from __future__ import absolute_import

import click
import json
import logging
from sys import exit
from treetaggerwrapper import TreeTagger, make_tags
from treetaggerpoll import TaggerProcessPoll
from treetaggerwrapper import make_tags, NotTag
from nltk import pos_tag, word_tokenize, pos_tag_sents
from strephit.commons.io import load_corpus
from strephit.commons.tokenize import Tokenizer


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
        self.tokenizer = Tokenizer(language)
        self.tagger = TreeTagger(
            TAGLANG=language,
            TAGDIR=tt_home,
            # Explicit TAGOPT: the default has the '-no-unknown' option,
            # which prints the token rather than '<unknown>' for unknown lemmas
            # We'd rather skip unknown lemmas, as they are likely to be wrong tags
            TAGOPT=u'-token -lemma -sgml -quiet',
            # Use our tokenization logic (CHUNKERPROC here)
            CHUNKERPROC=self._tokenizer_wrapper,
            **kwargs
        )

    def _tokenizer_wrapper(self, tagger, text_list):
        """ Wrap the tokenization logic with the signature required by the TreeTagger CHUNKERPROC kwarg
        """
        tokens = []
        for text in text_list:
            for token in self.tokenizer.tokenize(text):
                tokens.append(token)
        return tokens

    def _postprocess_tags(self, tags, skip_unknown=True):
        """ Clean tagged data from non-tags and unknown lemmas (optionally) """
        clean_tags = []
        for tag in tags:
            if type(tag) == NotTag:
                logger.warn("Non-tag found: %s. Skipping ..." % repr(tag))
                continue
            if skip_unknown and tag.lemma == u'<unknown>':
                logger.warn("Unknown lemma found: %s. Skipping ..." % repr(tag))
                continue
            clean_tags.append(tag)
        return clean_tags

    def tag_one(self, text, **kwargs):
        """ POS-Tags the given text, eventually skipping unknown lemmas """
        return self._postprocess_tags(make_tags(self.tagger.tag_text(text)))

    def tag_many(self, documents, batch_size=10000, **kwargs):
        """ POS-Tags many text documents. Use this for massive text tagging """
        tt_pool = TaggerProcessPoll(
            TAGLANG=self.language,
            TAGDIR=self.tt_home,
            TAGOPT=u'-token -lemma -sgml -quiet',
            CHUNKERPROC=self._tokenizer_wrapper
        )
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
            yield self._postprocess_tags(make_tags(job.result))


def get_pos_tagger(language, **kwargs):
    """ Returns an initialized instance of the preferred POS tagger for the given language """
    return TTPosTagger(language, **kwargs)


@click.command()
@click.argument('input-dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('document-key')
@click.argument('language-code')
@click.option('-t', '--tagger', type=click.Choice(['tt', 'nltk']), default='tt')
@click.option('-o', '--output-file', type=click.File('w'), default='pos_tagged.json')
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
