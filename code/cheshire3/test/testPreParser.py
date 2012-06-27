from base64 import b64encode
u"""Cheshire3 PreParser Unittests.

PreParser configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and PreParser instances will
be instantiated using configurations defined within this testing module, 
and tests carried out on those instances using data defined in this module.
"""

import binascii
import re

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    import cPickle as pickle
except ImportError:
    import pickle

from lxml import etree

from cheshire3.document import Document, StringDocument
from cheshire3.preParser import PreParser, UnicodeDecodePreParser, \
    CmdLinePreParser, FileUtilPreParser, MagicRedirectPreParser, \
    HtmlSmashPreParser, RegexpSmashPreParser, SgmlPreParser, AmpPreParser, \
    MarcToXmlPreParser, MarcToSgmlPreParser, TxtToXmlPreParser,\
    PicklePreParser, UnpicklePreParser, \
    B64EncodePreParser, B64DecodePreParser
    
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
        self.longMessage = True
        
    def tearDown(self):
        pass

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
    inDoc = None
    outDoc = None
    
    @classmethod
    def _get_class(self):
        raise NotImplementedError
    
    @classmethod
    def _get_testUnicode(self):
        return u'This is my document'

    def setUp(self):
        PreParserTestCase.setUp(self)
        self.testUc = self._get_testUnicode()
        if self.testUc:
            self.inDoc = StringDocument(self.testUc)
            self.outDoc = self.testObj.process_document(self.session, 
                                                        self.inDoc)

    def test_process_document_returnType(self):
        "Check that PreParser returns a Document."
        if self.inDoc is None:
            self.skipTest("No test Document available") 
        self.assertIsInstance(self.outDoc, Document)
    
    def test_process_document_returnProcessHistory(self):
        "Check processHistory of returned Document."
        if self.inDoc is None:
            self.skipTest("No test Document available")
        # Test for presence of process history
        procHist = self.outDoc.processHistory
        self.assertIsInstance(procHist, list,
                              u"processHistory is not a list")
        # Test that previous process history has been copied correctly
        for i, phi in enumerate(self.inDoc.processHistory):
            self.assertEqual(phi,
                             procHist[i],
                             u"processHistory missing historic item(s)")
        # Test that processHistory contains at least one item
        self.assertGreaterEqual(len(procHist), 1,
                                u"processHistory contains no items")
        # Test that this PreParser has been added to processHistory
        self.assertEqual(procHist[-1], self.testObj.id,
                         u"processHistory does not contain PreParser")


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
        self.testUc = self._get_testUnicode()
        self.inDoc = StringDocument(self.testUc.encode(self._get_codec()))
        self.outDoc = self.testObj.process_document(self.session, self.inDoc)

    def test_unicode_content(self):
        "Check Document with Unicode content returns unaltered."
        if not self.testUc:
            self.skipTest("No test Unicode available")
        uDoc = StringDocument(self.testUc)
        outDoc = self.testObj.process_document(self.session, uDoc)
        outDocContent = outDoc.get_raw(self.session)
        self.assertEqual(outDocContent,
                         self.testUc)
        
    def test_process_document_returnContent(self):
        "Check content of returned Document is unaltered aside from encoding."
        if self.inDoc is None:
            self.skipTest("No test Document available")
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

    @classmethod
    def _get_config(self):
        return etree.XML('''
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <paths>
    <path type="executable">cat</path>
  </paths>
</subConfig>
'''.format(self._get_class()))

    def test_process_document_returnContent(self):
        "Check content of returned Document (should be unaltered)."
        self.assertEqual(self.outDoc.get_raw(self.session),
                         self.inDoc.get_raw(self.session),
                         u"Returned document content not as expected")


class CmdLinePreParserInDocTestCase(CmdLinePreParserTestCase):
    """Cheshire3 CmdLinePreParser with %INDOC% Unittests.
    
    A CmdLinePreParser should run a command in the native Operating System to
    preParse the Document. In this case, test a command that requires an 
    incoming file.
    """
    
    @classmethod
    def _get_config(self):
        return etree.XML('''
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <paths>
    <path type="executable">cat</path>
  </paths>
  <options>
    <setting type="commandLine">%INDOC%</setting>
  </options>
</subConfig>
'''.format(self._get_class()))


