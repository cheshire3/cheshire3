"""Cheshire3 Index Implementations."""

import os
import re
import math
import struct
import codecs
import gzip

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from lxml import etree

import cheshire3.cqlParser as cql

from cheshire3.baseObjects import Index, Session
from cheshire3.utils import elementType, flattenTexts, vectorSimilarity,\
                            SimpleBitfield
from cheshire3.exceptions import ConfigFileException, QueryException, \
                                 C3ObjectTypeError, PermissionException
from cheshire3.internal import CONFIG_NS
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem,\
                                BitmapResultSet
from cheshire3.workflow import CachingWorkflow
from cheshire3.xpathProcessor import SimpleXPathProcessor


class IndexIter(object):
    """Object to facilitate iterating over an Index."""

    index = None
    session = None

    def __init__(self, index):
        self.index = index
        self.indexStore = index.indexStore
        self.session = Session()
        self.summary = 0
        # populate with first term
        try:
            self.nextData = self.indexStore.fetch_termList(self.session,
                                                           self.index,
                                                           "",
                                                           1)[0]
        except IndexError:
            self.nextData = None

    def __iter__(self):
        return self

    def next(self):
        """Return the next item from the iterator."""
        try:
            d = self.nextData
            if not d:
                raise StopIteration()
            if d[-1] == 'last':
                self.nextData = ""
            else:
                try:
                    nd = self.indexStore.fetch_termList(self.session,
                                                        self.index,
                                                        d[0], 2)[1]
                except IndexError:
                    self.nextData = ""
                else:
                    self.nextData = nd

            return self.index.construct_resultSet(self.session, d[1],
                                                  queryHash={'text': d[0],
                                                             'occurences': 1,
                                                             'positions': []})
        except:
            # Fail safely
            raise StopIteration()

    def jump(self, position):
        """Jump to a position in the sequence."""
        self.nextData = self.indexStore.fetch_termList(self.session,
                                                       self.index,
                                                       position, 1)[0]
        return self.index.construct_resultSet(self.session,
                                              self.nextData[1],
                                              queryHash={
                                                  'text': self.nextData[0],
                                                  'occurences': 1,
                                                  'positions': []
                                              })


