"""ObjectStore Implementations."""

from cheshire3.objectStore import SimpleObjectStore
from cheshire3.sql.recordStore import PostgresRecordIter, PostgresRecordStore


class PostgresObjectIter(PostgresRecordIter):
    """Iterator for Cheshire3 PostgresObjectStores"""

    def next(self):
        """Get the next data from iterator.

        Turn the data into a Cheshire3 object and return.
        """
        rec = PostgresRecordIter.next(self)
        obj = self.store._processRecord(None, rec.id, rec)
        return obj


class PostgresObjectStore(PostgresRecordStore, SimpleObjectStore):
    """PostgreSQL ObjectStore implementation."""

    def __iter__(self):
        # Return an iterator object to iter through
        return PostgresObjectIter(self.session, self)
