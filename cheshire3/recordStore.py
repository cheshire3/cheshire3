import os
import string
import time

from cheshire3.configParser import C3Object
from cheshire3.baseObjects import RecordStore, Record, ResultSetItem, Session
from cheshire3.baseStore import SimpleStore, BdbStore, DeletedObject
from cheshire3.baseStore import DirectoryStore, directoryStoreIter
from cheshire3.record import SaxRecord
from cheshire3.exceptions import *
from cheshire3.document import StringDocument
from cheshire3.utils import nonTextToken


from cheshire3.bootstrap import BSLxmlParser
from cheshire3.baseStore import BdbIter

try:
    # Deal with Python 3.0 deprecation
    import cPickle as pickle
except:
    import pickle

try:
    # Name when installed by hand
    import bsddb3 as bdb
except:
    # Name that comes in python 2.3
    import bsddb as bdb

# Fastest to pickle elementHash, append to list, then join with nonTextToken


class SimpleRecordStore(RecordStore):
    inTransformer = None
    outParser = None

    _possiblePaths = {
        'inTransformer': {
            'docs': ("Identifier for transformer to use to transform incoming "
                     "record into document for storage")
        },
        'outParser': {
            'docs': ("Identifier for parser to use to transform outgoing data "
                     "into a record")
        },
        'inWorkflow': {
            'docs': ("Identifier for a transforming workflow to use to "
                     "transform incoming record in to document for storage")
        },
        'outWorkflow': {
            'docs': ("Identifier for a parsing workflow to use to transform "
                     "outgoing data into a record")
        }
    }

    def __init__(self, session, config, parent):
        if (not self.paths):
            RecordStore.__init__(self, session, config, parent)
        self.inTransformer = self.get_path(session, 'inTransformer', None)
        self.outParser = self.get_path(session, 'outParser', None)
        self.inWorkflow = self.get_path(session, 'inWorkflow', None)
        self.outWorkflow = self.get_path(session, 'outWorkflow', None)

    def create_record(self, session, rec=None):

        p = self.permissionHandlers.get('info:srw/operation/1/create', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to "
                                          "create an object in %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to create an "
                                          "object in %s" % self.id)
        id = self.generate_id(session)
        if (rec is None):
            # Create a placeholder
            rec = SaxRecord([], "", id)
        else:
            rec.id = id
        rec.recordStore = self.id

        try:
            self.store_record(session, rec)
        except ObjectAlreadyExistsException:
            # Back out id change
            if type(id) == long:
                self.currentId -= 1
            raise
        except:
            raise
        return rec

    def replace_record(self, session, rec):
        # Hook for permissions check
        p = self.permissionHandlers.get('info:srw/operation/1/replace', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to "
                                          "replace an object in %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to replace an "
                                          "object in %s" % self.id)
        self.store_record(session, rec)

    def store_record(self, session, rec, transformer=None):
        rec.recordStore = self.id
        # Maybe add metadata, etc.
        if transformer is not None:
            # Allow custom transformer
            doc = transformer.process_record(session, rec)
            data = doc.get_raw(session)
        elif self.inTransformer is not None:
            doc = self.inTransformer.process_record(session, rec)
            data = doc.get_raw(session)
        elif self.inWorkflow is not None:
            doc = self.inWorkflow.process(session, rec)
            data = doc.get_raw(session)
        else:
            data = rec.get_xml(session)

        dig = self.generate_checkSum(session, data)
        md = {'byteCount': rec.byteCount,
              'wordCount': rec.wordCount,
              'digest': dig}
        # check for expires
        e = self.generate_expires(session, rec)
        if e:
            md['expires'] = e
        # Object metadata will overwrite generated (intentionally)
        md2 = rec.metadata
        md.update(md2)
        # Might raise ObjectAlreadyExistsException
        self.store_data(session, rec.id, data, metadata=md)
        # Now accumulate metadata
        self.accumulate_metadata(session, rec)
        return rec

    def fetch_record(self, session, id, parser=None):
        p = self.permissionHandlers.get('info:srw/operation/2/retrieve', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to "
                                          "retrieve an object from "
                                          "%s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to retrieve an "
                                          "object from %s" % self.id)
        data = self.fetch_data(session, id)
        if (data):
            rec = self._process_data(session, id, data, parser)
            # fetch metadata
            for attr in ['byteCount', 'wordCount', 'digest']:
                try:
                    setattr(rec,
                            attr,
                            self.fetch_recordMetadata(session, id, attr))
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
                raise PermissionException("Authenticated user required to "
                                          "delete an object from %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to replace an "
                                          "object from %s" % self.id)

        # FIXME: API: This if sucks but not sure how to avoid for workflow
        if isinstance(id, Record) or isinstance(id, ResultSetItem):
            id = id.id
        self.delete_data(session, id)

    def fetch_recordMetadata(self, session, id, mType):
        if isinstance(id, Record):
            id = id.id
        return self.fetch_metadata(session, id, mType)

    def _process_data(self, session, id, data, parser=None):
        # Split from fetch record for Iterators

        doc = StringDocument(data)
        if (parser is not None):
            rec = parser.process_document(session, doc)
        elif (self.outParser is not None):
            rec = self.outParser.process_document(session, doc)
        elif (self.outWorkflow is not None):
            rec = self.outWorkflow.process(session, doc)
        else:
            # Assume raw XML into LXML
            # try and set self.parser to an LxmlParser
            try:
                p = session.server.get_object(session, 'LxmlParser')
                self.parser = p
                rec = p.process_document(session, doc)
            except:
                rec = BSLxmlParser.process_document(session, doc)

        # Ensure basic required info
        rec.id = id
        rec.recordStore = self.id
        return rec


