u"""Unittests for Cheshire3.

A system like Cheshire3 presents significant challenges to unit testing. 
Firstly it is designed to be highly configurable to meet specific user 
requirements - modifying the configuration for a system object will alter 
it's behavior, and hence will most likely cause unit tests to fail.

Secondly, Cheshire3 is database oriented (a database being a virtual 
collection of records), meaning that thorough testing of it's processing 
objects requires the provision of some data and configurations appropriate to 
it.We will be providing a unittest database for this purpose.

This sub-package therefore provides limited testing of the Cheshire3 framework 
architecture, and default server configurations.
"""

__all__ = ['testAll',
           'testBaseStore',
           'testConfigParser',
           'testConfigs',
           'testDocument',
           'testDocumentFactory',
           'testDocumentStore',
           'testDynamic',
           'testExtractor',
           'testIndex',
           'testLogger',
           'testNormalizer',
           'testParser',
           'testPreParser',
           'testQueryFactory',
           'testQueryStore',
           'testRecord',
           'testRecordStore',
           'testResultSet',
           'testResultSetStore',
           'testSession',
           'testTokenizer',
           'testTokenMerger',
           'testUtils']
