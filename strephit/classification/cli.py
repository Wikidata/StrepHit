# -*- encoding: utf-8 -*-
import click

from strephit.classification import model_selection, classify

CLI_COMMANDS = {
    'model_selection': model_selection.main,
    'classify': classify.main,
}


@click.group(name='classification', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Roles classification """
    pass
