"""DocumentStore Implementations."""

from cheshire3.documentStore import SimpleDocumentStore
from cheshire3.sql.postgresStore import PostgresIter, PostgresStore


class PostgresDocumentIter(PostgresIter):

    def next(self):
        """Get the next data from iterator.

        Turn the data into a Document object and return.
        """
        d = PostgresIter.next(self)
        data = d[1]
        doc = self.store._process_data(self.session, d[0], data)
        return doc


class PostgresDocumentStore(PostgresStore, SimpleDocumentStore):
    """PostgreSQL DocumentStore implementation."""

    def __init__(self, session, node, parent):
        SimpleDocumentStore.__init__(self, session, node, parent)
        PostgresStore.__init__(self, session, node, parent)

    def __iter__(self):
        # Return an iterator object to iter through
        return PostgresDocumentIter(self.session, self)
