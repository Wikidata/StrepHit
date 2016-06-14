#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import logging
from collections import defaultdict, OrderedDict
from sys import exit
from numpy import average

import click
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from strephit.commons.io import load_corpus, load_scraped_items
from strephit.commons import parallel

logger = logging.getLogger(__name__)

VERBAL_PREFIXES = {
    'en': 'V',
    'it': 'VER',
}


def get_similarity_scores(verb_token, vectorizer, tf_idf_matrix):
    """ Compute the cosine similarity score of a given verb token against the input corpus TF/IDF matrix.

        :param str verb_token: Surface form of a verb, e.g., *born*
        :param sklearn.feature_extraction.text.TfidfVectorizer vectorizer: Vectorizer
         used to transform verbs into vectors
        :return: cosine similarity score
        :rtype: ndarray
    """
    verb_token_vector = vectorizer.transform([verb_token])
    # Here the linear kernel is the same as the cosine similarity, but faster
    # cf. http://scikit-learn.org/stable/modules/metrics.html#cosine-similarity
    scores = linear_kernel(verb_token_vector, tf_idf_matrix)
    logger.debug("Corpus-wide TF/IDF scores for '%s': %s" % (verb_token, scores))
    logger.debug("Average TF/IDF score for '%s': %f" % (verb_token, average(scores)))
    return scores


def produce_lemma_tokens(pos_tagged_path, pos_tag_key, language):
    """ Extracts a map from lemma to all its tokens

        :param str pos_tagged_path: path of the pos-tagged corpus
        :param str pos_tag_key: where the pos tag data is in each item
        :param language: language of the corpus
        :return: mapping from lemma to tokens
        :rtype: dict
    """
    corpus = load_scraped_items(pos_tagged_path)
    lemma_tokens = defaultdict(set)

    for item in corpus:
        for token, pos, lemma in item.get(pos_tag_key, []):
            if pos.startswith(VERBAL_PREFIXES[language]):
                lemma_tokens[lemma.lower()].add(token.lower())

    return lemma_tokens


def compute_tf_idf_matrix(corpus_path, document_key):
    """ Computes the TF-IDF matrix of the corpus

        :param str corpus_path: path of the corpus
        :param str document_key: where the textual content is in the corpus
        :return: a vectorizer and the computed matrix
        :rtype: tuple
    """
    corpus = load_corpus(corpus_path, document_key, text_only=True)
    vectorizer = TfidfVectorizer()
    return vectorizer, vectorizer.fit_transform(corpus)


class TFIDFRanking:
    """ Computes TF-IDF based rankings.
        The first ranking is based on the average TF-IDF score of each lemma over all corpus
        The second ranking is based on the average standard deviation of TF-IDF scores
        of each lemma over all corpus
    """

    def __init__(self, vectorizer, verbs, tfidf_matrix):
        self.vectorizer = vectorizer
        self.verbs = verbs
        self.tfidf_matrix = tfidf_matrix

    def score_lemma(self, lemma):
        """ Computess TF-IDF based score of a single lemma

            :param str lemma: The lemma to score
            :return: tuple with lemma, average tf-idf, average of tf-idf standard deviations
            :rtype: tuple of (str, float, float)
        """
        tf_idfs, st_devs = [], []
        for token in self.verbs[lemma]:
            scores = get_similarity_scores(token, self.vectorizer, self.tfidf_matrix)
            tf_idfs += filter(None, scores.flatten().tolist())
            st_devs.append(scores.std())

        return lemma, average(tf_idfs), average(st_devs)

    def find_ranking(self, processes=0):
        """ Ranks the verbs

            :param int processes: How many processes to use for parallel ranking
            :return: tuple with average tf-idf and average standard deviation ordered rankings
            :rtype: tuple of (OrderedDict, OrderedDict)
        """
        tfidf_ranking = {}
        stdev_ranking = {}
        for lemma, tfidf, stdev in parallel.map(self.score_lemma, self.verbs, processes):
            tfidf_ranking[lemma] = tfidf
            stdev_ranking[lemma] = stdev
        return (OrderedDict(sorted(tfidf_ranking.items(), key=lambda x: x[1], reverse=True)),
                OrderedDict(sorted(stdev_ranking.items(), key=lambda x: x[1], reverse=True)))


