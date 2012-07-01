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

from cheshire3.tokenizer import Tokenizer, SimpleTokenizer,\
    RegexpSubTokenizer, RegexpFindTokenizer, RegexpSplitTokenizer
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class TokenizerTestCase(Cheshire3ObjectTestCase):
    
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


class SimpleTokenizerTestCase(TokenizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return SimpleTokenizer

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenizer" id="{0.__name__}">
            <objectType>cheshire3.tokenizer.{0.__name__}</objectType>
        </subConfig>
        '''.format(self._get_class()))

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

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenizer" id="{0.__name__}">
            <objectType>cheshire3.tokenizer.{0.__name__}</objectType>
        </subConfig>
        '''.format(self._get_class()))

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

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenizer" id="{0.__name__}">
            <objectType>cheshire3.tokenizer.{0.__name__}</objectType>
        </subConfig>
        '''.format(self._get_class()))

    def _get_process_string_tests(self):
        # RegexpFindTokenizer result tokens should not include punctuation
        return [('This,is a sentence,to tokenize.',
                ['This', 'is', 'a', 'sentence', 'to', 'tokenize']),
                (u'This is unicode,to tokenize.',
                [u'This', u'is', u'unicode', u'to', u'tokenize']),
                ('Text\twith\ttabs...', ['Text', 'with', 'tabs']),
                ('All\non\nnew\nlines!', ['All', 'on', 'new', 'lines']),
                ('LeaveThisAlone', ['LeaveThisAlone'])]


class RegexpSplitTokenizerTestCase(TokenizerTestCase):
    
    @classmethod
    def _get_class(cls):
        return RegexpSplitTokenizer

    def _get_config(self):
        return etree.XML('''
        <subConfig type="tokenizer" id="{0.__name__}">
            <objectType>cheshire3.tokenizer.{0.__name__}</objectType>
            <options>
                <setting type="regexp">(?u)[_\n\t\s,.]+</setting>
            </options>
        </subConfig>
        '''.format(self._get_class()))

    def _get_process_string_tests(self):
        # RegexpFindTokenizer result tokens should not include punctuation
        return [('This,is a sentence,to tokenize.',
                ['This', 'is', 'a', 'sentence', 'to', 'tokenize', '']),
                (u'This is unicode,to tokenize.',
                [u'This', u'is', u'unicode', u'to', u'tokenize', '']),
                ('Text\twith\ttabs...', ['Text', 'with', 'tabs', '']),
                ('All\non\nnew\nlines!', ['All', 'on', 'new', 'lines!']),
                ('LeaveThisAlone', ['LeaveThisAlone'])]

    def setUp(self):
        TokenizerTestCase.setUp(self)
        self.maxDiff = None


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(SimpleTokenizerTestCase)
    suite.addTests(ltc(UnderscoreSimpleTokenizerTestCase))
    suite.addTests(ltc(RegexpSubTokenizerTestCase))
    suite.addTests(ltc(RegexpFindTokenizerTestCase))
    suite.addTests(ltc(RegexpSplitTokenizerTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))