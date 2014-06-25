u"""Cheshire3 Web QueryFactory Unittests.

QueryFactory configurations may be customized by the user. For the purposes
of unittesting, configuration files will be ignored and QueryFactory instances
will be instantiated using configuration data defined within this testing
module, and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.cqlParser import *
from cheshire3.queryFactory import SimpleQueryFactory
from cheshire3.web.www_utils import FieldStorageDict
from cheshire3.test.testQueryFactory import SimpleQueryFactoryTestCase


class WwwQueryFactoryTestCase(SimpleQueryFactoryTestCase):
    """Cheshire3 SimpleQueryFactory Test Case."""

    def _get_class(self):
        return SimpleQueryFactory

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="documentFactory" id="{0.__name__}">
            <objectType>cheshire3.queryFactory.{0.__name__}</objectType>
        </subConfig>'''.format(self._get_class()))

    def test_get_query_clause_www(self):
        "Test simple clause."
        form  = FieldStorageDict(
            fieldidx1='cql.anywhere',
            fieldrel1='all',
            fieldcont1='spam'
        )
        query = self.testObj.get_query(
            self.session,
            form,
            format='www'
        )
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

    def test_get_query_clause2_www(self):
        "Test simple clause with multiple terms."
        form  = FieldStorageDict(
            fieldidx1='cql.anywhere',
            fieldrel1='all',
            fieldcont1='spam eggs'
        )
        query = self.testObj.get_query(
            self.session,
            form,
            format='www'
        )
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
        self.assertEqual(query.term.value, 'spam eggs')

    def test_get_query_triple_www(self):
        "Test query with boolean."
        form  = FieldStorageDict(
            fieldidx1='cql.anywhere',
            fieldrel1='all',
            fieldcont1='spam',
            fieldbool1='and',
            fieldidx2='cql.anywhere',
            fieldrel2='all',
            fieldcont2='eggs'
        )
        query = self.testObj.get_query(
            self.session,
            form,
            format='www'
        )
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

    def test_get_query_triple2_www(self):
        "Test query with boolean and multiple terms."
        form  = FieldStorageDict(
            fieldidx1='cql.anywhere',
            fieldrel1='all',
            fieldcont1='spam',
            fieldbool1='and',
            fieldidx2='cql.anywhere',
            fieldrel2='all',
            fieldcont2='eggs bacon'
        )
        query = self.testObj.get_query(
            self.session,
            form,
            format='www'
        )
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
                         u'cql.anywhere all "eggs bacon"')

    def test_get_query_triple_www_compound(self):
        "Test query with boolean and multiple indexes."
        form  = FieldStorageDict(
            fieldidx1='cql.anywhere||dc.description',
            fieldrel1='all',
            fieldcont1='spam',
        )
        query = self.testObj.get_query(
            self.session,
            form,
            format='www'
        )
        # Check query instance
        self.assertIsInstance(query, Triple)
        # Check left clause
        self.assertIsInstance(query.leftOperand, SearchClause)
        # remember terms get quoted during parsing
        self.assertEqual(query.leftOperand.toCQL(),
                         u'cql.anywhere all "spam"')
        # Check boolean
        self.assertIsInstance(query.boolean, Boolean)
        self.assertEqual(query.boolean.value, 'or')
        # Check right clause
        self.assertIsInstance(query.rightOperand, SearchClause)
        # remember terms get quoted during parsing
        self.assertEqual(query.rightOperand.toCQL(),
                         u'dc.description all "spam"')

    def test_get_query_triple_www_compound_phrase(self):
        "Test query with boolean and multiple indexes with internal phrase."
        form  = FieldStorageDict(
            fieldidx1='cql.anywhere||dc.description',
            fieldrel1='all',
            fieldcont1='spam "eggs and bacon"',
        )
        query = self.testObj.get_query(
            self.session,
            form,
            format='www'
        )
        # Check query instance
        self.assertIsInstance(query, Triple)
        # Check left clause
        self.assertIsInstance(query.leftOperand, Triple)
        # Remember terms get quoted during parsing
        self.assertEqual(
            query.leftOperand.leftOperand.toCQL(),
            u'cql.anywhere =/cql.relevant/cql.proxinfo "eggs and bacon"'
        )
        self.assertEqual(query.leftOperand.boolean.value,
                         u'and')
        self.assertEqual(
            query.leftOperand.rightOperand.toCQL(),
            u'cql.anywhere all "spam"'
        )
        # Check boolean
        self.assertIsInstance(query.boolean, Boolean)
        self.assertEqual(query.boolean.value, 'or')
        # Check right clause
        self.assertIsInstance(query.rightOperand, Triple)
        # Remember terms get quoted during parsing
        self.assertEqual(
            query.rightOperand.leftOperand.toCQL(),
            u'dc.description =/cql.relevant/cql.proxinfo "eggs and bacon"'
        )
        self.assertEqual(query.rightOperand.boolean.value,
                         u'and')
        self.assertEqual(
            query.rightOperand.rightOperand.toCQL(),
            u'dc.description all "spam"'
        )


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(WwwQueryFactoryTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))