class SimpleIndex(Index):
    sources = {}
    xPathAllAbsolute = 1
    xPathAttributesRequired = []
    xPathsNormalized = {}
    currentFullPath = []
    currentPath = []
    storeOrig = 0
    canExtractSection = 1

    indexingTerm = ""
    indexingData = []

    _possiblePaths = {
        'indexStore': {
            "docs": "IndexStore identifier for where this index is stored"
        },
        'termIdIndex': {
            "docs": ("Alternative index object to use for termId for terms "
                     "in this index.")
        },
        'tempPath': {
            "docs": ("Path to a directory where temporary files will be "
                     "stored during batch mode indexing")
        }
    }

    _possibleSettings = {
        'lr_constant0': {
            "docs": ("Value for 1st constant in logistic regression relevance"
                     "assignments. default: -3.7"),
            'type': float
        },
        'lr_constant1': {
            "docs": ("Value for 2nd constant in logistic regression relevance"
                     "assignments. default: 1.269"),
            'type': float
        },
        'lr_constant2': {
            "docs": ("Value for 3rd constant in logistic regression relevance"
                     "assignments. default: -0.31"),
            'type': float
        },
        'lr_constant3': {
            "docs": ("Value for 4th constant in logistic regression relevance"
                     "assignments. default: 0.679"),
            'type': float
        },
        'lr_constant4': {
            "docs": ("Value for 5th constant in logistic regression relevance"
                     "assignments. default: -0.021"),
            'type': float
        },
        'lr_constant5': {
            "docs": ("Value for 6th constant in logistic regression relevance"
                     "assignments. default: 0.223"),
            'type': float
        },
        'lr_constant6': {
            "docs": ("Value for 7th constant in logistic regression relevance"
                     "assignments. default: 4.01"),
            'type': float
        },
        'okapi_constant_b': {
            "docs": ("Constant to use for tuning parameter 'b' in the "
                     "OKAPI BM-25 algorithm. 0 <= b <= 1 determines effect "
                     "of document length on term weight scaling. "
                     "0 -> no effect, 1 -> full scaling."),
            'type': float
        },
        'okapi_constant_k1': {
             "docs": "",
             'type': float
        },
        'okapi_constant_k3': {
             "docs": "",
             'type': float
        },
        'noIndexDefault': {
            "docs": ("If true, the index should not be called from "
                     "db.index_record()"),
            "type": int,
            "options": "0|1"
        },
        'noUnindexDefault': {
            "docs": ("If true, the index should not be called from "
                     "db.unindex_record()"),
            "type": int,
            "options": "0|1"
        },
        'sortStore': {
            "docs": "Should the index build a store to support sorting",
            'type': int,
            'options': '0|1'
        },
        'termIds': {
            "docs": "Should the index store termId -> term",
            'type': int,
            'options': '0|1'
        },
        'vectors': {
            "docs": "Should the index store vectors (doc -> list of termIds.",
            'type': int,
            'options': '0|1'
        },
        'proxVectors': {
            "docs": ("Should the index store vectors that also maintain "
                     "proximity for their terms"),
            'type': int,
            'options': '0|1'
        },
        'minimumSupport': {
            "docs": ("Minimum number of records in which the term must appear "
                     "for it to be indexed at all"),
            'type': int
        },
        'vectorMinGlobalFreq': {
            "docs": "Minimum global records for term to appear in a vector",
            'type': int
        },
        'vectorMaxGlobalFreq': {
            "docs": "Maximum global records for term to appear in a vector",
            'type': int
        },
        'vectorMinGlobalOccs': {
            "docs": "Minimum global occurences",
            'type': int
        },
        'vectorMaxGlobalOccs': {
            "docs": "Maximum global occurences",
            'type': int
        },
        'vectorMinLocalFreq': {
            "docs": "Minimum records in selected",
            'type': int
        },
        'vectorMaxLocalFreq': {
            "docs": "Maximum records in selected",
            'type': int
        },
        'freqList': {
            'docs': ("Store a frequency sorted list to step through "
                     "of records, occurrences or both"),
            'options': 'rec|occ|rec occ|occ rec'
        },
        'longSize': {
            "docs": ("Size of a long integer in this index's underlying data "
                     "structure (eg to migrate between 32 and 64 bit "
                     "platforms)"),
            'type': int
        },
        'recordStoreSizes': {
            "docs": ("Should we use recordStore sizes instead of database "
                     "sizes"),
            'type': int
        },
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
    }

    def _handleConfigNode(self, session, node):
        # Source
        if (node.localName == "source"):
            modes = node.getAttributeNS(None, 'mode')
            if not modes:
                modes = [u'data']
            else:
                modes = modes.split('|')
            process = None
            preprocess = None
            xp = None
            for child in node.childNodes:
                if child.nodeType == elementType:
                    if child.localName in ["xpath", "selector"]:
                        if xp is None:
                            ref = child.getAttributeNS(None, 'ref')
                            if ref:
                                xp = self.get_object(session, ref)
                            else:
                                xp = SimpleXPathProcessor(session, node, self)
                                xp._handleConfigNode(session, node)
                    elif child.localName == "preprocess":
                        # turn preprocess chain to workflow
                        ref = child.getAttributeNS(None, 'ref')
                        if ref:
                            preprocess = self.get_object(session, ref)
                        else:
                            child.localName = 'workflow'
                            preprocess = CachingWorkflow(session, child, self)
                            preprocess._handleConfigNode(session, child)
                    elif child.localName == "process":
                        # turn xpath chain to workflow
                        ref = child.getAttributeNS(None, 'ref')
                        if ref:
                            process = self.get_object(session, ref)
                        else:
                            try:
                                child.localName = 'workflow'
                            except:
                                # 4suite dom sets read only
                                # Shortcut to method for shorter lines!
                                cefn = child.ownerDocument.createElementNS
                                newTop = cefn(None, 'workflow')
                                for kid in child.childNodes:
                                    newTop.appendChild(kid)
                                child = newTop
                            process = CachingWorkflow(session, child, self)
                            process._handleConfigNode(session, child)

            for m in modes:
                mysrc = self.sources.setdefault(m, [])
                mysrc.append((xp, process, preprocess))

    def _handleLxmlConfigNode(self, session, node):
        # Source
        if node.tag in ["source", '{%s}source' % CONFIG_NS]:
            modes = node.attrib.get('{%s}mode' % CONFIG_NS,
                                    node.attrib.get('mode', 'data'))
            modes = modes.split('|')
            process = None
            preprocess = None
            xp = None
            for child in node.iterchildren(tag=etree.Element):
                if child.tag in ['xpath', '{%s}xpath' % CONFIG_NS,
                                 'selector', '{%s}selector' % CONFIG_NS]:
                    if xp is None:
                        ref = child.attrib.get('{%s}ref' % CONFIG_NS,
                                               child.attrib.get('ref', ''))
                        if ref:
                            xp = self.get_object(session, ref)
                        else:
                            node.set('id', self.id + '-xpath')
                            xp = SimpleXPathProcessor(session, node, self)
                            xp._handleLxmlConfigNode(session, node)
                elif child.tag in ['preprocess', '{%s}preprocess' % CONFIG_NS]:
                    # turn preprocess chain to workflow
                    ref = child.attrib.get('{%s}ref' % CONFIG_NS,
                                           child.attrib.get('ref', ''))
                    if ref:
                        preprocess = self.get_object(session, ref)
                    else:
                        # create new element
                        e = etree.XML(etree.tostring(child))
                        e.tag = 'workflow'
                        e.set('id', self.id + "-preworkflow")
                        preprocess = CachingWorkflow(session, e, self)
                        preprocess._handleLxmlConfigNode(session, e)
                elif child.tag in ['process', '{%s}process' % CONFIG_NS]:
                    # turn xpath chain to workflow
                    ref = child.attrib.get('{%s}ref' % CONFIG_NS,
                                           child.attrib.get('ref', ''))
                    if ref:
                        process = self.get_object(session, ref)
                    else:
                        # create new element
                        e = etree.XML(etree.tostring(child))
                        e.tag = 'workflow'
                        e.set('id', self.id + "-workflow")
                        process = CachingWorkflow(session, e, self)
                        process._handleLxmlConfigNode(session, e)
            for m in modes:
                mysrc = self.sources.setdefault(m, [])
                mysrc.append((xp, process, preprocess))

    def __init__(self, session, config, parent):
        self.sources = {}
        self.xPathAttributesRequired = []
        self.xPathsNormalized = {}
        self.xPathAllAbsolute = 1
        self.indexingTerm = ""
        self.indexingData = []

        self.maskList = ['*', '?', '^']
        self.caretRe = re.compile(r'(?<!\\)\^')
        self.qmarkRe = re.compile(r'(?<!\\)\?')
        self.astxRe = re.compile(r'(?<!\\)\*')

        Index.__init__(self, session, config, parent)

        lss = self.get_setting(session, 'longSize')
        if lss:
            self.longStructSize = int(lss)
        else:
            #self.longStructSize = len(struct.pack('L', 1))
            self.longStructSize = struct.calcsize('l')

        self.recordStoreSizes = self.get_setting(session,
                                                 'recordStoreSizes',
                                                 0)
        # We need a Store object
        iStore = self.get_path(session, 'indexStore', None)
        self.indexStore = iStore

        if (iStore is None):
            raise ConfigFileException("Index (%s) does not have an "
                                      "indexStore." % (self.id))
        else:
            iStore.create_index(session, self)

        self.resultSetClass = SimpleResultSet
        self.recordStore = ""

    def __iter__(self):
        return IndexIter(self)

    def _locate_firstMask(self, term, start=0):
        try:
            return min([term.index(x, start) for x in self.maskList])
        except ValueError:
            # one or more are not found (i.e. == -1)
            firstMaskList = [term.find(x, start) for x in self.maskList]
            firstMaskList.sort()
            firstMask = firstMaskList.pop(0)
            while len(firstMaskList) and firstMask < 0:
                firstMask = firstMaskList.pop(0)
            return firstMask

    def _regexify_wildcards(self, term):
        # Escape existing special regex chars
        term = term.replace('.', r'\.')
        term = term[0] + self.caretRe.sub(r'\^', term[1:-1]) + term[-1]
        term = self.qmarkRe.sub('.', term)
        term = self.astxRe.sub('.*', term)
        if (term[-1] == '^') and (term[-2] != '\\'):
            term = term[:-1]
        return term + '$'

    def _processRecord(self, session, record, source):
        (xpath, process, preprocess) = source
        if preprocess:
            record = preprocess.process(session, record)
        if xpath:
            try:
                rawlist = xpath.process_record(session, record)
            except C3ObjectTypeError:
                rawlist = [[]]
            processed = process.process(session, rawlist)
        else:
            processed = process.process(session, record)
        return processed

    def extract_data(self, session, rec):
        processed = self._processRecord(session, rec, self.sources[u'data'][0])
        if processed:
            keys = processed.keys()
            keys.sort()
            return keys[0]
        else:
            return None

    def index_record(self, session, rec):
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add "
                                          "to index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to "
                                          "index %s" % self.id)
        if 'sort' in self.sources:
            sortHash = self._processRecord(session, rec,
                                           self.sources[u'sort'][0])
            if sortHash:
                sortVal = sortHash.keys()[0]
            else:
                sortVal = ''
        else:
            sortVal = ''

        for src in self.sources[u'data']:
            processed = self._processRecord(session, rec, src)
            if sortVal:
                # Don't blank sortVal, or will be overwritten
                # in subsequent iterations
                k = processed.keys()[0]
                processed[k]['sortValue'] = sortVal
            self.indexStore.store_terms(session, self, processed, rec)
        return rec

    def delete_record(self, session, rec):
        # Extract terms, and remove from store
        p = self.permissionHandlers.get('info:srw/operation/2/unindex', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to "
                                          "remove from index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to remove from "
                                          "index %s" % self.id)
        istore = self.get_path(session, 'indexStore')

        if self.get_setting(session, 'vectors', 0):
            # use vectors to unindex instead of reprocessing
            # faster, only way for 'now' metadata.
            vec = self.fetch_vector(session, rec)
            # [totalUniqueTerms, totalFreq, [(tid, freq)+]]
            processed = {}
            for (t, f) in vec[2]:
                term = self.fetch_termById(session, t)
                processed[term] = {'occurences': f}
            if istore is not None:
                istore.delete_terms(session, self, processed, rec)
        else:
            for src in self.sources[u'data']:
                processed = self._processRecord(session, rec, src)
                if (istore is not None):
                    istore.delete_terms(session, self, processed, rec)

    def begin_indexing(self, session):
        # Find all indexStores
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add "
                                          "to index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to "
                                          "index %s" % self.id)
        stores = []
        istore = self.get_path(session, 'indexStore')
        if (istore is not None and not istore in stores):
            stores.append(istore)
        for s in stores:
            s.begin_indexing(session, self)

    def commit_indexing(self, session):
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add "
                                          "to index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to "
                                          "index %s" % self.id)
        stores = []
        istore = self.get_path(session, 'indexStore')
        if (istore is not None and not istore in stores):
            stores.append(istore)
        for s in stores:
            s.commit_indexing(session, self)

    def commit_parallelIndexing(self, session):
        istore = self.get_path(session, 'indexStore')
        istore.commit_parallelIndexing(session, self)

    def search(self, session, clause, db):
        # Final destination. Process Term.
        p = self.permissionHandlers.get('info:srw/operation/2/search', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to "
                                          "search index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to search "
                                          "index %s" % self.id)

        res = {}
        # src = (xp, processwf, preprocesswf)
        # Try to get process for relation/modifier, failing that relation,
        # fall back to that used for data
        for src in self.sources.get(clause.relation.toCQL(),
                                    self.sources.get(clause.relation.value,
                                                     self.sources[u'data'])):
            res.update(src[1].process(session, [[clause.term.value]]))

        store = self.get_path(session, 'indexStore')
        matches = []
        rel = clause.relation
        if (rel.prefix == 'cql' or
            rel.prefixURI == 'info:srw/cql-context-set/1/cql-v1.1'):
            if (rel.value == 'scr'):
                pm = db.get_path(session, 'protocolMap')
                try:
                    rel.value = pm.defaultRelation
                except AttributeError:
                    pass

        # While we're looking at the query, check if we should do blind
        # relevance feedback on this clause
        feedback = 0
        for m in rel.modifiers:
            m.type.parent = clause
            m.type.resolvePrefix()
            if (m.type.prefixURI.startswith(
                                    'info:srw/cql-context-set/2/relevance')):
                if m.type.value == "feedback":
                    try:
                        feedback = int(m.value)
                    except ValueError:
                        feedback = 1

        construct_resultSet = self.construct_resultSet
        if (rel.value in ['any', 'all', '=', 'exact', 'window'] and
            (rel.prefix == 'cql' or
             rel.prefixURI == 'info:srw/cql-context-set/1/cql-v1.1'
            )):
            for k, qHash in res.iteritems():
                if k[0] == '^':
                    k = k[1:]
                firstMask = self._locate_firstMask(k)
                while (firstMask > 0) and (k[firstMask - 1] == '\\'):
                    firstMask = self._locate_firstMask(k, firstMask + 1)
                # TODO: slow regex e.g. if first char is *
                if (firstMask > -1):
                    startK = k[:firstMask]
                    try:
                        nextK = startK[:-1] + unichr(ord(startK[-1]) + 1)
                    except IndexError:
                        # Left truncation, all terms from the index
                        # TODO: we should check if there's a inversion of
                        # index keys
                        termList = store.fetch_termList(session, self,
                                                        startK, 0, '>=')
                    else:
                        termList = store.fetch_termList(session, self,
                                                        startK, 0, '>=',
                                                        end=nextK)
                    if len(k) > 1:
                        # Filter terms by regex
                        # FIXME: need to do something cleverer than this if
                        # first character is masked. This implementation will
                        # be incredibly slow for these cases...
                        if ((firstMask < len(k) - 1) or
                            (k[firstMask] in ['?', '^'])):
                            # not simply right hand truncation
                            kRe = re.compile(self._regexify_wildcards(k))
                            mymatch = kRe.match
                            termList = filter(lambda t: mymatch(t[0]),
                                              termList)

                    maskBase = self.resultSetClass(
                                               session, [],
                                               recordStore=self.recordStore)
                    maskClause = cql.parse(clause.toCQL())
                    maskClause.relation.value = u'any'
                    if (clause.relation.value == u'='):
                        # tell combine to keep proxInfo
                        pass

                    try:
                        maskResultSets = [
                            construct_resultSet(session, t[1], qHash)
                            for t in termList
                        ]
                        maskBase = maskBase.combine(session, maskResultSets,
                                                    maskClause, db)
                        maskBase.queryTerm = qHash['text']
                        try:
                            maskBase.queryPositions = qHash['positions']
                        except KeyError:
                            pass
                    except:
                        pass
                    else:
                        matches.append(maskBase)
                else:
                    term = store.fetch_term(session, self, k)
                    s = construct_resultSet(session, term, qHash)
                    matches.append(s)
        elif (clause.relation.value in ['>=', '>', '<', '<=']):
            if (len(res) != 1):
                raise QueryException("%s %s" % (clause.relation.toCQL(),
                                                clause.term.value),
                                     24)
            else:
                termList = store.fetch_termList(session, self, res.keys()[0],
                                                0, clause.relation.value)
                for t in termList:
                    matches.append(construct_resultSet(session, t[1]))
        elif (clause.relation.value == "within"):
            if (len(res) != 2):
                raise QueryException('%s "%s"' % (clause.relation.toCQL(),
                                                  clause.term.value),
                                     24)
            else:
                termList = store.fetch_termList(session, self, res.keys()[0],
                                                end=res.keys()[1])
                matches.extend([construct_resultSet(session, t[1])
                                for t in termList])
        else:
            raise QueryException('%s "%s"' % (clause.relation.toCQL(),
                                              clause.term.value),
                                 24)

        base = self.resultSetClass(session, [], recordStore=self.recordStore)
        base.recordStoreSizes = self.recordStoreSizes
        base.index = self
        if not matches:
            return base
        else:
            if (clause.relation.value == "=" and not
                isinstance(self, ProximityIndex)):
                # Can't do proximity, treat as a search for 'all'
                clause.relation.value = "all"
            rs = base.combine(session, matches, clause, db)
            if len(rs) and feedback:
                rs = self._blindFeedback(session, rs, clause, db)
            return rs

    def scan(self, session, clause, nTerms, direction=">=", summary=1):
        # Process term.
        p = self.permissionHandlers.get('info:srw/operation/2/scan', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to "
                                          "scan index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to scan index "
                                          "%s" % self.id)

        res = {}
        for src in self.sources.get(clause.relation.toCQL(),
                                    self.sources.get(clause.relation.value,
                                                     self.sources[u'data'])):
            res.update(src[1].process(session, [[clause.term.value]]))

        if len(res) == 0:
            # No term, so start at the beginning
            res = {'': ''}
        elif (len(res) != 1):
            raise QueryException("%s" % (clause.term.value), 24)
        store = self.get_path(session, 'indexStore')
        if direction == "=":
            k = res.keys()[0]
            if not k:
                k2 = "!"
            else:
                k2 = k[:-1] + unichr(ord(k[-1]) + 1)
            tList = store.fetch_termList(session, self, k,
                                         nTerms=nTerms, end=k2,
                                         summary=summary, relation='>=')
        else:
            tList = store.fetch_termList(session, self, res.keys()[0],
                                         nTerms=nTerms, relation=direction,
                                         summary=summary)
        # List of (term, occs)
        return tList

    def facets(self, session, resultSet, nTerms=0):
        """Return a list of term facets for the resultSet.

        Return a list of (term, termdata) tuples from this index which occur
        within the records in resultSet. Terms are returned in descending
        frequency (number of records) order.
        """
        termFreqs = {}
        recordFreqs = {}
        for r in resultSet:
            # Use vectors to identify terms
            vec = self.fetch_vector(session, r)
            if vec[2]:
                # store / increment freq
                for t in vec[2]:
                    try:
                        termFreqs[t[0]] += t[1]
                        recordFreqs[t[0]] += 1
                    except:
                        termFreqs[t[0]] = t[1]
                        recordFreqs[t[0]] = 1

        # Sort list by descending frequency (decorate-sort-undecorate)
        # Use 1 / freq - keeps terms with same freq in alpha order
        sortList = [(1.0 / v, k)
                    for k, v
                    in recordFreqs.iteritems()]
        sortList.sort()
        tids = [x[1] for x in sortList]
        if nTerms:
            tids = tids[:min(len(tids), nTerms)]
        terms = []
        for termId in tids:
            term = self.fetch_termById(session, termId)
            # (term, (termId, nRecs, freq))
            terms.append((term.decode('utf-8'),
                          (termId, recordFreqs[termId], termFreqs[termId])))
        return terms

    def searchByExamples(self, session, examples, clause, db, nTerms=20):
        """Return a ResultSet of items 'similar' to the given examples.

        Identify most common terms in examples, create a new resultSet of
        results that contains any of these terms.

        examples := iterable of example objects (e.g. ResultSet, list of
                    Records) to be used to search the index (i.e. by
                    identifying common terms)
        clause   := CQL clause (if examples is a resultSet this would the query
                    used to generate it)
        nTerms   := No. of most common (no. of records) terms to use to create
                    new resultSet
        """
        base = self.resultSetClass(session, [], recordStore=self.recordStore)
        base.recordStoreSizes = self.recordStoreSizes
        base.index = self
        try:
            terms = [t[0] for t in self.facets(session, examples, nTerms)]
        except:
            raise ConfigFileException("Index {0.id} does not support "
                                      "searchByExample; requires vector "
                                      "setting.".format(self))
        # Construct a CQL clause for combining the resultSets from the
        # discovered terms
        # Use modifiers from main clause so that we get scores from the same
        # relevance algorithm combined in the same way
        exClause = cql.SearchClause(clause.index,
                                    cql.Relation("any",
                                                 clause.relation.modifiers),
                                    cql.Term(" ".join(terms)))
        construct_rs = self.construct_resultSet
        store = self.indexStore
        matches = [construct_rs(session,
                                store.fetch_term(session, self, t),
                                {'text': t, 'proxLoc': [-1], 'occurences': 1})
                   for t in terms]
        self.log_debug(session, "searchByExamples ResultSets constructed")
        rs = base.combine(session, matches, exClause, db)
        self.log_debug(session, "searchByExamples ResultSets combined")
        return rs

    def _blindFeedback(self, session, rs, clause, db, nRecs=0, nTerms=20):
        """Expand ResultSet using blind/pseudo relevance feedback.

        Carry out blind/pseudo relevance feedback on the resultSet, merge and
        return.

        rs        := resultSet
        clause    := CQL clause that generated rs
        nRecs     := No. of top results to extract terms from
        nTerms    := No. of top terms to use to expand query
        """
        if not rs.relevancy:
            raise TypeError("Unable to carry out blind relevance feedback on "
                            "a resultSet with no relevance information")
        if not nRecs:
            nRecs = max(int(math.sqrt(len(rs))), 5)
        self.log_debug(session,
                       "Feedback requested; top {0} Terms from top {1} of "
                       "{2} Records".format(nTerms, nRecs, len(rs)))
        # Need to sort before slicing to get the 'good' results
        # Use the built-in sorted() to create a sorted iterable slice of top
        # results without changing original (otherwise combining with new
        # results will end up with duplicates)
        try:
            fbrs = self.searchByExamples(
                                 session,
                                 sorted(rs, key=lambda x: x.weight)[:nRecs],
                                 clause,
                                 db,
                                 nTerms)
        except ConfigFileException as e:
            self.log_warning(session,
                             "Unable to complete blind relevance feedback "
                             "loop: " + e.reason)
            return rs
        # Both resultSets now have scores assigned, so need to combine them
        # using a boolean
        fooQ = cql.parse(">rel=info:srw/cql-context-set/2/relevance-1.1 {0}"
                         " or/rel.combine=sum {1}".format(clause.toCQL(),
                                                          fbrs.query.toCQL()))
        base = self.resultSetClass(session, [], recordStore=self.recordStore)
        base.recordStoreSizes = self.recordStoreSizes
        base.index = self
        return base.combine(session, [rs, fbrs], fooQ, db)

    def similarity(self, session, record1, record2):
        """Calculate and return cosine similarity of records.

        Calculate and return cosine similarity of vector representations of the
        two record arguments.

        >>> self.similarity(session, rec, rec)
        1.0
        """
        if self.get_setting(session, 'vectors', 0):
            # We can fetch stored vectors
            vector1 = self.fetch_vector(session, record1)
            vector2 = self.fetch_vector(session, record2)
        else:
            # We could regenerate on the fly...
            raise NotImplementedError  # ...but not yet

        return vectorSimilarity(dict(vector1[2]), dict(vector2[2]))

    # Internal API for stores

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        """Return a string serialization representing the term.

        Return a string serialization representing the term for storage
        purposes. Used as a callback from IndexStore to serialize a list of
        terms and document references to be stored.

        termId  := numeric ID of term being serialized
        data    := list of longs
        nRecs   := number of Records containing the term, if known
        nOccs   := total occurrences of the term, if known
        """
        # in: list of longs
        if not nRecs:
            nRecs = len(data) / 3
        if not nOccs:
            nOccs = sum(data[2::3])
        fmt = '<' + 'lll' * (nRecs + 1)
        params = [fmt, termId, nRecs, nOccs] + data
        try:
            return struct.pack(*params)
        except:
            self.log_critical(session, 'Error while serializing index term.\n'
                              'HINT: are you trying to put proximity '
                              'information into a SimpleIndex?\n')
            raise

    def deserialize_term(self, session, data, nRecs=-1, prox=1):
        """Deserialize and return the internal representation of a term.

        Return the internal representation of a term as recreated from a
        string serialization from storage. Used as a callback from IndexStore
        to take serialized data and produce list of terms and document
        references.

        data  := string (usually retrieved from indexStore)
        nRecs := number of Records to deserialize (all by default)
        prox  := boolean flag to include proximity information
        """
        if nRecs == -1:
            fmt = '<' + 'lll' * (len(data) / (3 * self.longStructSize))
            return struct.unpack(fmt, data)
        else:
            fmt = '<' + "lll" * (nRecs + 1)
            endpoint = (nRecs + 1) * 3 * self.longStructSize
            return struct.unpack(fmt, data[:endpoint])

    def calc_sectionOffsets(self, session, start, nRecs, dataLen=0):
        #tid, recs, occs, (store, rec, freq)+
        a = (self.longStructSize * 3) + (self.longStructSize * start * 3)
        b = (self.longStructSize * 3 * nRecs)
        return [(a, b)]

    def merge_term(self, session, currentData, newData,
                   op="replace", nRecs=0, nOccs=0):
        """Merge newData into currentData and return the result.

        Merging takes the currentData and can add, replace or delete the data
        found in newData, and then returns the result. Used as a callback from
        IndexStore to take two sets of terms and merge them together.

        currentData := output of deserialize_terms
        newData     := flat list
        op          := replace | add | delete
        nRecs       := total records in newData
        nOccs       := total occurrences in newdata
        """
        (termid, oldTotalRecs, oldTotalOccs) = currentData[0:3]
        currentData = list(currentData[3:])

        if op == 'add':
            currentData.extend(newData)
            if nRecs:
                trecs = oldTotalRecs + nRecs
                toccs = oldTotalOccs + nOccs
            else:
                trecs = oldTotalRecs + len(newData) / 3
                toccs = oldTotalOccs + sum(newData[2::3])
        elif op == 'replace':
            for n in range(0, len(newData), 3):
                docid = newData[n]
                storeid = newData[n + 1]
                replaced = 0
                for x in range(3, len(currentData), 3):
                    if (currentData[x] == docid and
                        currentData[x + 1] == storeid):
                        currentData[x + 2] = newData[n + 2]
                        replaced = 1
                        break
                if not replaced:
                    currentData.extend([docid, storeid, newData[n + 2]])
            trecs = len(currentData) / 3
            toccs = sum(currentData[2::3])
        elif op == 'delete':
            for n in range(0, len(newData), 3):
                docid = newData[n]
                storeid = newData[n + 1]
                for x in range(0, len(currentData), 3):
                    if (currentData[x] == docid and
                        currentData[x + 1] == storeid):
                        del currentData[x:(x + 3)]
                        break
            trecs = len(currentData) / 3
            toccs = sum(currentData[2::3])
        merged = [termid, trecs, toccs] + currentData
        return merged

    def construct_resultSet(self, session, terms, queryHash={}):
        """Create and return a ResultSet.

        Take a list of the internal representation of terms, as stored in this
        Index, create and return an appropriate ResultSet object.
        """
        # in: unpacked
        # out: resultSet
        l = len(terms)
        ci = self.indexStore.construct_resultSetItem
        s = self.resultSetClass(session, [])
