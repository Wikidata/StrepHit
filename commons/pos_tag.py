#!/usr/bin/env python
# -*- encoding: utf-8 -*-   

import click
import json
from sys import exit
from commons.logger import logger
from commons.io_utils import load_corpus


class PosTagger():
    """A part-of-speech tagger: it can leverage different libraries for POS tagging."""
    
    def __init__(self, language, tagger, tt_home=None):
        if tagger not in ['tt', 'nltk']:
            raise ValueError("Unsupported or invalid POS tagging library: please use 'tt' for TreeTagger or 'nltk' for NLTK")
        self.language = language
        self.tagger = tagger
        self.tt_home = tt_home


    def tag_many(self, texts):
        """ Run a multi-process POS-tagger over a list of input texts.
            Works only with TreeTagger.
        """
        if self.tagger == 'tt':
            from treetaggerpoll import TaggerProcessPoll
            from treetaggerwrapper import make_tags
            jobs = []
            tt_pool = TaggerProcessPoll(TAGLANG=self.language, TAGDIR=self.tt_home)
            for text in texts:
                jobs.append(tt_pool.tag_text_async(text))
            for i, job in enumerate(jobs):
                job.wait_finished()
                yield make_tags(job.result)
                jobs[i] = None
            tt_pool.stop_poll()
        elif self.tagger == 'nltk':
            raise NotImplementedError("Multi-process POS tagging with NLTK is not yet implemented.")
    
    
    def tag_one(self, text):
        """Run a single-threaded POS-tagger over an input text."""
        if self.tagger == 'tt':
            from treetaggerwrapper import TreeTagger, make_tags
            tt = TreeTagger(TAGLANG=self.language, TAGDIR=self.tt_home)
            return make_tags(tt.tag_text(text))
        elif self.tagger == 'nltk':
            from nltk import pos_tag, word_tokenize
            return pos_tag(word_tokenize(text))


@click.command()
@click.argument('input_dir', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('language_code')
@click.option('-t', '--tagger', type=click.Choice(['tt', 'nltk']), default='tt')
@click.option('-o', '--output-file', type=click.File('wb'), default='pos_tagged.json')
@click.option('--tt-home', type=click.Path(exists=True, dir_okay=True, resolve_path=True), help="home directory for TreeTagger")
def main(input_dir, language_code, tagger, output_file, tt_home):
    """ Perform part-of-speech (POS) tagging over an input corpus.
    """
    pos_tagger = PosTagger(language_code, tagger, tt_home)
    texts = [item['bio'] for item in load_corpus(input_dir)]
    for tagged_text in pos_tagger.tag_many(texts):
        output_file.write(json.dumps(tagged_text))
    return 0


if __name__ == '__main__':
    exit(main())