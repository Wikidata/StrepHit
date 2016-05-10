# -*- encoding: utf-8 -*-
import unittest

from treetaggerwrapper import Tag

from strephit.classification import feature_extractors


class TestFactExtractorFeatureExtractor(unittest.TestCase):
    def setUp(self):
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
        self.assertEqual(extractor.feature_for('word1', 'pos', 3), 0)
        self.assertEqual(extractor.feature_for('word2', 'lemma', -2), 1)
        self.assertEqual(extractor.feature_for('WoRd1', 'POs', 3), 0)

    def test_extract_features_no_window(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en', 0)
        f1 = extractor.extract_features(**self.sentences_data[0])
        f2 = extractor.extract_features(**self.sentences_data[1])

        self.assertEqual(f1[0][0], f2[0][0])
        self.assertEqual(f1[1][0], f2[1][0])
        self.assertEqual(f1[2][0], f2[2][0])

    def test_extract_features_window(self):
        window = 2
        extractor = feature_extractors.FactExtractorFeatureExtractor('en', window)
        feat = extractor.extract_features(**self.sentences_data[1])
        self.assertEqual(len(feat[2][0]), 3 * (2 * window + 1))

    def test_feature_labels(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en')
        tokens = extractor.extract_features(**self.sentences_data[0])
        self.assertEqual(tokens[0][1], 0)
        self.assertEqual(tokens[1][1], 1)
        self.assertEqual(tokens[2][1], 1)
        self.assertEqual(tokens[3][1], 2)

    def test_get_training_set(self):
        extractor = feature_extractors.FactExtractorFeatureExtractor('en')
        extractor.process_sentence(**self.sentences_data[0])
        extractor.process_sentence(**self.sentences_data[1])
        X, Y = extractor.get_training_set()

        self.assertEqual(X.shape, (9, 63))
        self.assertEqual(list(Y), [0, 1, 1, 2, 1, 1, 1, 1, 1])
