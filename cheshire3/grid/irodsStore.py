
import os
import time
import datetime
import dateutil

try:
    import irods
except ImportError:
    irods = None

import bsddb as bdb

from cheshire3.configParser import C3Object
from cheshire3.baseStore import SimpleStore, DeletedObject
from cheshire3.baseStore import SwitchingBdbConnection
from cheshire3.baseObjects import Database
from cheshire3.documentStore import SimpleDocumentStore
from cheshire3.exceptions import *
from cheshire3.indexStore import BdbIndexStore
from cheshire3.objectStore import SimpleObjectStore
from cheshire3.recordStore import SimpleRecordStore, BdbRecordStore
from cheshire3.resultSetStore import SimpleResultSetStore

from cheshire3.grid.irods_utils import icatValToPy, pyValToIcat


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

    _possiblePaths = {
        'idNormalizer': {
            'docs': ("Identifier for Normalizer to use to turn the data "
                     "object's identifier into a suitable form for "
                     "storing. E.g.: StringIntNormalizer")
        },
        'outIdNormalizer': {
            'docs': ("Normalizer to reverse the process done by "
                     "idNormalizer")
        },
        'inWorkflow': {
            'docs': "Workflow with which to process incoming data objects."
        },
        'outWorkflow': {
            'docs': ("Workflow with which to process stored data objects "
                     "when requested.")
        },
        'irodsCollection': {
            'docs': "Top collection in irods"
        }
    }

    _possibleSettings = {
        'useUUID': {
            'docs': "Each stored data object should be assigned a UUID.",
            'type': int,
            'options': "0|1"
        },
        'digest': {
            'docs': ("Type of digest/checksum to use. Defaults to no "
                     "digest"),
            'options': 'sha|md5'
        },
        'expires': {
            'docs': ("Time after ingestion at which to delete the data "
                     "object in number of seconds."),
            'type': int
        },
        'storeDeletions': {
            'docs': "Maintain when an object was deleted from this store.",
            'type': int,
            'options': "0|1"
        },
        'irodsHost': {
            'docs': '',
            'type': str
        },
        'irodsPort': {
            'docs': '',
            'type': int
        },
        'irodsUser': {
            'docs': '',
            'type': str
        },
        'irodsZone': {
            'docs': '',
            'type': str
        },
        'irodsPassword': {
            'docs': '',
            'type': str
        },
        'irodsResource': {
            'docs': '',
            'type': str
        },
        'createSubDir': {
            'docs': ("Should a sub-directory/sub-collection be used for this "
                     "store"),
            'type': int,
            'options': "0|1"
        },
        'allowStoreSubDirs': {
            'docs': '',
            'type': int,
            'options': '0|1'
        }
    }

    _possibleDefaults = {
        'expires': {
            'docs': ("Default time after ingestion at which to delete the "
                     "data object in number of seconds.  Can be "
                     "overridden by the individual object."),
            'type': int
        }
    }

    def __init__(self, session, config, parent):
        C3Object.__init__(self, session, config, parent)
        if irods is None:
            raise MissingDependencyException(self.objectType, 'irods (PyRods)')
        self.cxn = None
        self.coll = None
        self.env = None
        self.idNormalizer = self.get_path(session, 'idNormalizer', None)
        self.outIdNormalizer = self.get_path(session,
                                             'outIdNormalizer',
                                             None)
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
        self.resource = self.get_setting(session, 'irodsResource', '')

        self.allowStoreSubDirs = self.get_setting(session,
                                                  'allowStoreSubDirs',
                                                  1)
        self._open(session)

    def __iter__(self):
        return irodsStoreIterator(self.session, self)

    def get_metadataTypes(self, session):
        return {'totalItems': long,
                'totalWordCount': long,
                'minWordCount': long,
                'maxWordCount': long,
                'totalByteCount': long,
                'minByteCount': long,
                'maxByteCount': long,
                'lastModified': str}

    def _open(self, session):
        if self.cxn is None:
            # connect to iRODS
            status, myEnv = irods.getRodsEnv()
            # Host
            if self.host:
                host = self.host
            else:
                try:
                    host = myEnv.getRodsHost()
                except AttributeError:
                    host = myEnv.rodsHost
            # Port
            if self.port:
                port = self.port
            else:
                try:
                    myEnv.getRodsPort()
                except AttributeError:
                    port = myEnv.rodsPort
            # User
            if self.user:
                username = myEnv.rodsUserName
            else:
                try:
                    username = myEnv.getRodsUserName()
                except AttributeError:
                    username = myEnv.rodsUserName
            # Zone
            if self.zone:
                zone = self.zone
            else:
                try:
                    zone = myEnv.getRodsZone()
                except AttributeError:
                    zone = myEnv.rodsZone

            conn, errMsg = irods.rcConnect(host, port, username, zone)
            if self.passwd:
                status = irods.clientLoginWithPassword(conn, self.passwd)
            else:
                status = irods.clientLogin(conn)

            if status:
                raise ConfigFileException("Cannot connect to iRODS: (%s)"
                                          " %s" % (status, errMsg))
            self.cxn = conn
            self.env = myEnv

            resources = irods.getResources(self.cxn)
            self.resourceHash = {}
            for r in resources:
                self.resourceHash[r.getName()] = r

        if self.coll is not None:
            # Already open, just skip
            return None
        try:
            rodsHome = myEnv.getRodsHome()
        except AttributeError:
            rodsHome = myEnv.rodsHome
        c = irods.irodsCollection(self.cxn, rodsHome)
        self.coll = c

        # Move into cheshire3 section
        path = self.get_path(session, 'irodsCollection', 'cheshire3')
        dirs = c.getSubCollections()
        if not path in dirs:
            c.createCollection(path)
        c.openCollection(path)

        if self.get_setting(session, 'createSubDir', 1):
            # Now look for object's storage area
            # Maybe move into database collection
            if (isinstance(self.parent, Database)):
                sc = self.parent.id
                dirs = c.getSubCollections()
                if not sc in dirs:
                    c.createCollection(sc)
                c.openCollection(sc)
            # Move into store collection
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
        i2.addInxVal(irods.COL_META_DATA_ATTR_VALUE,
                     "%s '%s'" % (opName, attValue))

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
        if status == 0:
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
        """ Delete data stored against id. """
        if (self.idNormalizer is not None):
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

        if self.resource:
            self.coll.delete(id, self.resource)
        else:
            self.coll.delete(id)

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            now = datetime.datetime.now(dateutil.tz.tzutc())
            now = now.strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')
            data = "\0http://www.cheshire3.org/ns/status/DELETED:%s" % now
            f = self.coll.create(id)
            f.write(data)
            f.close()
        for x in range(upwards):
            self.coll.upCollection()
        return None

    def fetch_data(self, session, id):
        """ Fetch and return data stored against id. """
        if (self.idNormalizer is not None):
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

        if self.resource:
            f = self.coll.open(id, rescName=self.resource)
        else:
            f = self.coll.open(id)        
        if f:
            data = f.read()
            f.close()
        else:
            for x in range(upwards):
                self.coll.upCollection()
            return None

        if (
            data and
            data.startswith("\0http://www.cheshire3.org/ns/status/"
                            "DELETED:")
        ):
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

        if id is None:
            id = self.generate_id(session)
        if (self.idNormalizer is not None):
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
        if self.resource:
            f = self.coll.create(id, self.resource)
        else:
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
        """Replicate data object across known iRODS Storage Resources."""

        if not self.resourceHash.has_key(location):
            raise ObjectDoesNotExistException('Unknown Storage Resource: '
                                              '%s' % location)

        if id is None:
            id = self.generate_id(session)
        if (self.idNormalizer is not None):
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
        """ Open irodsFile and get metadata from it. """

        if (self.idNormalizer is not None):
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

        collPath = self.coll.getCollName()
        # This is much more efficient than getting the file as it's simply
        # interacting with iCAT
        umd = irods.getFileUserMetadata(self.cxn,
                                        '{0}/{1}'.format(collPath, id)
                                        )

