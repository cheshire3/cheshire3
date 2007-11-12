
from configParser import C3Object
from baseObjects import RecordStore, Record
from baseStore import SimpleStore, BdbStore, DeletedObject
from record import SaxRecord
from c3errors import *
from document import StringDocument
import time, cPickle
from utils import nonTextToken

import string, os

try:
    # name when installed by hand
    import bsddb3 as bdb
except:
    # name that comes in python 2.3
    import bsddb as bdb

# Fastest to pickle elementHash, append to list, then join with nonTextToken


class SimpleRecordStore(RecordStore):
    inTransformer = None
    outParser = None

    _possiblePaths = {'inTransformer' : {'docs' : "Identifier for transformer to use to transform incoming record into document for storage"}
                      , 'outParser'  : {'docs' : "Identifier for parser to use to transform outgoing data into a record"}
                      }

    def __init__(self, session, config, parent):
        if (not self.paths):
            RecordStore.__init__(self, session, config, parent)
        self.inTransformer = self.get_path(session, 'inTransformer', None)
        self.outParser = self.get_path(session, 'outParser', None)

    def create_record(self, session, record=None):

        p = self.permissionHandlers.get('info:srw/operation/1/create', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to create an object in %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to create an object in %s" % self.id)

        id = self.generate_id(session)
        if (record == None):
            # Create a placeholder
            record = SaxRecord([], "", id)
        else:
            record.id = id
        record.recordStore = self.id

        try:
            self.store_record(session, record)
        except ObjectAlreadyExistsException:
            # Back out id change
            if type(id) == long:
                self.currentId -= 1
            raise
        except:
            raise
        return record

    def replace_record(self, session, record):
        # Hook for permissions check
        p = self.permissionHandlers.get('info:srw/operation/1/replace', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to replace an object in %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to replace an object in %s" % self.id)
        self.store_record(session, record)

    def store_record(self, session, record, transformer=None):
        record.recordStore = self.id        

        # Maybe add metadata, etc.
        if transformer != None:
            # Allow custom transformer
            doc = transformer.process_record(session, record)
            data = doc.get_raw()            
        elif self.inTransformer != None:
            doc = self.inTransformer.process_record(session, record)
            data = doc.get_raw()
        elif self.inWorkflow != None:
            doc = self.inWorkflow.process(session, record)
            data = doc.get_raw()
        else:
            sax = [x.encode('utf8') for x in record.get_sax()]
            sax.append("9 " + cPickle.dumps(record.elementHash))
            data = nonTextToken.join(sax)       

        dig = self.generate_checkSum(session, data)
        md = {'byteCount' : record.byteCount,
              'wordCount' : record.wordCount,
              'digest' : dig}
        # Might raise ObjectAlreadyExistsException
        self.store_data(session, record.id, data, metadata=md)
        # Now accumulate metadata
        self.accumulate_metadata(session, record)

	return record

    def fetch_record(self, session, id, parser=None):
        p = self.permissionHandlers.get('info:srw/operation/2/retrieve', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to retrieve an object from %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to retrieve an object from %s" % self.id)
      
        data = self.fetch_data(session, id)
        if (data):
            rec = self.process_data(session, id, data, parser)
            # fetch metadata
            for attr in ['byteCount', 'wordCount', 'digest']:
                try:
                    setattr(rec, attr, self.fetch_recordMetadata(session, id, attr))
                except:
                    continue
            return rec
        elif (isinstance(data, DeletedObject)):
            raise ObjectDeletedException(data)
        else:
            raise ObjectDoesNotExistException(id)
        

    def delete_record(self, session, id):
        p = self.permissionHandlers.get('info:srw/operation/1/delete', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to delete an object from %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to replace an object from %s" % self.id)

        # FIXME: API: This if sucks but not sure how to avoid for workflow
        if isinstance(id, Record):
            id = id.id
        self.delete_data(session, id)

    def fetch_recordMetadata(self, session, id, mtype):
        return self.fetch_metadata(session, id, mtype)

    def process_data(self, session, id, data, parser=None):
        # Split from fetch record for Iterators
        if (parser != None):
            doc = StringDocument(data)
            record = parser.process_document(session, doc)
        elif (self.outParser != None):
            doc = StringDocument(data)
            record = self.outParser.process_document(session, doc)
        elif (self.outWorkflow != None):
            doc = StringDocument(data)
            record = self.outWorkflow.process(session, doc)
        else:
            # Assume raw sax events
            data = unicode(data, 'utf-8')
            sax = data.split(nonTextToken)
            if sax[-1][0] == "9":
                line = sax.pop()
                elemHash = cPickle.loads(str(line[2:]))
            else:
                elemHash = {}
            record = SaxRecord(sax)
            record.elementHash = elemHash
        # Ensure basic required info
        record.id = id
        record.recordStore = self.id
        return record


from baseStore import BdbIter
class BdbRecordIter(BdbIter):
    # Get data from bdbIter and turn into record

    def next(self):
        d = BdbIter.next(self)
        rec = self.store.process_data(None, d[0], d[1])
        return rec

class BdbRecordStore(BdbStore, SimpleRecordStore):
    def __init__(self, session, config, parent):
        BdbStore.__init__(self, session, config, parent)
        SimpleRecordStore.__init__(self, session, config, parent)

    def get_storageTypes(self, session):
        types = ['database', 'wordCount', 'byteCount']
        if self.get_setting(session, 'digest'):
                types.append('digest')
        if self.get_setting(session, 'expires'):
            types.append('expires')
        return types

    def __iter__(self):
        # return an iter object
        return BdbRecordIter(self)

try:
    from baseStore import PostgresStore
    class PostgresRecordStore(PostgresStore, SimpleRecordStore):
        def __init__(self, session, config, parent):
            PostgresStore.__init__(self, session, config, parent)
            SimpleRecordStore.__init__(self, session, config, parent)
except:
    pass



class ParsingIter(object):
    recordStore = None
    documentStore = None
    workflow = None
    docStoreIter = None
    
    def __init__(self, recStore):
        self.recordStore = recStore
        self.workflow = recStore.workflow
        self.parser = recStore.parser
        self.docStoreIter = recStore.documentStore.__iter__()
    
    def next(self):
        d = self.docStoreIter.next()
        doc = StringDocument(d[1])
        if self.workflow:
            rec = self.workflow.process(self.docStoreIter.session, doc)
        elif self.parser:
            rec = self.parser.process_document(self.docStoreIter.session, doc)
        rec.recordStore = self.recordStore.id
        rec.id = d[0]
        return rec


class ParsingRecordStore(SimpleRecordStore, SimpleStore):
    # Store in unparsed format. Parse on load
    # cf buildassoc vs datastore in C2
    
    documentStore = None
    workflow = None
    parser = None

    _possiblePaths = {'documentStore' : {'docs' : "documentStore identifier where the data is held"}}

    def __iter__(self):
        # Return an iterator object that calls self.workflow
        return ParsingIter(self)

    def __init__(self, session, config, parent):
        SimpleRecordStore.__init__(self, session, config, parent)
        self.documentStore = self.get_path(session, 'documentStore')
        self.workflow = self.get_path(session, 'outWorkflow', None)
        self.parser = self.get_path(session, 'outParser', None)


    def create_record(self, session, record):
        # just copy some stuff around...
        record.recordStore = self.id
        record.id = record.parent[2]
        if record.id == -1:
            raise ValueError
        return record

    def fetch_record(self, session, id):
        # Fetch record from docStore, preparse, parse, return
        doc = self.documentStore.fetch_document(session, id)
        if self.workflow:
            rec = self.workflow.process(session, doc)
        elif self.parser:
            rec = self.parser.process_document(session, doc)
        else:
            raise ConfigFileException("%s does not have an outWorkflow or outParser." % self.id)
        rec.recordStore = self.id
        rec.id = id
        return rec

    def store_record(self, session, record):
        raise NotImplementedError

    def begin_storing(self, session):
        # Should we error?
        return None

    def commit_storing(self, session):
        return None



from record import MarcRecord

class MarcIter(BdbIter):
    recordStore = None
    documentStore = None
    workflow = None
    
    def __init__(self, recStore):
        self.recordStore = recStore
        self.workflow = recStore.workflow
        BdbIter.__init__(self, recStore.documentStore)
    
    def next(self):
        d = BdbIter.next(self)
        # d[0] is id
        # d[1] is raw data
        rec = MarcRecord(StringDocument(d[1]))
        rec.recordStore = self.recordStore.id
        rec.id = d[0]
        return rec

class MarcRecordStore(ParsingRecordStore):
    documentStore = None

    def __iter__(self):
        # Return an iterator object that calls self.workflow
        return MarcIter(self)
    
    def fetch_record(self, session, id):
        doc = self.documentStore.fetch_document(session, id)
        try:
            rec = MarcRecord(doc)
        except:
            rec = SaxRecord([])
        rec.recordStore = self.id
        rec.id = id
        return rec

    def fetch_recordMetadata(self, session, id, mtype):
        return self.documentStore.fetch_documentMetadata(session, id, mtype)


# Task API for PVM/MPI/SOAP/etc
class RemoteWriteRecordStore(BdbRecordStore):
    """ Listen for records and write """

    def store_data_remote(self, session, data, metadata={}):
        # Return Id to other task
        id = self.generate_id(session)
        try:
            self.store_data(session, id, data, metadata={})
            return id
        except ObjectAlreadyExistsException:
            return -1


class RemoteSlaveRecordStore(SimpleRecordStore):
        recordStore = ""
        writeTask = None
        taskType = None
        protocol = ""

        _possiblePaths = {'remoteStore' : {'docs' : "Identifier for remote store to send data to."}}
        _possibleSettings = {'protocol' : {'docs' : "Protocol to use for sending data. Currently MPI or PVM"}}

        def __init__(self, session, config, parent):
            SimpleRecordStore.__init__(self, session, config, parent)
            self.writeTask = None
            self.recordStore = self.get_path(session, 'remoteStore')
            if not self.recordStore:
                raise ConfigFileException('Missing recordStore identifier')
            self.protocol = self.get_setting(session, 'protocol')
            if self.protocol == 'PVM':
                from pvmProtocolHandler import Task
                self.taskType = Task
            elif self.protocol == 'MPI':
                from mpiProtocolHandler import Task
                self.taskType = Task
            else:
                raise ConfigFileException('Unknown or missing protocol: %s' % self.protocol)
            
        def begin_storing(self, session, wt=None):
            # set tasks
            if wt:
                self.writeTask = self.taskType(wt)
            return None

        def create_record(self, session, record=None):
            # Is this actually useful?
            if (record == None):
                record = SaxRecord([], "", "__new")
            else:
                record.id = "__new"
            self.store_record(session, record)
            return record

        def store_record(self, session, record):
            # str()ify
            if (self.inTransformer != None):
                doc = self.inTransformer.process_record(session, record)
                data = doc.get_raw()
            else:
                sax = record.get_sax()
                sax.append("9 " + cPickle.dumps(record.elementHash))
                data = nonTextToken.join(sax)       

            # Now send to task
            size = record.size

            md = {'wordCount' : record.wordCount,
                  'byteCount' : record.byteCount}

            if (self.writeTask != None):            
                self.writeTask.send([self.recordStore, 'store_data_remote', [session, data, md], {}], 1)
                msg = self.writeTask.recv()
            else:
                raise ValueError('WriteTask is None... did you call begin_storing?')
            record.recordStore = self.recordStore
            record.id = msg.data
            return record

        def fetch_record(self, session, record):
            raise NotImplementedError