#        rsilist = []
#        for t in range(3,len(terms),3):
#            item = ci(session, terms[t], terms[t+1], terms[t+2])
#            item.resultSet = s
#            rsilist.append(item)
#
#        s.fromList(rsilist)
        # Filter out duplicates
        rsis = {}
        for t in range(3, len(terms), 3):
            if terms[t] not in rsis:
                item = ci(session, terms[t], terms[t + 1], terms[t + 2])
                item.resultSet = s
                rsis[item.id] = (t, item)
        # Keep them in order
        s.fromList([r[1] for r in sorted(rsis.values())])
        s.index = self
        if queryHash:
            s.queryTerm = queryHash['text']
            s.queryFreq = queryHash['occurences']
        if (terms):
            s.termid = terms[0]
            s.totalRecs = terms[1]
            s.totalOccs = terms[2]
        else:
            s.totalRecs = 0
            s.totalOccs = 0
        return s

    # pass-throughs to indexStore

    def construct_resultSetItem(self, session, term,
                                rsiType="SimpleResultSetItem"):
        return self.indexStore.construct_resultSetItem(session, term[0],
                                                       term[1], term[2],
                                                       rsiType)

    def clear(self, session):
        self.indexStore.clear_index(session, self)

    def store_terms(self, session, data, rec):
        self.indexStore.store_terms(session, self, data, rec)

    def fetch_term(self, session, term, summary=False, prox=True):
        return self.indexStore.fetch_term(session, self, term, summary, prox)

    def fetch_termList(self, session, term, nTerms=0,
                       relation="", end="", summary=0):
        return self.indexStore.fetch_termList(session, self, term, nTerms,
                                              relation, end, summary)

    def fetch_termById(self, session, termId):
        return self.indexStore.fetch_termById(session, self, termId)

    def fetch_vector(self, session, rec, summary=False):
        return self.indexStore.fetch_vector(session, self, rec, summary)

    def fetch_proxVector(self, session, rec, elemId=-1):
        return self.indexStore.fetch_proxVector(session, self, rec, elemId)

    def fetch_summary(self, session):
        return self.indexStore.fetch_summary(session, self)

    def fetch_termFrequencies(self, session, mType='occ',
                              start=0, nTerms=100, direction=">"):
        return self.indexStore.fetch_termFrequencies(session, self, mType,
                                                     start, nTerms, direction)

    def fetch_metadata(self, session):
        return self.indexStore.fetch_indexMetadata(session, self)

    def fetch_sortValue(self, session, rec, ascending=True):
        return self.indexStore.fetch_sortValue(session, self, rec, ascending)

    def merge_tempFiles(self, session):
        return self.indexStore.merge_tempFiles(session, self)

    def commit_centralIndexing(self, session, filename=""):
        return self.indexStore.commit_centralIndexing(session, self, filename)