class CmdLinePreParserInOutDocTestCase(CmdLinePreParserTestCase):
    """Cheshire3 CmdLinePreParser with %INDOC% Unittests.
    
    A CmdLinePreParser should run a command in the native Operating System to
    preParse the Document. In this case, test a command that requires an 
    incoming file.
    """
    
    @classmethod
    def _get_config(self):
        return etree.XML('''
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <paths>
    <path type="executable">cat</path>
  </paths>
  <options>
    <setting type="commandLine">%INDOC% > %OUTDOC%</setting>
  </options>
</subConfig>
'''.format(self._get_class()))


class FileUtilPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 FileUtilPreParserTestCase Unittests.
    
    A FileUtilPreParserTestCase calls 'file' util to find out the current MIME
    type of file.
    """
    
    @classmethod
    def _get_class(self):
        return FileUtilPreParser


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
    
    @classmethod
    def _get_config(self):
        return etree.XML('''
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <options>
    <setting type="regexp"> </setting>
    <setting type="char"> </setting>
  </options>
</subConfig>
'''.format(self._get_class()))

    def test_process_document_returnContent(self):
        "Check content of returned Document (should be unaltered)."
        self.assertEqual(self.outDoc.get_raw(self.session),
                         self.inDoc.get_raw(self.session))


class RegexpSmashPreParserStripTestCase(RegexpSmashPreParserTestCase):
    """Cheshire3 RegexpSmashPreParser Unittests.

    A RegexpSmashPreParser either strips, replaces or keeps only data which 
    matches a given regular expression.
    
    This test case tests stripping a match.
    """

    @classmethod
    def _get_config(self):
        return etree.XML('''
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <options>
    <setting type="regexp">\sis</setting>
  </options>
</subConfig>
'''.format(self._get_class()))

    def test_process_document_returnContent(self):
        "Check content of returned Document (should lack 'is')."
        self.assertEqual(self.outDoc.get_raw(self.session),
                         re.sub('\sis', '', self.testUc),
                         u"Returned document content not as expected")


class RegexpSmashPreParserSubTestCase(RegexpSmashPreParserTestCase):
    """Cheshire3 RegexpSmashPreParser Unittests.

    A RegexpSmashPreParser either strips, replaces or keeps only data which 
    matches a given regular expression.
    
    This test case tests substituting a match.
    """

    @classmethod
    def _get_config(self):
        return etree.XML('''
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <options>
    <setting type="regexp">my</setting>
    <setting type="char">your</setting>
  </options>
</subConfig>
'''.format(self._get_class()))

    def test_process_document_returnContent(self):
        "Check content of returned Document ('my' -> 'your')."
        self.assertEqual(self.outDoc.get_raw(self.session),
                         re.sub('my', 'your', self.testUc),
                         u"Returned document content not as expected")


class RegexpSmashPreParserKeepTestCase(RegexpSmashPreParserTestCase):
    """Cheshire3 RegexpSmashPreParser Unittests.

    A RegexpSmashPreParser either strips, replaces or keeps only data which 
    matches a given regular expression.
    
    This test case tests keeping only a match.
    """

    @classmethod
    def _get_config(self):
        return etree.XML('''
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <options>
    <setting type="regexp">document</setting>
    <setting type="keep">1</setting>
    
  </options>
</subConfig>
'''.format(self._get_class()))

    def test_process_document_returnContent(self):
        "Check content of returned Document ('my' -> 'your')."
        self.assertEqual(self.outDoc.get_raw(self.session),
                         u''.join(re.findall('document', self.testUc)),
                         u"Returned document content not as expected")


class SgmlPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 SgmlPreParser Unittests.

    A SgmlPreParser converts SGML into XML.
    """

    @classmethod
    def _get_class(self):
        return SgmlPreParser

    @classmethod
    def _get_config(self):
        return etree.XML('''
<subConfig type="preParser" id="{0.__name__}">
  <objectType>cheshire3.preParser.{0.__name__}</objectType>
  <options>
    <setting type="emptyElements">img</setting>
  </options>
</subConfig>
'''.format(self._get_class()))

    @classmethod
    def _get_testUnicode(self):
        return u'<html>A Document with an <img alt=image></html>'

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            u'<html>A Document with an <img alt="image"/></html>')


class AmpPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 AmpPreParser Unittests.

    An AmpPreParser escapes lone ampersands in otherwise XML text.
    """

    @classmethod
    def _get_class(self):
        return AmpPreParser

    @classmethod
    def _get_testUnicode(self):
        return u'<html>tom&jerry & &amp;</html>'

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            u'<html>tom&amp;jerry &amp; &amp;</html>',
            u"Returned document content not as expected")


class MarcToXmlPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 MarcToXmlPreParser Unittests.
    
    A MarcToXmlPreParser converts MARC into MARCXML.
    """
    
    @classmethod
    def _get_class(self):
        return MarcToXmlPreParser

    @classmethod
    def _get_testUnicode(self):
        return u''


class MarcToSgmlPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 MarcToSgmlPreParser Unittests.
    
    A MarcToSgmlPreParser converts MARC into Cheshire2's MarcSgml.
    """
    
    @classmethod
    def _get_class(self):
        return MarcToSgmlPreParser

    @classmethod
    def _get_testUnicode(self):
        return u''


class TxtToXmlPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 TxtToXmlPreParser Unittests.
    
    A TxtToXmlPreParser minimally wraps text in <data> XML tags.
    """
    
    @classmethod
    def _get_class(self):
        return TxtToXmlPreParser

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            u'<data>{0}</data>'.format(self.testUc),
            u"Returned document content not as expected")


class PicklePreParserTestCase(ImplementedPreParserTestCase): 
    """Cheshire3 PicklePreParser Unittests.
     
    A PicklePreParser compresses Document content using Python pickle.
    """

    @classmethod
    def _get_class(self):
        return PicklePreParser
    
    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            pickle.dumps(self.testUc),
            u"Returned document content not as expected")

    
class UnpicklePreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 UnpicklePreParser Unittests.
    
    An UnpicklePreParser decompresses Document content using Python pickle.
    """
    
    @classmethod
    def _get_class(self):
        return UnpicklePreParser
    
    @classmethod
    def _get_testUnicode(self):
        # Keep method name, despite this PreParser requiring byte string
        # instead of unicode
        return 'VThis is my document\np0\n.'

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            pickle.loads(self.testUc),
            u"Returned document content not as expected")


class B64EncodePreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 B64EncodePreParser Unittests.

    A B64EncodePreParser encodes document in Base64."""

    @classmethod
    def _get_class(self):
        return B64EncodePreParser

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            'N\x18\xac\x8a\xc9\xb2v\x87.\x99\xe9\xed',
            u"Returned document content not as expected")


class B64DecodePreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 B64EncodePreParser Unittests.
    
    A B64DecodePreParser decodes Document from Base64."""

    @classmethod
    def _get_class(self):
        return B64DecodePreParser

    @classmethod
    def _get_testUnicode(self):
        return 'N\x18\xac\x8a\xc9\xb2v\x87.\x99\xe9\xed'

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            u'This is my document',
            u"Returned document content not as expected")


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(PreParserTestCase)
    suite.addTests(ltc(Utf8UnicodeDecodePreParserTestCase))
    suite.addTests(ltc(AsciiUnicodeDecodePreParserTestCase))
    suite.addTests(ltc(Iso8859_1UnicodeDecodePreParserTestCase))
    suite.addTests(ltc(CmdLinePreParserTestCase))
    suite.addTests(ltc(CmdLinePreParserInDocTestCase))
    suite.addTests(ltc(CmdLinePreParserInOutDocTestCase))
    suite.addTests(ltc(FileUtilPreParserTestCase))
    suite.addTests(ltc(HtmlSmashPreParserTestCase))
    suite.addTests(ltc(RegexpSmashPreParserTestCase))
    suite.addTests(ltc(RegexpSmashPreParserStripTestCase))
    suite.addTests(ltc(RegexpSmashPreParserSubTestCase))
    suite.addTests(ltc(RegexpSmashPreParserKeepTestCase))
    suite.addTests(ltc(SgmlPreParserTestCase))
    suite.addTests(ltc(AmpPreParserTestCase))
    suite.addTests(ltc(MarcToXmlPreParserTestCase))
    suite.addTests(ltc(MarcToSgmlPreParserTestCase))
    suite.addTests(ltc(TxtToXmlPreParserTestCase))
    suite.addTests(ltc(PicklePreParserTestCase))
    suite.addTests(ltc(UnpicklePreParserTestCase))
    suite.addTests(ltc(B64EncodePreParserTestCase))
    suite.addTests(ltc(B64DecodePreParserTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
