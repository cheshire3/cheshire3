
from cheshire3.configParser import C3Object
from cheshire3.baseStore import SimpleStore
from cheshire3.baseObjects import Database
from cheshire3.recordStore import SimpleRecordStore, BdbRecordStore
from cheshire3.documentStore import SimpleDocumentStore
from cheshire3.objectStore import SimpleObjectStore
from cheshire3.resultSetStore import SimpleResultSetStore
from cheshire3.documentFactory import MultipleDocumentStream

from cheshire3.exceptions import ObjectAlreadyExistsException, ObjectDoesNotExistException, ConfigFileException


from cheshire3.indexStore import BdbIndexStore
from cheshire3.baseStore import SwitchingBdbConnection
import bsddb as bdb


import irods, irods_error
import time, datetime, dateutil
import sys, os


def icatValToPy(val, un):
    if un in ['int', 'long']:
        return long(val)
    elif un == 'unicode':
        return val.decode('utf-8')
    elif un == 'float':
        return float(val)
    else:
        return val

def pyValToIcat(val):
    x = type(val)
    if x in [int, long]:
        return ("%020d" % val, 'long')
    elif x == unicode:
        return (val.encode('utf-8'), 'unicode')
    elif x == float:
        return ('%020f' % val, 'float')
    else:
        return (val, 'str')

    
