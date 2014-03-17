u"""Cheshire3 DocumentStore Unittests.

DocumentStore configurations may be customized by the user. For the purposes of
unittesting, configuration files will be ignored and DocumentStore instances
will be instantiated using configurations defined within this testing module, 
and tests carried out on those instances using data defined in this module.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import hashlib

from lxml import etree
from datetime import datetime

from cheshire3.document import Document, StringDocument
from cheshire3.documentStore import BdbDocumentStore, DirectoryDocumentStore
from cheshire3.exceptions import ObjectAlreadyExistsException,\
                                 ObjectDoesNotExistException,\
                                 ObjectDeletedException
from cheshire3.test.testBaseStore import SimpleStoreTestCase, BdbStoreTestCase
from cheshire3.test.testBaseStore import DirectoryStoreTestCase


class DocumentStoreTestCase(SimpleStoreTestCase):
    
    def _get_test_docs(self):
        for data in self._get_test_data():
            yield StringDocument(data, byteCount=len(data))

    def test_store_data(self):
        "Check that Doc is stored without corruption to copy in memory."
        for inDoc in self._get_test_docs():
            # Store the Document
            outDoc = self.testObj.create_document(self.session, inDoc)
            # Check that returned doc is unaltered
            self.assertEqual(outDoc.get_raw(self.session),
                             inDoc.get_raw(self.session),
                             u"Returned document content not as expected")

    def test_storeFetch_data(self):
        "Check that Doc is stored without corruption."
        for inDoc in self._get_test_docs():
            # Store the Document
            inDoc = self.testObj.create_document(self.session, inDoc)
            # Fetch the Document
            outDoc = self.testObj.fetch_document(self.session, inDoc.id)
            # Check returned object is instance of Document
            self.assertIsInstance(outDoc, Document)
            # Check that returned doc content is unaltered
            self.assertEqual(outDoc.get_raw(self.session),
                             inDoc.get_raw(self.session),
                             u"Returned document content not as expected")

    def test_storeFetch_metadata(self):
        "Check that metadata is stored and fetched without alteration."
        for inDoc in self._get_test_docs():
            # Assign some metadata
            # Get the current date and time
            now = datetime.utcnow()
            inDoc.metadata['creationDate'] = now
            # Add a checksum
            h = hashlib.new('md5')
            h.update(inDoc.get_raw(self.session))
            md = {
                'md5': {
                    'hexdigest': h.hexdigest(),
                    'analysisDateTime': now
                }
            }
            try:
                inDoc.metadata['checksum'].update(md)
            except KeyError:
                inDoc.metadata['checksum'] = md
            # Store the data
            self.testObj.create_document(self.session, inDoc)
            # Fetch the metadata
            byteCount = self.testObj.fetch_metadata(self.session, inDoc.id,
                                                    'byteCount')
            creationDate = self.testObj.fetch_metadata(self.session, inDoc.id,
                                                    'creationDate')
            checksums = self.testObj.fetch_metadata(self.session, inDoc.id,
                                                    'checksum')
            # Check that stored and fetched metadata are the same
            self.assertEqual(byteCount, len(inDoc.get_raw(self.session)))
            self.assertEqual(creationDate, now)
            self.assertDictEqual(checksums['md5'], md['md5'])
            

    def test_storeDeleteFetch_data(self):
        "Check that Document is deleted."
        for inDoc in self._get_test_docs():
            # Store the Document
            inDoc = self.testObj.create_document(self.session, inDoc)
            # Fetch the Document
            outDoc = self.testObj.fetch_document(self.session, inDoc.id)
            # Check that returned doc is unaltered
            self.assertEqual(outDoc.get_raw(self.session),
                             inDoc.get_raw(self.session),
                             u"Returned document content not as expected")
            # Delete the Document
            self.testObj.delete_document(self.session, inDoc.id)
            # Check that deleted data no longer exists / evaluates as false
            self.assertRaises(ObjectDoesNotExistException,
                              self.testObj.fetch_document,
                              self.session, inDoc.id)


class BdbDocumentStoreTestCase(DocumentStoreTestCase, BdbStoreTestCase):

    @classmethod
    def _get_class(cls):
        return BdbDocumentStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="documentStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


class DeletionsBdbDocumentStoreTestCase(BdbDocumentStoreTestCase):
    "BerkeleyDB based persistent Document storage with stored deletions."

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
        for inDoc in self._get_test_docs():
            # Store the Document
            inDoc = self.testObj.create_document(self.session, inDoc)
            # Fetch the Document
            outDoc = self.testObj.fetch_document(self.session, inDoc.id)
            # Check that returned doc is unaltered
            self.assertEqual(outDoc.get_raw(self.session),
                             inDoc.get_raw(self.session),
                             u"Returned document content not as expected")
            # Delete the Document
            self.testObj.delete_document(self.session, inDoc.id)
            # Check that deleted data no longer exists / evaluates as false
            self.assertRaises(ObjectDeletedException,
                              self.testObj.fetch_document,
                              self.session, inDoc.id)


class DirectoryDocumentStoreTestCase(DocumentStoreTestCase,
                                     DirectoryStoreTestCase):
    "Tests for simple file system directory based DocumentStore."

    @classmethod
    def _get_class(cls):
        return DirectoryDocumentStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="documentStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{1}/store</path>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))

    def test_store_data(self):
        "Check that Doc is stored without corruption to copy in memory."
        theoreticalSize = 0
        for inDoc in self._get_test_docs():
            # Store the Document
            outDoc = self.testObj.create_document(self.session, inDoc)
            theoreticalSize += 1
            # Check that Store returns the correct size
            self.assertEqual(self.testObj.get_dbSize(self.session),
                             theoreticalSize)
            # Check that returned doc is unaltered
            self.assertEqual(outDoc.get_raw(self.session),
                             inDoc.get_raw(self.session),
                             u"Returned document content not as expected")


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(BdbDocumentStoreTestCase)
    suite.addTests(ltc(DeletionsBdbDocumentStoreTestCase))
    suite.addTests(ltc(DirectoryDocumentStoreTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