#        if self.resource:
#            f = self.coll.open(id, rescName=self.resource)
#        else:
#            f = self.coll.open(id)
#	
#        if not f:
#            for x in range(upwards):
#                self.coll.upCollection()
#                return None
#        umd = f.getUserMetadata()
#        f.close()

        val = None
        for x in umd:
            if x[0] == mType:
                val = icatValToPy(x[1], x[2])
                break

        for x in range(upwards):
            self.coll.upCollection()
        return val

    def store_metadata(self, session, id, mType, value):
        """ Store value for mType metadata against id. """
        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        self._open(session)
        upwards = 0
        if id.find('/') > -1 and self.allowStoreSubDirs:
            idp = id.split('/')
            id = idp.pop()  # file is final part
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

        collPath = self.coll.getCollName()
        # this is much more efficient than getting the file as it's simply
        # interacting with iCAT
        irods.addFileUserMetadata(self.cxn,
                                  '{0}/{1}'.format(collPath, id),
                                  mType, *pyValToIcat(value)
                                  )

#        if self.resource:
#                f = self.coll.open(id, rescName=self.resource)
#            else:
#                f = self.coll.open(id)
#
#        if not f:
#            for x in range(upwards):
#        	self.coll.upCollection()
#            return None
#
#        f.addUserMetadata(mType, *pyValToIcat(value))
#        f.close()

        for x in range(upwards):
            self.coll.upCollection()

    def clean(self, session):
        """ Delete expired data objects. """
        now = time.time()
        now = pyValToIcat(now)[0]
        matches = self._queryMetadata(session, 'expires', '<', now)
        for m in matches:
            self.delete_data(session, m)
        return None

    def clear(self, session):
        """ Delete all objects. """
        self._open(session)
        for o in self.coll.getObjects():
            self.coll.delete(o[0], o[1])
        # reset metadata
        mt = self.get_metadataTypes(session)
        for (n, t) in mt.iteritems():
            setattr(self, n, t(0))
        return None

    def flush(self, session):
        """ Ensure all data is flushed to disk.

        Don't think there's an equivalent for iRODS."""
        return None


