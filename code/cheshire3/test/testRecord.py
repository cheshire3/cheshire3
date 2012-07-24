"""Cheshire3 Document Unittests."""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from xml.dom.minidom import parseString as minidomParseString
from lxml.etree import fromstring as lxmlParseString, tostring as lxmlToString

from cheshire3.baseObjects import Session
from cheshire3.baseObjects import Record
from cheshire3.record import MinidomRecord, LxmlRecord, SaxRecord


class RecordTestCase(unittest.TestCase):
    
    def _get_data(self):
        # Generator to yield data to be parsed into records
        yield ('<doc>'
               '<el attr="value">text</el>'  # element with attribute
               '<el>text</el>tail'           # element with tail text
               '<empty-el/>'                 # empty/self-closing element
               '</doc>')
        # Default namespaced example
        yield ('<doc xmlns="http://example.com/schemas/doc">'
               '<el attr="value">text</el>'  # element with attribute
               '<el>text</el>tail'           # element with tail text
               '<empty-el/>'                 # empty/self-closing element
               '</doc>')
        # Prefixed namespaced example
        yield ('<doc:doc xmlns:doc="http://example.com/schemas/doc">'
               '<doc:el attr="value">text</doc:el>'  # element with attribute
               '<doc:el>text</doc:el>tail'           # element with tail text
               '<doc:empty-el/>'                   # empty/self-closing element
               '</doc:doc>')
        # Unicode example
        yield (u'<doc>'
               u'<el attr="value">text</el>'  # element with attribute
               u'<el>text</el>tail'           # element with tail text
               u'<empty-el/>'                 # empty/self-closing element
               u'</doc>')
    
    def _get_class(self):
        raise NotImplementedError

    def _parse_data(self, data):
        raise NotImplementedError

    def setUp(self):
        self.session = Session()
        self.records = []
        cls = self._get_class()
        for d in self._get_data():
            recHash = {'xml': d,
                       'record': cls(self._parse_data(d),
                                     xml=d,
                                     byteCount=len(d))
                       }
            
            self.records.append(recHash)

    def tearDown(self):
        pass

    def test_instances(self):
        """Test that Record instance is correctly init'd."""
        cls = self._get_class()
        for recHash in self.records:
            rec = recHash['record']
            self.assertIsInstance(rec, Record)
            self.assertIsInstance(rec, cls)

    def test_byteCount(self):
        """Test that byteCount is correctly set."""
        for recHash in self.records:
            self.assertEqual(recHash['record'].byteCount, len(recHash['xml']))

    def test_get_xml(self):
        """Test that record.get_xml() returns correct XML."""
        for recHash in self.records:
            self.assertEqual(recHash['record'].get_xml(self.session),
                             recHash['xml'])
            

class MinidomRecordTestCase(RecordTestCase):
    
    def _get_class(self):
        return MinidomRecord
    
    def _parse_data(self, data):
        return minidomParseString(data)

    def test_get_dom(self):
        """Test that record.get_dom() returns correct DOM."""
        for recHash in self.records:
            dom = recHash['record'].get_dom(self.session)
            # Cannot do direct equality test on DOMs
            # Compare serialization
            # Serialization may have added an XML declaration
            self.assertRegexpMatches(dom.toxml(),
                                     '(<?xml.*?>)?' + recHash['xml']
                                     )

    def test_process_xpath(self):
        """Test that record.process_xpath() raises NotImplementedError."""
        self.assertRaises(NotImplementedError,
                          self.records[0]['record'].process_xpath,
                          self.session,
                          '/doc/el')


class LxmlRecordTestCase(RecordTestCase):
    
    def _get_class(self):
        return LxmlRecord

    def _parse_data(self, data):
        return lxmlParseString(data)
    
    def test_get_dom(self):
        """Test that record.get_dom() returns correct DOM."""
        for recHash in self.records:
            dom = recHash['record'].get_dom(self.session)
            # Cannot do direct equality test on DOMs
            # Compare serialization
            # Serialization may have added an XML declaration
            self.assertRegexpMatches(lxmlToString(dom),
                                     '(<?xml.*?>)?' + recHash['xml']
                                     )

    def test_process_xpath_raw(self):
        """Test record.process_xpath() non-namespaced."""
        recHash = self.records[0]
        # Test rooted XPath
        xpr = recHash['record'].process_xpath(self.session,
                                              '/doc/el/text()')
        self.assertEqual(len(xpr), 2, 
                         "Expected 2 results, got {0}".format(len(xpr)))
        self.assertEqual(xpr[0], 'text')
        self.assertEqual(xpr[1], 'text')
        # Test unrooted XPath
        xpr = recHash['record'].process_xpath(self.session,
                                              '//empty-el')
        self.assertEqual(len(xpr), 1)
        # Test attribute
        xpr = recHash['record'].process_xpath(self.session,
                                              '/doc/el/@attr')
        self.assertEqual(len(xpr), 1)
        self.assertEqual(xpr[0], 'value')
        
    def test_process_xpath_namespaced(self):
        """Test record.process_xpath() namespaced."""
        nsMap = {'d': "http://example.com/schemas/doc"}
        for recHash in self.records[1:3]:
            # Test rooted XPath
            xpr = recHash['record'].process_xpath(self.session,
                                                  '/d:doc/d:el/text()',
                                                  nsMap)
            self.assertEqual(len(xpr), 2)
            self.assertEqual(xpr[0], 'text')
            self.assertEqual(xpr[1], 'text')
            # Test unrooted XPath
            xpr = recHash['record'].process_xpath(self.session,
                                                  '//d:empty-el',
                                                  nsMap)
            self.assertEqual(len(xpr), 1)
            # Test attribute
            xpr = recHash['record'].process_xpath(self.session,
                                                  '/d:doc/d:el/@attr',
                                                  nsMap)
            self.assertEqual(len(xpr), 1)
            self.assertEqual(xpr[0], 'value')
            
    def test_process_xpath_uc(self):
        """Test record.process_xpath() unicode (data and XPath)."""
        recHash = self.records[3]
        # Test rooted XPath
        xpr = recHash['record'].process_xpath(self.session,
                                              u'/doc/el/text()')
        self.assertEqual(len(xpr), 2, 
                         "Expected 2 results, got {0}".format(len(xpr)))
        self.assertEqual(xpr[0], u'text')
        self.assertEqual(xpr[1], u'text')
        # Test unrooted XPath
        xpr = recHash['record'].process_xpath(self.session,
                                              u'//empty-el')
        self.assertEqual(len(xpr), 1)
        # Test attribute
        xpr = recHash['record'].process_xpath(self.session,
                                              u'/doc/el/@attr')
        self.assertEqual(len(xpr), 1)
        self.assertEqual(xpr[0], u'value')


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(MinidomRecordTestCase)
    suite.addTests(loader.loadTestsFromTestCase(LxmlRecordTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
