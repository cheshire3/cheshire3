u"""Cheshire3 Normalizer Unittests.

Normalizer configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Normalizer instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import string

from tempfile import mkstemp
from lxml import etree
from datetime import datetime

try:
    from pyuca import Collator
except ImportError:
    hasPyuca = False
else:
    hasPyuca = True

from cheshire3.normalizer import Normalizer, SimpleNormalizer, \
    DataExistsNormalizer, TermExistsNormalizer, CaseNormalizer, \
    ReverseNormalizer, SpaceNormalizer, ArticleNormalizer,\
    NumericEntityNormalizer, RegexpNormalizer, NamedRegexpNormalizer,\
    IntNormalizer, StringIntNormalizer,\
    StoplistNormalizer, TokenExpansionNormalizer,\
    RegexpFilterNormalizer, PossessiveNormalizer, FileAssistedNormalizer,\
    StemNormalizer, PhoneticNormalizer,\
    DateStringNormalizer, DateYearNormalizer,\
    IdToFilenameNormalizer, FilenameToIdNormalizer,\
    UnicodeCollationNormalizer, DiacriticNormalizer

from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class NormalizerTestCase(Cheshire3ObjectTestCase):
    """Base Class for Cheshire3 Normalizer Test Cases."""
    
    @classmethod
    def _get_class(cls):
        return Normalizer
    
    def _get_process_string_tests(self):
        # Return a list of 2-string tuples containing test pairs:
        # (string to be normalized, expected result)
        return []
    
    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        for instring, expected in self.process_string_tests:
            if expected is not None and expected:
                yield ({instring: {'text': instring, 
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   'proxLoc': [-1]
                                   }
                       },
                       {expected: {'text': expected,
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   'proxLoc': [-1]
                                   }
                        })
        
    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        self.process_string_tests = self._get_process_string_tests()
        self.process_hash_tests = self._get_process_hash_tests()
        
    def tearDown(self):
        pass
        
    def test_process_string(self):
        "Test output of process_string."
        if not self.process_string_tests:
            self.skipTest("No test data defined")
        for instring, expected in self.process_string_tests:
            output = self.testObj.process_string(self.session, instring) 
            self.assertEqual(output, expected,
                             u"'{0}' != '{1}' when normalizing '{2}'".format(
                                                                  output,
                                                                  expected,
                                                                  instring)
                             )
    
    def test_process_hash(self):
        "Test output of process_hash"
        if not self.process_hash_tests:
            self.skipTest("No test data defined")
        for inhash, expected in self.process_hash_tests:
            output = self.testObj.process_hash(self.session, inhash)
            self.assertDictEqual(output, expected)
    

class SimpleNormalizerTestCase(NormalizerTestCase):
    u"""Test Case for SimpleNormalizer (base class for Normalizers that should
    not change the data in any way). 
    """

    @classmethod
    def _get_class(cls):
        return SimpleNormalizer

    def _get_config(self):    
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
          <objectType>cheshire3.normalizer.{0.__name__}</objectType>
        </subConfig>'''.format(self._get_class()))
    
    def _get_process_string_tests(self):
        return [
            (string.uppercase, string.uppercase),
            (string.lowercase, string.lowercase),
            (string.punctuation, string.punctuation)]


class DataExistsNormalizerTestCase(SimpleNormalizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return DataExistsNormalizer

    def _get_process_string_tests(self):
        return [
            (string.uppercase, "1"),
            (string.lowercase, "1"),
            (string.punctuation, "1"),
            ("", "0")]

    def _get_process_hash_tests(self):
        return [
            ({"foo": {"text": "foo", "occurences": 1},
              "bar": {"text": "bar", "occurences": 2},
              "": {"text": "", "occurences": 10}
             },
             {"1": {"text": "1", "occurences": 3},
              "0": {"text": "0", "occurences": 10}
              })]
        
        
class TermExistsNormalizerTestCase(SimpleNormalizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return TermExistsNormalizer

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <options>
                <setting type="termlist">foo bar</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [
            ('foo', "1"),
            ('bar', "1"),
            ('baz', "0")
        ]

    def _get_process_hash_tests(self):
        return [
            ({
                "foo": {"text": "foo", "occurences": 1},
                "bar": {"text": "bar", "occurences": 2},
                "baz": {"text": "baz", "occurences": 10}
             },
             "2")
        ]

    def test_process_hash(self):
        if not self.process_hash_tests:
            self.skipTest("No test data defined")
        for inhash, expected in self.process_hash_tests:
            output = self.testObj.process_hash(self.session, inhash)
            self.assertEqual(output, expected)
            
        
class TermExistsNormalizerFreqTestCase(TermExistsNormalizerTestCase):

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <options>
                <setting type="termlist">foo bar</setting>
                <setting type="frequency">1</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [
            ('foo', "1"),
            ('bar', "1"),
            ('baz', "0")]

    def _get_process_hash_tests(self):
        return[
            ({
                "foo": {"text": "foo", "occurences": 1},
                "bar": {"text": "bar", "occurences": 2},
                "baz": {"text": "baz", "occurences": 10}
             },
             "3")
        ]
        

class CaseNormalizerTestCase(SimpleNormalizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return CaseNormalizer
    
    def _get_process_string_tests(self):
        return [
            ("FooBar", "foobar"),
            (string.uppercase, string.lowercase),
            (string.lowercase, string.lowercase),
            (string.punctuation, string.punctuation)
        ]

    def _get_process_hash_tests(self):
        return [
            ({
                "foo": {"text": "foo", "occurences": 1},
                "Foo": {"text": "Foo", "occurences": 1},
                "FOO": {"text": "FOO", "occurences": 1},
                "BaR": {"text": "BaR", "occurences": 2},
                "bAz": {"text": "bAz", "occurences": 10}
             },
             {
                "foo": {"text": "foo", "occurences": 3},
                "bar": {"text": "bar", "occurences": 2},
                "baz": {"text": "baz", "occurences": 10}
             })
        ]


class ReverseNormalizerTestCase(SimpleNormalizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return ReverseNormalizer

    def _get_process_string_tests(self):
        return [
            ("foo", "oof"),
            ("Hello World!", "!dlroW olleH"),
            ("madam", "madam"),
            ("A", "A")
        ]


class SpaceNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return SpaceNormalizer

    def _get_process_string_tests(self):
        return [
            ("This  is a       spacey sentence.",
             "This is a spacey sentence."),
            ("Spam\t&\teggs", "Spam & eggs"),
            ("some\nnew\nlines", "some new lines"),
            ("""
            This
            
            is starting
            
            
            to get
            
            
            
            silly!
            """,
            "This is starting to get silly!"
            )
        ]


class ArticleNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return ArticleNormalizer

    def _get_process_string_tests(self):
        return [("The spam", "spam"),
                ("the spam", "spam"),
                ("An egg", "egg"),
                ("an egg", "egg"),
                ("A chip", "chip"),
                ("a chip", "chip")]


class NumericEntityNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return NumericEntityNormalizer

    def _get_process_string_tests(self):
        return [(u'\xa3', "&#163;"),   # GBP sign
                (u'\xa9', "&#169;"),   # Copyright
                (u'\xe9', "&#233;"),   # Lower-case e with acute accent
                (u'\xe6', "&#230;"),   # Lower case ae dipthong
                ]


class RegexpNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return RegexpNormalizer


class RegexpNormalizerStripTestCase(RegexpNormalizerTestCase):

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <options>
                <setting type="regexp">(?i)spam\\w*</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [("spam", ""),
                ("Some spam email", "Some  email"),  # N.B. double space
                ("Spammage", ""),
                ("Eggs", "Eggs")]


class RegexpNormalizerSubTestCase(RegexpNormalizerTestCase):

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <docs>Replace all words (alpha only) with "spam"</docs>
            <options>
                <setting type="regexp">\\b[a-zA-Z]+?\\b</setting>
                <setting type="char">spam</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [("word", "spam"),
                ("Some spam email", "spam spam spam"),
                ("testing 1 2 3", "spam 1 2 3"),
                ("Cheshire3", "Cheshire3")]


class RegexpNormalizerKeepTestCase(RegexpNormalizerTestCase):

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <options>
                <setting type="regexp">(?i)spam\w*</setting>
                <setting type="keep">1</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [("spam", "spam"),
                ("Some spam email", "spam"),
                ("Spammage", "Spammage"),
                ("Eggs", "")]


class NamedRegexpNormalizerTestCase(SimpleNormalizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return NamedRegexpNormalizer

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
          <objectType>cheshire3.normalizer.{0.__name__}</objectType>
          <options>
            <setting type="regexp">(?i)(?P&lt;spamword&gt;spam\\w*)</setting>
            <setting type="template">--%(spamword)s--</setting>
          </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [("spam", "--spam--"),
                ("Spammage", "--Spammage--"),
                ("Eggs", "")]


class RegexpFilterKeepNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return RegexpFilterNormalizer

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <options>
                <setting type="regexp">(?i)spam\\w*?</setting>
                <setting type="keep">1</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [("spam", "spam"),
                ("Some spam email", None),
                ("Spammage", "Spammage"),
                ("Eggs", None)]


class RegexpFilterStripNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return RegexpFilterNormalizer

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <options>
                <setting type="regexp">(?i)spam\\w*?</setting>
                <setting type="keep">0</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [("spam", None),
                ("Some spam email", "Some spam email"),
                ("Spammage", None),
                ("Eggs", "Eggs")]


class PossessiveNormalizerTestCase(SimpleNormalizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return PossessiveNormalizer

    def _get_process_string_tests(self):
        return [("man's", "man"),           # singular possessive
                ("soldiers'", "soldiers"),  # plural possessive
                ("women's", "women")]       # irregular plural possessive


class IntNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return IntNormalizer

    def _get_process_string_tests(self):
        return [("1", 1),
                ("0000000000009", 9),
                ("123321", 123321)]


class StringIntNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return StringIntNormalizer

    def _get_process_string_tests(self):
        return [(1, "000000000001"),
                (9, "000000000009"),
                (123321, "000000123321"),
                ("spam", None)]


class FileAssistedNormalizerTestCase(SimpleNormalizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return FileAssistedNormalizer
    
    def _get_fileLines(self):
        return []

    def setUp(self):
        # Create a tempfile for the file assisted part
        fileid, self.path = mkstemp(text=True)
        with open(self.path, 'w') as fh:
            for line in self._get_fileLines():
                fh.write(line + '\n')
        SimpleNormalizerTestCase.setUp(self)
        
    def tearDown(self):
        SimpleNormalizerTestCase.tearDown(self)
        # Remove tempfile
        os.remove(self.path)


class StoplistNormalizerTestCase(FileAssistedNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return StoplistNormalizer

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <paths>
                <path type="stoplist">{1}</path>
            </paths>
        </subConfig>'''.format(self._get_class(), self.path))

    def _get_fileLines(self):
        return ["spam",
                "eggs"]

    def _get_process_string_tests(self):
        return [("spam", None),
                ("eggs", None),
                ("ham", "ham"),
                ("chips", "chips")]


class TokenExpansionNormalizerTestCase(FileAssistedNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return TokenExpansionNormalizer

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <paths>
                <path type="expansions">{1}</path>
            </paths>
            <options>
                <setting type="keepOriginal">1</setting>
            </options>
        </subConfig>'''.format(self._get_class(), self.path))

    def _get_fileLines(self):
        return ["UK United Kingdom",
                "USA United States of America",
                "WWF World Wildlife Fund"]

    def _get_process_string_tests(self):
        return [l.split(' ', 1) for l in self._get_fileLines()]

    def _get_process_hash_tests(self):
        # Check returned hash keeps original token
        return [
            ({'UK': {'text': 'UK'}},
             {'UK': {'text': 'UK'},
              'United': {'text': 'United'},
              'Kingdom': {'text': 'Kingdom'}}
             )]


class EnglishStemNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return StemNormalizer

    def _get_config(self):
        return etree.XML('''
        <subConfig type="normalizer" id="EnglishStemNormalizer">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <options>
                <setting type="language">english</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [('nurse', 'nurs'),
                ('nurses', 'nurs'),
                ('nursing', 'nurs'),
                ('nursery', 'nurseri')
                ]


class PhoneticNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return PhoneticNormalizer

    def _get_process_string_tests(self):
        return [('bacon', 'b25'),
                ('egg', 'e2'),
                ('sausage', 's22'),
                ('spam', 's15'),
                ('antidisestablishmentarianism', 'a5332231425536525')]

    def test_process_string_resultTermSizes(self):
        maxLen = self.testObj.get_setting(self.session, 'termSize')
        if not maxLen:
            self.skipTest("No termSize setting on object configuration")
        for instring, expected in self.process_string_tests:
            output = self.testObj.process_string(self.session, instring)
            self.assertLessEqual(len(output), maxLen)


class FivePhoneticNormalizerTestCase(PhoneticNormalizerTestCase):

    def _get_config(self):
        return etree.XML('''
         <subConfig type="normalizer" id="PhoneticNormalizer">
            <objectType>cheshire3.normalizer.{0.__name__}</objectType>
            <options>
                <setting type="termSize">5</setting>
            </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [('bacon', 'b2500'),
                ('egg', 'e2000'),
                ('sausage', 's2200'),
                ('spam', 's1500'),
                ('antidisestablishmentarianism',
                 'a5332')]


class DateStringNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return DateStringNormalizer

    def _get_process_string_tests(self):
        return [(datetime.utcfromtimestamp(0), '1970-01-01 00:00:00'),
                (datetime(2000, 01, 01, 12, 04, 55), '2000-01-01 12:04:55'),
                (datetime(2050, 01, 01), '2050-01-01 00:00:00'),
                ]


class DateYearNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return DateYearNormalizer
    
    def _get_process_string_tests(self):
        return [('1970-01-01 00:00:00', '1970'),
                ('2000-01-01 12:04:55', '2000'),
                ('2050-01-01 00:00:00', '2050'),
                ]


class IdToFilenameNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return IdToFilenameNormalizer

    def _get_process_string_tests(self):
        return [('foo', 'foo.xml'),
                ('bar', 'bar.xml'),
                ('baz', 'baz.xml'),
                ]


class TxtIdToFilenameNormalizerTestCase(IdToFilenameNormalizerTestCase):

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="normalizer" id="{0.__name__}">
          <objectType>cheshire3.normalizer.{0.__name__}</objectType>
          <options>
            <setting type="extension">.txt</setting>
          </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [('foo', 'foo.txt'),
                ('bar', 'bar.txt'),
                ('baz', 'baz.txt'),
                ]


class FilenameToIdNormalizerTestCase(SimpleNormalizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return FilenameToIdNormalizer

    def _get_process_string_tests(self):
        return [('foo.xml', 'foo'),
                ('bar.txt', 'bar'),
                ('baz.pdf', 'baz'),
                ]


class UnicodeCollationNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return UnicodeCollationNormalizer

    def _get_process_string_tests(self):
        return [('foo', ''),
                ('bar', ''),
                ('baz', '')]

    def setUp(self):
        if hasPyuca:
            SimpleNormalizerTestCase.setUp(self)

    @unittest.skipUnless(hasPyuca, "pyuca module unavailable")
    def test_serverInstance(self):
        SimpleNormalizerTestCase.test_serverInstance(self)

    @unittest.skipUnless(hasPyuca, "pyuca module unavailable")
    def test_instance(self):
        SimpleNormalizerTestCase.test_instance(self)

    @unittest.skipUnless(hasPyuca, "pyuca module unavailable")
    def test_process_string(self):
        SimpleNormalizerTestCase.test_process_string(self)

    @unittest.skipUnless(hasPyuca, "pyuca module unavailable")
    def test_process_hash(self):
        SimpleNormalizerTestCase.test_process_hash(self)
        

class DiacriticNormalizerTestCase(SimpleNormalizerTestCase):

    @classmethod
    def _get_class(cls):
        return DiacriticNormalizer

    def _get_process_string_tests(self):
        tests = []
        tests.append((unichr(167), 'Section'))
        tests.extend([(unichr(x), 'A') for x in range(192, 198)])
        tests.append((unichr(198), 'AE'))
        tests.append((unichr(199), 'C'))
        tests.extend([(unichr(x), 'E') for x in range(200, 204)])
        tests.extend([(unichr(x), 'I') for x in range(204, 208)])
        tests.append((unichr(208), 'D'))
        tests.append((unichr(209), 'N'))
        tests.extend([(unichr(x), 'O') for x in range(210, 215)])
        tests.append((unichr(215), 'x'))
        tests.append((unichr(216), 'O'))
        tests.extend([(unichr(x), 'U') for x in range(217, 221)])
        tests.append((unichr(221), 'Y'))
        tests.append((unichr(222), 'TH'))
        tests.append((unichr(223), 'ss'))
        tests.extend([(unichr(x), 'a') for x in range(224, 230)])
        tests.append((unichr(230), 'ae'))
        tests.append((unichr(231), 'c'))
        tests.extend([(unichr(x), 'e') for x in range(232, 236)])
        tests.extend([(unichr(x), 'i') for x in range(236, 240)])
        tests.append((unichr(240), 'd'))
        tests.append((unichr(241), 'n'))
        tests.extend([(unichr(x), 'o') for x in range(242, 247)])
        tests.append((unichr(248), 'o'))
        tests.extend([(unichr(x), 'u') for x in range(249, 253)])
        # There are many more, but these common ones should suffice for now
        return tests


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(SimpleNormalizerTestCase)
    suite.addTests(ltc(DataExistsNormalizerTestCase))
    suite.addTests(ltc(TermExistsNormalizerTestCase))
    suite.addTests(ltc(TermExistsNormalizerFreqTestCase))
    suite.addTests(ltc(CaseNormalizerTestCase))
    suite.addTests(ltc(ReverseNormalizerTestCase))
    suite.addTests(ltc(SpaceNormalizerTestCase))
    suite.addTests(ltc(ArticleNormalizerTestCase))
    suite.addTests(ltc(NumericEntityNormalizerTestCase))
    suite.addTests(ltc(RegexpNormalizerStripTestCase))
    suite.addTests(ltc(RegexpNormalizerSubTestCase))
    suite.addTests(ltc(RegexpNormalizerKeepTestCase))
    suite.addTests(ltc(NamedRegexpNormalizerTestCase))
    suite.addTests(ltc(RegexpFilterKeepNormalizerTestCase))
    suite.addTests(ltc(RegexpFilterStripNormalizerTestCase))
    suite.addTests(ltc(PossessiveNormalizerTestCase))
    suite.addTests(ltc(IntNormalizerTestCase))
    suite.addTests(ltc(StringIntNormalizerTestCase))
    suite.addTests(ltc(StoplistNormalizerTestCase))
    suite.addTests(ltc(TokenExpansionNormalizerTestCase))
    suite.addTests(ltc(EnglishStemNormalizerTestCase))
    suite.addTests(ltc(PhoneticNormalizerTestCase))
    suite.addTests(ltc(FivePhoneticNormalizerTestCase))
    suite.addTests(ltc(DateStringNormalizerTestCase))
    suite.addTests(ltc(DateYearNormalizerTestCase))
    suite.addTests(ltc(IdToFilenameNormalizerTestCase))
    suite.addTests(ltc(TxtIdToFilenameNormalizerTestCase))
    suite.addTests(ltc(FilenameToIdNormalizerTestCase))
    suite.addTests(ltc(UnicodeCollationNormalizerTestCase))
    suite.addTests(ltc(DiacriticNormalizerTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
