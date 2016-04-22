import click

from strephit.rule_based import classify

CLI_COMMANDS = {
    'classify': classify.main,
}


@click.group(name='rule_based', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Unsupervised fact extraction """
    pass
