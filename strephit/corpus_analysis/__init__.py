import click
from strephit.corpus_analysis import extract_framenet_frames, rank_verbs


CLI_COMMANDS = {
    'extract_framenet_frames': extract_framenet_frames.main,
    'rank_verbs': rank_verbs.main
}


@click.group(name='corpus_analysis', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Corpus analysis module """
    pass
