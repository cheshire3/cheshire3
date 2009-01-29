
from cheshire3.baseStore import SimpleStore

import irods

# Store metadata on irodsCollection object as userMetadata
# eg:

                
# fileStore style:  one object in irods per object sent to store
# object metadata on object
# reverse metadata per object ... in bdb?

class BaseIrodsStore(SimpleStore):

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
                      'outWorkflow' : {'docs' : "Workflow with which to process stored data objects when requested."}
                      }

    _possibleSettings = {'useUUID' : {'docs' : "Each stored data object should be assigned a UUID.", 'type': int, 'options' : "0|1"},
                         'digest' : {'docs' : "Type of digest/checksum to use. Defaults to no digest", 'options': 'sha|md5'},
                         'expires' : {'docs' : "Time after ingestion at which to delete the data object in number of seconds.", 'type' : int },
                         'storeDeletions' : {'docs' : "Maintain when an object was deleted from this store.", 'type' : int, 'options' : "0|1"}
                         }

    _possibleDefaults = {'expires': {"docs" : 'Default time after ingestion at which to delete the data object in number of seconds.  Can be overridden by the individual object.', 'type' : int}}
    


    def __init__(self, session, config, parent):
        C3Object.__init__(self, session, config, parent)
        self.cxn = None
        self.coll = None
        self._open(session)

        self.idNormalizer = self.get_path(session, 'idNormalizer', None)
        self.outIdNormalizer = self.get_path(session, 'outIdNormalizer', None)
        self.inWorkflow = self.get_path(session, 'inWorkflow', None)
        self.outWorkflow = self.get_path(session, 'outWorkflow', None)
        self.session = session

        # need to put these in a special directory
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
        # XXX Find location from config
        path = 'cheshire3'

        # connect to iRODS
        myEnv, status = irods.getRodsEnv()
        conn, errMsg = irods.rcConnect(myEnv.getRodsHost(), myEnv.getRodsPort(), 
                                       myEnv.getRodsUserName(), myEnv.getRodsZone())
        status = irods.clientLogin(conn)
        if status:
            raise ConfigFileException("Cannot connect to iRODS: (%s) %s" % (status, errMsg))

        c = irods.irodsCollection(conn, myEnv.getRodsHome())
        self.cxn = conn
        self.coll = c

        dirs = c.getSubCollections()
        if not path in dirs:
            c.createCollection(path)
        c.openCollection(path)

        # now look for object's storage area
        if (isinstance(self.parent, Database)):
            sc = parent.id
            dirs = c.getSubCollections()
            if not sc in dirs:
                c.createCollection(sc)
            c.openCollection(sc)

        dirs = c.getSubCollections()
        if not self.id in dirs:
            c.createCollection(self.id)
        c.openCollection(self.id)

        # Fetch user metadata
        myMetadata = self.get_metadataTypes(session)
        umd = c.getUserMetadata()
        umdHash = {}
        for u in umd:
            umdHash[u[0]] = u[1:]            
        for md in myMetadata:
            setattr(self, md, myMetadata[md](umdHash[md][0]))

        if self.totalItems != 0:
            self.meanWordCount = self.totalWordCount / self.totalItems
            self.meanByteCount = self.totalByteCount / self.totalItems
        else:
            self.meanWordCount = 1
            self.meanByteCount = 1

        # XXX now open reverse metadata stuff?

        
    def _close(self, session):
        # XXX close reverse metadata stuff
        irods.rcDisconnect(self.cxn)
        self.cxn = None
        self.coll = None

    def commit_metadata(self, session):
        # self.coll.addUserMetadata(type, value, units)
        mymd = self.get_metadataTypes(session)
        # need to delete values first
        umd = self.coll.getUserMetadata()
        umdHash = {}
        for u in umd:
            umdHash[u[0]] = u[1:]                    
        for md in mymd:
            self.coll.rmUserMetadata(md, umdHash[md][0])
            self.coll.addUserMetadata(md, str(getattr(self, md)))

    def begin_storing(self, session):
        if not this.cxn:
            self._open(session)
        return None

    def commit_storing(self, session):
        self.commit_metadata(session)
        self._close()
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

        self.coll.delete(id)

        for dbt in self.storageTypes:
            # XXX still don't know
            break
            cxn = self._open(session, dbt)
            if cxn != None:
                if dbt in self.reverseMetadataTypes:
                    # fetch value here, delete reverse
                    data = cxn.get(id)
                    cxn2 = self._open(session, dbt + "Reverse")                
                    if cxn2 != None:
                        cxn2.delete(data)
                cxn.delete(id)
                cxn.sync()

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            now = datetime.datetime.now(dateutil.tz.tzutc()).strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')            
            data = "\0http://www.cheshire3.org/status/DELETED:%s" % now
            f = self.coll.create(id)
            f.write(data)
            f.close()
        return None

    def fetch_data(self, session, id):
        # return data stored against id
        if (self.idNormalizer != None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        f = self.coll.open(id)        
        data = f.read()
        f.close()

        if data and data[:41] == "\0http://www.cheshire3.org/status/DELETED:":
            data = DeletedObject(self, id, data[41:])

        if data and self.expires:
            expires = self.generate_expires(session)
            f.addUserMetadata('expires', expires)
            # XXX is this actually useful?
        return data

    def store_data(self, session, id, data, metadata):
        dig = metadata.get('digest', "")
        if dig:
            # cxn = self._open(session, 'digestReverse')
            # XXX where to store?
            raise
            if cxn:
                exists = cxn.get(dig)
                if exists:
                    raise ObjectAlreadyExistsException(exists)

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
        f = self.coll.create(id)
        f.write(data)
        f.close()

        # store metadata with object
        for (m, val) in metadata.iteritems():
            f.addUserMetadata(m, val)
        return None

    def fetch_metadata(self, session, id, mType):
        # open irodsFile and get metadata from it
        f = self.coll.open(id)
        umd = f.getUserMetadata()
        for x in umd:
            if x[0] == mType:
                return x[1]
        
    def store_metadata(self, session, id, mType, value):
        # store value for mType metadata against id
        f = self.coll.open(id)
        f.addUserMetadata(mType, value)
        f.close()
    
    def clean(self, session):
        # delete expired data objects
        raise NotImplementedError

    def clear(self, session):
        # this would delete all the data out of self
        for o in self.coll.getObjects():
            self.coll.delete(o)
        return None
            
    def flush(self, session):
        # ensure all data is flushed to disk
        # don't think there's an equivalent
        return None
