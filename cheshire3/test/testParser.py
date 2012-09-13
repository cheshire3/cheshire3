u"""Cheshire3 Prser Unittests.

Parser configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Parser instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on those instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.document import StringDocument
from cheshire3.exceptions import XMLSyntaxError
from cheshire3.parser import Parser, SaxParser, MinidomParser, LxmlParser,\
                             LxmlHtmlParser, PassThroughParser, MarcParser
from cheshire3.record import Record, DomRecord, MinidomRecord, LxmlRecord,\
                             SaxRecord, MarcRecord
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class ParserTestCase(Cheshire3ObjectTestCase):
    """Abstract Base Class for Cheshire3 Parser Test Case."""

    @classmethod
    def _get_class(self):
        return Parser
    
    @classmethod
    def _get_config(self):    
        return etree.XML('''\
        <subConfig type="parser" id="{0.__name__}">
          <objectType>cheshire3.parser.{0.__name__}</objectType>
        </subConfig>
        '''.format(self._get_class()))
    
    @classmethod
    def _get_document(cls):
        return StringDocument('''''')

    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)

    def tearDown(self):
        pass

    def test_process_document_returnType(self):
        "Check that Base Class raises NotImplementedError."
        self.assertRaises(NotImplementedError, 
                          self.testObj.process_document,
                          self.session,
                          StringDocument(''))


class XmlParserTestCase(ParserTestCase):
    """Base Class for XML Parser test cases."""
    
    @classmethod
    def _get_class(self):
        return SaxParser
    
    @classmethod
    def _get_recordClass(cls):
        return SaxRecord

    @classmethod
    def _get_data(cls):
        # Generator to yield data to be parsed into records
        yield ('<doc>'
               '<el attr="value">text</el>'  # element with attribute
               '<el>text</el>tail'           # element with tail text
               '<empty-el/>'                 # empty/self-closing element
               '</doc>')
        # Default namespaced example
        yield ('<doc xmlns="http://example.com/schemas/doc">'
               '<el attr="value">text</el>'  # element with attribute
               '<el>text</el>tail'           # element with tail text
               '<empty-el/>'                 # empty/self-closing element
               '</doc>')
        # Prefixed namespaced example
        yield ('<doc:doc xmlns:doc="http://example.com/schemas/doc">'
               '<doc:el attr="value">text</doc:el>'  # element with attribute
               '<doc:el>text</doc:el>tail'           # element with tail text
               '<doc:empty-el/>'                   # empty/self-closing element
               '</doc:doc>')
        # Unicode example
        yield (u'<doc>'
               u'<el attr="value">text</el>'  # element with attribute
               u'<el>text</el>tail'           # element with tail text
               u'<empty-el/>'                 # empty/self-closing element
               u'</doc>')

    def test_process_document_invalid(self):
        "Check that invalid/non-well-formed XML is rejected."
        # Will need to be subclassed for each Parser implementation, as they
        # will likely all return their own error class
        self.assertRaises(XMLSyntaxError,
                          self.testObj.process_document,
                          self.session,
                          StringDocument('<xml>'))

    def test_process_document_returnType(self):
        "Check returns an instance of appropriate Record sub-class."
        for data in self._get_data():
            rec = self.testObj.process_document(self.session,
                                                StringDocument(data))
            self.assertIsInstance(rec, self._get_recordClass())

    def test_process_document_returnContent(self):
        "Check that returned Record content is unchanged."
        for data in self._get_data():
            rec = self.testObj.process_document(self.session,
                                                StringDocument(data))
            self.assertEqual(rec.get_xml(self.session),
                             data)

    def test_process_document_returnProcessHistory(self):
        "Check that returned Record has parser in history."
        for data in self._get_data():
            rec = self.testObj.process_document(self.session,
                                                StringDocument(data))
            self.assertEqual(len(rec.processHistory), 1)
            self.assertEqual(rec.processHistory[0],
                             self.testObj.id)


class SaxParserTestCase(XmlParserTestCase):
    """SaxParser tests."""

    @classmethod
    def _get_class(self):
        return SaxParser

    @classmethod
    def _get_recordClass(cls):
        return SaxRecord
    
    @classmethod
    def _get_data(cls):
        # Filter out namespaced example data
        for data in XmlParserTestCase._get_data():
            if not 'xmlns' in data:
                yield data


class NsSaxParserTestCase(SaxParserTestCase):
    """Namespace aware SaxParser Tests."""

    @classmethod
    def _get_config(self):    
        return etree.XML('''\
        <subConfig type="parser" id="{0.__name__}">
          <objectType>cheshire3.parser.{0.__name__}</objectType>
          <options>
            <setting type="namespaces">1</setting>
          </options>
        </subConfig>
        '''.format(self._get_class()))
        
    @classmethod
    def _get_data(cls):
        # Filter out non-namespaced example data
        for data in XmlParserTestCase._get_data():
            if 'xmlns' in data:
                yield data


class LxmlParserTestCase(XmlParserTestCase):
    
    @classmethod
    def _get_class(self):
        return LxmlParser
    
    @classmethod
    def _get_recordClass(cls):
        return LxmlRecord


class LxmlHtmlParserTestCase(LxmlParserTestCase):
    
    @classmethod
    def _get_class(self):
        return LxmlHtmlParser
    
    def test_process_document_returnContent(self):
        "Check that returned Record content is unchanged."
        self.skipTest("Likely to fail due to addition of HTML DOCTYPE "
                      "declaration")
        
    def test_process_document_invalid(self):
        "Check that invalid/non-well-formed XML is rejected."
        self.skipTest("LxmlHtmlParser is tolerant of non-well-formed XML")
    

class MinidomParserTestCase(XmlParserTestCase):

    @classmethod
    def _get_class(self):
        return MinidomParser

    @classmethod
    def _get_recordClass(cls):
        return MinidomRecord


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(ParserTestCase)
    suite.addTests(ltc(SaxParserTestCase))
    suite.addTests(ltc(NsSaxParserTestCase))
    suite.addTests(ltc(LxmlParserTestCase))
    suite.addTests(ltc(LxmlHtmlParserTestCase))
    suite.addTests(ltc(MinidomParserTestCase))
    return suite

    
if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
