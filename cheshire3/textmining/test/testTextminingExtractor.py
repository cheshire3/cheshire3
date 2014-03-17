u"""Cheshire3 Textmining Extractor Unittests.

Extractor configurations may be customized by the user. For the purposes of
unittesting, configuration files will be ignored and Extractor instances will
be instantiated using configuration data defined within this testing module,
and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.exceptions import ConfigFileException
from cheshire3.textmining.extractor import NLTKNamedEntityExtractor
from cheshire3.test.testExtractor import SimpleExtractorTestCase


class NLTKNamedEntityExtractorTestCase(SimpleExtractorTestCase):

    text = """\
Now, it is a fact, that there was nothing at all
particular about the knocker on the door, except that it
was very large. It is also a fact, that Scrooge had
seen it, night and morning, during his whole residence
in that place; also that Scrooge had as little of what
is called fancy about him as any man in the city of
London, even including--which is a bold word--the
corporation, aldermen, and livery. Let it also be
borne in mind that Scrooge had not bestowed one
thought on Marley, since his last mention of his
seven years' dead partner that afternoon. And then
let any man explain to me, if he can, how it happened
that Scrooge, having his key in the lock of the door,
saw in the knocker, without its undergoing any intermediate
process of change--not a knocker, but Marley's face.

...

