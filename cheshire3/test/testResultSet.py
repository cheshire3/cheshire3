u"""Cheshire3 ResultSet Unittests.

A ResultSet is collection of results, commonly pointers to Record typically
created in response to a search on a Database. ResultSets are also the return
value when searching an IndexStore or Index and are merged internally to
combine results when searching multiple Indexes with boolean operators.



The behavior of ResultSets are entirely dependent on the indexes and databases
from which they were created. This module creates some simple toy example
ResultSets in order to test the fundamental operations of merging  etc.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.baseObjects import Session, ResultSet, ResultSetItem
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem


class SimpleResultSetItemTestCase(unittest.TestCase):

    def setUp(self):
        """Setup some ResultsetItems to evaluate.

        N.B. a == b, other pairs should not evaluate as equal
        """
        self.session = session = Session()
        self.a = SimpleResultSetItem(session,
                                     id=0,
                                     recStore="recordStore",
                                     occs=0,
                                     database="",
                                     diagnostic=None,
                                     weight=0.5,
                                     resultSet=None,
                                     numeric=None)
        self.b = SimpleResultSetItem(session,
                                     id=0,
                                     recStore="recordStore",
                                     occs=0,
                                     database="",
                                     diagnostic=None,
                                     weight=0.5,
                                     resultSet=None,
                                     numeric=None)
        self.c = SimpleResultSetItem(session,
                                     id=1,
                                     recStore="recordStore",
                                     occs=0,
                                     database="",
                                     diagnostic=None,
                                     weight=0.5,
                                     resultSet=None,
                                     numeric=None)
        self.d = SimpleResultSetItem(session,
                                     id=0,
                                     recStore="recordStore2",
                                     occs=0,
                                     database="",
                                     diagnostic=None,
                                     weight=0.5,
                                     resultSet=None,
                                     numeric=None)

    def tearDown(self):
        del self.a, self.b, self.c, self.d

    def testEquality(self):
        """Test ResultSetItem equality"""
        self.assertEqual(self.a, self.b,
                         "ResultSetItems do not evaluate as equal")
        self.assertNotEqual(self.a, self.c,
                            "ResultSetItems do not evaluate as equal")
        self.assertNotEqual(self.a, self.d,
                            "ResultSetItems do not evaluate as equal")
        self.assertNotEqual(self.b, self.c,
                            "ResultSetItems do not evaluate as equal")
        self.assertNotEqual(self.b, self.d,
                            "ResultSetItems do not evaluate as equal")

    def testCmp(self):
        """Test ResultSetItem comparisons"""
        self.assertLess(self.a, self.c)
        self.assertLess(self.a, self.d)
        self.assertLess(self.b, self.c)
        self.assertLess(self.b, self.d)
        self.assertLess(self.d, self.c)

    def testSerialize(self):
        """Test ResultsetItem serialization."""
        # Check that a and b serialize to the same string
        strA = self.a.serialize(self.session, pickleOk=1)
        strB = self.b.serialize(self.session, pickleOk=1)
        strC = self.c.serialize(self.session, pickleOk=1)
        strD = self.d.serialize(self.session, pickleOk=1)
        self.assertEqual(strA, strB)
        # Check serialization expected to be different
        self.assertNotEqual(strA, strC)
        self.assertNotEqual(strA, strD)
        self.assertNotEqual(strB, strC)
        self.assertNotEqual(strB, strD)
        self.assertNotEqual(strC, strD)
        # Check serialization is well-formed XML
        for s in [strA, strB, strC, strD]:
            etree.fromstring(s)


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(SimpleResultSetItemTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
