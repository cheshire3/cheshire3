u"""Abstract Base Class for Cheshire3 Object Unittests."""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from cheshire3.baseObjects import Session


class Cheshire3TestCase(unittest.TestCase):
    u"""Abstract Base Class for Cheshire3 Test Cases.   
        
    Almost all objects in Cheshire3 require a Session, so create one.
    """
    
    def setUp(self):
        self.session = Session()
    
    def tearDown(self):
        pass
        
    def test_sessionInstance(self):
        self.assertIsInstance(self.session, Session)
