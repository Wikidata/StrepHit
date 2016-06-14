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