class IrodsSwitchingBdbConnection(SwitchingBdbConnection):

    # Fetch to local for manipulation, but maintain in irods

    def __init__(self, session, parent, path="",
                 maxBuckets=0, maxItemsPerBucket=0, bucketType=''):
        SwitchingBdbConnection.__init__(self, session, parent, path,
                                        maxBuckets, maxItemsPerBucket,
                                        bucketType)
        if irods is None:
            raise MissingDependencyException(self.objectType,
                                             'irods (PyRods)'
                                             )
        if parent.coll is None:
            parent._openIrods(session)
        self.irodsObjects = parent.coll.getObjects()
        self.cxnFiles = {}

    def bucket_exists(self, b):
        return (b in self.irodsObjects or
                os.path.exists(self.basePath + '_' + b))
            
    def _open(self, b):
        if self.cxns.has_key(b) and self.cxns[b] is not None:
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
                    outf = file(dbp, 'w')
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
        if irods is None:
            raise MissingDependencyException(self.objectType,
                                             'irods (PyRods)'
                                             )
        self.switchingClass = IrodsSwitchingBdbConnection
        self._openIrods(session)

    def _openIrods(self, session):

        if self.cxn is None:
            # connect to iRODS
            myEnv, status = irods.getRodsEnv()
            conn, errMsg = irods.rcConnect(myEnv.getRodsHost(),
                                           myEnv.getRodsPort(), 
                                           myEnv.getRodsUserName(),
                                           myEnv.getRodsZone()
                                           )
            status = irods.clientLogin(conn)
            if status:
                raise ConfigFileException("Cannot connect to iRODS: (%s) %s"
                                          "" % (status, errMsg))
            self.cxn = conn
            self.env = myEnv

        if self.coll is not None:
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


class IrodsIndexStore(BdbIndexStore):

    _possiblePaths = {
        'idNormalizer': {
            'docs': ("Identifier for Normalizer to use to turn the data "
                     "object's identifier into a suitable form for storing. "
                     "Eg: StringIntNormalizer")
        },
        'outIdNormalizer': {
            'docs': "Normalizer to reverse the process done by idNormalizer"
        },
        'inWorkflow': {
            'docs': "Workflow with which to process incoming data objects."
        },
        'outWorkflow': {
            'docs': ("Workflow with which to process stored data objects when "
                     "requested.")
        },
        'irodsCollection': {
            'docs': "Top collection in irods"}
    }

    _possibleSettings = {
        'useUUID': {
            'docs': "Each stored data object should be assigned a UUID.",
            'type': int,
            'options': "0|1"
        },
        'digest': {
            'docs': "Type of digest/checksum to use. Defaults to no digest",
            'options': 'sha|md5'
        },
        'expires': {
            'docs': ("Time after ingestion at which to delete the data "
                     "object in number of seconds."),
            'type': int 
        },
        'storeDeletions': {
            'docs': "Maintain when an object was deleted from this store.",
            'type': int,
            'options': "0|1"
        },
        'irodsHost': {
            'docs': '',
            'type': str
        },
        'irodsPort': {
            'docs': '',
            'type': int
        },
        'irodsUser': {
            'docs': '',
            'type': str
        },
        'irodsZone': {
            'docs': '',
            'type': str
        },
        'irodsPassword': {
            'docs': '',
            'type': str
        },
        'irodsResource': {
            'docs': '',
            'type': str
        },
        'createSubDir': {
            'docs': '',
            'type': int,
            'options': "0|1"
        },
        'allowStoreSubDirs': {
            'docs': '',
            'type': int,
            'options': '0|1'
        }
    }

    def __init__(self, session, config, parent):
        BdbIndexStore.__init__(self, session, config, parent)
        if irods is None:
            raise MissingDependencyException(self.objectType,
                                             'irods (PyRods)'
                                             )
        self.switchingClass = IrodsSwitchingBdbConnection
        self.vectorSwitchingClass = IrodsSwitchingBdbConnection
        self.coll = None
        self.cxn = None
        self.env = None

        self.host = self.get_setting(session, 'irodsHost', '')
        self.port = self.get_setting(session, 'irodsPort', 0)
        self.user = self.get_setting(session, 'irodsUser', '')
        self.zone = self.get_setting(session, 'irodsZone', '')
        self.passwd = self.get_setting(session, 'irodsPassword', '')
        self.resource = self.get_setting(session, 'irodsResource', '')

        self.allowStoreSubDirs = self.get_setting(session,
                                                  'allowStoreSubDirs',
                                                  1)
        # And open iRODS
        self._open(session)

    def _open(self, session):

        if self.cxn is None:
            # connect to iRODS
            myEnv, status = irods.getRodsEnv()
            host = self.host if self.host else myEnv.getRodsHost()
            port = self.port if self.port else myEnv.getRodsPort()
            user = self.user if self.user else myEnv.getRodsUserName()
            zone = self.zone if self.zone else myEnv.getRodsZone()

            conn, errMsg = irods.rcConnect(host, port, user, zone) 
            if self.passwd:
                status = irods.clientLoginWithPassword(conn, self.passwd)
            else:
                status = irods.clientLogin(conn)

            if status:
                raise ConfigFileException("Cannot connect to iRODS: (%s) %s"
                                          "" % (status, errMsg.getMsg()))
            self.cxn = conn
            self.env = myEnv

            resources = irods.getResources(self.cxn)
            self.resourceHash = {}
            for r in resources:
                self.resourceHash[r.getName()] = r

        if self.coll is not None:
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

    def _close(self, session):
        irods.rcDisconnect(self.cxn)
        self.cxn = None
        self.coll = None
        self.env = None


