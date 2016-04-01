#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
from collections import defaultdict, OrderedDict
from sys import exit
from nltk.corpus import framenet
from strephit.commons.wikidata import get_property_ids, get_entities, get_labels_and_aliases


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


def intersect_lemmas_with_framenet(corpus_lemmas, wikidata_properties):
    """
     Intersect verb lemmas extracted from the input corpus with FrameNet Lexical Units (LUs).
     :param list corpus_lemmas: List of verb lemmas
     :param dict wikidata_properties: dict with all Wikidata properties
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
                # Skip non-verbal LUs
                if lu['POS'] != 'V':
                    logger.debug("Skipping non-verbal LU '%s' ..." % lu_label)
                    continue
                logger.debug("Processing FrameNet LU '%s' ..." % lu_label)
                frame = lu['frame']
                frame_label = frame['name']
                core_fes = []
                extra_fes = []
                logger.debug("Processing Frame Elements (FEs) ...")
                fes = frame['FE']
                for fe_label, fe_data in fes.iteritems():
                    mapping = defaultdict(list)
                    # Compute exact matches between FEs and Wikidata properties labels and aliases
                    for pid, p_label_and_aliases in wikidata_properties.iteritems():
                        # Lowercase for better matching
                        p_label = p_label_and_aliases['label'].lower()
                        p_aliases = [p_alias.lower() for p_alias in p_label_and_aliases.get('aliases', [])]
                        fe = fe_label.lower()
                        if fe == p_label:
                            logger.debug("FE '%s' maps to '%s' label '%s'" % (fe_label, pid, p_label))
                            mapping[pid].append(p_label_and_aliases)
                        elif p_aliases and fe in p_aliases:
                            logger.debug("FE '%s' maps to one of '%s' aliases: %s" % (fe_label, pid, p_aliases))
                            mapping[pid].append(p_label_and_aliases)
                    fe_type = fe_data['coreType']
                    semantic_type_object = fe_data['semType']
                    semantic_type = semantic_type_object['name'] if semantic_type_object else None
                    # Skip FEs with no mapping to Wikidata
                    if not mapping:
                        logger.debug("FE '%s' has no mapping to Wikidata. Skipping ..." % fe_label)
                        continue
                    to_be_added = {
                        'fe': fe_label,
                        'type': fe_type,
                        'semantic_type': semantic_type,
                        'mapping': mapping
                    }
                    if fe_type == 'Core':
                        core_fes.append(to_be_added)
                    else:
                        extra_fes.append(to_be_added)
                # Skip frames with no mapping to Wikidata
                if not core_fes and not extra_fes:
                    logger.debug("No '%s' FEs could be mapped to Wikidata. Skipping ..." % frame_label)
                    continue
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
@click.argument('language_code')
@click.option('--top-n', '-n', default=150)
@click.option('--dump-enriched', '-e', type=click.File('w'),
              default='dev/framenet_lus.json')
@click.option('--dump-top-lemmas', '-t', type=click.File('w'),
              default='dev/top_lemma_tokens.json')
@click.option('--pid-batch', default=500)
@click.option('--prop-batch', default=50)
def main(ranking, all_lemmas, language_code, top_n, dump_enriched, dump_top_lemmas, pid_batch, prop_batch):
    """
     Extract FrameNet data given a ranking of corpus Lexical Units (lemmas).
     Return frames only if FEs map to Wikidata properties via exact matching of labels and aliases.
    """
    logger.info("Loading ranked corpus Lexical Units (LUs) from '%s' ..." % ranking.name)
    # Remember to preserve the order
    lus = json.load(ranking, object_pairs_hook=OrderedDict)
    logger.info("Loaded %d LUs" % len(lus))
    logger.info("Will consider the top %d LUs" % top_n)
    top = get_top_n_lus(lus, top_n)
    logger.debug("Top LUs: %s" % top)
    logger.info("Retrieving the full list of Wikidata properties ...")
    all_pids = get_property_ids(pid_batch)
    all_properties = get_entities(all_pids, prop_batch)
    logger.info("Extracting label and aliases only ...")
    clean_properties = get_labels_and_aliases(all_properties, language_code)
    enriched = intersect_lemmas_with_framenet(top, clean_properties)
    logger.info("Managed to enrich %d LUs with FrameNet data" % len(enriched))
    logger.info("Dumping top enriched LUs to '%s' ..." % dump_enriched.name)
    json.dump(enriched, dump_enriched, indent=2)
    top = extract_top_corpus_tokens(enriched, json.load(all_lemmas))
    logger.info("Dumping top lemmas with tokens to '%s' ..." % dump_top_lemmas.name)
    json.dump(top, dump_top_lemmas, indent=2)
    return 0


if __name__ == '__main__':
    exit(main())
