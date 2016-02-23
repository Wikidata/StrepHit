#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
from collections import defaultdict, OrderedDict
from sys import exit
from strephit.commons.pos_tag import TTPosTagger
from strephit.commons.io import load_corpus
from numpy import average
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


logger = logging.getLogger(__name__)

VERBAL_PREFIXES = {
    'en': 'V'
}


def extract_verbs(tagged_item, document_key, language, corpus_verbs):
    """ Extract verb lemmas and surface forms from the POS-tagged document of the given item and update the given corpus verbs
        :param dict tagged_item: document represented as a list of tagged tokens
        :param str document_key: `tagged_item` dict key containing the text document
        :param str language: language code used to extract suitable tags
        :param dict corpus_verbs: the corpus verbs dict to update. Must be a `defaultdict(set)`
        :return: the updated corpus verbs
        :rtype: dict
    """
    for tag in tagged_item[document_key]:
        if tag.pos.startswith(VERBAL_PREFIXES[language]):
            corpus_verbs[tag.lemma].add(tag.word)
    return corpus_verbs


def compute_tf_idf_matrix(corpus):
    """ Compute the TF/IDF matrix of the input corpus.
        :param corpus: an iterable of documents
        :return: the :class:`TfidfVectorizer` instance and the TF/IDF matrix
        :rtype: tuple
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
        :param dict verbs: Dictionary of verbs with lemmas as keys and tokens appearing in the corpus as values
        :param :class:`TfidfVectorizer` vectorizer: :class:`TfidfVectorizer` instance, as returned by :func:`compute_tf_idf_matrix`
        :param numpy.ndarray tf_idf_matrix: TF/IDF matrix, as returned by :func:`compute_tf_idf_matrix`
        :return: 2 rankings (ordered dicts), one with average TF/IDF scores and one with average standard deviation scores
        :rtype: tuple
    """
    avg_ranking = {}
    stdev_ranking = {}
    for lemma, tokens in verbs.iteritems():
        logger.debug("Computing scores for lemma '%s' ..." % lemma)
        # Lemma-based scores lists to be filled with token-based scores
        tf_idfs = []
        st_devs = []
        # Token-based scores are computed against the whole corpus
        for token in tokens:
            # TF/IDF
            scores = get_similarity_scores(token, vectorizer, tf_idf_matrix)
            # Keep TF/IDF scores > 0 and fill the lemma-based score list
            tf_idfs += filter(None, scores.flatten().tolist())
            # Compute stdev over the token-based TF/IDF scores and fill the other lemma-based score list
            st_devs.append(scores.std())
        logger.debug("TF/IDF scores: %s" % tf_idfs)
        logger.debug("stdev scores: %s" % st_devs)
        # Lemma-based final scores are averages of the score lists
        tf_idf_final = average(tf_idfs)
        stdev_final = average(st_devs)
        avg_ranking[lemma] = tf_idf_final
        stdev_ranking[lemma] = stdev_final
        logger.debug("Average TF/IDF score: %f" % tf_idf_final)
        logger.debug("Average stdev score: %f" % stdev_final)
    return OrderedDict(sorted(avg_ranking.items(), key=lambda x: x[1], reverse=True)), OrderedDict(sorted(stdev_ranking.items(), key=lambda x: x[1], reverse=True))


@click.command()
@click.argument('corpus_path', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.argument('document_key')
@click.argument('language_code')
@click.option('--pos-tagged', '-p', type=click.File(), help="Cached POS-tagged JSON file, to avoid POS-tagging again")
@click.option('--dump-pos-tagged', type=click.File('w'), default='pos_tagged.json')
@click.option('--dump-verbs', type=click.File('w'), default='verbs.json')
@click.option('--dump-tf-idf', type=click.File('w'), default='tf_idf_ranking.json')
@click.option('--dump-stdev', type=click.File('w'), default='stdev_ranking.json')
@click.option('--tt-home', type=click.Path(exists=True, dir_okay=True, resolve_path=True), help="home directory for TreeTagger")
def main(corpus_path, document_key, language_code, pos_tagged, dump_pos_tagged, dump_verbs, dump_tf_idf, dump_stdev, tt_home):
    """ Compute verb rankings of the input corpus.
    """
    pos_tagger = TTPosTagger(language_code, tt_home)
    corpus_for_tf_idf = load_corpus(corpus_path, document_key, text_only=True)
    logger.info("Computing TF/IDF matrix ...")
    vectorizer, tf_idf_matrix = compute_tf_idf_matrix(corpus_for_tf_idf)
    corpus_verbs = defaultdict(set)
    # Use the cached POS-tagged file if it exists
    if pos_tagged:
        logger.info("Loading cached POS-tagged file '%s' ..." % verbs.name)
        tagged_corpus = json.load(pos_tagged)
        for tagged_item in tagged_corpus:
            logger.debug("Extracting verbs from POS-tagged document: %s" % tagged_item[document_key])
            corpus_verbs = extract_verbs(tagged_item, document_key, language_code, corpus_verbs)
    else:
        logger.info("The POS-tagged corpus will be dumped to '%s'" % dump_pos_tagged.name)
        corpus = load_corpus(corpus_path, document_key)
        logger.info("Starting part-of-speech (POS) tagging ...")
        for tagged in pos_tagger.tag_many(corpus, document_key):
            dump_pos_tagged.write(json.dumps(tagged, indent=2))
            corpus_verbs = extract_verbs(tagged, document_key, language_code, corpus_verbs)
    # sets are not JSON serializable, so cast them to lists
    dumpable_corpus_verbs = {lemma: list(tokens) for lemma, tokens in corpus_verbs.iteritems()}
    logger.debug("Corpus verbs: %s" % corpus_verbs)
    logger.info("Dumping extracted verbs to '%s' ..." % dump_verbs.name)
    json.dump(dumpable_corpus_verbs, dump_verbs, indent=2)
    logger.info("Computing verb rankings ...")
    tf_idf_ranking, stdev_ranking = compute_ranking(corpus_verbs, vectorizer, tf_idf_matrix)
    logger.debug("Ranking based on average TF/IDF scores: %s" % json.dumps(tf_idf_ranking, indent=2))
    logger.debug("Ranking based on average standard deviation scores: %s" % json.dumps(stdev_ranking, indent=2))
    logger.info("Dumping rankings to '%s' (TF/IDF) and '%s' (stdev) ..." %(dump_tf_idf.name, dump_stdev.name))
    json.dump(tf_idf_ranking, dump_tf_idf, indent=2)
    json.dump(stdev_ranking, dump_stdev, indent=2)
    return 0


if __name__ == '__main__':
    exit(main())
