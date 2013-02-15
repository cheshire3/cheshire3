u"""Cheshire3 Dynamic Unittests.

Test the code that takes XML configurations, and dynamically translates them
into functional Objects within the Cheshire3 framework. 
"""

import os

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3 import baseObjects
from cheshire3.dynamic import importObject, buildObject, makeObjectFromDom
from cheshire3.exceptions import ConfigFileException
from cheshire3.exceptions import MissingDependencyException
from cheshire3.internal import cheshire3Root
from cheshire3.server import SimpleServer


class DynamicTestCase(unittest.TestCase):
    """Base Class for cheshire3.dynamic test cases."""
    
    def _get_objectTypes(self):
        return ['cheshire3.database.SimpleDatabase',
                'cheshire3.database.OptimisingDatabase',
                'cheshire3.documentFactory.SimpleDocumentFactory',
                'cheshire3.documentFactory.ComponentDocumentFactory',
                'cheshire3.documentStore.SimpleDocumentStore',
                'cheshire3.extractor.SimpleExtractor',
                'cheshire3.index.SimpleIndex',
                'cheshire3.index.ProximityIndex',
                'cheshire3.index.RangeIndex',
                'cheshire3.index.BitmapIndex',
                'cheshire3.indexStore.BdbIndexStore',
                'cheshire3.logger.SimpleLogger',
                'cheshire3.logger.FunctionLogger',
                'cheshire3.logger.LoggingLogger',
                'cheshire3.logger.DateTimeFileLogger',
                'cheshire3.logger.MultipleLogger',
                'cheshire3.normalizer.SimpleNormalizer',
                'cheshire3.normalizer.CaseNormalizer',
                'cheshire3.normalizer.SpaceNormalizer',
                'cheshire3.normalizer.RangeNormalizer',
                'cheshire3.objectStore.BdbObjectStore',
                'cheshire3.parser.MinidomParser',
                'cheshire3.parser.SaxParser',
                'cheshire3.parser.LxmlParser',
                'cheshire3.parser.LxmlHtmlParser',
                'cheshire3.parser.MarcParser',
                'cheshire3.preParser.UnicodeDecodePreParser',
                'cheshire3.preParser.HtmlTidyPreParser',
                'cheshire3.preParser.SgmlPreParser',
                'cheshire3.preParser.CharacterEntityPreParser',
                'cheshire3.queryFactory.SimpleQueryFactory',
                'cheshire3.queryStore.SimpleQueryStore',
                'cheshire3.recordStore.BdbRecordStore',
                'cheshire3.resultSetStore.BdbResultSetStore',
                'cheshire3.selector.XPathSelector',
                'cheshire3.selector.SpanXPathSelector',
                'cheshire3.selector.MetadataSelector',
                'cheshire3.tokenizer.RegexpSubTokenizer',
                'cheshire3.tokenizer.SentenceTokenizer',
                'cheshire3.tokenizer.DateTokenizer',
                'cheshire3.tokenizer.PythonTokenizer',
                'cheshire3.tokenMerger.SimpleTokenMerger',
                'cheshire3.tokenMerger.ProximityTokenMerger',
                'cheshire3.tokenMerger.RangeTokenMerger',
                'cheshire3.tokenMerger.NGramTokenMerger',
                'cheshire3.transformer.XmlTransformer',
                'cheshire3.transformer.LxmlXsltTransformer',
                'cheshire3.transformer.MarcTransformer',
                'cheshire3.workflow.SimpleWorkflow',
                'cheshire3.workflow.CachingWorkflow']

    def _get_configFromObjectType(self, objectType):    
        return etree.XML('''\
        <subConfig id="{0}">
          <objectType>{0}</objectType>
        </subConfig>'''.format(objectType))

    def setUp(self):
        self.session = baseObjects.Session()
        serverConfig = os.path.join(cheshire3Root,
                                    'configs',
                                    'serverConfig.xml')
        self.server = SimpleServer(self.session, serverConfig)
        # Disable stdout logging
        lgr = self.server.get_path(self.session, 'defaultLogger')
        lgr.minLevel = 60


class ImportObjectTestCase(DynamicTestCase):
    """Test importing classes from a module."""
    
    def test_badConfiguration_noObjectClass(self):
        "Check that bad configuration raises appropriate error."
        self.assertRaises(ConfigFileException,
                          importObject,
                          self.session,
                          'cheshire3')
        self.assertRaises(ConfigFileException,
                          importObject,
                          self.session,
                          'cheshire3.record')
        self.assertRaises(ConfigFileException,
                          importObject,
                          self.session,
                          'cheshire3.parser')
        self.assertRaises(ConfigFileException,
                          importObject,
                          self.session,
                          'cheshire3.noModule')

    def test_importBaseConfigs(self):
        "Check classes for processing object types can be imported."
        for objectType in self._get_objectTypes():
            cls = importObject(self.session, objectType)
            modName = objectType.split('.')[1]
            expCls = getattr(baseObjects, modName[0].upper() + modName[1:])
            self.assertTrue(issubclass(cls, expCls))


class BuildObjectTestCase(DynamicTestCase):
    """Test building an object from an ObjectType and args."""

    def setUp(self):
        DynamicTestCase.setUp(self)

    def test_buildObject(self):
        "Check processing objects can be instantiated"
        for objectType in self._get_objectTypes():
            if "Store" in objectType:
                # Don't build Stores - creates empty BDB files
                continue
            config = self._get_configFromObjectType(objectType)
            try:
                obj = buildObject(self.session,
                                  objectType,
                                  (config, self.server))
            except Exception as e:
                self.assertIsInstance(e,
                                      (ConfigFileException,
                                       NotImplementedError,
                                       MissingDependencyException),
                                      "When failing to buildObject of type "
                                      "'{0}' {1} is raised. Should be one of: "
                                      "ConfigFileException, "
                                      "NotImplementedError, "
                                      "MissingDependencyException"
                                      "".format(objectType,
                                                e.__class__.__name__)
                                      )
            else:
                modName = objectType.split('.')[1]
                expCls = getattr(baseObjects, modName[0].upper() + modName[1:])
                self.assertIsInstance(obj, expCls)


class MakeObjectFromDomTestCase(DynamicTestCase):
    """Test building an object from a config node."""

    def setUp(self):
        DynamicTestCase.setUp(self)

    def test_makeObjectFromDom(self):
        "Check processing objects can be created from a parsed configs."
        for objectType in self._get_objectTypes():
            if "Store" in objectType:
                # Don't build Stores - creates empty BDB files
                continue
            config = self._get_configFromObjectType(objectType)
            try:
                obj = makeObjectFromDom(self.session,
                                        config,
                                        self.server)
            except Exception as e:
                self.assertIsInstance(e,
                                      (ConfigFileException,
                                       NotImplementedError,
                                       MissingDependencyException),
                                      "When failing to makeObjectFromDom for "
                                      "type '{0}' {1} is raised. Should be "
                                      "one of: ConfigFileException, "
                                      "NotImplementedError, "
                                      "MissingDependencyException"
                                      "".format(objectType,
                                                e.__class__.__name__)
                                      )
            else:
                modName = objectType.split('.')[1]
                expCls = getattr(baseObjects, modName[0].upper() + modName[1:])
                self.assertIsInstance(obj, expCls)


def load_tests(loader, tests, pattern):
    ltc = loader.loadTestsFromTestCase
    suite = ltc(ImportObjectTestCase)
    suite.addTests(ltc(BuildObjectTestCase))
    suite.addTests(ltc(MakeObjectFromDomTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
