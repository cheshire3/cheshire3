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

from cheshire3.document import Document, StringDocument
from cheshire3.preParser import PreParser, UnicodeDecodePreParser
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

    def test_process_document_returnType(self):
        self.assertRaises(NotImplementedError, 
                          self.testObj.process_document,
                          self.session,
                          StringDocument(''))


class ImplementedPreParserTestCase(PreParserTestCase):
    """Base Class for Implemented Cheshire3 PreParser Test Cases.
    
    i.e. PreParsers with a process_document method that actually does 
    something
    """
    
    def _get_class(self):
        raise NotImplementedError
        
    def test_process_document_returnType(self):
        # Test that return value is a Document
        self.assertIsInstance(self.outDoc, Document)
    
    def test_process_document_returnProcessHistory(self):
        # Test for presence of process history
        procHist = self.outDoc.processHistory
        self.assertIsInstance(procHist, list)
        # Test that process history has been copied
        for i, phi in enumerate(self.inDoc.processHistory):
            self.assertEqual(phi,
                             procHist[i])
        # Test that this PreParser has been added to processHistory
        self.assertEqual(procHist[-1], self.testObj.id)


class UnicodeDecodePreParserTestCase(ImplementedPreParserTestCase):
    """Base Class for Cheshire3 UnicodeDecodePreParser Test Cases."""
    
    @classmethod
    def _get_class(self):
        return UnicodeDecodePreParser

    @classmethod
    def _get_codec(self):
        raise NotImplementedError
    
    @classmethod
    def _get_config(self):
        return etree.XML('''\
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <options>
    <setting type="codec">{1}</setting>
  </options>
</subConfig>
'''.format(self._get_class(), self._get_codec()))
        
    def setUp(self):
        PreParserTestCase.setUp(self)
        self.testUc = u'This is my document'
        self.inDoc = StringDocument(self.testUc.encode(self._get_codec()))
        self.outDoc = self.testObj.process_document(self.session, self.inDoc)

    def test_unicode_content(self):
        "Check Document with content returns unaltered."
        uDoc = StringDocument(self.testUc)
        outDoc = self.testObj.process_document(self.session, uDoc)
        outDocContent = outDoc.get_raw(self.session)
        self.assertEqual(outDocContent,
                         self.testUc)
        
    def test_process_document_returnContent(self):
        # Test that content of returned Document is unaltered
        outDocContent = self.outDoc.get_raw(self.session)
        self.assertEqual(outDocContent,
                         self.testUc)
        

class Utf8UnicodeDecodePreParserTestCase(UnicodeDecodePreParserTestCase):
    """Cheshire3 UTF-8 UnicodeDecodePreParser Test Cases."""
    
    @classmethod
    def _get_codec(self):
        return 'utf-8'

    
class AsciiUnicodeDecodePreParserTestCase(UnicodeDecodePreParserTestCase):
    """Cheshire3 Ascii UnicodeDecodePreParser Test Cases."""
    
    @classmethod
    def _get_codec(self):
        return 'ascii'


class Iso8859_1UnicodeDecodePreParserTestCase(UnicodeDecodePreParserTestCase):
    """Cheshire3 Ascii UnicodeDecodePreParser Test Cases."""
    
    @classmethod
    def _get_codec(self):
        return 'iso-8859-1'


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(PreParserTestCase)
    suite.addTests(ltc(Utf8UnicodeDecodePreParserTestCase))
    suite.addTests(ltc(AsciiUnicodeDecodePreParserTestCase))
    suite.addTests(ltc(Iso8859_1UnicodeDecodePreParserTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
