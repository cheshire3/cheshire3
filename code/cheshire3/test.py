u"""Limited unittests for Cheshire3.

A system like Cheshire3 presents significant challenges to unit testing. 
Firstly it is designed to be highly configurable to meet specific user 
requirements - modifying the configuration for a system object will alter 
it's behavior, and hence will most likely cause unit tests to fail.

Secondly, Cheshire3 is database oriented (a database being a virtual 
collection of records), meaning that thorough testing of it's processing 
objects requires the provision of some data and configurations appropriate to 
it.We will be providing a unittest database for this purpose.

This module therefore provides limited testing of the Cheshire3 framework 
architecture, and default server configurations.

"""

import os

try:
    import unittest2 as unittest
except ImportError:
    import unittest


from cheshire3.baseObjects import Session
from cheshire3.configParser import C3Object
from cheshire3.server import SimpleServer
from cheshire3.internal import cheshire3Root
from cheshire3.exceptions import ObjectDoesNotExistException


class Cheshire3TestCase(unittest.TestCase):
    u"""Abstract Base Class for Cheshire Test Cases.   
        
    Almost all objects in Cheshire3 require a Session, so create one.
    """
    
    def setUp(self):
        self.session = Session()
        
    def test_sessionInstance(self):
        self.assertIsInstance(self.session, Session)
        
        
class Cheshire3ServerTestCase(Cheshire3TestCase):
    
    def setUp(self):
        Cheshire3TestCase.setUp(self)
        serverConfig = os.path.join(cheshire3Root, 'configs', 'serverConfig.xml')
        self.server = SimpleServer(self.session, serverConfig)
        
    def tearDown(self):
        # Nothing to do as yet...
        pass
    
    def test_serverInstance(self):
        self.assertIsInstance(self.server, SimpleServer)
    
    def test_ObjectDoesNotExistException(self):
        self.assertRaises(ObjectDoesNotExistException, 
                     self.server.get_object, 
                     self.session, 
                     "An Object Identifier That Does Not Exist!!!")
        
    def generate_get_object_test(self, identifier):
        """Generate and return a method to test get_object for the given identifier."""
        def test(self):
            session = self.session
            serv = self.server
            try:
                obj = serv.get_object(session, identifier)
            except:
                # Assert that only fails due to unavailable optional dependency
                self.assertRaisesRegexp(ImportError, 
                                        "No module named [svm]", 
                                        serv.get_object, 
                                        session, 
                                        identifier)
            else:
                self.assertIsInstance(obj,
                                      C3Object,
                                      "Object {0} is not an instance of a C3Object sub-class!?".format(identifier))
        return test
        

def load_tests(loader, tests, pattern):
    # Create a suite with default tests
    suite = loader.loadTestsFromTestCase(Cheshire3ServerTestCase)
    # Create an instance of Cheshire3ServerTestCase
    tc = Cheshire3ServerTestCase('test_sessionInstance')
    # Set it up
    tc.setUp()
    # Iterate through all configured object adding a test for each
    for k in tc.server.subConfigs.iterkeys():
        test_name = "test_get_object_{0}".format(k)
        test_method = tc.generate_get_object_test(k)
        setattr(Cheshire3ServerTestCase, test_name, test_method)
        suite.addTest(Cheshire3ServerTestCase(test_name))
    # Return the complete test suite
    
    return suite

if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
