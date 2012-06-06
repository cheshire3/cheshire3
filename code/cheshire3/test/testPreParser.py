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
from cheshire3.preParser import PreParser, UnicodeDecodePreParser, \
    CmdLinePreParser, FileUtilPreParser, MagicRedirectPreParser, \
    HtmlSmashPreParser, RegexpSmashPreParser, SgmlPreParser, AmpPreParser, \
    MarcToXmlPreParser, MarcToSgmlPreParser, TxtToXmlPreParser,\
    PicklePreParser, UnpicklePreParser
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class PreParserTestCase(Cheshire3ObjectTestCase):
    """Base Class for Cheshire3 PreParser Test Cases.
    
    Also checks that Abstract Base Class has not been modified.
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
        "Check that PreParser is an instance of expected class"
        self.assertIsInstance(self.testObj, self._get_class())

    def test_process_document_returnType(self):
        "Check that Base Class raises NotImplementedError."
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

    def setUp(self):
        PreParserTestCase.setUp(self)
        self.testUc = u'This is my document'
        self.inDoc = StringDocument(self.testUc)
        self.outDoc = self.testObj.process_document(self.session, self.inDoc)
        
    def test_process_document_returnType(self):
        "Check that PreParser returns a Document."
        self.assertIsInstance(self.outDoc, Document)
    
    def test_process_document_returnProcessHistory(self):
        "Check processHistory of returned Document."
        # Test for presence of process history
        procHist = self.outDoc.processHistory
        self.assertIsInstance(procHist, list)
        # Test that previous process history has been copied correctly
        for i, phi in enumerate(self.inDoc.processHistory):
            self.assertEqual(phi,
                             procHist[i])
        # Test that this PreParser has been added to processHistory
        self.assertEqual(procHist[-1], self.testObj.id)


class UnicodeDecodePreParserTestCase(ImplementedPreParserTestCase):
    """Base Class for Cheshire3 UnicodeDecodePreParser Test Cases.
    
    A UnicodeDecodePreParser should accept a Document with content encoded in a
    non-unicode character encoding scheme and return a Document with the same 
    content decoded to Python's Unicode implementation.
    """
    
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
        "Check Document with Unicode content returns unaltered."
        uDoc = StringDocument(self.testUc)
        outDoc = self.testObj.process_document(self.session, uDoc)
        outDocContent = outDoc.get_raw(self.session)
        self.assertEqual(outDocContent,
                         self.testUc)
        
    def test_process_document_returnContent(self):
        "Check content of returned Document is unaltered aside from encoding."
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


class CmdLinePreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 CmdLinePreParser Unittests.
    
    A CmdLinePreParser should run a command in the native Operating System to
    preParse the Document.
    """
    
    @classmethod
    def _get_class(self):
        return CmdLinePreParser


class FileUtilPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 FileUtilPreParserTestCase Unittests.
    
    A FileUtilPreParserTestCase calls 'file' util to find out the current MIME
    type of file.
    """
    
    @classmethod
    def _get_class(self):
        return FileUtilPreParser


class MagicRedirectPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 MagicRedirectPreParser Unittests.

    A MagicRedirectPreParser maps to another appropriate PreParser based on
    the MIME type of the incoming Document.
    """

    @classmethod
    def _get_class(self):
        return MagicRedirectPreParser


class HtmlSmashPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 HtmlSmashPreParser Unittests.

    An HtmlSmashPreParser attempts to reduce HTML to its raw text.
    """

    @classmethod
    def _get_class(self):
        return HtmlSmashPreParser


class RegexpSmashPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 RegexpSmashPreParser Unittests.

    A RegexpSmashPreParser either strips, replaces or keeps only data which 
    matches a given regular expression.
    """
    
    @classmethod
    def _get_class(self):
        return RegexpSmashPreParser


class SgmlPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 SgmlPreParser Unittests.

    A SgmlPreParser converts SGML into XML.
    """

    @classmethod
    def _get_class(self):
        return SgmlPreParser


class AmpPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 AmpPreParser Unittests.

    An AmpPreParser escapes lone ampersands in otherwise XML text.
    """

    @classmethod
    def _get_class(self):
        return AmpPreParser


class MarcToXmlPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 MarcToXmlPreParser Unittests.
    
    A MarcToXmlPreParser converts MARC into MARCXML.
    """
    
    @classmethod
    def _get_class(self):
        return MarcToXmlPreParser


class MarcToSgmlPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 MarcToSgmlPreParser Unittests.
    
    A MarcToSgmlPreParser converts MARC into Cheshire2's MarcSgml.
    """
    
    @classmethod
    def _get_class(self):
        return MarcToSgmlPreParser


class TxtToXmlPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 TxtToXmlPreParser Unittests.
    
    A TxtToXmlPreParser minimally wrap text in <data> XML tags.
    """
    
    @classmethod
    def _get_class(self):
        return TxtToXmlPreParser


class PicklePreParserTestCase(ImplementedPreParserTestCase): 
    """Cheshire3 PicklePreParser Unittests.
     
    A PicklePreParser compresses Document content using Python pickle.
    """

    @classmethod
    def _get_class(self):
        return PicklePreParser

    
class UnpicklePreParserTestCase(ImplementedPreParserTestCase):
    """Chechire3 UnpicklePreParser Unittests.
    
    An UnpicklePreParser decompresses Document content using Python pickle.
    """
    
    @classmethod
    def _get_class(self):
        return UnpicklePreParser


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(PreParserTestCase)
    suite.addTests(ltc(Utf8UnicodeDecodePreParserTestCase))
    suite.addTests(ltc(AsciiUnicodeDecodePreParserTestCase))
    suite.addTests(ltc(Iso8859_1UnicodeDecodePreParserTestCase))
    suite.addTests(ltc(CmdLinePreParserTestCase))
    suite.addTests(ltc(FileUtilPreParserTestCase))
    suite.addTests(ltc(MagicRedirectPreParserTestCase))
    suite.addTests(ltc(HtmlSmashPreParserTestCase))
    suite.addTests(ltc(RegexpSmashPreParserTestCase))
    suite.addTests(ltc(SgmlPreParserTestCase))
    suite.addTests(ltc(AmpPreParserTestCase))
    suite.addTests(ltc(MarcToXmlPreParserTestCase))
    suite.addTests(ltc(MarcToSgmlPreParserTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
