#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
from collections import defaultdict, OrderedDict
from sys import exit
from nltk.corpus import framenet


logger = logging.getLogger(__name__)


def get_top_n_lus(ranked_lus, n):
    """
    Extract the top N Lexical Units (LUs) from a ranking.
    :param dict ranked_lus: LUs ranking, as returned by :func:`compute_ranking`
    :param int n: Number of top LUs to return
    :return: the top N LUs
    :rtype: list
    """
    return ranked_lus.keys()[:n]


def intersect_lemmas_with_framenet(corpus_lemmas):
    """
    Intersect verb lemmas extracted from the input corpus with FrameNet Lexical Units (LUs).
    :param list corpus_lemmas: List of verb lemmas
    :return: a dictionary of corpus lemmas enriched with FrameNet LUs data (dicts)
    :rtype: dict
    """
    # Each FrameNet LU triggers one frame, so assign them to the same corpus lemma
    enriched = defaultdict(list)
    for corpus_lemma in corpus_lemmas:
        # Look up the FrameNet LUs given the corpus lemma
        # Ensure exact match, as the lookup can be done only via regex
        lus = framenet.lus(r'^%s\.' % corpus_lemma)
        if lus:
            logger.debug("Found %d FrameNet Lexical Units (LUs) that match the corpus lemma '%s': %s" % (len(lus), corpus_lemma, lus))
            for lu in lus:
                lu_label = lu['name']
                logger.debug("Processing FrameNet LU '%s' ..." % lu_label)
                frame = lu['frame']
                frame_label = frame['name']
                core_fes = []
                extra_fes = []
                logger.debug("Processing Frame Elements (FEs) ...")
                fes = frame['FE']
                for fe_label, fe_data in fes.iteritems():
                    fe_type = fe_data['coreType']
                    semantic_type_object = fe_data['semType']
                    semantic_type = semantic_type_object['name'] if semantic_type_object else None
                    to_be_added = {
                        'fe': fe_label,
                        'type': fe_type,
                        'semantic_type': semantic_type
                    }
                    if fe_type == 'Core':
                        core_fes.append(to_be_added)
                    else:
                        extra_fes.append(to_be_added)
                logger.debug("Core FEs: %s" % core_fes)
                logger.debug("Extra FEs: %s" % extra_fes)
                intersected_lu = {
                    'lu': lu_label,
                    'frame': frame_label,
                    'pos': lu['POS'],
                    'core_fes': core_fes,
                    'extra_fes': extra_fes
                }
                enriched[corpus_lemma].append(intersected_lu)
                logger.debug("Corpus lemma '%s' enriched with frame data: %s" % (corpus_lemma, json.dumps(intersected_lu, indent=2)))
    return enriched


def extract_top_corpus_tokens(enriched_lemmas, all_lemma_tokens):
    """
    Extract the subset of corpus lemmas with tokens gievn the set of top lemmas
    :param list enriched_lemmas: Dist returned by :func:`intersect_lemmas_with_framenet`
    :param dict all_lemma_tokens: Dict of all corpus lemmas with tokens
    :return: the top lemmas with tokens dict
    :rtype: dict
    """
    top_lemmas_tokens = {}
    for top in enriched_lemmas:
        tokens = all_lemma_tokens.get(top)
        if tokens:
            top_lemmas_tokens[top] = tokens
    return top_lemmas_tokens


@click.command()
@click.argument('ranking', type=click.File())
@click.argument('all_lemmas', type=click.File())
@click.option('--top-n', '-n', default=50)
@click.option('--dump-enriched', '-e', type=click.File('w'),
              default='dev/framenet_lus.json')
@click.option('--dump-top-lemmas', '-t', type=click.File('w'),
              default='dev/top_lemma_tokens.json')
def main(ranking, all_lemmas, top_n, dump_enriched, dump_top_lemmas):
    """
    Extract FrameNet data given a ranking of corpus Lexical Units (lemmas)
    """
    logger.info("Loading ranked corpus Lexical Units (LUs) from '%s' ..." % ranking.name)
    # Remember to preserve the order
    lus = json.load(ranking, object_pairs_hook=OrderedDict)
    logger.info("Loaded %d LUs" % len(lus))
    logger.info("Will consider the top %d LUs" % top_n)
    top = get_top_n_lus(lus, top_n)
    logger.debug("Top LUs: %s" % top)
    enriched = intersect_lemmas_with_framenet(top)
    logger.info("Managed to enrich %d LUs with FrameNet data" % len(enriched))
    logger.info("Dumping top enriched LUs to '%s' ..." % dump_enriched.name)
    json.dump(enriched, dump_enriched, indent=2)
    top = extract_top_corpus_tokens(enriched, json.load(all_lemmas))
    logger.info("Dumping top lemmas with tokens to '%s' ..." % dump_top_lemmas.name)
    json.dump(top, dump_top_lemmas, indent=2)
    return 0


if __name__ == '__main__':
    exit(main())
