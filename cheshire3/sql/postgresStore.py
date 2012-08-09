"""PosgreSQL Store Abstract Classes."""

# Consider psycopg
import pg
import time
from lxml import etree

from cheshire3.baseStore import SimpleStore
from cheshire3.exceptions import *
from cheshire3.utils import elementType, getFirstData, nonTextToken, flattenTexts

# shouldn't really be here, but haven't had time to investigate yet...
from cheshire3.resultSet import SimpleResultSetItem

class PostgresIter(object):
    """Iterator for Cheshire3 PostgresStores."""
    
    store = None
    cxn = None
    idList = None
    cursor = None

    def __init__(self, session, store):
        self.session = session
        self.store = store
        self.cxn = pg.connect(self.store.database)
        query = "SELECT identifier FROM %s ORDER BY identifier ASC" % (self.store.table)
        query = query.encode('utf-8')
        res = self.cxn.query(query)
        all = res.dictresult()
        self.idList = [item['identifier'] for item in all]
        self.cursor = 0

    def __iter__(self):
        return self

    def next(self):
        """Return next data from Iterator"""
        try:
            query = "SELECT * FROM %s WHERE identifier='%s' LIMIT 1" % (self.store.table, self.idList[self.cursor])
            query = query.encode('utf-8')
            res = self.cxn.query(query)
            self.cursor +=1
            d = res.getresult()[0]
            while d and (d[0][:2] == "__"):
                query = "SELECT * FROM %s WHERE identifier='%s' LIMIT 1" % (self.store.table, self.idList[self.cursor])
                query = query.encode('utf-8')
                res = self.cxn.query(query)
                self.cursor +=1
                d = res.getresult()[0]
            
            if not d:
                raise StopIteration()
            return d
        except IndexError:
            raise StopIteration()

class PostgresStore(SimpleStore):
    """An interface to PosgreSQL storage mechanism for Cheshire3 objects (Abstract)."""
    
    cxn = None
    relations = {}

    _possiblePaths = {'databaseName' : {'docs' : "Database in which to store the data"}
                      , 'tableName' : {'docs' : "Table in the database in which to store the data"}
                      }
    # , 'idNormalizer'  : {'docs' : ""}}

    def __init__(self, session, config, parent):
        SimpleStore.__init__(self, session, config, parent)
        self.database = self.get_path(session, 'databaseName', 'cheshire3')
        self.table = self.get_path(session, 'tableName', parent.id + '_' + self.id)
        self.idNormalizer = self.get_path(session, 'idNormalizer', None)
        self._verifyDatabases(session)
        self.session = session
        
    def __iter__(self):
        # Return an iterator object to iter through
        return PostgresIter(self.session, self)

    def _handleConfigNode(self, session, node):
        if (node.nodeType == elementType and node.localName == 'relations'):
            self.relations = {}
            for rel in node.childNodes:
                if (rel.nodeType == elementType and rel.localName == 'relation'):
                    relName = rel.getAttributeNS(None, 'name')
                    fields = []
                    for fld in rel.childNodes:
                        if fld.nodeType == elementType:
                            if fld.localName == 'object':
                                oid = getFirstData(fld)
                                fields.append([oid, 'VARCHAR', oid])
                            elif fld.localName == 'field':
                                fname = fld.getAttributeNS(None, 'name')
                                ftype = getFirstData(fld)
                                fields.append([fname, ftype, ''])
                    self.relations[relName] = fields
        #- end _handleConfigNode ------------------------------------------

    def _handleLxmlConfigNode(self, session, node):
        if node.tag in ['relations', '{%s}relations' % CONFIG_NS]:
            self.relations = {}
            for rel in node.iterchildren(tag=etree.Element):
                if rel.tag in ['relation', '{%s}relation' % CONFIG_NS]:
                    relName = rel.attrib.get('name', None)
                    if relName is None:
                        raise ConfigFileException('Name not supplied for relation')
                    fields = []
                    for fld in rel.iterchildren(tag=etree.Element):
                        if fld.tag in ['object', '{%s}object' % CONFIG_NS]:
                            oid = flattenTexts(fld)
                            fields.append([oid, 'VARCHAR', oid])
                        elif fld.tag in ['field', '{%s}field' % CONFIG_NS]:
                            fname = fld.attrib.get('name', None)
                            if fname is None:
                                 ConfigFileException('Name not supplied for field')
                            ftype = flattenTexts(fld)
                            fields.append([fname, ftype, ''])
                            
                    self.relations[relName] = fields
        #- end _handleLxmlConfigNode ------------------------------------------

    def _verifyDatabases(self, session):
        try:
