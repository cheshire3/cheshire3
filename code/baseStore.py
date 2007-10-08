
from c3errors import *
from configParser import C3Object
import os, md5, sha, time
from baseObjects import Session
from random import Random
from dateutil import parser as dateparser

import string
try:
    from Ft.Lib.Uuid import GenerateUuid, UuidAsString
    use4Suite = 1
except:
    use4Suite = 0

randomGen = Random(time.time())
asciiChars = string.ascii_letters + string.digits + "@%#!-=."

import datetime, dateutil.tz

try:
    # name when installed by hand
    import bsddb3 as bdb
except:
    # name that comes in python 2.3
    import bsddb as bdb


class DeletedObject(object):
    id = ""
    time = ""
    store = ""
    
    def __nonzero__(self):
        return False

    def __init__(self, store, id, time="dunno when"):
        self.store = store
        self.id = id
        self.time = time

        
class SummaryObject(object):
    """ Allow database to have summary, but no storage """

    totalItems = 0
    totalWordCount = 0
    minWordCount = 0
    maxWordCount = 0
    meanWordCount = 0
    totalByteCount = 0
    minByteCount = 0
    maxByteCount = 0
    meanByteCount = 0
    lastModified = ''

    _possiblePaths = {'metadataPath' : {'docs' : "Path to file where the summary metadata will be kept."}}

    def __init__(self, session, node, parent):

        # don't want to inherit from database!
        mp = self.paths.get('metadataPath', '')
        if not mp:
            self.paths['metadataPath'] = ''
            return
        if (not os.path.isabs(mp)):
            # Prepend defaultPath from parents
            dfp = self.get_path(session, 'defaultPath')
            if (not dfp):
                raise(ConfigFileException("Store has relative metadata path, and no visible defaultPath."))
            mp = os.path.join(dfp, mp)
        self.paths['metadataPath'] = mp

        if (not os.path.exists(mp)):
            # We don't exist, try and instantiate new database
            self._initialise(mp)
        else:
            cxn = bdb.db.DB()
            try:
                cxn.open(mp)
                # Now load values.
                
                self.totalItems = long(cxn.get("totalItems"))
                self.totalWordCount = long(cxn.get("totalWordCount"))
                self.minWordCount = long(cxn.get("minWordCount"))
                self.maxWordCount = long(cxn.get("maxWordCount"))

                self.totalByteCount = long(cxn.get("totalByteCount"))
                self.minByteCount = long(cxn.get("minByteCount"))
                self.maxByteCount = long(cxn.get("maxByteCount"))
                
                self.lastModified = str(cxn.get("lastModified"))

                if self.totalItems != 0:
                    self.meanWordCount = self.totalWordCount / self.totalItems
                    self.meanByteCount = self.totalByteCount / self.totalItems
                else:
                    self.meanWordCount = 1
                    self.meanByteCount = 1
                cxn.close()
            except:
                # Doesn't exist in usable form
                self._initialise(mp)

    def _initDb(self, session, dbt):
            dbp = dbt + "Path"
            databasePath = self.get_path(session, dbp, "")
            if (not databasePath):
                databasePath = ''.join([self.id, "_", dbt, ".bdb"])
            if (not os.path.isabs(databasePath)):
                # Prepend defaultPath from parents
                dfp = self.get_path(session, 'defaultPath')
                if (not dfp):
                    raise(ConfigFileException("Store has relative path, and no visible defaultPath."))
                databasePath = os.path.join(dfp, databasePath)
            self.paths[dbp] = databasePath
                    
    def _initialise(self, mp):
        cxn = bdb.db.DB()
        cxn.set_flags(bdb.db.DB_RECNUM)
        try:
            cxn.open(mp, dbtype=bdb.db.DB_BTREE, flags = bdb.db.DB_CREATE, mode=0660)
        except:
            raise ValueError("Could not create %s" % mp)
        cxn.put("lastModified", time.strftime('%Y-%m-%d %H:%M:%S'))
        cxn.close()

    def commit_metadata(self, session):
        cxn = bdb.db.DB()
        mp = self.get_path(session, 'metadataPath')
        if mp:
            try:
                self.meanWordCount = self.totalWordCount / self.totalItems
                self.meanByteCount = self.totalByteCount / self.totalItems
            except ZeroDivisionError:
                self.meanWordCount = 1
                self.meanByteCount = 1
                
            self.lastModified = time.strftime('%Y-%m-%d %H:%M:%S')
            try:
                cxn.open(mp)
                cxn.put("totalItems", str(self.totalItems))
                cxn.put("totalWordCount", str(self.totalWordCount))
                cxn.put("minWordCount", str(self.minWordCount))
                cxn.put("maxWordCount", str(self.maxWordCount))
                cxn.put("totalByteCount", str(self.totalByteCount))
                cxn.put("minByteCount", str(self.minByteCount))
                cxn.put("maxByteCount", str(self.maxByteCount))
                cxn.put("lastModified", self.lastModified)
                cxn.close()
            except:
                # TODO: Nicer failure?
                raise

    def accumulate_metadata(self, session, what):
        self.totalItems += 1
        self.totalWordCount += what.wordCount
        if what.wordCount < self.minWordCount:
            self.minWordCount = what.wordCount
        if what.wordCount > self.maxWordCount:
            self.maxWordCount = what.wordCount

        self.totalByteCount += what.byteCount
        if what.byteCount < self.minByteCount:
            self.minByteCount = what.byteCount
        if what.byteCount > self.maxByteCount:
            self.maxByteCount = what.byteCount
        
    

