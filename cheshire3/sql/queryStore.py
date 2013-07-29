"""QueryStore Implmentations."""

from cheshire3.queryStore import SimpleQueryStore
from cheshire3.sql.postgresStore import PostgresStore


class PostgresQueryStore(PostgresStore, SimpleQueryStore):
    """PostgreSQL QueryStore implementation."""

    def __init__(self, session, node, parent):
        PostgresStore.__init__(self, session, node, parent)
