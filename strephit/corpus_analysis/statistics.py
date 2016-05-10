import logging
from urlparse import urlparse
from collections import defaultdict

import click

from strephit.commons.io import load_scraped_items
from strephit.commons import parallel

logger = logging.getLogger(__name__)


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
                logger.warn('found an item without URL, name: %s, bio: %s',
                            doc.get('name'), doc.get('bio', '')[:100] + ' ...')
                sources['_skipped_'] += 1
                continue
            elif with_bio and len(doc.get('bio') or '') < 5:
                continue

            parsed = urlparse(url)
            if parsed.netloc:
                sources[parsed.netloc] += 1
            else:
                logger.warn('cannot parse URL: %s', url)
                sources['_skipped_'] += 1
        return sources

    aggregated_sources = defaultdict(int)
    corpus = parallel.make_batches(load_scraped_items(corpus), 1000)
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
        logger.warn('Cannot import matplotlib, skipping chart')
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


@main.command()
@click.argument('corpus', type=click.Path(exists=True))
def about_biographies_count(corpus):
    """ Finds how many items have/don't have a biography
    """
    count = with_bio = characters = 0
    for doc in load_scraped_items(corpus):
        count += 1
        if doc.get('bio') and len(doc['bio']) > 5:
            with_bio += 1
            characters += len(doc['bio'])

    print 'Total number of items:', count
    print 'Items with a biography %d (%.2f %%)' % (with_bio, 100. * with_bio / count)
    print 'Cumulative length of biographies: %d characters' % characters

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warn('Cannot import matplotlib, skipping chart')
        return

    plt.bar([0, 1], [count - with_bio, with_bio], width=0.75)
    plt.xticks([0.375, 1.375], ['Without Biography', 'With Biography'])
    plt.grid(True, axis='y')
    plt.xlim((-0.5, 2.25))
    plt.show()

@main.command()
@click.argument('corpus', type=click.Path(exists=True))
@click.option('--bins', '-b', default=50, help='Number of bins to use for the histogram')
@click.option('--log-y/--lin-y', help='Use a linear/logarithmic Y axis')
def about_biographies_length(corpus, bins, log_y):
    """ Computes an histogram of biography length
    """
    lengths = []
    for doc in load_scraped_items(corpus):
        if len(doc.get('bio') or '') > 5:
            lengths.append(len(doc['bio']))

    width = float(max(lengths)) / bins
    buckets = defaultdict(int)
    for each in lengths:
        buckets[int(each / width)] += 1

    for i in xrange(max(buckets.keys())):
        print '%d - %d: %d' % (i * width, (i + 1) * width - 1, buckets[i])

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warn('Cannot import matplotlib, skipping chart')
        return

    plt.title('Biography length distribution for %d items' % len(lengths))
    plt.xlabel('Biography length in characters')
    plt.ylabel('Number of items')
    plt.hist(lengths, bins=bins, log=log_y)
    plt.grid(True)
    plt.tight_layout()
    plt.show()
