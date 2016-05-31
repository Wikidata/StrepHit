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
        return [
            s for s in process_semistructured.serialize_item(
                (10, kwargs, language, sourced_only))
        ]

    def test_complete_statements(self):
        self.assertEqual(set(self.get_statements(name='Fraser, Sir Colin', url='here')),
                         {('Q5145111', 'P1559', '"Colin Fraser"', 'here'),
                          ('Q5145111', 'P1035', 'Q209690', 'here')})

    def test_unsourced(self):
        self.assertEqual(self.get_statements(name='no-url', sourced_only=True), [])


class TestExtractSentences(unittest.TestCase):
    def setUp(self):
        self.text_key = 'txt'
        self.tagged_key = 'tg'
        self.sent_key = 'sent'
        self.url = 'http://www.example.org'
        self.match_base_form = False

        self.text_real = 'Forbes William was born on 3 January'
        self.tagged_real = [Tag(word=u'Forbes', pos=u'NP', lemma=u'Forbes'),
                            Tag(word=u'William', pos=u'NP', lemma=u'William'),
                            Tag(word=u'was', pos=u'VBD', lemma=u'be'),
                            Tag(word=u'born', pos=u'VVN', lemma=u'bear'),
                            Tag(word=u'on', pos=u'IN', lemma=u'on'),
                            Tag(word=u'3', pos=u'CD', lemma=u'3'),
                            Tag(word=u'January', pos=u'NP', lemma=u'January')]
        self.corpus_real = [{self.tagged_key: self.tagged_real,
                             self.text_key: self.text_real,
                             'url': self.url}]
        self.lemma_to_token_real = {'bear': ['born'], 'die': ['died']}

        self.text_fake = 'sentence with no verbs'
        self.tagged_fake = [Tag(word=u'sentence', pos=u'NN', lemma=u'sentence'),
                            Tag(word=u'with', pos=u'IN', lemma=u'with'),
                            Tag(word=u'no', pos=u'DT', lemma=u'no'),
                            Tag(word=u'verbs', pos=u'NNS', lemma=u'verb')]
        self.corpus_fake = [{self.tagged_key: self.tagged_fake,
                             self.text_key: self.text_fake,
                             'url': self.url}]
        self.lemma_to_token_fake = {'123': ['bbb', 'ccc']}

    def test_121_real(self):
        items = list(OneToOneExtractor(self.corpus_real, self.tagged_key, self.text_key, self.sent_key,
                                       'en', self.lemma_to_token_real, self.match_base_form).extract(1))

        self.assertEqual(len(items), 1)

        sentences = items[0][self.sent_key]
        self.assertEqual(len(sentences), 1)

        sentence = sentences[0]
        self.assertIn('url', sentence)
        self.assertIn('text', sentence)
        self.assertIn('lu', sentence)
        self.assertEqual(sentence['text'], self.text_real)
        self.assertIn(sentence['lu'], self.lemma_to_token_real.keys())

    def test_121_fake(self):
        items = list(OneToOneExtractor(self.corpus_real, self.tagged_key, self.text_key, self.sent_key,
                                       'en', self.lemma_to_token_fake, self.match_base_form).extract(1))
        self.assertEqual(items, [])

    def test_n2n_real(self):
        items = list(ManyToManyExtractor(self.corpus_real, self.tagged_key, self.text_key, self.sent_key,
                                         'en', self.lemma_to_token_real, self.match_base_form).extract(1))

        self.assertEqual(len(items), 1)

        sentences = items[0][self.sent_key]
        self.assertEqual(len(sentences), 1)

        missing_lus = set(self.lemma_to_token_real.keys())
        for sentence in sentences:
            self.assertIn('url', sentence)
            self.assertIn('text', sentence)
            self.assertIn('lu', sentence)
            self.assertEqual(sentence['text'], self.text_real)
            self.assertIn(sentence['lu'], missing_lus)
            missing_lus.remove(sentence['lu'])

    def test_n2n_fake(self):
        items = list(ManyToManyExtractor(self.corpus_real, self.tagged_key, self.text_key, self.sent_key,
                                         'en', self.lemma_to_token_fake, self.match_base_form).extract(1))
        self.assertEqual(items, [])

    def test_syntactic(self):
        items = list(SyntacticExtractor([{'bio': 'this is part a1, and this is part a2','url': 'www.example.org'}],
                                        'tag', 'bio', 'sentences', 'en', {'be': ['is', 'are']}, self.match_base_form
                                        ).extract(1))
        self.assertEqual(len(items), 1)

        sentences = items[0]['sentences']
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
        items = list(GrammarExtractor(self.corpus_real, self.tagged_key, self.text_key, self.sent_key,
                                      'en', self.lemma_to_token_real, self.match_base_form).extract(1))
        self.assertEqual(1, len(items))

        sentences = items[0][self.sent_key]
        self.assertEqual(1, len(sentences))

        sentence = sentences[0]
        self.assertIn('url', sentence)
        self.assertIn('text', sentence)
        self.assertIn('lu', sentence)
        self.assertEqual(sentence['text'], self.text_real)
        self.assertIn(sentence['lu'], self.lemma_to_token_real.keys())
