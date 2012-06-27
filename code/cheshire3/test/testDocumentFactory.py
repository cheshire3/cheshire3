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
from cheshire3.record import LxmlRecord
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
    
    @classmethod
    def _get_class(self):
        return ComponentDocumentFactory
    
    def _get_config(self):
        # Return a parsed config for the object to be tested
        return etree.XML('''\
<subConfig type="documentFactory" id="{0}">
    <objectType>cheshire3.documentFactory.{0}</objectType>
    <source>
      <xpath>meal</xpath>
    </source>
    <options>
        <default type="cache">0</default>
        <default type="format">component</default>
    </options>
</subConfig>'''.format(self._get_class().__name__))
        
    def _get_testData(self):
        yield LxmlRecord(etree.XML("""
        <menu>
            <meal>
                <egg/>
                <bacon/>
            </meal>
            <meal>
                <egg/>
                <sausage/>
                <bacon/>
            </meal>
            <meal>
                <egg/>
                <spam/>
            </meal>
            <meal>
                <egg/>
                <bacon/>
                <spam/>
            </meal>
        </menu>
        """))
    
    def _get_testDataAndExpected(self):
        for rec in self._get_testData():
            yield (rec,
                   [etree.tostring(el)
                    for el in
                    rec.process_xpath(self.session, 'meal')]
                   )

    def test_componentExtraction(self):
        for rec, expectedDocs in self._get_testDataAndExpected():
            self.testObj.load(self.session, rec)
            docs = []
            for doc in self.testObj:
                docs.append(doc)
            # Check expected number of Documents generated
            self.assertEqual(len(expectedDocs),
                             len(docs),
                             "Number of generated docs ({0}) not as expected"
                             " ({1})".format(len(docs), len(expectedDocs)))
            for doc, expected in zip(docs, expectedDocs):
                docstr = doc.get_raw(self.session)
                self.assertRegexpMatches(
                     docstr,
                     "<c3:?component.*?>\s+{0}\s+</c3:?component>".format(expected),
                     )
    

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
