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

    def store_terms(self, session, index, terms, rec):
        for k in terms.itervalues():
            term = k['text']
            newData = [rec.id, rec.recordStore, k['occurences']]
            # Handle proximity
            try:
                newData.extend(k['positions'])
            except KeyError:
                pass
            currentData = self.indexes[index.id].get(
                term,
                [len(self.indexes[index.id]), 0, 0]
            )
            (termid, totalRecs, totalOccs) = currentData[:3]
            currentData = currentData[3:]
            totalRecs += 1
            totalOccs += k['occurences']
            for n in range(0, len(newData), 3):
                docid = newData[n]
                storeid = newData[n + 1]
                replaced = 0
                for x in range(3, len(currentData), 3):
                    if (currentData[x] == docid and
                        currentData[x + 1] == storeid
                        ):
                        currentData[x + 2] = newData[n + 2]
                        replaced = 1
                        break
                if not replaced:
                    currentData.extend([docid, storeid, newData[n + 2]])
            mergedData = [termid, totalRecs, totalOccs] + currentData
            self.indexes[index.id][term] = mergedData


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

    def _get_test_records(self):
        for x in range(5):
            yield LxmlRecord(etree.XML('<record>'
                                       '<title>Title {0}</title>'
                                       '<content>Record {0} content.</content>'
                                       '</record>'.format(x)),
                             docId=x
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

    def test_processRecord(self):
        "Test processing a Record."
        if not self.testObj.sources:
            self.skipTest("Abstract class, no sources to test")
        for i, rec in enumerate(self._get_test_records()):
            data = self.testObj._processRecord(self.session,
                                             rec,
                                             self.testObj.sources[u'data'][0])
            # Check that return value is a dict
            self.assertIsInstance(data, dict)
            # Check that the dict is exactly as expected
            self.assertDictEqual(
                data,
                {'Title {0}'.format(i): {
                    'text': 'Title {0}'.format(i),
                    'occurences': 1,
                    'proxLoc': [-1]
                    }
                }
            )

    def test_extract_data(self):
        "Test extraction of data from a record."
        if not self.testObj.sources:
            self.skipTest("Abstract class, no sources to test")
        for i, rec in enumerate(self._get_test_records()):
            # Extract data and check expected value
            data = self.testObj.extract_data(self.session, rec)
            self.assertEqual(data, u'Title {0}'.format(i))

    def test_index_record(self):
        """Test indexing a Record.
        
        Check results in terms being extracted and stored.
        """
        if not self.testObj.sources:
            self.skipTest("Abstract class, no sources to test")
        for i, rec in enumerate(self._get_test_records()):
            # Assign store identifier
            rec.recordStore = 0
            # Index the Records
            self.testObj.index_record(self.session, rec)
            # Check that term occurs in IndexStore
            self.assertIn('Title {0}'.format(rec.id),
                          self.testObj.indexStore.indexes[self.testObj.id],
                          "Term not stored")
            # Check that terms have been stored by the Index's IndexStore
            self.assertDictContainsSubset(
                {'Title {0}'.format(rec.id): [i, 1, 1, rec.id, 0, 1]},
                self.testObj.indexStore.indexes[self.testObj.id],
                "Stored term structure not as expected"
            )


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

    def test_sources(self):
        "Test configured sources."
        # Test that there are sources
        self.assertTrue(self.testObj.sources,
                        "No data sources")
        # Test that there are no more or less than 1 source
        self.assertEqual(len(self.testObj.sources),
                         1,
                         "More or less than 1 data source: "
                         "{0!r}".format(self.testObj.sources))
        # Test that there is a source designated for 'data'
        self.assertIn(u'data',
                      self.testObj.sources,
                      "No u'data' source")


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

    def test_sources(self):
        "Test configured sources."
        # Test that there are sources
        self.assertTrue(self.testObj.sources,
                        "No data sources")
        # Test that there are no more or less than 1 source
        self.assertEqual(len(self.testObj.sources),
                         1,
                         "More or less than 1 data source: "
                         "{0!r}".format(self.testObj.sources))
        # Test that there is a source designated for 'data'
        self.assertIn(u'data',
                      self.testObj.sources,
                      "No u'data' source")
    

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