class SingleRecordStoreIndex(SimpleIndex):
    """Index implementation that assumes there is only 1 RecordStore.

    For single RecordStore cases this makes the index smaller and hence faster.
    Also enables compatibility with basic (non-proximity) Cheshire 2 index
    files.
    """

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        """Return a string serialization representing the term.

        Return a string serialization representing the term for storage
        purposes. Used as a callback from IndexStore to serialize a list of
        terms and document references to be stored.

        termId  := numeric ID of term being serialized
        data    := list of longs
        nRecs   := number of Records containing the term, if known
        nOccs   := total occurrences of the term, if known
        """
        # in: list of longs
        if not nRecs:
            nRecs = len(data) / 3
        if not nOccs:
            nOccs = sum(data[2::3])
        # strip out RecordStore pointer
        del data[1::3]
        fmt = '<' + 'lll' + ('ll' * nRecs)
        params = [fmt, termId, nRecs, nOccs] + data
        try:
            return struct.pack(*params)
        except:
            self.log_critical(session,
                              'Error while serializing index term.\n'
                              'HINT: are you trying to put proximity '
                              'information into a SimpleIndex?\n')
            raise

    def deserialize_term(self, session, data, nRecs=-1, prox=1):
        """Deserialize and return the internal representation of a term.

        Return the internal representation of a term as recreated from a
        string serialization from storage. Used as a callback from IndexStore
        to take serialized data and produce list of terms and document
        references.

        data  := string (usually retrieved from indexStore)
        nRecs := number of Records to deserialize (all by default)
        prox  := boolean flag to include proximity information
        """
        lss = self.longStructSize
        if nRecs == -1:
            fmt = '<' + 'l' * (len(data) / lss)
            out = list(struct.unpack(fmt, data))
        else:
            fmt = '<' + "lll" + "ll" * nRecs
            endpoint = (3 * lss) + (nRecs * 2 * lss)
            out = list(struct.unpack(fmt, data[:endpoint]))
        # Insert assumed RecordStore pointers
        for x in range(4, 3 + (3 * (len(out[3:]) / 2)), 3):
            out.insert(x, 0)
        return out

    def calc_sectionOffsets(self, session, start, nRecs, dataLen=0):
        # tid, recs, occs, (rec, freq)+
        a = (self.longStructSize * 3) + (self.longStructSize * start * 2)
        b = (self.longStructSize * 2 * nRecs)
        return [(a, b)]


