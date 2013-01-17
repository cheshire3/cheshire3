import os
import md5
import sha
import time
import string
import types
import base64
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from random import Random
from tarfile import *
    
try:
    from Ft.Lib.Uuid import GenerateUuid, UuidAsString
except:
    use4Suite = 0
else:
    use4Suite = 1

# Cheshire3 imports
from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Database, Session
from cheshire3.baseStore import BdbStore
from cheshire3.exceptions import *


randomGen = Random(time.time())
asciiChars = string.ascii_letters + string.digits + "@%#!-=."


try:
    from srboo import SrbConnection, SrbException
        
    from utils import parseSrbUrl
except:
    pass
else:

    class SrbStore(C3Object):
        """ Storage Resource Broker based storage """

        host = ""
        port = ""
        user = ""
        passwd = ""
        dn = ""
        domain = ""
        resource = ""
        subcollection = ""

        connection = None
        checkSumHash = {}
        currentId = -1

        def __init__(self, session, config, parent):
            C3Object.__init__(self, session, config, parent)
            self.idNormaliser = self.get_path(session, 'idNormaliser')
            self.checkSumHash = {}
            self.currentId = -1
            # Now find our info
            uri = self.get_path(session, 'srbServer')
            uri = uri.encode('utf-8')
            uri = uri.strip()
            if not uri:
                raise ConfigFileException("No srbServer to connect to.")
            else:
                info = parseSrbUrl(uri)
                for (a, v) in self.info.items():
                    setattr(self, a, v)

                if (isinstance(parent, Database)):
                    sc = parent.id + "/" + self.id
                else:
                    sc = self.id
                self.subcollection = info['path'] + "/cheshire3/" + sc

                try:
                    self.connection = SrbConnection(self.host, self.port,
                                                    self.domain,
                                                    user=self.user,
                                                    passwd=self.passwd
                                                    )
                    self.connection.resource = self.resource
                except SrbException:
                    # Couldn't connect :/
                    self.connection = None
                    raise
                xsc = self.subcollection + "/d2i"
                scs = xsc.split('/')
                orig = self.connection.collection
                for c in scs:
                    try:
                        self.connection.create_collection(c)
                    except SrbException, e:
                        # Err, at some point it should fail
                        # trying to create an existing collection...
                        pass
                    self.connection.open_collection(c)
                self.connection.open_collection(orig)
                self.connection.open_collection(self.subcollection)

        def _openContainer(self, session):
            if self.connection is None:
                try:                    
                    self.connection = SrbConnection(self.host,
                                                    self.port,
                                                    self.domain,
                                                    user=self.user,
                                                    passwd=self.passwd,
                                                    dn=self.dn
                                                    )
                    self.connection.resource = self.resource
                except SrbException:
                    # Couldn't connect :/
                    raise
                self.connection.open_collection(self.subcollection)

        def _closeContainer(self, session):
            if self.connection is not None:
                self.connection.disconnect()
                self.connection = None

        def begin_storing(self, session):
            self._openContainer(session)

        def commit_storing(self, session):
            self._closeContainer(session)

        def generate_id(self, session):
            # XXX Will fail for large collections.

            if self.currentId == -1:
                self._openContainer(session)
                n = self.connection.n_objects()
                if (n == 0):
                    self.currentId = 0
                else:
                    name = self.connection.object_metadata(n - 1)
                    if (name.isdigit()):
                        self.currentId = int(name) + 1
                    else:
                        raise ValueError("XXX: Can't generate new ids for non "
                                         "int stores")
            else:
                self.currentId = self.currentId + 1
            return self.currentId

        def store_data(self, session, id, data, size=0):        
            self._openContainer(session)
            id = str(id)
            if (self.idNormaliser <> None):
                id = self.idNormaliser.process_string(session, id)
            try:
                f = self.connection.create(id)
            except SrbException:
                f = self.connection.open(id, 'w')
            f.write(data)

            if (0):
                if (size):
                    f.set_umetadata('size', str(size))
                if (self.checkSumHash.has_key(id)):
                    f.set_umetadata('digest', self.checkSumHash[id])
            f.close()

            return None
        
        def fetch_data(self, session, id):
            self._openContainer(session)
            sid = str(id)
            if (self.idNormaliser <> None):
                sid = self.idNormaliser.process_string(session, sid)
            f = self.connection.open(sid)
            data = f.read()
            f.close()
            return data

        def delete_item(self, session, id):
            self._openContainer(session)
            sid = str(id)
            if (self.idNormaliser <> None):
                sid = self.idNormaliser.process_string(session, sid)
            f = self.connection.open(sid)
            digest = f.get_umetadata().get('digest', '')
            f.delete()
            f.close()

            if digest:
                self.connection.open_collection('d2i')
                f = self.connection.open(digest)
                f.delete()
                f.close()
                self.connection.up_collection()

        def fetch_idList(self, session, numReq=-1, start=""):
            self._openContainer(session)
            (scs, objs) = self.connection.walk_names()
            return objs

        def verify_checkSum(self, session, id, data, store=1):
            digest = self.get_setting(session, "digest")
            if (digest):
                if (digest == 'md5'):
                    dmod = md5
                elif (digest == 'sha'):
                    dmod = sha
                else:
                    raise ConfigFileException("Unknown digest type: %s"
                                              "" % digest)
                m = dmod.new()
                data = data.encode('utf-8')
                m.update(data)               
                self._openContainer(session)
                digest = m.hexdigest()

                if self.connection.objects > 0:
                    self.connection.open_collection('d2i')
                    try:
                        f = self.connection.open(digest)
                        data = f.read()
                        f.close()
                        raise ObjectAlreadyExistsException(data)
                    except:
                        pass
                    self.connection.up_collection()

                if store:
                    self.store_checkSum(session, id, digest)
                return digest
                
        def fetch_checkSum(self, session, id):
            self._openContainer(session)
            sid = str(id)
            if (self.idNormaliser <> None):
                sid = self.idNormaliser.process_string(session, sid)
            f = self.connection.open(sid)
            data = f.get_umetadata('digest')
            f.close()
            return data

        def fetch_size(self, session, id):
            self._open_container(session)
            sid = str(id)
            if (self.idNormaliser <> None):
                sid = self.idNormaliser.process_string(session, sid)
            f = self.connection.open(sid)
            data = f.get_umetadata('size')
            f.close()
            return int(data)

        def store_checkSum(self, session, id, digest):
            sid = str(id)
            if (self.idNormaliser <> None):
                sid = self.idNormaliser.process_string(session, sid)
            self.checkSumHash[sid] = digest
            self.connection.open_collection('d2i')
            try:
                f = self.connection.create(digest)
                f.write(sid)
                f.close()
            except:
                pass
            self.connection.up_collection()

        def clean(self, session):
            # Remove all files from Srb
            self._openContainer(session)
            self.connection.rmrf()
            self._closeContainer(session)


    class SrbBdbCombineStore(SrbStore, BdbStore):
        """ Combined BerkeleyDB in SRB based Storage """

        # Combine up to X records into one file
        # Store metadata locally in bdb
        maxRecords = 100
        incomingRecords = []
        cachedFilename = ""
        cachedTarfile = ""

        def __init__(self, session, config, parent):
            BdbStore.__init__(self, session, config, parent)
            SrbStore.__init__(self, session, config, parent)
            self.maxRecords = int(self.get_setting(session, "recordsPerFile"))
            self.digestForId = self.get_setting(session, "digestForId")
            self.useBase64 = self.get_setting(session, "base64")
            self.incomingRecords = []

        def _verifyDatabases(self, session):
            BdbStore._verifyDatabases(self, session)

        def begin_storing(self, session):
            BdbStore._openContainer(self, session)
            SrbStore._openContainer(self, session)

        def commit_storing(self, session):
            self._writeCache(session)
            BdbStore._closeContainer(self, session)
            SrbStore._closeContainer(self, session)

        def generate_id(self, session):
            return BdbStore.generate_id(self, session)

        def verify_checkSum(self, session, id, data, store=1):
            return BdbStore.verify_checkSum(self, session, id, data, store)
            
        def fetch_checkSum(self, session, id):
            return BdbStore.fetch_checkSum(self, session, id)
        
        def fetch_size(self, session, id):
            return BdbStore.fetch_size(self, session, id)
        
        def store_checkSum(self, session, id, digest):
            return BdbStore.store_checkSum(self, session, id, digest)

        def delete_item(self, session, id):
            SrbStore.delete_item(self, session, id)
            BdbStore.delete_item(self, session, id)

        def fetch_idList(self, session, numReq=-1, start=""):
            return BdbStore.fetch_idList(self, session, numReq, start)

        def clean(self, session):
            SrbStore.clean(self, session)
            # XXX: And truncate local metadata store?
            # BdbStore.clean(self, session)

        def fetch_data(self, session, id):
            # Extract from chunk
            # Cache most recent chunk as likely to be pulled back in order
            SrbStore._openContainer(self, session)
            sid = str(id)                        
            startid = id / self.maxRecords * self.maxRecords
            startsid = str(startid)
            end = startid + self.maxRecords - 1
            endsid = str(end)
            if (self.idNormaliser <> None):
                sid = self.idNormaliser.process_string(session, sid)
                endsid = self.idNormaliser.process_string(session, endsid)
                startsid = self.idNormaliser.process_string(session, startsid)
            filename = "%s-%s.tar" % (startsid, endsid)

            if (self.cachedFilename != filename):
                f = self.connection.open(filename)
                data = f.read()
                f.close()
                if self.useBase64:
                    data = base64.b64decode(data)
                self.cachedTarfile = data
                self.cachedFilename = filename
            else:
                data = self.cachedTarfile
                
            # Extract from tar
            buffer = StringIO.StringIO(data)
            tar = TarFile.open(mode="r|", fileobj=buffer)
            # This is very odd, but appears to be necessary
            f = None
            for ti in tar:
                if ti.name == sid:
                    f = tar.extractfile(ti)
                    break
            if f is not None:
                recdata = f.read()
                f.close()
            else:
                # Can't find record in tar file?!
                raise ValueError("Can't find record?")
            tar.close()
            buffer.close()
            return recdata

        def store_data(self, session, id, data, size=0):        
            # Cache until X items then push
            if (
                    len(self.incomingRecords) == 1 and
                    id != self.incomingRecords[-1][0] + 1
            ):
                # Write single
                self._writeSingle(session, self.incomingRecords[0])
                self.incomingRecords = [(id, data)]
            elif len(self.incomingRecords) < self.maxRecords:
                self.incomingRecords.append((id, data))
                # XXX Store size/digest?
            else:
                # Write cache as TarFile
                self._writeCache(session)
                self.incomingRecords = [(id, data)]

        def _writeCache(self, session):
            # Called from commit and store_data
            if (len(self.incomingRecords) == 1):
                return self._writeSingle(session, self.incomingRecords)

            tarbuffer = StringIO.StringIO("")
            tar = TarFile.open(mode="w|", fileobj=tarbuffer)
            for (id, data) in self.incomingRecords:
                sid = str(id)
                if (self.idNormaliser is not None):
                    sid = self.idNormaliser.process_string(session, sid)
                ti = TarInfo(sid)
                if isinstance(data, types.UnicodeType):
                    data = data.encode('utf-8')
                ti.size = len(data)
                buff = StringIO.StringIO(data)
                buff.seek(0)
                tar.addfile(ti, buff)
                buff.close()
            tar.close()

            tarbuffer.seek(0)
            data = tarbuffer.read()
            tarbuffer.close()

            if self.useBase64:
                data = base64.b64encode(data)

            # Now store tar in SRB
            startsid = str(self.incomingRecords[0][0])
            endsid = str(self.incomingRecords[0][0] + self.maxRecords - 1)

            if (self.idNormaliser is not None):
                startsid = self.idNormaliser.process_string(session, startsid)
                endsid = self.idNormaliser.process_string(session, endsid)

            name = "%s-%s.tar" % (startsid, endsid)
            self.incomingRecords = []

            SrbStore._openContainer(self, session)
            try:
                f = self.connection.create(name)
            except SrbException:
                f = self.connection.open(id, 'w')
            f.write(data)
            f.close()

        def _writeSingle(self, session, info):
            # Writing record into a tar file
            # May or may not exist already, but assume it does

            (id, recdata) = info
            sid = str(id)            
            startsid = str(id / 100 * 100)
            end = id + self.maxRecords
            endsid = str(end)
            if (self.idNormaliser <> None):
                sid = self.idNormaliser.process_string(session, sid)
                endsid = self.idNormaliser.process_string(session, endsid)
                startsid = self.idNormaliser.process_string(session, startsid)
            filename = "%s-%s.tar" % (startsid, endsid)

            SrbStore._openContainer(self, session)
            try:
                f = self.connection.open(filename, 'w')
            except SrbException:
                f = self.connection.create(filename)
            data = f.read()
            f.seek(0)

            # Put file into tar

            tarbuffer = StringIO.StringIO(data)
            tar = TarFile.open(mode="w|", fileobj=tarbuffer)
            ti = TarInfo(sid)
            buff = StringIO.StringIO(recdata)
            ti.frombuf(buff)
            ti.size = len(recdata)
            buff.seek(0)
            tar.addfile(ti, buff)
            buff.close()
            tar.close()
            tarbuffer.seek(0)
            newdata = tarbuffer.read()
            tarbuffer.close()

            # XXX Will this work for inserting smaller records?
            # Or will we end up with junk at end of file?
            f.write(newdata)
            f.close()


    class SrbDocumentStore(SrbStore, SimpleDocumentStore):
        def __init__(self, session, node, parent):
            SrbStore.__init__(self, session, node, parent)
            SimpleDocumentStore.__init__(self, session, node, parent)

    class CachingSrbDocumentStore(SrbBdbCombineStore, SimpleDocumentStore):
        def __init__(self, session, node, parent):
            SrbBdbCombineStore.__init__(self, session, node, parent)
            SimpleDocumentStore.__init__(self, session, node, parent)


    class SrbRecordStore(SimpleRecordStore, SrbStore):

        def __init__(self, session, config, parent):
            SrbStore.__init__(self, session, config, parent)
            SimpleRecordStore.__init__(self, session, config, parent)


    class CachingSrbRecordStore(SimpleRecordStore, SrbBdbCombineStore):
        # Storing/fetching lots of small records is expensive
        # Probably more expensive than finding records in a larger chunk
        
        def __init__(self, session, config, parent):
            SrbBdbCombineStore.__init__(self, session, config, parent)
            SimpleRecordStore.__init__(self, session, config, parent)


    class CachingSrbRemoteWriteRecordStore(SimpleRecordStore,
                                           SrbBdbCombineStore):
        # Storing/fetching lots of small records is expensive
        # Probably more expensive than finding records in a larger chunk

        def __init__(self, session, config, parent):
            SrbBdbCombineStore.__init__(self, session, config, parent)
            SimpleRecordStore.__init__(self, session, config, parent)
            
        def store_data_remote(self, session, data, size):
            # Return Id to other task
            id = self.generate_id(session)
            self.store_data(session, id, data, size)
            return id
