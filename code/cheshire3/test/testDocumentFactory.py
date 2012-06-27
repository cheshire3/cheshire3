u"""Cheshire3 DocumentFactory Unittests.

DocumentFactory configurations may be customized by the user. For the purposes 
of unittesting, configuration files will be ignored and DocumentFactory 
instances will be instantiated using configuration data defined within this 
testing module, and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest
    
import string

from lxml import etree

from cheshire3.documentFactory import SimpleDocumentFactory, \
ComponentDocumentFactory
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class DocumentFactoryTestCase(Cheshire3ObjectTestCase):
    
    def _get_testData(self):
        return []

    def test_load(self):
        # Test that load method of an instance returns the instance
        for data in self._get_testData():
            thing = self.testObj.load(self.session, data)
            self.assertIsInstance(thing, self._get_class())


class SimpleDocumentFactoryTestCase(DocumentFactoryTestCase):
    """Cheshire3 SimpleDocumentFactory Test Case."""
    
    @classmethod
    def _get_class(self):
        return SimpleDocumentFactory
    
    def _get_config(self):
        return etree.XML('''\
<subConfig type="documentFactory" id="baseDocumentFactory">
    <objectType>cheshire3.documentFactory.{0}</objectType>
</subConfig>'''.format(self._get_class().__name__))
        

class ComponentDocumentFactoryTestCase(DocumentFactoryTestCase):
    """ComponentDocumentFactory Test Case with simple XPath selectors."""
    
    def _get_class(self):
        return ComponentDocumentFactory
    
    def _get_config(self):
        # Return a parsed config for the object to be tested
        return etree.XML('''\
<subConfig type="documentFactory" id="componentDocumentFactory">
    <objectType>cheshire3.documentFactory.{0}</objectType>
    <source>
      <xpath>bar</xpath>
      <xpath>baz</xpath>
    </source>
    <options>
        <default type="cache">0</default>
        <default type="format">component</default>
    </options>
</subConfig>'''.format(self._get_class().__name__))

    def test_componentExtraction(self):
        pass
    

class SpanComponentDocumentFactoryTestCase(ComponentDocumentFactoryTestCase):
    """ComponentDocumentFactory Test Case with SpanXPathSelectors."""
    
    def _get_config(self):
        # Return a parsed config for the object to be tested
        return etree.XML('''\
        ''')


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(ComponentDocumentFactoryTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