class ProximityIndex(SimpleIndex):
    """Index that can store term locations to enable proximity search.

    An Index that can store element, word and character offset location
    information for term entries, enabling phrase, adjacency searches etc.

    Need to use an Extractor with prox setting and a ProximityTokenMerger
    """

    canExtractSection = 0
    _possibleSettings = {
        'nProxInts': {
            'docs': ("Number of integers per occurence in this index for "
                     "proximity information, typically 2 "
                     "(elementId, wordPosition) or "
                     "3 (elementId, wordPosition, byteOffset)"),
            'type': int
        }
    }

    def __init__(self, session, config, parent):
        SimpleIndex.__init__(self, session, config, parent)
        self.nProxInts = self.get_setting(session, 'nProxInts', 2)

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        # in: list of longs
        fmt = '<' + 'l' * (len(data) + 3)
        params = [fmt, termId, nRecs, nOccs] + data
        try:
            val = struct.pack(*params)
        except:
            self.log_critical(session,
                              "%s failed to pack: %r" % (self.id, params))
            raise
        return val

    def deserialize_term(self, session, data, nRecs=-1, prox=1):
        fmt = '<' + 'l' * (len(data) / self.longStructSize)
        flat = struct.unpack(fmt, data)
        (termid, totalRecs, totalOccs) = flat[:3]
        idx = 3
        docs = [termid, totalRecs, totalOccs]
        while idx < len(flat):
            doc = list(flat[idx:idx + 3])
            nidx = idx + 3 + (doc[2] * self.nProxInts)
            doc.extend(flat[idx + 3:nidx])
            idx = nidx
            docs.append(doc)
        return docs

    def merge_term(self, session, currentData, newData,
                   op="replace", nRecs=0, nOccs=0):
        # in: struct: deserialised, new: flag
        # out: flat

        (termid, oldTotalRecs, oldTotalOccs) = currentData[0:3]
        currentData = list(currentData[3:])

        if op == 'add':
            # flatten
            terms = []
            for t in currentData:
                terms.extend(t)
            terms.extend(newData)
            currentData = terms
            if nRecs != 0:
                trecs = oldTotalRecs + nRecs
                toccs = oldTotalOccs + nOccs
            else:
                # ...
                trecs = oldTotalRecs + len(newData)
                toccs = oldTotalOccs
                for t in newData:
                    toccs = toccs + t[2]
                raise ValueError("FIXME:  mergeTerms needs recs/occs params")

        elif op == 'replace':
            recs = [(x[0], x[1]) for x in currentData]
            newOccs = 0
            idx = 0
            while idx < len(newData):
                end = idx + 3 + (newData[idx + 2] * self.nProxInts)
                new = list(newData[idx:end])
                idx = end
                docid = new[0]
                storeid = new[1]
                if (docid, storeid) in recs:
                    loc = recs.index((docid, storeid))
                    # subtract old occs
                    occs = currentData[loc][2]
                    newOccs -= occs
                    currentData[loc] = new
                else:
                    currentData.append(new)
                newOccs += new[2]
            trecs = len(currentData)
            toccs = oldTotalOccs + newOccs
            # now flatten currentData
            n = []
            for s in currentData:
                n.extend(s)
            currentData = n

        elif op == 'delete':
            delOccs = 0
            idx = 0
            while idx < len(newData):
                doc = list(newData[idx:idx + 3])
                idx = idx + 3 + (doc[2] * self.nProxInts)
                for x in range(len(currentData)):
                    old = currentData[x]
                    if old[0] == doc[0] and old[1] == doc[1]:
                        delOccs = delOccs + old[2]
                        del currentData[x]
                        break
            trecs = len(currentData) - 3
            toccs = oldTotalOccs - delOccs
            # now flatten
            terms = []
            for t in currentData:
                terms.extend(t)
            currentData = terms

        merged = [termid, trecs, toccs]
        merged.extend(currentData)
        return merged

    def construct_resultSetItem(self, session, term, rsiType=""):
        # in: single triple
        # out: resultSetItem
        # Need to map recordStore and docid at indexStore
        item = self.indexStore.construct_resultSetItem(session, term[0],
                                                       term[1], term[2])
        item.proxInfo = term[3:]
        return item

    def construct_resultSet(self, session, terms, queryHash={}):
        # in: unpacked
        # out: resultSet
        rsilist = []
        ci = self.indexStore.construct_resultSetItem
        s = self.resultSetClass(session, [])
        for t in terms[3:]:
            item = ci(session, t[0], t[1], t[2])
            pi = t[3:]
            item.proxInfo = [
                             [pi[x:(x + self.nProxInts)]]
                             for x
                             in range(0, len(pi), self.nProxInts)
                            ]
            item.resultSet = s
            rsilist.append(item)
        s.fromList(rsilist)
        s.index = self
        if queryHash:
            s.queryTerm = queryHash['text']
            s.queryFreq = queryHash['occurences']
            s.queryPositions = []
            # not sure about this nProxInts??
            try:
                for x in queryHash['positions'][1::self.nProxInts]:
                    s.queryPositions.append(x)
            except:
                # no queryPos?
                pass
        if (terms):
            s.termid = terms[0]
            s.totalRecs = terms[1]
            s.totalOccs = terms[2]
        else:
            s.totalRecs = 0
            s.totalOccs = 0
        return s


