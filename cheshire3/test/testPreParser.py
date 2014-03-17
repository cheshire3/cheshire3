u"""Cheshire3 PreParser Unittests.

PreParser configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and PreParser instances will
be instantiated using configurations defined within this testing module, 
and tests carried out on those instances using data defined in this module.
"""

import hashlib
import re
import sys

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    import cPickle as pickle
except ImportError:
    import pickle

from lxml import etree
from base64 import b64encode

from cheshire3.document import Document, StringDocument
from cheshire3.preParser import PreParser, UnicodeDecodePreParser, \
    CmdLinePreParser, FileUtilPreParser,\
    HtmlSmashPreParser, HtmlFixupPreParser, RegexpSmashPreParser,\
    SgmlPreParser, AmpPreParser, \
    MarcToXmlPreParser, MarcToSgmlPreParser, TxtToXmlPreParser,\
    PicklePreParser, UnpicklePreParser, \
    B64EncodePreParser, B64DecodePreParser,\
    LZ4CompressPreParser, LZ4DecompressPreParser,\
    CharacterEntityPreParser, DataChecksumPreParser
    
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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


class HtmlFixupPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 HtmlFixupPreParser Unittests.

    An HtmlFixupPreParser attempts to fix up HTML to make it complete and
    parseable XML.
    """

    @classmethod
    def _get_class(self):
        return HtmlFixupPreParser

    @classmethod
    def _get_testUnicode(self):
        return u'<body>A Document with an <img alt=image></body>'

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            u'<html><body>A Document with an <img alt="image"/></body></html>')


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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
          <objectType>{0.__module__}.{0.__name__}</objectType>
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
            'VGhpcyBpcyBteSBkb2N1bWVudA==',
            u"Returned document content not as expected")


class B64DecodePreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 B64EncodePreParser Unittests.
    
    A B64DecodePreParser decodes Document from Base64."""

    @classmethod
    def _get_class(self):
        return B64DecodePreParser

    @classmethod
    def _get_testUnicode(self):
        return u'VGhpcyBpcyBteSBkb2N1bWVudA=='

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            u'This is my document',
            u"Returned document content not as expected")


@unittest.skipIf(sys.platform.startswith("sunos"),
                 "variable LZ4 support on SunOS")
