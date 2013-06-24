u"""Cheshire3 ResultSet Unittests.

A ResultSet is collection of results, commonly pointers to Record typically
created in response to a search on a Database. ResultSets are also the return
value when searching an IndexStore or Index and are merged internally to
combine results when searching multiple Indexes with boolean operators.

The behavior of ResultSets are entirely dependent on the indexes and databases
from which they were created. This module creates some simple toy example
ResultSets in order to test the fundamental operations of merging  etc.
"""

import math

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.baseObjects import Session, Database, RecordStore, ProtocolMap
from cheshire3.cqlParser import parse as cqlparse
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem


class FakeDatabase(Database):
    """Database specifically for unittesting relevance score calculations.

    May be initialize with only the minimum information needed for calculating
    ResultSet relevance etc.
    """

    def __init__(self, session, config, parent=None):
        self.totalItems = 100
        self.meanWordCount = 100

    def get_object(self, session, identifier):
        if identifier.startswith('recordStore'):
            return FakeRecordStore(session, None)

    def get_path(self, session, path):
        if path == 'protocolMap':
            return FakeProtocolMap(session, None)


class FakeRecordStore(RecordStore):
    """RecordStore specifically for unittesting relevance score calculations.

    Fulfil mimimum API required for calculating ResultSet relevance.
    """

    def __init__(self, session, config, parent=None):
        pass
    
    def fetch_recordMetadata(self, session, identifier, mdType):
        # Return an arbitrary value
        if mdType == 'wordCount':
            return 100


