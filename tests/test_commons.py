# -*- encoding: utf-8 -*-
import os
import shutil
import tempfile
import random
import unittest
import itertools
from strephit.commons import *
from collections import Counter
from treetaggerwrapper import Tag


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

    def test_execute(self):
        funcs = reduce(lambda x, y: x + y,
                       [(self.function, [x]) for x in xrange(10)])
        self.assertEqual(parallel.execute(0, *funcs),
                         map(self.function, xrange(10)))


class TestCache(unittest.TestCase):
    def random_hex_string(self, length):
        return ''.join(random.choice('0123456789abcdef') for _ in xrange(6))

    @cache.cached
    def not_entirely_random_hex_string(self, length):
        return self.random_hex_string(length)

    def setUp(self):
        self.cache_loc = self.random_hex_string(8)
        self.cache_hash_for = cache._hash_for
        self.cache_path_for = cache._path_for
        cache.BASE_DIR = os.path.join(tempfile.gettempdir(), self.cache_loc)
        os.makedirs(cache.BASE_DIR)

    def tearDown(self):
        shutil.rmtree(cache.BASE_DIR)
        cache._hash_for = self.cache_hash_for
        cache._path_for = self.cache_path_for

    def test_path(self):
        hashed = 'hashed key'
        full, base, fname = cache._path_for(hashed)
        self.assertEqual(os.path.join(base, fname), full)
        self.assertEqual(os.path.commonprefix([cache.BASE_DIR, full, base]),
                         cache.BASE_DIR)

    def test_simple_get(self):
        self.assertIsNone(cache.get('non existing'))
        self.assertEqual(cache.get('non existing', 'default'), 'default')

    def test_simple_set(self):
        cache.set('key', 'value')
        self.assertEqual(cache.get('key'), 'value')

    def test_set_overwrite(self):
        cache.set('key', 'value')
        cache.set('key', 'another value', overwrite=True)
        self.assertEqual(cache.get('key'), 'another value')
        cache.set('key', 'something else', overwrite=False)
        self.assertEqual(cache.get('key'), 'another value')

    def test_decorator(self):
        val = self.not_entirely_random_hex_string(128)
        for _ in xrange(10):
            self.assertEqual(val, self.not_entirely_random_hex_string(128))

    def test_unicode(self):
        cache.set(u'\u84c4\u3048\u3066 \u304f\u3060\u3055\u3044',
                  u'\u304a\u75b2\u308c\u3055\u307e')
        self.assertEqual(cache.get(u'\u84c4\u3048\u3066 \u304f\u3060\u3055\u3044'),
                         u'\u304a\u75b2\u308c\u3055\u307e')

    def test_collisions(self):
        def collision_hash(key):
            if key in {'key-1', 'key-2'}:
                return 'the same hashed value'
            else:
                return self.cache_hash_for(key)
        cache._hash_for = collision_hash

        cache.set('key-1', 'value-1')
        cache.set('key-2', 'value-2')

        self.assertEqual(cache.get('key-1'), 'value-1')
        self.assertEqual(cache.get('key-2'), 'value-2')

    def test_folder_creation(self):
        def same_prefix_path(hashed):
            base = os.path.join(cache.BASE_DIR, 'some prefix')
            return os.path.join(base, hashed), base, hashed
        cache._path_for = same_prefix_path

        try:
            cache.set('key1', 'value1')
            cache.set('key2', 'value2')
        except OSError:
            self.fail('failed to set cache')

    def test_decorator_key(self):
        @cache.cached
        def function1(x):
            return 'something from function 1'

        @cache.cached
        def function2(x):
            return 'something from function 2'

        function1('value')
        function2('value')

        self.assertNotEqual(function1('value'), function2('value'))

    def test_enabled(self):
        cache.ENABLED = False
        cache.set('key', 'value')
        self.assertEqual(cache.get('key', 'something else'), 'something else')
        cache.ENABLED = True

    def test_objects(self):
        obj = {'this': ['is', ['a']], 'complex': 'object'}
        cache.set('obj', obj)
        self.assertEqual(obj, cache.get('obj'))


