"""PosgreSQL Store Abstract Classes."""

import psycopg2

from contextlib import contextmanager
from datetime import datetime
from psycopg2.pool import ThreadedConnectionPool

from lxml import etree

from cheshire3.baseStore import SimpleStore
from cheshire3.exceptions import ConfigFileException
from cheshire3.internal import CONFIG_NS
from cheshire3.utils import (
    elementType,
    getFirstData,
    flattenTexts,
    nonTextToken
)
from cheshire3.sql.sqlStore import SQLIter, SQLStore

from cheshire3.resultSet import SimpleResultSetItem


class PostgresIter(object):
    """Iterator for Cheshire3 PostgresStores."""

    def _connect(self):
        return self.store._connect(self.session)


class PostgresStore(SQLStore):
    """Cheshire3 object storage abstraction for PostgreSQL."""

    relations = {}

    def __init__(self, session, config, parent):
        SimpleStore.__init__(self, session, config, parent)
        # Try databaseName for backward compatibility
        self.database = self.get_path(session, 'databaseName', "cheshire3")
        self.table = self.get_path(session,
                                   'tableName',
                                   parent.id + '_' + self.id
                                   )
        self.connectionPool = ThreadedConnectionPool(
            5,
            10,
            "dbname={0}".format(self.database)
        )
        self._verifyDatabases(session)

    def __del__(self):
        self.connectionPool.closeall()

    def __iter__(self):
        # Return an iterator object to iter through
        return PostgresIter(self.session, self)

    def _handleConfigNode(self, session, node):
        if (node.nodeType == elementType and node.localName == 'relations'):
            self.relations = {}
            for rel in node.childNodes:
                if (
                    rel.nodeType == elementType and
                    rel.localName == 'relation'
                ):
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
        #- end _handleConfigNode --------------------------------------------

    def _handleLxmlConfigNode(self, session, node):
        if node.tag in ['relations', '{%s}relations' % CONFIG_NS]:
            self.relations = {}
            for rel in node.iterchildren(tag=etree.Element):
                if rel.tag in ['relation', '{%s}relation' % CONFIG_NS]:
                    relName = rel.attrib.get('name', None)
                    if relName is None:
                        raise ConfigFileException('Name not supplied for '
                                                  'relation')
                    fields = []
                    for fld in rel.iterchildren(tag=etree.Element):
                        if fld.tag in ['object', '{%s}object' % CONFIG_NS]:
                            oid = flattenTexts(fld)
                            fields.append([oid, 'VARCHAR', oid])
                        elif fld.tag in ['field', '{%s}field' % CONFIG_NS]:
                            fname = fld.attrib.get('name', None)
                            if fname is None:
                                ConfigFileException('Name not supplied for '
                                                    'field')
                            ftype = flattenTexts(fld)
                            fields.append([fname, ftype, ''])

                    self.relations[relName] = fields
        #- end _handleLxmlConfigNode ----------------------------------------

    @contextmanager
    def _connect(self, session):
        try:
            cxn = self.connectionPool.getconn()
        except psycopg2.OperationalError as e:
            raise ConfigFileException("Cannot connect to Postgres: %r" %
                                      e.args
                                      )
        yield cxn
        # Commit transactions
        cxn.commit()
        # Return the cxn top the pool
        self.connectionPool.putconn(cxn)

    def _initialise(self, session):
        query = """
            CREATE TABLE {0} (identifier VARCHAR PRIMARY KEY,
            data BYTEA,
            digest VARCHAR(41),
            byteCount INT,
            wordCount INT,
            expires TIMESTAMP,
            tagName VARCHAR,
            parentStore VARCHAR,
            parentIdentifier VARCHAR,
            timeCreated TIMESTAMP,
            timeModified TIMESTAMP)""".format(self.table)
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
                        query += (" REFERENCES {0} (identifier) ON DELETE "
                                  "cascade".format(f[2])
                                  )
                    query += ", "
                query = query[:-2] + ")"
                res = self._query(query, tuple(args))

    def _escape_data(self, data):
        data = data.replace(nonTextToken, '\\\\000\\\\001')
        return psycopg2.Binary(data)

    def _unescape_data(self, data):
        data = str(data)
        return data.replace('\\000\\001', nonTextToken)

    def link(self, session, relation, *args, **kw):
        """Create a new row in the named relation.

        NOT API
        """
        fields = []
        values = []
        for obj in args:
            #fields.append(obj.recordStore)
            # Allows to link for objects other than Records
            fields.append(self.table)
            oid = obj.id
            if (self.idNormalizer):
                oid = self.idNormalizer.process_string(session, oid)
            values.append(oid)
        for (name, value) in kw.iteritems():
            fields.append(name)
            values.append(value)

        valuemarkers = ["%s" for i in range(len(values))]
        query = ("INSERT INTO {0}_{1} ({2}) VALUES ({3});"
                 "".format(self.table,
                           relation,
                           ', '.join(fields),
                           ', '.join(valuemarkers)
                           )
                 )
        self._query(query, tuple(values))

    def unlink(self, session, relation, *args, **kw):
        """Remove a row in the named relation.

        NOT API
        """
        condvals = []
        conds = []
        for obj in args:
            oid = obj.id
            if (self.idNormalizer):
                oid = self.idNormalizer.process_string(session, oid)
            # Allows to unlink for objects other than Records
            condvals.append(oid)
            conds.append("%s = %%s" % (self.table))

        for (name, value) in kw.iteritems():
            condvals.append(value)
            conds.append("%s = %%s" % (name))
        query = ("DELETE FROM {0}_{1} WHERE {2}"
                 "".format(self.table, relation, ' AND '.join(conds))
                 )
        self._query(query, tuple(condvals))

    def get_links(self, session, relation, *args, **kw):
        """Get linked rows in the named relation.

        NOT API
        """
        condvals = []
        conds = []
        for obj in args:
            oid = obj.id
            if (self.idNormalizer):
                oid = self.idNormalizer.process_string(session, oid)
            # Allows get_links for objects other than Records
            condvals.append(oid)
            conds.append("{0} = %s".format(self.table))

        for (name, value) in kw.iteritems():
            condvals.append(value)
            conds.append("{0} = %s".format(name))
        query = ("SELECT * FROM {0}_{1} WHERE {2};"
                 "".format(self.table, relation, ', '.join(conds))
                 )
        res = self._query(query, tuple(condvals))
        links = []
        reln = self.relations[relation]
        for row in res:
            link = []
            linkHash = {}
            for i in range(len(row)):
                name = reln[i - 1][0]
                if (reln[i - 1][2]):
                    link.append(SimpleResultSetItem(session, row[i], name))
                else:
                    linkHash[name] = row[i]

            links.append((link, linkHash))
        return links
