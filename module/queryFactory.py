
import cheshire3.cqlParser as cql
from cheshire3.baseObjects import QueryFactory

class QueryStream(object):
    def parse(self, session, data, codec, db):
        raise NotImplementedError()

class CqlQueryStream(QueryStream):

    def parse(self, session, data, codec, db):
        # XXX check codec, turn into unicode first
        return cql.parse(data)


class SimpleQueryFactory(QueryFactory):

    def __init__(self, session, config, parent):
        QueryFactory.__init__(self, session, config, parent)
        self.queryHash = {'cql' : CqlQueryStream()}       

    def get_query(self, session, data, format="cql", codec=None, db=None):
        try:
            strm = self.queryHash[format]
        except KeyError:
            raise ValueError("Unknown format: %s" % format)

        query = strm.parse(session, data, codec, db)
        return query
