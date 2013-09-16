from __future__ import with_statement

import os
import time
import hashlib
import bsddb as bdb
import datetime
import dateutil.tz
import shutil

from urllib import quote, unquote
from urlparse import urlsplit

try:
    import cPickle as pickle
except ImportError:
    import pickle

from dateutil import parser as dateparser

from cheshire3.exceptions import *
from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Session
from cheshire3.utils import gen_uuid


class DeletedObject(object):
    id = ""
    time = ""
    store = ""
    
    def __nonzero__(self):
        return False

    def __init__(self, store, id, time="unknown"):
        self.store = store
        self.id = id
        self.time = time

        
class SummaryObject(object):
    """ Allow database to have summary, but no storage """

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
        'metadataPath': {
            'docs': "Path to file where the summary metadata will be kept."
        }
    }

    def __init__(self, session, config, parent):
        # Don't want to inherit from database!
        mp = self.paths.get('metadataPath', '')
        if not mp:
            self.paths['metadataPath'] = ''
            return
        if not (urlsplit(mp).scheme or os.path.isabs(mp)):
            # Prepend defaultPath from parents
            dfp = self.get_path(session, 'defaultPath')
            if (not dfp):
                msg = ("Store has relative metadata path, and no visible "
                       "defaultPath.")
                raise ConfigFileException(msg)
            elif urlsplit(dfp).scheme:
                # Default path is a URL
                mp = '/'.join((dfp, mp))
            else:
                mp = os.path.join(dfp, mp)
        self.paths['metadataPath'] = mp
        if (not os.path.exists(mp)):
            # We don't exist, try and instantiate new database
            self._create(session, mp)
        else:
            cxn = bdb.db.DB()
            try:
                cxn.open(mp)
                # Now load values.
                self.totalItems = long(cxn.get("totalItems"))
                self.totalWordCount = long(cxn.get("totalWordCount"))
                self.minWordCount = long(cxn.get("minWordCount"))
                self.maxWordCount = long(cxn.get("maxWordCount"))

                self.totalByteCount = long(cxn.get("totalByteCount"))
                self.minByteCount = long(cxn.get("minByteCount"))
                self.maxByteCount = long(cxn.get("maxByteCount"))

                self.lastModified = str(cxn.get("lastModified"))

                if self.totalItems != 0:
                    self.meanWordCount = self.totalWordCount / self.totalItems
                    self.meanByteCount = self.totalByteCount / self.totalItems
                else:
                    self.meanWordCount = 1
                    self.meanByteCount = 1
                cxn.close()
            except:
                # Doesn't exist in usable form
                self._create(session, mp)

    def _initDb(self, session, dbt):
            dbp = dbt + "Path"
            databasePath = self.get_path(session, dbp, "")
            if (not databasePath):
                databasePath = ''.join([self.id, "_", dbt, ".bdb"])
            if (not os.path.isabs(databasePath)):
                # Prepend defaultPath from parents
                dfp = self.get_path(session, 'defaultPath')
                if not dfp:
                    msg = ("Store has relative path, and no visible "
                           "defaultPath.")
                    raise ConfigFileException(msg)
                databasePath = os.path.join(dfp, databasePath)
            self.paths[dbp] = databasePath
                    
    def _create(self, session, dbPath):
        cxn = bdb.db.DB()
        cxn.set_flags(bdb.db.DB_RECNUM)
        try:
            cxn.open(dbPath, dbtype=bdb.db.DB_BTREE,
                     flags=bdb.db.DB_CREATE, mode=0660)
        except:
            raise ValueError("Could not create %s" % dbPath)
        cxn.put("lastModified", time.strftime('%Y-%m-%d %H:%M:%S'))
        cxn.close()

    def commit_metadata(self, session):
        cxn = bdb.db.DB()
        mp = self.get_path(session, 'metadataPath')
        if mp:
            try:
                self.meanWordCount = self.totalWordCount / self.totalItems
                self.meanByteCount = self.totalByteCount / self.totalItems
            except ZeroDivisionError:
                self.meanWordCount = 1
                self.meanByteCount = 1
                
            self.lastModified = time.strftime('%Y-%m-%d %H:%M:%S')
            try:
                cxn.open(mp)
                cxn.put("totalItems", str(self.totalItems))
                cxn.put("totalWordCount", str(self.totalWordCount))
                cxn.put("minWordCount", str(self.minWordCount))
                cxn.put("maxWordCount", str(self.maxWordCount))
                cxn.put("totalByteCount", str(self.totalByteCount))
                cxn.put("minByteCount", str(self.minByteCount))
                cxn.put("maxByteCount", str(self.maxByteCount))
                cxn.put("lastModified", self.lastModified)
                cxn.close()
            except:
                # TODO: Nicer failure?
                raise

    def accumulate_metadata(self, session, obj):
        self.totalItems += 1
        self.totalWordCount += obj.wordCount
        if obj.wordCount < self.minWordCount:
            self.minWordCount = obj.wordCount
        if obj.wordCount > self.maxWordCount:
            self.maxWordCount = obj.wordCount

        self.totalByteCount += obj.byteCount
        if obj.byteCount < self.minByteCount:
            self.minByteCount = obj.byteCount
        if obj.byteCount > self.maxByteCount:
            self.maxByteCount = obj.byteCount


