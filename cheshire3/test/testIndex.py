u"""Cheshire3 Index Unittests.

Index configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Index instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on these instances.

Indexes require the configuration of an IndexStore. This module defines a
fake IndexStore class to fulfil the minimum API required to test Indexes.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.baseObjects import Database, IndexStore
from cheshire3.index import SimpleIndex
from cheshire3.record import LxmlRecord
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class FakeDatabase(Database):
    """Database specifically for unittesting Indexes.

    Fulfil mimimum API required for Indexes to process Records.
    """
    pass


class FakeIndexStore(IndexStore):
    """IndexStore specifically for unittesting Indexes.

    Fulfil mimimum API required for 'storing' and fetching terms. Terms
    will only be stored in memory, and hence will not persist between
    sessions or processes.
    """

    def __init__(self, session, config, parent):
    
        IndexStore.__init__(self, session, config, parent)
        self.indexes = {}

    def create_index(self, session, index):
        self.indexes[index.id] = {}


class SimpleIndexTestCase(Cheshire3ObjectTestCase):

    @classmethod
    def _get_class(cls):
        return SimpleIndex

    def _get_dependencyConfigs(self):
        yield etree.XML('''\
        <subConfig type="database" id="db_testIndexes">
          <objectType>cheshire3.test.testIndex.FakeDatabase</objectType>
        </subConfig>''')
        yield etree.XML('''\
        <subConfig type="indexStore" id="indexStore">
          <objectType>cheshire3.test.testIndex.FakeIndexStore</objectType>
        </subConfig>''')

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
            <object type="indexStore" ref="indexStore"/>
          </paths>
        </subConfig>'''.format(self._get_class()))

    def _get_test_record(self):
        return LxmlRecord(etree.XML('<record>'
                                    '<title>Title</title>'
                                    '<content>Record content.</content>'
                                    '</record>')
                          )

    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        self.session.database = "db_testIndexes"

    def test_locate_firstMask(self):
        """Check identification of masking (wildcard) characters."""
        # Test identifying first masking characters
        fm = self.testObj._locate_firstMask('^This is * search term?')
        self.assertEqual(fm, 0)
        fm = self.testObj._locate_firstMask('This is * search term?')
        self.assertEqual(fm, 8)
        fm = self.testObj._locate_firstMask('This is ? search term?')
        self.assertEqual(fm, 8)
        # Test identifying first masking character starting from a given point
        fm = self.testObj._locate_firstMask('This is * search term?', start=9)
        self.assertEqual(fm, 21)

    def test_regexify_wildcards(self):
        "Check changing masked terms (i.e. w/ wildcards) into regexes."
        regex = self.testObj._regexify_wildcards('^This is * search term?')
        self.assertEqual(regex, '^This is .* search term.$')
        regex = self.testObj._regexify_wildcards('This is * search term?')
        self.assertEqual(regex, 'This is .* search term.$')
        regex = self.testObj._regexify_wildcards('This is ? search term?')
        self.assertEqual(regex, 'This is . search term.$')
        # Check that explicit caret is not treated as an anchor
        regex = self.testObj._regexify_wildcards(
            r'This is ? search term? with a \^'
        )
        self.assertEqual(regex, r'This is . search term. with a \^$')


class XPathSimpleIndexTestCase(SimpleIndexTestCase):
    """Test a SimpleIndex configured with an explicit XPath."""
    
    def _get_config(self):
        return etree.XML('''\
        <subConfig type="" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
            <object type="indexStore" ref="indexStore"/>
          </paths>
          <source>
            <xpath>title</xpath>
            <process>
                <object type="extractor" ref="SimpleExtractor"/>
            </process>
          </source>
        </subConfig>'''.format(self._get_class()))

    def test_processRecord(self):
        rec = self._get_test_record()
        data = self.testObj._processRecord(self.session,
                                         rec,
                                         self.testObj.sources[u'data'][0])
        self.assertIsInstance(data, dict)
        self.assertIn('Title', data)
        self.assertDictContainsSubset(
            {'text': 'Title', 'occurences': 1},
            data['Title']
        )

    def test_extract_data(self):
        "Test extraction of data from a record."
        rec = self._get_test_record()
        data = self.testObj.extract_data(self.session, rec)
        self.assertEqual(data, u'Title')


class SelectorSimpleIndexTestCase(SimpleIndexTestCase):
    """Test a SimpleIndex configured with a referenced Selector."""
    
    def _get_dependencyConfigs(self):
        for conf in SimpleIndexTestCase._get_dependencyConfigs(self):
            yield conf
        yield etree.XML('''\
        <subConfig type="xpathProcessor" id="titleXPath">
          <objectType>cheshire3.selector.XPathSelector</objectType>
          <source>
            <location type="xpath">title</location>
          </source>
        </subConfig>''')

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
            <object type="indexStore" ref="indexStore"/>
          </paths>
          <source>
            <selector ref="titleXPath"/>
            <process>
                <object type="extractor" ref="SimpleExtractor"/>
            </process>
          </source>
        </subConfig>'''.format(self._get_class()))

    def test_processRecord(self):
        rec = self._get_test_record()
        data = self.testObj._processRecord(self.session,
                                         rec,
                                         self.testObj.sources[u'data'][0])
        self.assertIsInstance(data, dict)
        self.assertIn('Title', data)
        self.assertDictContainsSubset(
            {'text': 'Title', 'occurences': 1},
            data['Title']
        )

    def test_extract_data(self):
        "Test extraction of data from a record."
        rec = self._get_test_record()
        data = self.testObj.extract_data(self.session, rec)
        self.assertEqual(data, u'Title')


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(SimpleIndexTestCase)
    suite.addTests(ltc(XPathSimpleIndexTestCase))
    suite.addTests(ltc(SelectorSimpleIndexTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
