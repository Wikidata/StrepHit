# -*- encoding: utf-8 -*-
import unittest
from treetaggerwrapper import Tag
from strephit.extraction import process_semistructured, extract_sentences
from strephit.extraction.extract_sentences import *
from strephit.commons import cache

class TestSemistructured(unittest.TestCase):
    def setUp(self):
        cache.ENABLED = False

    def tearDown(self):
        cache.ENABLED = True

    def get_statements(self, sourced_only=False, language='en', **kwargs):
        ser = process_semistructured.SemistructuredSerializer(language, sourced_only)
        return list(ser.serialize_item(kwargs))

    def test_complete_statements(self):
        self.assertEqual(set(self.get_statements(name='Fraser, Sir Colin', url='here')),
                         {(True, ('Q5145111', 'P1559', 'en:"Colin Fraser"', 'here')),
                          (True, ('Q5145111', 'P1035', 'Q209690', 'here'))})

    def test_unresolved(self):
        self.assertEqual(self.get_statements(name='asd', url='here', sourced_only=True),
                         [(False, 'asd')])

    def test_unsourced(self):
        self.assertEqual(self.get_statements(name='no-url', sourced_only=True), [])


class TestExtractSentences(unittest.TestCase):
    def setUp(self):
        self.text_key = 'txt'
        self.sent_key = 'sent'

        self.url = 'http://www.example.org'
        self.name = 'Forbes William'

        self.match_base_form = False

        self.text_real = u'Forbes William was born on 3 January'
        self.corpus_real = [{self.text_key: self.text_real, 'url': self.url,
                             'name': self.name}]
        self.lemma_to_token_real = {'bear': ['born'], 'die': ['died']}

        self.text_fake = u'sentence with no verbs'
        self.corpus_fake = [{self.text_key: self.text_fake, 'url': self.url,
                             'name': self.name}]
        self.lemma_to_token_fake = {'123': ['bbb', 'ccc']}

    def test_121_real(self):
        sentences = list(OneToOneExtractor(
            self.corpus_real, self.text_key, self.sent_key, 'en',
            self.lemma_to_token_real, self.match_base_form
        ).extract(1))

        self.assertEqual(len(sentences), 1)

        sentence = sentences[0]
        self.assertIn('url', sentence)
        self.assertIn('text', sentence)
        self.assertIn('lu', sentence)
        self.assertEqual(sentence['text'], self.text_real)
        self.assertIn(sentence['lu'], self.lemma_to_token_real.keys())

    def test_121_fake(self):
        sentences = list(OneToOneExtractor(
            self.corpus_real, self.text_key, self.sent_key,
            'en', self.lemma_to_token_fake, self.match_base_form
        ).extract(1))
        self.assertEqual(sentences, [])

    def test_n2n_real(self):
        sentences = list(ManyToManyExtractor(
            self.corpus_real, self.text_key, self.sent_key,
            'en', self.lemma_to_token_real, self.match_base_form
        ).extract(1))

        missing_lus = set(self.lemma_to_token_real.keys())
        for sentence in sentences:
            self.assertIn('url', sentence)
            self.assertIn('text', sentence)
            self.assertIn('lu', sentence)
            self.assertEqual(sentence['text'], self.text_real)
            self.assertIn(sentence['lu'], missing_lus)
            missing_lus.remove(sentence['lu'])

    def test_n2n_fake(self):
        sentences = list(ManyToManyExtractor(
            self.corpus_real, self.text_key, self.sent_key,
            'en', self.lemma_to_token_fake, self.match_base_form
        ).extract(1))
        self.assertEqual(sentences, [])

    def test_syntactic(self):
        sentences = list(SyntacticExtractor(
            [{'bio': u'this is part a1, and this is part a2', 'url': 'www.example.org', 'name': 'abc def'}],
            'bio', 'sentences', 'en', {'be': ['is', 'are']}, self.match_base_form
        ).extract(1))

        self.assertEqual(len(sentences), 2)

        missing_parts = {'a1', 'a2'}
        for sentence in sentences:
            self.assertIn('url', sentence)
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

    def test_grammar(self):
        sentences = list(GrammarExtractor(
            self.corpus_real, self.text_key, self.sent_key,
            'en', self.lemma_to_token_real, self.match_base_form
        ).extract(1))

        self.assertEqual(1, len(sentences))

        sentence = sentences[0]
        self.assertIn('url', sentence)
        self.assertIn('text', sentence)
        self.assertIn('lu', sentence)
        self.assertEqual(sentence['text'], self.text_real)
        self.assertIn(sentence['lu'], self.lemma_to_token_real.keys())
