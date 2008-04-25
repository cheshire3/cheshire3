  
from baseObjects import IndexStore, Database
from configParser import C3Object
from c3errors import ConfigFileException, FileDoesNotExistException, FileAlreadyExistsException
from resultSet import SimpleResultSetItem
from index import *
import os, types, struct, sys, commands, time, glob
try:
    # Python 2.3 vs 2.2
    import bsddb as bdb
except:
    import bsddb3 as bdb

import random

nonTextToken = "\x00\t"    
NumTypes = [types.IntType, types.LongType]

class IndexStoreIter(object):
    # step through our indexes!

    def __init__(self, session, indexStore):
        self.session = session
        self.indexStore = indexStore
        dfp = indexStore.get_path(session, "defaultPath")
        files = os.listdir(dfp)
        # self.files = filter(self._fileFilter, files)
        self.files = [f for f in files if self._fileFilter(f)]
        self.position = 0

    
    def _fileFilter(self, x):
        if x[-6:] != ".index":
            return 0
        elif x[:len(self.indexStore.id)] != self.indexStore.id:
            return 0
        else:
            return 1

    def next(self):
        try:
            start = len(self.indexStore.id)+2
            idxid = self.files[self.position][start:-6]
            self.position += 1
            # now fetch the index
            return self.indexStore.get_object(self.session, idxid)
        except IndexError:
            raise StopIteration()

    def jump(self, position):
        self.position = position
        return self.next()


