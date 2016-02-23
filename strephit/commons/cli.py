import click
from strephit.commons import tokenize, pos_tag, io


CLI_COMMANDS = {
    'tokenize': tokenize.main,
    'pos_tag': pos_tag.main,
}


@click.group(name='commons', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Common utilities used by others """
    pass
