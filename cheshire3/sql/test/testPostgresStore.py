u"""Cheshire3 PostgresStore Unittests.

Store configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Store instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on instances.

baseStore contains base classes for stores for various types of objects:
Users, Records, Documents, etc.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.sql.postgresStore import PostgresStore
from cheshire3.test.testBaseStore import SimpleStoreTestCase


class PostgresStoreTestCase(SimpleStoreTestCase):
    "Base Class for BerkeleyDB based persistent storage mechanisms tests."

    @classmethod
    def _get_class(cls):
        return PostgresStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="postgresStore" id="{0.__name__}">
          <objectType>cheshire3.sql.postgresStore.{0.__name__}</objectType>
          <paths>
              <path type="tableName">{0.__name__}</path>
          </paths>
        </subConfig>'''.format(self._get_class()))


class BackwardCompatibilityPostgresStoreTestCase(SimpleStoreTestCase):
    "Base Class for BerkeleyDB based persistent storage mechanisms tests."

    @classmethod
    def _get_class(cls):
        return PostgresStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="postgresStore" id="{0.__name__}">
          <objectType>cheshire3.sql.postgresStore.{0.__name__}</objectType>
          <paths>
              <path type="databaseName">cheshire3</path>
              <path type="tableName">{0.__name__}</path>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


class UuidPostgresStoreTestCase(PostgresStoreTestCase):
    "BerkeleyDB based persistent storage mechanisms with UUID identifiers."

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>cheshire3.sql.postgresStore.{0.__name__}</objectType>
          <paths>
              <path type="tableName">{0.__name__}</path>
          </paths>
          <options>
            <setting type="useUUID">1</setting>
          </options>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


class DeletionsPostgresStoreTestCase(PostgresStoreTestCase):
    "BerkeleyDB based persistent storage mechanisms with stored deletions."

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>cheshire3.sql.postgresStore.{0.__name__}</objectType>
          <paths>
              <path type="tableName">{0.__name__}</path>
          </paths>
          <options>
            <setting type="storeDeletions">1</setting>
          </options>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(PostgresStoreTestCase)
    suite.addTests(ltc(UuidPostgresStoreTestCase))
    suite.addTests(ltc(DeletionsPostgresStoreTestCase))
    return suite

if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
