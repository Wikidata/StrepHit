# -*- encoding: utf-8 -*-
import click

from strephit.annotation import create_crowdflower_input, post_job, pull_results, generate_cml, parse_results

CLI_COMMANDS = {
    'create_crowdflower_input': create_crowdflower_input.main,
    'generate_cml': generate_cml.main,
    'post_job': post_job.main,
    'pull_results': pull_results.main,
    'parse_results': parse_results.main,
}


@click.group(name='annotation', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Corpus annotation via crowdsourcing """
    pass