class TestWikidata(unittest.TestCase):

    def setUp(self):
        cache.ENABLED = False

    def tearDown(self):
        cache.ENABLED = True

    def test_date_width(self):
        self.assertEqual(wikidata.format_date(1967, 1, 17),
                         '+00000001967-01-17T00:00:00Z/11')

    def test_negative_year(self):
        self.assertEqual(wikidata.format_date(-100, None, None),
                         '-00000000100-01-01T00:00:00Z/9')
        self.assertRaises(ValueError, wikidata.format_date, 100, -1, 1)
        self.assertRaises(ValueError, wikidata.format_date, 100, 1, -1)

    def test_parse_date(self):
        self.assertEqual(wikidata.parse_date('-00000000100-01-01T00:00:00Z/9'),
                         {'year': -100, 'month': None, 'day': None})

    def test_parse_date_with_precision(self):
        self.assertEqual(wikidata.parse_date('+00000000101-02-03T00:00:00Z', precision=10),
                         {'year': 101, 'month': 2, 'day': None})

    def test_missing(self):
        self.assertRaises(ValueError, wikidata.format_date, None, None, None)
        self.assertRaises(ValueError, wikidata.format_date, None, None, 1)
        self.assertRaises(ValueError, wikidata.format_date, None, 1, None)
        self.assertRaises(ValueError, wikidata.format_date, 1, None, 1)

        try:
            wikidata.format_date(1, 1, 1)
            wikidata.format_date(1, 1, None)
            wikidata.format_date(1, None, None)
            wikidata.format_date(None, 1, 1)
        except ValueError:
            self.fail('date should be accepted')

    def test_gender_resolver(self):
        self.assertEqual(wikidata.gender_resolver('P21', 'male', 'en'), 'Q6581097')
        self.assertEqual(wikidata.gender_resolver('P21', 'maschio', 'it'), 'Q6581097')
        self.assertEqual(wikidata.gender_resolver('P21', 'female', 'en'), 'Q6581072')
        self.assertEqual(wikidata.gender_resolver('P21', 'femmina', 'it'), 'Q6581072')

    def test_resolvers(self):
        self.assertEqual(wikidata.resolve('P1035', 'prof', 'en'), 'Q121594')
        self.assertEqual(wikidata.resolve('P21', 'male', 'en'), 'Q6581097')
        self.assertEqual(wikidata.resolve('P570', 'Feb 24, 2016', 'en'),
                         '+00000002016-02-24T00:00:00Z/11')

    def test_honorifics_resolver(self):
        for honorific, id_ in [
                ('prof', 'Q121594'),
                ('dr', 'Q4618975'),
                ('phd', 'Q4618975'),
                ('bishop', 'Q611644'),
                ('arcibishop', 'Q611644'),
                ('st', 'Q43115'),
                ('hon', 'Q2746176'),
                ('rev', 'Q42603'),
                ('prof', 'Q121594'),
                ('miss', 'Q13359947'),
                ('mrs', 'Q313549'),
                ('mister', 'Q177053'),
                ('mr', 'Q177053'),
                ('sir', 'Q209690')]:

            self.assertEqual(wikidata.honorifics_resolver('P1035', honorific, 'en'),
                             id_)

        with self.assertRaises(ValueError):
            _ = wikidata.honorifics_resolver('P1035', 'st', 'it')

    def test_name_resolver_with_birth(self):
        additional_info = {'P569': ['+1893-09-20T00:00:00Z/11']}
        self.assertEqual(wikidata.name_resolver('P1477', 'colin fraser', 'en', **additional_info),
                         'Q5145111')

    def test_name_resolver_with_death(self):
        additional_info = {'P570': ['+1958-08-15T00:00:00Z/11']}
        self.assertEqual(wikidata.name_resolver('P1477', 'colin fraser', 'en', **additional_info),
                         'Q5145111')

    def test_name_resolver_with_gender(self):
        self.assertEqual('', wikidata.name_resolver('P1477', 'colin fraser', 'en', P21=['Q6581097']))

    def test_place_resolver(self):
        self.assertEqual(wikidata.place_resolver('Pwhatever', 'vaughan', 'en'), 'Q44013')


