u"""Cheshire3 Session Unittests."""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from cheshire3.baseObjects import Session


class Cheshire3SessionTestCase(unittest.TestCase):
    u"""Cheshire3 Session Unittests.
    
    As Session is a special class that does not inherit from C3Object, test
    case does not inherit from Cheshire3TestCase either
    """
    
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
        
    def test_sessionInstance(self):
        session = Session()
        self.assertIsInstance(session, Session)
        
    def test_sessionEnvironmentDefault(self):
        session = Session()
        self.assertEqual(session.environment, "terminal")
    
    def test_sessionEnvironmentInit(self):
        session = Session(environment="apache")
        self.assertEqual(session.environment, "apache")
        
    def test_sessionEnvironmentAssign(self):
        session = Session()
        session.environment = "apache"
        self.assertEqual(session.environment,
                         "apache",
                         "session.environment assignment failed")
        session.environment = "terminal"
        self.assertEqual(session.environment,
                         "terminal",
                         "session.environment re-assignment failed")
        
    def test_sessionDatabaseInit(self):
        session = Session(database="db_test1")
        self.assertEqual(session.database, "db_test1")
        
    def test_sessionDatabaseAssign(self):
        session = Session()
        session.database = "db_test1"
        self.assertEqual(session.database,
                         "db_test1",
                         "session.database assignment failed")
        session.database = "db_test2"
        self.assertEqual(session.database,
                         "db_test2",
                         "session.database re-assignment failed")
        

def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(Cheshire3SessionTestCase)


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