class SimpleStore(C3Object, SummaryObject):
    """ Base Store implementation.  Provides non-storage-specific functions """
    
    # Instantiate some type of simple record store
    idNormalizer = None
    outIdNormalizer = None
    inWorkflow = None
    outWorkflow = None
    storageTypes = []
    reverseMetadataTypes = []
    currentId = -1
    useUUID = 0
    session = None
    switching = 0

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
            'docs': ("Workflow with which to process stored data objects "
                     "when requested.")
        }
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
        'bucketType': {
            'docs': ("Type of 'bucket' to use when splitting an index over "
                     "multiple files."),
        },
        'maxBuckets': {
            'docs': "Maximum number of 'buckets' to split an index into",
            'type': int
        },
        'maxItemsPerBucket': {
            'docs': "Maximum number of items to put into each 'bucket'",
            'type': int
        },
    }

    _possibleDefaults = {
        'expires': {
            "docs": ('Default time after ingestion at which to delete the '
                     'data object in number of seconds. Can be overridden by '
                     'the individual object.'),
            'type': int
        }
    }
    
    def __init__(self, session, config, parent):
        # Don't inherit metadataPath!
        C3Object.__init__(self, session, config, parent)
        self.switching = (
            self.get_setting(session, 'bucketType', '') or \
            self.get_setting(session, 'maxBuckets', 0) or \
            self.get_setting(session, 'maxItemsPerBucket', 0))

        SummaryObject.__init__(self, session, config, parent)
        self.idNormalizer = self.get_path(session, 'idNormalizer', None)
        self.outIdNormalizer = self.get_path(session, 'outIdNormalizer', None)
        self.inWorkflow = self.get_path(session, 'inWorkflow', None)
        self.outWorkflow = self.get_path(session, 'outWorkflow', None)

        self.session = session

        dbts = self.get_storageTypes(session)
        self.storageTypes = dbts
        revdbts = self.get_reverseMetadataTypes(session)
        self.reverseMetadataTypes = revdbts

        self.useUUID = self.get_setting(session, 'useUUID', 0)
        self.expires = self.get_default(session, 'expires', 0)
        for dbt in dbts:
            self._initDb(session, dbt)
            self._verifyDb(session, dbt)
            if dbt in revdbts:
                dbt = dbt + "Reverse"
                self._initDb(session, dbt)
                self._verifyDb(session, dbt)

    def _verifyDb(self, session, dbType):
        pass

    def generate_checkSum(self, session, data):
        digest = self.get_setting(session, "digest")
        if (digest):
            if (digest == 'md5'):
                m = hashlib.md5()
            elif (digest == 'sha'):
                m = hashlib.sha1()
            else:
                raise ConfigFileException("Unknown digest type: %s" % digest)

            if type(data) == unicode:
                data = data.encode('utf-8')
            m.update(data)               
            digest = m.hexdigest()
            return digest
        else:
            return None

    def generate_expires(self, session, obj=None):
        now = time.time()
        if obj and hasattr(obj, 'expires'):            
            return now + obj.expires
        elif self.expires > 0:
            return now + self.expires
        else:
            # Don't expire
            return 0

    def _openAll(self, session):
        for t in self.storageTypes:
            self._openDb(session, t)

    def _closeAll(self, session):
        for t in self.storageTypes:
            self._closeDb(session, t)
        for t in self.reverseMetadataTypes:
            self._closeDb(session, t + "Reverse")
        for (t, cxn) in self.cxns.items():
            if cxn is not None:
                try:
                    cxn.close()
                    self.cxns[t] = None
                except:
                    pass

    def generate_id(self, session):
        """Generate and return a new unique identifier."""
        return self.get_dbSize(session)

    def get_storageTypes(self, session):
        return ['database']

    def get_reverseMetadataTypes(self, session):
        return ['digest', 'expires']
        
    def get_dbSize(self, session):
        """Return number of items in storage."""
        raise NotImplementedError

    def begin_storing(self, session):
        """Prepare to store objects."""
        self._openAll(session)
        return None

    def commit_storing(self, session):
        """Finalize storing, e.g. commit to persistent storage."""
        self._closeAll(session)
        self.commit_metadata(session)
        return None
    
    def get_idChunkGenerator(self, session, taskManager=None):
        """Generator to yield chunks of ids from the store.
        
        Can be used during parallel processing to split processing into 
        chunks to be distributed across processes or processing nodes.
        """
        # Defaults
        maxChunkSize = 1000
        maxChunkByteCount = 2048000
        maxChunkWordCount = maxChunkByteCount / 5
        chunkBy = None
        chunkThreshold = 1
        total = self.get_dbSize(session)
        if taskManager is not None:
            maxChunkSize = taskManager.get_setting(session,
                                                   'maxChunkSize',
                                                   maxChunkSize)
            chunkBy = taskManager.get_setting(session, 'chunkBy', chunkBy)
            if (chunkBy is not None) and chunkBy.isalpha():
                # Chunking based on metadata
                cmax = 'maxChunk{0}'.format(chunkBy[0].upper() + chunkBy[1:])
                chunkThreshold = taskManager.get_setting(
                                     session, 
                                     cmax,
                                     locals().get(cmax,
                                     chunkByThreshold)
                )
            else:
                # Generic chunking
                if (chunkBy is not None) and chunkBy.isdigit():
                    # chunkBy is a number of preferred times to use each chunk
                    nIters = int(chunkBy)
                else:
                    nIters = 1
                nTasks = taskManager.nTasks
                maxChunkSize = min(maxChunkSize, (total / (nIters * nTasks)))
        
        numericId = 0
        iterator = self.__iter__()
        idNormalizer = self.idNormalizer
        outIdNormalizer = self.outIdNormalizer
        while numericId < total:
            chunk = []
            chunkTotal = 0
            while (chunkTotal < chunkThreshold and
                   len(chunk) < maxChunkSize and
                   numericId < total):
                # Get real id and de-normalize if possible
                id = iterator.nextData[0]
                obj = iterator.next()  # Move iterator on
                if outIdNormalizer:
                    id = outIdNormalizer.process_string(session, id)
                # chunkBy
                if chunkBy is not None:
                    b = self.fetch_metadata(session, id, chunkBy)
                    chunkTotal += b
                chunk.append(id)
                numericId += 1
            yield chunk
                
    def delete_data(self, session, id):
        """Delete data stored against id."""
        raise NotImplementedError

    def fetch_data(self, session, id):
        """Return data stored against id."""
        raise NotImplementedError

    def store_data(self, session, id, data, metadata):
        """Store data against id."""
        raise NotImplementedError

    def fetch_metadata(self, session, id, mType):
        """Return mType metadata stored against id."""
        raise NotImplementedError

    def store_metadata(self, session, id, mType, value):
        """Store value for mType metadata against id."""
        raise NotImplementedError
    
    def clean(self, session):
        """Delete expired data objects."""
        raise NotImplementedError

    def clear(self, session):
        """This would delete all the data out of self."""
        raise NotImplementedError

    def flush(self, session):
        """Ensure all data is flushed to disk."""
        raise NotImplementedError