class SimpleStore(C3Object, SummaryObject):
    """ Base Store implementation.  Provides non-storage-specific functions """
    
    # Instantiate some type of simple record store
    idNormaliser = None
    outIdNormaliser = None
    inWorkflow = None
    outWorkflow = None
    storageTypes = []
    reverseMetadataTypes = []
    currentId = -1
    useUUID = 0

    _possiblePaths = {'idNormaliser' : {'docs' : "Identifier for Normaliser to use to turn the data object's identifier into a suitable form for storing. Eg: StringIntNormaliser"},
                      'outIdNormaliser' : {'docs' : "Normaliser to reverse the process done by idNormaliser"},
                      'inWorkflow' : {'docs' : "Workflow with which to process incoming data objects."},
                      'outWorkflow' : {'docs' : "Workflow with which to process stored data objects when requested."}
                      }

    _possibleSettings = {'useUUID' : {'docs' : "Each stored data object should be assigned a UUID.", 'type': int, 'options' : "0|1"},
                         'digest' : {'docs' : "Type of digest/checksum to use. Defaults to no digest", 'options': 'sha|md5'},
                         'expires' : {'docs' : "Time after ingestion at which to delete the data object in number of seconds.", 'type' : int },
                         'storeDeletions' : {'docs' : "Maintain when an object was deleted from this store.", 'type' : int, 'options' : "0|1"}
                         }

    _possibleDefaults = {'expires': {"docs" : 'Default time after ingestion at which to delete the data object in number of seconds.  Can be overridden by the individual object.', 'type' : int}}
    
    def __init__(self, session, node, parent):

        # don't inherit metadataPath!
        C3Object.__init__(self, session, node, parent)
        SummaryObject.__init__(self, session, node, parent)
        self.idNormaliser = self.get_path(session, 'idNormaliser', None)
        self.outIdNormaliser = self.get_path(session, 'outIdNormaliser', None)
        self.inWorkflow = self.get_path(session, 'inWorkflow', None)
        self.outWorkflow = self.get_path(session, 'outWorkflow', None)

        dbts = self.get_storageTypes(session)
        self.storageTypes = dbts
        revdbts = self.get_reverseMetadataTypes(session)
        self.reverseMetadataTypes = revdbts

        self.useUUID = self.get_setting(session, 'useUUID', 0)
        self.expires = self.get_default(session, 'expires', 0)

        for dbt in dbts:
            self._initDb(session, dbt)
            self._verifyDatabase(session, dbt)
            if dbt in revdbts:
                dbt = dbt + "Reverse"
                self._initDb(session, dbt)
                self._verifyDatabase(session, dbt)


    def _verifyDatabase(self, session, dbType):
        pass

    def generate_uuid(self, session):
        if (use4Suite):
            key = UuidAsString(GenerateUuid())
        else:
            key = commands.getoutput('uuidgen')
            if (len(key) != 36 or key[8] != '-'):
                # failed, generate random string instead
                c = []
                for x in range(16):
                    c.append(asciiChars[randomGen.randrange(len(asciiChars))])
                key = ''.join(c)
        return key

    def generate_checkSum(self, session, data):
        digest = self.get_setting(session, "digest")
        if (digest):
            if (digest == 'md5'):
                dmod = md5
            elif (digest == 'sha'):
                dmod = sha
            else:
                raise ConfigFileException("Unknown digest type: %s" % digest)
            m = dmod.new()

            if type(data) == unicode:
                data = data.encode('utf-8')
            m.update(data)               
            digest = m.hexdigest()
            return digest
        else:
            return None

    def generate_expires(self, session, what=None):
        now = time.time()
        if what and hasattr(what, 'expires'):            
            return now + what.expires
        elif self.expires > 0:
            return now + self.expires
        else:
            # Don't expire
            return 0

    def _openAll(self, session):
        for t in self.storageTypes:
            self._open(session, t)

    def _closeAll(self, session):
        for t in self.storageTypes:
            self._close(session, t)
        for t in self.reverseMetadataTypes:
            self._close(session, t + "Reverse")

    def begin_storing(self, session):
        self._openAll(session)
        return None

    def commit_storing(self, session):
        self._closeAll(session)
        self.commit_metadata(session)
        return None

    def get_storageTypes(self, session):
        return ['database']

    def get_reverseMetadataTypes(self, session):
        return ['digest', 'expires']
        

