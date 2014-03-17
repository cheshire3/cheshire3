"""Relational Database Management System  (RDBMS) Support for Cheshire3.

Currently supports PostgreSQL, but other may be added if requirement demands
and time allows in the future.

Provides support for creating most types of stores (record, index, resultSet)
within an RDBMS environment.

Should also allow existing PostgreSQL databases to be used as a source of
documents for ingest via PostgresDocumentFactory, and PostgresDocumentStream.
"""

all = ['documentFactory', 'documentStore', 'index', 'indexStore',
       'objectStore', 'postgres', 'postgresStore', 'queryStore', 'recordStore',
       'resultSetStore', 'sqlite'
       ]