class BdbIter(object):
    store = None
    cursor = None
    cxn = None
    nextData = None

    def __init__(self, session, store):
        self.store = store
        self.session = session
        self.cxn = store._openDb(self.session, 'database')
        self.cursor = self.cxn.cursor()
        self.nextData = self.cursor.first()

    def __iter__(self):
        return self

    def next(self):
        try:
            d = self.nextData
            if not d:
                raise StopIteration()
            self.nextData = self.cursor.next()
            return d
        except:
            raise StopIteration()

    def jump(self, position):
        # Jump to this position
        self.nextData = self.cursor.set_range(position)
        return self.nextData[0]


class SwitchingBdbConnection(object):

    def __init__(self, session, parent, path="",
                 maxBuckets=0, maxItemsPerBucket=0, bucketType=''):
        self.session = session
        self.store = parent

        # Allow per call overrides, eg if parent object has multiple types
        if maxBuckets == 0:
            self.maxBuckets = parent.get_setting(session, 'maxBuckets', 0) 
        else:
            self.maxBuckets = maxBuckets

        if maxItemsPerBucket == 0:
            self.maxItemsPerBucket = parent.get_setting(session,
                                                        'maxItemsPerBucket',
                                                        0)
        else:
            self.maxItemsPerBucket = maxItemsPerBucket

        if bucketType == '':
            self.bucketType = parent.get_setting(session, 'bucketType', '')
        else:
            self.bucketType = bucketType

        if not self.bucketType:
            if self.maxItemsPerBucket:
                self.bucketType = 'int'
            elif self.maxBuckets:
                self.bucketType = 'hash'
            else:
                self.bucketType = 'term1'

        if os.path.isabs(path):
            self.basePath = path
        else:
            dfp = parent.get_path(session, 'defaultPath')
            basename = parent.id
            self.basePath = os.path.join(dfp, basename)        

        self.cxns = {}
        self.createArgs = {}
        self.openArgs = {}
        self.preOpenFlags = 0
        self.bucketFns = {'term1': self.termBucket1,
                          'term-1': self.termBucket_1,
                          'term2': self.termBucket2,
                          'term-2': self.termBucket_2,
                          'hash': self.hashBucket,
                          'int': self.intBucket,
                          'null': self.nullBucket}
        self.listBucketFns = {'term1': self.listTermBucket1,
                              'term-1': self.listTermBucket1,
                              'term2': self.listTermBucket2,
                              'term-2': self.listTermBucket_2,
                              'hash': self.listHashBucket,
                              'int': self.listIntBucket,
                              'null': self.listNullBucket
                              }

    def bucket_exists(self, b):
        return os.path.exists(self.basePath + '_' + b)

    def bucket(self, key):
        # bucket type and settings from parent
        fn = self.bucketFns[self.bucketType]
        return fn(key)

    def listBuckets(self):
        fn = self.listBucketFns[self.bucketType]
        return fn()

    def termBucket1(self, key):
        if not key:
            return "other"
        elif key[0].isalnum():
            return key[0].lower()
        elif key[0] > 'z':
            return 'extended'
        else:
            return "other"

    def listTermBucket1(self):
        l = ['other', 'extended']
        l.extend([str(x) for x in range(10)])
        l.extend([chr(x) for x in range(97, 123)])
        return l

    def termBucket_1(self, key):
        if not key:
            return "other"
        elif key[-1].isalnum():
            return key[-1].lower()
        elif key[-1] > 'z':
            return 'extended'
        else:
            return "other"

    def termBucket2(self, key):
        if not key:
            return "other"
        elif key[0].isdigit():
            return key[0]
        elif key[0].isalpha():
            if len(key) == 1:
                return key + "0"
            elif not key[1].isalnum():
                return key[0].lower() + '_'
            else:
                return key[:2].lower()
        else:
            return "other"

    def termBucket_2(self, key):
        if not key:
            return "other"
        elif key[-1].isdigit():
            return key[-1]
        elif key[-1].isalpha():
            if len(key) == 1:
                return '0' + key
            elif not key[-2].isalnum():
                return '_' + key[-1].lower()
            else:
                return key[-2:].lower()
        else:
            return "other"

    def listTermBucket2(self):
        lets = [chr(x) for x in range(97, 123)]
        nums = [str(x) for x in range(10)]
        all = []
        all.extend(lets)
        all.extend(nums)
        all.append('_')
        l = ['other']
        l.extend(nums)
        for let in lets:
            l.extend([let + x for x in all])
        return l

    def listTermBucket_2(self):
        # reversed order...
        lets = [chr(x) for x in range(97, 123)]
        nums = [str(x) for x in range(10)]
        all = []
        all.extend(lets)
        all.extend(nums)
        all.append('_')
        l = ['other']
        l.extend(nums)
        for let in all:
            l.extend([let + x for x in lets])
        return l

    def hashBucket(self, key):
        # Essentially random division, constrained number of buckets
        return str(hash(key) % self.maxBuckets)

    def listHashBucket(self):
        return [str(x) for x in range(self.maxBuckets)]

    def intBucket(self, key):
        # constrained number of items per bucket
        # must be integer key!  (eg internal record id)
        if not type(key) in [int, long] and not key.isdigit():
            msg = "Cannot use 'int' bucket method if keys are not numbers"
            raise ConfigFileException(msg)
        else:
            return str(long(key) / self.maxItemsPerBucket)

    def listIntBucket(self):
        # find out how many
        x = self.store.get_dbSize(self.session)
        return [str(y) for y in range((x / self.maxItemsPerBucket) + 1)]

    def nullBucket(self, key):
        # all in one bucket
        return '0'

    def listNullBucket(self):
        return ['0']

    def _open(self, b):
        if b in self.cxns and self.cxns[b] is not None:
            return self.cxns[b]
        else:
            cxn = bdb.db.DB()
            if self.preOpenFlags:
                cxn.set_flags(self.preOpenFlags)
            dbp = self.basePath + "_" + b

            if (not os.path.exists(dbp)):
                cxn.open(dbp, **self.store.createArgs[self.basePath])
                cxn.close()
                cxn = bdb.db.DB()                

            cxn.open(dbp, **self.openArgs)
            self.cxns[b] = cxn
            return cxn

    def _cursor(self, b):
        cxn = self._open(b)
        return b.cursor()

    def get(self, key, doff=-1, dlen=-1):
        # Find the correct bucket, and look in that cxn
        b = self.bucket(key)
        cxn = self._open(b)
        if doff != -1:
            return cxn.get(key, doff=doff, dlen=dlen)
        else:
            return cxn.get(key)

    def put(self, key, val):
        b = self.bucket(key)
        cxn = self._open(b)
        return cxn.put(key, val)

    def delete(self, key):
        b = self.bucket(key)
        cxn = self._open(b)
        return cxn.delete(key)

    def cursor(self):
        # create a switching cursor!
        l = self.listBuckets()
        return SwitchingBdbCursor(self, l)

    def sync(self):
        # sync all
        for c in self.cxns.itervalues():
            c.sync()
        return None

    def open(self, what, flags=0, dbtype=0, mode=0):
        # delay open until try to write
        self.basePath = what
        if flags == bdb.db.DB_CREATE:
            self.store.createArgs[what] = {'flags': flags,
                                           'dbtype': dbtype,
                                           'mode': mode}
        elif flags:
            self.openArgs = {'flags': flags}
        return None

    def close(self):
        for (k, c) in self.cxns.iteritems():
            c.close()
            self.cxns[k] = None
        return None

    def set_flags(self, f):
        self.preOpenFlags = f
        return None        