class XmlIndex(SimpleIndex):
    """Index to store terms as XML structure.

    e.g.::

        <rs tid="" recs="" occs="">
            <r i="DOCID" s="STORE" o="OCCS"/>
        </rs>

    """

    def __init__(self, session, config, parent):
        SimpleIndex.__init__(self, session, config, parent)
        # ping etree to initialize
        nothing = etree.fromstring("<xml/>")

    def _maybeCompress(self, xmlstr):
        compress = "0"
        if len(xmlstr) > 1000000:
            # compress
            compress = "1"
            outDoc = StringIO.StringIO()
            zfile = gzip.GzipFile(mode='wb', fileobj=outDoc, compresslevel=1)
            zfile.write(xmlstr)
            zfile.close()
            l = outDoc.tell()
            outDoc.seek(0)
            xmlstr = outDoc.read(l)
            outDoc.close()
        return compress + xmlstr

    def _maybeUncompress(self, data):
        compress = int(data[0])
        xmlstr = data[1:]
        if compress:
            # uncompress
            buff = StringIO.StringIO(xmlstr)
            zfile = gzip.GzipFile(mode='rb', fileobj=buff)
            xmlstr = zfile.read()
            zfile.close()
            buff.close()
        return xmlstr

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        # in: list of longs
        val = struct.pack('<lll', termId, nRecs, nOccs)
        xml = ['<rs tid="%s" recs="%s" occs="%s">' % (termId, nRecs, nOccs)]
        idx = 0
        for i in range(0, len(data), 3):
            xml.append('<r i="%s" s="%s" o="%s"/>' % data[i:i + 3])
        xml.append("</rs>")
        xmlstr = ''.join(xml)
        data = self._maybeCompress(xmlstr)
        final = val + data
        return final

    def deserialize_term(self, session, data, nRecs=-1, prox=1):
        lss3 = 3 * self.longStructSize
        fmt = '<lll'
        (termid, totalRecs, totalOccs) = struct.unpack(fmt, data[:lss3])
        xmlstr = self._maybeUncompress(data[lss3:])
        return [termid, totalRecs, totalOccs, xmlstr]

    def construct_resultSet(self, session, terms, queryHash={}):
        # in: [termid, recs, occs, XML]
        # out: resultSet
        rs = SimpleResultSet(session, [])
        if len(terms) < 3:
            # no data
            return rs
        rsilist = []
        #ci = self.indexStore.construct_resultSetItem
        # Parse xml
        doc = etree.fromstring(terms[3])
        rsi = None

        for elem in doc.iter():
            if elem.tag == 'rs':
                # extract any further rs info here
                pass
            elif elem.tag == 'r':
                # process a hit: i, s, o
                if rsi:
                    rsi.proxInfo = pi
                    rsilist.append(rsi)
                vals = [int(x) for x in elem.attrib.values()]
                rsi = SimpleResultSetItem(session, *vals)
                # rsi = ci(session, *vals)
                rsi.resultSet = rs
                pi = []
            elif elem.tag == 'p':
                # process prox info
                pi.append([[int(x) for x in elem.attrib.values()]])
        if rsi:
            rsi.proxInfo = pi
            rsilist.append(rsi)
        rs.fromList(rsilist)
        rs.index = self
        if queryHash:
            rs.queryTerm = queryHash['text']
            rs.queryFreq = queryHash['occurences']
            rs.queryPositions = []
            # Not sure about this nProxInts??
            try:
                for x in queryHash['positions'][1::self.nProxInts]:
                    rs.queryPositions.append(x)
            except:
                # No queryPos?
                pass
        if (terms):
            rs.termid = terms[0]
            rs.totalRecs = terms[1]
            rs.totalOccs = terms[2]
        else:
            rs.totalRecs = 0
            rs.totalOccs = 0
        return rs


class XmlProximityIndex(XmlIndex):
    """ProximityIndex to store terms as XML structure.

    e.g.::

        <rs tid="" recs="" occs="">
          <r i="DOCID" s="STORE" o="OCCS">
            <p e="ELEM" w="WORDNUM" c="CHAROFFSET"/>
          </r>
        </rs>

    """

    _possibleSettings = {
        'nProxInts': {
            'docs': ("Number of integers per occurence in this index for "
                     "proximity information, typically 2 "
                     "(elementId, wordPosition) or "
                     "3 (elementId, wordPosition, byteOffset)"),
            'type': int
        }
    }

    def __init__(self, session, config, parent):
        XmlIndex.__init__(self, session, config, parent)
        self.nProxInts = self.get_setting(session, 'nProxInts', 2)

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        # in: list of longs
        npi = self.get_setting(session, 'nProxInts', 2)
        val = struct.pack('<lll', termId, nRecs, nOccs)
        xml = ['<rs tid="%s" recs="%s" occs="%s">' % (termId, nRecs, nOccs)]
        idx = 0
        while idx < len(data):
            xml.append('<r i="%s" s="%s" o="%s">' % tuple(data[idx:idx + 3]))
            if npi == 3:
                for x in range(data[idx + 2]):
                    xml.append('<p e="%s" w="%s" c="%s"/>' %
                               tuple(data[idx + 3 + (x * 3):idx + 6 + (x * 3)])
                               )
                idx = idx + idx + 6 + (x * 3)
            else:
                for x in range(data[idx + 2]):
                    p = tuple(data[idx + 3 + (x * 2):idx + 5 + (x * 2)])
                    xml.append('<p e="%s" w="%s"/>' % p)
                idx = idx + 5 + (x * 2)
            xml.append('</r>')
        xml.append("</rs>")
        xmlstr = ''.join(xml)
        data = self._maybeCompress(xmlstr)
        final = val + data
        return final


