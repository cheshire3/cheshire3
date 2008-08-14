
from cheshire3.baseObjects import QueryStore
from cheshire3.baseStore import BdbStore
import cheshire3.cqlParser as cql

class SimpleQueryStore(BdbStore, QueryStore):

    def create_query(self, session, query=None):
        # Create a record like <query> text </query>
        id = self.generate_id(session)
        if query:
            data = query.toCQL()
            query.id = id
            if hasattr(query, 'resultSet'):
                rsid = query.resultSet.id
                query.resultSetId = rsid
                # Save link to result set
                self.store_data(session, "__rset_%s" % id, str(rsid))
        else:
            data = ""
        self.store_data(session, id, data)
        return id

    def delete_query(self, session, id):
        self.delete_item(session, id)

    def fetch_query(self, session, id):
        cql = self.fetch_data(session, id)
        q = cql.parse(cql)
        q.id = id
        rsid = self.fetch_data(session, "__rset_%s" % id)
        if rsid:
            self.resultSetId = rsid
        return q

    def store_query(self, session, query):
        # Where to get ID from???
        raise NotImplementedError
        r = self.store_record(session, rec)
        return id
