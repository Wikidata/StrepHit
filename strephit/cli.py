import click
import sys
from strephit import commons
from strephit.commons import logger


CLI_COMMANDS = {
    'commons': commons.cli,
}


@click.group(commands=CLI_COMMANDS)
@click.pass_context
@click.option('--log-level', type=click.Choice(['debug', 'info', 'warning']), default='info')
@click.option('--log-file', type=click.File('w'), default=sys.stderr)
def cli(ctx, log_level, log_file):
    logger.logger = logger.setup_logger(log_level, log_file)
