# -*- encoding: utf-8 -*-
import click

from strephit.extraction.process_semistructured import process_semistructured
from strephit.extraction import extract_sentences

CLI_COMMANDS = {
    'process_semistructured': process_semistructured,
    'extract_sentences': extract_sentences.main,
}


@click.group(name='extraction', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Data extraction from the corpus """
    pass
