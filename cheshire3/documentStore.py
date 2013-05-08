
from cheshire3.baseObjects import DocumentStore, Session
from cheshire3.exceptions import *
from cheshire3.document import StringDocument
from cheshire3.baseStore import BdbStore, BdbIter, FileSystemStore
from cheshire3.baseStore import DeletedObject
from cheshire3.baseStore import DirectoryStore, directoryStoreIter
try:
    # Name when installed by hand
    import bsddb3 as bdb
except:
    # Name that comes in Python 2.3, though Python >= 2.6 required
    import bsddb as bdb


class SimpleDocumentStore(DocumentStore):
    inPreParser = None
    outPreParser = None
    inWorkflow = None
    outWorkflow = None

    _possiblePaths = {
        'inPreParser': {
            'docs': ("Identifier for a preParser through which to pass the "
                     "documents being ingested."
        )},
        'outPreParser': {
            'docs': ("Identifier for a preParser through which to pass the "
                     "documents being requested")
        }
    }

    def __init__(self, session, config, parent):
        if (not self.paths):
            DocumentStore.__init__(self, session, config, parent)
        self.inPreParser = self.get_path(session, 'inPreParser', None)
        self.outPreParser = self.get_path(session, 'outPreParser', None)
        self.inWorkflow = self.get_path(session, 'inWorkflow', None)
        self.outWorkflow = self.get_path(session, 'outWorkflow', None)

    def create_document(self, session, doc=None):
        p = self.permissionHandlers.get('info:srw/operation/1/create', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to create an object in "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to create an object in %s" % self.id
                raise PermissionException(msg)
        id = self.generate_id(session)
        if (doc is None):
            # Create a placeholder
            doc = StringDocument("")
        else:
            doc.id = id
        doc.documentStore = self.id
        try:
            self.store_document(session, doc)
        except ObjectAlreadyExistsException:
            # Back out id change
            if type(id) == long:
                self.currentId -= 1
            raise
        except:
            raise
        return doc

    def store_document(self, session, doc):
        doc.documentStore = self.id
        if (self.inPreParser is not None):
            doc = self.inPreParser.process_document(session, doc)
        elif self.inWorkflow is not None:
            doc = self.inWorkflow.process(session, doc)
        data = doc.get_raw(session)
        md = doc.metadata
        if doc.wordCount:
            md['wordCount'] = doc.wordCount
        if doc.byteCount:
            md['byteCount'] = doc.byteCount
        if self.expires or doc.expires:
            md['expires'] = self.generate_expires(session, doc)
        if doc.byteOffset:
            md['byteOffset'] = doc.byteOffset
        if doc.filename:
            md['filename'] = doc.filename
        self.store_data(session, doc.id, data, md)

    def fetch_document(self, session, id):
        p = self.permissionHandlers.get('info:srw/operation/2/retrieve', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to retrieve an object "
                       "from %s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = ("Permission required to retrieve an object from "
                       "%s" % self.id)
                raise PermissionException(msg)
        data = self.fetch_data(session, id)
        if (data):
            doc = StringDocument(data)
            if (self.outPreParser is not None):
                doc = self.outPreParser.process_document(session, doc)
            elif (self.outWorkflow is not None):
                doc = self.outWorkflow.process(session, doc)
            doc.id = id
            doc.documentStore = self.id
            doc.parent = ('document', self.id, id)
            return doc
        elif (isinstance(data, DeletedObject)):
            raise ObjectDeletedException(data)
        else:
            raise ObjectDoesNotExistException(id)

    def delete_document(self, session, id):
        p = self.permissionHandlers.get('info:srw/operation/1/delete', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to delete an object from "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = ("Permission required to replace an object from "
                       "%s" % self.id)
                raise PermissionException(msg)

        if isinstance(id, StringDocument):
            id = id.id
        self.delete_data(session, id)

    def _process_data(self, session, id, data, preParser=None):
        # Split from fetch record for Iterators
        if (preParser is not None):
            doc = StringDocument(data)
            doc = preParser.process_document(session, doc)
        elif (self.outPreParser is not None):
            doc = StringDocument(data)
            doc = self.outPreParser.process_document(session, doc)
        elif (self.outWorkflow is not None):
            doc = StringDocument(data)
            doc = self.outWorkflow.process(session, doc)
        else:
            doc = StringDocument(data)
        # Ensure basic required info
        doc.id = id
        doc.documentStore = self.id
        return doc


class BdbDocIter(BdbIter):
    def next(self):
        d = BdbIter.next(self)
        doc = StringDocument(d[1])
        doc.id = d[0]
        return doc


class BdbDocumentStore(BdbStore, SimpleDocumentStore):
    # Instantiate some type of simple doc store
    def __init__(self, session, config, parent):
        BdbStore.__init__(self, session, config, parent)
        SimpleDocumentStore.__init__(self, session, config, parent)

    def __iter__(self):
        return BdbDocIter(self.session, self)


class FileSystemDocumentStore(FileSystemStore, SimpleDocumentStore):
    def __init__(self, session, config, parent):
        FileSystemStore.__init__(self, session, config, parent)
        SimpleDocumentStore.__init__(self, session, config, parent)

    def get_storageTypes(self, session):
        types = ['filename', 'byteCount', 'byteOffset']
        if self.get_setting(session, 'digest'):
                types.append('digest')
        if self.get_setting(session, 'expires'):
            types.append('expires')
        return types


class DirectoryDocumentStore(DirectoryStore, SimpleDocumentStore):
    # Instantiate some type of simple doc store
    def __init__(self, session, config, parent):
        DirectoryStore.__init__(self, session, config, parent)
        SimpleDocumentStore.__init__(self, session, config, parent)

    def __iter__(self):
        return directoryDocumentStoreIter(self)

    def fetch_document(self, session, id_):
        # Fetch the document
        doc = SimpleDocumentStore.fetch_document(self, session, id_)
        # Assign the filename attribute
        internalId = self._normalizeIdentifier(session, id_)
        doc.filename = self._getFilePath(session, internalId)
        return doc


def directoryDocumentStoreIter(store):
    session = Session()
    for id_, data in directoryStoreIter(store):
        doc = StringDocument(data)
        doc.id = id_
        internalId = store._normalizeIdentifier(session, id_)
        doc.filename = store._getFilePath(session, internalId)
        yield doc
