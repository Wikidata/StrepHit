#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging

import click
from collections import defaultdict
import csv
import re
import random
import json

logger = logging.getLogger(__name__)


def process_unit(unit_id, sentences):
    assert all(s['_unit_id'] == unit_id for s in sentences)
    assert len(set(s['id'] for s in sentences)) == 1
    assert len(set(s['sentence'] for s in sentences)) == 1
    assert len(set(s['frame'] for s in sentences)) == 1

    chunk_count = 1 + max(int(k.split('_')[1]) for k in sentences[0].keys() if re.match(r'chunk_\d+', k))
    fe_count = 1 + max(int(k.split('_')[1]) for k in sentences[0].keys() if re.match(r'fe_\d+', k))

    # build a mapping chunk --> all assigned FEs
    chunks = defaultdict(list)
    for each in sentences:
        for i in xrange(chunk_count):
            fe = each['answer_chunk_%02d' % i]
            chunk = each['chunk_%02d' % i]
            if fe and chunk and fe != 'None':
                chunks[chunk].append(fe)

    # build a mapping FE --> chunk determined with majority voting
    fes = {}
    for chunk, judgments in chunks.iteritems():
        counts = defaultdict(lambda: 0)
        for each in judgments:
            counts[each] += 1

        most = max(counts.values())
        fe = random.choice([c for c, j in counts.iteritems() if j == most])
        fes[fe] = chunk

    # fill in missing FEs
    for i in xrange(fe_count):
        fe = sentences[0]['fe_%02d' % i]
        if fe and fe not in fes:
            fes[fe] = None

    is_gold = sentences[0]['_golden'].lower() in {'t', 'true', 'y', 'yes'}
    gold_fes = {}
    if is_gold:
        for i in xrange(fe_count):
            fe = sentences[0]['chunk_%02d' % i]
            gold = sentences[0]['answer_chunk_%02d_gold' % i]
            if fe and gold:
                gold_fes[fe] = [
                    g if g.lower() != 'none' else None
                    for g in gold.split('\n')
                ]

    unit = {
        'id': sentences[0]['id'],
        'sentence': sentences[0]['sentence'],
        'frame': sentences[0]['frame'],
        'lu': sentences[0]['lu'],
        'fes': fes,
        'gold_fes': dict(gold_fes),
    }

    return unit

@click.command()
@click.argument('results', type=click.File('r'))
@click.option('--outfile', '-o', type=click.Path(dir_okay=False), default='output/training_set.jsonlines')
@click.option('--split-lus', is_flag=True)
def main(results, outfile, split_lus):
    """ Parses the CSV with the results from crowdflower
    """

    logger.info("Parsing annotation results from '%s' ..." % results.name)
    sentences = defaultdict(lambda: list())
    reader = csv.DictReader(results)
    for each in reader:
        sentences[each['_unit_id']].append(each)

    files = {}

    def get_file(lu):
        fname = outfile % lu if split_lus else outfile
        if fname not in files:
            files[fname] = open(fname, 'w')
        return files[fname]

    try:
        for k, v in sentences.iteritems():
            processed = process_unit(k, v)
            f = get_file(processed['lu'])
            f.write(json.dumps(processed))
            f.write('\n')
    finally:
        for f in files.values():
            f.close()
        logger.info("Done, training data dumped to %s",
                    ', '.join(files.keys()))
