"""Deprecated module maintained for backward compatibility."""

# backward compatibility imports
from cheshire3.sql.postgresStore import PostgresIter, PostgresStore
from cheshire3.sql.documentStore import (PostgresDocumentIter,
                                         PostgresDocumentStore)
from cheshire3.sql.index import PostgresIndex
from cheshire3.sql.indexStore import PostgresIndexStore
from cheshire3.sql.objectStore import PostgresObjectIter, PostgresObjectStore
from cheshire3.sql.queryStore import PostgresQueryStore
from cheshire3.sql.recordStore import PostgresRecordIter, PostgresRecordStore
from cheshire3.sql.resultSetStore import PostgresResultSetStore
from cheshire3.sql.documentFactory import (PostgresDocumentStream,
                                           PostgresDocumentFactory)
