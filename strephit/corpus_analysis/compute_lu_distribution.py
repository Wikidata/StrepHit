import click
import json
import logging
from nltk.parse.stanford import StanfordParser
from nltk.tree import Tree
from itertools import imap
from collections import defaultdict, OrderedDict
from strephit.commons.split_sentences import SentenceSplitter
from strephit.commons.io import load_corpus
from strephit.commons.pos_tag import TTPosTagger
from strephit.commons import parallel


logger = logging.getLogger(__name__)
# some globals for the workers (some of them cannot be pickled)
splitter = tagger = all_verbs = parser = None


def worker_with_sub_sentences(bio):
    def find_sub_sentences(tree):
        # sub-sentences are the lowest S nodes
        if not isinstance(tree, Tree):
            return []

        s = reduce(lambda x, y: x + y, map(find_sub_sentences, iter(tree)), [])
        if tree.label() == 'S':
            return s or [tree]
        else:
            return s

    def find_verbs(tree):
        if len(tree) == 1 and not isinstance(tree[0], Tree):
            if tree.label().startswith('V'):
                yield (tree.label(), tree[0])
        else:
            for child in tree:
                for each in find_verbs(child):
                    yield each

    counter = defaultdict(int)
    for root in parser.raw_parse_sents(splitter.split(bio)):
        root = root.next()
        if len(root.leaves()) < 5:
            continue

        sub_sents = find_sub_sentences(root)
        for sub in sub_sents:
            verbs = set(chunk for _, chunk in find_verbs(sub))
            counter[len(all_verbs.intersection(verbs))] += 1

    return counter


def worker_with_sentences(bio):
    counter = defaultdict(int)
    for sent in splitter.split(bio):
        sent = sent.strip().lower()
        if len(sent) < 5:
            continue

        tagged = tagger.tag_one(sent)
        if not tagged:
            continue

        verbs = set(chunk for chunk, pos, _ in tagged if pos.startswith('V'))
        counter[len(all_verbs.intersection(verbs))] += 1

    return counter


@click.command()
@click.argument('corpus', type=click.Path(exists=True))
@click.argument('verbs', type=click.File('r'))
@click.option('--sub-sentences/--simple-sentences', default=False)
@click.option('--processes', '-p', default=0)
@click.option('--output', '-o', default='dev/lus_per_sent.json', type=click.File('w'))
def main(corpus, verbs, processes, output, sub_sentences):
    """ Compute the LU distribution in the corpus, i.e. how many LUs per sentence
    """
    global splitter, tagger, parser, all_verbs
    splitter = SentenceSplitter('en')
    tagger = TTPosTagger('en')
    parser = StanfordParser(path_to_jar='dev/stanford-corenlp-3.6.0.jar',
                            path_to_models_jar='dev/stanford-corenlp-3.6.0-models.jar',
                            java_options=' -mx1G -Djava.ext.dirs=dev/')  # no way to make classpath work
    all_verbs = reduce(lambda x, y: x.union(y), imap(set, json.load(verbs).values()), set())
    all_verbs.discard('be')
    all_verbs.discard('have')

    args = load_corpus(corpus, 'bio', text_only=True)
    worker = worker_with_sub_sentences if sub_sentences else worker_with_sentences
    counter = defaultdict(int)

    for i, counts in enumerate(parallel.map(worker, args, processes)):
        for k, v in counts.iteritems():
            counter[k] += v

        if (i + 1) % 10000 == 0:
            logger.info('Processed %d documents', i + 1)

    counter = OrderedDict(sorted(counter.items(), key=lambda (k, v): k))
    for k, v in counter.iteritems():
        print k, v

    json.dump(counter, output, indent=2)
