#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
from random import choice
from nltk.parse.stanford import StanfordParser
from nltk.tree import Tree
from strephit.commons.io import load_dumped_corpus
from strephit.commons.tokenize import Tokenizer
from strephit.commons.split_sentences import SentenceSplitter
from strephit.commons.pos_tag import TTPosTagger
from strephit.commons import parallel
from sys import exit


logger = logging.getLogger(__name__)


class SentenceExtractor:
    """ Base class for sentence extractors.
    """

    def __init__(self, corpus, document_key, sentences_key, language, lemma_to_token):
        """ Initializes the extractor.
            :param corpus: The corpus, iterable of `dict`s. Generator preferred
            :param document_key: The key from which to retrieve the text from each item
            :param sentences_key: The key to which the extracted sentences should be stored
            :param language: The language the text is in
            :param lemma_to_token: Mapping from lemma to list of tokens
        """
        self.corpus = corpus
        self.document_key = document_key
        self.sentences_key = sentences_key
        self.lemma_to_token = lemma_to_token
        self.language = language

    def extract_from_item(self, item):
        """ Extract sentences from an item. Relies on `setup_extractor`
            having been called
            :param dict item: Item from which to extract sentences
            :return: The original item and list of extracted sentences
            :rtype: tuple of dict, list
        """
        raise NotImplementedError()

    def setup_extractor(self):
        """ Optional setup code, run before starting the extraction
        """
        pass

    def teardown_extractor(self):
        """ Optional teardown code, run after the extraction
        """
        pass

    def extract(self, processes=0):
        """ Processes the corpus extracting sentences from each item
            and storing them in the item itself.
        """
        self.setup_extractor()

        try:
            count = 0
            for i, (item, extracted) in enumerate(parallel.map(self.extract_from_item,
                                                               self.corpus, processes)):

                # assign an unique incremental ID to each sentence
                for each in extracted:
                    each['id'] = count
                    count += 1

                item[self.sentences_key] = extracted
                yield item

                if (i + 1) % 10000 == 0:
                    logger.info('Processed %d items, extracted %d sentences',
                                i + 1, count)

            logger.info('Total sentences extracted: %d', count)
        finally:
            self.teardown_extractor()


class OneToOneExtractor(SentenceExtractor):
    """ 121 extraction strategy: 1 sentence per 1 LU
        N.B.: the same sentence will appear only once
        the sentence is assigned to a RANDOM LU
    """
    splitter = None
    tokenizer = None
    all_verb_tokens = None
    token_to_lemma = None
    tagger = None

    def setup_extractor(self):
        self.splitter = SentenceSplitter(self.language)
        self.tokenizer = Tokenizer(self.language)
        self.tagger = TTPosTagger(self.language)

        self.all_verb_tokens = set()
        self.token_to_lemma = {}
        for lemma, match_tokens in self.lemma_to_token.iteritems():
            for match_token in match_tokens:
                self.all_verb_tokens.add(match_token.lower())
                self.token_to_lemma[match_token.lower()] = lemma
        logger.debug("All match tokens: %s" % self.all_verb_tokens)

    def extract_from_item(self, item):
        extracted = []

        document = item.get(self.document_key)
        if not document:
            return

        sentences = self.splitter.split(document)
        for sentence in sentences:
            tokens = [token.lower() for token in self.tokenizer.tokenize(sentence)]
            if not tokens:
                continue

            tagged = self.tagger.tag_one(tokens, tagonly=True)
            sentence_verbs = [token for token, pos, lemma in tagged if pos.startswith('V')]

            matched = []
            for token in self.all_verb_tokens:
                if token in sentence_verbs:
                    matched.append(token)

            if matched:
                assigned_token = choice(matched)
                assigned_lu = self.token_to_lemma[assigned_token]
                extracted.append({
                    'lu': assigned_lu,
                    'text': sentence,
                    'tagged': tagged,
                })

        if extracted:
            logger.debug("%d sentences extracted. Removing the full text from the item ...", len(extracted))
            item.pop(self.document_key)  # Remove text key
            return item, extracted
        else:
            logger.debug("No sentences extracted. Skipping the whole item ...")


class ManyToManyExtractor(SentenceExtractor):
    """ n2n extraction strategy: many sentences per many LUs
        N.B.: the same sentence is likely to appear multiple times
    """
    splitter = None
    tokenizer = None
    tagger = None

    def setup_extractor(self):
        self.splitter = SentenceSplitter(self.language)
        self.tokenizer = Tokenizer(self.language)
        self.tagger = TTPosTagger(self.language)

    def extract_from_item(self, item):
        extracted = []

        document = item.get(self.document_key)
        if not document:
            return

        sentences = self.splitter.split(document)
        for sentence in sentences:
            tagged = self.tagger.tag_one([token.lower() for token in self.tokenizer.tokenize(sentence)],
                                         tagonly=True)
            sentence_tokens = [token for token, pos, lemma in tagged if pos.startswith('V')]

            for lemma, match_tokens in self.lemma_to_token.iteritems():
                for match in match_tokens:
                    if match.lower() in sentence_tokens:
                        extracted.append({
                            'lu': lemma,
                            'text': sentence,
                            'tagged': tagged,
                        })

        if extracted:
            logger.debug("%d sentences extracted. Removing the full text from the item ...", len(extracted))
            item.pop(self.document_key)
            return item, extracted
        else:
            logger.debug("No sentences extracted. Skipping the whole item ...")