class BdbIter(object):
    store = None
    cursor = None
    cxn = None
    nextData = None

    def __init__(self, store):
        self.store = store
        self.session = Session()
        self.cxn = store._open(self.session, 'database')
        self.cursor = self.cxn.cursor()
        self.nextData = self.cursor.first()

    def __iter__(self):
        return self

    def next(self):
        try:
            d = self.nextData
            if not d:
                raise StopIteration()
            self.nextData = self.cursor.next()
            return d
        except:
            raise StopIteration()

    def jump(self, position):
        # Jump to this position
        self.nextData = self.cursor.set_range(position)
        return self.nextData[0]


class BdbStore(SimpleStore):
    """ Berkeley DB based storage """
    cxns = {}

    def __init__(self, session, node, parent):
        self.cxns = {}
        SimpleStore.__init__(self, session, node, parent)

    def __iter__(self):
        # Return an iterator object to iter through... keys?
        return BdbIter(self)

    def _verifyDatabase(self, session, dbt):
        dbp = self.get_path(session, dbt + "Path")
        if (not os.path.exists(dbp)):
            # We don't exist, try and instantiate new database
            self._initialise(dbp)
        else:
            cxn = bdb.db.DB()
            try:
                cxn.open(dbp)
                cxn.close()
            except:
                # Busted. Try to initialise
                self._initialise(dbp)

    def _initialise(self, dbp):
        cxn = bdb.db.DB()
        cxn.set_flags(bdb.db.DB_RECNUM)
        try:
            cxn.open(dbp, dbtype=bdb.db.DB_BTREE, flags = bdb.db.DB_CREATE, mode=0660)
        except:
            raise ValueError("Could not create: %s" % dbp)
        cxn.close()

    def _open(self, session, dbType):
        cxn = self.cxns.get(dbType, None)
        if cxn == None:
            if dbType in self.storageTypes or (dbType[-7:] == 'Reverse' and dbType[:-7] in self.reverseMetadataTypes):
                cxn = bdb.db.DB()
                cxn.set_flags(bdb.db.DB_RECNUM)
                dbp = self.get_path(session, dbType + 'Path')
                if dbp:
                    if session.environment == "apache":
                        cxn.open(dbp, flags=bdb.db.DB_NOMMAP)
                    else:
                        cxn.open(dbp)
                    self.cxns[dbType] = cxn
                    return cxn
                else:
                    return None
            else:
                # trying to store something we don't care about
                return None
        else:
            return cxn

    def _close(self, session, dbType):
        cxn = self.cxns.get(dbType, None)
        if cxn != None:
            try:
                self.cxns[dbType].close()
            except:
                # silently fail, as we're closing anyway
                pass
            self.cxns[dbType] = None

    def flush(self, session):
        # Call sync to flush all to disk
        for cxn in self.cxns.values():
            if cxn != None:
                cxn.sync()

    def generate_id(self, session):

        if self.useUUID:
            return self.generate_uuid(session)

        cxn = self._open(session, 'digest')
        if cxn == None:
            cxn = self._open(session, 'database')
        if (self.currentId == -1 or session.environment == "apache"):
            c = cxn.cursor()
            item = c.last()
            if item:
                # might need to out normalise key
                key = item[0]
                if self.outIdNormaliser:
                    key = self.outIdNormaliser.process_string(session, key)
                    if not type(key) in (int, long):
                        self.useUUID = 1
                        key = self.generate_uuid(session)
                    else:
                        key += 1
                else:
                    key = long(key)
                    key += 1
            else:
                key = 0
        else:
            key = self.currentId +1
        self.currentId = key
        return key

    def store_data(self, session, key, data, metadata={}):        
        dig = metadata.get('digest', "")
        if dig:
            cxn = self._open(session, 'digestReverse')
            if cxn:
                exists = cxn.get(dig)
                if exists:
                    raise ObjectAlreadyExistsException(exists)

        cxn = self._open(session, 'database')
        if (self.idNormaliser != None):
            key = self.idNormaliser.process_string(session, key)
        elif type(key) == unicode:
            key = key.encode('utf-8')
        else:
            key = str(key)

        if self.inWorkflow:
            data = self.inWorkflow.process(session, data)
        if type(data) == unicode:
            data = data.encode('utf-8')
        cxn.put(key, data)
        
        for (m, val) in metadata.items():
            self.set_metadata(session, key, m, val)
        return None

    def fetch_data(self, session, key):
        cxn = self._open(session, 'database')
        if (self.idNormaliser != None):
            key = self.idNormaliser.process_string(session, key)
        elif type(key) == unicode:
            key = key.encode('utf-8')
        else:
            key = str(key)
        data = cxn.get(key)

        if data and data[:41] == "\0http://www.cheshire3.org/status/DELETED:":
            data = DeletedObject(self, key, data[41:])
        elif self.outWorkflow:
            data = self.outWorkflow.process(session, data)

        if data and self.expires:
            # update touched
            expires = self.generate_expires(session)
            self.set_metadata(session, key, 'expires', expires)

        return data
        
    def delete_data(self, session, key):
        self._openAll(session)
        cxn = self._open(session, 'database')

        if (self.idNormaliser != None):
            key = self.idNormaliser.process_string(session, key)
        elif type(key) == unicode:
            key = key.encode('utf-8')
        else:
            key = str(key)

        # main database is a storageType now
        for dbt in self.storageTypes:
            cxn = self._open(session, dbt)
            if cxn != None:
                if dbt in self.reverseMetadataTypes:
                    # fetch value here, delete reverse
                    data = cxn.get(key)
                    cxn2 = self._open(session, dbt + "Reverse")                
                    if cxn2 != None:
                        cxn2.delete(data)
                cxn.delete(key)
                cxn.sync()

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            cxn = self._open(session, 'database')
            now = datetime.datetime.now(dateutil.tz.tzutc()).strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')            
            cxn.put(key, "\0http://www.cheshire3.org/status/DELETED:%s" % now)
            cxn.sync()


    def fetch_metadata(self, session, key, mtype):
        if mtype[-7:] != "Reverse":
            if (self.idNormaliser != None):
                key = self.idNormaliser.process_string(session, key)
            elif type(key) == unicode:
                key = key.encode('utf-8')
            elif type(key) != str:
                key = str(key)
        cxn = self._open(session, mtype)
        if cxn != None:
            data = cxn.get(key)
            if data:
                if mtype[-5:] == "Count" or mtype[-8:] == "Position" or mtype[-6:] in ("Amount", 'Offset'):
                    data = long(data)
                elif mtype[-4:] == "Date":
                    data = dateparser.parse(data)
            return data       
        else:
            return None

    def set_metadata(self, session, key, mtype, value):
        cxn = self._open(session, mtype)
        if cxn != None:
            if type(value) in (int, long, float):
                value = str(value)
            cxn.put(key, value)
            if mtype in self.reverseMetadataTypes:
                cxn = self._open(session, mtype + "Reverse")
                if cxn != None:
                    cxn.put(value, key)
        

    def fetch_idList(self, session, numReq=-1, start=""):
        # return numReq ids from start
        ids = []
        cxn = self._open(session, 'digest')
        if not cxn:
            cxn = self._open(session, 'database')

        # Very Slow for large DBs!
        if numReq == -1 and not start:
            keys = cxn.keys()
            return keys

        if start:
            if (self.idNormaliser != None):
                start = self.idNormaliser.process_string(session, start)
            elif type(start) == unicode:
                start = start.encode('utf-8')
            else:
                start = str(start)
                
        c = cxn.cursor()
        if (start == ""):
            try:
                (key, data) = c.first(dlen=0, doff=0)
            except:
                # No data in store
                return []
        else:
            try:
                (key, data) = c.set_range(start, dlen=0, doff=0)
            except:
                # No data after point in store
                return []
        ids.append(key)
        if numReq == -1:
            tup = c.next(dlen=0, doff=0)
            while tup:
                ids.append(tup[0])
	        tup = c.next(dlen=0, doff=0)
        else:
            for x in range(numReq-1):
                try:
                    ids.append(c.next()[0])
                except:
                    break
        return ids

    def clean(self, session, force=False):
        # check for expires
        # NB this zeros the data pages, but does not zero the file size
        # delete the files to do that ;)

        self._openAll(session)
        if force or not self.cxns.has_key('expiresReverse'):
            deleted = self.cxns['database'].stat(bdb.db.DB_FAST_STAT)['nkeys']
            for c in self.cxns:
                self.cxns[c].truncate()
        else:
            now = time.time()
            cxn = self._open(session, 'expiresReverse')
            c = cxn.cursor()
            deleted = 0
            try:
                (key, data) = c.set_range(str(now))
                # float(time) --> object id
                if (float(key) <= now):
                    self.delete_data(session, data)
                    deleted = 1
                (key, data) = c.prev()
            except:
                # No database
                deleted = 0
                key = False
            while key:
                self.delete_data(session, data)
                deleted += 1
                try:
                    (key, data) = c.prev()
                    if not float(key):
                        break
                except:
                    # Reached beginning
                    break
        self._closeAll(session)        
        return deleted


    def get_dbsize(self, session):
        cxn = self._open(session, 'digest')
        if not cxn:
            cxn = self._open(session, 'database')
        return cxn.stat(bdb.db.DB_FAST_STAT)['nkeys']



