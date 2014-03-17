"""Run all tests."""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from cheshire3.test import __all__


def load_tests(loader, tests, pattern):
    # Create a suite with default tests
    loadTestsFromName = unittest.defaultTestLoader.loadTestsFromName
    suite = unittest.TestSuite()
    for modname in __all__:
        if modname == 'testAll':
            continue
        try:
            # Check if the module defines load_tests
            module = __import__(modname, globals(), locals(), [])
        except ImportError:
            # Load all tests from the module
            modname = "cheshire3.test.{0}".format(modname)
            try:
                modsuite = loadTestsFromName(modname + '.suite')
            except AttributeError:
                modsuite = loadTestsFromName(modname)
        else:
            try:
                load_tests_fn = getattr(module, 'load_tests')
            except AttributeError:
                # No tests to load for this module
                continue
            else:
                modsuite = load_tests_fn(loader, tests, pattern)
            
        suite.addTest(modsuite)
    # Return the complete test suite
    return suite


def suite():
    return load_tests(unittest.defaultTestLoader, [], 'test*.py')


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
