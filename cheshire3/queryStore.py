
from cheshire3.baseObjects import QueryStore
from cheshire3.baseStore import BdbStore, DeletedObject
import cheshire3.cqlParser as cqlParser
from cheshire3.exceptions import *


class SimpleQueryStore(QueryStore):

    def create_query(self, session, query=None):
        """Create a record like <query> text </query>."""
        id = self.generate_id(session)
        if query is not None:
            query.id = id
            self.store_query(session, query)
            return query
        else:
            data = ""
        self.store_data(session, id, data)
        return id

    def delete_query(self, session, id):
        self.delete_data(session, id)

    def fetch_query(self, session, id):
        """Fetch query data, parse it into a query object and return."""
        cql = self.fetch_data(session, id)
        if cql is not None and cql:
            q = cqlParser.parse(cql)
        elif (isinstance(cql, DeletedObject)):
            raise ObjectDeletedException(cql)
        else:
            raise ObjectDoesNotExistException(id)
        q.id = id
        try:
            rsid = self.fetch_data(session, "__rset_%s" % id)
        except ObjectDoesNotExistException:
            pass
        else:
            self.resultSetId = rsid
        return q

    def store_query(self, session, query):
        """Store query data, assuming query object has an id. Return the query."""
        if (not hasattr(query, 'id')) or (query.id is None):
            # Where to get ID from??? 
            raise NotImplementedError

        id = query.id
        data = query.toCQL().encode('utf-8')
        # Encode to utf-8
        if hasattr(query, 'resultSet'):
            rsid = query.resultSet.id
            query.resultSetId = rsid
            # Save link to result set
            self.store_data(session, "__rset_%s" % id, str(rsid))

        self.store_data(session, id, data)
        return query


class BdbQueryStore(BdbStore, SimpleQueryStore):
    pass