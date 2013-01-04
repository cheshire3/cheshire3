from __future__ import absolute_import

import os
import sys
import commands
import string
import time
import types
import struct

from cheshire3.configParser import C3Object
from cheshire3.baseObjects import ResultSetStore
from cheshire3.baseStore import BdbStore
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem
from cheshire3.exceptions import ConfigFileException
from cheshire3 import dynamic


NumTypes = [types.IntType, types.LongType]


class SimpleResultSetStore(ResultSetStore):

    storeHash = {}
    storeHashReverse = {}
    databaseHash = {}
    databaseHashReverse = {}

    _possiblePaths = {
        'recordStoreHash': {
            'docs': ("List of recordStore identifiers. "
                     "Maps from position in list to int stored.")
        },
        'databaseHash': {
            'docs': ("List of database identifiers. "
                     "Maps from position in list to int stored.")
        }
    }

    def __init__(self, session, config, parent):
        ResultSetStore.__init__(self, session, config, parent)
        rsh = self.get_path(session, 'recordStoreHash')
        if rsh:
            wds = rsh.split()
            for w in range(len(wds)):
                self.storeHash[long(w)] = wds[w]
                self.storeHashReverse[wds[w]] = long(w)
        dbsh = self.get_path(session, 'databaseHash')
        if dbsh:
            wds = dbsh.split()
            for w in range(len(wds)):
                self.databaseHash[long(w)] = wds[w]
                self.databaseHashReverse[wds[w]] = long(w)

    def create_resultSet(self, session, rset=None):
        id = self.generate_id(session)
        if (not rset):
            # Create a place holder with no information
            expires = self.generate_expires(session, rset)
            if expires:
                md = {'expires': expires}
            else:
                md = {}
            self.store_data(session, id, "", md)
            self.commit_storing(session)
        else:
            rset.id = id
            self.store_resultSet(session, rset)
        return id

    def fetch_resultSet(self, session, id):
        data = self.fetch_data(session, id)
        if (data):
            (cl, srlz) = data.split('||', 1)
            rset = dynamic.buildObject(session, cl, [])
            rset.deserialise(session, srlz)
            return rset
        else:
            return SimpleResultSet(session, [], id)

    def store_resultSet(self, session, rset):
        # Serialise resultSet to data + class
        srlz = rset.serialise(session,
                              pickleOk=self.get_setting(session,
                                                        'proxInfo',
                                                        1)
                              )
        cl = '{0}.{1}'.format(rset.__class__.__module__,
                              rset.__class__.__name__)
        data = cl + "||" + srlz
        expires = self.generate_expires(session, rset)
        if expires:
            md = {'expires': expires}
        else:
            md = {}
        self.store_data(session, rset.id, data, md)

    def delete_resultSet(self, session, id):
        self.delete_data(session, id)
        self.commit_storing(session)


class BdbResultSetStore(SimpleResultSetStore, BdbStore):

    _possibleSettings = {
        'proxInfo': {
            'docs': ("Should the result set store maintain proximity "
                     "information. Defaults to Yes (1), but if this is not "
                     "needed, it is a significant increase in speed to turn "
                     "it off (0)"),
            'type': int
        }
    }

    storeHash = {}
    storeHashReverse = {}
    databaseHash = {}
    databaseHashReverse = {}
    cxn = None
    txn = None

    def __init__(self, session, config, parent):
        self.databaseTypes = ['database', 'expires']
        SimpleResultSetStore.__init__(self, session, config, parent)
        BdbStore.__init__(self, session, config, parent)


class BdbResultSetStore2(BdbResultSetStore):
    pass
