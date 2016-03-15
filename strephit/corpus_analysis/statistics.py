import click
import json
import logging
from urlparse import urlparse
from collections import defaultdict
from strephit.commons.io import load_scraped_items
from strephit.commons import parallel


logger = logging.getLogger(__name__)


def bulkenize(iterable, size):
    bulk = []
    for each in iterable:
        bulk.append(each)
        if len(bulk) % size == 0:
            yield bulk
            bulk = []
    if bulk:
        yield bulk


@click.group()
def main():
    """ Computes and plots some statistics about the corpus
    """
    pass


@main.command()
@click.argument('corpus', type=click.Path(exists=True))
@click.option('--with-bio', '-b', is_flag=True)
@click.option('--processes', '-p', default=0)
def about_sources(corpus, processes, with_bio):
    """ Items' sources
    """
    def worker(items):
        sources = defaultdict(int)
        for doc in items:
            url = doc.get('url')
            if not url:
                #logger.warn('found an item without URL, name: %s, bio: %s',
                #            doc.get('name'), doc.get('bio', '')[:100] + ' ...')
                print 'E',
                sources['_skipped_'] += 1
                continue
            elif with_bio and not doc.get('bio'):
                sources['_skipped_'] += 1
                continue

            parsed = urlparse(url)
            if parsed.netloc:
                sources[parsed.netloc] += 1
            else:
                sources['_skipped_'] += 1
        return sources

    aggregated_sources = defaultdict(int)
    corpus = bulkenize(load_scraped_items(corpus), 1000)
    for sources in parallel.map(worker, corpus, processes):
        for k, v in sources.iteritems():
            aggregated_sources[k] += v

    aggregated_sources = sorted(aggregated_sources.items(),
                                key=lambda (_, v): v, reverse=True)
    for source, count in aggregated_sources:
        print source, count

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warn('Cannot import matplotlib, skipping pie chart')
        return

    count = sum(c for s, c in aggregated_sources)
    display_sources = filter(lambda (s, v): float(v) / count >= 0.01,
                             aggregated_sources)
    sources, values = map(list, zip(*display_sources))
    sources.append('Rest')
    values.append(count - sum(values))
    plt.pie(values, labels=sources)
    plt.axis('equal')
    plt.show()
