"""ResultSetStore Implementations."""

import pg
import time

from cheshire3 import dynamic
from cheshire3.resultSetStore import SimpleResultSetStore
from cheshire3.sql.postgresStore import PostgresIter, PostgresStore


class PostgresResultSetStore(PostgresStore, SimpleResultSetStore):
    """PostgreSQL ResultSetStore implementation."""
    
    _possibleSettings = {
                         'overwriteOkay' : {'docs': 'Can resultSets in this store be overwritten by a resultSet with the same identifier. NB if the item membership or order of a resultSet change, then the resultSet is fundamentally altered and should be assigned a new identifier. A stored resultSet should NEVER be overwritten by one that has different items or ordering!. 1 = Yes, 0 = No (default).', 'type': int, 'options' : "0|1"}
                        }
    
    def __init__(self, session, node, parent):
        SimpleResultSetStore.__init__(self, session, node, parent)
        PostgresStore.__init__(self, session, node, parent)

    def _verifyDatabases(self, session):
        # Custom resultSetStore table
        try:
            #self.cxn = pg.connect(self.database)
            self._openContainer(session)
        except pg.InternalError as e:
            raise ConfigFileException("Cannot connect to Postgres: %r" % e.args)

        try:
            query = "SELECT identifier FROM %s LIMIT 1" % self.table
            res = self._query(query)
        except pg.ProgrammingError as e:
            # no table for self, initialise
            query = """
            CREATE TABLE %s (identifier VARCHAR PRIMARY KEY,
            data BYTEA,
            size INT,
            class VARCHAR,
            timeCreated TIMESTAMP,
            timeAccessed TIMESTAMP,
            expires TIMESTAMP);
            """ % self.table
            self._query(query)
            # rs.id, rs.serialise(), digest, len(rs), rs.__class__, now, expireTime
            # NB: rs can't be modified

        # And check additional relations
        for (name, fields) in self.relations.iteritems():
            try:
                query = "SELECT identifier FROM %s_%s LIMIT 1" % (self.table,name)
                res = self._query(query)
            except pg.ProgrammingError as e:
                # No table for relation, initialise
                query = "CREATE TABLE %s_%s (identifier SERIAL PRIMARY KEY, " % (self.table, name)
                for f in fields:
                    query += ("%s %s" % (f[0], f[1]))
                    if f[2]:
                        # Foreign Key
                        query += (" REFERENCES %s (identifier)" % f[2])
                    query += ", "
                query = query[:-2] + ");"                        
                res = self._query(query)


    def store_data(self, session, id, data, size=0):        
        # should call store_resultSet
        raise NotImplementedError

    def create_resultSet(self, session, rset):
        id = self.generate_id(session)
        rset.id = id
        rset.retryOnFail = 1
        self.store_resultSet(session, rset)
        return id

    def store_resultSet(self, session, rset):
        self._openContainer(session)
        now = time.time()
        nowStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))        
        if (rset.expires):
            expires = now + rset.expires
        else:
            expires = now + self.get_default(session, 'expires', 600)
        rset.timeExpires = expires
        expiresStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(expires))
        id = rset.id
        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)

        # Serialise and store
        srlz = rset.serialize(session)
        cl = str(rset.__class__)
        data = srlz.replace('\x00', '\\\\000')
        try:
            ndata = pg.escape_bytea(data)
        except:
            # insufficient PyGreSQL version - do the best we can
            ndata = data.replace("'", "\\'")
            
        query = "INSERT INTO %s (identifier, data, size, class, timeCreated, timeAccessed, expires) VALUES ('%s', E'%s', %s, '%s', '%s', '%s', '%s')" % (self.table, id, ndata, len(rset), cl, nowStr, nowStr, expiresStr)
        try:
            self._query(query)
        except pg.ProgrammingError as e:
            # already exists, retry for overwrite, create
            if self.get_setting(session, 'overwriteOkay', 0):
                query = "UPDATE %s SET data = E'%s', size = %s, class = '%s', timeAccessed = '%s', expires = '%s' WHERE identifier = '%s';" % (self.table, ndata, len(rset), cl, nowStr, expiresStr, id)
                self._query(query)
            elif hasattr(rset, 'retryOnFail'):
                # generate new id, re-store
                id = self.generate_id(session)
                if (self.idNormalizer is not None):
                    id = self.idNormalizer.process_string(session, id)
                query = "INSERT INTO %s (identifier, data, size, class, timeCreated, timeAccessed, expires) VALUES ('%s', E'%s', %s, '%s', '%s', '%s', '%s')" % (self.table, id, ndata, len(rset), cl, nowStr, nowStr, expiresStr)
                self._query(query)
            else:
                raise ObjectAlreadyExistsException(self.id + '/' + id)
        return rset

    def fetch_resultSet(self, session, id):
        self._openContainer(session)

        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, sid)
        query = "SELECT class, data FROM %s WHERE identifier = '%s';" % (self.table, sid)
        res = self._query(query)
        try:
            rdict = res.dictresult()[0]
        except IndexError:
            raise ObjectDoesNotExistException('%s/%s' % (self.id, sid))

        data = rdict['data']
        try:
            ndata = pg.unescape_bytea(data)
        except:
            # insufficient PyGreSQL version
            ndata = data.replace("\\'", "'")
            
        ndata = ndata.replace('\\000', '\x00')
        ndata = ndata.replace('\\012', '\n')
        # data is res.dictresult()
        cl = rdict['class']
        rset = dynamic.buildObject(session, cl, [[]])
        rset.deserialize(session, ndata)
        rset.id = id
        
        # Update expires 
        now = time.time()
        nowStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))        
        expires = now + self.get_default(session, 'expires', 600)
        rset.timeExpires = expires
        expiresStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(expires))

        query = "UPDATE %s SET timeAccessed = '%s', expires = '%s' WHERE identifier = '%s';" % (self.table, nowStr, expiresStr, sid)
        self._query(query)
        return rset


    def delete_resultSet(self, session, id):
        self._openContainer(session)
        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, sid)
        query = "DELETE FROM %s WHERE identifier = '%s';" % (self.table, sid)
        self._query(query)
