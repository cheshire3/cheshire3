
from configParser import C3Object
from baseObjects import ResultSetStore
from baseStore import BdbStore
from resultSet import SimpleResultSet, SimpleResultSetItem
import os, types, struct, sys, commands, string, time, dynamic
from c3errors import ConfigFileException


# name of result set needs to be unique within RSS
# But users may name result sets non uniquely in Z
# This map needs to happen at the user/session end
# Hence only the RSS can name a result set.

NumTypes = [types.IntType, types.LongType]

class SimpleResultSetStore(ResultSetStore):
    storeHash = {}
    storeHashReverse = {}
    databaseHash = {}
    databaseHashReverse = {}

    _possiblePaths = {'recordStoreHash' : {'docs' : "List of recordStore identifiers. Maps from position in list to int stored."},
                      'databaseHash' : {'docs' : "List of database identifiers. Maps from position in list to int stored."}}

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


class BdbResultSetStore(SimpleResultSetStore, BdbStore):

    def __init__(self, session, config, parent):
        self.databaseTypes = ['database', 'expires']
        SimpleResultSetStore.__init__(self, session, config, parent)
        BdbStore.__init__(self, session, config, parent)

    def create_resultSet(self, session, rset=None):
        id = self.generate_id(session)
        if (not rset):
            # Create a place holder with no information
            expires = self.generate_expires(session, rset)
            if expires:
                md = {'expires' : expires}
            else:
                md = {}
            self.store_data(session, id, "", md)
            self.commit_storing(session)
        else:
            rset.id = id
            self.store_resultSet(session, rset)
        return id

    def delete_resultSet(self, session, id):
        self.delete_data(session, id)
        self.commit_storing(session)

    def fetch_resultSet(self, session, id):
        data = self.fetch_data(session, id)
        if (data):
            unpacked = struct.unpack("L" * (len(data) / 4), data)
            items = []
            for o in range(len(unpacked))[::4]:
                db = self.databaseHash[unpacked[o+3]]
                items.append(SimpleResultSetItem(session, unpacked[o], self.storeHash[unpacked[o+1]], unpacked[o+2], db)) 
            return SimpleResultSet(session, items, id)
        elif (isinstance(data, DeletedObject)):
            raise ObjectDeletedException(data)
        else:
            return SimpleResultSet(session, [], id)

    def store_resultSet(self, session, rset):
        idlist = []
        for k in range(len(rset)):
            storeid = rset[k].recordStore

            id = rset[k].id
            if (not type(storeid) in NumTypes):
                # Map
                if (self.storeHashReverse.has_key(storeid)):
                    storeid = self.storeHashReverse[storeid]
                else:
                    self.storeHashReverse[storeid] = len(self.storeHash.keys())
                    self.storeHash[self.storeHashReverse[storeid]] = storeid
                    storeid = self.storeHashReverse[storeid]
            databaseid = rset[k].database
            if (not type(databaseid) in NumTypes):
                # Map
                if (self.databaseHashReverse.has_key(databaseid)):
                    databaseid = self.databaseHashReverse[databaseid]
                else:
                    self.databaseHashReverse[databaseid] = len(self.databaseHash.keys())
                    self.databaseHash[self.databaseHashReverse[databaseid]] = databaseid
                    databaseid = self.databaseHashReverse[databaseid]
                    
            idlist.extend([id, storeid, rset[k].occurences, databaseid])
        params = ['L' * len(idlist)]
        params.extend(idlist)
        data = apply(struct.pack, params)
        expires = self.generate_expires(session, rset)
        if expires:
            md = {'expires' : expires}
        else:
            md = {}
        self.store_data(session, rset.id, data, md)


class BdbResultSetStore2(BdbResultSetStore):

    _possibleSettings = {'proxInfo' : {'docs' : "Should the result set store maintain proximity information. Defaults to Yes (1), but if this is not needed, it is a significant increase in speed to turn it off (0)", 'type': int}}

    storeHash = {}
    storeHashReverse = {}
    databaseHash = {}
    databaseHashReverse = {}
    cxn = None
    txn = None

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
        srlz = rset.serialise(session, pickle=self.get_setting(session, 'proxInfo', 1))
        cl = str(rset.__class__)
        data = cl + "||" + srlz        

        expires = self.generate_expires(session, rset)
        if expires:
            md = {'expires' : expires}
        else:
            md = {}
        self.store_data(session, rset.id, data, md)
