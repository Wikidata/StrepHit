#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
from sys import exit
from strephit.commons.wikidata import get_property_ids, get_entities, get_labels_and_aliases

logger = logging.getLogger(__name__)


def compute_exact_matches(corpus_frames, wikidata_properties):
    """
     Compute the subset of the given dict of corpus Frame Elements
     that exactly match Wikidata properties.
     :param dict corpus_frames: dict returned by :func:`extract_framenet_frames`
     :param dict wikidata_properties: dict with all Wikidata properties
     :return: `corpus_frames` subset with mappings to Wikidata properties
    """
    exact_matches = defaultdict(list)
    for lemma, frames in corpus_frames.iteritems():
        for frame in frames:
            for pid, p_label_and_aliases in wikidata_properties.iteritems():
                # Lowercase for better matching
                p_label = p_label_and_aliases['label'].lower()
                p_aliases = p_label_and_aliases.get('aliases')
                for core_fe in frame['core_fes']:
                    # Lowercase for better matching
                    fe = core_fe['fe'].lower()
                    if fe == p_label:
                        logger.debug("Core FE '%s' maps to '%s' label '%s'" % (fe, pid, p_label))
                        exact_matches[lemma].append(frame)
                        exact_matches[lemma]
                        core_fe['mapping'].append({pid: p_label_and_aliases})
                    elif p_aliases and fe in p_aliases:
                        logger.debug("Core FE '%s' maps to one of '%s' aliases: %s" % (fe, pid, p_aliases))
                        core_fe['mapping'].append({pid: p_label_and_aliases})
                for extra_fe in frame['extra_fes']:
                    # Lowercase for better matching
                    fe = extra_fe['fe'].lower()
                    if fe == p_label:
                        logger.debug("Extra FE '%s' maps to '%s' label '%s'" % (fe, pid, p_label))
                        extra_fe['mapping'].append({pid: p_label_and_aliases})
                    elif p_aliases and fe in p_aliases:
                        logger.debug("Extra FE '%s' maps to one of '%s' aliases: %s" % (fe, pid, p_aliases))
                        extra_fe['mapping'].append({pid: p_label_and_aliases})
    return exact_matches


@click.command()
@click.argument('corpus_frames', type=click.File())
@click.argument('language_code')
@click.option('--pid-batch', default=500)
@click.option('--prop-batch', default=50)
@click.option('--outfile', '-o', type=click.File('w'), default='output/exact_matches.json')
def main(corpus_frames, language_code, pid_batch, prop_batch, outfile):
    """ Map FEs to Wikidata properties via exact matches """
    all_pids = get_property_ids(pid_batch)
    all_properties = get_entities(all_pids, prop_batch)
    clean_properties = get_labels_and_aliases(all_properties, language_code)
    logger.debug(json.dumps(clean_properties, indent=2))
    logger.info("Computing exact matches mapping ...")
    exact_matches = compute_exact_matches(json.load(corpus_frames), clean_properties)
    logger.info("Total matches: %d Will dump to '%s' ..." %(len(exact_matches), outfile.name))
    json.dump(exact_matches, outfile, indent=2)
    return 0


if __name__ == '__main__':
    exit(main())