class IrodsStore(SimpleStore):

    cxn = None
    coll = None

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

    _possiblePaths = {'idNormalizer' : {'docs' : "Identifier for Normalizer to use to turn the data object's identifier into a suitable form for storing. Eg: StringIntNormalizer"},
                      'outIdNormalizer' : {'docs' : "Normalizer to reverse the process done by idNormalizer"},
                      'inWorkflow' : {'docs' : "Workflow with which to process incoming data objects."},
                      'outWorkflow' : {'docs' : "Workflow with which to process stored data objects when requested."},
                      'irodsCollection' : {'docs' : "Top collection in irods"}
                      }

    _possibleSettings = {'useUUID' : {'docs' : "Each stored data object should be assigned a UUID.", 'type': int, 'options' : "0|1"},
                         'digest' : {'docs' : "Type of digest/checksum to use. Defaults to no digest", 'options': 'sha|md5'},
                         'expires' : {'docs' : "Time after ingestion at which to delete the data object in number of seconds.", 'type' : int },
                         'storeDeletions' : {'docs' : "Maintain when an object was deleted from this store.", 'type' : int, 'options' : "0|1"},
                         'irodsHost' : {'docs' :'', 'type' : str},
                         'irodsPort' : {'docs' :'', 'type' : int},
                         'irodsUser' : {'docs' :'', 'type' : str},
                         'irodsZone' : {'docs' :'', 'type' : str},
                         'irodsPasswd' : {'docs' :'', 'type' : str},
                         'createSubDir' : {'docs' :'', 'type' : int, 'options' : "0|1"},
                         'allowStoreSubDirs' : {'docs' : '', 'type' : int, 'options' : '0|1'}
                         }

    _possibleDefaults = {'expires': {"docs" : 'Default time after ingestion at which to delete the data object in number of seconds.  Can be overridden by the individual object.', 'type' : int}}
    

    def __init__(self, session, config, parent):
        C3Object.__init__(self, session, config, parent)
        self.cxn = None
        self.coll = None
        self.env = None
        self.idNormalizer = self.get_path(session, 'idNormalizer', None)
        self.outIdNormalizer = self.get_path(session, 'outIdNormalizer', None)
        self.inWorkflow = self.get_path(session, 'inWorkflow', None)
        self.outWorkflow = self.get_path(session, 'outWorkflow', None)
        self.session = session

        self.useUUID = self.get_setting(session, 'useUUID', 0)
        self.expires = self.get_default(session, 'expires', 0)

        self.host = self.get_setting(session, 'irodsHost', '')
        self.port = self.get_setting(session, 'irodsPort', 0)
        self.user = self.get_setting(session, 'irodsUser', '')
        self.zone = self.get_setting(session, 'irodsZone', '')
        self.passwd = self.get_setting(session, 'irodsPassword', '')

        self.allowStoreSubDirs = self.get_setting(session, 'allowStoreSubDirs', 1)
        self._open(session)


    def get_metadataTypes(self, session):
        return {'totalItems' : long,
                'totalWordCount' : long,
                'minWordCount' : long,
                'maxWordCount' : long,
                'totalByteCount' : long,
                'minByteCount' : long,
                'maxByteCount' : long,
                'lastModified' : str}

    def _open(self, session):

        if self.cxn == None:
            # connect to iRODS
            myEnv, status = irods.getRodsEnv()

            host = self.host if self.host else myEnv.getRodsHost()
            port = self.port if self.host else myEnv.getRodsPort()
            user = self.user if self.host else myEnv.getRodsUserName()
            zone = self.zone if self.host else myEnv.getRodsZone()
            
            conn, errMsg = irods.rcConnect(host, port, user, zone)
            if self.passwd:
                status = irods.clientLoginWithPassword(conn, zone)
            else:
                status = irods.clientLogin(conn)

            if status:
                raise ConfigFileException("Cannot connect to iRODS: (%s) %s" % (status, errMsg))
            self.cxn = conn
            self.env = myEnv

            resources = irods.getResources(self.cxn)
            self.resourceHash = {}
            for r in resources:
                self.resourceHash[r.getName()] = r

            
        if self.coll != None:
            # already open, just skip
            return None

        c = irods.irodsCollection(self.cxn, self.env.getRodsHome())
        self.coll = c

        # move into cheshire3 section
        path = self.get_path(session, 'irodsCollection', 'cheshire3')
        dirs = c.getSubCollections()
        if not path in dirs:
            c.createCollection(path)
        c.openCollection(path)


        if self.get_setting(session, 'createSubDir', 1):
            # now look for object's storage area
            # maybe move into database collection
            if (isinstance(self.parent, Database)):
                sc = self.parent.id
                dirs = c.getSubCollections()
                if not sc in dirs:
                    c.createCollection(sc)
                c.openCollection(sc)
            # move into store collection
            dirs = c.getSubCollections()
            if not self.id in dirs:
                c.createCollection(self.id)
            c.openCollection(self.id)

        # Fetch user metadata
        myMetadata = self.get_metadataTypes(session)
        umd = c.getUserMetadata()
        umdHash = {}
        for u in umd:
            umdHash[u[0]] = icatValToPy(*u[1:])

        for md in myMetadata:
            try:
                setattr(self, md, umdHash[md])
            except KeyError:
                # hasn't been set yet
                pass

        if self.totalItems != 0:
            self.meanWordCount = self.totalWordCount / self.totalItems
            self.meanByteCount = self.totalByteCount / self.totalItems
        else:
            self.meanWordCount = 1
            self.meanByteCount = 1

        
    def _close(self, session):
        irods.rcDisconnect(self.cxn)
        self.cxn = None
        self.coll = None


    def _queryMetadata(self, session, attName, opName, attValue):

        genQueryInp = irods.genQueryInp_t()
        # select what we want to fetch
        i1 = irods.inxIvalPair_t()
        i1.addInxIval(irods.COL_DATA_NAME, 0)
        genQueryInp.setSelectInp(i1)

        attValue, units = pyValToIcat(attValue)
        
        i2 = irods.inxValPair_t()
        i2.addInxVal(irods.COL_META_DATA_ATTR_NAME, "='%s'" % attName)
        i2.addInxVal(irods.COL_META_DATA_ATTR_VALUE, "%s '%s'" % (opName, attValue))

        self._open(session)
        collName = self.coll.getCollName()
        i2.addInxVal(irods.COL_COLL_NAME, "= '%s'" % collName)

        genQueryInp.setSqlCondInp(i2)

        # configure paging
        genQueryInp.setMaxRows(1000)
        genQueryInp.setContinueInx(0)

        matches = []
        # do query
        genQueryOut, status = irods.rcGenQuery(self.cxn, genQueryInp)
        if status == irods_error.CAT_NO_ROWS_FOUND:
            return []
        elif status == 0:
            sqlResults = genQueryOut.getSqlResult()
            matches = sqlResults[0].getValues()
        
        while status == 0 and genQueryOut.getContinueInx() > 0:
            genQueryInp.setContinueInx(genQueryOut.getContinueInx())
            genQueryOut, status = irods.rcGenQuery(self.cxn, genQueryInp)
            sqlResults = genQueryOut.getSqlResult()
            matches.extend(sqlResults[0].getValues())
        return matches


    def commit_metadata(self, session):
        mymd = self.get_metadataTypes(session)
        # need to delete values first
        umd = self.coll.getUserMetadata()
        umdHash = {}
        for u in umd:
            umdHash[u[0]] = u[1:]            
        for md in mymd:
            try:
                self.coll.rmUserMetadata(md, umdHash[md][0])
            except KeyError:
                # not been set yet
                pass
            val, un = pyValToIcat(getattr(self, md))
            self.coll.addUserMetadata(md, val, un)

    def begin_storing(self, session):
        self._open(session)
        return None

    def commit_storing(self, session):
        self.commit_metadata(session)
        self._close(session)
        return None

    def get_dbSize(self, session):
        return self.coll.getLenObjects()

    def delete_data(self, session, id):
        # delete data stored against id
        if (self.idNormalizer != None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        # all metadata stored on object, no need to delete from elsewhere
        self._open(session)

        upwards = 0
        if id.find('/') > -1 and self.allowStoreSubDirs:
            idp = id.split('/')
            id = idp.pop()
            while idp:
                dn = idp.pop(0)
                if not dn in self.coll.getSubCollections():
                    for x in range(upwards):
                        self.coll.upCollection()
                    raise ObjectDoesNotExistException(id)
                self.coll.openCollection(dn)
                upwards += 1
        else:
            id = id.replace('/', '--')

        self.coll.delete(id)

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            now = datetime.datetime.now(dateutil.tz.tzutc()).strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')
            data = "\0http://www.cheshire3.org/ns/status/DELETED:%s" % now
            f = self.coll.create(id)
            f.write(data)
            f.close()

        for x in range(upwards):
            self.coll.upCollection()
        return None

    def fetch_data(self, session, id):
        # return data stored against id
        if (self.idNormalizer != None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        self._open(session)

        upwards = 0
        if id.find('/') > -1 and self.allowStoreSubDirs:
            idp = id.split('/')
            id = idp.pop()
            while idp:
                dn = idp.pop(0)
                if not dn in self.coll.getSubCollections():                    
                    for x in range(upwards):
                        self.coll.upCollection()
                    return None
                self.coll.openCollection(dn)
                upwards += 1
        else:
            id = id.replace('/', '--')

        f = self.coll.open(id)        
        if f:
            data = f.read()
            f.close()
        else:
            print "COULD NOT FIND: %s in %s" % (id, self.coll.getCollName())
            for x in range(upwards):
                self.coll.upCollection()
            return None
        
        if data and data[:44] == "\0http://www.cheshire3.org/ns/status/DELETED:":
            data = DeletedObject(self, id, data[41:])
        if data and self.expires:
            expires = self.generate_expires(session)
            self.store_metadata(session, id, 'expires', expires)
        for x in range(upwards):
            self.coll.upCollection()
        return data

    def store_data(self, session, id, data, metadata):
        dig = metadata.get('digest', "")
        if dig:
            match = self._queryMetadata(session, 'digest', '=', dig)
            if match:
                raise ObjectAlreadyExistsException(match[0])

        if id == None:
            id = self.generate_id(session)
        if (self.idNormalizer != None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        if type(data) == unicode:
            data = data.encode('utf-8')
        self._open(session)

        upwards = 0
        if id.find('/') > -1 and self.allowStoreSubDirs:
            idp = id.split('/')
            id = idp.pop()
            while idp:
                dn = idp.pop(0)
                if not dn in self.coll.getSubCollections():
                    self.coll.createCollection(dn)
                self.coll.openCollection(dn)
                upwards += 1
        else:
            id = id.replace('/', '--')
            
        # XXX This should be in a try/except/finally block
        f = self.coll.create(id)
        if not f:
            for x in range(upwards):
                self.coll.upCollection()
            raise ValueError("Cannot create new file: %s" % id)
        f.write(data)
        f.close()

        # store metadata with object
        for (m, val) in metadata.iteritems():
            self.store_metadata(session, id, m, val)

        for x in range(upwards):
            self.coll.upCollection()

        return None

    def replicate_data(self, session, id, location):

        if not self.resourceHash.has_key(location):
            raise ObjectDoesNotExistException('Unknown Storage Resource: %s' % location)

        if id == None:
            id = self.generate_id(session)
        if (self.idNormalizer != None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        upwards = 0
        if id.find('/') > -1 and self.allowStoreSubDirs:
            idp = id.split('/')
            id = idp.pop()
            while idp:
                dn = idp.pop(0)
                if not dn in self.coll.getSubCollections():
                    for x in range(upwards):
                        self.coll.upCollection()
                    raise ObjectDoesNotExistException(id)
                self.coll.openCollection(dn)
                upwards += 1
        else:
            id = id.replace('/', '--')

        f = self.coll.open(id)
        f.replicate(location)
        f.close()
        for x in range(upwards):
            self.coll.upCollection()
        return None

    def fetch_metadata(self, session, id, mType):
        # open irodsFile and get metadata from it

        if (self.idNormalizer != None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        self._open(session)

        upwards = 0
        if id.find('/') > -1 and self.allowStoreSubDirs:
            idp = id.split('/')
            id = idp.pop()
            while idp:
                dn = idp.pop(0)
                if not dn in self.coll.getSubCollections():
                    for x in range(upwards):
                        self.coll.upCollection()
                    raise ObjectDoesNotExistException(id)
                self.coll.openCollection(dn)
                upwards += 1
        else:
            id = id.replace('/', '--')

        f = self.coll.open(id)
        umd = f.getUserMetadata()
        val = None
        for x in umd:
            if x[0] == mType:
                val = icatValToPy(x[1], x[2])
                break
        f.close()
        for x in range(upwards):
            self.coll.upCollection()
        return val

        
    def store_metadata(self, session, id, mType, value):
        # store value for mType metadata against id

        if (self.idNormalizer != None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        self._open(session)
        f = self.coll.open(id)
        f.addUserMetadata(mType, *pyValToIcat(value))
        f.close()
    
    def clean(self, session):
        # delete expired data objects
        # self.cxn.query('select data_name from bla where expire < now')
        now = time.time()
        now = pyValToIcat(now)[0]
        matches = self._queryMetadata(session, 'expires', '<', now)
        for m in matches:
            self.delete_data(session, m)
        return None

    def clear(self, session):
        # delete all objects
        self._open(session)
        for o in self.coll.getObjects():
            self.coll.delete(o)
        # reset metadata
        mt = self.get_metadataTypes(session)
        for (n, t) in mt.iteritems():
            setattr(self, n, t(0))
        return None
            
    def flush(self, session):
        # ensure all data is flushed to disk... don't think there's an equivalent
        return None


# hooray for multiple inheritance!

class IrodsRecordStore(SimpleRecordStore, IrodsStore):
    def __init__(self, session, config, parent):
        IrodsStore.__init__(self, session, config, parent)
        SimpleRecordStore.__init__(self, session, config, parent)

class IrodsDocumentStore(SimpleDocumentStore, IrodsStore):
    def __init__(self, session, config, parent):
        IrodsStore.__init__(self, session, config, parent)
        SimpleDocumentStore.__init__(self, session, config, parent)
        
class IrodsObjectStore(SimpleObjectStore, IrodsStore):
    def __init__(self, session, config, parent):
        IrodsStore.__init__(self, session, config, parent)
        SimpleObjectStore.__init__(self, session, config, parent)

class IrodsResultSetStore(SimpleResultSetStore, IrodsStore):
    def __init__(self, session, config, parent):
        IrodsStore.__init__(self, session, config, parent)
        SimpleResultSetStore.__init__(self, session, config, parent)


#-------------------------------


class IrodsSwitchingBdbConnection(SwitchingBdbConnection):

    # Fetch to local for manipulation, but maintain in irods

    def __init__(self, session, parent, path="", maxBuckets=0, maxItemsPerBucket=0, bucketType=''):
        SwitchingBdbConnection.__init__(self, session, parent, path, maxBuckets, maxItemsPerBucket, bucketType)
        if parent.coll == None:
            parent._openIrods(session)
        self.irodsObjects = parent.coll.getObjects()
        self.cxnFiles = {}


    def bucket_exists(self, b):
        return b in self.irodsObjects or os.path.exists(self.basePath + '_' + b)
            
    def _open(self, b):
        if self.cxns.has_key(b) and self.cxns[b] != None:
            return self.cxns[b] 
        else:
            cxn = bdb.db.DB()
            if self.preOpenFlags:
                cxn.set_flags(self.preOpenFlags)
            dbp = self.basePath + "_" + b

            if (not os.path.exists(dbp)):
                # find file name
                (d, fn) = os.path.split(dbp)
                if fn in self.irodsObjects:
                    # suck it down
                    inf = self.store.coll.open(fn)
                    outf = file(dbp,'w')
                    data = inf.read(1024000)
                    while data:
                        outf.write(data)
                        data = inf.read(1024000)
                    inf.close()
                    outf.close()
                else:
                    cxn.open(dbp, **self.store.createArgs[self.basePath])
                    cxn.close()
                    cxn = bdb.db.DB()                

            cxn.open(dbp, **self.openArgs)
            self.cxns[b] = cxn
            self.cxnFiles[cxn] = dbp
            return cxn

    def close(self):
        for (k, c) in self.cxns.iteritems():
            c.close()
            # upload to irods
            srcPath = self.cxnFiles[c]
            (dirn, fn) = os.path.split(srcPath)        

            # use file/C api
            dataObjOprInp = irods.dataObjInp_t()
            dataObjOprInp.setOprType(irods.PUT_OPR)
            dataObjOprInp.setOpenFlags(irods.O_RDWR)
            targPath = self.store.coll.getCollName() + "/" + fn
            statbuf = os.stat(srcPath)            
            dataObjOprInp.setCreateMode(statbuf.st_mode)
            dataObjOprInp.setObjPath(targPath)
            dataObjOprInp.setDataSize(statbuf.st_size)
            irods.rcDataObjPut(self.store.cxn, dataObjOprInp, srcPath)

            self.cxns[k] = None
        return None

    def sync(self):
        # sync all
        for (k, c) in self.cxns.iteritems():
            c.sync()
        return None



class IrodsSwitchingRecordStore(BdbRecordStore):

    def __init__(self, session, config, parent):
        self.switchingClass = IrodsSwitchingBdbConnection
        self.coll = None
        self.cxn = None
        self.env = None
        
        # And open irods
        BdbRecordStore.__init__(self, session, config, parent)
        self.switchingClass = IrodsSwitchingBdbConnection
        self._openIrods(session)
        

    def _openIrods(self, session):

        if self.cxn == None:
            # connect to iRODS
            myEnv, status = irods.getRodsEnv()
            conn, errMsg = irods.rcConnect(myEnv.getRodsHost(), myEnv.getRodsPort(), 
                                           myEnv.getRodsUserName(), myEnv.getRodsZone())
            status = irods.clientLogin(conn)
            if status:
                raise ConfigFileException("Cannot connect to iRODS: (%s) %s" % (status, errMsg))
            self.cxn = conn
            self.env = myEnv
            
        if self.coll != None:
            # already open, just skip
            return None

        c = irods.irodsCollection(self.cxn, self.env.getRodsHome())
        self.coll = c

        # move into cheshire3 section
        path = self.get_path(session, 'irodsCollection', 'cheshire3')
        dirs = c.getSubCollections()
        if not path in dirs:
            c.createCollection(path)
        c.openCollection(path)

        # now look for object's storage area
        # maybe move into database collection
        if (isinstance(self.parent, Database)):
            sc = self.parent.id
            dirs = c.getSubCollections()
            if not sc in dirs:
                c.createCollection(sc)
            c.openCollection(sc)

        # move into store collection
        dirs = c.getSubCollections()
        if not self.id in dirs:
            c.createCollection(self.id)
        c.openCollection(self.id)

        
    def _closeIrods(self, session):
        irods.rcDisconnect(self.cxn)
        self.cxn = None
        self.coll = None
        self.env = None


# -----------------------------------------------------------

class IrodsIndexStore(BdbIndexStore):

    def __init__(self, session, config, parent):
        BdbIndexStore.__init__(self, session, config, parent)

        self.switchingClass = IrodsSwitchingBdbConnection
        self.vectorSwitchingClass = IrodsSwitchingBdbConnection
        self.coll = None
        self.cxn = None
        self.env = None
        
        # And open irods
        self._open(session)
        

    def _open(self, session):

        if self.cxn == None:
            # connect to iRODS
            myEnv, status = irods.getRodsEnv()
            conn, errMsg = irods.rcConnect(myEnv.getRodsHost(), myEnv.getRodsPort(), 
                                           myEnv.getRodsUserName(), myEnv.getRodsZone())
            status = irods.clientLogin(conn)
            if status:
                raise ConfigFileException("Cannot connect to iRODS: (%s) %s" % (status, errMsg))
            self.cxn = conn
            self.env = myEnv
            
        if self.coll != None:
            # already open, just skip
            return None

        c = irods.irodsCollection(self.cxn, self.env.getRodsHome())
        self.coll = c

        # move into cheshire3 section
        path = self.get_path(session, 'irodsCollection', 'cheshire3')
        dirs = c.getSubCollections()
        if not path in dirs:
            c.createCollection(path)
        c.openCollection(path)

        # now look for object's storage area
        # maybe move into database collection
        if (isinstance(self.parent, Database)):
            sc = self.parent.id
            dirs = c.getSubCollections()
            if not sc in dirs:
                c.createCollection(sc)
            c.openCollection(sc)

        # move into store collection
        dirs = c.getSubCollections()
        if not self.id in dirs:
            c.createCollection(self.id)
        c.openCollection(self.id)

        
    def _close(self, session):
        irods.rcDisconnect(self.cxn)
        self.cxn = None
        self.coll = None
        self.env = None

