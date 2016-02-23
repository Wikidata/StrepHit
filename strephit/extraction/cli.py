# -*- encoding: utf-8 -*-
import click
from strephit.extraction.process_semistructured import process_semistructured


CLI_COMMANDS = {
    'process_semistructured': process_semistructured,
}


@click.group(name='extraction', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Data extraction from the corpus """
    pass
