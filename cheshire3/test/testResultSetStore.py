u"""Cheshire3 ResultSetStore Unittests.

A ResultSet is collection of results, commonly pointers to Record typically
created in response to a search on a Database.

A ResultSetStore is a persistent storage mechanism for ResultSet objects.

ResultSetStore configurations may be customized by the user. For the purposes
of unittesting, configuration files will be ignored and ResultsetStore
instances will be instantiated using configurations defined within this testing
module, and tests carried out on those instances using data defined in this
module.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.resultSet import ResultSet, SimpleResultSet, SimpleResultSetItem
from cheshire3.resultSetStore import BdbResultSetStore
from cheshire3.test.testBaseStore import SimpleStoreTestCase, BdbStoreTestCase


class ResultSetStoreTestCase(SimpleStoreTestCase):

    def _get_test_resultSets(self):
        for x in range(5):
            rs = SimpleResultSet(self.session)
            for y in range(5):
                occs = 5 - x
                rs.append(SimpleResultSetItem(self.session,
                                              id=y,
                                              recStore="recordStore",
                                              occs=occs,
                                              database="",
                                              diagnostic=None,
                                              weight=0.5,
                                              resultSet=None,
                                              numeric=None)
                          )
            yield rs

    def test_store_data(self):
        "Check that ResultSet is stored without alteration to copy in memory."
        for inRs in self._get_test_resultSets():
            # Get a representation of the ResultSet
            items = [(i.id, i.recordStore, i.occurences, i.weight)
                     for i
                     in inRs]
            # Store the ResultSet
            self.testObj.create_resultSet(self.session, inRs)
            # Check that fetched ResultSet is unaltered
            new_items = [(i.id, i.recordStore, i.occurences, i.weight)
                         for i
                         in inRs]
            self.assertListEqual(new_items,
                                 items,
                                 u"Returned ResultSet altered while storing")

    def test_storeFetch_data(self):
        "Check that Resultset is stored and retrieved without alteration."
        for inRs in self._get_test_resultSets():
            # Store the ResultSet
            identifier = self.testObj.create_resultSet(self.session, inRs)
            # Fetch the ResultSet
            outRs = self.testObj.fetch_resultSet(self.session, identifier)
            # Check returned object is instance of ResultSet
            self.assertIsInstance(outRs, ResultSet)
            # Check that returned doc content is unaltered
            self.assertEqual(outRs.serialize(self.session),
                             inRs.serialize(self.session),
                             u"Fetched ResultSet not same as stored")


class BdbResultSetStoreTestCase(ResultSetStoreTestCase, BdbStoreTestCase):

    @classmethod
    def _get_class(cls):
        return BdbResultSetStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="recordStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(BdbResultSetStoreTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