#            self.cxn = pg.connect(self.database)
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
            digest VARCHAR(41),
            byteCount INT,
            wordCount INT,
            expires TIMESTAMP,
            tagName VARCHAR,
            parentStore VARCHAR,
            parentIdentifier VARCHAR,
            timeCreated TIMESTAMP,
            timeModified TIMESTAMP);
            """ % self.table
            self._query(query)


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
                        query += (" REFERENCES %s (identifier) ON DELETE cascade" % f[2])
                    query += ", "
                query = query[:-2] + ") ;"                        
                res = self._query(query)

    def _openContainer(self, session):
        if self.cxn is None:
            self.cxn = pg.connect(self.database)

    def _closeContainer(self, session):
        if self.cxn is not None:
            self.cxn.close()
            del self.cxn
            self.cxn = None

    def _query(self, query):
        if self.cxn is None:
            self.cxn = pg.connect(self.database)
        query = query.encode('utf-8')
        res = self.cxn.query(query)
        return res

    def begin_storing(self, session):
        self._openContainer(session)
        return None

    def commit_storing(self, session):
        self._closeContainer(session)
        return None

    def generate_id(self, session):
        self._openContainer(session)
        # Find greatest current id
        if (self.currentId == -1 or session.environment == 'apache'):
            query = "SELECT CAST(identifier AS int) FROM %s ORDER BY identifier DESC LIMIT 1;" % self.table
            res = self._query(query)
            try:
                id = int(res.dictresult()[0]['identifier']) +1
            except:
                id = 0
            self.currentId = id
            return id
        else:
            self.currentId += 1
            return self.currentId

    def store_data(self, session, id, data, metadata={}):        
        self._openContainer(session)
        id = str(id)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        data = data.replace(nonTextToken, '\\\\000\\\\001')

        query = "INSERT INTO %s (identifier, timeCreated) VALUES ('%s', '%s');" % (self.table, id, now)
        try:
            self._query(query)
        except:
            # already exists
            pass

        try:
            ndata = pg.escape_bytea(data)
        except:
            # insufficient PyGreSQL version
            ndata = data.replace("'", "\\'")

        if metadata:
            extra = []
            for (n,v) in metadata.iteritems():
                if type(v) in (int, long):
                    extra.append('%s = %s' % (n,v))
                else:
                    extra.append("%s = '%s'" % (n,v))
            extraq = ', '.join(extra)
            query = "UPDATE %s SET data = E'%s', %s, timeModified = '%s' WHERE identifier = '%s';" % (self.table, ndata, extraq, now, id)
        else:
            query = "UPDATE %s SET data = E'%s', timeModified = '%s' WHERE  identifier = '%s';" % (self.table, ndata, now, id)

        try:
            self._query(query)
        except pg.ProgrammingError:
            # Uhhh...
            print query
            raise
        return None


    def fetch_data(self, session, id):
        self._openContainer(session)
        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, sid)
        query = "SELECT data FROM %s WHERE identifier = '%s';" % (self.table, sid)
        res = self._query(query)
        try:
            data = res.dictresult()[0]['data']
        except IndexError:
            raise ObjectDoesNotExistException(id)
        
        try:
            ndata = pg.unescape_bytea(data)
        except:
            # insufficient PyGreSQL version
            ndata = data.replace("\\'", "'")
            
        ndata = ndata.replace('\\000\\001', nonTextToken)
        ndata = ndata.replace('\\012', '\n')
        return ndata

    def delete_data(self, session, id):
        self._openContainer(session)
        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, str(id))
        query = "DELETE FROM %s WHERE identifier = '%s';" % (self.table, sid)
        self._query(query)
        return None

    def fetch_metadata(self, session, id, mType):
        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)
        self._openContainer(session)
        query = "SELECT %s FROM %s WHERE identifier = '%s';" % (mType, self.table, id)
        res = self._query(query)
        try:
            data = res.dictresult()[0][mtype]
        except:
            if mtype.endswith(("Count", "Position", "Amount", "Offset")):
                return 0
            return None
        return data

    def store_metadata(self, session, key, mType, value):
        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)
        self._openContainer(session)
        query = "UPDATE %s SET %s = %r WHERE identifier = '%s';" % (self.table, mType, value, id)
        try:
            self._query(query)
        except:
            return None
        return value

    def clear(self, session):
        self._openContainer(session)
        query = "DELETE FROM %s" % (self.table)
        self._query(query)    
    
    def clean(self, session):
        # here is where sql is nice...
        self._openContainer(session)
        nowStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
        query = "DELETE FROM %s WHERE expires < '%s';" % (self.table, nowStr)
        self._query(query)

    def get_dbSize(self, session):
        query = "SELECT count(identifier) AS count FROM %s;" % (self.table)
        res = self._query(query)
        return res.dictresult()[0]['count']


    # NOT API
    def link(self, session, relation, *args, **kw):
        # create a new row in the named relation
        fields = []
        values = []
        for obj in args:
            #fields.append(obj.recordStore)
            fields.append(self.table)        # allows to link for objects other than Records
            oid = obj.id
            if (self.idNormalizer):
                oid = self.idNormalizer.process_string(session, oid)                
            values.append(repr(oid))
        for (name, value) in kw.iteritems():
            fields.append(name)
            if isinstance(value, basestring) and value.find("'") > -1:
                values.append("E'{0}'".format(value.replace("'", r"\'")))
            else:
                values.append(repr(value))

        query = "INSERT INTO %s_%s (%s) VALUES (%s);" % (self.table, relation, ', '.join(fields), ', '.join(values))
        self._query(query)
        

    # Also NOT API
    def unlink(self, session, relation, *args, **kw):
        conds = []
        for obj in args:
            oid = obj.id
            if (self.idNormalizer):
                oid = self.idNormalizer.process_string(session, oid)                
            #cond += ("%s = %r, " % (obj.recordStore, oid))
            conds.append("%s = %r" % (self.table, oid)) # allows to unlink for objects other than Records
        for (name, value) in kw.iteritems():
            conds.append("%s = %r" % (name, value))
        query = "DELETE FROM %s_%s WHERE %s;" % (self.table, relation, ' AND '.join(conds))
        self._query(query)


    # STILL NOT API
    def get_links(self, session, relation, *args, **kw):
        conds = []
        for obj in args:
            oid = obj.id
            if (self.idNormalizer):
                oid = self.idNormalizer.process_string(session, oid)                
            #cond += ("%s = %r, " % (obj.recordStore, oid))
            conds.append("%s = %r" % (self.table, oid))        # allows get_links for objects other than Records
        for (name, value) in kw.iteritems():
            conds.append("%s = %r" % (name, value))           
        query = "SELECT * FROM %s_%s WHERE %s;" % (self.table, relation, ', '.join(conds))
        res = self._query(query)

        links = []
        reln = self.relations[relation]
        for row in res.getresult():
            link = []
            linkHash = {}
            for i in range(len(row)):
                name = reln[i-1][0]
                if (reln[i-1][2]):
                    link.append(SimpleResultSetItem(session, row[i], name))
                else:
                    linkHash[name] = row[i]

            links.append((link, linkHash))
        return links
