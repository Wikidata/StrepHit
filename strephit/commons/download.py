from __future__ import absolute_import
import zipfile
import contextlib
import os
import logging

import click
import requests

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

logger = logging.getLogger(__name__)


@click.group()
def main():
    """ Downloads external resources
    """
    pass


@main.command()
@click.option('--extract-to', default='dev/', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--zip-url', default='http://nlp.stanford.edu/software/stanford-corenlp-full-2015-12-09.zip')
def stanford_corenlp(extract_to, zip_url):
    logger.info('downloading to %s', extract_to)

    try:
        os.makedirs(extract_to)
    except OSError:
        pass

    with contextlib.closing(requests.get(zip_url, stream=True)) as r:
        with zipfile.ZipFile(StringIO(r.content)) as arch:
            for finfo in arch.infolist():
                fname = os.path.basename(finfo.filename)
                if fname.endswith('.jar') and \
                        'src' not in fname and \
                        'source' not in fname and \
                        'javadoc' not in fname:

                    logger.info(fname)
                    with open(os.path.join(extract_to, fname), 'w') as f:
                        f.write(arch.read(finfo))
