"""SQL Store Abstract Base Classes."""

from datetime import datetime

from cheshire3.baseStore import SimpleStore
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.utils import nonTextToken


class SQLIter(object):
    """Iterator for DB-API 2.0 compliant SQL Stores."""

    store = None
    cxn = None
    position = None
    idList = None

    def __init__(self, session, store):
        self.session = session
        self.store = store
        query = ("SELECT identifier FROM {0} ORDER BY identifier ASC"
                 "".format(self.store.table)
                 )
        query = query.encode('utf-8')
        with self._connect(store.database) as cxn:
            with cxn.cursor() as cur:
                cur.execute(query)
                self.idList = [row[0] for row in cur]
        self.position = 0

    def __iter__(self):
        return self

    def _connect(self):
        raise NotImplementedError()

    def next(self):
        """Return next data from Iterator"""
        with self._connect() as cxn:
            try:
                query = ("SELECT * FROM {0} WHERE identifier = %s LIMIT 1"
                         "".format(self.store.table)
                         )
                query = query.encode('utf-8')
                with cxn.cursor() as cursor:
                    cursor.execute(query, (self.idList[self.position]))
                    self.position += 1
                    d = cursor.fetchone()
                while d and (d[0][:2] == "__"):
                    query = ("SELECT * FROM {0} WHERE identifier = %s LIMIT 1"
                             "".format(self.store.table)
                             )
                    query = query.encode('utf-8')
                    with cxn.cursor() as cursor:
                        cursor.execute(query, (self.idList[self.position]))
                        self.position += 1
                        d = self.cursor.fetchone()
                if not d:
                    raise StopIteration()
                return d
            except IndexError:
                raise StopIteration()


class SQLStore(SimpleStore):
    """DB-API 2.0 compliant SQL Store implementation.

    Cheshire3 base Store implementation that are compliant with DB-API 2.0
    (Python Database API Specification v2.0).
    """

    cxn = None

    _possiblePaths = {
        'databasePath': {
            'docs': "Database in which to store the data"
        },
        'tableName': {
            'docs': "Table in the database in which to store the data"
        }
    }

    def __init__(self, session, config, parent):
        SimpleStore.__init__(self, session, config, parent)
        # Try databaseName for backward compatibility
        self.database = self.get_path(session, 'databasePath', "")
        self.table = self.get_path(session,
                                   'tableName',
                                   parent.id + '_' + self.id
                                   )
        self._verifyDatabases(session)

    def __iter__(self):
        # Return an iterator object to iter through
        return SQLIter(self.session, self)

    def _verifyDatabases(self, session):
        query = "SELECT identifier FROM {0} LIMIT 1".format(self.table)
        try:
            self._query(query)
        except:
            self._initialise(session)

    def _connect(self, session):
        raise NotImplementedError()

    def _initialise(self, session):
        raise NotImplementedError()

    def _query(self, query, args=tuple()):
        query = query.encode('utf-8')
        with self._connect(self.session) as cxn:
            with cxn.cursor() as cur:
                cur.execute(query, args)
                try:
                    return cur.fetchall()
                except:
                    # CREATE TABLE, DELETE etc do not return results
                    return

    def _escape_data(self, data):
        return data.replace(nonTextToken, '\\\\000\\\\001')

    def _unescape_data(self, data):
        return data.replace('\\000\\001', nonTextToken)

    def begin_storing(self, session):
        pass

    def commit_storing(self, session):
        pass

    def generate_id(self, session):
        # Find greatest current id
        if (self.currentId == -1 or session.environment == 'apache'):
            query = ("SELECT CAST(identifier AS int) FROM {0} ORDER BY "
                     "identifier DESC LIMIT 1".format(self.table)
                     )
            res = self._query(query)
            try:
                id_ = int(res[0][0]) + 1
            except:
                id_ = 0
            self.currentId = id_
            return id_
        else:
            self.currentId += 1
            return self.currentId

    def store_data(self, session, id_, data, metadata={}):
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)
        elif isinstance(id_, unicode):
            id_ = id_.encode('utf-8')
        else:
            id_ = str(id_)
        now = datetime.utcnow()
        query = ("INSERT INTO {0} (identifier, timeCreated) VALUES (%s, %s);"
                 "".format(self.table)
                 )
        args = (id_, now)
        try:
            self._query(query, args)
        except:
            # Already exists
            pass
        query = ("UPDATE {0} SET data = %s, timeModified = %s "
                 "WHERE identifier = %s;".format(self.table)
                 )
        args = (self._escape_data(data), now, id_)
        try:
            self._query(query, args)
        except:
            # Uhhh...
            print query
            raise
        for (mType, value) in metadata.iteritems():
            self.store_metadata(session, id_, mType, value)

    def fetch_data(self, session, id_):
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, id_)
        elif isinstance(id_, unicode):
            sid = id_.encode('utf-8')
        else:
            sid = str(id_)
        query = ("SELECT data FROM {0} WHERE identifier = %s"
                 "".format(self.table))
        res = self._query(query, (sid,))
        try:
            data = res[0][0]
        except IndexError:
            return None
        return self._unescape_data(data)

    def delete_data(self, session, id_):
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, id_)
        elif isinstance(id_, unicode):
            sid = id_.encode('utf-8')
        else:
            sid = str(id_)
        query = "DELETE FROM {0} WHERE identifier = %s".format(self.table)
        self._query(query, (sid))

    def fetch_metadata(self, session, id_, mType):
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)
        elif isinstance(id_, unicode):
            id_ = id_.encode('utf-8')
        else:
            id_ = str(id_)
        if mType == "creationDate":
            mType = "timeCreated"
        elif mType == "modificationDate":
            mType = "timeModified"
        query = ("SELECT {0} FROM {1} WHERE identifier = %s"
                 "".format(mType, self.table))
        res = self._query(query, (id_,))
        try:
            data = res[0][0]
        except IndexError:
            raise ObjectDoesNotExistException()
        except KeyError:
            if mType.endswith(("Count", "Position", "Amount", "Offset")):
                return 0
            return None
        return data

    def store_metadata(self, session, id_, mType, value):
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)
        elif isinstance(id_, unicode):
            id_ = id_.encode('utf-8')
        else:
            id_ = str(id_)
        if mType == "creationDate":
            mType = "timeCreated"
        elif mType == "modificationDate":
            mType = "timeModified"
        query = ("UPDATE {0} SET {1} = %s WHERE identifier = %s"
                 "".format(self.table, mType)
                 )
        args = (value, id_)
        try:
            self._query(query, args)
        except:
            return None
        return value

    def clear(self, session):
        query = "DELETE FROM {0}".format(self.table)
        self._query(query)

    def clean(self, session):
        # here is where sql is nice...
        now = datetime.utcnow()
        query = "DELETE FROM {0} WHERE expires < %s".format(self.table)
        self._query(query, (now,))

    def get_dbSize(self, session):
        query = "SELECT count(identifier) AS count FROM {0}".format(self.id)
        res = self._query(query)
        return int(res[0][0])
