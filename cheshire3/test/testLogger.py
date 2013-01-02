u"""Cheshire3 Logger Unittests.

Logger configurations may be customized by the user. For the purposes of
unittesting, configuration files will be ignored and Logger instances
will be instantiated using configurations defined within this testing module,
and tests carried out on those instances using data defined in this module.
"""
from __future__ import with_statement

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os

from tempfile import mktemp
from lxml import etree

from cheshire3.logger import SimpleLogger
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class SimpleLoggerTestCase(Cheshire3ObjectTestCase):
    "Tests for file based Logger."

    @classmethod
    def _get_class(cls):
        return SimpleLogger

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="filePath">{1}</path>
          </paths>
          <options>
            <!-- Do not cache lines -->
            <setting type="cacheLength">0</setting>
          </options>
        </subConfig>'''.format(self._get_class(), self.logPath))

    def setUp(self):
        # Get a tempfile name
        self.logPath = mktemp(suffix=".log", prefix="testLogger")
        Cheshire3ObjectTestCase.setUp(self)

    def tearDown(self):
        # Remove log file
        os.remove(self.logPath)

    def test_fileExists(self):
        "Check log file was created."
        self.assertTrue(os.path.exists(self.logPath))

    def test_logMessage(self):
        "Check a given message is written to the log file."
        self.testObj.log(self.session, "This is my log message")
        # Logger's line cache should be empty
        self.assertListEqual(self.testObj.lineCache, [])
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
            self.assertIn("This is my log message", line)
            # N.B. Logger should append a newline after each message
            self.assertTrue(line.endswith("\n"))

    def test_logNotSet(self):
        "Check NOTSET message is written to the log file."
        self.testObj.log_lvl(self.session, 0, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("NOTSET", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logDebug(self):
        "Check DEBUG message is written to the log file."
        self.testObj.log_lvl(self.session, 10, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("DEBUG", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logInfo(self):
        "Check INFO message is written to the log file."
        self.testObj.log_lvl(self.session, 20, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("INFO", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logWarning(self):
        "Check WARNING message is written to the log file."
        self.testObj.log_lvl(self.session, 30, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("WARNING", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logError(self):
        "Check ERROR message is written to the log file."
        self.testObj.log_lvl(self.session, 40, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("ERROR", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logCritical(self):
        "Check CRITICAL message is written to the log file."
        self.testObj.log_lvl(self.session, 50, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("CRITICAL", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])


class SimpleLoggerDefaultLevelTestCase(Cheshire3ObjectTestCase):
    "Tests for file based Logger with a default logging level."

    @classmethod
    def _get_class(cls):
        return SimpleLogger

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="filePath">{1}</path>
          </paths>
          <options>
            <!-- Do not cache lines -->
            <setting type="cacheLength">0</setting>
            <default type="level">20</default>
          </options>
        </subConfig>'''.format(self._get_class(), self.logPath))

    def setUp(self):
        # Get a tempfile name
        self.logPath = mktemp(suffix=".log",
                              prefix="testLogger")
        Cheshire3ObjectTestCase.setUp(self)

    def tearDown(self):
        # Remove log file
        os.remove(self.logPath)

    def test_logMessage(self):
        "Check a given message with default level written to the log file."
        self.testObj.log(self.session, "This is my default level log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("INFO", line)
        self.assertIn("This is my default level log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logNotSet(self):
        "Check a given message with default level written to the log file."
        self.testObj.log_lvl(self.session,
                             0,
                             "This is my default level log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("INFO", line)
        self.assertIn("This is my default level log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])


class SimpleLoggerMinLevelTestCase(Cheshire3ObjectTestCase):
    "Tests for file based Logger with minimum log level."

    @classmethod
    def _get_class(cls):
        return SimpleLogger

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="filePath">{1}</path>
          </paths>
          <options>
            <!-- Do not cache lines -->
            <setting type="cacheLength">0</setting>
            <setting type="minLevel">10</setting>
          </options>
        </subConfig>'''.format(self._get_class(), self.logPath))

    def setUp(self):
        # Get a tempfile name
        self.logPath = mktemp(suffix=".log", prefix="testLogger")
        Cheshire3ObjectTestCase.setUp(self)

    def tearDown(self):
        # Remove log file
        os.remove(self.logPath)

    def test_fileExists(self):
        "Check log file was created."
        self.assertTrue(os.path.exists(self.logPath))

    def test_logMessage(self):
        "Check a message without log level is NOT written to the log file."
        self.testObj.log(self.session,
                         "Message without level should not be written")
        with open(self.logPath, 'r') as fh:
            logs = fh.read()
            self.assertNotIn("Message without level should not be written",
                             logs)

    def test_logNotSet(self):
        "Check NOTSET message is written to the log file."
        self.testObj.log_lvl(self.session,
                             0,
                             "0 level message should not be written")
        with open(self.logPath, 'r') as fh:
            logs = fh.read()
            self.assertNotIn("0 level message should not be written", logs)

    def test_logDebug(self):
        "Check DEBUG message is written to the log file."
        self.testObj.log_lvl(self.session, 10, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("DEBUG", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logInfo(self):
        "Check INFO message is written to the log file."
        self.testObj.log_lvl(self.session, 20, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("INFO", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logWarning(self):
        "Check WARNING message is written to the log file."
        self.testObj.log_lvl(self.session, 30, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("WARNING", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logError(self):
        "Check ERROR message is written to the log file."
        self.testObj.log_lvl(self.session, 40, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("ERROR", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logCritical(self):
        "Check CRITICAL message is written to the log file."
        self.testObj.log_lvl(self.session, 50, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("CRITICAL", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])


class SimpleLoggerMinAndDefaultLevelTestCase(Cheshire3ObjectTestCase):
    "Tests for file based Logger with minimum and default log level."

    @classmethod
    def _get_class(cls):
        return SimpleLogger

    def _get_config(self):
        return etree.XML('''\
        <subConfig type="baseStore" id="{0.__name__}">
          <objectType>{0.__module__}.{0.__name__}</objectType>
          <paths>
              <path type="filePath">{1}</path>
          </paths>
          <options>
            <!-- Do not cache lines -->
            <setting type="cacheLength">0</setting>
            <setting type="minLevel">10</setting>
            <default type="level">20</default>
          </options>
        </subConfig>'''.format(self._get_class(), self.logPath))

    def setUp(self):
        # Get a tempfile name
        self.logPath = mktemp(suffix=".log", prefix="testLogger")
        Cheshire3ObjectTestCase.setUp(self)

    def tearDown(self):
        # Remove log file
        os.remove(self.logPath)

    def test_fileExists(self):
        "Check log file was created."
        self.assertTrue(os.path.exists(self.logPath))

    def test_logMessage(self):
        """Check a given message with default level written to the log file.

        default level >= minLevel.
        """
        self.testObj.log(self.session, "This is my default level log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("INFO", line)
        self.assertIn("This is my default level log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logNotSet(self):
        "Check NOTSET message is written to the log file."
        self.testObj.log_lvl(self.session,
                             0,
                             "0 level message should not be written")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("INFO", line)
        self.assertIn("0 level message should not be written", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logDebug(self):
        "Check DEBUG message is written to the log file."
        self.testObj.log_lvl(self.session, 10, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("DEBUG", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logInfo(self):
        "Check INFO message is written to the log file."
        self.testObj.log_lvl(self.session, 20, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("INFO", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logWarning(self):
        "Check WARNING message is written to the log file."
        self.testObj.log_lvl(self.session, 30, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("WARNING", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logError(self):
        "Check ERROR message is written to the log file."
        self.testObj.log_lvl(self.session, 40, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("ERROR", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])

    def test_logCritical(self):
        "Check CRITICAL message is written to the log file."
        self.testObj.log_lvl(self.session, 50, "This is my log message")
        with open(self.logPath, 'r') as fh:
            for line in fh:
                pass
        self.assertIn("CRITICAL", line)
        self.assertIn("This is my log message", line)
        # N.B. Logger should append a newline after each message
        self.assertTrue(line.endswith("\n"))
        # Logger's line cache should now be empty
        self.assertListEqual(self.testObj.lineCache, [])


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(SimpleLoggerTestCase)
    suite.addTests(ltc(SimpleLoggerDefaultLevelTestCase))
    suite.addTests(ltc(SimpleLoggerMinLevelTestCase))
    suite.addTests(ltc(SimpleLoggerMinAndDefaultLevelTestCase))
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
