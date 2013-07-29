"""RecordStore implementations."""

from cheshire3.recordStore import SimpleRecordStore
from cheshire3.utils import nonTextToken
from cheshire3.sql.postgresStore import PostgresIter, PostgresStore


class PostgresRecordIter(PostgresIter):
    """Iterator for Cheshire3 PostgresRecordStores."""

    def next(self):
        """Get the next data from iterator

        Turn the data into a Record object and return.
        """
        d = PostgresIter.next(self)
        data = d[1]
        data = data.replace('\\000\\001', nonTextToken)
        data = data.replace('\\012', '\n')
        rec = self.store._process_data(self.session, d[0], data)
        return rec


class PostgresRecordStore(PostgresStore, SimpleRecordStore):
    """PostgreSQL RecordStore implementation."""

    def __init__(self, session, node, parent):
        SimpleRecordStore.__init__(self, session, node, parent)
        PostgresStore.__init__(self, session, node, parent)

    def __iter__(self):
        # Return an iterator object to iter through
        return PostgresRecordIter(self.session, self)