"And the Union workhouses?" demanded Scrooge.
"Are they still in operation?"
"""

    @classmethod
    def _get_class(cls):
        return NLTKNamedEntityExtractor

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="extractor" id="{0.__name__}">
          <objectType>cheshire3.textmining.extractor.{0.__name__}</objectType>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        # Return a list of tuples containing test pairs:
        # (string to be tokenized, expected tokens list)
        return [(self.text,
                 {'Scrooge': {
                      'text': 'Scrooge',
                      'occurences': self.text.count('Scrooge'),
                      'proxLoc': [-1] * self.text.count('Scrooge')
                      },
                  'Marley': {
                      'text': 'Marley',
                      'occurences': self.text.count('Marley'),
                      'proxLoc': [-1] * self.text.count('Marley')
                      },
                  'London': {
                      'text': 'London',
                      'occurences': self.text.count('London'),
                      'proxLoc': [-1] * self.text.count('London')
                      },
                  'Union': {
                      'text': 'Union',
                      'occurences': self.text.count('Union'),
                      'proxLoc': [-1] * self.text.count('Union')
                      }
                  })]

    def _get_process_node_tests(self):
        return [(etree.XML('<data>{0}</data>'.format(self.text)),
                 {'Scrooge': {
                      'text': 'Scrooge',
                      'occurences': self.text.count('Scrooge'),
                      'proxLoc': [-1] * self.text.count('Scrooge')
                      },
                  'Marley': {
                      'text': 'Marley',
                      'occurences': self.text.count('Marley'),
                      'proxLoc': [-1] * self.text.count('Marley')
                      },
                  'London': {
                      'text': 'London',
                      'occurences': self.text.count('London'),
                      'proxLoc': [-1] * self.text.count('London')
                      },
                  'Union': {
                      'text': 'Union',
                      'occurences': self.text.count('Union'),
                      'proxLoc': [-1] * self.text.count('Union')
                      }
                  })]

    def _get_process_xpathResult_tests(self):
        tests = []
        for inp, expected in self._get_process_string_tests():
            tests.append(([[inp]], expected))
        for inp, expected in self._get_process_node_tests():
            tests.append(([[inp]], expected))
        return tests

    def test_process_string(self):
        for inp, expected in self._get_process_string_tests():
            output = self.testObj.process_string(self.session, inp)
            self.assertDictEqual(output, expected)

    def test_process_node(self):
        for inp, expected in self._get_process_node_tests():
            output = self.testObj.process_node(self.session, inp)
            self.assertDictEqual(output, expected)


class NLTKPersonNameExtractorTestCase(NLTKNamedEntityExtractorTestCase):
    """Test a NamedEntityExtractor configured to extract only People."""

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="extractor" id="{0.__name__}">
          <objectType>cheshire3.textmining.extractor.{0.__name__}</objectType>
          <options>
            <setting type="entityTypes">PERSON</setting>
          </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        # Return a list of tuples containing test pairs:
        # (string to be tokenized, expected tokens list)
        return [(self.text,
                 {'Scrooge': {
                      'text': 'Scrooge',
                      'occurences': self.text.count('Scrooge'),
                      'proxLoc': [-1] * self.text.count('Scrooge')
                      },
                  'Marley': {
                      'text': 'Marley',
                      'occurences': self.text.count('Marley'),
                      'proxLoc': [-1] * self.text.count('Marley')
                      }
                  })]

    def _get_process_node_tests(self):
        return [(etree.XML('<data>{0}</data>'.format(self.text)),
                 {'Scrooge': {
                      'text': 'Scrooge',
                      'occurences': self.text.count('Scrooge'),
                      'proxLoc': [-1] * self.text.count('Scrooge')
                      },
                  'Marley': {
                      'text': 'Marley',
                      'occurences': self.text.count('Marley'),
                      'proxLoc': [-1] * self.text.count('Marley')
                      }
                  })]


class NLTKPeopleNameExtractorTestCase(NLTKPersonNameExtractorTestCase):
    """Test a NamedEntityExtractor configured to extract only People.

    NLTKPersonNameExtractorTestCase but with variation in config.
    """

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="extractor" id="{0.__name__}">
          <objectType>cheshire3.textmining.extractor.{0.__name__}</objectType>
          <options>
            <setting type="entityTypes">people</setting>
          </options>
        </subConfig>'''.format(self._get_class()))


class NLTKPlaceNameExtractorTestCase(NLTKNamedEntityExtractorTestCase):
    """Test a NamedEntityExtractor configured to extract only Places."""

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="extractor" id="{0.__name__}">
          <objectType>cheshire3.textmining.extractor.{0.__name__}</objectType>
          <options>
            <setting type="entityTypes">PLACE</setting>
          </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        # Return a list of tuples containing test pairs:
        # (string to be tokenized, expected tokens list)
        return [(self.text,
                 {'London': {
                      'text': 'London',
                      'occurences': self.text.count('London'),
                      'proxLoc': [-1] * self.text.count('London')
                      }
                  })]

    def _get_process_node_tests(self):
        return [(etree.XML('<data>{0}</data>'.format(self.text)),
                 {'London': {
                      'text': 'London',
                      'occurences': self.text.count('London'),
                      'proxLoc': [-1] * self.text.count('London')
                      }
                  })]


class NLTKGeoNameExtractorTestCase(NLTKPlaceNameExtractorTestCase):
    """Test a NamedEntityExtractor configured to extract only Places.

    As NLTKPlaceNameExtractorTestCase but with variation in config.
    """

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="extractor" id="{0.__name__}">
          <objectType>cheshire3.textmining.extractor.{0.__name__}</objectType>
          <options>
            <setting type="entityTypes">Geo</setting>
          </options>
        </subConfig>'''.format(self._get_class()))


class NLTKOrganizationNameExtractorTestCase(NLTKNamedEntityExtractorTestCase):
    """Test a NamedEntityExtractor configured to extract only Organizations."""

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="extractor" id="{0.__name__}">
          <objectType>cheshire3.textmining.extractor.{0.__name__}</objectType>
          <options>
            <setting type="entityTypes">ORGANIZATION</setting>
          </options>
        </subConfig>'''.format(self._get_class()))

    def _get_process_string_tests(self):
        # Return a list of tuples containing test pairs:
        # (string to be tokenized, expected tokens list)
        return [(self.text,
                 {'Union': {
                      'text': 'Union',
                      'occurences': self.text.count('Union'),
                      'proxLoc': [-1] * self.text.count('Union')
                      }
                  })]

    def _get_process_node_tests(self):
        return [(etree.XML('<data>{0}</data>'.format(self.text)),
                 {'Union': {
                      'text': 'Union',
                      'occurences': self.text.count('Union'),
                      'proxLoc': [-1] * self.text.count('Union')
                      }
                  })]


class NLTKCompanyNameExtractorTestCase(NLTKOrganizationNameExtractorTestCase):
    """Test a NamedEntityExtractor configured to extract only Organizations.

    As NLTKOrganizationNameExtractorTestCase but with variation in config.
    """

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="extractor" id="{0.__name__}">
          <objectType>cheshire3.textmining.extractor.{0.__name__}</objectType>
          <options>
            <setting type="entityTypes">company</setting>
          </options>
        </subConfig>'''.format(self._get_class()))


class NLTKInvalidNameExtractorTestCase(NLTKNamedEntityExtractorTestCase):
    """Named Entity Extractor with an unsupported entityType."""

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="extractor" id="{0.__name__}">
          <objectType>cheshire3.textmining.extractor.{0.__name__}</objectType>
          <options>
            <setting type="entityTypes">EVENT</setting>
          </options>
        </subConfig>'''.format(self._get_class()))

    def setUp(self):
        """Expected failure initializing object."""
        self.assertRaises(ConfigFileException,
                          NLTKNamedEntityExtractorTestCase.setUp,
                          self)
        self.testObj = None

    @unittest.expectedFailure
    def test_instance(self):
        """Test case expected to fail due to configuration error."""
        NLTKNamedEntityExtractorTestCase.test_instance(self)

    @unittest.expectedFailure
    def test_mergeHash(self):
        """Test case expected to fail due to configuration error."""
        NLTKNamedEntityExtractorTestCase.test_mergeHash(self)

    @unittest.expectedFailure
    def test_process_node(self):
        """Test case expected to fail due to configuration error."""
        NLTKNamedEntityExtractorTestCase.test_process_node(self)

    @unittest.expectedFailure
    def test_process_string(self):
        """Test case expected to fail due to configuration error."""
        NLTKNamedEntityExtractorTestCase.test_process_string(self)

    @unittest.expectedFailure
    def test_process_xpathResult(self):
        """Test case expected to fail due to configuration error."""
        NLTKNamedEntityExtractorTestCase.test_process_xpathResult(self)


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(NLTKNamedEntityExtractorTestCase)
    suite.addTests(ltc(NLTKPersonNameExtractorTestCase))
    suite.addTests(ltc(NLTKPeopleNameExtractorTestCase))
    suite.addTests(ltc(NLTKPlaceNameExtractorTestCase))
    suite.addTests(ltc(NLTKGeoNameExtractorTestCase))
    suite.addTests(ltc(NLTKOrganizationNameExtractorTestCase))
    suite.addTests(ltc(NLTKCompanyNameExtractorTestCase))
    suite.addTests(ltc(NLTKInvalidNameExtractorTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
