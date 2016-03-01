# -*- encoding: utf-8 -*-
import click
from strephit.web_sources_corpus.preprocess_corpus import preprocess_corpus
from strephit.web_sources_corpus import run_all


CLI_COMMANDS = {
    'preprocess_corpus': preprocess_corpus,
    'run_all': run_all.main,
}


@click.group(name='web_sources_corpus', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Corpus retrieval from the web """
    pass