class BdbRecordIter(BdbIter):
    # Get data from bdbIter and turn into record

    def next(self):
        d = BdbIter.next(self)
        rec = self.store._process_data(self.session, d[0], d[1])
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
        return BdbRecordIter(self.session, self)


try:
    from cheshire3.baseStore import PostgresStore
except:
    pass
else:
    class PostgresRecordStore(PostgresStore, SimpleRecordStore):
        def __init__(self, session, config, parent):
            PostgresStore.__init__(self, session, config, parent)
            SimpleRecordStore.__init__(self, session, config, parent)


class RedirectRecordStore(SimpleRecordStore, SimpleStore):
    # Store in unparsed format. Parse on load
    # cf buildassoc vs datastore in C2
    _possiblePaths = {
        'documentStore': {
            'docs': "documentStore identifier where the data is held"
        }
    }

    documentStore = None

    def __iter__(self):
        # Return an iterator object that calls self.workflow
        return ParsingIter(self)

    def __init__(self, session, config, parent):
        SimpleRecordStore.__init__(self, session, config, parent)
        self.documentStore = self.get_path(session, 'documentStore')

    def create_record(self, session, rec):
        # maybe just copy some stuff around...
        rec.recordStore = self.id
        if rec.parent and rec.parent[2]:
            rec.id = rec.parent[2]
            if rec.id == -1:
                raise ValueError
            return rec
        else:
            return SimpleRecordStore.create_record(self, session, rec)

    def store_data(self, session, id, data, metadata={}):
        # write this to documentStore as document
        return self.documentStore.store_data(session, id, data, metadata)

    def fetch_data(self, session, id):
        # read from documentStore
        return self.documentStore.fetch_data(session, id)

    def begin_storing(self, session):
        return self.documentStore.begin_storing(session)

    def commit_storing(self, session):
        return self.documentStore.commit_storing(session)

    def fetch_recordMetadata(self, session, id, mType):
        return self.documentStore.fetch_documentMetadata(session, id, mType)


# Pass back info for PVM/MPI/SOAP/etc
class RemoteWriteRecordStore(BdbRecordStore):
    """ Listen for records and write """

    def store_data(self, session, id, data, metadata={}):
        # Return Id to other task
        # Almost don't need this function/class
        if id is None:
            id = self.generate_id(session)
        try:
            BdbRecordStore.store_data(self, session, id, data, metadata)
            return id
        except ObjectAlreadyExistsException:
            return -1


class RemoteSlaveRecordStore(BdbRecordStore):
    recordStore = ""
    writeTask = None
    taskType = None
    protocol = ""

    _possiblePaths = {
        'remoteStore': {
            'docs': "Remote store to send data to."
        }
    }

    _possibleSettings = {
        'protocol': {
            'docs': "Protocol to use for sending data. Currently MPI or PVM"
        }
    }

    def __init__(self, session, config, parent):
        SimpleRecordStore.__init__(self, session, config, parent)
        self.writeTask = None
        self.recordStore = self.get_path(session, 'remoteStore')
        if not self.recordStore:
            raise ConfigFileException('Missing recordStore identifier')

    def begin_storing(self, session):
        # set tasks
        self.writeTask = session.processManager.namedTasks['writeTask']
        return None

    def create_record(self, session, rec=None):
        if (rec is None):
            rec = SaxRecord([], "", None)
        else:
            rec.id = None
        self.store_record(session, rec)
        return rec

    def store_record(self, session, rec, transformer=None):
        rec.recordStore = self.recordStore.id
        # Maybe add metadata, etc.
        if transformer is not None:
            # Allow custom transformer
            doc = transformer.process_record(session, rec)
            data = doc.get_raw(session)
        elif self.inTransformer is not None:
            doc = self.inTransformer.process_record(session, rec)
            data = doc.get_raw(session)
        elif self.inWorkflow is not None:
            doc = self.inWorkflow.process(session, rec)
            data = doc.get_raw(session)
        else:
            sax = [x.encode('utf8') for x in rec.get_sax(session)]
            sax.append("9 " + pickle.dumps(rec.elementHash))
            data = nonTextToken.join(sax)
        dig = self.generate_checkSum(session, data)
        md = {'byteCount': rec.byteCount,
              'wordCount': rec.wordCount,
              'digest': dig}
        if (self.writeTask is not None):
            self.writeTask.call(self.recordStore,
                                'store_data',
                                session,
                                rec.id,
                                data,
                                md)
            msg = self.writeTask.recv()
        else:
            raise ValueError('WriteTask is None... '
                             'did you call begin_storing?')
        if rec.id is None:
            rec.id = msg.data
        return rec

    def fetch_record(self, session, id, parser=None):
        raise NotImplementedError


class DirectoryRecordStore(DirectoryStore, SimpleRecordStore):
    def __init__(self, session, config, parent):
        DirectoryStore.__init__(self, session, config, parent)
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
        return directoryRecordStoreIter(self)


def directoryRecordStoreIter(store):
    session = Session()
    for id_, data in directoryStoreIter(store):
        yield store._process_data(session, id_, data)