class RangeIndex(SimpleIndex):
    """Index to enable searching over one-dimensional range (e.g. time).

    Need to use a RangeTokenMerger
    """
    # 1 3 should match 1, 2, 3
    # a c should match a* b* c
    # unsure about this - RangeIndex only necessary for 'encloses' queries
    # Also appropriate for 'within', so implememnted - John

    def search(self, session, clause, db):
        # Check if we can just use SimpleIndex.search
        if (clause.relation.value not in ['encloses', 'overlaps', 'within',
                                          '>', '>=', '<', '<=', '>=<']):
            return SimpleIndex.search(self, session, clause, db)
        else:
            p = self.permissionHandlers.get('info:srw/operation/2/search',
                                            None)
            if p:
                if not session.user:
                    raise PermissionException("Authenticated user required to "
                                              "search index %s" % self.id)
                okay = p.hasPermission(session, session.user)
                if not okay:
                    raise PermissionException("Permission required to search "
                                              "index %s" % self.id)
            # Final destination. Process Term.
            res = {}
            # Try to get process for relation/modifier, failing that relation,
            # fall back to that used for data
            for src in self.sources.get(
                                        clause.relation.toCQL(),
                                        self.sources.get(clause.relation.value,
                                                         self.sources[u'data'])
                                    ):
                res.update(src[1].process(session, [[clause.term.value]]))
            store = self.get_path(session, 'indexStore')
            matches = []
            rel = clause.relation
            if (len(res) != 1):
                msg = "%s %s" % (clause.relation.toCQL(), clause.term.value)
                raise QueryException(msg, 24)
            keys = res.keys()[0].split('/', 1)
            startK = keys[0]
            endK = keys[1]
            rel = clause.relation.value
            if rel in ['encloses', '<', '<=']:
                # RangeExtractor should already return the range in ascending
                # order
                termList = store.fetch_termList(session, self,
                                                startK, relation='<')
                if rel == 'encloses':
                    # list comprehension is easier to understand
                    #termList = filter(lambda t: endK < t[0].split('/', 1)[1],
                    #                  termList)
                    termList = [t for t in termList
                                if (t[0].split('/', 1)[1] > endK)]
                elif rel == '<':
                    termList = [t for t in termList
                                if (t[0].split('/', 1)[1] < endK)]
                elif rel == '<=':
                    termList = [t for t in termList
                                if (t[0].split('/', 1)[1] <= endK)]
            elif rel == 'within':
                termList = store.fetch_termList(session, self,
                                                startK, end=endK)
                # List comprehension is easier to understand
                #termList = filter(lambda t: endK > t[0].split('/', 1)[1],
                #                  termList)
                termList = [t for t in termList
                            if (endK > t[0].split('/', 1)[1])]
            elif rel in ['overlaps', '>=<']:
                # Fetch all which start before the end point
                termList = store.fetch_termList(session, self,
                                                endK, relation='<=')
                # Filter for only those that end after start point
                termList = [t for t in termList
                            if (startK <= t[0].split('/', 1)[1])]
            elif rel.startswith('>'):
                termList = store.fetch_termList(session, self,
                                                endK, relation=rel)
            else:
                # This just SHOULD NOT have happened!...
                msg = '%s "%s"' % (clause.relation.toCQL(), clause.term.value)
                raise QueryException(msg, 24)
            matches.extend([self.construct_resultSet(session, t[1])
                            for t in termList])
            base = self.resultSetClass(session, [],
                                       recordStore=self.recordStore)
            base.recordStoreSizes = self.recordStoreSizes
            base.index = self
            if not len(matches):
                return base
            else:
                rs = base.combine(session, matches, clause, db)
                return rs


class BitmapIndex(SimpleIndex):
    # store as hex -- fast to generate, 1 byte per 4 bits.
    # eval to go from hex to long for bit manipulation

    _possiblePaths = {
        'recordStore': {
            "docs": ("The recordStore in which the records are kept "
                     "(as this info not maintained in the index)")
        }
    }

    def __init__(self, session, config, parent):
        SimpleIndex.__init__(self, session, config, parent)
        self.indexingData = SimpleBitfield()
        self.indexingTerm = ""
        self.recordStore = self.get_setting(session, 'recordStore', None)
        if not self.recordStore:
            rs = self.get_path(session, 'recordStore', None)
            if rs:
                self.recordStore = rs.id
        self.resultSetClass = BitmapResultSet

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        # in: list of longs
        if len(data) == 1 and isinstance(data[0], SimpleBitfield):
            # HACK.  Accept bitfield from mergeTerms
            bf = data[0]
        else:
            bf = SimpleBitfield()
            for item in data[::3]:
                bf[item] = 1
        pack = struct.pack('<lll', termId, nRecs, nOccs)
        val = pack + str(bf)
        return val

    def calc_sectionOffsets(self, session, start, nRecs, dataLen):
        # order is (of course) backwards
        # so we need length of data etc etc.
        start = (dataLen - (start / 4) + 1) - (nRecs / 4)
        packing = dataLen - (start + (nRecs / 4) + 1)
        return [(start, (nRecs / 4) + 1, '0x', '0' * packing)]

    def deserialize_term(self, session, data, nRecs=-1, prox=0):
        lsize = 3 * self.longStructSize
        longs = data[:lsize]
        terms = list(struct.unpack('<lll', longs))
        if len(data) > lsize:
            bf = SimpleBitfield(data[lsize:])
            terms.append(bf)
        return terms

    def merge_term(self, session, currentData, newData,
                   op="replace", nRecs=0, nOccs=0):
        (termid, oldTotalRecs, oldTotalOccs, oldBf) = currentData
        if op in['add', 'replace']:
            for t in newData[1::3]:
                oldBf[t] = 1
        elif op == 'delete':
            for t in newData[1::3]:
                oldBf[t] = 0
        trecs = oldBf.lenTrueItems()
        toccs = trecs
        merged = [termid, trecs, toccs, oldBf]
        return merged

    def construct_resultSetItem(self, session, term, rsiType=""):
        # in: single triple
        # out: resultSetItem
        # Need to map recordStore and docid at indexStore
        return self.indexStore.construct_resultSetItem(session, term[0],
                                                       term[1], term[2])

    def construct_resultSet(self, session, terms, queryHash={}):
        # in: unpacked
        # out: resultSet
        if len(terms) > 3:
            data = terms[3]
            s = BitmapResultSet(session, data, recordStore=self.recordStore)
        else:
            bmp = SimpleBitfield(0)
            s = BitmapResultSet(session, bmp, recordStore=self.recordStore)
        s.index = self
        if queryHash:
            s.queryTerm = queryHash['text']
            s.queryFreq = queryHash['occurences']
        if (terms):
            s.termid = terms[0]
            s.totalRecs = terms[1]
            s.totalOccs = terms[2]
        else:
            s.totalRecs = 0
            s.totalOccs = 0
        return s


class RecordIdentifierIndex(Index):

    _possibleSettings = {
        'recordStore': {
            "docs": ("The recordStore in which the records are kept "
                     "(as this info not maintained in the index)")
            }
    }

    def begin_indexing(self, session):
        pass

    def commit_indexing(self, session):
        pass

    def index_record(self, session, rec):
        return rec

    def delete_record(self, session, rec):
        pass

    def clear(self, session):
        pass

    def scan(self, session, clause, nTerms, direction):
        raise NotImplementedError()

    def search(self, session, clause, db):
        # Copy data from clause to resultSetItem after checking exists
        recordStore = self.get_path(session, 'recordStore')
        base = SimpleResultSet(session)
        if clause.relation.value in ['=', 'exact']:
            t = clause.term.value
            if t.isdigit():
                t = long(t)
            if recordStore.fetch_metadata(session, t, 'wordCount') > -1:
                item = SimpleResultSetItem(session)
                item.id = t
                item.recordStore = recordStore.id
                item.database = db.id
                items = [item]
            else:
                items = []
        elif clause.relation.value == 'any':
            # split on whitespace
            terms = clause.term.value.split()
            items = []
            for t in terms:
                if t.isdigit():
                    t = long(t)
                if recordStore.fetch_metadata(session, t, 'wordCount') > -1:
                    item = SimpleResultSetItem(session)
                    item.id = t
                    item.database = db.id
                    item.recordStore = recordStore.id
                    items.append(item)
        elif (clause.relation.value in ['<', '<='] and
              clause.term.value.isdigit()):
            t = long(clause.term.value)
            if clause.relation.value == '<':
                terms = range(t)
            else:
                terms = range(t + 1)

            items = []
            for t in terms:
                if recordStore.fetch_metadata(session, t, 'wordCount') > -1:
                    item = SimpleResultSetItem(session)
                    item.id = t
                    item.database = db.id
                    item.recordStore = recordStore.id
                    items.append(item)
        else:
            msg = '%s "%s"' % (clause.relation.toCQL(), clause.term.value)
            raise QueryException(msg, 24)

        base.fromList(items)
        base.index = self
        return base


