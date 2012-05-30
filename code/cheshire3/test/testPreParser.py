u"""Cheshire3 PreParser Unittests.

PreParser configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and PreParser instances will
be instantiated using configurations defined within this testing module, 
and tests carried out on those instances using data defined in this module.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.document import StringDocument
from cheshire3.preParser import PreParser
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class PreParserTestCase(Cheshire3ObjectTestCase):
    """Base Class for Cheshire3 PreParser Test Cases.
    
    Tests that Abstract Base Class has not been modified.
    """
    
    @classmethod
    def _get_class(self):
        return PreParser
    
    @classmethod
    def _get_config(self):    
        return etree.XML('''\
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
</subConfig>
'''.format(self._get_class()))
    
    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        
    def tearDown(self):
        pass
        
    def test_instance(self):
        self.assertIsInstance(self.testObj, self._get_class())
        
    def test_processDocument(self):
        self.assertRaises(NotImplementedError, 
                          self.testObj.process_document,
                          self.session,
                          StringDocument(''))


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(PreParserTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
