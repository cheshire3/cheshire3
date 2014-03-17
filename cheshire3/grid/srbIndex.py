import os
import time
import commands
try:
    # Python 2.3 vs 2.2
    import bsddb as bdb
except ImportError:
    import bsddb3 as bdb

from cheshire3.baseObjects import Database
from cheshire3.exceptions import ConfigFileException, PermissionException
from cheshire3.indexStore import BdbIndexStore

try:
    from srboo import *
    from utils import parseSrbUrl
except:
    pass
else:
    
    # Split index files into chunks based on first two letters,
    # one for each number, one for non letter/non number.
    # Then construct across the grid per initial chr
    # Then store index chunks in SRB
    # SRB layout:
    # $HOME/cheshire3/databaseName/indexStoreName/indexName/chunk.index

    # To search, pull down appropriate chunk on demand if necessary
    # write to disk then search it.
    # This relies on SRB null chr fix of 2005/11/01

    class SrbBdbIndexStore(BdbIndexStore):

        host = ""
        port = ""
        user = ""
        passwd = ""
        dn = ""
        domain = ""
        resource = ""
        subcollection = ""

        connection = None
        tempChunks = 0

        def _connect(self):
            try:
                self.connection = SrbConnection(self.host, self.port,
                                                self.domain, user=self.user,
                                                passwd=self.passwd, dn=self.dn
                                                )
                self.connection.resource = self.resource
            except SrbException:
                # Couldn't connect :/
                raise
            scs = self.subcollection.split('/')
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

        def __init__(self, session, config, parent):
            BdbIndexStore.__init__(self, session, config, parent)
            self.tempChunks = self.get_setting(session, 'tempChunks')
            uri = self.get_path(session, 'srbServer')
            uri = uri.encode('utf-8')
            uri = uri.strip()
            if not uri:
                raise ConfigFileException("No srbServer to connect to.")
            else:
                info = parseSrbUrl(uri)
                for (a, v) in info.items():
                    setattr(self, a, v)

                if (isinstance(parent, Database)):
                    sc = parent.id + "/" + self.id
                else:
                    sc = self.id
                self.subcollection = "cheshire3/" + sc
                self.connection = None
                self._connect()

        def _openIndexChunk(self, session, index, chunk): 
            dfp = self.get_path(session, 'defaultPath')
            dbname = os.path.join(dfp, index.id, "%s.index" % chunk)
            cxn = bdb.db.DB()
            if session.environment == "apache":
                cxn.open(dbname, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(dbname)
            return cxn

        def _createIndexChunk(self, session, index, chunk):
            dfp = self.get_path(session, 'defaultPath')
            dbname = os.path.join(dfp, index.id, "%s.index" % chunk)
            cxn = bdb.db.DB()
            cxn.open(dbname, dbtype=bdb.db.DB_BTREE,
                     flags=bdb.db.DB_CREATE, mode=0660)
            return cxn
        
        def _storeIndexChunk(self, session, index, chunk):
            start = time.time()
            dfp = self.get_path(session, 'defaultPath')
            fname = "%s.index" % chunk
            dbname = os.path.join(dfp, index.id, fname)
            # read file, store in srb
            try:
                self.connection.open_collection(index.id)
            except:
                self.connection = None
                while not self.connection:
                    self._connect()
                self.connection.open_collection(index.id)
            inh = file(dbname)
            outh = self.connection.create(fname)
            data = inh.read(102400)
            while data:
                outh.write(data)
                data = inh.read(102400)
            inh.close()
            outh.close()
            self.connection.up_collection()
       
        def _whichChunk(self, term):
            # buckets based on first chrs
            if not term:
                return "other"
            elif term[0].isalnum():
                return term[0].lower()
            elif term[0] > 'z':
                return "other2"
            else:
                return "other"

            # -------------------------
            # Split on first two 
            #
            if not term:
                return "other"
            elif term[0].isdigit():
                return term[0]
            elif term[0].isalpha():
                if len(term) == 1:
                    return term + "0"
                elif not term[1].isalnum():
                    # recursively strip non alnum chars
                    return self._whichChunk(term[0] + term[2:])
                else:
                    return term[:2].lower()
            else:
                return "other"
            #
            # --------------------------

        def _maybeFetchChunk(self, session, index, term):
            # Check if we exist, otherwise fetch
            fn = self._whichChunk(term)
            fname = "%s.index" % fn
            dfp = self.get_path(session, "defaultPath")
            path = os.path.join(dfp, index.id, fname)
            if not os.path.exists(path):
                okay = self._fetchChunk(session, index, fn)
                if not okay:
                    return None
            return fn

        def _fetchChunk(self, session, index, chunk):
            try:
                self.connection.open_collection(index.id)
            except:
                self.connection = None
                while not self.connection:
                    self._connect()
                self.connection.open_collection(index.id)
            dfp = self.get_path(session, "defaultPath")
            fname = "%s.index" % chunk
            path = os.path.join(dfp, index.id, fname)
            if not fname in self.connection.walk_names()[1]:
                self.connection.up_collection()
                return 0
            try:
                inh = self.connection.open(fname)
            except:
                # Can't open :(
                self.connection.up_collection()
                return 0
            outh = file(path, 'w')
            data = inh.read(10240)
            while data:
                outh.write(data)
                data = inh.read(10240)
            inh.close()
            outh.close()
            self.connection.up_collection()
            return 1

        def begin_indexing(self, session, index):
            if not self.tempChunks:
                return BdbIndexStore.begin_indexing(self, session, index)
            temp = self.get_path(session, 'tempPath')
            if not os.path.isabs(temp):
                temp = os.path.join(self.get_path(session, 'defaultPath'),
                                    temp)
            self.tempPath = temp
            if (not os.path.exists(temp)):
                try:
                    os.mkdir(temp)
                except:
                    raise(ConfigFileException('TempPath does not exist and is '
                                              'not creatable.'))
            elif (not os.path.isdir(temp)):
                raise(ConfigFileException('TempPath is not a directory.'))

            # Make temp files on demand, in hash
            self.outFiles[index] = {}

        def commit_indexing(self, session, index):
            if self.tempChunks:
                temp = self.tempPath
                keys = self.outFiles[index].keys()
                for f in self.outFiles[index].values():
                    f.flush()
                    f.close()
                del self.outFiles[index]
                sort = self.get_path(session, 'sortPath')
                if hasattr(session, 'task'):
                    task = session.task
                else:
                    task = None
                if hasattr(session, 'phase'):
                    load = 0
                else:
                    load = 1

                sfiles = []
                for k in keys:
                    if task:
                        fn = '_'.join([self.id, index.id, k, task])
                    else:
                        fn = '_'.join([self.id, index.id, k])
                    tf = os.path.join(temp, fn + "_TEMP")
                    sf = os.path.join(temp, fn + "_SORT")
                    cmd = "%s -f %s -o %s" % (sort, tf, sf)
                    f = commands.getoutput(cmd)
                    os.remove(tf)
                    if load:
                        self.commit_indexing2(session, index, sf)
                    else:
                        sfiles.append(sf)
                return sfiles               
            else:
                BdbIndexStore.commit_indexing(self, session, index)

        def commit_indexing2(self, session, index, sorted):
            # Look on session for chunk to process
            # otherwise process all

            f = file(sorted)

            # load all chunks from this file
            termid = long(0)
            done = 0
            prevTerm = None
            cxn = None
            currChunk = None
            currFirst = None
            l = f.readline()

            t2s = index.serialise_terms
            whichChunk = self._whichChunk
            storeChunk = self._storeIndexChunk
            createChunk = self._createIndexChunk
            while(l):
                data = l.split(nonTextToken)
                term = data[0]
                if not done and term[:2] != currFirst:
                    which = whichChunk(term)
                    if currChunk != which:
                        if cxn:
                            cxn.close()
                            err = storeChunk(session, index, currChunk)
                        cxn = createChunk(session, index, which)
                        currChunk = which
                        currFirst = term[:2]
                        if prevTerm is None:
                            prevTerm = term
                fullinfo = map(long, data[1:])
                occs = acc(term, fullinfo)
                if occs and occs[0] != []:
                    termid += 1
                    packed = t2s(termid, occs)
                    cxn.put(prevTerm, packed)
                    prevTerm = data[0]
                l = f.readline()
                l = l[:-1]
                if not done and not l:
                    l = " "
                    done = 1
            f.close()
            os.remove(sorted)
            cxn.close()
            storeChunk(session, index, currChunk)

        def create_index(self, session, index):
            p = self.permissionHandlers.get('info:srw/operation/1/create',
                                            None)
            if p:
                if not session.user:
                    raise PermissionException("Authenticated user required to "
                                              "create index in %s" % self.id)
                okay = p.hasPermission(session, session.user)
                if not okay:
                    raise PermissionException("Permission required to create "
                                              "index in %s" % self.id)
            # Create local temp space
            dfp = self.get_path(session, "defaultPath")
            dirname = os.path.join(dfp, index.id)
            if not os.path.exists(dirname):
                os.mkdir(dirname)
            # Don't create any bdb files
            if (index.get_setting(session, "sortStore")):
                raise NotImplementedError("sortStore")
            if (index.get_setting(session, "reverseIndex")):
                raise NotImplementedError("reverseIndex")

            # Create permanent SRB space
            try:
                dirs = self.connection.walk_names()[0]
            except:
                self.connection = None
                while not self.connection:
                    self._connect()
                dirs = self.connection.walk_names()[0]
            if not index.id in dirs:
                self.connection.create_collection(index.id)

        def clean_index(self, session, index):
            # XXX Delete all SRB files
            raise NotImplementedError()

        def delete_index(self, session, index):
            self.clean_index(session, index)

        def fetch_sortValue(self, session, index, item):
            raise NotImplementedError("sortStore")

        def delete_terms(self, session, index, terms, record):
            raise NotImplementedError()

        def store_terms(self, session, index, hash, record):
            if self.tempChunks:
                if not hash:
                    return
                
                # Make sure you know what you're doing
                storeid = record.recordStore
                if not isinstance(storeid, types.IntType):
                    storeid = self.storeHashReverse[storeid]
                docid = long(record.id)

                for k in hash.values():
                    try:
                        text = k['text'].encode('utf-8')
                    except:
                        print text
                        text = ""
                    if not text:
                        continue
                    lineList = [text,
                                str(docid),
                                str(storeid),
                                str(k['occurences'])
                                ]
                    try:
                        lineList.append(nonTextToken.join(map(str,
                                                              k['positions'])
                                                          )
                                        )
                    except KeyError:
                        # non prox
                        pass
                    if not text or not text[0].isalnum():
                        tf = "other"
                    else:
                        tf = text[0].lower()
                    
                    try:
                        outh = self.outFiles[index][tf]
                    except:
                        if session.task:
                            fname = '_'.join([self.id,
                                              index.id,
                                              tf,
                                              session.task,
                                              'TEMP']
                                             )
                        else:
                            fname = '_'.join([self.id, index.id, tf, 'TEMP'])
                        fname = os.path.join(self.tempPath, fname)
                        outh = file(fname, 'w')
                        self.outFiles[index][tf] = outh
                    outh.write(nonTextToken.join(lineList) + "\n")
                return
            if self.outFiles.has_key(index):
                BdbIndexStore.store_terms(self, session, index, hash, record)
            else:
                raise NotImplementedError()

        def fetch_termList(self, session, index, term, numReq=0, relation="",
                           end="", summary=0, reverse=0):
            if reverse:
                raise NotImplementedError("reverseIndex")
            if (not (numReq or relation or end)):
                # XXX Default from config
                numReq = 20
            if (not relation and not end):
                relation = ">="
            if (not relation):
                if (term > end):
                    relation = "<="
                else:
                    relation = ">"            

            # Only return to end of current index?

            chunk = self._maybeFetchChunk(session, index, term)
            if chunk is None:
                # no data
                return []
            cxn = self._openIndexChunk(session, index, chunk)

            if summary:
                dataLen = index.longStructSize * self.reservedLongs

            c = cxn.cursor()
            term = term.encode('utf-8')
            try:
                if summary:
                    (key, data) = c.set_range(term, dlen=dataLen, doff=0)
                else:
                    (key, data) = c.set_range(term)
            except Exception, e:
                if summary:
                    (key, data) = c.last(dlen=dataLen, doff=0)
                else:
                    (key, data) = c.last()
                if (relation in [">", ">="] and term > key):
                    # Asked for > than maximum key
                    cxn.close()
                    return []

            tlist = []
            fetching = 1

            if (not (key == term and relation in ['>', '<'])):
                # We want this one
                unpacked = index.deserialise_terms(data)
                tlist.append([key, unpacked])
                if numReq == 1:
                    fetching = 0
            while fetching:
                dir = relation[0]
                if (dir == ">"):
                    if summary:
                        tup = c.next(dlen=dataLen, doff=0)
                    else:
                        tup = c.next()
                else:
                    if summary:
                        tup = c.prev(dlen=dataLen, doff=0)
                    else:
                        tup = c.prev()
                if tup:
                    (key, rec) = tup
                    if (end and dir == '>' and key >= end):
                        fetching = 0
                    elif (end and dir == "<" and key <= end):
                        fetching = 0
                    else:
                        unpacked = index.deserialise_terms(rec)
                        if reverse:
                            key = key[::-1]
                        tlist.append([key, unpacked])
                        if (numReq and len(tlist) == numReq):
                            fetching = 0
                else:
                    key = None
                    fetching = 0
            cxn.close()
            return tlist            

        def fetch_term(self, session, index, term):
            val = self.fetch_packed(session, index, term)
            if val is not None:
                return index.deserialise_terms(val)
            else:
                return []

        def fetch_packed(self, session, index, term):
            try:
                term = term.encode('utf-8')
            except:
                pass
            chunk = self._maybeFetchChunk(session, index, term)
            if chunk is None:
                return None
            cxn = self._openIndexChunk(session, index, chunk)
            val = cxn.get(term)
            return val
