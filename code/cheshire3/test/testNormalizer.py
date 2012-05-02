u"""Cheshire3 Normalizer Unittests.

Normalizer configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Normalizer instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on instances.
"""

import unittest
import string

from lxml import etree

from cheshire3.normalizer import Normalizer, SimpleNormalizer, \
    DataExistsNormalizer, TermExistsNormalizer, CaseNormalizer
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class NormalizerTestCase(Cheshire3ObjectTestCase):
    """Base Class for Cheshire3 Normalizer Test Cases.."""
    
    def _get_process_string_tests(self):
        # Return a list of 2-string tuples containing test pairs:
        # (string to be normalized, expected result)
        return []
    
    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        return []
        
    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        self.process_string_tests = self._get_process_string_tests()
        self.process_hash_tests = self._get_process_hash_tests()
        
    def tearDown(self):
        pass
        
    def test_instance(self):
        self.assertIsInstance(self.testObj, Normalizer)

    def test_process_string(self):
        for instring, expected in self.process_string_tests:
            output = self.testObj.process_string(self.session, instring) 
            self.assertEqual(output, expected)
    
    def test_process_hash(self):
        for inhash, expected in self.process_hash_tests:
            output = self.testObj.process_hash(self.session, inhash)
            self.assertDictEqual(output, expected)
    

class SimpleNormalizerTestCase(NormalizerTestCase):
    u"""Test Case for SimpleNormalizer (base class for Normalizers that should
    not change the data in any way). 
    """

    def _get_config(self):    
        return etree.XML('''\
<subConfig type="normalizer" id="SimpleNormalizer">
  <objectType>cheshire3.normalizer.SimpleNormalizer</objectType>
</subConfig>
''')
    
    def _get_process_string_tests(self):
        return [
            (string.uppercase, string.uppercase),
            (string.lowercase, string.lowercase),
            (string.punctuation, string.punctuation)]
        
    def _get_process_hash_tests(self):
        return [
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
        
    def test_instance(self):
        self.assertIsInstance(self.testObj, SimpleNormalizer)
    

class DataExistsNormalizerTestCase(SimpleNormalizerTestCase):
    
    def _get_config(self):
        return etree.XML('''\
<subConfig type="normalizer" id="DataExistsNormalizer">
    <objectType>cheshire3.normalizer.DataExistsNormalizer</objectType>
</subConfig>
''')
    
    def _get_process_string_tests(self):
        return [
            (string.uppercase, "1"),
            (string.lowercase, "1"),
            (string.punctuation, "1"),
            ("", "0")]
        
    def _get_process_hash_tests(self):
        return [
            ({"foo": {"text": "foo", "occurences": 1},
              "bar": {"text": "bar", "occurences": 2},
              "": {"text": "", "occurences": 10}
             },
             {"1": {"text": "1", "occurences": 3},
              "0": {"text": "0", "occurences": 10}
              })]
        
    def test_instance(self):
        self.assertIsInstance(self.testObj, DataExistsNormalizer)
        
        
class TermExistsNormalizerTestCase(SimpleNormalizerTestCase):
    
    def _get_config(self):
        return etree.XML('''\
<subConfig type="normalizer" id="DataExistsNormalizer">
    <objectType>cheshire3.normalizer.TermExistsNormalizer</objectType>
    <options>
        <setting type="termlist">foo bar</setting>
    </options>
</subConfig>
''')
        
    def _get_process_string_tests(self):
        return[
            ('foo', "1"),
            ('bar', "1"),
            ('baz', "0")
        ]
        
    def _get_process_hash_tests(self):
        return [
            ({
                "foo": {"text": "foo", "occurences": 1},
                "bar": {"text": "bar", "occurences": 2},
                "baz": {"text": "baz", "occurences": 10}
             },
             "2")
        ]

    def test_process_hash(self):
        for input, expected in self.process_hash_tests:
            output = self.testObj.process_hash(self.session, input)
            self.assertEqual(output, expected)
            
    def test_instance(self):
        self.assertIsInstance(self.testObj, TermExistsNormalizer)
        
        
class TermExistsNormalizerFreqTestCase(TermExistsNormalizerTestCase):
    
    def _get_config(self):
        return etree.XML('''\
<subConfig type="normalizer" id="DataExistsNormalizer">
    <objectType>cheshire3.normalizer.TermExistsNormalizer</objectType>
    <options>
        <setting type="termlist">foo bar</setting>
        <setting type="frequency">1</setting>
    </options>
</subConfig>
''')
    
    def _get_process_string_tests(self):
        return [
            ('foo', "1"),
            ('bar', "1"),
            ('baz', "0")]
        
    def _get_process_hash_tests(self):
        return[
            ({
                "foo": {"text": "foo", "occurences": 1},
                "bar": {"text": "bar", "occurences": 2},
                "baz": {"text": "baz", "occurences": 10}
             },
             "3")
        ]
        

class CaseNormalizerTestCase(SimpleNormalizerTestCase):
    
    def _get_config(self):
        return etree.XML('''\
<subConfig type="normalizer" id="DataExistsNormalizer">
    <objectType>cheshire3.normalizer.CaseNormalizer</objectType>
</subConfig>
''')
    
    def _get_process_string_tests(self):
        return [
            ("FooBar", "foobar"),
            (string.uppercase, string.lowercase),
            (string.lowercase, string.lowercase),
            (string.punctuation, string.punctuation)
        ]
        
    def _get_process_hash_tests(self):
        return [
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
    
    def test_instance(self):
        self.assertIsInstance(self.testObj, CaseNormalizer)


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