class PopularityRanking:
    """ Ranking based on the popularity of each verb. Simply counts the
        frequency of each lemma over all corpus
    """

    def __init__(self, corpus_path, pos_tag_key):
        self.tags = self._flatten(item.get(pos_tag_key) for item in load_scraped_items(corpus_path))

    @staticmethod
    def _flatten(iterable):
        for each in iterable:
            for x in each:
                yield x

    @staticmethod
    def _bulkenize(iterable, bulk_size):
        acc = []
        for each in iterable:
            acc.append(each)
            if len(acc) % bulk_size == 0:
                yield acc
                acc = []

        if acc:
            yield acc

    @staticmethod
    def score_from_tokens(tokens):
        scores = defaultdict(int)
        for token, pos, lemma in tokens:
            if pos.startswith('V'):
                scores[lemma.lower()] += 1
        return scores

    def find_ranking(self, processes=0, bulk_size=10000, normalize=True):
        ranking = defaultdict(int)
        for score in parallel.map(self.score_from_tokens,
                                  self._bulkenize(self.tags, bulk_size),
                                  processes):

            for k, v in score.iteritems():
                ranking[k] += v

        ranking = OrderedDict(sorted(ranking.items(), key=lambda x: x[1], reverse=True))

        if normalize:
            max_score = float(ranking[next(iter(ranking))])
            for lemma, score in ranking.iteritems():
                ranking[lemma] = score / max_score

        return ranking


def harmonic_ranking(*rankings):
    """ Combines individual rankings with an harmonic mean to obtain a final ranking

        :param rankings: dictionary of individual rankings
        :return: the new, combined ranking
    """
    def product(x, y):
        return x * y

    def sum(x, y):
        return x + y

    def get(k):
        return (r[k] for r in rankings)

    lemmas = reduce(lambda x, y: x.union(y), (set(r) for r in rankings))
    return OrderedDict(sorted(
        [(l, len(rankings) * reduce(product, get(l)) / (1 + reduce(sum, get(l)))) for l in lemmas],
        key=lambda (_, v): v,
        reverse=True
    ))


@click.command()
@click.argument('pos_tagged', type=click.Path(exists=True, dir_okay=False))
@click.argument('document_key')
@click.argument('language')
@click.option('--pos-tag-key', default='pos_tag')
@click.option('--dump-verbs', type=click.File('w'), default='dev/verbs.json')
@click.option('--dump-tf-idf', type=click.File('w'), default='dev/tf_idf_ranking.json')
@click.option('--dump-stdev', type=click.File('w'), default='dev/stdev_ranking.json')
@click.option('--dump-popularity', type=click.File('w'), default='dev/popularity_ranking.json')
@click.option('--dump-final', type=click.File('w'), default='dev/verb_ranking.json')
@click.option('--processes', '-p', default=0)
def main(pos_tagged, document_key, pos_tag_key, language, dump_verbs, dump_tf_idf,
         dump_stdev, dump_popularity, dump_final, processes):
    """ Computes the three verb rankings: average TF-IDF, average of TF-IDF
        standard deviation and popularity.
    """

    logger.info('Computing lemma to token map and TF-IDF matrix')
    lemma_tokens, (vectorizer, tf_idf_matrix) = parallel.execute(
        2,
        produce_lemma_tokens, (pos_tagged, pos_tag_key, language),
        compute_tf_idf_matrix, (pos_tagged, document_key)
    )

    logger.info('scoring verbs by popularity')
    pop_ranking = PopularityRanking(pos_tagged, pos_tag_key).find_ranking(processes)

    logger.info('scoring verbs by TF-IDF based metrics (average and stdandard deviation)')
    tfidf_ranking, stdev_ranking = TFIDFRanking(vectorizer, lemma_tokens, tf_idf_matrix).find_ranking(processes)

    logger.info('producing final ranking')
    final_ranking = harmonic_ranking(pop_ranking, tfidf_ranking, stdev_ranking)

    logger.info('dumping all the rankings')
    json.dump(tfidf_ranking, dump_tf_idf, indent=2)
    json.dump(stdev_ranking, dump_stdev, indent=2)
    json.dump(pop_ranking, dump_popularity, indent=2)
    json.dump(lemma_tokens, dump_verbs, default=lambda x: list(x), indent=2)
    json.dump(final_ranking, dump_final, indent=2)
