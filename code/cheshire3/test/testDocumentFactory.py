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
        i = 0
        for rec, expectedDocs in self._get_testDataAndExpected():
            rec.id = format(i, "d>0")
            i += 1 
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
                     "<c3:?component.*?>{0}</c3:?component>".format(expected),
                     )
    

class SpanComponentDocumentFactoryTestCase(ComponentDocumentFactoryTestCase):
    """ComponentDocumentFactory Test Case with SpanXPathSelectors."""
    
    def _get_dependencyConfigs(self):
        yield etree.XML('''
        <subConfig type="selector" id="spanXPath">
            <objectType>cheshire3.selector.SpanXPathSelector</objectType>
            <source>
                <xpath>hr</xpath>
                <xpath>hr</xpath>
            </source>
        </subConfig>''')

    def _get_config(self):
        # Return a parsed config for the object to be tested
        return etree.XML('''
        <subConfig type="documentFactory" id="componentDocumentFactory">
          <objectType>
            cheshire3.documentFactory.ComponentDocumentFactory
          </objectType>
          <source>
            <xpath ref="spanXPath" />
          </source>
          <options>
            <setting type="keepStart">0</setting>
            <setting type="keepEnd">0</setting>
            <default type="cache">0</default>
            <default type="format">component</default>
            <default type="codec">utf-8</default>
          </options>
        </subConfig>''')

    def _get_testDataAndExpected(self):
        # Simple example
        yield (LxmlRecord(etree.XML("""
        <div>
            <hr/>
            <p>
                Some text.
            </p>
            <hr/>
        </div>""")), ["""
            <p>
                Some text.
            </p>"""])
        # Simple example with tail text
        yield (LxmlRecord(etree.XML("""
        <div>
            <hr/>
            <p>
                Some text.
            </p> With tail text.
            <hr/>
        </div>""")), ["""
            <p>
                Some text.
            </p> With tail text.
        """])
        # Example where endNode is not a sibling of startNode
        # Tail text should be excluded now
        yield (LxmlRecord(etree.XML("""
        <div>
            <hr/>
            <p>
                Some text.
                <hr/>
            </p> With tail text
        </div>""")), ["""
            <p>
                Some text.
            </p>
        """])
        # Example where endNode is sibling of startNode ancestor
        yield (LxmlRecord(etree.XML("""
        <div>
            <p>Some text.
               <hr/>
            </p> With tail text
            <hr/>
        </div>""")), ["""
            <p></p> With tail text
        """])
        # Namespaced example
        yield (LxmlRecord(etree.XML("""
        <div xmlns="http.cheshire3.org/schemas/tests">
            <hr/>
            <p>
                Some text.
            </p>
            <hr/>
        </div>""")), ["""
            <p>
                Some text.
            </p>"""])
        

def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(ComponentDocumentFactoryTestCase)
    suite.addTests(ltc(SpanComponentDocumentFactoryTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