class SwitchingBdbCursor(object):
    """Cursor to handle switching between multiple BerkeleyDB connections."""

    def __init__(self, cxn, l):
        self.switch = cxn
        nl = []
        for b in l:
            if cxn.bucket_exists(b):
                nl.append(b)
        self.buckets = nl
        self.currCursor = None
        self.currBucketIdx = -1

    def set_cursor(self, b):
        try:
            idx = self.buckets.index(b)
            self.currBucketIdx = idx
        except:
            msg = "%r is not a known bucket (%r)" % (b, self.buckets)
            raise ValueError(msg)
        cxn = self.switch._open(b)
        cur = cxn.cursor()
        if self.currCursor is not None:
            self.currCursor.close()
        self.currCursor = cur
        return cur
        
    def first(self, doff=-1, dlen=-1):
        if self.currBucketIdx != 0:
            cursor = self.set_cursor(self.buckets[0])
        if dlen != -1:
            return cursor.first(doff=doff, dlen=dlen)
        else:
            return cursor.first()

    def last(self, doff=-1, dlen=-1):
        if self.currBucketIdx != len(self.buckets) - 1:
            cursor = self.set_cursor(self.buckets[-1])
        else:
            cursor = self.currCursor
        if dlen != -1:
            return cursor.last(doff=doff, dlen=dlen)
        else:
            return cursor.last()

    def next(self, doff=-1, dlen=-1):
        # Needs to wrap
        if self.currCursor:
            if dlen != -1:
                x = self.currCursor.next(doff=doff, dlen=dlen)
            else:
                x = self.currCursor.next()
            if x is None and self.currBucketIdx != len(self.buckets) - 1:
                c = self.set_cursor(self.buckets[self.currBucketIdx + 1])
                if dlen != -1:
                    return c.first(doff=doff, dlen=dlen)
                else:
                    return c.first()
            else:
                return x
        else:
            return self.first(doff=doff, dlen=dlen)

    def prev(self, doff=-1, dlen=-1):
        # Needs to wrap
        if self.currCursor:
            if dlen != -1:
                x = self.currCursor.prev(doff=doff, dlen=dlen)
            else:
                x = self.currCursor.prev()
            if x is None and self.currBucketIdx != 0:                
                c = self.set_cursor(self.buckets[self.currBucketIdx - 1])
                if dlen != -1:
                    return c.last(doff=doff, dlen=dlen)
                else:
                    return c.last()
            else:
                return x
        else:
            return self.last(doff=doff, dlen=dlen)
        
    def set_range(self, where, dlen=-1, doff=-1):
        # jump to where bucket
        b = self.switch.bucket(where)
        try:
            cursor = self.set_cursor(b)
        except ValueError:
            # non existant bucket
            tl = self.buckets[:]
            tl.append(b)
            tl.sort()
            idx = tl.index(b)
            if idx != len(self.buckets):
                nb = self.buckets[idx]
            else:
                nb = self.buckets[-1]
            cursor = self.set_cursor(nb)
           
        if dlen != -1:
            x = cursor.set_range(where, dlen=dlen, doff=doff)
        else:
            x = cursor.set_range(where)
        # at end of where bucket, step to next

        if x is None and self.currBucketIdx != len(self.buckets) - 1:
            c = self.set_cursor(self.buckets[self.currBucketIdx + 1])
            if dlen != -1:
                return c.first(doff=doff, dlen=dlen)
            else:
                return c.first()
        else:
            # End of index
            return x


