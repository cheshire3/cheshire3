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
from cheshire3.cqlParser import parse as cqlparse
from cheshire3.index import SimpleIndex
from cheshire3.record import LxmlRecord
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem
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

    def delete_terms(self, session, index, terms, rec):
        for k in terms.keys():
            currentData = self.indexes[index.id].get(k)
            if (currentData is not None):
                gone = [rec.id, rec.recordStore, terms[k]['occurences']]
                (termid, oldTotalRecs, oldTotalOccs) = currentData[0:3]
                currentData = list(currentData[3:])
                for n in range(0, len(gone), 3):
                    docid = gone[n]
                    storeid = gone[n + 1]
                    for x in range(0, len(currentData), 3):
                        if (currentData[x] == docid and
                            currentData[x + 1] == storeid):
                            del currentData[x:(x + 3)]
                            break
                trecs = len(currentData) / 3
                toccs = sum(currentData[2::3])
                mergedData = [termid, trecs, toccs] + currentData
                if not mergedData[1]:
                    # All terms deleted
                    del self.indexes[index.id][k]
                else:
                    self.indexes[index.id][k] = mergedData

    def construct_resultSetItem(self, session, recId,
                                recStoreId, nOccs, rsiType=None):
        numericId = recId
        recStore = ["recordStore"][recStoreId]
        return SimpleResultSetItem(session, recId, recStore,
                                   nOccs, session.database,
                                   numeric=numericId
                                   )

    def fetch_term(self, session, index, term, summary=False, prox=True):
        try:
            unpacked = self.indexes[index.id][term]
        except KeyError:
            unpacked = []
        if summary:
            unpacked = unpacked[:3]
        return unpacked


