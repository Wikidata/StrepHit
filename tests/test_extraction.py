# -*- encoding: utf-8 -*-
import unittest
from strephit.extraction import process_semistructured


class TestSemistructured(unittest.TestCase):
    def get_statements(self, cache=False, sourced_only=False, language='en', **kwargs):
        return  [
            s for s in process_semistructured.serialize_item(
                (10, kwargs, cache, language, sourced_only))
        ]

    def test_honoricifs(self):
        for full, cleaned in [('rev. john eddowes', 'john eddowes'),
                              ('sir john ware edgar', 'john ware edgar'),
                              ('hon. sir malcolm fraser', 'malcolm fraser'),
                              ]:
            self.assertEqual(process_semistructured.strip_honorifics(full)[0],
                             cleaned)

    def test_fix_name(self):
        self.assertEqual(process_semistructured.fix_name('  Colin Fraser    '),
                         ('colin fraser', []))
        self.assertEqual(process_semistructured.fix_name('Fraser, Colin'),
                         ('colin fraser', []))
        self.assertEqual(process_semistructured.fix_name('Sir Colin Fraser'),
                         ('colin fraser', ['sir']))
        self.assertEqual(process_semistructured.fix_name('Fraser, Sir Colin'),
                         ('colin fraser', ['sir']))

    def test_complete_statements(self):
        self.assertEqual(set(self.get_statements(name= 'Fraser, Sir Colin', url='here')),
                         set([u'Q933409\tP1477\t"colin fraser"\tS854\t"here"',
                              u'Q933409\tP1035\t"sir"\tS854\t"here"']))

    def test_unsourced(self):
        self.assertEqual(self.get_statements(name='no-url', sourced_only=True), [])
