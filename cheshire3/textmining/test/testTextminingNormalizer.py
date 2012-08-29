u"""Cheshire3 Textmining Normalizer Unittests.

Normalizer configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Normalizer instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree
from collections import Hashable

from cheshire3.textmining.normalizer import NltkPosNormalizer
from cheshire3.test.testNormalizer import NormalizerTestCase

class NltkPosNormalizerTestCase(NormalizerTestCase):
    """Base Class for Cheshire3 NLTK PoS Normalizer Test Cases."""
    
    @classmethod
    def _get_class(cls):
        return NltkPosNormalizer

    def _get_config(self):    
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
          <objectType>cheshire3.textmining.normalizer.{0.__name__}</objectType>
        </subConfig>'''.format(self._get_class()))
    
    def _get_process_string_tests(self):
        # Return a list of 2-string tuples containing test pairs:
        # (string to be normalized, expected result)
        # Examples taken from NLTK online documentation
        return [("John's big idea isn't all that bad.",
                 "John/NNP 's/POS big/JJ idea/NN is/VBZ n't/RB all/DT that/DT "
                 "bad/JJ ./."),
                (['John', "'s", 'big', 'idea', 'is', "n't", 'all', 'that',
                  'bad', '.'],
                 ['John/NNP', "'s/POS", 'big/JJ', 'idea/NN', 'is/VBZ',
                  "n't/RB", 'all/DT', 'that/DT', 'bad/JJ', './.'])
                ]
        
    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        for instring, expected in self.process_string_tests:
            if (expected is not None and
                isinstance(expected, Hashable) and
                expected):
                yield ({instring: {'text': instring, 
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   'proxLoc': [-1]
                                   }
                       },
                       {expected: {'text': expected,
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   'proxLoc': [-1]
                                   }
                        })    


class NltkJustPosNormalizerTestCase(NltkPosNormalizerTestCase):
    """Cheshire3 NLTK PoS Normalizer Test Case to return only the PoS."""
    
    @classmethod
    def _get_class(cls):
        return NltkPosNormalizer

    def _get_config(self):    
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
          <objectType>cheshire3.textmining.normalizer.{0.__name__}</objectType>
          <options>
            <setting type="justPos">1</setting>
          </options>
        </subConfig>'''.format(self._get_class()))
    
    def _get_process_string_tests(self):
        # Return a list of 2-string tuples containing test pairs:
        # (string to be normalized, expected result)
        # Examples taken from NLTK online documentation
        return [("John's big idea isn't all that bad.",
                 "NNP POS JJ NN VBZ RB DT DT JJ ."),
                (['John', "'s", 'big', 'idea', 'is', "n't", 'all', 'that',
                  'bad', '.'],
                 ['NNP', "POS", 'JJ', 'NN', 'VBZ', "RB", 'DT', 'DT',
                  'JJ', '.'])
                ]


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(NltkPosNormalizerTestCase)
    suite.addTests(ltc(NltkJustPosNormalizerTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))