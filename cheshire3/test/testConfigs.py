u"""Unittests for Cheshire3 Server Configs."""

import os
import re

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from cheshire3.configParser import C3Object
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.test.testConfigParser import Cheshire3ObjectTestCase


class Cheshire3ServerConfigsTestCase(Cheshire3ObjectTestCase):
    
    def setUp(self):
        Cheshire3ObjectTestCase.setUp(self)
        # Compile a regex for acceptable missing imports
        # (i.e. optional features)
        self.importRegex = re.compile("""No\ module\ named\ (?:
            svm     # Support Vector Machine (datamining)
            |PyZ3950 # Z39.50 for Python (web)
            |rdflib  # Resource Description Framework (graph)
            )""", re.VERBOSE)
        
    def tearDown(self):
        # Nothing to do as yet...
        pass
    
    def test_ObjectDoesNotExistException(self):
        self.assertRaises(ObjectDoesNotExistException, 
                     self.server.get_object, 
                     self.session, 
                     "An Object Identifier That Does Not Exist!!!")
        
    def generate_get_object_test(self, identifier):
        "Generate and return method to test get_object for given identifier."
        def test(self):
            session = self.session
            serv = self.server
            try:
                obj = serv.get_object(session, identifier)
            except:
                # Assert that only fails due to unavailable optional dependency
                self.assertRaisesRegexp(ImportError, 
                                        self.importRegex, 
                                        serv.get_object, 
                                        session, 
                                        identifier)
            else:
                self.assertIsInstance(
                    obj,
                    C3Object,
                    "Object {0} is not an instance of a C3Object "
                    "sub-class!?".format(identifier)
                )
        return test


#def load_tests(loader, tests, pattern):
#    # Create a suite with default tests
#    suite = loader.loadTestsFromTestCase(Cheshire3ServerConfigsTestCase)
#    # Create an instance of Cheshire3ServerTestCase from which to dynamically 
#    # generate test methods
#    tc = Cheshire3ServerConfigsTestCase('test_sessionInstance')
#    # Set it up
#    tc.setUp()
#    # Iterate through all configured object adding a test for each
#    for k in tc.server.subConfigs.iterkeys():
#        test_name = "test_get_object_{0}".format(k)
#        test_method = tc.generate_get_object_test(k)
#        setattr(Cheshire3ServerConfigsTestCase, test_name, test_method)
#        suite.addTest(Cheshire3ServerConfigsTestCase(test_name))
#    tc.tearDown()
#    # Return the complete test suite
#    return suite
#
#
#if __name__ == '__main__':
#    tr = unittest.TextTestRunner(verbosity=2)
#    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))

if __name__ == '__main__':
    unittest.main()
