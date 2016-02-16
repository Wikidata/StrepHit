# -*- coding: utf-8 -*-

import utils
from nose2.compat import unittest


class TestParseBirthDeath(unittest.TestCase):
    cases = [
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
    ]

    def test(self):
        for string, birth, death in self.cases:
            b, d = utils.parse_birth_death(string)
            self.assertEqual(birth, b)
            self.assertEqual(death, d)
