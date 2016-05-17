# -*- encoding: utf-8 -*-
import unittest

from strephit.rule_based import classify


class TestClassify(unittest.TestCase):
    def setUp(self):
        self.language = 'en'
        self.frame_data = {
            'play': {
                'frame': 'competition',
                'lu': 'play.v',
                'pos': 'V',
                'extra_fes': [],
                'core_fes': [
                    {
                        'type': 'Core',
                        'fe': 'Participant_1',
                        'semantic_type': None,
                        'dbpedia_classes': ['Person', 'Organisation']
                    },
                    {
                        'type': 'Core',
                        'fe': 'Participant_2',
                        'semantic_type': None,
                        'dbpedia_classes': ['Person', 'Organisation']
                    },
                    {
                        'type': 'Core',
                        'fe': 'Competition',
                        'semantic_type': None,
                        'dbpedia_classes': ['Competition']
                    }
                ]
            }
        }

        self.sentences = [
            {
                'text': 'Jo played Leslie at tennis.',
                'tagged': [
                    ('Jo', 'NP', 'Jo'),
                    ('played', 'VVD', 'play'),
                    ('Leslie', 'NP', 'Leslie'),
                    ('at', 'IN', 'at'),
                    ('tennis', 'NN', 'tennis')
                ],
                'linked_entities': [
                    {
                        'chunk': 'Jo',
                        'start': 0,
                        'end': 2,
                        'confidence': 1.0,
                        'uri': 'http://jo',
                        'types': [
                            'http://dbpedia.org/ontology/Person'
                        ]
                    },
                    {
                        'chunk': 'Leslie',
                        'start': 10,
                        'end': 16,
                        'confidence': 1.0,
                        'uri': 'http://leslie',
                        'types': [
                            'http://dbpedia.org/ontology/Person'
                        ]
                    },
                    {
                        'chunk': 'tennis',
                        'start': 20,
                        'end': 26,
                        'confidence': 1.0,
                        'uri': 'http://tennis',
                        'types': [
                            'http://dbpedia.org/ontology/Competition'
                        ]
                    }
                ]
            }
        ]

    def test_assing_frame_elements(self):
        cl = classify.RuleBasedClassifier(self.frame_data, self.language)
        assigned = cl.assign_frame_elements(self.sentences[0]['linked_entities'],
                                            self.frame_data['play'])

        self.assertEqual(assigned['Competition']['chunk'], 'tennis')
        self.assertEqual(assigned['Competition']['score'], 1.0)
        self.assertEqual(assigned['Competition']['type'], 'Core')
        self.assertEqual(assigned['Competition']['fe'], 'Competition')
        self.assertEqual(assigned['Competition']['uri'], 'http://tennis')
        self.assertTrue(assigned['Participant_1']['chunk'] in {'Leslie', 'Jo'})