class FakeProtocolMap(ProtocolMap):
    """ProtocolMap specifically for unittesting relevance score calculations.

    Fulfil mimimum API required for calculating ResultSet relevance.
    """

    def __init__(self, session, config, parent=None):
        pass

    def resolveIndex(self, session, clause):
        return None


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
                                        occs=5,
                                        database="",
                                        diagnostic=None,
                                        weight=0.5,
                                        resultSet=None,
                                        numeric=None)
        self.rsi2 = SimpleResultSetItem(session,
                                        id=0,
                                        recStore="recordStore",
                                        occs=3,
                                        database="",
                                        diagnostic=None,
                                        weight=0.5,
                                        resultSet=None,
                                        numeric=None)
        self.rsi3 = SimpleResultSetItem(session,
                                        id=1,
                                        recStore="recordStore",
                                        occs=1,
                                        database="",
                                        diagnostic=None,
                                        weight=0.5,
                                        resultSet=None,
                                        numeric=None)
        self.rsi4 = SimpleResultSetItem(session,
                                        id=0,
                                        recStore="recordStore2",
                                        occs=2,
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

    def testTfidf(self):
        "Test combining with TF-IDF relevance ranking."
        # A clause / boolean is required to combine ResultSets
        clause = cqlparse('my.index all/rel.algorithm=tfidf "foo bar"')
        clause.addPrefix('rel', "info:srw/cql-context-set/2/relevance-1.2")
        # A Database is required for relevance ranking
        db = FakeDatabase(self.session, None, parent=None)
        # Test self.a
        # Create a new ResultSet to combine into
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.a], clause, db)
        self.assertEqual(len(rs), 2)
        for rsi in rs:
            # Check that each ResultSetItem has a score (weight)
            self.assertTrue(hasattr(rsi, 'weight'))
            # Check that each ResultSetItem has a scaled score less than 1
            self.assertLessEqual(rsi.scaledWeight, 1.0)
        # Check scores are correct and in order
        matches = len(self.a)
        self.assertListEqual([rsi.weight for rsi in rs],
                             [5 * math.log(db.totalItems / matches),
                              1 * math.log(db.totalItems / matches)]
                             )
        # Test self.b
        # Create a new ResultSet to combine into
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.b], clause, db)
        self.assertEqual(len(rs), 2)
        for rsi in rs:
            # Check that each ResultSetItem has a score (weight)
            self.assertTrue(hasattr(rsi, 'weight'))
            # Check that each ResultSetItem has a scaled score less than 1
            self.assertLessEqual(rsi.scaledWeight, 1.0)
        # Check scores are correct and in order
        matches = len(self.b)
        self.assertListEqual([rsi.weight for rsi in rs],
                             [3 * math.log(db.totalItems / matches),
                              2 * math.log(db.totalItems / matches)]
                             )

    def testCori(self):
        "Test combining with CORI relevance ranking."
        # A clause / boolean is required to combine ResultSets
        clause = cqlparse('my.index all/rel.algorithm=cori "foo bar"')
        clause.addPrefix('rel', "info:srw/cql-context-set/2/relevance-1.2")
        # A Database is required for relevance ranking
        db = FakeDatabase(self.session, None)
        # A RecordStore is required for CORI score calculation
        recStore = FakeRecordStore(self.session, None)
        # Test self.a
        # Create a new ResultSet to combine into 
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.a], clause, db)
        self.assertEqual(len(rs), 2)
        for rsi in rs:
            # Check that each ResultSetItem has a score (weight)
            self.assertTrue(hasattr(rsi, 'weight'))
            # Check that each ResultSetItem has a scaled score less than 1
            self.assertLessEqual(rsi.scaledWeight, 1.0)
        # Check scores are correct and in order
        matches = len(self.a)
        # I is used in calculating score for each item
        I = (math.log((db.totalItems + 0.5) / matches) /
             math.log(db.totalItems + 1.0))
        expectedScores = []
        for rsi in [self.rsi1, self.rsi3]:
            size = recStore.fetch_recordMetadata(self.session,
                                                 rsi.id,
                                                 'wordCount')
            T = (rsi.occurences /
                 (rsi.occurences + 50.0 + (( 150.0 * size) / db.meanWordCount))
                 )
            expectedScores.append(0.4 + (0.6 * T * I))
        self.assertListEqual([rsi.weight for rsi in rs], expectedScores)
        # Test self.b
        # Create a new ResultSet to combine into 
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.b], clause, db)
        self.assertEqual(len(rs), 2)
        for rsi in rs:
            # Check that each ResultSetItem has a score (weight)
            self.assertTrue(hasattr(rsi, 'weight'))
            # Check that each ResultSetItem has a scaled score less than 1
            self.assertLessEqual(rsi.scaledWeight, 1.0)
        # Check scores are correct and in order
        matches = len(self.b)
        # I is used in calculating score for each item
        I = (math.log((db.totalItems + 0.5) / matches) /
             math.log(db.totalItems + 1.0))
        expectedScores = []
        for rsi in [self.rsi2, self.rsi4]:
            size = recStore.fetch_recordMetadata(self.session,
                                                 rsi.id,
                                                 'wordCount')
            T = (rsi.occurences /
                 (rsi.occurences + 50.0 + (( 150.0 * size) / db.meanWordCount))
                 )
            expectedScores.append(0.4 + (0.6 * T * I))
        self.assertListEqual([rsi.weight for rsi in rs], expectedScores)

    def testOkapi(self):
        "Test combining with OKAPI BM-25 relevance ranking."
        # A clause / boolean is required to combine ResultSets
        b, k1, k3 = [0.75, 1.5, 1.5]
        clause = cqlparse('my.index all/rel.algorithm=okapi/'
                          'rel.const0={0}/'
                          'rel.const1={1}/'
                          'rel.const2={2}'
                          ' "foo bar"'.format(b, k1, k3))
        clause.addPrefix('rel', "info:srw/cql-context-set/2/relevance-1.2")
        # A Database is required for relevance ranking
        db = FakeDatabase(self.session, None)
        # A RecordStore is required for CORI score calculation
        recStore = FakeRecordStore(self.session, None)
        # Test self.a
        # Create a new ResultSet to combine into 
        rs = SimpleResultSet(self.session)
        # Set ResultSet queryFrequency - required for OKAPI BM-25
        self.a.queryFreq = 1
        rs = rs.combine(self.session, [self.a], clause, db)
        self.assertEqual(len(rs), 2)
        for rsi in rs:
            # Check that each ResultSetItem has a score (weight)
            self.assertTrue(hasattr(rsi, 'weight'))
#            self.assertTrue(rsi.weight)
            # Check that each ResultSetItem has a scaled score less than 1
            self.assertLessEqual(rsi.scaledWeight, 1.0)
        # Check scores are correct and in order
        matches = len(self.a)
        idf = math.log(db.totalItems / matches)
        qtw = ((k3 + 1) * 1) / (k3 + 1)
        expectedScores = []
        for rsi in [self.rsi1, self.rsi3]:
            size = recStore.fetch_recordMetadata(self.session,
                                                 rsi.id,
                                                 'wordCount')
            T = (((k1 + 1) * rsi.occurences) /
                 ((k1 * ((1 - b) + b *
                         (size / db.meanWordCount)
                         )
                   ) +
                  rsi.occurences)
                 )
            expectedScores.append(idf * T * qtw)
        self.assertListEqual([rsi.weight for rsi in rs], expectedScores)
        # Test self.b
        # Create a new ResultSet to combine into 
        rs = SimpleResultSet(self.session)
        # Set ResultSet queryFrequency - required for OKAPI BM-25
        self.b.queryFreq = 1
        rs = rs.combine(self.session, [self.b], clause, db)
        self.assertEqual(len(rs), 2)
        for rsi in rs:
            # Check that each ResultSetItem has a score (weight)
            self.assertTrue(hasattr(rsi, 'weight'))