class IrodsRecordStore(SimpleRecordStore, IrodsStore):
    # Hooray for multiple inheritance!

    def __init__(self, session, config, parent):
        IrodsStore.__init__(self, session, config, parent)
        SimpleRecordStore.__init__(self, session, config, parent)

    def __iter__(self):
        return irodsDataObjStoreIterator(self.session, self)


class IrodsDocumentStore(SimpleDocumentStore, IrodsStore):
    def __init__(self, session, config, parent):
        IrodsStore.__init__(self, session, config, parent)
        SimpleDocumentStore.__init__(self, session, config, parent)

    def __iter__(self):
        return irodsDataObjStoreIterator(self.session, self)


class IrodsObjectStore(SimpleObjectStore, IrodsStore):
    def __init__(self, session, config, parent):
        IrodsStore.__init__(self, session, config, parent)
        SimpleObjectStore.__init__(self, session, config, parent)

    def __iter__(self):
        return irodsObjectStoreIterator(self.session, self)


class IrodsResultSetStore(SimpleResultSetStore, IrodsStore):
    def __init__(self, session, config, parent):
        IrodsStore.__init__(self, session, config, parent)
        SimpleResultSetStore.__init__(self, session, config, parent)


# Iterator helper classes

def irodsCollectionIterator(coll):
    """Generator to yield ids and data from all files within a collection.

    Generator to yield ids and data from files in a collection and its 
    sub-collections.
    """
    for subcoll in coll.getSubCollections():
        coll.openCollection(subcoll)
        for filename, data in irodsCollectionIterator(coll):
            yield (subcoll + '/' + filename, data)
        coll.upCollection()

    for dataObj in coll.getObjects():
        # Cannot use with statement as IrodsFile objects do not have
        # an __exit__ method...yet
        fh = coll.open(dataObj[0], "r", dataObj[1])
        data = fh.read()
        fh.close()
        yield (dataObj[0], data)


def irodsStoreIterator(session, store):
    """Generator to yield data from an IrodsStore."""
    for id, data in irodsCollectionIterator(store.coll):
        # de-normalize id
        if store.outIdNormalizer is not None:
            id = store.outIdNormalizer.process_string(session, id)
        if not store.allowStoreSubDirs:
            id = id.replace('--', '/')
        # check for DeletedObject
        if (
            data and
            data.startswith("\0http://www.cheshire3.org/ns/status/DELETED:")
        ):
            data = DeletedObject(self, id, data[41:])
        # update expires
        if data and store.expires:
            expires = store.generate_expires(session)
            store.store_metadata(session, id, 'expires', expires)
        # check for data outWorkflow
        yield (id, data)


def irodsDataObjStoreIterator(session, store):
    """Generator to yield data objects (Records/Documents) from an IrodsStore.
    
    Generator to yield data objects, e.g. Records or Documents, from an
    IrodsStore.
    """
    for id, data in irodsStoreIterator(session, store):
        obj = store._process_data(session, id, data)
        yield obj


def irodsObjectStoreIterator(session, store):
    """Generator to yield Objects (e.g. Users) from an IrodsStore."""
    for id, data in irodsStoreIterator(session, store):
        rec = store._process_data(session, id, data)
        obj = store._processRecord(session, id, rec)
        yield obj