class LZ4CompressPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 LZ4CompressPreParser Unittests."""

    @classmethod
    def _get_class(self):
        return LZ4CompressPreParser

    @classmethod
    def _get_testUnicode(self):
        return u'red lorry, yellow lorry,' * 50

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            '\xb0\x04\x00\x00\xf3\x02red lorry, yellow\x0e\x00\x0f\x18\x00'
            '\xff\xff\xff\xff\x84Porry,',
            u"Returned document content not as expected")


@unittest.skipIf(sys.platform.startswith("sunos"),
                 "variable LZ4 support on SunOS")
class LZ4DecompressPreParserTestCase(ImplementedPreParserTestCase):
    """Cheshire3 LZ4DecompressPreParser Unittests."""

    @classmethod
    def _get_class(self):
        return LZ4DecompressPreParser

    @classmethod
    def _get_testUnicode(self):
        return ('\xb0\x04\x00\x00\xf3\x02red lorry, yellow\x0e\x00\x0f\x18\x00'
                '\xff\xff\xff\xff\x84Porry,')

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            u'red lorry, yellow lorry,' * 50,
            u"Returned document content not as expected")


class CharacterEntityPreParserTestCase(ImplementedPreParserTestCase):
    
    @classmethod
    def _get_class(self):
        return CharacterEntityPreParser

    @classmethod
    def _get_testUnicode(self):
        return (u'&apos; &hellip; &ldquo; &lsqb; &rsqb; &sol; '
                '&commat; &plus; &percnt; '
                '&nbsp; &iexcl; &cent; &pound; &curren; &yen; &brvbar; &sect; '
                '&uml; &copy; &ordf; &laquo; &not; &shy; &reg; &macr; &deg; '
                '&plusmn; &sup2; &sup3; &acute; &micro; &para; &middot; '
                '&cedil; &sup1; &ordm; &raquo; &frac14; &frac12; &frac34; '
                '&iquest; &Agrave; &Aacute; &Acirc; &Atilde; &Auml; &Aring; '
                '&AElig; &Ccedil; &Egrave; &Eacute; &Ecirc; &Euml; &Igrave; '
                '&Iacute; &Icirc; &Iuml; &ETH; &Ntilde; &Ograve; &Oacute; '
                '&Ocirc; &Otilde; &Ouml; &times; &Oslash; &Ugrave; &Uacute; '
                '&Ucirc; &Uuml; &Yacute; &THORN; &szlig; &agrave; &aacute; '
                '&acirc; &atilde; &auml; &aring; &aelig; &ccedil; &egrave; '
                '&eacute; &ecirc; &euml; &igrave; &iacute; &icirc; &iuml; '
                '&eth; &ntilde; &ograve; &oacute; &ocirc; &otilde; &ouml; '
                '&divide; &oslash; &ugrave; &uacute; &ucirc; &uuml; &yacute; '
                '&thorn; &yuml; '
                '&frac58; '
                '&123; ')

    def test_process_document_returnContent(self):
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(
            self.outDoc.text,
            (u"' ...  [ ] \\ @ + % "
             '&#160; &#161; &#162; &#163; &#164; &#165; &#166; &#167; &#168; '
             '&#169; &#170; &#171; &#172; &#173; &#174; &#175; &#176; &#177; '
             '&#178; &#179; &#180; &#181; &#182; &#183; &#184; &#185; &#186; '
             '&#187; &#188; &#189; &#190; &#191; &#192; &#193; &#194; &#195; '
             '&#196; &#197; &#198; &#199; &#200; &#201; &#202; &#203; &#204; '
             '&#205; &#206; &#207; &#208; &#209; &#210; &#211; &#212; &#213; '
             '&#214; &#215; &#216; &#217; &#218; &#219; &#220; &#221; &#222; '
             '&#223; &#224; &#225; &#226; &#227; &#228; &#229; &#230; &#231; '
             '&#232; &#233; &#234; &#235; &#236; &#237; &#238; &#239; &#240; '
             '&#241; &#242; &#243; &#244; &#245; &#246; &#247; &#248; &#249; '
             '&#250; &#251; &#252; &#253; &#254; &#255; '
             '5&#8260;8 '
             '&#123; ')
             )


class DataChecksumPreParserTestCase(ImplementedPreParserTestCase):

    @classmethod
    def _get_class(self):
        return DataChecksumPreParser

    @classmethod
    def _get_testUnicode(self):
        return u'This is my document'

    @classmethod
    def _get_checksumAlgorithm(self):
        return 'md5'

    def _get_config(self):
        return etree.XML('''
        <subConfig type="preParser" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <options>
            <setting type="sumType">{1}</setting>
          </options>
        </subConfig>
        '''.format(self._get_class(), self._get_checksumAlgorithm()))
            
    def test_process_document_returnContent(self):
        "Check Document data is unchanged."
        if self.inDoc is None:
            self.skipTest("No test Document available")
        self.assertEqual(self.outDoc.text, self._get_testUnicode())

    def test_process_document_metadata(self):
        "Check Document metadata."
        # Check Document.metadata['checksum'] exists
        alg = self._get_checksumAlgorithm()
        self.assertTrue(
            self.outDoc.metadata,
            "No items in returned Document metadata")
        self.assertTrue(
            'checksum' in self.outDoc.metadata,
            "No checksum items in returned Document metadata")
        # Check Document.metadata['checksum'][alg] exists
        self.assertTrue(
            alg in self.outDoc.metadata['checksum'],
            "{0} checksum not in returned Document metadata".format(alg))
        # Check Document.metadata[algorithm][alg] has correct value
        h = hashlib.new(alg)
        h.update(self._get_testUnicode())
        self.assertEqual(
            self.outDoc.metadata['checksum'][alg]['hexdigest'],
            h.hexdigest(),
            "incorrect {0} checksum in Document metadata".format(alg))


class SHA1DataChecksumPreParserTestCase(DataChecksumPreParserTestCase):

    @classmethod
    def _get_checksumAlgorithm(self):
        return 'sha1'


class SHA256DataChecksumPreParserTestCase(DataChecksumPreParserTestCase):

    @classmethod
    def _get_checksumAlgorithm(self):
        return 'sha256'


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
    suite.addTests(ltc(HtmlFixupPreParserTestCase))
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
    suite.addTests(ltc(LZ4CompressPreParserTestCase))
    suite.addTests(ltc(LZ4DecompressPreParserTestCase))
    suite.addTests(ltc(CharacterEntityPreParserTestCase))
    suite.addTests(ltc(DataChecksumPreParserTestCase))
    suite.addTests(ltc(SHA1DataChecksumPreParserTestCase))
    suite.addTests(ltc(SHA256DataChecksumPreParserTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