class BdbIndexStore(IndexStore):

    indexing = 0
    outFiles = {}
    outSortFiles = {}
    storeHash = {}
    storeHashReverse = {}
    sortStoreCxn = {}
    identifierMapCxn = {}
    indexCxn = {}
    vectorCxn = {}
    proxVectorCxn = {}
    termIdCxn = {}
    reservedLongs = 3

    _possiblePaths = {'recordStoreHash' : {'docs' : "Space separated list of recordStore identifiers kept in this indexStore (eg map from position in list to integer)"}
                      , 'tempPath' : {'docs' : "Path in which temporary files are kept during batch mode indexing"}
                      , 'sortPath' : {'docs' : "Path to the 'sort' utility used for sorting temporary files"}
                      }

    _possibleSettings = {'maxVectorCacheSize' : {'docs' : "Number of terms to cache when building vectors", 'type' :int}}

    def __init__(self, session, config, parent):
        IndexStore.__init__(self, session, config, parent)
        self.outFiles = {}
        self.storeHash = {}
        self.outSortFiles = {}
        self.metadataCxn = None
        self.sortStoreCxn = {}
        self.identifierMapCxn = {}
        self.indexCxn = {}
        self.vectorCxn = {}
        self.proxVectorCxn = {}
        self.termIdCxn = {}
        self.termFreqCxn = {}
        self.reservedLongs = 3
        self.session = session

        rsh = self.get_path(session, 'recordStoreHash')
        if rsh:
            wds = rsh.split()
            for (w, wd) in enumerate(wds):
                self.storeHash[w] = wd
                self.storeHashReverse[wd] = w

        # Record Hash (in bdb) 
        fnbase = "recordIdentifiers_" + self.id + "_"
        fnlen = len(fnbase)
        dfp = self.get_path(session, "defaultPath")
        try:
            files = os.listdir(dfp)
        except OSError:
            try:
                os.mkdir(dfp, 0755)
                files = os.listdir(dfp)
            except:
                raise ConfigFileException("Cannot create default path for %s: %s" % (self.id, dfp))
        for f in files:
            if (f[:fnlen] == fnbase):
                recstore = f[fnlen:-4]
                dbp = os.path.join(dfp, f)
                cxn = bdb.db.DB()
                #cxn.set_flags(bdb.db.DB_RECNUM)
                if session.environment == "apache":
                    cxn.open(dbp, flags=bdb.db.DB_NOMMAP)
                else:
                    cxn.open(dbp)
                self.identifierMapCxn[recstore] = cxn

    def __iter__(self):
        return IndexStoreIter(self.session, self)

    def _openMetadata(self, session):
        if self.metadataCxn != None:
            return self.metadataCxn
        else:
            mp = self.get_path(session, 'metadataPath')
            if not mp:
                dfp = self.get_path(session, 'defaultPath')
                mp = os.path.join(dfp, 'metadata.bdb')

            if not os.path.exists(mp):
                oxn = bdb.db.DB()
                oxn.open(mp, dbtype=bdb.db.DB_BTREE, flags=bdb.db.DB_CREATE, mode=0660)
                oxn.close()

            cxn = bdb.db.DB()
            if session.environment == "apache":
                cxn.open(mp, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(mp)
            self.metadataCxn = cxn
            return cxn

    def _closeMetadata(self, session):
        if self.metadataCxn != None:
            self.metadataCxn.close()
            self.metadataCxn = None

    def _closeIndex(self, session, index):
        if self.indexCxn.has_key(index):
            self.indexCxn[index].close()
            del self.indexCxn[index]

    def _openIndex(self, session, index):
        if self.indexCxn.has_key(index):
            return self.indexCxn[index]
        else:
            dfp = self.get_path(session, 'defaultPath')
            basename = self._generateFilename(index)
            dbname = os.path.join(dfp, basename)
            cxn = bdb.db.DB()
            #cxn.set_flags(bdb.db.DB_RECNUM)
            if session.environment == "apache":
                cxn.open(dbname, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(dbname)
            self.indexCxn[index] = cxn
            return cxn


    def _generateFilename(self, index):
        stuff = [self.id, "--", index.id, ".index"]
        return ''.join(stuff)
    
    
    def _listExistingFiles(self, session, index):
        dfp = self.get_path(session, "defaultPath")
        name = self._generateFilename(index)
        return glob.glob(os.path.join(dfp, name + '*'))


    def _get_internalId(self, session, rec):
        if self.identifierMapCxn.has_key(rec.recordStore):
            cxn = self.identifierMapCxn[rec.recordStore]
        else:
            fn = "recordIdentifiers_" + self.id + "_" + rec.recordStore + ".bdb"
            dfp = self.get_path(session, "defaultPath")
            dbp = os.path.join(dfp, fn)
            if not os.path.exists(dbp):
                # Create
                cxn = bdb.db.DB()
                #cxn.set_flags(bdb.db.DB_RECNUM)
                cxn.open(dbp, dbtype=bdb.db.DB_BTREE, flags = bdb.db.DB_CREATE, mode=0660)
                cxn.close()
            # Open
            cxn = bdb.db.DB()
            #cxn.set_flags(bdb.db.DB_RECNUM)
            if session.environment == "apache":
                cxn.open(dbp, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(dbp)
            self.identifierMapCxn[rec.recordStore] = cxn    
        # Now we have cxn, check it rec exists
	recid = rec.id
	if type(recid) == unicode:
	    try:
		recid = rec.id.encode('utf-8')
	    except:
		recid = rec.id.encode('utf-16')
	try:
            data = cxn.get(recid)
            if data:
                return long(data)
        except:
            pass
        # Doesn't exist, write
        c = cxn.cursor()
        c.set_range("__i2s_999999999999999")
        data = c.prev()
        if (data and data[0][:6] == "__i2s_"):
            max = long(data[0][6:])
            intid = "%015d" % (max + 1)
        else:
            intid = "000000000000000"
        cxn.put(recid, intid)
        cxn.put("__i2s_%s" % intid, recid)
        return long(intid)
    
    def _get_externalId(self, session, recordStore, identifier):
        if self.identifierMapCxn.has_key(recordStore):
            cxn = self.identifierMapCxn[recordStore]
        else:
            fn = "recordIdentifiers_" + self.id + "_" + recordStore + ".bdb"
            dfp = self.get_path(session, "defaultPath")
            dbp = os.path.join(dfp, fn)
            if not os.path.exists(dbp):
                raise FileDoesNotExistException(dbp)
            cxn = bdb.db.DB()
            #cxn.set_flags(bdb.db.DB_RECNUM)
            if session.environment == "apache":
                cxn.open(dbp, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(dbp)
            self.identifierMapCxn[recordStore] = cxn
        identifier = "%015d" % identifier        
        data = cxn.get("__i2s_%s" % identifier)
        if (data):
            return data
        else:
            raise FileDoesNotExistException("%s/%s" % (recordStore, identifier))
            

    # Not API, but called for grid file xfer
    def fetch_temp_file(self, session, idxid):

        index = self.get_object(session, idxid)
        temp = self.get_path(session, 'tempPath')
        if not os.path.isabs(temp):
            temp = os.path.join(self.get_path(session, 'defaultPath'), temp)
        basename = os.path.join(temp, self._generateFilename(index))
        if (hasattr(session, 'task')):
            basename += str(session.task)
            
        tempfile = basename + "_SORT"
        fh = file(tempfile)
        data = fh.read()
        fh.close()
        return data


    def fetch_summary(self, session, index):
        # Fetch summary data for all terms in index
        # eg for sorting, then iterating
        # USE WITH CAUTION
        # Everything done here for speed

        cxn = self._openIndex(session, index)
        cursor = cxn.cursor()
        dataLen = index.longStructSize * self.reservedLongs
        terms = []

        (term, val) = cursor.first(doff=0, dlen=dataLen)
        while (val):
            (termid, recs, occs) = struct.unpack('lll', val)
            terms.append({'t': term, 'i' : termid, 'r' : recs, 'o' : occs})
            try:
                (term, val) = cursor.next(doff=0, dlen=dataLen)
            except:
                val = 0

        self._closeIndex(session, index)
        return terms
        

    def begin_indexing(self, session, index):

        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add to indexStore %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to indexStore %s" % self.id)
        temp = self.get_path(session, 'tempPath')
        if not os.path.isabs(temp):
            temp = os.path.join(self.get_path(session, 'defaultPath'), temp)
        if (not os.path.exists(temp)):
            try:
                os.mkdir(temp)
            except:
                raise(ConfigFileException('TempPath does not exist and is not creatable.'))
        elif (not os.path.isdir(temp)):
            raise(ConfigFileException('TempPath is not a directory.'))
        basename = os.path.join(temp, self._generateFilename(index))
        if (hasattr(session, 'task')):
            basename += str(session.task)
            
        # In case we're called twice
        if (not self.outFiles.has_key(index)):
            self.outFiles[index] = codecs.open(basename + "_TEMP", 'a', 'utf-8', 'xmlcharrefreplace')

            if (index.get_setting(session, "sortStore")):
                # Store in db for faster sorting
                if (session.task):
                    # Need to tempify
                    raise NotImplementedError
                dfp = self.get_path(session, "defaultPath")
                name = self._generateFilename(index) + "_VALUES"
                fullname = os.path.join(dfp, name)
                if (not os.path.exists(fullname)):
                    raise FileDoesNotExistException(fullname)
                cxn = bdb.db.DB()
                #cxn.set_flags(bdb.db.DB_RECNUM)
                if session.environment == "apache":
                    cxn.open(fullname, flags=bdb.db.DB_NOMMAP)
                else:
                    cxn.open(fullname)
                self.outSortFiles[index] = cxn


    def get_indexingPosition(self, session):
        # Useful if the indexing breaks for some reason and want to restart
        temp = self.get_path(session, 'tempPath')
        if not os.path.isabs(temp):
            temp = os.path.join(self.get_path(session, 'defaultPath'), temp)
        files = os.listdir(temp)
        recids = []
        for f in files:
            # Open, find last line, find recid
            fh = file(os.path.join(temp, f))
            fh.seek(-1024, 2)
            data = fh.read(1024)
            lines = data.split('\n')
            l= lines[-2]
            bits = l.split('\x00\t')
            recids.append(long(bits[1]))
        currRec =  max(recids)
        # Note that this is the representation regardless of the actual record id
        # eg string ids are mapped before this point
        # Then:  myIter = recStore.__iter__()
        #        myIter.jump(currRec)
        # to restart at this position. Remember to call begin_indexing() again
        return "%012d" % currRec


    def commit_indexing(self, session, index):
        # Need to do this per index so one store can be doing multiple things at once
        # Should only be called if begin_indexing() has been
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add to indexStore %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to indexStore %s" % self.id)

        temp = self.get_path(session, 'tempPath')
        dfp = self.get_path(session, 'defaultPath')
        if not os.path.isabs(temp):
            temp = os.path.join(dfp, temp)

        for k in self.outSortFiles:
            self.outSortFiles[k].close()
        if (not self.outFiles.has_key(index)):
            raise FileDoesNotExistException(index.id)
        sort = self.get_path(session, 'sortPath')
	if (not os.path.exists(sort)):
	    raise ConfigFileException("Sort executable for %s does not exist" % self.id)
	
        fh = self.outFiles[index]
        fh.flush()
        fh.close()
        del self.outFiles[index]

        for db in self.identifierMapCxn.values():
            db.sync()
        
        basename = self._generateFilename(index)
        if (hasattr(session, 'task')):
            basename += str(session.task)
       
        basename = os.path.join(temp, basename)
        tempfile = basename + "_TEMP"
        sorted = basename + "_SORT"
	cmd = "%s %s -T %s -o %s" % (sort, tempfile, temp, sorted)
	commands.getoutput(cmd)
	# Sorting might fail.
        if (not os.path.exists(sorted)):
            raise ValueError("Failed to sort %s" % tempfile)
        if not index.get_setting(session, 'vectors'):
            os.remove(tempfile)
	if hasattr(session, 'phase') and session.phase == 'commit_indexing1':
            return sorted

        # Original terms from data
        return self.commit_centralIndexing(session, index, sorted)

    def merge_tempFiles(self, session, index):

        sort = self.get_path(session, 'sortPath')
        temp = self.get_path(session, 'tempPath')
        dfp = self.get_path(session, 'defaultPath')
        if not os.path.isabs(temp):
            temp = os.path.join(dfp, temp)
	if (not os.path.exists(sort)):
	    raise ConfigFileException("Sort executable for %s does not exist" % self.id)
        basename = self._generateFilename(index)
        baseGlob = os.path.join(temp, "%sTask*SORT" % basename)
        sortFileList = glob.glob(baseGlob)
        sortFiles = " ".join(sortFileList)
        sorted = os.path.join(temp, "%s_SORT" % basename)
	cmd = "%s -m -T %s -o %s %s" % (sort, temp, sorted, sortFiles)
	out = commands.getoutput(cmd)
        if not os.path.exists(sorted):
            raise ValueError("Didn't sort %s" % index.id)
        for tsfn in sortFileList:
            os.remove(tsfn)
        return sorted

    def commit_centralIndexing(self, session, index, filePath):
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add to indexStore %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to indexStore %s" % self.id)

        if not filePath:
            temp = self.get_path(session, 'tempPath')
            dfp = self.get_path(session, 'defaultPath')
            if not os.path.isabs(temp):
                temp = os.path.join(dfp, temp)
            basename = self._generateFilename(index)
            filePath = os.path.join(temp, basename + "_SORT")
            
        cxn = self._openIndex(session, index)
        cursor = cxn.cursor()
        nonEmpty = cursor.first()
        metadataCxn = self._openMetadata(session)        

        # Should this be:
        # f = codecs.open(filePath, 'r', 'utf-8')    ?
        f = file(filePath)

        tidIdx = index.get_path(session, 'termIdIndex', None)
        vectors = index.get_setting(session, 'vectors', 0)
        proxVectors = index.get_setting(session, 'proxVectors', 0)
        termIds = index.get_setting(session, 'termIds', 0)

        if not nonEmpty:
            termid = long(0)
        else:
            # find highest termid. First check termid->term map
            tidcxn = None
            if vectors:
                tidcxn = self.termIdCxn.get(index, None)
                if not tidcxn:
                    self._openVectors(session, index)
                    tidcxn = self.termIdCxn.get(index, None)
            if not tidcxn:
                # okay, no termid hash. hope for best with final set
                # of terms from regular index
                (term, value) = cursor.last(doff=0, dlen=3*index.longStructSize)
                (last, x,y) = index.deserialize_term(session, value)                    
            else:
                tidcursor = tidcxn.cursor()
                (finaltid, term) = tidcursor.last()
                last = long(finaltid)
                tidcxn.close()
                del tidcxn
                self.termIdCxn[index] = None
            termid = last

        currTerm = None
        currData = []
        l = 1

        s2t = index.deserialize_term
        mt = index.merge_term
        t2s = index.serialize_term
        minTerms = index.get_setting(session, 'minimumSupport')
        if not minTerms:
            minTerms = 0

        dfp = self.get_path(session, 'defaultPath')
        basename = self._generateFilename(index)
        dbname = os.path.join(dfp, basename)
        if vectors or termIds:
            tidcxn = bdb.db.DB()
            tidcxn.open(dbname + "_TERMIDS")
        

        nTerms = 0
        nRecs = 0
        nOccs = 0
        totalChars = 0
        maxNRecs = 0
        maxNOccs = 0
        
        start = time.time()
        while(l):
            l = f.readline()[:-1]
            data = l.split(nonTextToken)
            term = data[0]
            #fullinfo = map(long, data[1:])
            fullinfo = [long(x) for x in data[1:]]
            if term == currTerm:
                # accumulate
                if fullinfo:
                    totalRecs += 1
                    totalOccs += fullinfo[2]
                    currData.extend(fullinfo)
            else:
                # Store
                #if currData and totalRecs >= minTerms:
                if currData:                
                    if (nonEmpty):
                        val = cxn.get(currTerm)
                        if (val != None):
                            unpacked = s2t(session, val)
                            tempTermId = unpacked[0]
                            unpacked = mt(session, unpacked, currData, 'add', nRecs=totalRecs, nOccs=totalOccs)
                            totalRecs = unpacked[1]
                            totalOccs = unpacked[2]
                            unpacked = unpacked[3:]
                            termid -= 1
                        else:
                            tempTermId = termid
                            unpacked = currData
                        packed = t2s(session, tempTermId, unpacked, nRecs=totalRecs, nOccs=totalOccs)
                    else:
                        tempTermId = termid
                        try:
                            packed = t2s(session, termid, currData, nRecs=totalRecs, nOccs=totalOccs)
                        except:
                            print "%s failed to t2s %s" % (self.id, currTerm)
                            print termid
                            print currData
                            raise
                    nTerms += 1
                    nRecs += totalRecs
                    nOccs += totalOccs
                    totalChars += len(currTerm)
                    maxNRecs = max(maxNRecs, totalRecs)
                    maxNOccs = max(maxNOccs, totalOccs)
                    cxn.put(currTerm, packed)
                    if (vectors or termIds) and tempTermId == termid:
                        tidcxn.put("%012d" % termid, currTerm)
                # assign new line
                try:
                    totalOccs = fullinfo[2]
                    # we'll decrement if we already exist
                    termid += 1
                    currTerm = term
                    currData = fullinfo
                    totalRecs = 1
                except:
                    # end of file
                    pass

        self._closeIndex(session, index)
        os.remove(filePath)

        if metadataCxn:
            # LLLLLL:  nTerms, nRecs, nOccs, maxRecs, maxOccs, totalChars
            val = struct.pack("LLLLLL", nTerms, nRecs, nOccs, maxNRecs, maxNOccs, totalChars)
            metadataCxn.put(index.id.encode('utf8'), val)
            self._closeMetadata(session)

        if vectors or termIds:
            tidcxn.close()

        if vectors:
            # build vectors here
            termCache = {}
            freqCache = {}
            maxCacheSize = index.get_setting(session, 'maxVectorCacheSize', -1)
            if maxCacheSize == -1:
                maxCacheSize = self.get_setting(session, 'maxVectorCacheSize', 50000)

            rand = random.Random()

            # settings for what to go into vector store
            # -1 for just put everything in
            minGlobalFreq = int(index.get_setting(session, 'vectorMinGlobalFreq', '-1'))
            maxGlobalFreq = int(index.get_setting(session, 'vectorMaxGlobalFreq', '-1'))
            minGlobalOccs = int(index.get_setting(session, 'vectorMinGlobalOccs', '-1'))
            maxGlobalOccs = int(index.get_setting(session, 'vectorMaxGlobalOccs', '-1'))
            minLocalFreq = int(index.get_setting(session, 'vectorMinLocalFreq', '-1'))
            maxLocalFreq = int(index.get_setting(session, 'vectorMaxLocalFreq', '-1'))

            base = filePath[:-4] + "TEMP"
            fh = codecs.open(base, 'r', 'utf-8', 'xmlcharrefreplace')
            # read in each line, look up 
            currDoc = "000000000000"
            currStore = "0"
            docArray = []
            proxHash = {}
            cxn = bdb.db.DB()
            cxn.open( dbname + "_VECTORS")
            if proxVectors:
                proxCxn = bdb.db.DB()
                proxCxn.open(dbname +"_PROXVECTORS")

            totalTerms = 0
            totalFreq = 0
            while True:            
                try:
                    l = fh.readline()[:-1]
                    bits = l.split(nonTextToken)
                except:
                    break
                if len(bits) < 4:
                    break
                (term, docid, storeid, freq) = bits[:4]
                if docArray and (docid != currDoc or currStore != storeid):
                    # store previous
                    docArray.sort()
                    flat = []
                    [flat.extend(x) for x in docArray]
                    fmt = "L" * len(flat)                    
                    packed = struct.pack(fmt, *flat)
                    cxn.put(str("%s|%s" % (currStore, currDoc.encode('utf8'))), packed)
                    docArray = []
                    if proxVectors:
                        pdocid = long(currDoc)
                        for (elem, parr) in proxHash.iteritems():
                            proxKey = struct.pack('LL', pdocid, elem)
                            if elem < 0 or elem > 4294967295:
                                raise ValueError(elem)

                            proxKey = "%s|%s" % (currStore.encode('utf8'), proxKey)
                            parr.sort()
                            flat = []
                            [flat.extend(x) for x in parr]
                            proxVal = struct.pack('L' * len(flat), *flat)
                            proxCxn.put(proxKey, proxVal)
                        proxHash = {}                        
                currDoc = docid
                currStore = storeid
                tid = termCache.get(term, None)
                if tid == None:
                    if not term:
                        #???
                        continue
                    tdata = self.fetch_term(session, index, term, summary=True)
                    try:
                        (tid, tdocs, tfreq) = tdata[:3]
                    except:
                        print term
                        print index.id
                        print tdata
                        raise
                    termCache[term] = tid
                    freqCache[term] = [tdocs, tfreq]
                    # check caches aren't exploding
                    ltc = len(termCache)
                    if ltc >= maxCacheSize:
                        # select random key to remove
                        (k,v) = termCache.popitem()
                        del freqCache[k]
                        # too many random calls
                        #r = rand.randint(0,ltc-1)
                        #k = termCache.keys()[r]
                        #del termCache[k]
                        #del freqCache[k]
                else:
                    (tdocs, tfreq) = freqCache[term]
                if ( (minGlobalFreq == -1 or tdocs >= minGlobalFreq) and
                     (maxGlobalFreq == -1 or tdocs <= maxGlobalFreq) and
                     (minGlobalOccs == -1 or tfreq >= minGlobalOccs) and
                     (maxGlobalOccs == -1 or tfreq <= maxGlobalOccs) and
                     (minLocalFreq == -1 or tfreq >= minLocalFreq) and
                     (maxLocalFreq == -1 or tfreq <= maxLocalFreq) ):
                    docArray.append([tid, long(freq)])
                    totalTerms += 1
                    totalFreq += long(freq)                    
                if proxVectors:
                    nProxInts = index.get_setting(session, 'nProxInts', 2)
                    # proxInfo = map(long, bits[4:])
                    proxInfo = [long(x) for x in bits[4:]]
                    tups = [proxInfo[x:x+nProxInts] for x in range(0,len(proxInfo),nProxInts)]
                    for t in tups:
                        val = [t[1], tid]
                        val.extend(t[2:])                        
                        try:
                            proxHash[t[0]].append(val)
                        except KeyError:
                            proxHash[t[0]] = [val]
                    
            # Catch final document
            if docArray:
                docArray.sort()
                # Put in total terms, total occurences
                flat = []
                [flat.extend(x) for x in docArray]
                fmt = "L" * len(flat)
                packed = struct.pack(fmt, *flat)
                cxn.put(str("%s|%s" % (storeid, docid.encode('utf8'))), packed)
                if proxVectors:
                    pdocid = long(currDoc)
                    for (elem, parr) in proxHash.iteritems():
                        proxKey = struct.pack('LL', pdocid, elem)
                        proxKey = "%s|%s" % (storeid.encode('utf8'), proxKey)
                        parr.sort()
                        flat = []
                        [flat.extend(x) for x in parr]
                        proxVal = struct.pack('L' * len(flat), *flat)
                        proxCxn.put(proxKey, proxVal)
                    proxCxn.close()
            fh.close()
            cxn.close()
            os.remove(base)

        fl = index.get_setting(session, 'freqList', "")
        if fl:
            cxn = self._openIndex(session, index)
            cursor = cxn.cursor()
            dataLen = index.longStructSize * self.reservedLongs
            terms = []

            try:
                (term, val) = cursor.first(doff=0, dlen=dataLen)
                while (val):
                    (termid, recs, occs) = struct.unpack('lll', val)
                    terms.append({'i' : termid, 'r' : recs, 'o' : occs})
                    try:
                        (term, val) = cursor.next(doff=0, dlen=dataLen)
                    except:
                        val = 0
                lt = len(terms)
                if fl.find('rec') > -1:
                    # 1 = most frequent
                    terms.sort(key=lambda x: x['r'], reverse=True)
                    cxn = bdb.db.DB()
                    cxn.open(dbname + "_FREQ_REC")
                    for (t, term) in enumerate(terms):
                        termidstr = struct.pack('ll', term['i'], term['r'])
                        cxn.put("%012d" % t, termidstr)                                        
                    cxn.close()

                if fl.find('occ') > -1:
                    terms.sort(key=lambda x: x['o'], reverse=True)                
                    cxn = bdb.db.DB()
                    cxn.open(dbname + "_FREQ_OCC")
                    for (t, term) in enumerate(terms):
                        termidstr = struct.pack('ll', term['i'], term['o'])
                        cxn.put("%012d" % t, termidstr)                                        
                    cxn.close()                
            except TypeError:
                # no data in index
                pass
            self._closeIndex(session, index)

        return None
    
    
    def _closeVectors(self, session, index):
        for cxnx in [self.termIdCxn, self.vectorCxn, self.proxVectorCxn]:
            try: 
                cxnx[index].close()
            except KeyError:
                continue

            del cxnx[index]


    def _openVectors(self, session, index):
        tidcxn = bdb.db.DB()
        dfp = self.get_path(session, 'defaultPath')
        basename = self._generateFilename(index)

        dbname = os.path.join(dfp, basename)
        tidcxn.open( dbname + "_TERMIDS")
        self.termIdCxn[index] = tidcxn
        if index.get_setting(session, 'vectors'):
            cxn = bdb.db.DB()
            cxn.open(dbname + "_VECTORS")
            self.vectorCxn[index] = cxn
        if index.get_setting(session, 'proxVectors'):
            cxn = bdb.db.DB()
            cxn.open(dbname + "_PROXVECTORS")
            self.proxVectorCxn[index] = cxn


    def fetch_vector(self, session, index, rec, summary=False):
        # rec can be resultSetItem or record

        tidcxn = self.termIdCxn.get(index, None)
        if not tidcxn:
            self._openVectors(session, index)
            tidcxn = self.termIdCxn.get(index, None)
            cxn = self.vectorCxn.get(index, None)
        else:
            cxn = self.vectorCxn[index]

        docid = rec.id
        if (not type(docid) in NumTypes):
            if (type(docid) == types.StringType and docid.isdigit()):
                docid = long(docid)
            else:
                # Look up identifier in local bdb
                docid = self._get_internalId(session, rec)         
        docid = "%012d" % docid
        # now add in store
        docid = "%s|%s" % (self.storeHashReverse[rec.recordStore], docid)

        if summary:
            data = cxn.get(docid, doff=0, dlen=8)
        else:
            data = cxn.get(docid)
        if data:
            flat = struct.unpack('L' * (len(data)/4), data)
            lf = len(flat)
            unflatten = [(flat[x], flat[x+1]) for x in xrange(0,lf,2)]
            # totalTerms, totalFreq, [(termId, freq),...]
            lu = lf /2
            return [lu, sum([x[1] for x in unflatten]), unflatten]
        else:
            return []


    def fetch_proxVector(self, session, index, rec, elemId=-1):
        # rec can be resultSetItem or record

        cxn = self.proxVectorCxn.get(index, None)
        if cxn == None:
            self._openVectors(session, index)
            cxn = self.proxVectorCxn.get(index, None)

        docid = rec.id
        if (not type(docid) in NumTypes):
            if (type(docid) == types.StringType and docid.isdigit()):
                docid = long(docid)
            else:
                # Look up identifier in local bdb
                docid = self._get_internalId(session, rec)         

        nProxInts = index.get_setting(session, 'nProxInts', 2)
        def unpack(data):
            flat = struct.unpack('L' * (len(data)/4), data)
            lf = len(flat)
            unflat = [flat[x:x+nProxInts] for x in range(0,lf,nProxInts)]
            return unflat

        if elemId == -1:
            # fetch all for this record
            key = struct.pack('LL', docid, 0)
            keyid = key[:4]
            key = str(self.storeHashReverse[rec.recordStore]) + "|" +  key
            c = cxn.cursor()
            (k, v) = c.set_range(key)
            vals = {}
            # XXX won't work for > 9 recordStores...
            while k[2:6] == keyid:
                elemId = struct.unpack('L', k[6:])[0]
                vals[elemId] = unpack(v)
                try:
                    (k,v) = c.next()
                except TypeError:
                    break
            return vals
            
        else:
            key = struct.pack('LL', docid, elemId)
            # now add in store
            key = str(self.storeHashReverse[rec.recordStore]) + "|" +  key
            data = cxn.get(key)
            if data:
                return unpack(data)
            else:
                return []

    def fetch_termById(self, session, index, termId):
        tidcxn = self.termIdCxn.get(index, None)
        if not tidcxn:
            self._openVectors(session, index)
            tidcxn = self.termIdCxn.get(index, None)
        termid = "%012d" % termId
        data = tidcxn.get(termId)
        if type(data) == tuple and data[0] == termid:
            data = data[1]
        if not data:
            return ""
        else:
            return data


    def _closeTermFreq(self, session, index, which):
        try: cxns = self.termFreqCxn[index]
        except KeyError: return
        try: cxns[which].close()
        except KeyError: return
        del self.termFreqCxn[index][which]


    def _openTermFreq(self, session, index, which):

        fl = index.get_setting(session, "freqList", "") 
        if fl.find(which) == -1:
            return None

        cxns = self.termFreqCxn.get(index, {})
        tfcxn = cxns.get(which, None)
        if tfcxn != None:
            return tfcxn
        
        tfcxn = bdb.db.DB()
        dfp = self.get_path(session, 'defaultPath')
        basename = self._generateFilename(index)
        dbname = os.path.join(dfp, basename)
        if which == 'rec':
            tfcxn.open(dbname + "_FREQ_REC")
            if cxns == {}:
                self.termFreqCxn[index] = {'rec' : tfcxn}
            else:
                self.termFreqCxn[index]['rec'] = tfcxn
        elif which == 'occ':
            tfcxn.open(dbname + "_FREQ_OCC")
            if cxns == {}:
                self.termFreqCxn[index] = {'occ' : tfcxn}
            else:
                self.termFreqCxn[index]['occ'] = tfcxn
        return tfcxn


    def fetch_termFrequencies(self, session, index, mType='occ', start=1, nTerms=100, direction=">"):
        cxn = self._openTermFreq(session, index, mType)
        if cxn == None:
            return []
        else:
            c = cxn.cursor()
            freqs = []
            
            if start < 0:
                # go to end and reverse
                (t,v) = c.last()
                if start != -1:
                    slot = int(t) + start + 1
                    (t,v) = c.set_range("%012d" % slot)
            elif start == 0:
                (t,v) = c.first()
            else:
                (t,v) = c.set_range("%012d" % start)
            if direction[0] == "<":
                next = c.prev
            else:
                next = c.next
            while len(freqs) < nTerms:
                (tid, fr) = struct.unpack('ll', v)
                freqs.append((int(t), tid, fr))
                try:
                    (t,v) = next()
                except TypeError:
                    break
            return freqs


    def fetch_indexMetadata(self, session, index):
        cxn = self._openMetadata(session)
        data = cxn.get(index.id.encode('utf-8'))
        if data:
            # LLLLLL:  nTerms, nRecs, nOccs, maxRecs, maxOccs, totalChars
            vals = struct.unpack('LLLLLL', data)
            return dict(zip(('nTerms', 'nRecs', 'nOccs', 'maxRecs', 'maxOccs', 'totalChars'), vals))
            return vals
        else:
            return []


    def create_term(self, session, index, termId, resultSet):
        # Take resultset and munge to index format, serialise, store

        term = resultSet.queryTerm
        unpacked = []
        # only way to be sure
        totalRecs = resultSet.totalRecs
        totalOccs = resultSet.totalOccs
        for item in resultSet:
            unpacked.extend([item.id, self.storeHashReverse[item.recordStore], item.occurences])
        packed = index.serialize_term(session, termId, unpacked, nRecs=totalRecs, nOccs=totalOccs)
        cxn = self._openIndex(session, index)
        cxn.put(term, packed)
        # NB: need to remember to close index manually

    def contains_index(self, session, index):
        # Send Index object, check exists, return boolean
        dfp = self.get_path(session, "defaultPath")
        name = self._generateFilename(index)
        return os.path.exists(os.path.join(dfp, name))
    
    
    def _create_indexFile(self, dbname, flags=[]):
        # for use by self.create_index
        if os.path.exists(dbname):
            raise FileAlreadyExistsException(dbname)
        cxn = bdb.db.DB()
        for f in flags:
            cxn.set_flags(f)
        try:
            cxn.open(dbname, dbtype=bdb.db.DB_BTREE, flags=bdb.db.DB_CREATE, mode=0660)
        except:
            raise ConfigFileException(dbname)
        else:
            cxn.close()
        

    def create_index(self, session, index):
        # Send Index object to create, null return
        p = self.permissionHandlers.get('info:srw/operation/1/create', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to create index in %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to create index in %s" % self.id)

        dfp = self.get_path(session, "defaultPath")
        name = self._generateFilename(index)
        fullname = os.path.join(dfp, name)
        try: self._create_indexFile(fullname)
        except FileAlreadyExistsException: pass
        
        if (index.get_setting(session, "sortStore")):
            try: self._create_indexFile(fullname + "_VALUES")
            except FileAlreadyExistsException: pass
            
        vecs = index.get_setting(session, "vectors")
        tids = index.get_setting(session, "termIds")
        if vecs or tids:
            try: self._create_indexFile(fullname + "_TERMIDS", flags=[bdb.db.DB_RECNUM])
            except FileAlreadyExistsException: pass

        if vecs:
            try:
                try: self._create_indexFile(fullname + "_VECTORS", flags=[bdb.db.DB_RECNUM])
                except FileAlreadyExistsException: pass

                if index.get_setting(session, 'proxVectors'):
                    try: self._create_indexFile(fullname + "_PROXVECTORS", flags=[bdb.db.DB_RECNUM])
                    except FileAlreadyExistsException: pass

            except:
                raise(ValueError)
        fl = index.get_setting(session, "freqList", "") 
        if fl:
            if fl.find('rec') > -1: 
                try: self._create_indexFile(fullname + "_FREQ_REC", flags=[bdb.db.DB_RECNUM])
                except FileAlreadyExistsException: pass

            if fl.find('occ') > -1:
                try: self._create_indexFile(fullname + "_FREQ_OCC", flags=[bdb.db.DB_RECNUM])
                except FileAlreadyExistsException: pass

        return 1


    def clear_index(self, session, index):
        self._closeIndex(session, index)
        self._closeVectors(session, index)
        self._closeTermFreq(session, index, 'rec')
        self._closeTermFreq(session, index, 'occ')
        for dbname in self._listExistingFiles(session, index):
            cxn = bdb.db.DB()
            cxn.remove(dbname)

        self.create_index(session, index)
        return None


    def delete_index(self, session, index):
        # Send Index object to delete, null return
        p = self.permissionHandlers.get('info:srw/operation/1/delete', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to delete index from %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to delete index from %s" % self.id)
        
        for dbname in self._listExistingFiles(session, index):
            os.remove(dbname)

        return 1

        
    def fetch_sortValue(self, session, index, rec):
        if (self.sortStoreCxn.has_key(index)):
            cxn = self.sortStoreCxn[index]
        else:
            if (not index.get_setting(session, 'sortStore')):
                raise FileDoesNotExistException()
            dfp = self.get_path(session, "defaultPath")
            name = self._generateFilename(index) + "_VALUES"
            fullname = os.path.join(dfp, name)
            cxn = bdb.db.DB()
            #cxn.set_flags(bdb.db.DB_RECNUM)
            if session.environment == "apache":
                cxn.open(fullname, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(fullname)
            self.sortStoreCxn[index] = cxn
        return cxn.get("%s/%s" % (str(rec.recordStore), rec.id))


    def store_terms(self, session, index, terms, rec):
        # Store terms from hash
        # Need to store:  term, totalOccs, totalRecs, (record id, recordStore id, number of occs in record)
        # hash is now {tokenA:tokenA, ...}

        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add to indexStore %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to indexStore %s" % self.id)

        if (not terms):
            # No terms to index
            return

        storeid = rec.recordStore
        if (not type(storeid) in NumTypes):
            # Map
            if (self.storeHashReverse.has_key(storeid)):
                storeid = self.storeHashReverse[storeid]
            else:
                # YYY: Error or metadata store?
                self.storeHashReverse[storeid] = len(self.storeHash.keys())
                self.storeHash[self.storeHashReverse[storeid]] = storeid
                raise ConfigFileException("indexStore %s does not recognise recordStore: %s" % (self.id, storeid))
        
        docid = rec.id
        if (not type(docid) in NumTypes):
            if (type(docid) == types.StringType and docid.isdigit()):
                docid = long(docid)
            else:
                # Look up identifier in local bdb
                docid = self._get_internalId(session, rec)         
        elif (docid == -1):
            # Unstored record
            raise ValueError(str(record))
        
        if self.outFiles.has_key(index):
            # Batch loading
            value = terms.values()[0]['text']
            if (self.outSortFiles.has_key(index) and value):
                if type(value) == unicode:
                    sortVal = value.encode('utf-8')
                else:
                    sortVal = value
                self.outSortFiles[index].put("%s/%s" % (str(rec.recordStore), docid), sortVal)

            prox = terms[value].has_key('positions')
            for k in terms.values():
                kw = k['text']
                if type(kw) != unicode:
                    try:
                        kw = kw.decode('utf-8')
                    except:
                        print "%s failed to decode %s" % (self.id, repr(kw))
                        raise
                self.outFiles[index].write(kw)
                # ensure that docids are sorted to numeric order
                lineList = ["", "%012d" % docid, str(storeid), str(k['occurences'])]
                if prox:
                    # lineList.extend(map(str, k['positions']))
                    lineList.extend([str(x) for x in k['positions']])
                self.outFiles[index].write(nonTextToken.join(lineList) + "\n")
        else:

            # Directly insert into index
            cxn = self._openIndex(session, index)

            # This is going to be ... slow ... with lots of i/o
            # Use commit method unless only doing very small amounts of work.

            for k in terms.values():
                key = k['text']
                stuff = [docid, storeid, k['occurences']]
                try:
                    stuff.extend(k['positions'])
                except:
                    pass
                val = cxn.get(key.encode('utf-8'))
                if (val != None):
                    current = index.deserialize_term(session, val)               
                    unpacked = index.merge_term(session, current, stuff, op="replace", nRecs=1, nOccs=k['occurences'])
                    (termid, totalRecs, totalOccs) = unpacked[:3]
                    unpacked = unpacked[3:]
                else:
                    # This will screw up non vectorised indexes.
                    termid = cxn.stat()['nkeys']
                    unpacked = stuff
                    totalRecs = 1
                    totalOccs = k['occurences']
                   
                packed = index.serialize_term(session, termid, unpacked, nRecs=totalRecs, nOccs=totalOccs)
                cxn.put(key.encode('utf-8'), packed)
            self._closeIndex(session, index)

    def delete_terms(self, session, index, terms, rec):
        p = self.permissionHandlers.get('info:srw/operation/2/unindex', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to delete from indexStore %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to delete from indexStore %s" % self.id)
        if not terms:
            return

        docid = rec.id
        # Hash
        if (type(docid) == types.StringType and docid.isdigit()):
            docid = long(docid)
        elif (type(docid) in NumTypes):
            pass        
        else:
            # Look up identifier in local bdb
            docid = self._get_internalId(session, rec)               
        
        storeid = rec.recordStore
        if (not type(storeid) in NumTypes):
            # Map
            if (self.storeHashReverse.has_key(storeid)):
                storeid = self.storeHashReverse[storeid]
            else:
                # YYY: Error or metadata store?
                self.storeHashReverse[storeid] = len(self.storeHash.keys())
                self.storeHash[self.storeHashReverse[storeid]] = storeid
                storeid = self.storeHashReverse[storeid]
                raise ConfigFileException("indexStore %s does not recognise recordStore: %s" % (self.id, storeid))        

            # Directly insert into index
            cxn = self._openIndex(session, index)

            for k in terms.keys():
                val = cxn.get(k.encode('utf-8'))
                if (val <> None):
                    current = index.deserialize_term(session, val)               
                    gone = [docid, storeid, terms[k]['occurences']]
                    unpacked = index.merge_term(session, current, gone, 'delete')
                    if not unpacked[1]:
                        # all terms deleted
                        cxn.delete(k.encode('utf-8'))
                    else:
                        packed = index.serialize_term(session, current[0], unpacked[3:])
                        cxn.put(k.encode('utf-8'), packed)
            self._closeIndex(session, index)


    # NB:  c.set_range('a', dlen=12, doff=0)
    # --> (key, 12bytestring)    
    # --> unpack for termid, docs, occs

    def fetch_termList(self, session, index, term, nTerms=0, relation="", end="", summary=0, reverse=0):
        p = self.permissionHandlers.get('info:srw/operation/2/scan', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to scan indexStore %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to scan indexStore %s" % self.id)

        if (not (nTerms or relation or end)):
            nTerms = 20
        if (not relation and not end):
            relation = ">="
        if type(end) == unicode:
            end = end.encode('utf-8')
        if (not relation):
            if (term > end):
                relation = "<="
            else:
                relation = ">"

        if reverse:
            dfp = self.get_path(session, "defaultPath")
            name = self._generateFilename(index)
            fullname = os.path.join(dfp, name)
            fullname += "_REVERSE"
            term = term[::-1]
            end = end[::-1]
            cxn = bdb.db.DB()
            # cxn.set_flags(bdb.db.DB_RECNUM)
            if session.environment == "apache":
                cxn.open(fullname, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(fullname)
        else:
            cxn = self._openIndex(session, index)

        if summary:
            dataLen = index.longStructSize * self.reservedLongs

        c = cxn.cursor()
        term = term.encode('utf-8')
        try:
            if summary:
                (key, data) = c.set_range(term, dlen=dataLen,doff=0)
            else:
                (key, data) = c.set_range(term)
        except Exception, e:
            try:
                if summary:
                    (key, data) = c.last(dlen=dataLen, doff=0)
                else:
                    (key, data) = c.last()
            except TypeError:
                # Index is empty
                return []
            if (relation in [">", ">="] and term > key):
                # Asked for > than maximum key
                return []

        tlist = []
        fetching = 1

        if (key == term and relation in ['>', '<']):
            pass
        elif (key > term and relation in ['<', '<=']):
            pass
        elif (key > term and relation in ['<', '<=']):
            pass
        else:
            unpacked = index.deserialize_term(session, data)
            if reverse:
                key = key[::-1]
            tlist.append([key.decode('utf-8'), unpacked])
            if nTerms == 1:
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
                elif (end and dir  == "<" and key <= end):
                    fetching = 0
                else:
                    unpacked = index.deserialize_term(session, rec)
                    if reverse:
                        key = key[::-1]
                    tlist.append([key.decode('utf-8'), unpacked])
                    if (nTerms and len(tlist) == nTerms):
                        fetching = 0
            else:
                if tlist:
                    if (dir == ">"):
                        tlist[-1].append("last")
                    else:
                        tlist[-1].append("first")
                key = None
                fetching = 0

        return tlist


    def construct_resultSetItem(self, session, recId, recStoreId, nOccs, rsiType="SimpleResultSetItem"):
        recStore = self.storeHash[recStoreId]
        if self.identifierMapCxn and self.identifierMapCxn.has_key(recStore):
            numericId = recId
            recId = self._get_externalId(session, recStore, numericId)
        else:
            numericId = None
        if rsiType == "SimpleResultSetItem":
            return SimpleResultSetItem(session, recId, recStore, nOccs, session.database, numeric=numericId)
        elif rsiType == "Hash":
            return ("%s/%s" % (recStore, recId), {"recordStore" : recStore, "recordId" : recId, "occurences" : nOccs, "database" : session.database})
        else:
            raise NotImplementedError(rsitype)


    def fetch_term(self, session, index, term, summary=False, prox=True):
        p = self.permissionHandlers.get('info:srw/operation/2/search', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to search indexStore %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to search indexStore %s" % self.id)
        unpacked = []
        val = self._fetch_packed(session, index, term, summary)
        if (val != None):
            try:
                unpacked = index.deserialize_term(session, val, prox=prox)
            except:
                raise
                print "%s failed to deserialise %s %s %s" % (self.id, index.id, term, val)
        return unpacked

    def _fetch_packed(self, session, index, term, summary=False, numReq=0, start=0):
        try:
            term = term.encode('utf-8')
        except:
            pass
        cxn = self._openIndex(session, index)
        if summary:
            dataLen = index.longStructSize * self.reservedLongs
            val = cxn.get(term, doff=0, dlen=dataLen)

        elif (start != 0 or numReq != 0) and index.canExtractSection:
            # try to extract only section...
            fulllen = cxn.get_size(term)
            offsets = index.calc_sectionOffsets(session, start, numReq, fulllen)
            if not numReq:
                numReq = 100

            # XXX this should be on index somewhere!!
            # first get summary
            vals = []
            dataLen = index.longStructSize * self.reservedLongs
            val = cxn.get(term, doff=0, dlen=dataLen)
            vals.append(val)
            # now step through offsets, prolly only 1
            for o in offsets:
                val = cxn.get(term, doff=o[0], dlen=o[1])
                if len(o) > 2:
                    val = o[2] + val
                if len(o) > 3:
                    val = val + o[3]
                vals.append(val)
            return ''.join(vals)
        else:
            val = cxn.get(term)
        return val




