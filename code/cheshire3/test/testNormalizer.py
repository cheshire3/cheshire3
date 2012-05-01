u"""Cheshire3 Normalizer Unittests.

Normalizer configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Normalizer instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on instances.
"""

import unittest
import string

from lxml import etree

from cheshire3.dynamic import makeObjectFromDom
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class SimpleNormalizerTestCase(Cheshire3ObjectTestCase):
    u"""Base Class for Cheshire3 Normalizer Test Cases.
    
    Also includes tests for SimpleNormalizer base class that should not change
    the data in any way. 
    """

    def _init_config(self):    
        self.config = etree.XML('''\
<subConfig type="normalizer" id="SimpleNormalizer">
  <objectType>cheshire3.normalizer.SimpleNormalizer</objectType>
</subConfig>
''')
    
    def _init_tests(self):
        # Initialize equality tests for process_string
        self.process_string_test_pairs = [
            (string.uppercase, string.uppercase),
            (string.lowercase, string.lowercase),
            (string.punctuation, string.punctuation)]
        # Initialize dictionary equality tests for process_hash
        self.process_hash_test_pairs = [
            ({'foo': {'text': 'foo', 
                      'occurences': 1, 
                      'positions': [0, 0, 0], 
                      'proxLoc': [-1]
                      }
              },
             {'foo': {'text': 'foo', 
                      'occurences': 1, 
                      'positions': [0, 0, 0], 
                      'proxLoc': [-1]
                      }
              })]
    
    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        self._init_config()
        self.normalizer = makeObjectFromDom(self.session, self.config, None)
        self._init_tests()

    def tearDown(self):
        pass

    def test_process_string(self):
        for input, expected in self.process_string_test_pairs:
            output = self.normalizer.process_string(self.session, input) 
            self.assertEqual(output, expected)
        
    def test_process_hash(self):
        for input, expected in self.process_hash_test_pairs:
            output = self.normalizer.process_hash(self.session, input)
            self.assertDictEqual(output, expected)


class DataExistsNormalizerTestCase(SimpleNormalizerTestCase):
    
    def _init_config(self):
        self.config = etree.XML('''\
<subConfig type="normalizer" id="DataExistsNormalizer">
    <objectType>cheshire3.normalizer.DataExistsNormalizer</objectType>
</subConfig>
''')
    
    def _init_tests(self):
        # Initialize equality tests for process_string
        self.process_string_test_pairs = [
            (string.uppercase, "1"),
            (string.lowercase, "1"),
            (string.punctuation, "1"),
            ("", "0")]
        # Initialize dictionary equality tests for process_hash
        self.process_hash_test_pairs = [({"foo": {"text": "foo", "occurences": 1},
                                          "bar": {"text": "bar", "occurences": 2},
                                         "": {"text": "", "occurences": 10}},
                                         {"1": {"text": "1", "occurences": 3},
                                         "0": {"text": "0", "occurences": 10}})
                                        ]
        
        
class TermExistsNormalizerTestCase(SimpleNormalizerTestCase):
    
    def _init_config(self):
        self.config = etree.XML('''\
<subConfig type="normalizer" id="DataExistsNormalizer">
    <objectType>cheshire3.normalizer.TermExistsNormalizer</objectType>
    <options>
        <setting type="termlist">foo bar</setting>
    </options>
</subConfig>
''')
        
    def _init_tests(self):
        # Initialize equality tests for process_string
        self.process_string_test_pairs = [
            ('foo', "1"),
            ('bar', "1"),
            ('baz', "0")
        ]
        # Initialize dictionary equality tests for process_hash
        self.process_hash_test_pairs = [
            ({
                "foo": {"text": "foo", "occurences": 1},
                "bar": {"text": "bar", "occurences": 2},
                "baz": {"text": "baz", "occurences": 10}
             },
             "2")
        ]

    def test_process_hash(self):
        for input, expected in self.process_hash_test_pairs:
            output = self.normalizer.process_hash(self.session, input)
            self.assertEqual(output, expected)
        
        
class TermExistsNormalizerFreqTestCase(TermExistsNormalizerTestCase):
    
    def _init_config(self):
        self.config = etree.XML('''\
<subConfig type="normalizer" id="DataExistsNormalizer">
    <objectType>cheshire3.normalizer.TermExistsNormalizer</objectType>
    <options>
        <setting type="termlist">foo bar</setting>
        <setting type="frequency">1</setting>
    </options>
</subConfig>
''')
        
    def _init_tests(self):
        # Initialize equality tests for process_string
        self.process_string_test_pairs = [
            ('foo', "1"),
            ('bar', "1"),
            ('baz', "0")]
        # Initialize dictionary equality tests for process_hash
        self.process_hash_test_pairs = [
            ({
                "foo": {"text": "foo", "occurences": 1},
                "bar": {"text": "bar", "occurences": 2},
                "baz": {"text": "baz", "occurences": 10}
             },
             "3")
        ]


class CaseNormalizerTestCase(SimpleNormalizerTestCase):
    
    def _init_config(self):
        self.config = etree.XML('''\
<subConfig type="normalizer" id="DataExistsNormalizer">
    <objectType>cheshire3.normalizer.CaseNormalizer</objectType>
</subConfig>
''')
    
    def _init_tests(self):
        # Initialize equality tests for process_string
        self.process_string_test_pairs = [
            ("FooBar", "foobar"),
            (string.uppercase, string.lowercase),
            (string.lowercase, string.lowercase),
            (string.punctuation, string.punctuation)
        ]
        # Initialize dictionary equality tests for process_hash
        self.process_hash_test_pairs = [
            ({
                "foo": {"text": "foo", "occurences": 1},
                "Foo": {"text": "Foo", "occurences": 1},
                "FOO": {"text": "FOO", "occurences": 1},
                "BaR": {"text": "BaR", "occurences": 2},
                "bAz": {"text": "bAz", "occurences": 10}
             },
             {
                "foo": {"text": "foo", "occurences": 3},
                "bar": {"text": "bar", "occurences": 2},
                "baz": {"text": "baz", "occurences": 10}
             })
        ]


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(SimpleNormalizerTestCase)
    suite.addTests(loader.loadTestsFromTestCase(DataExistsNormalizerTestCase))
    suite.addTests(loader.loadTestsFromTestCase(TermExistsNormalizerTestCase))
    suite.addTests(loader.loadTestsFromTestCase(TermExistsNormalizerFreqTestCase))
    suite.addTests(loader.loadTestsFromTestCase(CaseNormalizerTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
