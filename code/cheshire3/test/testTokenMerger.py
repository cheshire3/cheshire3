
u"""Cheshire3 TokenMerger Unittests.

TokenMerger configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and TokenMerger instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import string

from lxml import etree

from cheshire3.tokenMerger import SimpleTokenMerger,\
    ProximityTokenMerger, OffsetProximityTokenMerger,\
    SequenceRangeTokenMerger, MinMaxRangeTokenMerger, NGramTokenMerger,\
    ReconstructTokenMerger
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class TokenMergerTestCase(Cheshire3ObjectTestCase):
    
    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenMerger" id="{0.__name__}">
            <objectType>{0.__module__}.{0.__name__}</objectType>
        </subConfig>
        '''.format(self._get_class()))

    def _get_process_string_tests(self):
        # Return a list of tuples containing test pairs:
        # (string to be tokenized, expected tokens list)
        return [(string.uppercase, string.uppercase),
                (string.lowercase, string.lowercase),
                (string.digits, string.digits)]
    
    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        for instring, expected in self.process_string_tests:
            if expected is not None and expected:
                yield ({instring: {'text': [instring], 
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   }
                       },
                       {expected: {'text': expected,
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   }
                        })
                yield ({instring: {'text': [instring, instring], 
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   }
                       },
                       {expected: {'text': expected,
                                   'occurences': 2, 
                                   'positions': [0, 0, 0], 
                                   }
                        })

    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        self.process_string_tests = self._get_process_string_tests()
        self.process_hash_tests = self._get_process_hash_tests()
        self.maxDiff = None

    def test_process_string(self):
        "Check that process_string returns the expected tokens."
        if not self.process_string_tests:
            self.skipTest("No test data defined")
        for instring, expected in self.process_string_tests:
            output = self.testObj.process_string(self.session, instring)
            self.assertEqual(output, expected)
    
    def test_process_hash(self):
        "Check that process_hash returns expected hash."
        if not self.process_hash_tests:
            self.skipTest("No test data defined")
        for inhash, expected in self.process_hash_tests:
            output = self.testObj.process_hash(self.session, inhash)
            self.assertDictEqual(output, expected)


class SimpleTokenMergerTestCase(TokenMergerTestCase):

    @classmethod
    def _get_class(cls):
        return SimpleTokenMerger


class ProximityTokenMergerTestCase(TokenMergerTestCase):

    @classmethod
    def _get_class(cls):
        return ProximityTokenMerger

    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        for instring, expected in self.process_string_tests:
            if expected is not None and expected:
                yield ({instring: {'text': [instring], 
                                   'occurences': 1, 
                                   'proxLoc': [1]
                                   }
                       },
                       {instring: {'text': expected,
                                   'occurences': 1, 
                                   'positions': [1, 0], 
                                   }
                        })
                yield ({instring: {'text': [instring, instring], 
                                   'occurences': 1, 
                                   'proxLoc': [1]
                                   }
                       },
                       {instring: {'text': expected,
                                   'occurences': 2, 
                                   'positions': [1, 0, 1, 1], 
                                   }
                        })


class OffsetProximityTokenMergerTestCase(TokenMergerTestCase):

    @classmethod
    def _get_class(cls):
        return OffsetProximityTokenMerger

    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        for instring, expected in self.process_string_tests:
            if expected is not None and expected:
                yield ({instring: {'text': [instring], 
                                   'occurences': 1, 
                                   'proxLoc': [1],
                                   'wordOffs': [0],
                                   'charOffsets': [0]
                                   }
                       },
                       {instring: {'text': expected,
                                   'occurences': 1, 
                                   'positions': [1, 0, 0], 
                                   }
                        })
                yield ({instring: {'text': [instring, instring], 
                                   'occurences': 1, 
                                   'proxLoc': [1],
                                   'wordOffs': [0, 2],
                                   'charOffsets': [0, 100]
                                   }
                       },
                       {instring: {'text': expected,
                                   'occurences': 2, 
                                   'positions': [1, 0, 0, 1, 2, 100], 
                                   }
                        })


class SequenceRangeTokenMergerTestCase(TokenMergerTestCase):

    @classmethod
    def _get_class(cls):
        return SequenceRangeTokenMerger

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenMerger" id="{0.__name__}">
            <objectType>{0.__module__}.{0.__name__}</objectType>
            <options>
                <setting type="char">/</setting>
            </options>
        </subConfig>
        '''.format(self._get_class()))

    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        yield ({'None': {'text': [0, 4, 5, 9],
                         'occurences': 1, 
                        }
               },
               {'0/4': {'text': '0/4',
                        'occurences': 1, 
                       },
                '5/9': {'text': '5/9',
                        'occurences': 1, 
                       }
                })


class MinMaxRangeTokenMergerTestCase(TokenMergerTestCase):

    @classmethod
    def _get_class(cls):
        return MinMaxRangeTokenMerger

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenMerger" id="{0.__name__}">
            <objectType>{0.__module__}.{0.__name__}</objectType>
            <options>
                <setting type="char">/</setting>
            </options>
        </subConfig>
        '''.format(self._get_class()))

    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        yield ({'0': {'text': [0], 
                      'occurences': 1, 
                },
                '9': {'text': [9], 
                      'occurences': 1, 
                }
               },
               {'0/9': {'text': '0/9',
                        'occurences': 1, 
                       }
                })


class NGramTokenMergerTestCase(TokenMergerTestCase):

    @classmethod
    def _get_class(cls):
        return NGramTokenMerger

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenMerger" id="{0.__name__}">
            <objectType>{0.__module__}.{0.__name__}</objectType>
            <options>
                <setting type="nValue">2</setting>
            </options>
        </subConfig>
        '''.format(self._get_class()))
    
    def _get_process_hash_tests(self):
        yield ({'This is a tokenized sentence': {
                    'text': ['This', 'is', 'a', 'tokenized', 'sentence'], 
                    'occurences': 1}
               },
               {'This is': {
                    'text': 'This is',
                    'occurences': 1},
                'is a': {
                    'text': 'is a',
                    'occurences': 1},
                'a tokenized': {
                    'text': 'a tokenized',
                    'occurences': 1},
                'tokenized sentence': {
                    'text': 'tokenized sentence',
                    'occurences': 1}
              })
        yield ({u'This is tokenized unicode': {
                    'text': [u'This', u'is', u'tokenized', u'unicode'],
                    'occurences': 1,
                    }
               },
               {u'This is': {
                    'text': u'This is',
                    'occurences': 1},
                u'is tokenized': {
                    'text': u'is tokenized',
                    'occurences': 1},
                u'tokenized unicode': {
                    'text': u'tokenized unicode',
                    'occurences': 1}
              })


class ReconstructTokenMergerTestCase(TokenMergerTestCase):

    @classmethod
    def _get_class(cls):
        return ReconstructTokenMerger

    def _get_process_hash_tests(self):
        yield ({'This is a tokenized sentence': {
                    'text': ['This', 'is', 'a', 'tokenized', 'sentence'], 
                    'occurences': 1}
               },
               {'This is a tokenized sentence': {
                    'text': 'This is a tokenized sentence', 
                    'occurences': 1}
              })


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(SimpleTokenMergerTestCase)
    suite.addTests(ltc(ProximityTokenMergerTestCase))
    suite.addTests(ltc(OffsetProximityTokenMergerTestCase))
    suite.addTests(ltc(SequenceRangeTokenMergerTestCase))
    suite.addTests(ltc(MinMaxRangeTokenMergerTestCase))
    suite.addTests(ltc(NGramTokenMergerTestCase))
    suite.addTests(ltc(ReconstructTokenMergerTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
