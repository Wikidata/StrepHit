import logging
from collections import defaultdict
from urlparse import urlparse
import json
import click
from strephit.commons import parallel
import random


logger = logging.getLogger(__name__)


def lu_count(sentences, processes=0, input_encoded=False):
    """ Count how many sentences per LU there are for each source

        :param iterable sentences: Corpus with the POS-tagged sentences
        :param int processes: how many processes to use for parallel execution
        :param bool input_encoded: whether the corpus is an iterable of dictionaries
         or an iterable of JSON-input_encoded documents. JSON-input_encoded
         documents are preferable over large size dictionaries for performance reasons
        :return: A dictionary source -> frequencies, where frequencies is
         another dictionary lemma -> count
        :type: bool
    """

    def worker(batch):
        freqs = defaultdict(lambda: 0)
        for row in batch:
            sentence = json.loads(row) if input_encoded else row

            parsed = urlparse(sentence['url'])
            if not parsed.netloc:
                logger.warn('cannot parse URL: %s', sentence['url'])
                return

            lu = sentence['lu']
            freqs[(parsed.netloc, lu)] += 1

        return freqs.items()

    frequencies = defaultdict(lambda: defaultdict(lambda: 0))
    for (source, lemma), count in parallel.map(worker, sentences, processes,
                                               batch_size=100, flatten=True):
        frequencies[source][lemma] += count
    return frequencies


def extract_sentences(sentences, probabilities, processes=0, input_encoded=False, output_encoded=False):
    """ Extracts some sentences from the corpus following the given probabilities

        :param iterable sentences: Extracted sentences
        :param dict probabilities: Conditional probabilities of extracting a sentence containing
         a specific LU given the source of the sentence. It is therefore a mapping
         source -> probabilities, where probabilities is itself a mapping LU -> probability
        :param int processes: how many processes to use for parallel execution
        :param bool input_encoded: whether the corpus is an iterable of dictionaries or an
         iterable of JSON-encoded documents. JSON-encoded documents are preferable
         over large size dictionaries for performance reasons
        :param bool output_encoded: whether to return a generator of dictionaries or a generator
         of JSON-encoded documents. Prefer encoded output for performance reasons
        :return: Generator of sentences
    """

    def worker(batch):
        for row in batch:
            sentence = json.loads(row) if input_encoded else row
            parsed = urlparse(sentence['url'])
            if not parsed.netloc:
                logger.warn('cannot parse URL: %s', sentence['url'])
                return

            lu = sentence['lu']
            p = probabilities[(parsed.netloc, lu)]

            if random.random() < p:
                yield parsed.netloc, lu, json.dumps(sentence) if output_encoded else sentence

    counts = defaultdict(lambda: 0)
    for source, lu, sentence in parallel.map(worker, sentences, processes,
                                             batch_size=100, flatten=True):
        counts[(source, lu)] += 1
        yield sentence

    aggs_lu = defaultdict(lambda: 0)
    aggs_source = defaultdict(lambda: 0)
    for (source, lu), n in counts.iteritems():
        aggs_lu[lu] += n
        aggs_source[source] += n

    logger.debug('aggregated statistics per LU: %s', aggs_lu)
    logger.debug('aggregated statistics per source: %s', aggs_source)


@click.command()
@click.argument('sentences', type=click.File('r'))
@click.argument('sentences-per-lu', type=click.FLOAT)
@click.option('--processes', '-p', default=0)
@click.option('-o', '--output', type=click.File('w'),
              default='dev/sentences-balanced.jsonlines')
def main(sentences, sentences_per_lu, processes, output):
    """ Stochastically extracts sentences so that there are a given number
        of sentences for each LU equally spread amongst the different sources
    """

    logger.info('Obtaining the LU distribution amongst sources')
    frequencies = lu_count(sentences, processes, input_encoded=True)

    number_of_sources = len(frequencies)
    number_of_lus = len(reduce(lambda x, y: x | y, map(set, frequencies.values())))
    lu_per_source = sentences_per_lu / number_of_sources

    logger.debug('Have %d LUs in %d sources', number_of_lus, number_of_sources)
    logger.info('Calculating the conditional probabilities of LUs given sources')

    probabilities = {}
    for source, lu_freqs in frequencies.iteritems():
        for lu, n in lu_freqs.iteritems():
            p = lu_per_source / n
            probabilities[(source, lu)] = p
            if p > 1.0:
                logger.warn('Not enough sentences with LU %s in source %s, '
                            'all of them will be taken', lu, source)
                logger.debug('should take %.2f, but only %d are available',
                             lu_per_source, n)

    logger.info('Extracting sentences from the corpus')
    logger.debug('Expect roughly %d sentences, unless some sources are lacking',
                 sentences_per_lu * number_of_lus)

    sentences.seek(0)
    count = 0
    for i, sentence in enumerate(extract_sentences(sentences, probabilities, processes,
                                                   input_encoded=True, output_encoded=True)):
        output.write(sentence)
        output.write('\n')

        count = i + 1
        if count % 1000 == 0:
            logger.info('Extracted %d sentences', count)

    logger.info('Finished, extracted %d sentences', count)
