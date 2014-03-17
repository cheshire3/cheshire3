"""ResultSetStore Implementations."""

import psycopg2
import time

from datetime import datetime, timedelta

from cheshire3 import dynamic
from cheshire3.exceptions import *
from cheshire3.resultSetStore import SimpleResultSetStore
from cheshire3.sql.postgresStore import PostgresIter, PostgresStore


class PostgresResultSetStore(PostgresStore, SimpleResultSetStore):
    """PostgreSQL ResultSetStore implementation."""

    _possibleSettings = {
        'overwriteOkay': {
            'docs': ('Can resultSets in this store be overwritten by a '
                     'resultSet with the same identifier. NB if the item '
                     'membership or order of a resultSet change, then the '
                     'resultSet is fundamentally altered and should be '
                     'assigned a new identifier. A stored resultSet should '
                     'NEVER be overwritten by one that has different items '
                     'or ordering!. 1 = Yes, 0 = No (default).'),
            'type': int,
            'options': "0|1"
        }
    }

    def __init__(self, session, node, parent):
        SimpleResultSetStore.__init__(self, session, node, parent)
        PostgresStore.__init__(self, session, node, parent)

    def _initialise(self, session):
        query = """
            CREATE TABLE {0} (identifier VARCHAR PRIMARY KEY,
            data BYTEA,
            size INT,
            class VARCHAR,
            timeCreated TIMESTAMP,
            timeAccessed TIMESTAMP,
            expires TIMESTAMP);
            """.format(self.table)
        self._query(query)

        # And check additional relations
        for (name, fields) in self.relations.iteritems():
            try:
                query = ("SELECT identifier FROM {0}_{1} LIMIT 1"
                         "".format(self.table, name))
                res = self._query(query)
            except psycopg2.ProgrammingError as e:
                # No table for relation, initialise
                query = ("CREATE TABLE {0}_{1} (identifier SERIAL PRIMARY KEY, "
                         "".format(self.table, name))
                args = []
                for f in fields:
                    query += "%s %s"
                    args.extend((f[0], f[1]))
                    if f[2]:
                        # Foreign Key
                        query += " REFERENCES {0} (identifier)".format(f[2])
                    query += ", "
                query = query[:-2] + ")"
                res = self._query(query, tuple(args))

    def store_data(self, session, id_, data, metadata={}):
        # User should call store_resultSet instead
        raise NotImplementedError("Use `store_resultSet()` method")

    def create_resultSet(self, session, rset):
        id_ = self.generate_id(session)
        rset.id = id_
        rset.retryOnFail = 1
        self.store_resultSet(session, rset)
        return id_

    def store_resultSet(self, session, rset):
        now = datetime.utcnow()
        if (rset.expires):
            expiry_delta = timedelta(rset.expires)
        else:
            expiry_delta = timedelta(self.get_default(session, 'expires', 600))
        rset.timeExpires = expires = now + expiry_delta
        id_ = rset.id
        if (self.idNormalizer is not None):
            id_ = self.idNormalizer.process_string(session, id_)
        elif isinstance(id_, unicode):
            id_ = id_.encode('utf-8')
        else:
            id_ = str(id_)
        # Serialise and store
        srlz = rset.serialize(session)
        ndata = self._escape_data(srlz)
        cl = '.'.join((rset.__class__.__module__, rset.__class__.__name__))
        query = ("INSERT INTO {0} (identifier, data, size, class, "
                 "timeCreated, timeAccessed, expires) VALUES "
                 "(%s, %s, %s, %s, %s, %s, %s)".format(self.table)
                 )
        args = (id_,
                ndata,
                len(rset),
                cl,
                now,
                now,
                expires
                )
        try:
            self._query(query, args)
        except (psycopg2.ProgrammingError, psycopg2.IntegrityError) as e:
            # Already exists, retry for overwrite, create
            if self.get_setting(session, 'overwriteOkay', 0):
                query = ("UPDATE {0} SET data = %s, size = %s, "
                         "class = %s, timeAccessed = %s, expires = %s "
                         "WHERE identifier = %s;".format(self.table)
                         )
                args = (ndata,
                        len(rset),
                        cl,
                        now,
                        expires,
                        id_
                        )
                self._query(query, args)
            elif hasattr(rset, 'retryOnFail'):
                # generate new id, re-store
                id_ = self.generate_id(session)
                if (self.idNormalizer is not None):
                    id_ = self.idNormalizer.process_string(session, id_)
                query = ("INSERT INTO {0} (identifier, data, size, class, "
                         "timeCreated, timeAccessed, expires) VALUES "
                         "(%s, %s, %s, %s, %s, %s, %s)".format(self.table)
                         )
                args = (id_,
                        ndata,
                        len(rset),
                        cl,
                        now,
                        now,
                        expires
                        )
                self._query(query, args)
            else:
                raise ObjectAlreadyExistsException(self.id + '/' + id_)
        return rset

    def fetch_resultSet(self, session, id_):
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, id_)
        elif isinstance(id_, unicode):
            sid = id_.encode('utf-8')
        else:
            sid = str(id_)
        query = ("SELECT class, data FROM {0} WHERE identifier = %s;"
                 "".format(self.table)
                 )
        res = self._query(query, (sid,))
        try:
            cl, data = res[0]
        except IndexError:
            raise ObjectDoesNotExistException('%s/%s' % (self.id, sid))
        ndata = self._unescape_data(data)
        rset = dynamic.buildObject(session, cl, [[]])
        rset.deserialize(session, ndata)
        rset.id = id_

        # Update expires
        now = datetime.utcnow()
        if (rset.expires):
            expiry_delta = timedelta(rset.expires)
        else:
            expiry_delta = timedelta(self.get_default(session, 'expires', 600))
        rset.timeExpires = expires = now + expiry_delta
        query = ("UPDATE {0} SET timeAccessed = %s, expires = %s "
                 "WHERE identifier = %s;".format(self.table)
                 )
        self._query(query, (now, expires, sid))
        return rset

    def delete_resultSet(self, session, id_):
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, id_)
        elif isinstance(id_, unicode):
            sid = id_.encode('utf-8')
        else:
            sid = str(id_)
        query = "DELETE FROM {0} WHERE identifier = %s;".format(self.table)
        self._query(query, (sid,))