class SimpleIndexTestCase(Cheshire3ObjectTestCase):
    """Test a SimpleIndex configured with an explicit XPath.

    Also acts as base class for testing SimpleIndexes with varying
    configurations.
    """

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
          <source>
            <xpath>title</xpath>
            <process>
                <object type="extractor" ref="SimpleExtractor"/>
            </process>
          </source>
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
        for i, rec in enumerate(self._get_test_records()):
            # Extract data and check expected value
            data = self.testObj.extract_data(self.session, rec)
            self.assertEqual(data, u'Title {0}'.format(i))

    def test_index_record(self):
        """Test indexing a Record.
        
        Check results in terms being extracted and stored.
        """
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

    def test_delete_record(self):
        """Test deleting (unindexing) a Record.

        Check deleting a Record results in terms being extracted and removed
        from the IndexStore.
        """
        # Initialize IndexStore with some data
        terms = self.testObj.indexStore.indexes[self.testObj.id]
        for i in range(5):
            terms["Title {0}".format(i)] = [i, 1, 1, i, 0, 1]

        for i, rec in enumerate(self._get_test_records()):
            # Assign store identifier
            rec.recordStore = 0
            # Delete the Record
            self.testObj.delete_record(self.session, rec)
            # Check that term no longer occurs in IndexStore
            self.assertNotIn('Title {0}'.format(rec.id),
                          self.testObj.indexStore.indexes[self.testObj.id],
                          "Term not deleted")

    def test_construct_resultSet(self):
        """Test ResultSet construction."""
        # Create some fake Index data, data structure:
        # [termId, totalRecs, totalOccs, recId, recRecordStore, recOccs, ...]
        indexData = [0, None, None, 0, 0, 3, 1, 0, 2]
        # Calculate total Records, total Occurences
        totalRecs = len(indexData[3:]) / 3    # length of records part / 3
        indexData[1] = totalRecs
        self.assertTrue(indexData[1] is not None and indexData[1] >= 0,
                        "Incorrect definition of test data: totalRecs")
        totalOccs = sum(indexData[3:][2::3])  # sum of record occurences
        indexData[2] = totalOccs
        self.assertTrue(indexData[2] is not None and indexData[2] >= 0,
                        "Incorrect definition of test data: totalRecs")

        # Construct ResultSet
        rs = self.testObj.construct_resultSet(self.session,
                                              indexData,
                                              {})
        # Check return value
        self.assertIsInstance(rs, SimpleResultSet)
        # Test ResultSet summary data
        self.assertEqual(rs.totalRecs,
                         totalRecs,
                         "ResultSet.totalRecs not as expected ({0})"
                         "".format(totalRecs)
                         )
        # Test len(ResultSet)
        self.assertEqual(len(rs),
                         totalRecs,
                         "ResultSet length not as expected ({0})"
                         "".format(totalRecs)
                         )
        self.assertEqual(rs.termid, 0, "ResultSet.termid not as expected (0)")
        self.assertEqual(rs.totalOccs,
                         totalOccs,
                         "ResultSet.totalOccs not as expected ({0})"
                         "".format(totalOccs)
                         )
        # Check items
        for rsi in rs:
            self.assertIsInstance(rsi, SimpleResultSetItem)
        # Check identifiers
        self.assertEqual(rs[0].id, 0)
        self.assertEqual(rs[1].id, 1)
        # Check occurences (sic)
        self.assertEqual(rs[0].occurences, 3)
        self.assertEqual(rs[1].occurences, 2)
        # Check resultSet raise appropriate error when outside bounds
        with self.assertRaises(IndexError):
            rs[2]

    def test_search(self):
        """Test a simple search of the Index."""
        # Initialize IndexStore with some data
        indexData = [0, None, None, 0, 0, 3, 1, 0, 2]
        # Calculate total Records, total Occurences
        totalRecs = len(indexData[3:]) / 3    # length of records part / 3
        indexData[1] = totalRecs
        self.assertTrue(indexData[1] is not None and indexData[1] >= 0,
                        "Incorrect definition of test data: totalRecs")
        totalOccs = sum(indexData[3:][2::3])  # sum of record occurences
        indexData[2] = totalOccs
        self.assertTrue(indexData[2] is not None and indexData[2] >= 0,
                        "Incorrect definition of test data: totalRecs")
        self.testObj.indexStore.indexes[self.testObj.id]['bar'] = indexData
        # Parse a query
        query = cqlparse('c3.foo = bar')
        # Fetch a Database object
        db = self.server.get_object(self.session, self.session.database)

        # Carry out the search
        rs = self.testObj.search(self.session, query, db)
        # Check return value
        self.assertIsInstance(rs, SimpleResultSet)

        # Test ResultSet summary data
        self.assertEqual(rs.totalRecs,
                         totalRecs,
                         "ResultSet.totalRecs not as expected: {0} != {1}"
                         "".format(rs.totalRecs, totalRecs)
                         )
        # Test len(ResultSet)
        self.assertEqual(len(rs),
                         totalRecs,
                         "ResultSet length not as expected ({0})"
                         "".format(totalRecs)
                         )
        self.assertEqual(rs.termid,
                         indexData[0],
                         "ResultSet.termid not as expected: {0} != {1}"
                         "".format(rs.termid, indexData[0]))
        self.assertEqual(rs.totalOccs,
                         totalOccs,
                         "ResultSet.totalOccs not as expected: {0} != {1}"
                         "".format(rs.totalOccs, totalOccs)
                         )
        # Check items
        for rsi in rs:
            self.assertIsInstance(rsi, SimpleResultSetItem)
        # Check identifiers
        self.assertEqual(rs[0].id, 0)
        self.assertEqual(rs[1].id, 1)
        # Check occurences (sic)
        self.assertEqual(rs[0].occurences, 3)
        self.assertEqual(rs[1].occurences, 2)
        # Check resultSet raise appropriate error when outside bounds
        with self.assertRaises(IndexError):
            rs[2]


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


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(SimpleIndexTestCase)
    suite.addTests(ltc(SelectorSimpleIndexTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
