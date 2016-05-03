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
    chunks = defaultdict(lambda: list())
    for each in sentences:
        for i in xrange(chunk_count):
            fe = each['chunk_%02d' % i]
            chunk = each['orig_chunk_%02d' % i]
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
        if not fe:
            import pdb; pdb.set_trace()
        fes[fe] = chunk

    # fill in missing FEs
    for i in xrange(fe_count):
        fe = sentences[0]['fe_%02d' % i]
        if fe and fe not in fes:
            fes[fe] = None

    unit = {
        'id': sentences[0]['id'],
        'sentence': sentences[0]['sentence'],
        'frame': sentences[0]['frame'],
        'fes': fes,
    }

    return unit

@click.command()
@click.argument('results', type=click.File('r'))
@click.argument('output', type=click.File('w'))
def main(results, output):
    """ Parses the CSV with the results from crowdflower
    """

    sentences = defaultdict(lambda: list())
    reader = csv.DictReader(results)
    for each in reader:
        sentences[each['_unit_id']].append(each)

    for k, v in sentences.iteritems():
        processed = process_unit(k, v)
        output.write(json.dumps(processed))
        output.write('\n')
