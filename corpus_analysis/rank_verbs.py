#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
from collections import defaultdict, OrderedDict
from sys import exit
from commons.pos_tag import PosTagger
from commons.io_utils import load_corpus
from commons.logger import logger
from numpy import average, std
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


VERBAL_PREFIXES = {
    'en': 'V'
}


def extract_verbs(pos_tagged_corpus, language):
    """Extract verb lemmas and surface forms from a POS-tagged text."""
    verbs = defaultdict(set)
    for tagged_document in pos_tagged_corpus:
        logger.debug("POS-tagged document: %s" % tagged_document)
        for tag in tagged_document:
            if tag.pos.startswith(VERBAL_PREFIXES[language]):
                verbs[tag.lemma].add(tag.word)
    # sets are not JSON serializable, so cast them to lists
    return {lemma: list(tokens) for lemma, tokens in verbs.iteritems()}


def compute_tf_idf_matrix(corpus):
    """ Compute the TF/IDF matrix of the input corpus.
        :param corpus: an iterable of documents
        :return: the :class:`TfidfVectorizer` instance and the TF/IDF matrix
    """
    vectorizer = TfidfVectorizer()
    return vectorizer, vectorizer.fit_transform(corpus)


def get_similarity_scores(verb_token, vectorizer, tf_idf_matrix):
    """ Compute the cosine similarity score of a given verb token against the input corpus TF/IDF matrix.
        :param str verb_token: Surface form of a verb, e.g., *born*
        :return: cosine similarity score
        :rtype: float
    """
    verb_token_vector = vectorizer.transform([verb_token])
    # Here the linear kernel is the same as the cosine similarity, but faster
    # cf. http://scikit-learn.org/stable/modules/metrics.html#cosine-similarity
    scores = linear_kernel(verb_token_vector, tf_idf_matrix)
    logger.debug("Corpus-wide TF/IDF scores for '%s': %s" % (verb_token, scores))
    logger.info("Average TF/IDF score for '%s': %f" % (verb_token, average(scores)))
    return scores


def compute_ranking(verbs, vectorizer, tf_idf_matrix):
    """ Compute the final verb rankings.
        :param dict verbs: Dictionary of verbs with lemmas as keys and corpus tokens as values
        :return: 2 rankings, one with average TF/IDF and one with standard deviation scores
        :rtype: tuple
    """
    avg_ranking = stdev_ranking = {}
    for lemma, tokens in verbs.iteritems():
        logger.debug("Computing scores for lemma '%s' ..." % lemma)
        averages = []
        stdevs = []
        for token in tokens:
            token_scores = get_similarity_scores(token, vectorizer, tf_idf_matrix)
            averages += filter(None, token_scores.flatten().tolist())
            stdevs.append(token_scores.std())
        logger.debug("TF/IDF scores: %s" % averages)
        logger.debug("stdev scores: %s" % stdevs)
        tf_idf_final = average(averages)
        stdev_final = average(stdevs)
        avg_ranking[lemma] = tf_idf_final
        stdev_ranking[lemma] = stdev_final
        logger.debug("Average TF/IDF score: %f" % tf_idf_final)
        logger.debug("Average stdev score: %f" % stdev_final)
    return OrderedDict(sorted(avg_ranking.items(), key=lambda x: x[1], reverse=True)), OrderedDict(sorted(stdev_ranking.items(), key=lambda x: x[1], reverse=True))


@click.command()
@click.argument('corpus_path', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('document_key')
@click.argument('language_code')
@click.option('-t', '--tagger', type=click.Choice(['tt', 'nltk']), default='tt')
@click.option('-o', '--output-file', type=click.File('wb'), default='verbs.json')
@click.option('--tt-home', type=click.Path(exists=True, dir_okay=True, resolve_path=True), help="home directory for TreeTagger")
def main(corpus_path, document_key, language_code, tagger, output_file, tt_home):
    """ Perform part-of-speech (POS) tagging over an input corpus.
    """
    pos_tagger = PosTagger(language_code, tagger, tt_home)
    # Need to create the corpus generator twice,
    # as it will be consumed by 2 functions, i.e., compute_tf_idf_matrix and pos_tagger.tag_many
    corpus = load_corpus(corpus_path, document_key)
    corpus_for_tf_idf = load_corpus(corpus_path, document_key)
    logger.info("Computing TF/IDF matrix ...")
    vectorizer, tf_idf_matrix = compute_tf_idf_matrix(corpus_for_tf_idf)
    logger.info("Starting part-of-speech (POS) tagging ...")
    tagged_corpus = [tagged_document for tagged_document in pos_tagger.tag_many(corpus)]
    corpus_verbs = extract_verbs(tagged_corpus, language_code)
    logger.debug("Corpus verbs: %s" % corpus_verbs)
    json.dump(corpus_verbs, output_file, indent=2)
    avg_ranking, stdev_ranking = compute_ranking(corpus_verbs, vectorizer, tf_idf_matrix)
    logger.info("Ranking based on average TF/IDF scores: %s" % json.dumps(avg_ranking, indent=2))
    logger.info("Ranking based on average standard deviation scores: %s" % json.dumps(stdev_ranking, indent=2))
    return 0


if __name__ == '__main__':
    exit(main())
