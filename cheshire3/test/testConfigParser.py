u"""Abstract Base Class for Cheshire3 Object Unittests."""

import os

try:
    import unittest2 as unittest
except ImportError:
    import unittest
    
import string

from lxml import etree

from cheshire3.baseObjects import Session
from cheshire3.configParser import C3Object, CaselessDictionary
from cheshire3.dynamic import makeObjectFromDom
from cheshire3.internal import cheshire3Root
from cheshire3.server import SimpleServer


class Cheshire3ObjectTestCase(unittest.TestCase):
    u"""Abstract Base Class for Cheshire3 Test Cases.   
        
    Almost all objects in Cheshire3 require a Session, and a server as its 
    parent, so create these now.
    """

    @classmethod
    def _get_class(cls):
        # Return class of object to test
        return C3Object
    
    def _get_config(self):
        # Return a parsed config for the object to be tested
        return etree.XML('''
        <subConfig id="{0.__name__}">
            <objectType>{0.__module__}.{0.__name__}</objectType>
        </subConfig>
        '''.format(self._get_class()))
    
    def _get_dependencyConfigs(self):
        # Generator of configs for objects on which this object depends
        # e.g. an Index may depends on and IndexStore for storage, and
        # Selectors, Extractors etc.
        return
        yield
    
    def setUp(self):
        self.session = Session()
        serverConfig = os.path.join(cheshire3Root,
                                    'configs',
                                    'serverConfig.xml')
        self.server = SimpleServer(self.session, serverConfig)
        for config in self._get_dependencyConfigs():
            identifier = config.get('id')
            self.server.subConfigs[identifier] = config
        # Disable stdout logging
        lgr = self.server.get_path(self.session, 'defaultLogger')
        lgr.minLevel = 60
        # Create object that will be tested
        config = self._get_config()
        self.testObj = makeObjectFromDom(self.session, config, self.server)
    
    def tearDown(self):
        pass
    
    def test_serverInstance(self):
        "Check test case's Session instance."
        self.assertIsInstance(self.server, SimpleServer)
        
    def test_instance(self):
        "Check that C3Object is an instance of the expected class."
        self.assertIsInstance(self.testObj, self._get_class())


class NamespacedCheshire3ObjectTestCase(Cheshire3ObjectTestCase):

    def _get_config(self):
        # Return a parsed config for the object to be tested
        return etree.XML(
            '<cfg:subConfig '
            'xmlns:cfg="http://www.cheshire3.org/schemas/config/"'
            ' id="{0.__name__}">'
            '<cfg:objectType>{0.__module__}.{0.__name__}</cfg:objectType>'
            '</cfg:subConfig>'.format(self._get_class())
        )


class DefaultNamespacedCheshire3ObjectTestCase(Cheshire3ObjectTestCase):

    def _get_config(self):
        # Return a parsed config for the object to be tested
        return etree.XML(
            '<subConfig '
            'xmlns="http://www.cheshire3.org/schemas/config/" '
            'id="{0.__name__}">'
            '<objectType>{0.__module__}.{0.__name__}</objectType>'
            '</subConfig>'.format(self._get_class())
        )


class CaselessDictionaryTestCase(unittest.TestCase):
    
    def setUp(self):
        # Set up a regular dictionary for quick init of caseless one in tests
        l = [(char, i) for i, char in enumerate(string.uppercase)]
        self.d = d = dict(l)
        # Set up a caseless dictionary for non-mutating tests
        self.cd = CaselessDictionary(d)
    
    def tearDown(self):
        pass
    
    def test_init(self):
        self.assertIsInstance(CaselessDictionary(),
                              CaselessDictionary)
        self.assertIsInstance(CaselessDictionary(self.d),
                              CaselessDictionary)
        self.assertIsInstance(CaselessDictionary(self.d.items()),
                              CaselessDictionary)
        
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
    ltc = loader.loadTestsFromTestCase
    suite = ltc(CaselessDictionaryTestCase)
    suite.addTests(ltc(Cheshire3ObjectTestCase))
    suite.addTests(ltc(NamespacedCheshire3ObjectTestCase))
    suite.addTests(ltc(DefaultNamespacedCheshire3ObjectTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
