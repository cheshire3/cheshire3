"""Index Implementations."""

from cheshire3.index import SimpleIndex
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem


class PostgresIndex(SimpleIndex):
    """PostgreSQL Index implementation."""

    def construct_resultSet(self, session, terms, queryHash={}):
        # in: res.dictresult()

        s = SimpleResultSet(session, [])
        rsilist = []
        for t in terms['records']:
            (store, id) = t['recordid'].split('/', 1)
            occs = t['occurences']
            item = SimpleResultSetItem(session, id, store, occs, resultSet=s)
            rsilist.append(item)
        s.fromList(rsilist)
        s.index = self
        if queryHash:
            s.queryTerm = queryHash['text']
            s.queryFreq = queryHash['occurences']
        s.totalRecs = terms['totalRecs']
        s.totalOccs = terms['totalOccs']
        return s
