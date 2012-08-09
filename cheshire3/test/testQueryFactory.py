u"""Cheshire3 QueryFactory Unittests.

QueryFactory configurations may be customized by the user. For the purposes 
of unittesting, configuration files will be ignored and QueryFactory 
instances will be instantiated using configuration data defined within this 
testing module, and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.cqlParser import *
from cheshire3.queryFactory import SimpleQueryFactory
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class SimpleQueryFactoryTestCase(Cheshire3ObjectTestCase):
    """Cheshire3 SimpleQueryFactory Test Case."""
    
    def _get_class(self):
        return SimpleQueryFactory
    
    def _get_config(self):
        return etree.XML('''\
        <subConfig type="documentFactory" id="{0.__name__}">
            <objectType>cheshire3.queryFactory.{0.__name__}</objectType>
        </subConfig>'''.format(self._get_class()))

    def test_get_query_invalid(self):
        "Check that invalid/non-well-formed CQL raises appropriate Diagnostic."
        self.assertRaises(Diagnostic,
                          self.testObj.get_query,
                          self.session,
                          "cql.anywhere all spam eggs")

    def test_get_query_clause(self):
        "Check that simple clause is parsed correctly."
        query = self.testObj.get_query(self.session,
                                       u"cql.anywhere all spam")
        # Check query instance
        self.assertIsInstance(query, SearchClause)
        # Check Index
        self.assertIsInstance(query.index, Index)
        self.assertEqual(query.index.prefix, 'cql')
        self.assertEqual(query.index.value, 'anywhere')
        # Check Relation
        self.assertIsInstance(query.relation, Relation)
        self.assertEqual(query.relation.value, 'all')
        # Check Value
        self.assertIsInstance(query.term, Term)
        self.assertEqual(query.term.value, 'spam')

    def test_get_query_clause_modifiers(self):
        "Check that relation modifiers are parsed correctly."
        query = self.testObj.get_query(
                   self.session,
                   u'cql.anywhere all/cql.stem/rel.algorithm=okapi "spam"')
        self.assertTrue(len(query.relation.modifiers))
        for mod in query.relation.modifiers:
            self.assertIsInstance(mod, ModifierClause)
        self.assertEqual(str(query.relation.modifiers[0].type),
                         'cql.stem')
        self.assertEqual(str(query.relation.modifiers[1].type),
                         'rel.algorithm')
        self.assertEqual(str(query.relation.modifiers[1].comparison),
                         '=')
        self.assertEqual(str(query.relation.modifiers[1].value),
                         'okapi')
        
    def test_get_query_triple(self):
        "Check that query with boolean is parsed correctly."
        query = self.testObj.get_query(self.session,
                                       u"cql.anywhere all spam"
                                       u" and "
                                       u"cql.anywhere all eggs")
        # Check query instance
        self.assertIsInstance(query, Triple)
        # Check left clause
        self.assertIsInstance(query.leftOperand, SearchClause)
        # remember terms get quoted during parsing
        self.assertEqual(query.leftOperand.toCQL(),
                         u'cql.anywhere all "spam"')
        # Check boolean
        self.assertIsInstance(query.boolean, Boolean)
        self.assertEqual(query.boolean.value, 'and')
        # Check right clause
        self.assertIsInstance(query.rightOperand, SearchClause)
        # remember terms get quoted during parsing
        self.assertEqual(query.rightOperand.toCQL(),
                         u'cql.anywhere all "eggs"')

    def test_get_query_triple_modifiers(self):
        "Check that query with boolean modifiers is parsed correctly."
        query = self.testObj.get_query(self.session,
                                       u"cql.anywhere all spam"
                                       u" and/rel.combine=sum "
                                       u"cql.anywhere all eggs")
        self.assertTrue(len(query.boolean.modifiers))
        for mod in query.boolean.modifiers:
            self.assertIsInstance(mod, ModifierClause)
        self.assertEqual(str(query.boolean.modifiers[0].type),
                         'rel.combine')
        self.assertEqual(str(query.boolean.modifiers[0].comparison),
                         '=')
        self.assertEqual(str(query.boolean.modifiers[0].value),
                         'sum')


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(SimpleQueryFactoryTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))