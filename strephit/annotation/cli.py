# -*- encoding: utf-8 -*-
import click
from strephit.annotation import post_job, pull_results


CLI_COMMANDS = {
    'post_job': post_job.main,
    'pull_results': pull_results.main,
}


@click.group(name='annotation', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Corpus annotation via crowdsourcing """
    pass
