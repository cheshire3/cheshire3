u"""Cheshire3 Tokenizer Unittests.

Tokenizer configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Tokenzer instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree
from xml.sax.saxutils import escape
from datetime import datetime

from cheshire3.tokenizer import Tokenizer, SimpleTokenizer,\
    RegexpSubTokenizer, RegexpFindTokenizer, RegexpSplitTokenizer,\
    RegexpFindOffsetTokenizer, RegexpFindPunctuationOffsetTokenizer,\
    SentenceTokenizer, DateTokenizer, DateRangeTokenizer, PythonTokenizer
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class TokenizerTestCase(Cheshire3ObjectTestCase):

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenizer" id="{0.__name__}">
            <objectType>{0.__module__}.{0.__name__}</objectType>
        </subConfig>
        '''.format(self._get_class()))

    def _get_process_string_tests(self):
        # Return a list of tuples containing test pairs:
        # (string to be tokenized, expected tokens list)
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
                       {instring: {'text': expected,
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   'proxLoc': [-1]
                                   }
                        })

    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        self.process_string_tests = self._get_process_string_tests()
        self.process_hash_tests = self._get_process_hash_tests()

    def test_process_string(self):
        "Check that process_string returns the expected tokens."
        if not self.process_string_tests:
            self.skipTest("No test data defined")
        for instring, expected in self.process_string_tests:
            output = self.testObj.process_string(self.session, instring)
            self.assertIsInstance(output, list)
            for outToken, expToken in zip(output, expected):
                self.assertEqual(outToken, expToken,
                    u"'{0}' != '{1}' when tokenizing '{2}'".format(output,
                                                                   expected,
                                                                   instring)
                )

    def test_process_hash(self):
        "Check that process_hash returns expected hash."
        if not self.process_hash_tests:
            self.skipTest("No test data defined")
        for inhash, expected in self.process_hash_tests:
            output = self.testObj.process_hash(self.session, inhash)
            self.assertDictEqual(output, expected)


class OffsetTokenizerTestCase(TokenizerTestCase):
    "Abstract Base Class for testing Tokenizers that return (tokens, offsets)."
    
    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        for instring, (expTokens, expOffsets) in self.process_string_tests:
            if expTokens:
                # Filter out empty tokens
                toks = [et for et in expTokens if et]
                # Truncate offsets
                offs = expOffsets[:len(toks)]
                yield ({instring: {'text': instring, 
                                   'occurences': 1, 
                                   'positions': [0, 0, 0], 
                                   'proxLoc': [-1]
                                   }
                       },
                       {instring: {'text': toks,
                                   'occurences': 1,
                                   'positions': [0, 0, 0],
                                   'charOffsets': offs,
                                   'proxLoc': [-1]
                                   }
                        })

    def test_process_string(self):
        "Check that process_string returns the expected tokens and offsets."
        if not self.process_string_tests:
            self.skipTest("No test data defined")
        for instring, (expTokens, expOffsets) in self.process_string_tests:
            outTokens, outOffsets = self.testObj.process_string(self.session,
                                                                instring)
            self.assertIsInstance(outTokens, list)
            self.assertEqual(
                outTokens,
                expTokens,
                u"'{0}' != '{1}' when tokenizing '{2}'".format(outTokens,
                                                                   expTokens,
                                                                   instring)
            )
            self.assertIsInstance(outOffsets, list)
            self.assertEqual(
                outOffsets,
                expOffsets,
                u"'{0}' != '{1}' when tokenizing '{2}'".format(outOffsets,
                                                               expOffsets,
                                                               instring)
            )
            for outToken, expToken in zip(outTokens, expTokens):
                self.assertEqual(
                    outToken, expToken,
                    u"'{0}' != '{1}' when tokenizing '{2}'".format(outTokens,
                                                                   expTokens,
                                                                   instring)
                )
            for outOffset, expOffset in zip(outOffsets, expOffsets):
                self.assertEqual(
                    outOffset, expOffset,
                    u"'{0}' != '{1}' when tokenizing '{2}'".format(outOffsets,
                                                                   expOffsets,
                                                                   instring)
                )


class SimpleTokenizerTestCase(TokenizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return SimpleTokenizer

    def _get_process_string_tests(self):
        return [('This is a sentence to tokenize.',
                ['This', 'is', 'a', 'sentence', 'to', 'tokenize.']),
                (u'This is unicode to tokenize.',
                [u'This', u'is', u'unicode', u'to', u'tokenize.']),
                ('Text\twith\ttabs...', ['Text', 'with', 'tabs...']),
                ('All\non\nnew\nlines!', ['All', 'on', 'new', 'lines!']),
                ('LeaveThisAlone', ['LeaveThisAlone'])]


class UnderscoreSimpleTokenizerTestCase(SimpleTokenizerTestCase):
    "Test SimpleNormalizer, splitting on '_'."

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenizer" id="{0.__name__}">
            <objectType>cheshire3.tokenizer.{0.__name__}</objectType>
            <options>
                <setting type="char">_</setting>
            </options>
        </subConfig>
        '''.format(self._get_class()))

    def _get_process_string_tests(self):
        return [('This_is_a_sentence_to_tokenize.',
                ['This', 'is', 'a', 'sentence', 'to', 'tokenize.']),
                (u'This_is_unicode_to_tokenize.',
                [u'This', u'is', u'unicode', u'to', u'tokenize.']),
                ('Leave this alone!', ['Leave this alone!'])]


class RegexpSubTokenizerTestCase(TokenizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return RegexpSubTokenizer

    def _get_process_string_tests(self):
        # RegexpSubTokenizer result tokens should not include punctuation
        return [('This, is a sentence, to tokenize.',
                ['This', 'is', 'a', 'sentence', 'to', 'tokenize']),
                (u'This is unicode to tokenize.',
                [u'This', u'is', u'unicode', u'to', u'tokenize']),
                ('Text\twith\ttabs...', ['Text', 'with', 'tabs']),
                ('All\non\nnew\nlines!', ['All', 'on', 'new', 'lines']),
                ('LeaveThisAlone', ['LeaveThisAlone'])]


class RegexpFindTokenizerTestCase(TokenizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return RegexpFindTokenizer

    def _get_process_string_tests(self):
        # RegexpFindTokenizer result tokens should not include punctuation
        return [('This,is a sentence,to tokenize.',
                ['This', 'is', 'a', 'sentence', 'to', 'tokenize']),
                (u'This is unicode,to tokenize.',
                [u'This', u'is', u'unicode', u'to', u'tokenize']),
                ('Text\twith\ttabs...', ['Text', 'with', 'tabs']),
                ('All\non\nnew\nlines!', ['All', 'on', 'new', 'lines']),
                ('LeaveThisAlone', ['LeaveThisAlone'])]


class RegexpFindOffsetTokenizerTestCase(OffsetTokenizerTestCase):

    @classmethod
    def _get_class(cls):
        return RegexpFindOffsetTokenizer

    def _get_process_string_tests(self):
        # RegexpFindTokenizer result tokens should not include punctuation
        # Empty tokens are expected at this stage, as they are usually dealt
        # with by process_hash or a TokenMerger at a later stage
        return [('This,is a sentence,to tokenize.',
                 (['This', 'is', 'a', 'sentence', 'to', 'tokenize'],
                  [0, 5, 8, 10, 19, 22])),
                (u'This is unicode,to tokenize.',
                 ([u'This', u'is', u'unicode', u'to', u'tokenize'],
                  [0, 5, 8, 16, 19])),
                ('Text\twith\ttabs...',
                 (['Text', 'with', 'tabs'],
                  [0, 5, 10])),
                ('All\non\nnew\nlines!',
                 (['All', 'on', 'new', 'lines'],
                  [0, 4, 7, 11])),
                ('LeaveThisAlone',
                 (['LeaveThisAlone'],
                  [0]))
        ]

    def _get_process_hash_tests(self):
        # Return a list of 2-dictionary tuples containing test pairs:
        # (dictionary to be normalized, expected result)
        for instring, (expTokens, expOffsets) in self.process_string_tests:
            if expTokens:
                # Filter out empty tokens
                toks = [et for et in expTokens if et]
                # Truncate offsets
                offs = expOffsets[:len(toks)]
                yield ({instring: {'text': instring,
                                   'occurences': 1,
                                   'positions': [0, 0, 0],
                                   'proxLoc': [-1]
                                   }
                       },
                       {instring: {'text': toks,
                                   'occurences': 1,
                                   'positions': [0, 0, 0],
                                   'charOffsets': offs,
                                   'proxLoc': [-1]
                                   }
                        })

    def test_process_string(self):
        "Check that process_string returns the expected tokens and offsets."
        if not self.process_string_tests:
            self.skipTest("No test data defined")
        for instring, (expTokens, expOffsets) in self.process_string_tests:
            outTokens, outOffsets = self.testObj.process_string(self.session,
                                                                instring)
            self.assertIsInstance(outTokens, list)
            self.assertIsInstance(outOffsets, list)
            for outToken, expToken in zip(outTokens, expTokens):
                self.assertEqual(
                    outToken, expToken,
                    u"'{0}' != '{1}' when tokenizing '{2}'".format(outTokens,
                                                                   expTokens,
                                                                   instring)
                )
            for outOffset, expOffset in zip(outOffsets, expOffsets):
                self.assertEqual(
                    outOffset, expOffset,
                    u"'{0}' != '{1}' when tokenizing '{2}'".format(outOffsets,
                                                                   expOffsets,
                                                                   instring)
                )


class RegexpFindPunctuationOffsetTokenizerTestCase(
                                           RegexpFindOffsetTokenizerTestCase):

    def setUp(self):
        RegexpFindOffsetTokenizerTestCase.setUp(self)
        self.maxDiff = None

    @classmethod
    def _get_class(cls):
        return RegexpFindPunctuationOffsetTokenizer

    def _get_process_string_tests(self):
        # RegexpFindTokenizer result tokens should not include punctuation
        # Empty tokens are expected at this stage, as they are usually dealt
        # with by process_hash or a TokenMerger at a later stage
        return [('This,is a sentence,to tokenize.',
                 (['This', 'is', 'a', 'sentence', 'to', 'tokenize'],
                  [0, 4, 8, 10, 18, 22])),
                (u'This is unicode,to tokenize.',
                 ([u'This', u'is', u'unicode', u'to', u'tokenize'],
                  [0, 5, 8, 15, 19])),
                ('Text\twith\ttabs...',
                 (['Text', 'with', 'tabs'],
                  [0, 5, 10])),
                ('All\non\nnew\nlines!',
                 (['All', 'on', 'new', 'lines'],
                  [0, 4, 7, 11])),
                ('LeaveThisAlone',
                 (['LeaveThisAlone'],
                  [0]))
        ]


class RegexpSplitTokenizerTestCase(TokenizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return RegexpSplitTokenizer

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenizer" id="{0.__name__}">
            <objectType>cheshire3.tokenizer.{0.__name__}</objectType>
            <docs>Split on any non alpha-numeric characters</docs>
            <options>
                <setting type="regexp">(?u)\W+</setting>
            </options>
        </subConfig>
        '''.format(self._get_class()))

    def _get_process_string_tests(self):
        # RegexpFindTokenizer result tokens should not include punctuation
        # Empty tokens are expected at this stage, as they are usually dealt
        # with by a TokenMerger at a later stage
        return [('This,is a sentence,to tokenize.',
                ['This', 'is', 'a', 'sentence', 'to', 'tokenize', '']),
                (u'This is unicode,to tokenize.',
                [u'This', u'is', u'unicode', u'to', u'tokenize', '']),
                ('Text\twith\ttabs...', ['Text', 'with', 'tabs', '']),
                ('All\non\nnew\nlines!', ['All', 'on', 'new', 'lines', '']),
                ('LeaveThisAlone', ['LeaveThisAlone'])]


class SentenceTokenizerTestCase(TokenizerTestCase):

    @classmethod
    def _get_class(cls):
        return SentenceTokenizer

    def _get_process_string_tests(self):
        # N.B. this Tokenizer will append . where necessary to achieve a match
        return [('This is a sentence to tokenize. This is a second.',
                ['This is a sentence to tokenize.', ' This is a second.']),
                (u'This is unicode to tokenize.',
                [u'This is unicode to tokenize.']),
                ('Sentence with indication... of a pause.',
                 ['Sentence with indication... of a pause.']),
                ('Sentence split over\nmultiple lines!',
                 ['Sentence split over\nmultiple lines!']),
                ('Sentence without a final full stop or period',
                 ['Sentence without a final full stop or period.'])]


class DateTokenizerTestCase(TokenizerTestCase):

    @classmethod
    def _get_class(cls):
        return DateTokenizer

    def _get_process_string_tests(self):
        return [('1970-01-01',
                [datetime(1970, 1, 1).isoformat()]),
                (u'1970-01-01',
                [datetime(1970, 1, 1).isoformat()]),
                (u'1st January 1970',
                [datetime(1970, 1, 1).isoformat()]),
                ('26 October 1985',
                 [datetime(1985, 10, 26).isoformat()]),
                ('26th October 1985',
                 [datetime(1985, 10, 26).isoformat()]),
                ('26th of October, 1985',
                 [datetime(1985, 10, 26).isoformat()]),
        ]


class DateRangeTokenizerTestCase(DateTokenizerTestCase):

    @classmethod
    def _get_class(cls):
        return DateRangeTokenizer

    def _get_process_string_tests(self):
        # Tests adapted from doctests specified in DateRangeTokenizer
        # For single dates, attempts to expand this into the largest possible
        # range that the data could specify. e.g. 1902-04 means the whole of 
        # April 1902.
        return [('2003/2004',
                ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']),
                (u'2003/2004',
                ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']),
                ('2003-2004',
                 ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']),
                ('2003 2004',
                 ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']),
                ('2003 to 2004',
                 ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']),
                ("1902-04",
                 ['1902-04-01T00:00:00', '1902-04-30T23:59:59.999999']),
                ("1902-02",
                 ['1902-02-01T00:00:00', '1902-02-28T23:59:59.999999'])
        ]


class PythonTokenizerTestCase(OffsetTokenizerTestCase):

    @classmethod
    def _get_class(cls):
        return PythonTokenizer

    def _get_process_string_tests(self):
        return [('spam = None',
                 (['spam/NAME', '=/OP', 'None/NAME'],
                  [0, 5, 7])),
                ('def multiply(a, b):\n'
                 '    return a * b',
                (['def/KEYWORD', 'multiply/NAME', '(/OP', 'a/NAME', ',/OP',
                  'b/NAME', ')/OP', ':/OP', 'return/KEYWORD', 'a/NAME', '*/OP',
                  'b/NAME'],
                 [0, 4, 12, 13, 14, 16, 17, 18, 24, 31, 33, 35]))
        ]


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(SimpleTokenizerTestCase)
    suite.addTests(ltc(UnderscoreSimpleTokenizerTestCase))
    suite.addTests(ltc(RegexpSubTokenizerTestCase))
    suite.addTests(ltc(RegexpFindTokenizerTestCase))
    suite.addTests(ltc(RegexpFindOffsetTokenizerTestCase))
    suite.addTests(ltc(RegexpFindPunctuationOffsetTokenizerTestCase))
    suite.addTests(ltc(RegexpSplitTokenizerTestCase))
    suite.addTests(ltc(SentenceTokenizerTestCase))
    suite.addTests(ltc(DateTokenizerTestCase))
    suite.addTests(ltc(DateRangeTokenizerTestCase))
    suite.addTests(ltc(PythonTokenizerTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))