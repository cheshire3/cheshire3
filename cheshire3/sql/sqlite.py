
from cheshire3.exceptions import *
from cheshire3.baseStore import SimpleStore, DeletedObject
from cheshire3.baseObjects import ResultSetStore
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem
from cheshire3 import dynamic

import os
import time
import datetime
import dateutil
import struct
import StringIO
import gzip
import sqlite3


class SQLiteIter(object):
    store = None
    cxn = None
    cursor = None

    def __init__(self, session, store):
        self.session = session
        self.store = store
        query = ("SELECT identifier, data FROM %s ORDER BY identifier ASC" %
                 (self.store.id)
                 )
        self.cursor = self.store.cxn.execute(query)

    def __iter__(self):
        return self

    def next(self):
        try:
            res = self.cursor.fetchone()
            if res:
                d = [res[0], res[1].decode('string_escape')]
                return d
            else:
                raise StopIteration()
        except IndexError:
            raise StopIteration()


# Use one database per store == one file
# can create multiple tables inside it if necessary

class SQLiteStore(SimpleStore):

    cxn = None

    def __init__(self, session, config, parent):
        self.cxn = None
        SimpleStore.__init__(self, session, config, parent)
        databasePath = self.get_path(session, "databasePath", "")
        if (not databasePath):
            databasePath = ''.join([self.id, ".sqlite"])
        if (not os.path.isabs(databasePath)):
            # Prepend defaultPath from parents
            dfp = self.get_path(session, 'defaultPath')
            if (not dfp):
                raise ConfigFileException("Store has relative path, and no "
                                          "visible defaultPath.")
            databasePath = os.path.join(dfp, databasePath)
        self.paths['databasePath'] = databasePath
        if not os.path.exists(databasePath):
            self._initialise(session)
        else:
            self.cxn = sqlite3.connect(databasePath)

    def __iter__(self):
        # Return an iterator object to iter through... keys?
        return SQLiteIter(self.session, self)

    def _initialise(self, session):
        dbPath = self.get_path(session, 'databasePath')
        cxn = sqlite3.connect(dbPath)
        self.cxn = cxn
        query = """
        CREATE TABLE %s (identifier TEXT PRIMARY KEY,
        data BLOB,
        digest TEXT,
        byteCount INT,
        wordCount INT,
        expires TEXT,
        tagName TEXT,
        parentStore TEXT,
        parentIdentifier TEXT,
        timeCreated TEXT,
        timeModified TEXT);
        """ % self.id
        cxn.execute(query)

    def get_dbSize(self, session):
        query = "SELECT count(identifier) AS count FROM %s" % self.id
        cur = self.cxn.execute(query)
        res = cur.fetchone()
        return int(res[1])

    def generate_id(self, session):
        if self.useUUID:
            return self.generate_uuid(session)
        else:
            if self.currentId < 0 or session.environment == "apache":
                # find end key
                query = ("SELECT identifier FROM %s ORDER BY identifier "
                         "DESC LIMIT 1" % self.id
                         )
                cur = self.cxn.execute(query)
                res = cur.fetchone()
                # XXX Check that this is sane
                if not res:
                    self.currentId = 0
                else:
                    self.currentId = int(res[0])

            self.currentId += 1
            return self.currentId

    def store_data(self, session, id_, data, metadata={}):
        dig = metadata.get('digest', "")
        if dig:
            query = "SELECT identifier FROM %s WHERE digest = '?'"
            cur = self.cxn.execute(query, (dig,))
            exists = cur.fetchone()
            if exists:
                raise ObjectAlreadyExistsException(exists)

        if id_ is None:
            id_ = self.generate_id(session)
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)
        elif type(id_) == unicode:
            id_ = id_.encode('utf-8')
        else:
            id_ = str(id_)
        if type(data) == unicode:
            data = data.encode('utf-8')
        # Now store, with metadata
        qdata = data.encode('string_escape')

        now = time.strftime("%Y-%m-%d %H:%M:%S")
        query = ("INSERT INTO %s (identifier, timeCreated) VALUES (?, ?);" %
                 self.id
                 )
        try:
            self.cxn.execute(query, (id_, now))
        except sqlite3.IntegrityError:
            # Already exists, but that's okay
            pass

        if metadata:
            extra = []
            extraVals = [qdata]
            for (n, v) in metadata.iteritems():
                extra.append('%s =?' % n)
                extraVals.append(v)
            extraVals.extend([now(), id_])
            extraq = ', '.join(extra)
            query = ("UPDATE %s SET data = ?, %s, timeModified = ? WHERE "
                     "identifier = ?;" % (self.id, extraq)
                     )
            try:
                self.cxn.execute(query, extraVals)
            except:
                raise
        else:
            query = ("UPDATE %s SET data = ?, timeModified = ? WHERE "
                     "identifier = ?;" % (self.id)
                     )
            try:
                self.cxn.execute(query, (data, now(), id_))
            except:
                raise
        self.flush(session)
        return None

    def fetch_data(self, session, id_):
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)
        elif type(id_) == unicode:
            id_ = id_.encode('utf-8')
        else:
            id_ = str(id_)

        # Now fetch
        query = "SELECT data FROM %s WHERE identifier = ?;" % (self.id)
        cur = self.cxn.execute(query, (id_,))
        res = cur.fetchone()
        if res:
            data = res[0]
        else:
            raise ObjectDoesNotExistException(id_)
        data = data.decode('string_escape')

        if (
            data and
            data[:44] == "\0http://www.cheshire3.org/ns/status/DELETED:"
        ):
            data = DeletedObject(self, id_, data[41:])
        if data and self.expires:
            # update touched
            expires = self.generate_expires(session)
            self.store_metadata(session, id_, 'expires', expires)
            self.flush(session)
        return data

    def delete_data(self, session, id_):
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)
        elif type(id_) == unicode:
            id_ = id_.encode('utf-8')
        else:
            id_ = str(id_)

        query = "DELETE FROM %s WHERE identifier = ?;" % (self.id)
        self.cxn.execute(query, (id_,))

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            now = datetime.datetime.now(dateutil.tz.tzutc())
            now = now.strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')
            query = ("INSERT INTO %s ('identifier', 'data', 'modifiedTime') "
                     "VALUES (?, ? ,?)" % self.id
                     )
            data = "\0http://www.cheshire3.org/ns/status/DELETED:%s" % now
            self.cxn.execute(query, (id_, data, now))
        self.flush(session)
        return None

    def fetch_metadata(self, session, id_, mType):
        if mType[-7:] == "Reverse":
            # Reverse our lookup
            pass
        else:
            if (self.idNormalizer is not None):
                id_ = self.idNormalizer.process_string(session, id_)
            elif type(id_) == unicode:
                id_ = id_.encode('utf-8')
            elif type(id_) != str:
                id_ = str(id_)
            query = "SELECT %s FROM %s WHERE identifier = ?" % (mType, self.id)
            cur = self.cxn.execute(query, (id_,))
            res = cur.fetchone()
            if res:
                return res[0]
            else:
                return None

    def store_metadata(self, session, id_, mType, value):
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)
        elif type(id_) == unicode:
            id_ = id_.encode('utf-8')
        else:
            id_ = str(id_)
        query = ("UPDATE %s SET %s = ? WHERE identifier = ?" %
                 (self.table, mType)
                 )
        self.cxn.execute(query, (value, id_))
        self.flush(session)
        return value

    def flush(self, session):
        self.cxn.commit()
        dbPath = self.get_path(session, 'databasePath')
        cxn = sqlite3.connect(dbPath)
        self.cxn = cxn

    def clear(self, session):
        query = "DELETE FROM %s" % (self.id)
        self.cxn.execute(query)
        return None

    def clean(self, session):
        nowStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
        query = "DELETE FROM %s WHERE expires < '%s';" % (self.id, nowStr)
        self.cxn.execute(query)
        return None


