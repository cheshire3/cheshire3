u"""Cheshire3 RecordStore Unittests.

RecordStore configurations may be customized by the user. For the purposes of
unittesting, configuration files will be ignored and RecordStore instances
will be instantiated using configurations defined within this testing module, 
and tests carried out on those instances using data defined in this module.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import string
import random

from lxml import etree
from datetime import datetime

from cheshire3.record import Record, LxmlRecord
from cheshire3.recordStore import BdbRecordStore, DirectoryRecordStore
from cheshire3.exceptions import ObjectAlreadyExistsException,\
                                 ObjectDoesNotExistException,\
                                 ObjectDeletedException
from cheshire3.test.testBaseStore import SimpleStoreTestCase, BdbStoreTestCase
from cheshire3.test.testBaseStore import DirectoryStoreTestCase


class RecordStoreTestCase(SimpleStoreTestCase):

    def _get_test_data(self):
        chars = string.uppercase + string.lowercase + string.digits
        for x in range(5):
            # Generate a random string of data
            l = random.randint(100, 100000)
            yield ''.join([random.choice(chars) for x in range(l)])

    def _get_test_recs(self):
        for data in self._get_test_data():
            node = etree.Element('data')
            node.text = data
            xml = etree.tostring(node)
            yield LxmlRecord(node, xml=xml, byteCount=len(xml))

    def test_store_data(self):
        "Check that Rec is stored without corruption to copy in memory."
        for inRec in self._get_test_recs():
            # Store the Record
            outRec = self.testObj.create_record(self.session, inRec)
            # Check that returned doc is unaltered
            self.assertEqual(outRec.get_xml(self.session),
                             inRec.get_xml(self.session),
                             u"Returned record content not as expected")

    def test_storeFetch_data(self):
        "Check that Record is stored without corruption."
        for inRec in self._get_test_recs():
            # Store the Record
            inRec = self.testObj.create_record(self.session, inRec)
            # Fetch the Record
            outRec = self.testObj.fetch_record(self.session, inRec.id)
            # Check returned object is instance of Record
            self.assertIsInstance(outRec, Record)
            # Check that returned doc content is unaltered
            self.assertEqual(outRec.get_xml(self.session),
                             inRec.get_xml(self.session),
                             u"Returned record content not as expected")

    def test_storeFetch_metadata(self):
        "Check that metadata is stored and fetched without alteration."
        for inRec in self._get_test_recs():
            # Assign some metadata
            # Get the current date and time
            now = datetime.utcnow()
            inRec.metadata['creationDate'] = now
            # Store the data
            self.testObj.create_record(self.session, inRec)
            # Fetch the metadata
            byteCount = self.testObj.fetch_metadata(self.session, inRec.id,
                                                    'byteCount')
            creationDate = self.testObj.fetch_metadata(self.session, inRec.id,
                                                    'creationDate')
            # Check that stored and fetched metadata are the same
            self.assertEqual(byteCount, len(inRec.get_xml(self.session)))
            self.assertEqual(creationDate, now)

    def test_storeDeleteFetch_data(self):
        "Check that Record is deleted."
        for inRec in self._get_test_recs():
            # Store the Record
            inRec = self.testObj.create_record(self.session, inRec)
            # Fetch the Record
            outRec = self.testObj.fetch_record(self.session, inRec.id)
            # Check that returned doc is unaltered
            self.assertEqual(outRec.get_xml(self.session),
                             inRec.get_xml(self.session),
                             u"Returned record content not as expected")
            # Delete the Record
            self.testObj.delete_record(self.session, inRec.id)
            # Check that deleted data no longer exists / evaluates as false
            self.assertRaises(ObjectDoesNotExistException,
                              self.testObj.fetch_record,
                              self.session, inRec.id)


class BdbRecordStoreTestCase(RecordStoreTestCase, BdbStoreTestCase):

    @classmethod
    def _get_class(cls):
        return BdbRecordStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="recordStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
              <object type="idNormalizer" ref="StringIntNormalizer"/>
              <object type="inTransformer" ref="XmlTransformer"/>
              <object type="outParser" ref="LxmlParser"/>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


class DeletionsBdbRecordStoreTestCase(BdbRecordStoreTestCase):
    "BerkeleyDB based persistent Record storage with stored deletions."

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="recordStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{0.__name__}.bdb</path>
              <object type="idNormalizer" ref="StringIntNormalizer"/>
              <object type="inTransformer" ref="XmlTransformer"/>
              <object type="outParser" ref="LxmlParser"/>
          </paths>
          <options>
            <setting type="storeDeletions">1</setting>
          </options>
        </subConfig>'''.format(self._get_class(), self.defaultPath))

    def test_storeDeleteFetch_data(self):
        "Check that Record is deleted."
        for inRec in self._get_test_recs():
            # Store the Record
            inRec = self.testObj.create_record(self.session, inRec)
            # Fetch the Record
            outRec = self.testObj.fetch_record(self.session, inRec.id)
            # Check that returned doc is unaltered
            self.assertEqual(outRec.get_xml(self.session),
                             inRec.get_xml(self.session),
                             u"Returned record content not as expected")
            # Delete the Record
            self.testObj.delete_record(self.session, inRec.id)
            # Check that deleted data no longer exists / evaluates as false
            self.assertRaises(ObjectDeletedException,
                              self.testObj.fetch_record,
                              self.session, inRec.id)


class DirectoryRecordStoreTestCase(RecordStoreTestCase,
                                   DirectoryStoreTestCase):
    "Tests for simple file system directory based RecordStore."

    @classmethod
    def _get_class(cls):
        return DirectoryRecordStore

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="recordStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="defaultPath">{1}</path>
              <path type="databasePath">{1}/store</path>
              <object type="inTransformer" ref="XmlTransformer"/>
              <object type="outParser" ref="LxmlParser"/>
          </paths>
        </subConfig>'''.format(self._get_class(), self.defaultPath))


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(BdbRecordStoreTestCase)
    suite.addTests(ltc(DeletionsBdbRecordStoreTestCase))
    suite.addTests(ltc(DirectoryRecordStoreTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
