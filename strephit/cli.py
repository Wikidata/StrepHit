from __future__ import absolute_import

import click

import strephit
from strephit.commons import logging, cache

CLI_COMMANDS = {
    'annotation': strephit.annotation.cli.cli,
    'commons': strephit.commons.cli.cli,
    'corpus_analysis': strephit.corpus_analysis.cli.cli,
    'extraction': strephit.extraction.cli.cli,
    'web_sources_corpus': strephit.web_sources_corpus.cli.cli,
}


@click.group(commands=CLI_COMMANDS)
@click.pass_context
@click.option('--log-level', type=(unicode, click.Choice(logging.LEVELS)), multiple=True)
@click.option('--cache-dir', type=click.Path(file_okay=False, resolve_path=True), default=None)
def cli(ctxm, log_level, cache_dir):
    logging.setup()
    for module, level in log_level:
        logging.setLogLevel(module, level)

    if cache_dir:
        cache.BASE_DIR = cache_dir
