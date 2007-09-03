

# Give qf a string, get back a query object
# Why?  ...  Removes dependency on PyZ3950.CQLParser in all scripts
# Allows for non CQL queries, with sufficient translation
# Allows for query generation during workflows from string


from PyZ3950.CQLParser import parse
from baseObjects import QueryFactory

class SimpleQueryFactory(QueryFactory):

    def process_string(self, session, data, type="cql", db=None):
        if type == "cql":
            return parse(data)
        else:
            raise NotImplementedError()