# rec.checksumValue
class ReverseMetadataIndex(Index):

    _possiblePaths = {
        'recordStore': {
            "docs": ("The recordStore in which the records are kept "
                     "(as this info not maintained in the index)")
        }
    }

    _possibleSettings = {
        'metadataType': {
            "docs": ("The type of metadata to provide an 'index' for. "
                     "Defaults to digestReverse.")
        }
    }

    def begin_indexing(self, session):
        pass

    def commit_indexing(self, session):
        pass

    def index_record(self, session, rec):
        return record

    def delete_record(self, session, rec):
        pass

    def clear(self, session):
        pass

    def scan(self, session, clause, nTerms, direction):
        raise NotImplementedError()

    def search(self, session, clause, db):
        mtype = self.get_setting(session, 'metadataType', 'digestReverse')
        recordStore = self.get_path(session, 'recordStore')
        base = SimpleResultSet(session)
        if clause.relation.value in ['=', 'exact']:
            t = clause.term.value
            rid = recordStore.fetch_metadata(session, t, mtype)
            if rid:
                item = SimpleResultSetItem(session)
                item.id = rid
                item.recordStore = recordStore.id
                item.database = db.id
                items = [item]
            else:
                items = []
        elif clause.relation.value == 'any':
            # Split on whitespace
            terms = clause.term.value.split()
            items = []
            for t in terms:
                rid = recordStore.fetch_metadata(session, t, mtype)
                if rid:
                    item = SimpleResultSetItem(session)
                    item.id = rid
                    item.database = db.id
                    item.recordStore = recordStore.id
                    items.append(item)
        base.fromList(items)
        base.index = self
        return base


class PassThroughIndex(SimpleIndex):
    """Special Index pull in search terms from another Database."""

    def _handleLxmlConfigNode(self, session, node):
        # Source
        if node.tag in ['xpath', '{%s}xpath' % CONFIG_NS,
                         'selector', '{%s}selector' % CONFIG_NS]:
            ref = node.attrib.get('{%s}ref' % CONFIG_NS,
                                  node.attrib.get('ref', ''))
            if ref:
                xp = self.get_object(session, ref)
            else:
                xp = SimpleXPathProcessor(session, node, self)
                xp.sources = [[xp._handleLxmlLocationNode(session, node)]]
            self.xpath = xp

    def _handleConfigNode(self, session, node):
        # Source
        if (node.localname in ["xpath", "selector"]):
            ref = node.getAttributeNS('ref')
            if ref:
                xp = self.get_object(session, ref)
            else:
                xp = SimpleXPathProcessor(session, node, self)
                xp.sources = [[xp._handleLocationNode(session, node)]]
            self.xpath = xp

    def __init__(self, session, config, parent):
        self.xpath = None
        SimpleIndex.__init__(self, session, config, parent)
        dbStr = self.get_path(session, 'database', '')
        if not dbStr:
            raise ConfigFileException("No remote database given in "
                                      "%s" % self.id)
        db = session.server.get_object(session, dbStr)
        if not db:
            raise ConfigFileException("Unknown remote database given in "
                                      "%s" % self.id)
        self.database = db

        idxStr = self.get_path(session, 'remoteIndex', "")
        if not idxStr:
            raise ConfigFileException("No remote index given in %s" % self.id)
        idx = db.get_object(session, idxStr)
        if not idx:
            msg = ("Unknown index %s in remote database %s for %s" %
                   (idxStr, db.id, self.id))
            raise ConfigFileException(msg)
        self.remoteIndex = idx

        idxStr = self.get_path(session, 'remoteKeyIndex', "")
        if idxStr:
            idx = db.get_object(session, idxStr)
            if not idx:
                msg = ("Unknown index %s in remote database %s for %s" %
                       (idxStr, db.id, self.id))
                raise ConfigFileException(msg)
            self.remoteKeyIndex = idx
        else:
            self.remoteKeyIndex = None

        idx = self.get_path(session, 'localIndex', None)
        if not idx:
            raise ConfigFileException("No local index given in %s" % self.id)
        self.localIndex = idx

    def search(self, session, clause, db):
        # First do search on remote index
        currDb = session.database
        session.database = self.database.id
        rs = self.remoteIndex.search(session, clause, self.database)
        # Fetch all matched records
        values = {}
        for rsi in rs:
            rec = rsi.fetch_record(session)
            # Process xpath
            try:
                value = self.xpath.process_record(session, rec)[0][0]
            except:
                # No data where we expect it
                continue
            if value:
                values[value] = 1

        # Construct search from keys and return local search
        localq = cql.parse('c3.%s any "%s"' %
                           (self.localIndex.id, ' '.join(values.keys())))
        session.database = currDb
        return self.localIndex.search(session, localq, db)

    def scan(self, session, clause, nTerms, direction=">="):
        """Scan remote index.

        Note Well:  If term in remote doesn't appear, it's still included
        with trecs and toccs of 0.  termid is always -1 as it's meaningless
        in the local context -- could be multiple or 0
        """
        currDb = session.database
        session.database = self.database.id
        scans = self.remoteIndex.scan(session, clause, nTerms,
                                      direction, summary=0)
        if not scans:
            return []
        newscans = []
        storeHash = {}
        end = 0
        endMarker = ''
        while True:
            for info in scans:
                if len(info) == 3:
                    end = 1
                    endMarker = info[2]
                term = info[0]
                termInfo = info[1]
                trecs = 0
                toccs = 0
                termid = -1
                # Construct result set is more portable but slower
                rs = self.remoteIndex.construct_resultSet(session, termInfo)
                for rsi in rs:
                    rec = rsi.fetch_record(session)
                    # process xpath
                    try:
                        value = self.xpath.process_record(session, rec)[0][0]
                    except:
                        # no data where we expect it
                        continue
                    info = self.localIndex.fetch_term(session, value,
                                                      summary=1, prox=0)
                    if info:
                        trecs += info[1]
                        toccs += info[2]
                if trecs:
                    newscans.append([term, [termid, trecs, toccs]])

                    if endMarker != '':
                        newscans[-1].append(endMarker)
                        endMarker = ''

            if (not end) and len(newscans) < nTerms + 1:
                # fetch new scans
                clause.term.value = scans[-1][0]
                if direction == "<=":
                    direction = "<"
                elif direction == ">=":
                    direction = ">"
                scans = self.remoteIndex.scan(session, clause, 10,
                                              direction, summary=0)
            else:
                break
        if endMarker != '' and len(newscans):
            newscans[-1].append(endMarker)
        return newscans[:nTerms]

    def fetch_sortValue(self, session, rec, ascending=True):
        if not self.remoteKeyIndex:
            return ''
        key = self.localIndex.fetch_sortValue(session, rec, ascending)
        if not key:
            return ''
        currDb = session.database
        session.database = self.database.id
        q = cql.parse('c3.%s exact "%s"' % (self.remoteKeyIndex.id, key))
        rs = self.remoteKeyIndex.search(session, q, self.database)
        if rs:
            sv = self.remoteIndex.fetch_sortValue(session, rs[0], ascending)
        else:
            sv = ''
        session.database = currDb
        return sv

    # No need to do anything during indexing
    def begin_indexing(self, session):
        pass

    def commit_indexing(self, session):
        pass

    def index_record(self, session, rec):
        return rec

    def delete_record(self, session, rec):
        pass
