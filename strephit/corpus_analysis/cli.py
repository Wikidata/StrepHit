import click

from strephit.corpus_analysis import extract_framenet_frames, rank_verbs, compute_lu_distribution, statistics

CLI_COMMANDS = {
    'extract_framenet_frames': extract_framenet_frames.main,
    'rank_verbs': rank_verbs.main,
    'compute_lu_distribution': compute_lu_distribution.main,
    'find_statistics': statistics.main,
}


@click.group(name='corpus_analysis', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Corpus analysis module """
    pass
