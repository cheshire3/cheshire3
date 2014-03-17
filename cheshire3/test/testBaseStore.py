u"""Cheshire3 Base Store Unittests.

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

import os.path
import random
import string

from datetime import datetime
from tempfile import mkdtemp
from shutil import rmtree
from lxml import etree

from cheshire3.baseStore import BdbStore, DeletedObject, FileSystemStore
from cheshire3.baseStore import DirectoryStore
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class SimpleStoreTestCase(Cheshire3ObjectTestCase):
    "Abstract Base Class for persistent storage mechanism test."
    
    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>cheshire3.baseStore.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
          </paths>
        </subConfig>'''.format(self._get_class(),
                               self.defaultPath))
    
    def _get_test_data(self):
        for x in range(5):
            # Generate a random string of data
            l = random.randint(100, 100000)
            yield ''.join([random.choice(string.printable) for y in range(l)])
            
    def setUp(self):
        # Create a tempfile placeholder
        self.defaultPath = mkdtemp(prefix=self.__class__.__name__)
        Cheshire3ObjectTestCase.setUp(self)

    def tearDown(self):
        rmtree(self.defaultPath)

    # Test methods

    def test_generate_id(self):
        "Check identifier generation."
        for data in self._get_test_data():
            ident = self.testObj.generate_id(self.session)
            self.assertIsInstance(ident, int)

    def test_storeFetch_data(self):
        "Check that data is stored and fetched without corruption."
        for data in self._get_test_data():
            # Assign an identifier
            ident = self.testObj.generate_id(self.session)
            # Store the data
            self.testObj.store_data(self.session, ident, data)
            # Fetch the data
            data2 = self.testObj.fetch_data(self.session, ident)
            # Check that generated and fetched are the same
            self.assertEqual(data2, data, "Retrieved data != stored data")

    def test_storeFetch_metadata(self):
        "Check that metadata is stored and fetched without corruption."
        for data in self._get_test_data():
            # Assign an identifier
            ident = self.testObj.generate_id(self.session)
            # Get the current date and time
            now = datetime.utcnow()
            # Store the data
            self.testObj.store_data(self.session, ident, data,
                                    metadata={
                                        'byteCount': len(data),
                                        'creationDate': now
                                    })
            # Fetch the metadata
            byteCount = self.testObj.fetch_metadata(self.session, ident,
                                                    'byteCount')
            creationDate = self.testObj.fetch_metadata(self.session, ident,
                                                    'creationDate')
            # Check that stored and fetched metadata are the same
            self.assertEqual(byteCount, len(data))
            self.assertEqual(creationDate, now)

    def test_storeDeleteFetch_data(self):
        "Check that data is deleted."
        for data in self._get_test_data():
            # Assign an identifier
            ident = self.testObj.generate_id(self.session)
            # Store the data
            self.testObj.store_data(self.session, ident, data)
            # Fetch the data
            data2 = self.testObj.fetch_data(self.session, ident)
            # Check that generated and fetched are the same
            self.assertEqual(data2, data, "Retrieved data != stored data")
            # Delete the data
            self.testObj.delete_data(self.session, ident)
            # Check that deleted data no longer exists / evaluates as false
            data2 = self.testObj.fetch_data(self.session, ident)
            self.assertFalse(data2)

    def test_clear(self):
        "Check that clear method empties the store."
        for data in self._get_test_data():
            # Assign an identifier
            ident = self.testObj.generate_id(self.session)
            # Store the data
            self.testObj.store_data(self.session, ident, data)
            # Fetch the data
            data2 = self.testObj.fetch_data(self.session, ident)
            # Check that generated and fetched are the same
            self.assertEqual(data2, data, "Retrieved data != stored data")
            # Clear the data
            self.testObj.clear(self.session)
            # Check that deleted data no longer exists / evaluates as false
            data2 = self.testObj.fetch_data(self.session, ident)
            self.assertFalse(data2)


class BdbStoreTestCase(SimpleStoreTestCase):
    "Base Class for BerkeleyDB based persistent storage mechanisms tests."

    @classmethod
    def _get_class(cls):
        return BdbStore
    
    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>cheshire3.baseStore.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


class UuidBdbStoreTestCase(BdbStoreTestCase):
    "BerkeleyDB based persistent storage mechanisms with UUID identifiers."

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>cheshire3.baseStore.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
          </paths>
          <options>
            <setting type="useUUID">1</setting>
          </options>
        </subConfig>'''.format(self._get_class(), self.defaultPath))

    def test_generate_id(self):
        "Check identifier generation."
        for x in range(100):
            ident = self.testObj.generate_id(self.session)
            self.assertIsInstance(ident, str)


class DeletionsBdbStoreTestCase(BdbStoreTestCase):
    "BerkeleyDB based persistent storage mechanisms with stored deletions."

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>cheshire3.baseStore.{0.__name__}</objectType>
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
        for data in self._get_test_data():
            # Assign an identifier
            ident = self.testObj.generate_id(self.session)
            # Store the data
            self.testObj.store_data(self.session, ident, data)
            # Fetch the data
            data2 = self.testObj.fetch_data(self.session, ident)
            # Check that generated and fetched are the same
            self.assertEqual(data2, data, "Retrieved data != stored data")
            # Delete the data
            self.testObj.delete_data(self.session, ident)
            # Check that deleted data no longer exists / evaluates as false
            data2 = self.testObj.fetch_data(self.session, ident)
            self.assertIsInstance(data2, DeletedObject,
                                  "Data deletion not stored")


class UserPathBdbStoreTestCase(BdbStoreTestCase):
    "BerkeleyDB storage with user home directory based file path."
    
    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>cheshire3.baseStore.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))

    def setUp(self):
        # Create a tempfile placeholder
        userPath = '~/.cheshire3-server'
        tempPath = mkdtemp("", "test", os.path.expanduser(userPath))
        self.defaultPath = os.path.join(userPath,
                                        os.path.split(tempPath)[-1])
        Cheshire3ObjectTestCase.setUp(self)

    def tearDown(self):
        defaultPath = os.path.expanduser(self.defaultPath)
        rmtree(defaultPath)


class FileSystemStoreTestCase(SimpleStoreTestCase):
    "Tests for file system based store."
    
    @classmethod
    def _get_class(cls):
        return FileSystemStore

    # Test methods

    def test_storeFetch_data(self):
        "Check that data is stored and fetched without corruption."
        for data in self._get_test_data():
            # Assign a random identifier
            ident = ''.join([random.choice(string.lowercase)
                             for x in range(10)])
            # Write the data to the file
            # N.B. FileSystemDataStore assumes file already exists
            filepath = os.path.join(self.defaultPath, ident)
            with open(filepath, 'w') as fh:
                fh.write(data)
            # Store the data
            self.testObj.begin_storing(self.session)
            self.testObj.store_data(self.session, ident, data,
                                    metadata={
                                        'filename': filepath,
                                        'byteCount': len(data),
                                        'byteOffset': 0,
                                    })
            self.testObj.commit_storing(self.session)
            # Fetch the data
            data2 = self.testObj.fetch_data(self.session, ident)
            # Check that generated and fetched are the same
            self.assertEqual(data2, data, "Retrieved data != stored data")

    def test_storeDeleteFetch_data(self):
        "Check that data is stored, fetched and deleted."
        for data in self._get_test_data():
            # Assign a random identifier
            ident = ''.join([random.choice(string.lowercase)
                             for x in range(10)])
            # Write the data to the file
            # N.B. FileSystemDataStore assumes file already exists
            filepath = os.path.join(self.defaultPath, ident)
            with open(filepath, 'w') as fh:
                fh.write(data)
            # Store the data
            self.testObj.begin_storing(self.session)
            self.testObj.store_data(self.session, ident, data,
                                    metadata={
                                        'filename': filepath,
                                        'byteCount': len(data),
                                        'byteOffset': 0,
                                    })
            self.testObj.commit_storing(self.session)
            # Fetch the data
            data2 = self.testObj.fetch_data(self.session, ident)
            # Check that generated and fetched are the same
            self.assertEqual(data2, data, "Retrieved data != stored data")
            # Delete the data
            self.testObj.delete_data(self.session, ident)
            # Check that deleted data no longer exists / evaluates as false
            data3 = self.testObj.fetch_data(self.session, ident)
            self.assertFalse(data3)
            
    def test_storeFetch_metadata(self):
        "Check that metadata is stored and fetched without corruption."
        for data in self._get_test_data():
            # Assign a random identifier
            ident = ''.join([random.choice(string.lowercase)
                             for x in range(10)])
            # Write the data to the file
            # N.B. FileSystemDataStore assumes file already exists
            filepath = os.path.join(self.defaultPath, ident)
            with open(filepath, 'w') as fh:
                fh.write(data)
            # Get the current date and time
            now = datetime.utcnow()
            # Store the data
            self.testObj.begin_storing(self.session)
            self.testObj.store_data(self.session, ident, data,
                                    metadata={
                                        'filename': filepath,
                                        'byteCount': len(data),
                                        'byteOffset': 0,
                                        'creationDate': now
                                    })
            self.testObj.commit_storing(self.session)
            # Fetch the metadata
            byteCount = self.testObj.fetch_metadata(self.session, ident,
                                                    'byteCount')
            creationDate = self.testObj.fetch_metadata(self.session, ident,
                                                    'creationDate')
            # Check that stored and fetched metadata are the same
            self.assertEqual(byteCount, len(data))
            self.assertEqual(creationDate, now)

    def test_clear(self):
        "Check that clear method empties the store."
        for data in self._get_test_data():
            # Assign a random identifier
            ident = ''.join([random.choice(string.lowercase)
                             for x in range(10)])
            # Write the data to the file
            # N.B. FileSystemDataStore assumes file already exists
            filepath = os.path.join(self.defaultPath, ident)
            with open(filepath, 'w') as fh:
                fh.write(data)
            # Store the data
            self.testObj.begin_storing(self.session)
            self.testObj.store_data(self.session, ident, data,
                                    metadata={
                                        'filename': filepath,
                                        'byteCount': len(data),
                                        'byteOffset': 0,
                                    })
            self.testObj.commit_storing(self.session)
            # Fetch the data
            data2 = self.testObj.fetch_data(self.session, ident)
            # Check that generated and fetched are the same
            self.assertEqual(data2, data, "Retrieved data != stored data")
            # Clear the data
            self.testObj.clear(self.session)
            # Check that deleted data no longer exists / evaluates as false
            data2 = self.testObj.fetch_data(self.session, ident)
            self.assertFalse(data2)


class DirectoryStoreTestCase(BdbStoreTestCase):
    "Tests for simple file system directory based store."

    @classmethod
    def _get_class(cls):
        return DirectoryStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>cheshire3.baseStore.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{1}/store</path>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))

    def test_slashIdentifier(self):
        """Test storing to an identifier containing a slash.

        Test storing to an identifier containing a character that could be
        interpreted as a path separator by the OS filesystem.
        """
        for data in self._get_test_data():
            # Assign an identifier
            ident = self.testObj.generate_id(self.session)
            # Put an os path separator in the identifier
            ident = os.path.join(str(ident), '1')
            # Store the data
            self.testObj.store_data(self.session, ident, data)
            # Fetch the data
            data2 = self.testObj.fetch_data(self.session, ident)
            # Check that generated and fetched are the same
            self.assertEqual(data2, data, "Retrieved data != stored data")


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(BdbStoreTestCase)
    suite.addTests(ltc(UuidBdbStoreTestCase))
    suite.addTests(ltc(DeletionsBdbStoreTestCase))
    suite.addTests(ltc(UserPathBdbStoreTestCase))
    suite.addTests(ltc(FileSystemStoreTestCase))
    suite.addTests(ltc(DirectoryStoreTestCase))
    return suite

if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
