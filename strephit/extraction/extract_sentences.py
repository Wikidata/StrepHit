#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
from random import choice
from strephit.commons.io import load_dumped_corpus
from strephit.commons.tokenize import Tokenizer
from strephit.commons.split_sentences import SentenceSplitter
from sys import exit


logger = logging.getLogger(__name__)


def _add_match(match, sentence, extracted, sentence_id, lemma, item):
    logger.debug("Token '%s' matches sentence '%s'" % (match, sentence))
    matched_sentence = {
        'id': sentence_id,
        'lu': lemma,
        'text': sentence
    }
    item['sentences'].append(matched_sentence)
    sentence_id += 1
    extracted += 1
    return sentence_id, extracted


def extract_121(corpus, document_key, language, matches):
    """ 121 extraction strategy: 1 sentence per 1 LU
        N.B.: the same sentence will appear only once
        the sentence is assigned to a RANDOM LU
    """
    splitter = SentenceSplitter(language)
    tokenizer = Tokenizer(language)

    all_match_tokens = set()
    # dict token: lemma
    token_to_lemma = {}
    for lemma, match_tokens in matches.iteritems():
        for match_token in match_tokens:
            all_match_tokens.add(match_token)
            token_to_lemma[match_token] = lemma
    logger.debug("All match tokens: %s" % all_match_tokens)

    sentence_id = 0
    for item in corpus:
        extracted = 0
        item['sentences'] = []
        # Each input item should always contain text documents
        # Raise KeyError otherwise
        document = item[document_key]
        sentences = splitter.split(document)
        for sentence in sentences:
            sentence_tokens = [token.lower() for token in tokenizer.tokenize(sentence)]
            matched = []
            for match in all_match_tokens:
                if match.lower() in sentence_tokens:
                    matched.append(match)
            if matched:
                assigned_token = choice(matched)
                assigned_lu = token_to_lemma[assigned_token]
                current_id, current_extracted = _add_match(assigned_token, sentence, extracted, sentence_id, assigned_lu, item)
                sentence_id = current_id
                extracted = current_extracted

        if extracted > 0:
            logger.debug("%d sentences extracted. Removing the full text from the item ..." % extracted)
            item.pop(document_key)  # Remove text key
            yield item, extracted
        else:
            logger.debug("No sentences extracted. Skipping the whole item ...")


def extract_n2n(corpus, document_key, language, matches):
    """n2n extraction strategy: many sentences per many LUs
        N.B.: the same sentence is likely to appear multiple times
    """

    splitter = SentenceSplitter(language)
    tokenizer = Tokenizer(language)

    sentence_id = 0
    for item in corpus:
        extracted = 0
        item['sentences'] = []
        # Each input item should always contain text documents
        # Raise KeyError otherwise
        document = item[document_key]
        sentences = splitter.split(document)
        for sentence in sentences:
            # Remember to lowercase
            sentence_tokens = [token.lower() for token in tokenizer.tokenize(sentence)]

            for lemma, match_tokens in matches.iteritems():
                for match in match_tokens:
                    # Remember to lowercase
                    if match.lower() in sentence_tokens:
                        current_id, current_extracted = _add_match(match, sentence, extracted, sentence_id, lemma, item)
                        sentence_id = current_id
                        extracted = current_extracted

        if extracted > 0:
            logger.debug("%d sentences extracted. Removing the full text from the item ..." % extracted)
            item.pop(document_key)  # Remove text key
            yield item, extracted
        else:
            logger.debug("No sentences extracted. Skipping the whole item ...")


def extract_sentences(corpus, document_key, language, matches, strategy):
    """
    Extract sentences from the given corpus by matching tokens against a given set.
    :param corpus: Iterable of documents containing text and metadata
    :param str document_key: dict key to get the text documents
    :param str language: ISO 639-1 language code used for tokenization and sentence splitting
    :param dict matches: Dict with corpus lemmas as keys and tokens to be matched as values
    :param str strategy: One of the 3 extraction strategies ['121', 'n2n', 'syntactic']
    :return: the corpus, updated with the extracted sentences and the number of extracted sentences
    :rtype: generator of tuples
    """

    if strategy == 'n2n':
        logger.info("Will extract sentences using the 'many to many' strategy: the same sentence is likely to appear multiple times, with different LUs.")
        extract = extract_n2n
    elif strategy == '121':
        logger.info("Will extract sentences using the 'one to one' strategy: the same sentence will appear only once.")
        extract = extract_121
    elif strategy == 'syntactic':
        logger.info("Will extract sentences using the 'syntactic' strategy: the same sentence will appear only once.")
        pass
    else:
        raise ValueError("Malformed or unsupported extraction strategy: please use one of ['121', 'n2n', or 'syntactic']")

    for each in extract(corpus, document_key, language, matches):
        yield each


@click.command()
@click.argument('corpus', type=click.File())
@click.argument('document_key')
@click.argument('language_code')
@click.argument('matches', type=click.File())
@click.option('--strategy', '-s', type=click.Choice(['n2n', '121', 'syntactic']), default='n2n')
@click.option('--output', '-o', type=click.File('w'), default='dev/sentences.jsonlines')
def main(corpus, document_key, language_code, matches, strategy, output):
    """ Extract corpus sentences containing at least one token in the given set. """
    logger.info("Loading corpus dump from '%s' ..." % corpus.name)
    loaded = load_dumped_corpus(corpus, document_key)
    logger.info("Starting sentence extraction. Matches will be loaded from '%s'" % matches.name)
    total = 0
    updated = extract_sentences(loaded, document_key, language_code, json.load(matches), strategy)
    for item, extracted in updated:
        total += extracted
        output.write(json.dumps(item) + '\n')
    logger.info("Total sentences extracted: %d" % total)
    return 0


if __name__ == '__main__':
    exit(main())

