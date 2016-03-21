# -*- encoding: utf-8 -*-
import unittest
from strephit.extraction import process_semistructured, extract_sentences
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
    def test_121(self):
        extracted = [x for x in extract_sentences.extract_sentences([
            {'text': 'tokens a1, a2'}
        ], 'text', 'en', {'1': ['a1'], '2': ['a2']}, '121')]

        self.assertEqual(len(extracted), 1)
        sentences, count = extracted[0]

        self.assertEqual(count, 1)
        self.assertEqual(len(sentences['sentences']), count)

        sentence = sentences['sentences'][0]
        self.assertIn('text', sentence)
        self.assertIn('lu', sentence)
        self.assertEqual('tokens a1, a2', sentence['text'])
        self.assertIn(sentence['lu'], {'1', '2'})

    def test_n2n(self):
        extracted = [x for x in extract_sentences.extract_sentences([
            {'text': 'tokens a1, a2'}
        ], 'text', 'en', {'1': ['a1'], '2': ['a2']}, 'n2n')]

        self.assertEqual(len(extracted), 1)
        sentences, count = extracted[0]

        self.assertEqual(count, 2)
        self.assertEqual(len(sentences['sentences']), count)

        missing_lus = {'1', '2'}
        for sentence in sentences['sentences']:
            self.assertIn('text', sentence)
            self.assertIn('lu', sentence)
            self.assertEqual('tokens a1, a2', sentence['text'])
            self.assertIn(sentence['lu'], missing_lus)
            missing_lus.remove(sentence['lu'])

    def test_syntactic(self):
        extracted = [x for x in extract_sentences.extract_sentences([
            {'bio': 'this is part a1, and this is part a2'}
        ], 'bio', 'en', {'be': ['is', 'are']}, 'syntactic')]

        self.assertEqual(len(extracted), 1)
        sentences, count = extracted[0]

        self.assertEqual(count, 2)
        self.assertEqual(len(sentences['sentences']), count)

        missing_parts = {'a1', 'a2'}
        for sentence in sentences['sentences']:
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
