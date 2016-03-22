# -*- encoding: utf-8 -*-
import unittest
from strephit.extraction import process_semistructured, extract_sentences
from strephit.extraction.extract_sentences import OneToOneExtractor, ManyToManyExtractor, SyntacticExtractor
from strephit.commons import cache

class TestSemistructured(unittest.TestCase):
    def setUp(self):
        cache.ENABLED = False

    def tearDown(self):
        cache.ENABLED = True

    def get_statements(self, cache=False, sourced_only=False, language='en', **kwargs):
        return [
            s for s in process_semistructured.serialize_item(
                (10, kwargs, cache, language, sourced_only))
        ]

    def test_complete_statements(self):
        self.assertEqual(set(self.get_statements(name='Fraser, Sir Colin', url='here')),
                         {u'Q5145111\tP1477\t"colin fraser"\tS854\t"here"',
                          u'Q5145111\tP1035\tQ209690\tS854\t"here"'})

    def test_unsourced(self):
        self.assertEqual(self.get_statements(name='no-url', sourced_only=True), [])


class TestExtractSentences(unittest.TestCase):
    def setUp(self):
        self.bio_key = 'text'
        self.sent_key = 'sent'

        self.bio_real = 'Austrian architect, born 1927 and died 1988'
        self.corpus_real = [{self.bio_key: self.bio_real}]
        self.lemma_to_token_real = {'bear': ['born'], 'die': ['died']}

        self.bio_fake = 'aaa bbb ccc ddd eee'
        self.corpus_fake = [{self.bio_key: self.bio_fake}]
        self.lemma_to_token_fake = {'123': ['bbb', 'ccc']}

    def test_121_real(self):
        items = list(OneToOneExtractor(self.corpus_real, self.bio_key, self.sent_key,
                                       'en', self.lemma_to_token_real).extract(1))

        self.assertEqual(len(items), 1)

        sentences = items[0][self.sent_key]
        self.assertEqual(len(sentences), 1)

        sentence = sentences[0]
        self.assertIn('text', sentence)
        self.assertIn('lu', sentence)
        self.assertEqual(sentence['text'], self.bio_real)
        self.assertIn(sentence['lu'], self.lemma_to_token_real.keys())

    def test_121_fake(self):
        items = list(OneToOneExtractor(self.corpus_fake, self.bio_key, self.sent_key,
                                       'en', self.lemma_to_token_fake).extract(1))
        self.assertEqual(items, [])

    def test_n2n_real(self):
        items = list(ManyToManyExtractor(self.corpus_real, self.bio_key, self.sent_key,
                                         'en', self.lemma_to_token_real).extract(1))

        self.assertEqual(len(items), 1)

        sentences = items[0][self.sent_key]
        self.assertEqual(len(sentences), 2)

        missing_lus = set(self.lemma_to_token_real.keys())
        for sentence in sentences:
            self.assertIn('text', sentence)
            self.assertIn('lu', sentence)
            self.assertEqual(sentence['text'], self.bio_real)
            self.assertIn(sentence['lu'], missing_lus)
            missing_lus.remove(sentence['lu'])

    def test_n2n_fake(self):
        items = list(ManyToManyExtractor(self.corpus_fake, self.bio_key, self.sent_key,
                                         'en', self.lemma_to_token_fake).extract(1))
        self.assertEqual(items, [])

    def test_syntactic(self):
        items = list(SyntacticExtractor([{'bio': 'this is part a1, and this is part a2'}],
                                        'bio', 'sentences', 'en', {'be': ['is', 'are']}).extract(1))
        self.assertEqual(len(items), 1)

        sentences = items[0]['sentences']
        self.assertEqual(len(sentences), 2)

        missing_parts = {'a1', 'a2'}
        for sentence in sentences:
            self.assertIn('text', sentence)
            self.assertIn('lu', sentence)
            self.assertEqual(sentence['lu'], 'be')

            for p in missing_parts:
                if p in sentence['text']:
                    self.assertEqual(sentence['text'], 'this is part ' + p)
                    missing_parts.remove(p)
                    break
            else:
                self.fail('Extracted unexpected sentence: %s' % repr(sentence))

        if missing_parts:
            self.fail('Did not find parts: %s' % repr(missing_parts))
