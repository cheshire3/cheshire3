u"""Abstract Base Class for Cheshire3 Object Unittests."""

try:
    import unittest2 as unittest
except ImportError:
    import unittest
    
import string

from cheshire3.baseObjects import Session
from cheshire3.configParser import CaselessDictionary


class Cheshire3TestCase(unittest.TestCase):
    u"""Abstract Base Class for Cheshire3 Test Cases.   
        
    Almost all objects in Cheshire3 require a Session, so create one.
    """
    
    def setUp(self):
        self.session = Session()
    
    def tearDown(self):
        pass
        

class CaselessDictionaryTestCase(unittest.TestCase):
    
    def setUp(self):
        # Set up a regular dictionary for quick init of caseless one in tests
        self.d = d = dict([(char, i) for i, char in enumerate(string.uppercase)])
        # Set up a caseless dictionary for non-mutating tests
        self.cd = CaselessDictionary(d)
    
    def tearDown(self):
        pass
    
    def test_init(self):
        self.assertIsInstance(CaselessDictionary(), CaselessDictionary)
        self.assertIsInstance(CaselessDictionary(self.d), CaselessDictionary)
        self.assertIsInstance(CaselessDictionary(self.d.items()), CaselessDictionary)
        
    def test_contains(self):
        # Test contains each key
        for char in string.uppercase:
            self.assertTrue(char in self.cd)
            
    def test_contains_anycase(self):
        # Test contains each key but in lower case
        for char in string.lowercase:
            self.assertTrue(char in self.cd)
            
    def test_contains_false(self):
        # Test does not contain any keys that wasn't set
        for char in string.punctuation:
            self.assertFalse(char in self.cd)
            
    def test_getitem(self):
        # Test __getitem__ by key
        for i, char in enumerate(string.uppercase):
            self.assertEqual(self.cd[char], i)
            
    def test_getitem_anycase(self):
        # Test __getitem__ by key but in lower case
        for i, char in enumerate(string.lowercase):
            self.assertEqual(self.cd[char], i)
            
    def test_getitem_keyerror(self):
        # Test __getitem__ for missing keys raises KeyError
        for char in string.punctuation:
            self.assertRaises(KeyError, self.cd.__getitem__, char)
            
    def test_get(self):
        # Test get by key
        for i, char in enumerate(string.uppercase):
            self.assertEqual(self.cd.get(char), i)
            
    def test_get_anycase(self):
        # Test get by key but in lower case
        for i, char in enumerate(string.lowercase):
            self.assertEqual(self.cd.get(char), i)
            
    def test_get_default(self):
        # Test returns None when missing key and no default given
        self.assertIsNone(self.cd.get('NotThere'))
        # Test returns not None when missing key and default given
        self.assertIsNotNone(self.cd.get('NotThere', ''))
        # Test returns given default when missing key
        self.assertEqual(self.cd.get('NotThere', 0), 0)
        self.assertEqual(self.cd.get('NotThere', ""), "")
        self.assertEqual(self.cd.get('NotThere', "Default"), "Default")
        
    def test_setitem(self):
        # Test that items can be got after being set
        cd = CaselessDictionary()
        for key, val in self.d.iteritems():
            cd[key] = val
            self.assertEqual(cd[key], val)
            self.assertEqual(cd[key.lower()], val)
        

def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(CaselessDictionaryTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
