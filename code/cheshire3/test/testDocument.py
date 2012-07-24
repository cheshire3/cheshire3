"""Cheshire3 Document Unittests."""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from cheshire3.baseObjects import Session
from cheshire3.document import StringDocument


class StringDocumentTestCase(unittest.TestCase):

    def setUp(self):
        self.session = Session()
        self.testPairs = [('application/xml',
                           '<doc><foo/><bar><baz/></baz></doc>',
                           []),
                          ('text/plain',
                           'This is my document!',
                           ['aProcessingObject'])
                          ]
        self.testDocs = []
        for mt, data, processHistory in self.testPairs:
            self.testDocs.append(StringDocument(data, mimeType=mt,
                                                creator=id(self),
                                                history=processHistory,
                                                byteCount=len(data),
                                                wordCount=len(data.split(' '))
                                                )
                                 )

    def tearDown(self):
        pass

    def test_instance(self):
        """Test that StringDocument instance is correctly init'd."""
        for (mt, data, processHistory), doc in zip(self.testPairs,
                                                   self.testDocs):
            self.assertIsInstance(doc, StringDocument)

    def test_mimeType(self):
        """Test that mimeType is set correctly."""
        for (mt, data, processHistory), doc in zip(self.testPairs,
                                                   self.testDocs):
            self.assertEqual(doc.mimeType, mt)

    def test_processHistory(self):
        """Test that processHistory is copied correctly."""
        for (mt, data, processHistory), doc in zip(self.testPairs,
                                                   self.testDocs):
            for i, ident in enumerate(processHistory):
                self.assertEqual(ident, doc.processHistory[i])

    def test_byteCount(self):
        """Test that byteCount is correctly set."""
        for (mt, data, processHistory), doc in zip(self.testPairs,
                                                   self.testDocs):
            self.assertEqual(len(data), doc.byteCount)

    def test_wordCount(self):
        """Test that wordCount is correctly set."""
        for (mt, data, processHistory), doc in zip(self.testPairs,
                                                   self.testDocs):
            self.assertEqual(len(data.split(' ')), doc.wordCount)

    def test_creator(self):
        """Test that creator is appended to processHistory."""
        for doc in self.testDocs:
            self.assertEqual(doc.processHistory[-1], id(self))

    def test_get_raw(self):
        """Test that doc.get_raw() returns correct data."""
        for (mt, data, processHistory), doc in zip(self.testPairs,
                                                   self.testDocs):
            self.assertEqual(data, doc.get_raw(self.session))


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(StringDocumentTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
