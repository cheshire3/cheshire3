u"""Cheshire3 QueryStore Unittests.

QueryStore configurations may be customized by the user. For the purposes 
of unittesting, configuration files will be ignored and QueryStore 
instances will be instantiated using configuration data defined within this 
testing module, and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.cqlParser import parse as cqlParse, PrefixableObject as Query
from cheshire3.queryStore import QueryStore, BdbQueryStore
from cheshire3.exceptions import ObjectAlreadyExistsException,\
                                 ObjectDoesNotExistException,\
                                 ObjectDeletedException
from cheshire3.test.testBaseStore import SimpleStoreTestCase, BdbStoreTestCase


class QueryStoreTestCase(SimpleStoreTestCase):
    
    def _get_test_queries(self):
        yield cqlParse(u"cql.anywhere all spam")
        yield cqlParse(u'cql.anywhere all/cql.stem/rel.algorithm=okapi "spam"')
        yield cqlParse(u"cql.anywhere all spam"
                       u" and "
                       u"cql.anywhere all eggs")

    def test_store_data(self):
        "Check that Query is stored without corruption to copy in memory."
        for inQuery in self._get_test_queries():
            # Store the Query
            outQuery = self.testObj.create_query(self.session, inQuery)
            # Check that returned doc is unaltered
            self.assertEqual(outQuery.toCQL(),
                             inQuery.toCQL(),
                             u"Returned document content not as expected")

    def test_storeFetch_data(self):
        "Check that Query is stored without corruption."
        for inQuery in self._get_test_queries():
            # Store the Query
            inQuery = self.testObj.create_query(self.session, inQuery)
            # Fetch the Query
            outQuery = self.testObj.fetch_query(self.session, inQuery.id)
            # Check returned object is instance of Query
            self.assertIsInstance(outQuery, Query)
            # Check that returned doc content is unaltered
            self.assertEqual(outQuery.toCQL(),
                             inQuery.toCQL(),
                             u"Returned document content not as expected")

    def test_storeFetch_metadata(self):
        "Check that metadata is stored and fetched without alteration."
        self.skipTest("No metadata stored for Queries")

    def test_storeDeleteFetch_data(self):
        "Check that Query is deleted."
        for inQuery in self._get_test_queries():
            # Store the Query
            inQuery = self.testObj.create_query(self.session, inQuery)
            # Fetch the Query
            outQuery = self.testObj.fetch_query(self.session, inQuery.id)
            # Check that returned doc is unaltered
            self.assertEqual(outQuery.toCQL(),
                             inQuery.toCQL(),
                             u"Returned document content not as expected")
            # Delete the Query
            self.testObj.delete_query(self.session, inQuery.id)
            # Check that deleted data no longer exists / evaluates as false
            self.assertRaises(ObjectDoesNotExistException,
                              self.testObj.fetch_query,
                              self.session, inQuery.id)


class BdbQueryStoreTestCase(QueryStoreTestCase, BdbStoreTestCase):

    @classmethod
    def _get_class(cls):
        return BdbQueryStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="documentStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


class DeletionsBdbQueryStoreTestCase(BdbQueryStoreTestCase):
    "BerkeleyDB based persistent Query storage with stored deletions."

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="documentStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
          </paths>
          <options>
            <setting type="storeDeletions">1</setting>
          </options>
        </subConfig>'''.format(self._get_class(), self.defaultPath))

    def test_storeDeleteFetch_data(self):
        "Check that data is deleted."
        for inQuery in self._get_test_queries():
            # Store the Query
            inQuery = self.testObj.create_query(self.session, inQuery)
            # Fetch the Query
            outQuery = self.testObj.fetch_query(self.session, inQuery.id)
            # Check that returned doc is unaltered
            self.assertEqual(outQuery.toCQL(),
                             inQuery.toCQL(),
                             u"Returned document content not as expected")
            # Delete the Query
            self.testObj.delete_query(self.session, inQuery.id)
            # Check that deleted data no longer exists / evaluates as false
            self.assertRaises(ObjectDeletedException,
                              self.testObj.fetch_query,
                              self.session, inQuery.id)


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(BdbQueryStoreTestCase)
    suite.addTests(ltc(DeletionsBdbQueryStoreTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