class TrivialSqliteResultSetStore(ResultSetStore, SQLiteStore):

    def _serialise(self, session, rset):
        ids = [x.id for x in rset]
        format = '<' + 'l' * len(ids)
        data = struct.pack(format, *ids)
        data = data.encode('string_escape')
        return data

    def _deserialise(self, session, data, size, id_):
        data = data.decode('string_escape')
        fmt = '<' + 'l' * size
        ids = struct.unpack(fmt, data)
        # can't use bitfield, as need to preserve order
        rset = SimpleResultSet(session)
        items = [SimpleResultSetItem(session, x, resultSet=rset) for x in ids]
        rset.fromList(items)
        rset.id = id_
        return rset

    def _initialise(self, session):
        dbPath = self.get_path(session, 'databasePath')
        cxn = sqlite3.connect(dbPath)
        self.cxn = cxn
        query = """
        CREATE TABLE %s (identifier TEXT PRIMARY KEY,
        data BLOB,
        size INT,
        queryTime REAL,
        expires TEXT,
        timeCreated TEXT,
        timeAccessed TEXT);
        """ % self.id
        cxn.execute(query)

    def create_resultSet(self, session, rset):
        if not rset.id:
            id_ = self.generate_id(session)
            rset.id = id_
        rset.retryOnFail = 1
        self.store_resultSet(session, rset)
        return rset.id

    def store_resultSet(self, session, rset):
        now = time.time()
        nowStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))
        if (rset.expires):
            expires = now + rset.expires
        else:
            expires = now + self.get_default(session, 'expires', 600)
        rset.timeExpires = expires
        expiresStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(expires))
        id_ = rset.id
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)

        # Serialise and store
        data = self._serialise(session, rset)

        query = ("INSERT INTO %s (identifier, data, size, expires, "
                 "queryTime, timeCreated, timeAccessed) VALUES "
                 "(?, ?, ?, ?, ?, ?, ?)" % (self.id)
                 )
        try:
            self.cxn.execute(query,
                             (id_,
                              data,
                              len(rset),
                              expiresStr,
                              rset.queryTime,
                              nowStr,
                              nowStr
                              )
                             )
        except:
            # Already exists, retry for create
            if hasattr(rset, 'retryOnFail'):
                # Generate new id, re-store
                id_ = self.generate_id(session)
                if (self.idNormalizer is not None):
                    id_ = self.idNormalizer.process_string(session, id_)
                self.cxn.execute(query,
                                 (id_,
                                  data,
                                  len(rset),
                                  expiresStr,
                                  rset.queryTime,
                                  nowStr,
                                  nowStr
                                  )
                                 )
            else:
                raise ObjectAlreadyExistsException(self.id + '/' + id_)
        self.flush(session)
        return rset

    def fetch_resultSet(self, session, id_):
        sid = str(id_)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, sid)
        query = "SELECT data, size FROM %s WHERE identifier = ?" % (self.id)
        cur = self.cxn.execute(query, (sid,))
        res = cur.fetchone()
        if not res:
            raise ObjectDoesNotExistException('%s/%s' % (self.id, sid))

        data = res[0]
        size = res[1]
        rset = self._deserialise(session, data, size, id_)

        # Update expires
        now = time.time()
        nowStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))
        expires = now + self.get_default(session, 'expires', 600)
        rset.timeExpires = expires
        expiresStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(expires))
        query = ("UPDATE %s SET timeAccessed = ?, expires = ? WHERE "
                 "identifier = ?" % (self.id)
                 )
        self.cxn.execute(query, (nowStr, expiresStr, sid))
        self.flush(session)
        return rset

    def delete_resultSet(self, session, id_):
        sid = str(id_)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, sid)
        query = "DELETE FROM %s WHERE identifier = ?" % (self.table)
        self.cxn.execute(query, (sid,))
        self.flush(session)
        return None