class SyntacticExtractor(SentenceExtractor):
    """ Tries to split sentences into sub-sentences so that each of them
        contains only one LU
    """

    splitter = None
    parser = None
    token_to_lemma = None
    all_verbs = None

    def setup_extractor(self):
        self.splitter = SentenceSplitter(self.language)
        self.parser = StanfordParser(path_to_jar='dev/stanford-corenlp-3.6.0.jar',
                                     path_to_models_jar='dev/stanford-corenlp-3.6.0-models.jar',
                                     java_options=' -mx2G -Djava.ext.dirs=dev/')

        self.token_to_lemma = {}
        for lemma, tokens in self.lemma_to_token.iteritems():
            for t in tokens:
                self.token_to_lemma[t] = lemma
        self.all_verbs = set(self.token_to_lemma.keys())

    def extract_from_item(self, item):
        extracted = []
        bio = item.get(self.document_key, '').lower()
        if not bio:
            return

        try:
            roots = self.parser.raw_parse_sents(self.splitter.split(bio))
        except (OSError, UnicodeDecodeError):
            logger.exception('cannot parse biography, skipping')
            return

        for root in roots:
            root = root.next()
            try:
                sub_sents = self.find_sub_sentences(root)
            except:
                logger.exception('cannot find sub-sentences')
                continue

            for sub in sub_sents:
                try:
                    text = ' '.join(chunk for _, chunk in self.find_terminals(sub))
                    logger.debug('processing text ' + text)
                    verbs = set(chunk for _, chunk in self.find_terminals(sub, 'V'))
                except:
                    logger.exception('cannot extract verbs or parse sentence')
                    continue

                found = verbs.intersection(self.all_verbs)

                if len(found) == 0:
                    logger.debug('No matching verbs found in sub sentence')
                elif len(found) == 1:
                    extracted.append({
                        'lu': self.token_to_lemma[found.pop()],
                        'text': text,
                    })
                else:
                    logger.debug('More than one matching verbs found in sentence %s: %s',
                                 text, repr(found))

        if extracted:
            logger.debug("%d sentences extracted. Removing the full text from the item ...",
                         len(extracted))
            item.pop(self.document_key)
            return item, extracted
        else:
            logger.debug("No sentences extracted. Skipping the whole item ...")

    def find_sub_sentences(self, tree):
        # sub-sentences are the lowest S nodes in the parse tree
        if not isinstance(tree, Tree):
            return []

        s = reduce(lambda x, y: x + y, map(self.find_sub_sentences, iter(tree)), [])
        if tree.label() == 'S':
            return s or [tree]
        else:
            return s

    def find_terminals(self, tree, label=None):
        # finds all terminals in the tree with the given label prefix
        if len(tree) == 1 and not isinstance(tree[0], Tree):
            if label is None or tree.label().startswith(label):
                yield (tree.label(), tree[0])
        else:
            for child in tree:
                for each in self.find_terminals(child, label):
                    yield each


def extract_sentences(corpus, document_key, sentences_key, language, matches, strategy, processes=0):
    """
    Extract sentences from the given corpus by matching tokens against a given set.
    :param corpus: Iterable of documents containing text and metadata
    :param str document_key: dict key to get the text documents
    :param str sentences_key: dict key where to put extracted sentences
    :param str language: ISO 639-1 language code used for tokenization and sentence splitting
    :param dict matches: Dict with corpus lemmas as keys and tokens to be matched as values
    :param str strategy: One of the 3 extraction strategies ['121', 'n2n', 'syntactic']
    :param int processes: How many concurrent processes to use
    :return: the corpus, updated with the extracted sentences and the number of extracted sentences
    :rtype: generator of tuples
    """

    if strategy == 'n2n':
        logger.info("Will extract sentences using the 'many to many' strategy: the same "
                    "sentence is likely to appear multiple times, with different LUs.")
        extractor = ManyToManyExtractor
    elif strategy == '121':
        logger.info("Will extract sentences using the 'one to one' strategy: the same "
                    "sentence will appear only once.")
        extractor = OneToOneExtractor
    elif strategy == 'syntactic':
        logger.info("Will extract sentences using the 'syntactic' strategy: the same "
                    "sentence will appear only once.")
        extractor = SyntacticExtractor
    else:
        raise ValueError("Malformed or unsupported extraction strategy: "
                         "please use one of ['121', 'n2n', or 'syntactic']")

    for each in extractor(corpus, document_key, sentences_key, language, matches).extract(processes):
        yield each


@click.command()
@click.argument('corpus', type=click.File('r'))
@click.argument('document_key')
@click.argument('language_code')
@click.argument('matches', type=click.File('r'))
@click.option('--strategy', '-s', type=click.Choice(['n2n', '121', 'syntactic']), default='n2n')
@click.option('--output', '-o', type=click.File('w'), default='dev/sentences.jsonlines')
@click.option('--sentences-key', default='sentences')
@click.option('--processes', '-p', default=0)
def main(corpus, document_key, language_code, matches, strategy, output, processes, sentences_key):
    """ Extract corpus sentences containing at least one token in the given set. """
    logger.info("Loading corpus dump from '%s' ..." % corpus.name)
    loaded = load_dumped_corpus(corpus, document_key)
    logger.info("Starting sentence extraction. Matches will be loaded from '%s'" % matches.name)
    updated = extract_sentences(loaded, document_key, sentences_key, language_code,
                                json.load(matches), strategy, processes)
    for item in updated:
        output.write(json.dumps(item) + '\n')
    return 0


if __name__ == '__main__':
    exit(main())