class BdbStore(SimpleStore):
    """Berkeley DB based storage """
    cxns = {}

    def __init__(self, session, config, parent):
        self.cxns = {}
        self.createArgs = {}
        SimpleStore.__init__(self, session, config, parent)
        self.switchingClass = SwitchingBdbConnection

    def __iter__(self):
        # Return an iterator object to iter through... keys?
        return BdbIter(self.session, self)

    def _create(self, session, dbp):
        if self.switching:
            cxn = self.switchingClass(session, self, dbp)
        else:
            cxn = bdb.db.DB()
        cxn.set_flags(bdb.db.DB_RECNUM)
        try:
            cxn.open(dbp, dbtype=bdb.db.DB_BTREE, 
                     flags=bdb.db.DB_CREATE, mode=0660)
        except:
            raise ValueError("Could not create: %s" % dbp)
        cxn.close()

    def _verifyDb(self, session, dbType):
        dbp = self.get_path(session, dbType + "Path")
        if self.switching and dbType in self.get_noSwitchTypes(session):
            self.switching = False
            rv = self._verify(session, dbp)
            self.switching = True
            return rv
        else:
            return self._verify(session, dbp)

    def _verify(self, session, dbp):
        if (not os.path.exists(dbp)):
            # We don't exist, try and instantiate new database
            self._create(session, dbp)
        else:
            cxn = bdb.db.DB()
            try:
                cxn.open(dbp)
                cxn.close()
            except:
                # try to recreate
                self._create(session, dbp)

    def _openDb(self, session, dbType):
        cxn = self.cxns.get(dbType, None)
        if cxn is None:
            dbp = self.get_path(session, dbType + 'Path')
            if dbp is None:
                self._initDb(session, dbType)
                self._verifyDb(session, dbType)
                dbp = self.get_path(session, dbType + 'Path')
            if (os.path.exists(dbp) or
                dbType in self.storageTypes or
                (dbType[-7:] == 'Reverse' and
                 dbType[:-7] in self.reverseMetadataTypes)):
                if (self.switching and
                    dbType in self.get_noSwitchTypes(session)):
                    self.switching = False
                    cxn = self._open(session, dbp)
                    self.switching = True
                else:
                    cxn = self._open(session, dbp)
                self.cxns[dbType] = cxn
                return cxn
            else:
                # Trying to store something we don't care about
                return None
        else:
            return cxn

    def _open(self, session, dbp):
        if self.switching:
            cxn = self.switchingClass(session, self, dbp)
        else:
            cxn = bdb.db.DB()
        cxn.set_flags(bdb.db.DB_RECNUM)
        if session.environment == "apache":
            cxn.open(dbp, flags=bdb.db.DB_NOMMAP)
        else:
            cxn.open(dbp)
        return cxn

    def _closeDb(self, session, dbType):
        cxn = self.cxns.get(dbType, None)
        if cxn is not None:
            try:
                cxn.close()
            except:
                # silently fail, as we're closing anyway
                pass
            self.cxns[dbType] = None

    def _remove(self, session, dbp):
        try:
            cxn = bdb.db.DB()
            cxn.remove(dbp)
        except:
            pass

    def get_noSwitchTypes(self, session):
        return ['digest', 'digestReverse', 'metadata']

    def get_dbSize(self, session):
        cxn = self._openDb(session, 'digest')
        if cxn is None:
            cxn = self._openDb(session, 'database')
        return cxn.stat(bdb.db.DB_FAST_STAT)['nkeys']

    def generate_id(self, session):
        if self.useUUID:
            return gen_uuid()

        cxn = self._openDb(session, 'digest')
        if cxn is None:
            cxn = self._openDb(session, 'database')
        if (self.currentId == -1 or session.environment == "apache"):
            c = cxn.cursor()
            item = c.last()
            if item:
                # Might need to out normalise key
                key = item[0]
                if self.outIdNormalizer:
                    key = self.outIdNormalizer.process_string(session, key)
                    if not type(key) in (int, long):
                        self.useUUID = 1
                        key = gen_uuid()
                    else:
                        key += 1
                else:
                    key = long(key)
                    key += 1
            else:
                key = 0
        else:
            key = self.currentId + 1
        self.currentId = key
        return key

    def store_data(self, session, id, data, metadata={}):        
        dig = metadata.get('digest', "")
        if dig:
            cxn = self._openDb(session, 'digestReverse')
            if cxn:
                exists = cxn.get(dig)
                if exists:
                    raise ObjectAlreadyExistsException(exists)

        cxn = self._openDb(session, 'database')
        # Should always have an id by now, but just in case
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
        cxn.put(id, data)

        for (m, val) in metadata.iteritems():
            self.store_metadata(session, id, m, val)
        return None

    def fetch_data(self, session, id):
        cxn = self._openDb(session, 'database')
        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)
        data = cxn.get(id)

        if (data and
            data[:44] == "\0http://www.cheshire3.org/ns/status/DELETED:"):
            data = DeletedObject(self, id, data[41:])
            
        if data and self.expires:
            # update touched
            expires = self.generate_expires(session)
            self.store_metadata(session, id, 'expires', expires)
        return data
    
    def delete_data(self, session, id):
        self._openAll(session)
        cxn = self._openDb(session, 'database')

        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        # Main database is a storageType now
        for dbt in self.storageTypes:
            cxn = self._openDb(session, dbt)
            if cxn is not None:
                if dbt in self.reverseMetadataTypes:
                    # fetch value here, delete reverse
                    data = cxn.get(id)
                    cxn2 = self._openDb(session, dbt + "Reverse")                
                    if cxn2 is not None:
                        cxn2.delete(data)
                cxn.delete(id)
                cxn.sync()

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            cxn = self._openDb(session, 'database')
            now = datetime.datetime.now(dateutil.tz.tzutc())
            now = now.strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')            
            cxn.put(id,
                    "\0http://www.cheshire3.org/ns/status/DELETED:%s" % now)
            cxn.sync()

    def fetch_metadata(self, session, id, mType):
        if not mType.endswith("Reverse"):
            if (self.idNormalizer is not None):
                id = self.idNormalizer.process_string(session, id)
            elif type(id) == unicode:
                id = id.encode('utf-8')
            elif type(id) != str:
                id = str(id)
