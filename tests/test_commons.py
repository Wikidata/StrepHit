import unittest
import itertools
from strephit.commons import parallel
from collections import Counter


class TestParallel(unittest.TestCase):
    def setUp(self):
        self.list_in = range(10)
        self.correct = set(map(self.function, self.list_in))
        self.list_in_nones = [x if x % 4 == 0 else None for x in xrange(20)]
        self.correct_nones = set(filter(self.none_filter, map(self.function,
                                        filter(self.none_filter, self.list_in_nones))))
        self.correct_multi = itertools.chain(*map(self.multi_function, self.list_in))

    def function(self, x):
        return 2 * x

    def none_filter(self, x):
        return x is not None

    def multi_function(self, x):
        for z in xrange(x):
            yield z

    def exc_function(self, x):
        raise ValueError('hello!')

    def consume(self, generator):
        [x for x in generator]

    def test_single_process(self):
        list_out = set(parallel.map(self.function, self.list_in, processes=1))
        self.assertEqual(list_out, self.correct)

    def test_multi_process(self):
        list_out = set(parallel.map(self.function, self.list_in, processes=2))
        self.assertEqual(list_out, self.correct)

    def test_with_nones_single_process(self):
        list_out = set(parallel.map(self.function, self.list_in_nones, processes=2))
        self.assertEqual(list_out, self.correct_nones)

    def test_with_nones_multi_process(self):
        list_out = set(parallel.map(self.function, self.list_in_nones, processes=1))
        self.assertEqual(list_out, self.correct_nones)

    def test_more_workers(self):
        list_out = set(parallel.map(self.function, self.list_in, processes=20))
        self.assertEqual(list_out, self.correct)

    def test_flatten_single_process(self):
        list_out = parallel.map(self.multi_function, self.list_in, processes=1,
                                flatten=True)
        self.assertEqual(Counter(list_out), Counter(self.correct_multi))

    def test_flatten_multi_process(self):
        list_out = parallel.map(self.multi_function, self.list_in, processes=2,
                                flatten=True)
        self.assertEqual(Counter(list_out), Counter(self.correct_multi))

    def test_exception_single(self):
        self.assertRaises(ValueError, self.consume,
                          parallel.map(self.exc_function, self.list_in, processes=1,
                                      raise_exc=True))
