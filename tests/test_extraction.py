# -*- encoding: utf-8 -*-
import unittest
from strephit.extraction import process_semistructured


class TestSemistructured(unittest.TestCase):
    def get_statements(self, cache=False, sourced_only=False, language='en', **kwargs):
        return  [
            s for s in process_semistructured.serialize_item(
                (10, kwargs, cache, language, sourced_only))
        ]

    def test_complete_statements(self):
        self.assertEqual(set(self.get_statements(name= 'Fraser, Sir Colin', url='here')),
                         {u'Q933409\tP1477\t"colin fraser"\tS854\t"here"',
                          u'Q933409\tP1035\tQ209690\tS854\t"here"'})

    def test_unsourced(self):
        self.assertEqual(self.get_statements(name='no-url', sourced_only=True), [])