#        self.log_debug(session, mType)
        cxn = self._openDb(session, mType)
#        self.log_debug(session, cxn)
        if cxn is not None:
            data = cxn.get(id)
            if data:
                if data.startswith("\0http://www.cheshire3.org/ns/"
                                   "datatype/PICKLED:"):
                    data = data.split(':', 2)[2]
                    data = pickle.loads(data)
                elif mType.endswith(("Count", "Position", "Amount", "Offset")):
                    data = long(data)
                elif mType.endswith("Date"):
                    data = dateparser.parse(data)
            return data       
        else:
            return None

    def store_metadata(self, session, id, mType, value):
        if value is None:
            return
        cxn = self._openDb(session, mType)
        if cxn is None:
            self._initDb(session, mType)
            self._verifyDb(session, mType)
            cxn = self._openDb(session, mType)
        if cxn is not None:
            if isinstance(value, (int, long, float, datetime.datetime)):
                value = str(value)
            elif isinstance(value, (dict, list, tuple)):
                value = ("\0http://www.cheshire3.org/ns/datatype/PICKLED:"
                         "{0}".format(pickle.dumps(value)))
            cxn.put(id, value)
            if mType in self.reverseMetadataTypes:
                cxn = self._openDb(session, mType + "Reverse")
                if cxn is not None:
                    cxn.put(value, id)
        
    def flush(self, session):
        # Call sync to flush all to disk
        for cxn in self.cxns.values():
            if cxn is not None:
                cxn.sync()
                
    def clear(self, session):
        self._closeAll(session)
        self.cxns = {}
        for t in self.get_storageTypes(session):
            p = self.get_path(session, "%sPath" % t)
            self._remove(session, p)
            self._initDb(session, t)
            self._verifyDb(session, t)
        for t in self.get_reverseMetadataTypes(session):
            p = self.get_path(session, "%sReversePath" % t)
            self._remove(session, p)
            self._initDb(session, "%sReverse" % t)
            self._verifyDb(session, "%sReverse" % t)
        return self
                
    def clean(self, session):
        self._openAll(session)
        now = time.time()
        cxn = self._open(session, 'expiresReverse')
        c = cxn.cursor()
        deleted = 0
        try:
            (key, data) = c.set_range(str(now))
            # float(time) --> object id
            if (float(key) <= now):
                self.delete_data(session, data)
                deleted = 1
            (key, data) = c.prev()
        except:
            # No database
            deleted = 0
            key = False
        while key:
            self.delete_data(session, data)
            deleted += 1
            try:
                (key, data) = c.prev()
                if not float(key):
                    break
            except:
                # Reached beginning
                break
        self._closeAll(session)        
        return self


class FileSystemIter(object):
    store = None
    cursor = None
    cxn = None
    nextData = None

    def __init__(self, store):
        self.store = store
        self.session = Session()
        self.cxn = store._open(self.session, 'byteCount')
        self.cursor = self.cxn.cursor()
        (key, val) = self.cursor.first()
        self.nextData = (key, self.store.fetch_data(self.session, key))

    def __iter__(self):
        return self

    def next(self):
        try:
            d = self.nextData
            if not d:
                raise StopIteration()
            (key, val) = self.cursor.next()
            self.nextData = (key, self.store.fetch_data(self.session, key))
            return d
        except:
            raise StopIteration()

    def jump(self, position):
        # Jump to this position
        self.nextData = self.cursor.set_range(position)
        return self.nextData[0]