class TestDatetime(unittest.TestCase):
    def test_simple_date(self):
        self.assertEqual(datetime.parse('24/2/2016'),
                         {'year': 2016, 'month': 2, 'day': 24})

    def test_simply_year(self):
        self.assertEqual(datetime.parse('1863'),
                         {'year': 1863, 'month': None, 'day': None})

    def test_fallbacks(self):
        self.assertEqual(datetime.parse('b.c. 123'),
                         {'year': -123, 'day': None, 'month': None})
        self.assertEqual(datetime.parse('123Bc'),
                         {'year': -123, 'day': None, 'month': None})


class TestText(unittest.TestCase):
    def test(self):
        for string, birth, death in [
                    ('b. 1234', '1234', None),
                    ('b. ca. 1234', '1234', None),
                    ('b. c. 1234', '1234', None),
                    ('d. 1234', None, '1234'),
                    ('d. ca. 1234', None, '1234'),
                    ('d. c. 1234', None, '1234'),
                    ('19th century', '1801', '1900'),
                    ('1234-5678', '1234', '5678'),
                    ('ca. 1234-5678', '1234', '5678'),
                    ('c. 1234-5678', '1234', '5678'),
                    ('1234-ca. 5678', '1234', '5678'),
                    ('1234-c. 5678', '1234', '5678'),
                ]:
            b, d = text.parse_birth_death(string)
            self.assertEqual(birth, b)
            self.assertEqual(death, d)

    def test_honoricifs(self):
        for full, cleaned in [('rev. john eddowes', 'john eddowes'),
                              ('sir john ware edgar', 'john ware edgar'),
                              ('hon. sir malcolm fraser', 'malcolm fraser'),
                              ]:
            self.assertEqual(text.strip_honorifics(full)[0],
                             cleaned)

    def test_fix_name(self):
        self.assertEqual(text.fix_name('  Colin Fraser    '),
                         ('colin fraser', []))
        self.assertEqual(text.fix_name('Fraser, Colin'),
                         ('colin fraser', []))
        self.assertEqual(text.fix_name('Sir Colin Fraser'),
                         ('colin fraser', ['sir']))
        self.assertEqual(text.fix_name('Fraser, Sir Colin'),
                         ('colin fraser', ['sir']))


class TestSplitter(unittest.TestCase):
    def test(self):
        splitter = PunktSentenceSplitter('en')
        self.assertListEqual(list(splitter.split('hello world. this is another sentence! got it?')),
                             ['hello world.', 'this is another sentence!', 'got it?'])


class TestPosTag(unittest.TestCase):
    items = [
        {
            'id': 1,
            'text': u'first item to be tagged',
            'correct': [Tag(word=u'first', pos=u'JJ', lemma=u'first'),
                        Tag(word=u'item', pos=u'NN', lemma=u'item'),
                        Tag(word=u'to', pos=u'TO', lemma=u'to'),
                        Tag(word=u'be', pos=u'VB', lemma=u'be'),
                        Tag(word=u'tagged', pos=u'VVN', lemma=u'tag')],
        },
        {
            'id': 2,
            'text': u'another item ready for pos tag',
            'correct': [Tag(word=u'another', pos=u'DT', lemma=u'another'),
                        Tag(word=u'item', pos=u'NN', lemma=u'item'),
                        Tag(word=u'ready', pos=u'JJ', lemma=u'ready'),
                        Tag(word=u'for', pos=u'IN', lemma=u'for'),
                        Tag(word=u'pos', pos=u'NNS', lemma=u'po'),
                        Tag(word=u'tag', pos=u'NN', lemma=u'tag')]

        }
    ]

    def setUp(self):
        self.tagger = pos_tag.TTPosTagger('en')

    def test_tag_many(self):
        for each in self.tagger.tag_many(self.items, 'text', 'tagged'):
            self.assertIn('correct', each)
            self.assertIn('tagged', each)
            self.assertIn('text', each)
            self.assertEqual(each['tagged'], each['correct'])

    def tag_one(self):
        for each in self.items:
            self.assertEqual(self.tagger.tag_one(each['text']),
                             each['correct'])