#            self.assertTrue(rsi.weight)
            # Check that each ResultSetItem has a scaled score less than 1
            self.assertLessEqual(rsi.scaledWeight, 1.0)
        # Check scores are correct and in order
        matches = len(self.a)
        idf = math.log(db.totalItems / matches)
        qtw = ((k3 + 1) * 1) / (k3 + 1)
        expectedScores = []
        for rsi in [self.rsi2, self.rsi4]:
            size = recStore.fetch_recordMetadata(self.session,
                                                 rsi.id,
                                                 'wordCount')
            T = (((k1 + 1) * rsi.occurences) /
                 ((k1 * ((1 - b) + b *
                         (size / db.meanWordCount)
                         )
                   ) +
                  rsi.occurences)
                 )
            expectedScores.append(idf * T * qtw)
        self.assertListEqual([rsi.weight for rsi in rs], expectedScores)

    def testCombineMeanWeights(self):
        "Test combining ResultSet scores by mean average."
        # A clause / boolean is required to combine ResultSets
        # Use TF-IDF because it's most simple to calculate
        clause = cqlparse('my.index '
                          'all/rel.algorithm=tfidf/rel.combine=mean '
                          '"foo bar"')
        
        clause.addPrefix('rel', "info:srw/cql-context-set/2/relevance-1.2")
        # A Database is required for relevance ranking
        db = FakeDatabase(self.session, None, parent=None)
        # Create a new ResultSet to combine into
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.a, self.b], clause, db)
        # Check return value is a Resultset
        self.assertIsInstance(rs, SimpleResultSet)
        # Check merged ResultSet has 1 item
        self.assertEqual(len(rs), 1)
        # Check that merged ResultSet contains the correct item
        self.assertIn(self.rsi1, rs)
        for rsi in rs:
            # Check that each ResultSetItem has a score (weight)
            self.assertTrue(hasattr(rsi, 'weight'))
            # Check that each ResultSetItem has a scaled score less than 1
            self.assertLessEqual(rsi.scaledWeight, 1.0)
        # Check combined scores correct
        matches = len(self.b)
        self.assertEqual(rs[0].weight,
                         sum([5 * math.log(db.totalItems / matches),
                              3 * math.log(db.totalItems / matches)
                              ]
                             ) / 2
                         )

    def testCombineSumWeights(self):
        "Test combining ResultSet scores by summation."
        # A clause / boolean is required to combine ResultSets
        # Use TF-IDF because it's most simple to calculate
        clause = cqlparse('my.index '
                          'all/rel.algorithm=tfidf/rel.combine=sum '
                          '"foo bar"')
        
        clause.addPrefix('rel', "info:srw/cql-context-set/2/relevance-1.2")
        # A Database is required for relevance ranking
        db = FakeDatabase(self.session, None, parent=None)
        # Create a new ResultSet to combine into
        rs = SimpleResultSet(self.session)
        rs = rs.combine(self.session, [self.a, self.b], clause, db)
        # Check return value is a Resultset
        self.assertIsInstance(rs, SimpleResultSet)
        # Check merged ResultSet has 1 item
        self.assertEqual(len(rs), 1)
        # Check that merged ResultSet contains the correct item
        self.assertIn(self.rsi1, rs)
        for rsi in rs:
            # Check that each ResultSetItem has a score (weight)
            self.assertTrue(hasattr(rsi, 'weight'))
            # Check that each ResultSetItem has a scaled score less than 1
            self.assertLessEqual(rsi.scaledWeight, 1.0)
        # Check combined scores correct
        matches = len(self.b)
        self.assertEqual(rs[0].weight,
                         sum([5 * math.log(db.totalItems / matches),
                              3 * math.log(db.totalItems / matches)
                              ]
                             )
                         )

    def testSerialize(self):
        for rs in [self.a, self.b]:
            srlzd = rs.serialize(self.session)
            self.assertIsInstance(srlzd, basestring,
                                  u"ResultSet serialization not "
                                  u"string or unicode."
                                  )
            try:
                etree.fromstring(srlzd)
            except etree.XMLSyntaxError:
                self.fail(u"ResultSet serialization is not well-formed XML")


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(SimpleResultSetItemTestCase)
    suite.addTests(ltc(SimpleResultSetTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
