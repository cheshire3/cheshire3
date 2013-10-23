"""Cheshire3 IndexStore Implementations."""

import sys
import os
import types
import struct
import time
import glob
import re
import random
import fileinput

try:
    # Python 2.3 vs 2.2
    import bsddb as bdb
except ImportError:
    import bsddb3 as bdb

# Intra-package import - absolute imports are good practice
from cheshire3.baseObjects import IndexStore, Database
from cheshire3.configParser import C3Object
from cheshire3.exceptions import ConfigFileException
from cheshire3.exceptions import FileDoesNotExistException,\
    FileAlreadyExistsException, PermissionException
from cheshire3.resultSet import SimpleResultSetItem
from cheshire3.index import *
from cheshire3.baseStore import SwitchingBdbConnection
from cheshire3.utils import getShellResult


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
            start = len(self.indexStore.id) + 2
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
    storeHash = {}
    storeHashReverse = {}

    sortStoreCxn = {}
    identifierMapCxn = {}
    indexCxn = {}
    vectorCxn = {}
    proxVectorCxn = {}
    termIdCxn = {}

    reservedLongs = 3

    _possiblePaths = {
        'recordStoreHash': {
            'docs': ("Space separated list of recordStore identifiers kept "
                     "in this indexStore (e.g. map from position in list to "
                     "integer)")
        },
        'tempPath': {
            'docs': ("Path in which temporary files are kept during batch"
                     "mode indexing")
        },
        'sortPath': {
            'docs': ("Path to the 'sort' utility used for sorting temporary "
                     "files")
        }
    }

    _possibleSettings = {
        'maxVectorCacheSize': {
            'docs': "Number of terms to cache when building vectors",
            'type': int
        },
        'bucketType': {
            'docs': ("Type of 'bucket' to use when splitting an index over "
                     "multiple files."),
            'options': 'term1|term2|hash'
        },
        'maxBuckets': {
            'docs': "Maximum number of 'buckets' to split an index into",
            'type': int
        },
        'maxItemsPerBucket': {
            'docs': "Maximum number of items to put into each 'bucket'",
            'type': int
        },
        'vectorBucketType': {
            'docs': ("Type of 'bucket' to use when splitting an index's "
                     "vectors over multiple files."),
            'options': 'hash|int'
        },
        'vectorMaxBuckets': {
            'docs': ("Maximum number of 'buckets' to split an index's "
                     "vectors into"),
            'type': int
        },
        'vectorMaxItemsPerBucket': {
            'docs': ("Maximum number of items to put into each vector "
                     "'bucket'"),
            'type': int
        },
        'dirPerIndex': {
            'docs': "Create a sub-directory for each index, yes or no?",
            'type': int,
            'options': '0|1'
        }
    }

    def __init__(self, session, config, parent):
        IndexStore.__init__(self, session, config, parent)
        self.session = session
        self.reservedLongs = 3

        # Temporary, small, necessarily single, or don't care dbs/files
        self.outFiles = {}          # batch loading file
        self.metadataCxn = None     # indexStore level metadata
        self.identifierMapCxn = {}  # str recid <--> long recid

        # Splittable files (Bdb connection objects)
        # Controlled by switching
        self.switching = (
            self.get_setting(session, 'bucketType', '') or
            self.get_setting(session, 'maxBuckets', 0) or
            self.get_setting(session, 'maxItemsPerBucket', 0)
        )
        self.switchingClass = SwitchingBdbConnection
        self.indexCxn = {}          # term -> rec list

        # Controlled by vectorSwitching
        self.vectorSwitching = (
            self.get_setting(session, 'vectorBucketType', '') or
            self.get_setting(session, 'vectorMaxBuckets', 0) or
            self.get_setting(session, 'vectorMaxItemsPerBucket', 0)
        )
        self.vectorSwitchingClass = SwitchingBdbConnection
        self.sortStoreCxn = {}      # recid -> sort value
        self.termIdCxn = {}         # termid -> term value
        self.vectorCxn = {}         # recid -> term vector
        self.proxVectorCxn = {}     # recid -> term prox vector
        self.termFreqCxn = {}       # rank -> term

        self.createArgs = {}

        self.storeHash = {}
        rsh = self.get_path(session, 'recordStoreHash')
        if rsh:
            wds = rsh.split()
            for (w, wd) in enumerate(wds):
                self.storeHash[w] = wd
                self.storeHashReverse[wd] = w

        self.dirPerIndex = self.get_setting(session, 'dirPerIndex', 0)

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
                msg = "Cannot create default path for %s: %s" % (self.id, dfp)
                raise ConfigFileException(msg)

        for f in files:
            if (f[:fnlen] == fnbase):
                recstore = f[fnlen:-4]
                dbp = os.path.join(dfp, f)
                cxn = bdb.db.DB()
                if session.environment == "apache":
                    cxn.open(dbp, flags=bdb.db.DB_NOMMAP)
                else:
                    cxn.open(dbp)
                self.identifierMapCxn[recstore] = cxn

    def __iter__(self):
        return IndexStoreIter(self.session, self)

    def _openMetadata(self, session):
        if self.metadataCxn is not None:
            return self.metadataCxn
        else:
            mp = self.get_path(session, 'metadataPath')
            if not mp:
                dfp = self.get_path(session, 'defaultPath')
                mp = os.path.join(dfp, 'metadata.bdb')

            if not os.path.exists(mp):
                oxn = bdb.db.DB()
                oxn.open(mp, dbtype=bdb.db.DB_BTREE,
                         flags=bdb.db.DB_CREATE, mode=0660)
                oxn.close()

            cxn = bdb.db.DB()
            if session.environment == "apache":
                cxn.open(mp, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(mp)
            self.metadataCxn = cxn
            return cxn

    def _closeMetadata(self, session):
        if self.metadataCxn is not None:
            self.metadataCxn.close()
            self.metadataCxn = None

    def _closeIndex(self, session, index):
        if index in self.indexCxn:
            self.indexCxn[index].close()
            del self.indexCxn[index]

    def _openIndex(self, session, index):
        if index in self.indexCxn:
            return self.indexCxn[index]
        else:
            dfp = self.get_path(session, 'defaultPath')
            basename = self._generateFilename(index)
            dbp = os.path.join(dfp, basename)

            if self.switching:
                # check for overrides
                vbt = index.get_setting(session, 'bucketType', '')
                vmb = index.get_setting(session, 'maxBuckets', 0)
                vmi = index.get_setting(session, 'maxItemsPerBucket', 0)
                if vbt or vmb or vmi:
                    cxn = self.switchingClass(
                        session, self, dbp,
                        bucketType=vbt, maxBuckets=vmb, maxItemsPerBucket=vmi
                    )
                else:
                    cxn = self.switchingClass(session, self, dbp)
            else:
                cxn = bdb.db.DB()

            if session.environment == "apache":
                cxn.open(dbp, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(dbp)
            self.indexCxn[index] = cxn
            return cxn

    def _generateFilename(self, index):
        if self.dirPerIndex:
            return os.path.join(index.id, index.id + ".index")
        else:
            return "%s--%s.index" % (self.id, index.id)

    def _listExistingFiles(self, session, index):
        dfp = self.get_path(session, "defaultPath")
        name = self._generateFilename(index)
        return glob.glob(os.path.join(dfp, name + '*'))

    def _get_internalId(self, session, rec):
        if rec.recordStore in self.identifierMapCxn:
            cxn = self.identifierMapCxn[rec.recordStore]
        else:
            fn = "recordIdentifiers_{0}_{1}.bdb".format(self.id,
                                                        rec.recordStore)
            dfp = self.get_path(session, "defaultPath")
            dbp = os.path.join(dfp, fn)
            if not os.path.exists(dbp):
                cxn = bdb.db.DB()
                cxn.open(dbp, dbtype=bdb.db.DB_BTREE,
                         flags=bdb.db.DB_CREATE, mode=0660)
                cxn.close()
            cxn = bdb.db.DB()
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
        if recordStore in self.identifierMapCxn:
            cxn = self.identifierMapCxn[recordStore]
        else:
            fn = "recordIdentifiers_" + self.id + "_" + recordStore + ".bdb"
            dfp = self.get_path(session, "defaultPath")
            dbp = os.path.join(dfp, fn)
            if not os.path.exists(dbp):
                raise FileDoesNotExistException(dbp)
            cxn = bdb.db.DB()
            if session.environment == "apache":
                cxn.open(dbp, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(dbp)
            self.identifierMapCxn[recordStore] = cxn
        identifier = "%015d" % identifier
        data = cxn.get("__i2s_%s" % identifier)
        if data:
            return data
        elif data is not None:
            # We shouldn't raise DoesNotExistException, but we we probably
            # shouldn't return an empty string either.
            # However, returning anything other than the real identifier
            # (i.e. the empty string) results in errors further down the line
            return data
        else:
            msg = "%s/%s" % (recordStore, identifier)
            raise FileDoesNotExistException(msg)

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
            (termid, recs, occs) = struct.unpack('<lll', val)
            terms.append({'t': term, 'i': termid, 'r': recs, 'o': occs})
            try:
                (term, val) = cursor.next(doff=0, dlen=dataLen)
            except:
                val = 0

        self._closeIndex(session, index)
        return terms

    def begin_indexing(self, session, index):
        """Begin indexing process.

        Open BerkeleyDB connections, create temp files  etc.
        """
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to add to indexStore "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to add to indexStore %s" % self.id
                raise PermissionException(msg)
        temp = self.get_path(session, 'tempPath')
        if not os.path.isabs(temp):
            temp = os.path.join(self.get_path(session, 'defaultPath'), temp)
        if (not os.path.exists(temp)):
            try:
                os.mkdir(temp)
            except OSError:
                msg = 'TempPath does not exist and is not creatable.'
                raise ConfigFileException(msg)
        elif (not os.path.isdir(temp)):
            raise(ConfigFileException('TempPath is not a directory.'))

        if self.dirPerIndex:
            indexDirPath = os.path.join(temp, index.id)
            try:
                os.mkdir(indexDirPath)
            except OSError:
                # Already exists
                pass
            except:
                self.log_critical(session,
                                  "Could not create {0}"
                                  "".format(indexDirPath)
                                  )
                raise

        basename = os.path.join(temp, self._generateFilename(index))
        if (hasattr(session, 'task')):
            basename += str(session.task)

        # In case we're called twice
        if (not index in self.outFiles):
            self.outFiles[index] = codecs.open(basename + "_TEMP",
                                               'a',
                                               'utf-8',
                                               'xmlcharrefreplace')
            if (index.get_setting(session, "sortStore")):
                # Store in db for faster sorting
                dfp = self.get_path(session, "defaultPath")
                name = self._generateFilename(index) + "_VALUES"

                fullname = os.path.join(dfp, name)

                if self.vectorSwitching:
                    vbt = self.get_setting(session,
                                           'vectorBucketType',
                                           ''
                                           )
                    vmb = self.get_setting(session,
                                           'vectorMaxBuckets',
                                           0
                                           )
                    vmi = self.get_setting(session,
                                           'vectorMaxItemsPerBucket',
                                           0
                                           )
                    cxn = self.vectorSwitchingClass(
                        session, self, fullname,
                        bucketType=vbt, maxBuckets=vmb, maxItemsPerBucket=vmi
                    )
                else:
                    cxn = bdb.db.DB()
                if session.environment == "apache" or session.task:
                    # Do not memory map in multiprocess environments
                    cxn.open(fullname, flags=bdb.db.DB_NOMMAP)
                else:
                    cxn.open(fullname)
                self.sortStoreCxn[index] = cxn

    def commit_indexing(self, session, index):
        # Need to do this per index so one store can be doing multiple
        # things at once
        # Should only be called if begin_indexing() has been
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to add to indexStore "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to add to indexStore %s" % self.id
                raise PermissionException(msg)

        temp = self.get_path(session, 'tempPath')
        dfp = self.get_path(session, 'defaultPath')
        if not os.path.isabs(temp):
            temp = os.path.join(dfp, temp)

        try:
            self.sortStoreCxn[index].close()
            del self.sortStoreCxn[index]
        except KeyError:
            pass

        if (not index in self.outFiles):
            raise FileDoesNotExistException(index.id)
        sort = self.get_path(session, 'sortPath')
        if (not os.path.exists(sort)):
            msg = "Sort executable for %s does not exist" % self.id
            raise ConfigFileException(msg)

        fh = self.outFiles[index]
        fh.flush()
        fh.close()
        del self.outFiles[index]

        for db in self.identifierMapCxn.values():
            db.sync()

        # Sort the  _TEMP file written during indexing into a _SORT file
        basename = self._generateFilename(index)
        if (hasattr(session, 'task')):
            basename += str(session.task)

        basename = os.path.join(temp, basename)
        tempfile = basename + "_TEMP"
        sorted = basename + "_SORT"
        cmd = "%s %s -T %s -o %s" % (sort, tempfile, temp, sorted)
        getShellResult(cmd)
        # Sorting might fail.
        if (not os.path.exists(sorted)):
            msg = "Failed to sort {0}".format(tempfile)
            self.log_critical(session, msg)
            raise ValueError(msg)
        if not index.get_setting(session, 'vectors'):
            os.remove(tempfile)
        if ((hasattr(session, 'task') and session.task) or
            (hasattr(session, 'phase') and
             session.phase == 'commit_indexing1')):
            return sorted
        # Original terms from data
        return self.commit_centralIndexing(session, index, sorted)

    def commit_parallelIndexing(self, session, index):
        sort = self.get_path(session, 'sortPath')
        temp = self.get_path(session, 'tempPath')
        dfp = self.get_path(session, 'defaultPath')
        if not os.path.isabs(temp):
            temp = os.path.join(dfp, temp)
        # Merge multiple _SORT files into a single _SORT file for finalizing
        self.log_debug(session,
                       "Merging parallel sort files for {0}"
                       "".format(index.id)
                       )
        if (not os.path.exists(sort)):
            msg = "Sort executable for %s does not exist" % self.id
            raise ConfigFileException(msg)
        basename = self._generateFilename(index)
        baseGlob = os.path.join(temp, "%s*SORT" % basename)
        sortFileList = glob.glob(baseGlob)
        sortFiles = " ".join(sortFileList)
        sorted = os.path.join(temp, "%s_SORT" % basename)
        cmd = "%s -m -T %s -o %s %s" % (sort, temp, sorted, sortFiles)
        out = getShellResult(cmd)
        if not os.path.exists(sorted):
            msg = "Didn't sort %s" % index.id
            self.log_error(session, msg)
            raise ValueError(msg)
        # Merge multiple _TEMP files into a single _TEMP file
        baseGlob = os.path.join(temp, "%s*_TEMP" % basename)
        tempFileList = glob.glob(baseGlob)
        self.log_debug(session,
                       "Concatenating {0} parallel _TEMP files for {1}"
                       "".format(len(tempFileList), index.id)
                       )
        mergedFn = os.path.join(temp, "%s_TEMP" % basename)
        # Merge natively in Python. This takes longer than using `cat` but is
        # more reliable and should work cross-platform
        with open(mergedFn, 'wb') as outfh:
            for line in fileinput.input(tempFileList, mode='rb'):
                outfh.write(line)
        # Clean up
        for tsfn in sortFileList + tempFileList:
            os.remove(tsfn)
        return self.commit_centralIndexing(session, index, sorted)

    def commit_centralIndexing(self, session, index, filePath):
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to add to indexStore "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to add to indexStore %s" % self.id
                raise PermissionException(msg)
        if not filePath:
            temp = self.get_path(session, 'tempPath')
            dfp = self.get_path(session, 'defaultPath')
            if not os.path.isabs(temp):
                temp = os.path.join(dfp, temp)
            basename = self._generateFilename(index)
            filePath = os.path.join(temp, basename + "_SORT")

        cxn = self._openIndex(session, index)
        cursor = cxn.cursor()
        try:
            nonEmpty = cursor.first()
        except:
            nonEmpty = False
        metadataCxn = self._openMetadata(session)

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
                if tidcxn is None:
                    self._openVectors(session, index)
                    tidcxn = self.termIdCxn.get(index, None)
            if tidcxn is None:
                # okay, no termid hash. hope for best with final set
                # of terms from regular index
                (term, value) = cursor.last(doff=0,
                                            dlen=(3 * index.longStructSize))
                (last, x, y) = index.deserialize_term(session, value)
            else:
                tidcursor = tidcxn.cursor()
                (finaltid, term) = tidcursor.last()
                last = long(finaltid)
                tidcxn.close()
                self.termIdCxn[index] = None
                del tidcxn
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
            tidcxn = self.termIdCxn.get(index, None)
            if tidcxn is None:
                self._openVectors(session, index)
                tidcxn = self.termIdCxn.get(index, None)

        nTerms = 0
        nRecs = 0
        nOccs = 0
        totalChars = 0
        maxNRecs = 0
        maxNOccs = 0

        # Finalize sorted data in _SORT into Index file(s)
        f = file(filePath)
        while(l):
            l = f.readline()[:-1]
            data = l.split(nonTextToken)
            term = data[0]
            fullinfo = []
            for x in data[1:]:
                try:
                    fullinfo.append(long(x))
                except ValueError:
                    # Some unexpected data in the index :(
                    self.log_debug(session,
                                   'Unexpected value in raw index, '
                                   'attempting to recover...')
                    # Attempt to recover
                    # Find the first thing that could be a long but not
                    # entirely composed of 0s
                    try:
                        mylong = long(re.search('\d*[1-9]\d*', x).group(0))
                    except AttributeError:
                        # No match - nothing we can do
                        self.log_error(session,
                                       'Unexpected value in raw index data, '
                                       'skipping entry')
                        continue
                    else:
                        fullinfo.append(mylong)
                        self.log_debug(session,
                                       'Recovered value: {0}'.format(mylong))
            if term == currTerm:
                # Accumulate
                if fullinfo:
                    totalRecs += 1
                    totalOccs += fullinfo[2]
                    currData.extend(fullinfo)
            else:
                # Store
                if currData:
                    if (nonEmpty):
                        val = cxn.get(currTerm)
                        if (val is not None):
                            unpacked = s2t(session, val)
                            tempTermId = unpacked[0]
                            unpacked = mt(session, unpacked, currData, 'add',
                                          nRecs=totalRecs, nOccs=totalOccs)
                            totalRecs = unpacked[1]
                            totalOccs = unpacked[2]
                            unpacked = unpacked[3:]
                            termid -= 1
                        else:
                            tempTermId = termid
                            unpacked = currData
                        packed = t2s(session, tempTermId, unpacked,
                                     nRecs=totalRecs, nOccs=totalOccs)
                    else:
                        tempTermId = termid
                        try:
                            packed = t2s(session, termid, currData,
                                         nRecs=totalRecs, nOccs=totalOccs)
                        except:
                            raise

                    if totalRecs >= minTerms:
                        nTerms += 1
                        nRecs += totalRecs
                        nOccs += totalOccs
                        totalChars += len(currTerm)
                        maxNRecs = max(maxNRecs, totalRecs)
                        maxNOccs = max(maxNOccs, totalOccs)
                        cxn.put(currTerm, packed)
                        del packed
                        if (vectors or termIds) and tempTermId == termid:
                            tidcxn.put("%012d" % termid, currTerm)
                    else:
                        # cheat and undo our term increment
                        termid -= 1
                try:
                    totalOccs = fullinfo[2]
                    termid += 1
                    currTerm = term
                    currData = fullinfo
                    totalRecs = 1
                except:
                    pass

        self._closeIndex(session, index)
        os.remove(filePath)

        if metadataCxn:
            # LLLLLL:  nTerms, nRecs, nOccs, maxRecs, maxOccs, totalChars
            val = struct.pack("<LLLLLL", nTerms, nRecs, nOccs,
                              maxNRecs, maxNOccs, totalChars)
            metadataCxn.put(index.id.encode('utf8'), val)
            self._closeMetadata(session)

        if vectors or termIds:
            tidcxn.close()
            self.termIdCxn[index] = None
            del tidcxn

        if vectors:
            self._buildVectors(session, index, filePath[:-4] + "TEMP")

        fl = index.get_setting(session, 'freqList', "")
        if fl:
            cxn = self._openIndex(session, index)
            cursor = cxn.cursor()
            dataLen = index.longStructSize * self.reservedLongs
            terms = []

            try:
                (term, val) = cursor.first(doff=0, dlen=dataLen)
                while (val):
                    (termid, recs, occs) = struct.unpack('<lll', val)
                    terms.append({'i': termid, 'r': recs, 'o': occs})
                    try:
                        (term, val) = cursor.next(doff=0, dlen=dataLen)
                    except:
                        val = 0
                lt = len(terms)
                if fl.find('rec') > -1:
                    # 1 = most frequent
                    terms.sort(key=lambda x: x['r'], reverse=True)

                    cxn = self._openTermFreq(session, index, 'rec')
                    for (t, term) in enumerate(terms):
                        termidstr = struct.pack('<ll', term['i'], term['r'])
                        cxn.put("%012d" % t, termidstr)
                    self._closeTermFreq(session, index, 'rec')

                if fl.find('occ') > -1:
                    terms.sort(key=lambda x: x['o'], reverse=True)
                    cxn = self._openTermFreq(session, index, 'occ')
                    #cxn = bdb.db.DB()
                    #cxn.open(dbname + "_FREQ_OCC")
                    for (t, term) in enumerate(terms):
                        termidstr = struct.pack('<ll', term['i'], term['o'])
                        cxn.put("%012d" % t, termidstr)
                    self._closeTermFreq(session, index, 'occ')

            except TypeError:
                # no data in index
                pass
            self._closeIndex(session, index)

        return None

    def _buildVectors(self, session, index, filePath):
        # build vectors here
        termCache = {}
        freqCache = {}
        maxCacheSize = index.get_setting(session,
                                         'maxVectorCacheSize', -1)
        if maxCacheSize == -1:
            maxCacheSize = self.get_setting(session,
                                            'maxVectorCacheSize', 50000)

        rand = random.Random()

        # Settings for what to go into vector store
        # -1 for just put everything in
        minGlobalFreq = int(index.get_setting(session,
                                              'vectorMinGlobalFreq', '-1'))
        maxGlobalFreq = int(index.get_setting(session,
                                              'vectorMaxGlobalFreq', '-1'))
        minGlobalOccs = int(index.get_setting(session,
                                              'vectorMinGlobalOccs', '-1'))
        maxGlobalOccs = int(index.get_setting(session,
                                              'vectorMaxGlobalOccs', '-1'))
        minLocalFreq = int(index.get_setting(session,
                                             'vectorMinLocalFreq', '-1'))
        maxLocalFreq = int(index.get_setting(session,
                                             'vectorMaxLocalFreq', '-1'))

        proxVectors = index.get_setting(session, 'proxVectors', 0)

        # Temp filepath
        base = filePath
        fh = codecs.open(base, 'r', 'utf-8', 'xmlcharrefreplace')
        # Read in each line, look up
        currDoc = "000000000000"
        currStore = "0"
        docArray = []
        proxHash = {}

        cxn = self.vectorCxn.get(index, None)
        if cxn is None:
            self._openVectors(session, index)
            cxn = self.vectorCxn[index]
        if proxVectors:
            proxCxn = self.proxVectorCxn[index]

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
                fmt = '<' + "L" * len(flat)
                packed = struct.pack(fmt, *flat)
                cxn.put(str("%s|%s" % (currStore, currDoc.encode('utf8'))),
                        packed)
                docArray = []
                if proxVectors:
                    pdocid = long(currDoc)
                    for (elem, parr) in proxHash.iteritems():
                        proxKey = struct.pack('<LL', pdocid, elem)
                        if elem < 0 or elem > 4294967295:
                            raise ValueError(elem)

                        proxKey = "%s|%s" % (currStore.encode('utf8'), proxKey)
                        parr.sort()
                        flat = []
                        [flat.extend(x) for x in parr]
                        proxVal = struct.pack('<' + 'L' * len(flat), *flat)
                        proxCxn.put(proxKey, proxVal)
                    proxHash = {}
            currDoc = docid
            currStore = storeid
            tid = termCache.get(term, None)
            if tid is None:
                if not term:
                    #???
                    continue
                tdata = self.fetch_term(session, index, term, summary=True)
                if tdata:
                    try:
                        (tid, tdocs, tfreq) = tdata[:3]
                    except:
                        msg = u"Broken: %r %r %r" % (term, index.id, tdata)
                        self.log_critical(session, msg.encode('utf-8'))
                        raise
                else:
                    termCache[term] = (0, 0)
                    freqCache[term] = (0, 0)
                    continue
                termCache[term] = tid
                freqCache[term] = [tdocs, tfreq]
                # check caches aren't exploding
                ltc = len(termCache)
                if ltc >= maxCacheSize:
                    # select random key to remove
                    (k, v) = termCache.popitem()
                    del freqCache[k]
            else:
                (tdocs, tfreq) = freqCache[term]
                if not tdocs or not tfreq:
                    continue
            if (
                (minGlobalFreq == -1 or tdocs >= minGlobalFreq) and
                (maxGlobalFreq == -1 or tdocs <= maxGlobalFreq) and
                (minGlobalOccs == -1 or tfreq >= minGlobalOccs) and
                (maxGlobalOccs == -1 or tfreq <= maxGlobalOccs) and
                (minLocalFreq == -1 or tfreq >= minLocalFreq) and
                (maxLocalFreq == -1 or tfreq <= maxLocalFreq)
            ):
                docArray.append([tid, long(freq)])
                totalTerms += 1
                totalFreq += long(freq)
            if proxVectors:
                nProxInts = index.get_setting(session, 'nProxInts', 2)
                proxInfo = [long(x) for x in bits[4:]]
                tups = [proxInfo[x:x + nProxInts]
                        for x
                        in range(0, len(proxInfo), nProxInts)
                        ]
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
            fmt = '<' + "L" * len(flat)
            packed = struct.pack(fmt, *flat)
            cxn.put(str("%s|%s" % (storeid, docid.encode('utf8'))), packed)
            if proxVectors:
                pdocid = long(currDoc)
                for (elem, parr) in proxHash.iteritems():
                    proxKey = struct.pack('<LL', pdocid, elem)
                    proxKey = "%s|%s" % (storeid.encode('utf8'), proxKey)
                    parr.sort()
                    flat = []
                    [flat.extend(x) for x in parr]
                    proxVal = struct.pack('<' + 'L' * len(flat), *flat)
                    proxCxn.put(proxKey, proxVal)
                proxCxn.close()
                self.proxVectorCxn[index] = None
                del proxCxn
        fh.close()
        cxn.close()
        os.remove(base)

    def _closeVectors(self, session, index):
        for cxnx in [self.termIdCxn, self.vectorCxn, self.proxVectorCxn]:
            try:
                cxnx[index].close()
            except KeyError:
                continue

            del cxnx[index]

    def _openVectors(self, session, index):

        dfp = self.get_path(session, 'defaultPath')
        basename = self._generateFilename(index)
        dbname = os.path.join(dfp, basename)

        dbp = dbname + "_TERMIDS"
        if self.vectorSwitching:
            vbt = self.get_setting(session, 'vectorBucketType', '')
            vmb = self.get_setting(session, 'vectorMaxBuckets', 0)
            vmi = self.get_setting(session, 'vectorMaxItemsPerBucket', 0)
            cxn = self.vectorSwitchingClass(
                session, self, dbp,
                bucketType=vbt, maxBuckets=vmb, maxItemsPerBucket=vmi
            )
        else:
            cxn = bdb.db.DB()

        cxn.open(dbp)
        self.termIdCxn[index] = cxn

        if index.get_setting(session, 'vectors'):
            dbp = dbname + "_VECTORS"
            if self.vectorSwitching:
                cxn = self.vectorSwitchingClass(
                    session, self, dbp,
                    bucketType=vbt, maxBuckets=vmb, maxItemsPerBucket=vmi
                )
            else:
                cxn = bdb.db.DB()
            cxn.open(dbp)
            self.vectorCxn[index] = cxn

        if index.get_setting(session, 'proxVectors'):
            dbp = dbname + "_PROXVECTORS"
            if self.vectorSwitching:
                cxn = self.vectorSwitchingClass(session, self, dbp,
                                                bucketType=vbt, maxBuckets=vmb,
                                                maxItemsPerBucket=vmi)
            else:
                cxn = bdb.db.DB()
            cxn.open(dbp)
            self.proxVectorCxn[index] = cxn

    def fetch_vector(self, session, index, rec, summary=False):
        # rec can be resultSetItem or record

        tidcxn = self.termIdCxn.get(index, None)
        if tidcxn is None:
            self._openVectors(session, index)
            tidcxn = self.termIdCxn.get(index, None)
            cxn = self.vectorCxn.get(index, None)
        else:
            cxn = self.vectorCxn[index]

        docid = rec.id
        if (not type(docid) in NumTypes):
            if (isinstance(docid, basestring) and docid.isdigit()):
                docid = long(docid)
            else:
                # Look up identifier in local bdb
                docid = self._get_internalId(session, rec)
        docid = "%012d" % docid
        # now add in store
        docid = "%s|%s" % (self.storeHashReverse[rec.recordStore], docid)

        if summary:
            data = cxn.get(docid, doff=0, dlen=(2 * index.longStructSize))
        else:
            data = cxn.get(docid)
        if data:
            flat = struct.unpack(
                '<' + 'L' * (len(data) / index.longStructSize),
                data
            )
            lf = len(flat)
            unflatten = [(flat[x], flat[x + 1]) for x in xrange(0, lf, 2)]
            # totalTerms, totalFreq, [(termId, freq),...]
            lu = lf / 2
            return [lu, sum([x[1] for x in unflatten]), unflatten]
        else:
            return [0, 0, []]

    def fetch_proxVector(self, session, index, rec, elemId=-1):
        """Fetch and return the proximity vector.

        Fetch proximity vector for rec from index.
        rec can be resultSetItem or record
        """

        cxn = self.proxVectorCxn.get(index, None)
        if cxn is None:
            self._openVectors(session, index)
            cxn = self.proxVectorCxn.get(index, None)

        docid = rec.id
        if (not type(docid) in NumTypes):
            if (isinstance(docid, basestring) and docid.isdigit()):
                docid = long(docid)
            else:
                # Look up identifier in local bdb
                docid = self._get_internalId(session, rec)

        nProxInts = index.get_setting(session, 'nProxInts', 2)
        longStructSize = index.longStructSize

        def unpack(data):
            flat = struct.unpack(
                '<' + 'L' * (len(data) / longStructSize),
                data
            )
            lf = len(flat)
            unflat = [flat[x:x + nProxInts] for x in range(0, lf, nProxInts)]
            return unflat

        if elemId == -1:
            # fetch all for this record
            key = struct.pack('<LL', docid, 0)
            keyid = key[:4]
            key = str(self.storeHashReverse[rec.recordStore]) + "|" + key
            c = cxn.cursor()
            (k, v) = c.set_range(key)
            vals = {}
            # XXX won't work for > 9 recordStores...
            while k[2:6] == keyid:
                elemId = struct.unpack('<L', k[6:])[0]
                vals[elemId] = unpack(v)
                try:
                    (k, v) = c.next()
                except TypeError:
                    break
            return vals

        else:
            key = struct.pack('<LL', docid, elemId)
            # now add in store
            key = str(self.storeHashReverse[rec.recordStore]) + "|" + key
            data = cxn.get(key)
            if data:
                return unpack(data)
            else:
                return []

    def fetch_termById(self, session, index, termId):
        tidcxn = self.termIdCxn.get(index, None)
        if tidcxn is None:
            self._openVectors(session, index)
            tidcxn = self.termIdCxn.get(index, None)
        termid = "%012d" % termId
        data = tidcxn.get(termid)
        if type(data) == tuple and data[0] == termid:
            data = data[1]
        if not data:
            return ""
        else:
            return data

    def _closeTermFreq(self, session, index, which):
        try:
            cxns = self.termFreqCxn[index]
        except KeyError:
            return
        try:
            cxns[which].close()
        except KeyError:
            return
        del self.termFreqCxn[index][which]

    def _openTermFreq(self, session, index, which):
        fl = index.get_setting(session, "freqList", "")
        if fl.find(which) == -1:
            return None

        cxns = self.termFreqCxn.get(index, {})
        tfcxn = cxns.get(which, None)
        if tfcxn is not None:
            return tfcxn

        dfp = self.get_path(session, 'defaultPath')
        basename = self._generateFilename(index)
        dbname = os.path.join(dfp, basename)
        dbp = dbname + "_FREQ_" + which.upper()

        if self.vectorSwitching:
            vbt = self.get_setting(session, 'vectorBucketType', '')
            vmb = self.get_setting(session, 'vectorMaxBuckets', 0)
            vmi = self.get_setting(session, 'vectorMaxItemsPerBucket', 0)
            tfcxn = self.vectorSwitchingClass(
                session, self, dbp,
                bucketType=vbt, maxBuckets=vmb, vectorMaxItemsPerBucket=vmi
            )
        else:
            tfcxn = bdb.db.DB()
        if which == 'rec':
            tfcxn.open(dbp)
            if cxns == {}:
                self.termFreqCxn[index] = {'rec': tfcxn}
            else:
                self.termFreqCxn[index]['rec'] = tfcxn
        elif which == 'occ':
            tfcxn.open(dbp)
            if cxns == {}:
                self.termFreqCxn[index] = {'occ': tfcxn}
            else:
                self.termFreqCxn[index]['occ'] = tfcxn
        return tfcxn

    def fetch_termFrequencies(self, session, index, mType='occ',
                              start=0, nTerms=100, direction=">"):
        cxn = self._openTermFreq(session, index, mType)
        if cxn is None:
            return []
        else:
            c = cxn.cursor()
            freqs = []

            if start < 0:
                # go to end and reverse
                (t, v) = c.last()
                if start != -1:
                    slot = int(t) + start + 1
                    (t, v) = c.set_range("%012d" % slot)
            elif start == 0:
                (t, v) = c.first()
            else:
                (t, v) = c.set_range("%012d" % start)
            if direction[0] == "<":
                next = c.prev
            else:
                next = c.next
            while len(freqs) < nTerms:
                (tid, fr) = struct.unpack('<ll', v)
                freqs.append((int(t), tid, fr))
                try:
                    (t, v) = next()
                except TypeError:
                    break
            return freqs

    def fetch_indexMetadata(self, session, index):
        cxn = self._openMetadata(session)
        data = cxn.get(index.id.encode('utf-8'))
        if data:
            # LLLLLL:  nTerms, nRecs, nOccs, maxRecs, maxOccs, totalChars
            keys = ('nTerms', 'nRecs', 'nOccs',
                    'maxRecs', 'maxOccs', 'totalChars')
            vals = struct.unpack('<LLLLLL', data)
            return dict(zip(keys, vals))
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
            unpacked.extend([item.id, self.storeHashReverse[item.recordStore],
                             item.occurences])
        packed = index.serialize_term(session, termId, unpacked,
                                      nRecs=totalRecs, nOccs=totalOccs)
        cxn = self._openIndex(session, index)
        cxn.put(term, packed)
        # NB: need to remember to close index manually

    def contains_index(self, session, index):
        # Send Index object, check exists, return boolean
        dfp = self.get_path(session, "defaultPath")
        name = self._generateFilename(index)
        return os.path.exists(os.path.join(dfp, name))

    def _create(self, session, dbname, flags=[], vectorType=1):
        # for use by self.create_index
        if os.path.exists(dbname):
            raise FileAlreadyExistsException(dbname)
        if vectorType == 0 and self.switching:
            cxn = self.switchingClass(session, self, dbname)
        elif vectorType and self.vectorSwitching:
            dbp = dbname + "_VECTORS"
            vbt = self.get_setting(session, 'vectorBucketType', '')
            vmb = self.get_setting(session, 'vectorMaxBuckets', 0)
            vmi = self.get_setting(session, 'vectorMaxItemsPerBucket', 0)
            cxn = self.vectorSwitchingClass(
                session, self, dbp,
                bucketType=vbt, maxBuckets=vmb, maxItemsPerBucket=vmi
            )
        else:
            cxn = bdb.db.DB()

        for f in flags:
            cxn.set_flags(f)
        try:
            cxn.open(dbname,
                     dbtype=bdb.db.DB_BTREE,
                     flags=bdb.db.DB_CREATE,
                     mode=0660
                     )
        except:
            raise ConfigFileException(dbname)
        else:
            cxn.close()

    def create_index(self, session, index):
        # Send Index object to create, null return
        p = self.permissionHandlers.get('info:srw/operation/1/create', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to create index in "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to create index in %s" % self.id
                raise PermissionException(msg)

        dfp = self.get_path(session, "defaultPath")
        if self.dirPerIndex:
            idp = os.path.join(dfp, index.id)
            if not os.path.exists(idp):
                os.mkdir(idp)

        name = self._generateFilename(index)
        fullname = os.path.join(dfp, name)
        try:
            self._create(session, fullname, vectorType=0)
        except FileAlreadyExistsException:
            pass

        if (index.get_setting(session, "sortStore")):
            try:
                self._create(session, fullname + "_VALUES")
            except FileAlreadyExistsException:
                pass

        vecs = index.get_setting(session, "vectors")
        tids = index.get_setting(session, "termIds")
        if vecs or tids:
            try:
                self._create(session, fullname + "_TERMIDS",
                             flags=[bdb.db.DB_RECNUM])
            except FileAlreadyExistsException:
                pass

        if vecs:
            try:
                try:
                    self._create(session, fullname + "_VECTORS",
                                 flags=[bdb.db.DB_RECNUM])
                except FileAlreadyExistsException:
                    pass

                if index.get_setting(session, 'proxVectors'):
                    try:
                        self._create(session, fullname + "_PROXVECTORS",
                                     flags=[bdb.db.DB_RECNUM])
                    except FileAlreadyExistsException:
                        pass

            except:
                raise(ValueError)
        fl = index.get_setting(session, "freqList", "")
        if fl:
            if fl.find('rec') > -1:
                try:
                    self._create(session, fullname + "_FREQ_REC",
                                 flags=[bdb.db.DB_RECNUM])
                except FileAlreadyExistsException:
                    pass

            if fl.find('occ') > -1:
                try:
                    self._create(session, fullname + "_FREQ_OCC",
                                 flags=[bdb.db.DB_RECNUM])
                except FileAlreadyExistsException:
                    pass

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
                msg = ("Authenticated user required to delete index from "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to delete index from %s" % self.id
                raise PermissionException(msg)

        for dbname in self._listExistingFiles(session, index):
            os.remove(dbname)

        return 1

    def _openSortStore(self, session, index):
        if (not index.get_setting(session, 'sortStore')):
            raise FileDoesNotExistException()
        cxn = self.sortStoreCxn.get(index, None)
        if cxn:
            return cxn

        dfp = self.get_path(session, "defaultPath")
        name = self._generateFilename(index) + "_VALUES"
        fullname = os.path.join(dfp, name)
        if self.vectorSwitching:
            pass
        else:
            cxn = bdb.db.DB()
        if session.environment == "apache":
            cxn.open(fullname, flags=bdb.db.DB_NOMMAP)
        else:
            cxn.open(fullname)
        self.sortStoreCxn[index] = cxn
        return cxn

    def fetch_sortValue(self, session, index, rec, lowest=True):
        try:
            cxn = self.sortStoreCxn[index]
        except:
            cxn = self._openSortStore(session, index)

        val = cxn.get("%s/%s" % (str(rec.recordStore), rec.id))
        if val is None:
            val = cxn.get("%s/%s" % (str(rec.recordStore), rec.numericId))
        if val is None:
            # Missing value
            return val
        # Split value at non-text token
        values = val.split('\0')
        if lowest:
            return values[0]
        else:
            return values[-1]

    def store_terms(self, session, index, terms, rec):
        # Store terms from hash
        # Need to store:
        # term, totalOccs, totalRecs,
        #     (record id, recordStore id, number of occs in record)
        # hash is now {tokenA:tokenA, ...}

        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to add to indexStore "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to add to indexStore %s" % self.id
                raise PermissionException(msg)

        if (not terms):
            # No terms to index
            return

        storeid = rec.recordStore
        if (not type(storeid) in NumTypes):
            # Map
            if (storeid in self.storeHashReverse):
                storeid = self.storeHashReverse[storeid]
            else:
                # YYY: Error or metadata store?
                numeric_storeid = len(self.storeHash.keys())
                self.storeHashReverse[storeid] = numeric_storeid
                self.storeHash[numeric_storeid] = storeid
                msg = ("indexStore %s does not recognise recordStore: "
                       "%s" % (self.id, storeid))
                raise ConfigFileException(msg)

        docid = rec.id
        if (not type(docid) in NumTypes):
            if (isinstance(docid, basestring) and docid.isdigit()):
                docid = long(docid)
            else:
                # Look up identifier in local bdb
                docid = self._get_internalId(session, rec)
        elif (docid == -1):
            # Unstored record
            raise ValueError(str(rec))

        if index in self.outFiles:
            # Batch loading
            if (index in self.sortStoreCxn):
                # Concatenate lowest and highest values, separated by a
                # non-text tokento enable ascending and descending sort

                # Fetch existing values
                existingVal = self.sortStoreCxn[index].get(
                    "%s/%s" % (str(rec.recordStore), docid)
                )
                if existingVal:
                    sortVals = existingVal.split('\0')
                else:
                    sortVals = []
                for valueHash in terms.itervalues():
                    if 'sortValue' in valueHash:
                        sortVal = valueHash['sortValue']
                    else:
                        sortVal = valueHash['text']

                    if type(sortVal) == unicode:
                        sortVal = sortVal.encode('utf-8')
                    sortVals.append(sortVal)
                # Sort the combined list
                sortVals.sort()
                # Concatenate lowest and highest values
                self.sortStoreCxn[index].put(
                    "%s/%s" % (str(rec.recordStore), docid),
                    sortVals[0] + '\0' + sortVals[-1]
                )

            valueHash = terms.values()[0]
            value = valueHash['text']
            prox = 'positions' in terms[value]
            for k in terms.values():
                kw = k['text']
                if type(kw) != unicode:
                    try:
                        try:
                            kw = kw.decode('utf-8')
                        except AttributeError:
                            # kw is not a unicode object
                            # Maybe it's an integer, e.g. wordCount, byteCount
                            kw = unicode(kw).decode('utf-8')
                    except:
                        msg = u"%s failed to decode %s" % (self.id, repr(kw))
                        self.log_critical(session, msg.encode('utf-8'))
                        raise
                self.outFiles[index].write(kw)
                # ensure that docids are sorted to numeric order
                lineList = ["",
                            "%012d" % docid,
                            str(storeid),
                            str(k['occurences'])]
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
                if (val is not None):
                    current = index.deserialize_term(session, val)
                    unpacked = index.merge_term(session, current, stuff,
                                                op="replace", nRecs=1,
                                                nOccs=k['occurences'])
                    (termid, totalRecs, totalOccs) = unpacked[:3]
                    unpacked = unpacked[3:]
                else:
                    vecs = index.get_setting(session, "vectors")
                    tids = index.get_setting(session, "termIds")
                    tidcxn = None
                    if vecs or tids:
                        tidcxn = self.termIdCxn.get(index, None)
                        if tidcxn is None:
                            self._openVectors(session, index)
                            tidcxn = self.termIdCxn.get(index, None)
                    if tidcxn is None:
                        # Okay, no termid hash. hope for best with final set
                        # of terms from regular index
                        cursor = cxn.cursor()
                        (term, value) = cursor.last(
                            doff=0,
                            dlen=(3 * index.longStructSize)
                        )
                        (last, x, y) = index.deserialize_term(session, value)
                    else:
                        tidcursor = tidcxn.cursor()
                        (finaltid, term) = tidcursor.last()
                        last = long(finaltid)

                    termid = last + 1
                    unpacked = stuff
                    totalRecs = 1
                    totalOccs = k['occurences']

                packed = index.serialize_term(session, termid, unpacked,
                                              nRecs=totalRecs, nOccs=totalOccs)
                cxn.put(key.encode('utf-8'), packed)
            self._closeIndex(session, index)

    def delete_terms(self, session, index, terms, rec):
        p = self.permissionHandlers.get('info:srw/operation/2/unindex', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to delete from indexStore"
                       " %s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = ("Permission required to delete from indexStore "
                       "%s" % self.id)
                raise PermissionException(msg)
        if not terms:
            return

        docid = rec.id
        # Hash
        if (isinstance(docid, basestring) and docid.isdigit()):
            docid = long(docid)
        elif (type(docid) in NumTypes):
            pass
        else:
            # Look up identifier in local bdb
            docid = self._get_internalId(session, rec)

        storeid = rec.recordStore
        if (not type(storeid) in NumTypes):
            # Map
            if (storeid in self.storeHashReverse):
                storeid = self.storeHashReverse[storeid]
            else:
                # YYY: Error or metadata store?
                self.storeHashReverse[storeid] = len(self.storeHash.keys())
                self.storeHash[self.storeHashReverse[storeid]] = storeid
                storeid = self.storeHashReverse[storeid]
                msg = ("indexStore %s does not recognise recordStore: "
                       "%s" % (self.id, storeid))
                raise ConfigFileException(msg)

            # Directly insert into index
            cxn = self._openIndex(session, index)

            for k in terms.keys():
                val = cxn.get(k.encode('utf-8'))
                if (val is not None):
                    current = index.deserialize_term(session, val)
                    gone = [docid, storeid, terms[k]['occurences']]
                    unpacked = index.merge_term(session, current,
                                                gone, 'delete')
                    if not unpacked[1]:
                        # all terms deleted
                        cxn.delete(k.encode('utf-8'))
                    else:
                        packed = index.serialize_term(session, current[0],
                                                      unpacked[3:])
                        cxn.put(k.encode('utf-8'), packed)
            self._closeIndex(session, index)

    # NB:  c.set_range('a', dlen=12, doff=0)
    # --> (key, 12bytestring)
    # --> unpack for termid, docs, occs

    def fetch_termList(self, session, index, term,
                       nTerms=0, relation="", end="", summary=0, reverse=0):
        p = self.permissionHandlers.get('info:srw/operation/2/scan', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to scan indexStore "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to scan indexStore %s" % self.id
                raise PermissionException(msg)

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

            if self.switching:
                vbt = index.get_setting(session, 'bucketType', '')
                vmb = index.get_setting(session, 'maxBuckets', 0)
                vmi = index.get_setting(session, 'maxItemsPerBucket', 0)
                if vbt or vmb or vmi:
                    cxn = self.switchingClass(
                        session, self, fullname,
                        bucketType=vbt, maxBuckets=vmb, maxItemsPerBucket=vmi
                    )
                else:
                    cxn = self.switchingClass(session, self, fullname)

            else:
                cxn = bdb.db.DB()
            if session.environment == "apache":
                cxn.open(fullname, flags=bdb.db.DB_NOMMAP)
            else:
                cxn.open(fullname)
        else:
            cxn = self._openIndex(session, index)

        dataLen = index.longStructSize * self.reservedLongs

        c = cxn.cursor()
        if not term:
            # Special escape for first term (i.e. empty string)
            term = c.first()[0]
        else:
            term = term.encode('utf-8')
        try:
            if summary:
                (key, data) = c.set_range(term, dlen=dataLen, doff=0)
            else:
                (key, data) = c.set_range(term)
        except Exception as e:
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
        if (end and relation in ['>', '>='] and key > end):
            return []
        elif (end and relation in ['<', '<='] and key < end):
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
                elif (end and dir == "<" and key <= end):
                    fetching = 0
                else:
                    unpacked = index.deserialize_term(session, rec)
                    if reverse:
                        key = key[::-1]
                    tlist.append([key.decode('utf-8'), unpacked])
                    if (nTerms and len(tlist) == nTerms):
                        fetching = 0
                        if dir == '<':
                            fltup = c.prev(dlen=dataLen, doff=0)
                            if not fltup:
                                tlist[-1].append('first')
                        else:
                            fltup = c.next(dlen=dataLen, doff=0)
                            if not fltup:
                                tlist[-1].append('last')

            else:
                if tlist:
                    if (dir == ">"):
                        tlist[-1].append("last")
                    else:
                        tlist[-1].append("first")
                key = None
                fetching = 0

        return tlist

    def construct_resultSetItem(self, session, recId, recStoreId, nOccs,
                                rsiType="SimpleResultSetItem"):
        recStore = self.storeHash[recStoreId]
        if self.identifierMapCxn and recStore in self.identifierMapCxn:
            numericId = recId
            recId = self._get_externalId(session, recStore, numericId)
        else:
            numericId = None

        if rsiType == "SimpleResultSetItem":
            return SimpleResultSetItem(session, recId, recStore,
                                       nOccs, session.database,
                                       numeric=numericId)
        elif rsiType == "Hash":
            return ("%s/%s" % (recStore, recId),
                    {"recordStore": recStore,
                     "recordId": recId,
                     "occurences": nOccs,
                     "database": session.database})
        else:
            raise NotImplementedError(rsiType)

    def fetch_term(self, session, index, term, summary=False, prox=True):
        p = self.permissionHandlers.get('info:srw/operation/2/search', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to search indexStore "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to search indexStore %s" % self.id
                raise PermissionException(msg)
        unpacked = []
        val = self._fetch_packed(session, index, term, summary)
        if (val is not None):
            try:
                unpacked = index.deserialize_term(session, val, prox=prox)
            except:
                msg = (u"{0} failed to deserialise {1} {2} {3}"
                       u"".format(self.id, index.id, term, val)
                       )
                self.log_critical(session, msg.encode('utf-8'))
                raise
        return unpacked

    def _fetch_packed(self, session, index, term,
                      summary=False, numReq=0, start=0):
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
            offsets = index.calc_sectionOffsets(session, start,
                                                numReq, fulllen)
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
