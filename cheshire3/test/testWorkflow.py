u"""Cheshire3 Tokenizer Unittests.

Workflow configurations may be customized by the user. For the purposes of 
unittesting, configuration files will be ignored and Workflow instances will
be instantiated using configuration data defined within this testing module, 
and tests carried out on instances.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from lxml import etree

from cheshire3.baseObjects import Database
from cheshire3.workflow import SimpleWorkflow, CachingWorkflow
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class FakeDatabase(Database):
    """Database specifically for unittesting Workflow execution.

    May be initialize with only the minimum information needed.
    """

    def __init__(self, session, config, parent=None):
        Database.__init__(self, session, config, parent=parent)


class WorkflowTestCase(Cheshire3ObjectTestCase):
    """Base Class for Workflow Test Cases."""

    def _get_dependencyConfigs(self):
        yield etree.XML('''\
        <subConfig type="database" id="db_testWorkflows">
          <objectType>cheshire3.test.testWorkflow.FakeDatabase</objectType>
        </subConfig>''')

    def _get_config(self):
        return etree.XML('''
        <subConfig type="workflow" id="{0.__name__}">
            <objectType>{0.__module__}.{0.__name__}</objectType>
            <workflow>
            </workflow>
        </subConfig>
        '''.format(self._get_class()))

    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        self.session.database = 'db_testWorkflows'

    def testWorkflowRuns(self):
        """Check generated workflow runs without errors"""
        self.testObj.process(self.session)


class LoggingWorkflowTestCase(WorkflowTestCase):
    """Base Class for testing Logging in Workflows."""

    def _get_config(self):
        return etree.XML('''
        <subConfig type="workflow" id="{0.__name__}">
            <objectType>{0.__module__}.{0.__name__}</objectType>
            <workflow>
                <!-- test logging nothing -->
                <log></log>
                <!-- test logging split over multiple lines
                e.g. due to automatic XML source formatting -->
                <log>
                    Some log message
                </log>
                <log>"" +
                    repr(input) +
                    "Some more text"
                </log>
                <!-- test logging levels -->
                <log level="debug"></log>
                <log level="info"></log>
                <log level="warning"></log>
                <log level="error"></log>
                <log level="critical"></log>
            </workflow>
        </subConfig>
        '''.format(self._get_class()))


class SimpleWorkflowTestCase(WorkflowTestCase):

    @classmethod
    def _get_class(cls):
        return SimpleWorkflow


class CachingWorkflowTestCase(WorkflowTestCase):

    @classmethod
    def _get_class(cls):
        return CachingWorkflow


class LoggingSimpleWorkflowTestCase(SimpleWorkflowTestCase,
                                    LoggingWorkflowTestCase):

    @classmethod
    def _get_class(cls):
        return SimpleWorkflow

    def _get_config(self):
        return LoggingWorkflowTestCase._get_config(self)


class LoggingCachingWorkflowTestCase(CachingWorkflowTestCase,
                                     LoggingWorkflowTestCase):

    @classmethod
    def _get_class(cls):
        return CachingWorkflow

    def _get_config(self):
        return LoggingWorkflowTestCase._get_config(self)


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase 
    suite = ltc(SimpleWorkflowTestCase)
    suite.addTests(ltc(CachingWorkflowTestCase))
    suite.addTests(ltc(LoggingSimpleWorkflowTestCase))
    suite.addTests(ltc(LoggingCachingWorkflowTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))