class SimpleSqliteResultSetStore(TrivialSqliteResultSetStore):

    _possibleSettings = {
        'proxInfo': {
            'docs': ("Should the result set store maintain proximity "
                     "information. Defaults to Yes (1), but if this is not "
                     "needed, it is a significant increase in speed to turn "
                     "it off (0)"
                     ),
            'type': int
        },
        'compress': {
            'docs': ("Should the serialised result set be compressed with "
                     "gzip -1 (default, 1) or not (0)."
                     ),
            'type': int
        }
    }

    def _serialise(self, session, rset):
        srlz = rset.serialise(session,
                              pickle=self.get_setting(session, 'proxInfo', 1)
                              )

        if self.get_setting(session, 'compress', 1):
            outDoc = StringIO.StringIO()
            zfile = gzip.GzipFile(mode='wb', fileobj=outDoc, compresslevel=1)
            zfile.write(srlz)
            zfile.close()
            l = outDoc.tell()
            outDoc.seek(0)
            srlz = outDoc.read(l)
            outDoc.close()
            srlz = srlz.encode('string_escape')

        cl = str(rset.__class__)
        data = cl + "||" + srlz
        return data

    def _deserialise(self, session, data, size, id_):
        (cl, srlz) = data.split('||', 1)
        rset = dynamic.buildObject(session, cl, [[]])
        # rset = SimpleResultSet(session, [])
        if self.get_setting(session, 'compress', 1):
            # gunzip
            srlz = srlz.decode('string_escape')
            buff = StringIO.StringIO(srlz)
            zfile = gzip.GzipFile(mode='rb', fileobj=buff)
            srlz = zfile.read()
            zfile.close()
            buff.close()

        rset.deserialise(session, srlz)
        return rset
