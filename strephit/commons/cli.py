import click
from strephit.commons import tokenize, pos_tag, entity_linking, split_sentences


CLI_COMMANDS = {
    'tokenize': tokenize.main,
    'pos_tag': pos_tag.main,
    'entity_linking': entity_linking.main,
    'split_sentences': split_sentences.main,
}


@click.group(name='commons', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Common utilities used by others """
    pass
