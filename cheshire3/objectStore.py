"""Implementations for configured object stores."""

from cheshire3.baseObjects import ObjectStore
from cheshire3.configParser import C3Object
from cheshire3.recordStore import BdbRecordStore
from cheshire3.utils import getFirstData, elementType
from cheshire3.exceptions import ConfigFileException
from cheshire3 import dynamic
from cheshire3.baseStore import BdbIter


class SimpleObjectStore(ObjectStore):

    def get_storageTypes(self, session):
        # Assume that we want to store wordCount, byteCount
        types = ['database']
        if self.get_setting(session, 'digest'):
            types.append('digest')
        if self.get_setting(session, 'expires'):
            types.append('expires')
        return types

    # NB Use create_record() to store configurations
    def create_object(self, session, obj=None):
        # Need to implement object -> config xml for all objects!
        # Check doesn't exist, then call store_object
        raise NotImplementedError

    def delete_object(self, session, id):
        return self.delete_record(session, id)

    def fetch_object(self, session, id):
        rec = self.fetch_record(session, id)
        if rec:
            object = self._processRecord(session, id, rec)
            return object
        else:
            return None

    def store_object(self, session, obj):
        raise NotImplementedError

    def _processRecord(self, session, id, rec):
        # Split from fetch_object for Iterators
        dom = rec.get_dom(session)

        if (hasattr(dom, 'childNodes')):
            for d in dom.childNodes:
                if d.nodeType == elementType:
                    topNode = d
                    break
        else:
            # LXML
            topNode = dom

        object = dynamic.makeObjectFromDom(session, topNode, self)
        return object


class BdbObjectIter(BdbIter):
    """Facilitate iterating through a BerkeleyDB based ObjectStore.

    Get data from bdbIter and turn into record, then process record into
    object.
    """

    def next(self):
        d = BdbIter.next(self)
        rec = self.store._process_data(self.session, d[0], d[1])
        obj = self.store._processRecord(self.session, d[0], rec)
        return obj


class BdbObjectStore(BdbRecordStore, SimpleObjectStore):
    """BerkeleyDB based implementation of an ObjectStore.

    Store XML records in RecordStore, retrieve and instantiate when requested.
    """

    def __iter__(self):
        return BdbObjectIter(self.session, self)
