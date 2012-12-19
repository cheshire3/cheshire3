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
from cheshire3.cqlParser import parse as cqlparse
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


class SimpleResultSetTestCase(unittest.TestCase):

    def setUp(self):
        """Setup some ResultsetItems and put them into ResultSets to evaluate.

        N.B. a == b, other pairs should not evaluate as equal
        """
        self.session = session = Session()
        # Set up same 4 ResultSetItems as for SimpleResultSetItemTestCase
        self.rsi1 = SimpleResultSetItem(session,
                                        id=0,
                                        recStore="recordStore",
                                        occs=0,
                                        database="",
                                        diagnostic=None,
                                        weight=0.5,
                                        resultSet=None,
                                        numeric=None)
        self.rsi2 = SimpleResultSetItem(session,
                                        id=0,
                                        recStore="recordStore",
                                        occs=0,
                                        database="",
                                        diagnostic=None,
                                        weight=0.5,
                                        resultSet=None,
                                        numeric=None)
        self.rsi3 = SimpleResultSetItem(session,
                                        id=1,
                                        recStore="recordStore",
                                        occs=0,
                                        database="",
                                        diagnostic=None,
                                        weight=0.5,
                                        resultSet=None,
                                        numeric=None)
        self.rsi4 = SimpleResultSetItem(session,
                                        id=0,
                                        recStore="recordStore2",
                                        occs=0,
                                        database="",
                                        diagnostic=None,
                                        weight=0.5,
                                        resultSet=None,
                                        numeric=None)
        # Put identical (rsi1 and rsi2) into separate ResultSets
        self.a = SimpleResultSet(session, [self.rsi1, self.rsi3], id="a")
        self.b = SimpleResultSet(session, [self.rsi2, self.rsi4], id="b")

    def testInit(self):
        "Check initialization of ResultSet"
        rs = SimpleResultSet(self.session)
        # Check is instance of ResultSet
        self.assertIsInstance(rs, ResultSet)
        # Check is instance of SimpleResultSet
        self.assertIsInstance(rs, SimpleResultSet)
        # Check is empty
        self.assertEqual(len(rs), 0)

    def testInstance(self):
        "Check that ResultSet instances are of expected class."
        self.assertIsInstance(self.a, SimpleResultSet)
        self.assertIsInstance(self.b, SimpleResultSet)

    def testLen(self):
        "Check that len(ResultSet) returns correct length."
        self.assertEqual(len(self.a), 2)
        self.assertEqual(len(self.b), 2)

    def testGetitem(self):
        "Check that built-in __getitem__ returns appropriate values"
        self.assertEqual(self.a[0], self.rsi1)
        self.assertEqual(self.a[1], self.rsi3)
        self.assertEqual(self.b[0], self.rsi2)
        self.assertEqual(self.b[1], self.rsi4)

    def testFromList(self):
        "Test population of SimpleResultSet using fromList method."
        rs = SimpleResultSet(self.session)
        self.assertEqual(len(rs), 0)
        self.assertIsInstance(rs, SimpleResultSet)
        rs.fromList([self.rsi1, self.rsi3])
        for x, y in zip(self.a, rs):
            self.assertEqual(x, y)

    def testAppend(self):
        "Test appending a single item to a ResultSet"
        rs = SimpleResultSet(self.session)
        self.assertEqual(len(rs), 0)
        rs.append(self.rsi1)
        self.assertEqual(len(rs), 1)
        self.assertEqual(rs[-1], self.rsi1)

    def testExtend(self):
        "Test appending multiple item to a ResultSet"
        rs = SimpleResultSet(self.session)
        self.assertEqual(len(rs), 0)
        rs.extend([self.rsi1, self.rsi2])
        self.assertEqual(len(rs), 2)
        self.assertEqual(rs[0], self.rsi1)
        self.assertEqual(rs[1], self.rsi2)

    def testCombineAll(self):
        "Test combining ResultSets with 'all'"
        # A clause / boolean is required to combine ResultSets
        clause = cqlparse('my.index all "foo"')
        # Create a new ResultSet to combine into 
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.a, self.b], clause)
        # Check return value is a Resultset
        self.assertIsInstance(rs, SimpleResultSet)
        # Check merged ResultSet has 1 item
        self.assertEqual(len(rs), 1)
        # Check that merged ResultSet contains the correct item
        self.assertIn(self.rsi1, rs)

    def testCombineAny(self):
        "Test combining ResultSets with 'any'"
        # A clause / boolean is required to combine ResultSets
        clause = cqlparse('my.index any "foo"')
        # Create a new ResultSet to combine into 
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.a, self.b], clause)
        # Check return value is a Resultset
        self.assertIsInstance(rs, SimpleResultSet)
        # Check merged ResultSet contains each ResultSetItem
        self.assertIn(self.rsi1, rs)
        self.assertIn(self.rsi2, rs)
        self.assertIn(self.rsi3, rs)
        self.assertIn(self.rsi4, rs)
        # Check merged ResultSet has 3 items (as rsi1 and rsi2 are identical)
        self.assertEqual(len(rs), 3)

    def testCombineNot(self):
        "Test combining ResultSets with 'not'"
        # A clause / boolean is required to combine ResultSets
        clause = cqlparse('my.index = foo not my.index = bar')
        # Create a new ResultSet to combine into 
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.a, self.b], clause)
        # Check return value is a Resultset
        self.assertIsInstance(rs, SimpleResultSet)
        # Check merged ResultSet has 1 item
        self.assertEqual(len(rs), 1)
        # Check that merged ResultSet contains the correct item
        self.assertNotIn(self.rsi1, rs)
        self.assertIn(self.rsi3, rs)


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(SimpleResultSetItemTestCase)
    suite.addTests(ltc(SimpleResultSetTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
