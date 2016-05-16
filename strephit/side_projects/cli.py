# -*- encoding: utf-8 -*-
import click

from strephit.side_projects import wlm

CLI_COMMANDS = {
    'wlm': wlm.main,
}


@click.group(name='extraction', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Side projects scripts """
    pass