class FileSystemStore(BdbStore):
    # Leave the data somewhere on disk    
    # Use metadata to map identifier to file, offset, length
    # Object to be stored needs this information, obviously!

    currFileHandle = None
    currFileName = ""

    def __iter__(self):
        return FileSystemIter(self.session, self)

    def get_storageTypes(self, session):
        return ['filename', 'byteCount', 'byteOffset']

    def get_reverseMetadataTypes(self, session):
        return ['digest', 'expires']

    def store_data(self, session, id, data, metadata={}):        
        dig = metadata.get('digest', "")
        if dig:
            cxn = self._openDb(session, 'digestReverse')
            if cxn:
                exists = cxn.get(dig)
                if exists:
                    raise ObjectAlreadyExistsException(exists)

        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        if not ('filename' in metadata and
                'byteCount' in metadata and
                'byteOffset' in metadata):
            msg = "Need file, byteOffset and byteCount to use FileSystemStore"
            raise ValueError(msg)

        for (m, val) in metadata.iteritems():
            self.store_metadata(session, id, m, val)
        return None

    def fetch_data(self, session, id):
        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        filename = self.fetch_metadata(session, id, 'filename')
        start = self.fetch_metadata(session, id, 'byteOffset')
        length = self.fetch_metadata(session, id, 'byteCount')
        
        if filename is None and start is None and length is None:
            # Data has been deleted
            return None

        if filename != self.currFileName:
            if self.currFileHandle:
                self.currFileHandle.close()
            self.currFileHandle = file(filename)
        try:
            self.currFileHandle.seek(start)
        except:
            # closed, reopen
            self.currFileHandle = file(filename)
            self.currFileHandle.seek(start)
        data = self.currFileHandle.read(length)

        if (data and
            data[:44] == "\0http://www.cheshire3.org/ns/status/DELETED:"):
            data = DeletedObject(self, id, data[41:])
        elif self.outWorkflow:
            data = self.outWorkflow.process(session, data)

        if data and self.expires:
            # update touched
            expires = self.generate_expires(session)
            self.store_metadata(session, id, 'expires', expires)
        return data
        
    def delete_data(self, session, id):
        self._openAll(session)

        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)

        filename = self.fetch_metadata(session, id, 'filename')
        start = self.fetch_metadata(session, id, 'byteOffset')
        length = self.fetch_metadata(session, id, 'byteCount')

        # Main database is a storageType now
        for dbt in self.storageTypes:
            cxn = self._openDb(session, dbt)
            if cxn is not None:
                if dbt in self.reverseMetadataTypes:
                    # Fetch value here, delete reverse
                    data = cxn.get(id)
                    cxn2 = self._openDb(session, dbt + "Reverse")                
                    if cxn2 is not None:
                        cxn2.delete(data)
                cxn.delete(id)
                cxn.sync()

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            now = datetime.datetime.now(dateutil.tz.tzutc())
            now = now.strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')            
            out = "\0http://www.cheshire3.org/ns/status/DELETED:%s" % now

            if len(out) < length:
                f = file(filename, 'w')
                f.seek(start)
                f.write(out)
                f.close()
            else:
                # Can't write deleted status as original doc is shorter than
                # deletion info!
                pass


def directoryStoreIter(store):
    session = Session()
    databasePath = store.get_path(session, 'databasePath')
    for root, dirs, files in os.walk(databasePath):
        for name in files:
            filepath = os.path.join(root, name)
            # Split off identifier
            id_ = filepath[len(databasePath) + 1:]
            # De-normalize id
            if not store.allowStoreSubDirs:
                id_ = unquote(id_)
            if store.outIdNormalizer is not None:
                id_ = store.outIdNormalizer.process_string(session, id_)
            # Read in data
            with open(filepath, 'r') as fh:
                data = fh.read()
            # Check for DeletedObject
            if (
                data and
                data.startswith("\0http://www.cheshire3.org/ns/status/"
                                "DELETED:")
            ):
                data = DeletedObject(self, id, data[41:])

            # Update expires
            if data and store.expires:
                expires = store.generate_expires(session)
                store.store_metadata(session, id, 'expires', expires)

            yield (id_, data)
        # By default don't iterate over VCS directories
        for vcs in ['CVS', '.git', '.hg', '.svn']:
            try:
                dirs.remove(vcs)
            except:
                # This VCS isn't there, so no need to remove
                continue


