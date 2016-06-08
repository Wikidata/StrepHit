# -*- encoding: utf-8 -*-

import unittest

from strephit.annotation import parse_results


class TestParseResults(unittest.TestCase):
    def setUp(self):
        self.unit_id = 1
        self.sentence_id = 1000

        self.sentences = [
            {
                '_unit_id': self.unit_id,
                'id': self.sentence_id,
                'answer_chunk_00': 'Entity',
                'chunk_00': 'table',
                'sentence': 'sentence 1000',
                'frame': 'something',
                'fe_00': 'Entity',
                'fe_01': 'Agent',
            }, {
                '_unit_id': self.unit_id,
                'id': self.sentence_id,
                'answer_chunk_00': 'Entity',
                'chunk_00': 'table',
                'sentence': 'sentence 1000',
                'frame': 'something',
                'fe_00': 'Entity',
                'fe_01': 'Agent',
            }, {
                '_unit_id': self.unit_id,
                'id': self.sentence_id,
                'answer_chunk_00': 'Agent',
                'chunk_00': 'table',
                'sentence': 'sentence 1000',
                'frame': 'something',
                'fe_00': 'Entity',
                'fe_01': 'Agent',
            },
        ]

    def test_basic(self):
        result = parse_results.process_unit(self.unit_id,
                                            [self.sentences[0]])

        self.assertEqual(result['frame'], self.sentences[0]['frame'])
        self.assertEqual(result['sentence'], self.sentences[0]['sentence'])
        self.assertEqual(result['id'], self.sentences[0]['id'])

    def test_majority(self):
        result = parse_results.process_unit(self.unit_id,
                                            self.sentences)
        self.assertEqual(result['fes']['Entity'], 'table')

    def test_missing(self):
        result = parse_results.process_unit(self.unit_id,
                                            self.sentences)
        self.assertEqual(result['fes']['Agent'], None)
