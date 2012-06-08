"""IndexStore Implementations."""

from cheshire3.baseObjects import IndexStore
import cheshire3.cqlParser as cql
from cheshire3.sql.postgresStore import PostgresStore

# -- non proximity, just store occurences of type per record
# CREATE TABLE parent.id + self.id + index.id (identifier SERIAL PRIMARY KEY, term VARCHAR, occurences INT, recordId VARCHAR, stem VARCHAR, pos VARCHAR);

# -- proximity. Store each token, not each type, per record
# CREATE TABLE parent.id + self.id + index.id (identifier SERIAL PRIMARY KEY, term VARCHAR, field VARCHAR, recordId VARCHAR, stem VARCHAR, pos VARCHAR);

# -- then check adjacency via identifier comparison (plus field/recordId)

# -- recordId = recordStore.id / record.id
# -- so then can do easy intersection/union on them

# CREATE INDEX parent.id+self.id+index.id+termIndex on aboveTable (term);
# BEGIN
# INSERT INTO aboveTable (...) VALUES (...);
# COMMIT
# CLUSTER aboveIndex on aboveTable;

class PostgresIndexStore(IndexStore, PostgresStore):
    """PostgreSQL IndexStore implementation."""
    
    database = ""
    transaction = 0

    _possibleSettings = {'termProcess' : {'docs' : "Position of the process map to use for processing terms in the query.", 'type': int}}
    _possiblePaths = {'databaseName' : {'docs' : 'Name of the database in which to store the indexes.  Table names are assigned automatically.'}
                      , 'protocolMap' : {'docs' : 'ProtocolMap identifier for the indexes?'}}

    def __init__(self, session, config, parent):
        IndexStore.__init__(self, session, config, parent)
        # Open connection
        self.database = self.get_path(session, 'databaseName', 'cheshire3')
        # multiple tables, one per index 
        self.transaction = 0

    def _generate_tableName(self, session, index):
        base = self.parent.id + "__" + self.id + "__" + index.id
        return base.replace('-', '_').lower()

    def contains_index(self, session, index):
        self._openContainer(session)
        table = self._generate_tableName(session, index)
        query = "SELECT relname FROM pg_stat_user_tables WHERE relname = '%s'" % table;
        res = self._query(query)
        return len(res.dictresult()) == 1

    def create_index(self, session, index):
        self._openContainer(session)
        table = self._generate_tableName(session, index)
        query = "CREATE TABLE %s (identifier SERIAL PRIMARY KEY, term VARCHAR, occurences INT, recordId VARCHAR, stem VARCHAR, pos VARCHAR)" % table
        query2 = "CREATE INDEX %s ON %s (term)" % (table + "_INDEX", table)
        self._openContainer(session)
        self._query(query)
        self._query(query2)

    def begin_indexing(self, session, index):
        self._openContainer(session)
        if not self.transaction:
            self._query('BEGIN')
            self.transaction = 1

    def commit_indexing(self, session, index):
        if self.transaction:
            self._query('COMMIT')
            self.transaction = 0
        table = self._generate_tableName(session, index)
        termIdx = table + "_INDEX"
        self._query('CLUSTER %s ON %s' % (termIdx, table))

    def store_terms(self, session, index, termhash, record):
        # write directly to db, as sort comes as CLUSTER later
        table = self._generate_tableName(session, index)
        queryTmpl = "INSERT INTO %s (term, occurences, recordId) VALUES ('%%s', %%s, '%r')" % (table, record)

        for t in termhash.values():
            term = t['text'].replace("'", "''")
            query = queryTmpl % (term, t['occurences'])
            self._query(query)

    def delete_terms(self, session, index, termHash, record):
        table = self._generate_tableName(session, index)
        query = "DELETE FROM %s WHERE recordId = '%r'" % (table, record)
        self._query(query)


    def fetch_term(self, session, index, term, prox=True):
        # should return info to create result set
        # --> [(rec, occs), ...]
        table = self._generate_tableName(session, index)
        term = term.replace("'", "\\'");
        query = "SELECT recordId, occurences FROM %s WHERE term='%s'" % (table, term)
        res = self._query(query)
        dr = res.dictresult()
        totalRecs = len(dr)
        occq = "SELECT SUM(occurences) as sum FROM %s WHERE term='%s'" % (table, term)
        res = self._query(occq)
        totalOccs = res.dictresult()[0]['sum']
        return {'totalRecs' : totalRecs, 'records' : dr, 'totalOccs' : totalOccs}

    def fetch_termList(self, session, index, term, numReq=0, relation="", end="", summary=0, reverse=0):
        table = self._generate_tableName(session, index)

        if (not (numReq or relation or end)):
            numReq = 20
        if (not relation and not end):
            relation = ">="
        if type(end) == unicode:
            end = end.encode('utf-8')
        if (not relation):
            if (term > end):
                relation = "<="
            else:
                relation = ">"

        if relation in ['<', '<=']:
            order = "order by term desc "
        else:
            order = ""

        # assumes summary, atm :|
        # term, total recs, total occurences

        occq = "SELECT term, count(term), sum(occurences) FROM %s WHERE term%s'%s' group by term %sLIMIT %s" % (table, relation, term, order, numReq)
        res = self._query(occq)
        # now construct list from query result

        tlist = res.getresult()
        tlist = [(x[0], (0, x[1], x[2])) for x in tlist]
        if order:
            # re-reverse
            tlist = tlist[::-1]
        return tlist


    def _cql_to_sql(self, session, query, pm):
        if (isinstance(query, cql.SearchClause)):
            idx = pm.resolveIndex(session, query)

            if (idx is not None):
                # check if 'stem' relmod

                # get the index to chunk the term
                pn = idx.get_setting(session, 'termProcess')
                if (pn is None):
                    pn = 0
                else:
                    pn = int(pn)
                process = idx.sources[pn][1]
                res = idx._processChain(session, [query.term.value], process)
                if len(res) == 1:
                    nterm = res.keys()[0]

                # check stem
                if query.relation['stem']:
                    termCol = 'stem'
                else:
                    termCol = 'term'
                table = self._generate_tableName(session, idx)
                qrval = query.relation.value
                
                if qrval == "any":
                    terms = []
                    for t in res:
                        terms.append("'" + t + "'")
                    inStr = ', '.join(terms)
                    q = "SELECT DISTINCT recordid FROM %s WHERE %s in (%s)" % (table, termCol, inStr)
                elif qrval == "all":
                    qs = []
                    for t in res:
                        qs.append("SELECT recordid FROM %s WHERE %s = '%s'" % (table, termCol, t))
                    q = " INTERSECT ".join(qs)
                elif qrval == "exact":
                    q = "SELECT recordid FROM %s WHERE %s = '%s'" % (table, termCol, nterm)
                elif qrval == "within":
                    q = "SELECT recordid FROM %s WHERE %s BETWEEN '%s' AND '%s'" % (table, termCol, res[0], nterm)
                elif qrval in ['>', '<', '>=', '<=', '<>']:
                    q = "SELECT recordid FROM %s WHERE %s %s '%s'" % (table, termCol, qrval, nterm)
                elif qrval == '=':
                    # no prox
                    raise NotImplementedError()
                else:
                    raise NotImplementedError(qrval)

                return q
            else:
                raise ObjectDoesNotExistException(query.index.toCQL())

        else:
            left = self._cql_to_sql(session, query.leftOperand, pm)
            right = self._cql_to_sql(session, query.rightOperand, pm)
            bl = query.boolean
            if bl.value == "and":
                b = 'INTERSECT'
            elif bl.value == "or":
                b = 'UNION'
            elif bl.value == 'not':
                b = 'EXCEPT'
            else:
                raise NotImplementedError()
            q = "(%s %s %s)" % (left, b, right)
            return q


    # kludgey optimisation
    def search(self, session, query, db):
        pm = db.get_path(session, 'protocolMap')
        if not pm:
            db._cacheProtocolMaps(session)
            pm = db.protocolMaps.get('http://www.loc.gov/zing/srw/')
            db.paths['protocolMap'] = pm
        query = self._cql_to_sql(session, query, pm)
        res = self._query(query)
        dr = res.dictresult()
        rset = SimpleResultSet([])
        rsilist = []
        for t in dr:
            (store, id) = t['recordid'].split('/',1)
            item = SimpleResultSetItem(session, id, store, 1, resultSet=rset)
            rsilist.append(item)
        rset.fromList(rsilist)
        return rset
