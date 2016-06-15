# -*- encoding: utf-8 -*-
import unittest

from treetaggerwrapper import Tag

from strephit.classification import feature_extractors


class TestFactExtractorFeatureExtractor(unittest.TestCase):
    def setUp(self):
        self.gazetteer = {
            'sentence': ['feature1', 'feature2']
        }

        self.sentences_data = [
            {
                'sentence': u'This is the first sentence',
                'fes': {
                    'Subject': u'this',
                    'Missing': u'this is not',
                    'Object': u'first sentence',
                },
            },
            {
                'sentence': u'This is the second sentence',
                'fes': {},
            }
        ]

    def test_sorted_set(self):
        s = feature_extractors.SortedSet()
        for i in xrange(5):
            index = s.put(i)
            self.assertEqual(index, i)

        for i in xrange(5):
            index = s.index(i)
            self.assertEqual(index, i)

    def test_sentence_to_tokens(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en')
        tokens = extractor.sentence_to_tokens(**self.sentences_data[0])
        self.assertEqual(tokens, [[u'this', u'DT', u'this', u'Subject'],
                                  Tag(word=u'is', pos=u'VBZ', lemma=u'be'),
                                  Tag(word=u'the', pos=u'DT', lemma=u'the'),
                                  [u'first sentence', 'ENT', u'first sentence', u'Object']])

    def test_feature_for(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en')
        self.assertEqual(extractor.feature_for('word1', 'pos', 3, True), 1)
        self.assertEqual(extractor.feature_for('word2', 'lemma', -2, True), 2)
        self.assertEqual(extractor.feature_for('WoRd1', 'POs', 3, True), 1)

    def test_extract_features_no_window(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en', 0)
        _, f1 = extractor.extract_features(add_unknown=True, gazetteer=self.gazetteer,
                                           **self.sentences_data[0])
        _, f2 = extractor.extract_features(add_unknown=True, gazetteer=self.gazetteer,
                                           **self.sentences_data[1])

        self.assertEqual(f1[0][0], f2[0][0])
        self.assertEqual(f1[1][0], f2[1][0])
        self.assertEqual(f1[2][0], f2[2][0])

    def test_extract_features_window(self):
        window = 2
        extractor = feature_extractors.FactExtractorFeatureExtractor('en', window)
        _, feat = extractor.extract_features(add_unknown=True, gazetteer=self.gazetteer,
                                             **self.sentences_data[1])

        self.assertEqual(len(feat[2][0]), 3 * (2 * window + 1) + 2)

    def test_feature_labels(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en')
        _, tokens = extractor.extract_features(add_unknown=True, gazetteer=self.gazetteer,
                                               **self.sentences_data[0])
        self.assertEqual(tokens[0][1], 0)
        self.assertEqual(tokens[1][1], 1)
        self.assertEqual(tokens[2][1], 1)
        self.assertEqual(tokens[3][1], 2)

    def test_get_training_set(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en')
        extractor.process_sentence(add_unknown=True, gazetteer=self.gazetteer,
                                   **self.sentences_data[0])
        extractor.process_sentence(add_unknown=True, gazetteer=self.gazetteer,
                                   **self.sentences_data[1])
        x, y = extractor.get_features()

        self.assertEqual(x.shape, (9, 70))
        self.assertEqual(list(y), [0, 1, 1, 2, 1, 1, 1, 1, 1])

    def test_unknown_token(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en')
        self.assertEqual(extractor.feature_for('a', 'b', 12, add_unknown=False),
                         extractor.unk_index)
