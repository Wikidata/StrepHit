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


def intersect_verbs_with_framenet(corpus_verb_lemmas):
    """
    Intersect verb lemmas extracted from the input corpus with FrameNet Lexical Units (LUs).
    :param list corpus_verb_lemmas: List of verb lemmas
    :return: a list of corpus lemmas enriched with FrameNet LUs data (dicts)
    :rtype: list
    """
    enriched = []
    for corpus_lemma in corpus_verb_lemmas:
        # Look up the FrameNet LUs given the corpus lemma
        # Ensure exact match, as the lookup can be done only via regex
        lus = framenet.lus(r'^%s\.' % corpus_lemma)
        if lus:
            logger.debug("Found %d FrameNet Lexical Units (LUs) that match the corpus lemma '%s': %s" % (len(lus), corpus_lemma, lus))
            # Each LU triggers one frame, so assign them to the same corpus lemma
            enriched_lemma = defaultdict(list)
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
                enriched_lemma[corpus_lemma].append(intersected_lu)
            logger.debug("Corpus lemma enriched with frame data: %s" % json.dumps(enriched_lemma, indent=2))
            enriched.append(enriched_lemma)
    return enriched


@click.command()
@click.argument('corpus_lus', type=click.File('rb'))
@click.option('--top-n', '-n', default=50)
@click.option('--output-file', '-o', type=click.File('w'), default='framenet_lus.json')
def main(corpus_lus, top_n, output_file):
    """
    Extract FrameNet data given a ranking of corpus Lexical Units (lemmas)
    """
    logger.info("Loading ranked corpus Lexical Units (LUs) from '%s' ..." % corpus_lus.name)
    # Remember to preserve the order
    lus = json.load(corpus_lus, object_pairs_hook=OrderedDict)
    logger.info("Loaded %d LUs" % len(lus))
    logger.info("Will consider the top %d LUs" % top_n)
    top = get_top_n_lus(lus, top_n)
    logger.debug("Top LUs: %s" % top)
    enriched = intersect_verbs_with_framenet(top)
    logger.info("Managed to enrich %d LUs with FrameNet data" % len(enriched))
    logger.debug("Enriched LUs: %s" % enriched)
    logger.info("Dumping enriched LUs to '%s' ..." % output_file.name)
    json.dump(enriched, output_file, indent=2)
    return 0


if __name__ == '__main__':
    exit(main())