class FileSystemIter(object):
    store = None
    cursor = None
    cxn = None
    nextData = None

    def __init__(self, store):
        self.store = store
        self.session = Session()
        self.cxn = store._open(self.session, 'byteCount')
        self.cursor = self.cxn.cursor()
        (key, val) = self.cursor.first()
        self.nextData = (key, self.store.fetch_data(self.session, key))

    def __iter__(self):
        return self

    def next(self):
        try:
            d = self.nextData
            if not d:
                raise StopIteration()
            (key, val) = self.cursor.next()
            self.nextData = (key, self.store.fetch_data(self.session, key))
            return d
        except:
            raise StopIteration()

    def jump(self, position):
        # Jump to this position
        self.nextData = self.cursor.set_range(position)
        return self.nextData[0]


class FileSystemStore(BdbStore):
    # Leave the data somewhere on disk    
    # Use metadata to map identifier to file, offset, length
    # Object to be stored needs this information, obviously!

    currFileHandle = None
    currFileName = ""


    def __iter__(self):
        return FileSystemIter(self)

    def get_storageTypes(self, session):
        return ['filename', 'byteCount', 'byteOffset']

    def get_reverseMetadataTypes(self, session):
        return ['digest', 'expires']


    def store_data(self, session, key, data, metadata={}):        
        dig = metadata.get('digest', "")
        if dig:
            cxn = self._open(session, 'digestReverse')
            if cxn:
                exists = cxn.get(dig)
                if exists:
                    raise ObjectAlreadyExistsException(exists)

        if (self.idNormaliser != None):
            key = self.idNormaliser.process_string(session, key)
        elif type(key) == unicode:
            key = key.encode('utf-8')
        else:
            key = str(key)

        if not (metadata.has_key('filename') and metadata.has_key('byteCount') and metadata.has_key('byteOffset')):
            raise SomeException("Need file, byteOffset and byteCount to use FileSystemStore")

        for (m, val) in metadata.items():
            self.set_metadata(session, key, m, val)
        return None

    def fetch_data(self, session, key):
        if (self.idNormaliser != None):
            key = self.idNormaliser.process_string(session, key)
        elif type(key) == unicode:
            key = key.encode('utf-8')
        else:
            key = str(key)

        filename = self.fetch_metadata(session, key, 'filename')
        start = self.fetch_metadata(session, key, 'byteOffset')
        length = self.fetch_metadata(session, key, 'byteCount')

        if filename != self.currFileName:
            if self.currFileHandle:
                self.currFileHandle.close()
            self.currFileHandle = file(filename)
        try:
            self.currFileHandle.seek(start)
        except:
            # closed, reopen
            self.currFileHandle = file(filename)
            self.currFileHandle.seek(start)
        data = self.currFileHandle.read(length)

        if data and data[:41] == "\0http://www.cheshire3.org/status/DELETED:":
            data = DeletedObject(self, key, data[41:])
        elif self.outWorkflow:
            data = self.outWorkflow.process(session, data)

        if data and self.expires:
            # update touched
            expires = self.generate_expires(session)
            self.set_metadata(session, key, 'expires', expires)
        return data
        
    def delete_data(self, session, key):
        self._openAll(session)

        if (self.idNormaliser != None):
            key = self.idNormaliser.process_string(session, key)
        elif type(key) == unicode:
            key = key.encode('utf-8')
        else:
            key = str(key)

        filename = self.fetch_metadata(session, key, 'filename')
        start = self.fetch_metadata(session, key, 'byteOffset')
        length = self.fetch_metadata(session, key, 'byteCount')

        # main database is a storageType now
        for dbt in self.storageTypes:
            cxn = self._open(session, dbt)
            if cxn != None:
                if dbt in self.reverseMetadataTypes:
                    # fetch value here, delete reverse
                    data = cxn.get(key)
                    cxn2 = self._open(session, dbt + "Reverse")                
                    if cxn2 != None:
                        cxn2.delete(data)
                cxn.delete(key)
                cxn.sync()

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            now = datetime.datetime.now(dateutil.tz.tzutc()).strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')            
            out = "\0http://www.cheshire3.org/status/DELETED:%s" % now

            if len(out) < length:
                f = file(filename, 'w')
                f.seek(start)
                f.write(out)
                f.close()
            else:
                # Can't write deleted status as original doc is shorter than deletion info!
                pass