class DirectoryStore(BdbStore):
    """Store Objects as files in a directory on the filesystem.

    Really simple Store to store Objects as files within a directory (and
    possibly sub-directories). An important thing to remember is that
    files may be added/modified/deleted by an external entity.
    """
    
    _possibleSettings = {
        'createSubDir': {
            'docs': ('Should a sub-directory/sub-collection be used for this '
                     'store'),
            'type': int,
            'options' : "0|1"
        },
        'allowStoreSubDirs': {
            'docs': ('Allow Store to create sub-directories if it encounters '
                     'an operating system path separator in an identifier. If'
                     ' false (0) operating system path separators are escaped.'
                     ),
            'type': int,
            'options' : '0|1'
        }
    }

    def __init__(self, session, config, parent):
        BdbStore.__init__(self, session, config, parent)
        if self.switching:
            raise ConfigFileException('Switching not supported by {0}'
                                      ''.format(self.__class__.__name__))
        self.allowStoreSubDirs = self.get_setting(session,
                                                  'allowStoreSubDirs',
                                                  1)
        # TODO: Refresh metadata in case files have changed

    def __iter__(self):
        return directoryStoreIter(self)

    def _initDb(self, session, dbt):
        dbp = dbt + "Path"
        databasePath = self.get_path(session, dbp, "")
        if not databasePath:
            databasePath = self.id
        elif self.get_setting(session, 'createSubDir', 0):
            databasePath = os.path.join(databasePath, self.id)
        if (not os.path.isabs(databasePath)):
            # Prepend defaultPath from parents
            dfp = self.get_path(session, 'defaultPath')
            if not dfp:
                msg = ("Store has relative path, and no visible "
                       "defaultPath.")
                raise ConfigFileException(msg)
            databasePath = os.path.join(dfp, databasePath)
        self.paths[dbp] = databasePath

    def _verifyDb(self, session, dbType):
        dbp = self.get_path(session, dbType + "Path")
        if dbType == 'database':
            # Simply the directory in which to store data
            # Ensure that it exists (including any intermediate dirs)
            if not os.path.exists(dbp):
                os.makedirs(dbp)
        else:
            return BdbStore._verify(self, session, dbp)

    def _openDb(self, session, dbType):
        if dbType == 'database':
            # Simply the directory in which to store data
            # Ensure that it exists
            dbp = self.get_path(session, dbType + 'Path')
            if dbp is None:
                self._initDb(session, dbType)
                self._verifyDb(session, dbType)
        else:
            return BdbStore._openDb(self, session, dbType)

    def _closeDb(self, session, dbType):
        if dbType == 'database':
            # Simply the directory in which to store data - do nothing
            pass
        else:
            return BdbStore._closeDb(self, session, dbType)

    def _normalizeIdentifier(self, session, identifier):
        # Apply any necessary normalization to the identifier 
        if (self.idNormalizer != None):
            identifier = self.idNormalizer.process_string(session, identifier)
        elif type(id) == unicode:
            identifier = identifier.encode('utf-8')
        else:
            identifier = str(identifier)
        return identifier

    def _getFilePath(self, session, identifier):
        if os.path.sep in identifier and not self.allowStoreSubDirs:
            # Escape os path separator
            identifier = quote(identifier)
        databasePath = self.get_path(session, 'databasePath')
        return os.path.join(databasePath, identifier)

    def generate_id(self, session):
        """Generate and return a new unique identifier."""
        return self.get_dbSize(session)

    def get_storageTypes(self, session):
        return ['database']

    def get_reverseMetadataTypes(self, session):
        return ['digest']

    def get_dbSize(self, session):
        """Return number of items in storage."""
        databasePath = self.get_path(session, 'databasePath')
        return sum([len(t[2]) for t in os.walk(databasePath)])

    def delete_data(self, session, identifier):
        """Delete data stored against id."""
        self._openAll(session)
        identifier = self._normalizeIdentifier(session, identifier)
        filepath = self._getFilePath(session, identifier)

        # Main database is a storageType now
        for dbt in self.storageTypes:
            if dbt == 'database':
                # Simply the directory in which to store data
                # Delete the file
                os.remove(filepath)
            else:
                cxn = self._openDb(session, dbt)
                if cxn is not None:
                    if dbt in self.reverseMetadataTypes:
                        # Fetch value here, delete reverse
                        data = cxn.get(identifier)
                        cxn2 = self._openDb(session, dbt + "Reverse")
                        if cxn2 is not None:
                            cxn2.delete(data)
                    cxn.delete(identifier)
                    cxn.sync()

        # Maybe store the fact that this object used to exist.
        if self.get_setting(session, 'storeDeletions', 0):
            now = datetime.datetime.now(dateutil.tz.tzutc())
            now = now.strftime("%Y-%m-%dT%H:%M:%S%Z").replace('UTC', 'Z')
            with open(filepath, 'w') as fh:
                fh.write("\0http://www.cheshire3.org/ns/status/DELETED:{0}"
                         "".format(now)
                         )

    def fetch_data(self, session, identifier):
        """Return data stored against identifier."""
        identifier = self._normalizeIdentifier(session, identifier)
        filepath = self._getFilePath(session, identifier)
        try:
            with open(filepath) as fh:
                data = fh.read()
        except IOError:
            # No file
            data = None
        if (data and
            data.startswith("\0http://www.cheshire3.org/ns/status/DELETED:")
            ):
            data = DeletedObject(self, identifier, data[41:])
        if data and self.expires:
            expires = self.generate_expires(session)
            self.store_metadata(session, identifier, 'expires', expires)
        return data

    def store_data(self, session, identifier, data, metadata={}):
        """Store data against identifier."""
        dig = metadata.get('digest', "")
        if dig:
            cxn = self._openDb(session, 'digestReverse')
            if cxn:
                exists = cxn.get(dig)
                if exists:
                    raise ObjectAlreadyExistsException(exists)
        # Should always have an id by now, but just in case
        if identifier is None:
            identifier = self.generate_id(session)
        identifier = self._normalizeIdentifier(session, identifier)
        filepath = self._getFilePath(session, identifier)
        # Check for subdirectories
        if os.path.sep in identifier and self.allowStoreSubDirs:
            # Create necessary sub-directories
            directory, filename = os.path.split(filepath)
            os.makedirs(directory)
        # Encode data if necessary
        if type(data) == unicode:
            data = data.encode('utf-8')
        with open(filepath, 'w') as fh:
            fh.write(data)
        for (m, val) in metadata.iteritems():
            self.store_metadata(session, identifier, m, val)
        return None

    def fetch_metadata(self, session, identifier, mType):
        """Return mType metadata stored against identifier."""
        return BdbStore.fetch_metadata(self, session, identifier, mType)

    def store_metadata(self, session, identifier, mType, value):
        """Store value for mType metadata against identifier."""
        return BdbStore.store_metadata(self, session, identifier, mType, value)

    def clean(self, session):
        """Delete expired data objects."""
        return BdbStore.clear(self, session)

    def clear(self, session):
        """Delete all the data out of self."""
        self._closeAll(session)
        self.cxns = {}
        for t in self.get_storageTypes(session):
            p = self.get_path(session, "%sPath" % t)
            if t == 'database':
                # Simply the directory in which to store data
                # Clear the entire directory
                shutil.rmtree(p)
            else:
                self._remove(session, p)
            self._initDb(session, t)
            self._verifyDb(session, t)
        for t in self.get_reverseMetadataTypes(session):
            p = self.get_path(session, "%sReversePath" % t)
            self._remove(session, p)
            self._initDb(session, "%sReverse" % t)
            self._verifyDb(session, "%sReverse" % t)
        return self

    def flush(self, session):
        """Ensure all data is flushed to disk."""
        return BdbStore.flush(self, session)
