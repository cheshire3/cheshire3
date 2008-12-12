
from cheshire3.baseObjects import Index, Document, Session
from cheshire3.configParser import C3Object
from cheshire3.utils import elementType, getFirstData, flattenTexts
from cheshire3.exceptions import ConfigFileException, QueryException
from cheshire3.record import SaxRecord, DomRecord
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem
from cheshire3.workflow import CachingWorkflow
from cheshire3.xpathProcessor import SimpleXPathProcessor
import cheshire3.cqlParser as cql

import re, types, sys, os, struct, time

import codecs
import gzip, StringIO
from lxml import etree


class IndexIter(object):
    index = None
    session = None

    def __init__(self, index):
        self.index = index
        self.indexStore = index.indexStore
        self.session = Session()
        self.summary = 0
        # populate with first term
        self.nextData = self.indexStore.fetch_termList(self.session, self.index, "", 1)[0]

    def __iter__(self):
        return self

    def next(self):
        try:
            d = self.nextData
            if not d:
                raise StopIteration()
            if d[-1] == 'last':
                self.nextData = ""
            else:
                try:
                    self.nextData = self.indexStore.fetch_termList(self.session, self.index, d[0], 2)[1]
                except IndexError:
                    self.nextData = ""
            return self.index.construct_resultSet(self.session, d[1], queryHash={'text':d[0], 'occurences': 1, 'positions' : []})
        except:
            # fail safe
            raise StopIteration()

    def jump(self, position):
        # Jump to this position
        self.nextData = self.indexStore.fetch_termList(self.session, self.index, position, 1)[0]
        return self.index.construct_resultSet(self.session, self.nextData[1], queryHash={'text':self.nextData[0], 'occurences': 1, 'positions' : []})



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

    _possiblePaths = {'indexStore' : {"docs" : "IndexStore identifier for where this index is stored"}
                      , 'termIdIndex' : {"docs" : "Alternative index object to use for termId for terms in this index."}
                      , 'tempPath' : {"docs" : "Path to a directory where temporary files will be stored during batch mode indexing"}
                      }

    _possibleSettings = {'cori_constant0' : {"docs" : "", 'type' : float},
                         'cori_constant1' : {"docs" : "", 'type' : float},
                         'cori_constant2' : {"docs" : "", 'type' : float},
                         'lr_constant0' : {"docs" : "", 'type' : float},
                         'lr_constant1' : {"docs" : "", 'type' : float},
                         'lr_constant2' : {"docs" : "", 'type' : float},
                         'lr_constant3' : {"docs" : "", 'type' : float},
                         'lr_constant4' : {"docs" : "", 'type' : float},
                         'lr_constant5' : {"docs" : "", 'type' : float},
                         'lr_constant6' : {"docs" : "", 'type' : float},
                         'noIndexDefault' : {"docs" : "If true, the index should not be called from db.index_record()", "type" : int, "options" : "0|1"},
                         'noUnindexDefault' : {"docs" : "If true, the index should not be called from db.unindex_record()", "type" : int, "options" : "0|1"},
                         'sortStore' : {"docs" : "Should the index build a sort store", 'type' : int, 'options' : '0|1'},
                         'termIds' : {"docs" : "Should the index store termId -> term", 'type' : int, 'options' : '0|1'},
                         'vectors' : {"docs" : "Should the index store vectors (doc -> list of termIds.", 'type' : int, 'options' : '0|1'},
                         'proxVectors' : {"docs" : "Should the index store vectors that also maintain proximity for their terms", 'type' : int, 'options' : '0|1'},
                         'minimumSupport' : {"docs" : "Minimum number of records in which the term must appear for it to be indexed at all", 'type' : int},
                         'vectorMinGlobalFreq' : {"docs" : "Minimum global records for term to appear in a vector", 'type' : int},
                         'vectorMaxGlobalFreq' : {"docs" : "Maximum global records for term to appear in a vector", 'type' : int},
                         'vectorMinGlobalOccs' : {"docs" : "Minimum global occurences", 'type' : int},
                         'vectorMaxGlobalOccs' : {"docs" : "Maximum global occurences", 'type' : int},
                         'vectorMinLocalFreq' : {"docs" : "Minimum records in selected", 'type' : int},
                         'vectorMaxLocalFreq' : {"docs" : "Maximum records in selected", 'type' : int},
                         'freqList' : {'docs' : 'Store a frequency sorted list to step through of records, occurences or both', 'options' : 'rec|occ|rec occ|occ rec'},
                         'longSize' : {"docs" : "Size of a long integer in this index's underlying data structure (eg to migrate between 32 and 64 bit platforms)", 'type' : int},
                         'recordStoreSizes' : {"docs" : "Should we use recordStore sizes instead of database sizes", 'type' : int},
                         'maxVectorCacheSize' : {'docs' : "Number of terms to cache when building vectors", 'type' :int}
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
                    if child.localName == "xpath":
                        if xp == None:
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
                                newTop = child.ownerDocument.createElementNS(None, 'workflow')
                                for kid in child.childNodes:
                                    newTop.appendChild(kid)
                                child = newTop
                            process = CachingWorkflow(session, child, self)
                            process._handleConfigNode(session, child)

            for m in modes:
                self.sources.setdefault(m, []).append((xp, process, preprocess))


    def _handleLxmlConfigNode(self, session, node):
        # Source
        if (node.tag == "source"):
            modes = node.attrib.get('mode', 'data')
            modes = modes.split('|')
            process = None
            preprocess = None
            xp = None
            for child in node.iterchildren(tag=etree.Element):
                if child.tag == "xpath":
                    if xp == None:
                        ref = child.attrib.get('ref', '')
                        if ref:
                            xp = self.get_object(session, ref)
                        else:
                            node.set('id', self.id + '-xpath')
                            xp = SimpleXPathProcessor(session, node, self)
                            xp._handleLxmlConfigNode(session, node)
                elif child.tag == "preprocess":
                    # turn preprocess chain to workflow
                    ref = child.attrib.get('ref', '')
                    if ref:
                        preprocess = self.get_object(session, ref)
                    else:
                        # create new element
                        e = etree.XML(etree.tostring(child))
                        e.tag = 'workflow'
                        e.set('id', self.id + "-preworkflow")
                        preprocess = CachingWorkflow(session, child, self)
                        preprocess._handleLxmlConfigNode(session, child)
                elif child.tag == "process":
                    # turn xpath chain to workflow
                    ref = child.attrib.get('ref', '')
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
                self.sources.setdefault(m, []).append((xp, process, preprocess))


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
            self.longStructSize = len(struct.pack('L', 1))
            
        
        self.recordStoreSizes = self.get_setting(session, 'recordStoreSizes', 0)
        # We need a Store object
        iStore = self.get_path(session, 'indexStore', None)
        self.indexStore = iStore

        if (iStore == None):
            raise(ConfigFileException("Index (%s) does not have an indexStore." % (self.id)))
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
        term = term.replace('.', r'\.')          # escape existing special regex chars
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
            rawlist = xpath.process_record(session, record)
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
                raise PermissionException("Authenticated user required to add to index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to index %s" % self.id)

        if 'sort' in self.sources:
            sortHash = self._processRecord(session, rec, self.sources[u'sort'][0])
            if sortHash:
                sortVal = sortHash.keys()[0]
            else:
                sortVal = ''
        else:
            sortVal = ''

        for src in self.sources[u'data']:
            processed = self._processRecord(session, rec, src)
            if sortVal:
                # don't blank sortVal, or will be overwritten in subsequent iters
                k = processed.keys()[0]
                processed[k]['sortValue'] = sortVal
            self.indexStore.store_terms(session, self, processed, rec)
        return rec

    def delete_record(self, session, rec):
        # Extract terms, and remove from store
        p = self.permissionHandlers.get('info:srw/operation/2/unindex', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to remove from index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to remove from index %s" % self.id)
        istore = self.get_path(session, 'indexStore')

        if self.get_setting(session, 'vectors', 0):
            # use vectors to unindex instead of reprocessing
            # faster, only way for 'now' metadata.
            vec = self.fetch_vector(session, rec)
            # [totalUniqueTerms, totalFreq, [(tid, freq)+]]
            processed = {}
            for (t,f) in vec[2]:
                term = self.fetch_termById(session, t)
                processed[term] = {'occurences' : f}
            if istore != None:
                istore.delete_terms(session, self, processed, rec)
        else:
            for src in self.sources[u'data']:
                processed = self._processRecord(session, rec, src)
                if (istore != None):
                    istore.delete_terms(session, self, processed, rec)
                
    def begin_indexing(self, session):
        # Find all indexStores
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add to index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to index %s" % self.id)
        stores = []
        istore = self.get_path(session, 'indexStore')
        if (istore != None and not istore in stores):
            stores.append(istore)
        for s in stores:
            s.begin_indexing(session, self)


    def commit_indexing(self, session):
        p = self.permissionHandlers.get('info:srw/operation/2/index', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to add to index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to add to index %s" % self.id)
        stores = []
        istore = self.get_path(session, 'indexStore')
        if (istore != None and not istore in stores):
            stores.append(istore)
        for s in stores:
            s.commit_indexing(session, self)


    def search(self, session, clause, db):
        # Final destination. Process Term.
        p = self.permissionHandlers.get('info:srw/operation/2/search', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to search index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to search index %s" % self.id)

        res = {}
        # src = (xp, processwf, preprocesswf)
        # try to get process for relation/modifier, failing that relation, fall back to that used for data
        for src in self.sources.get(clause.relation.toCQL(), self.sources.get(clause.relation.value, self.sources[u'data'])):
            res.update(src[1].process(session, [[clause.term.value]]))

        store = self.get_path(session, 'indexStore')
        matches = []
        rel = clause.relation
        if (rel.prefix == 'cql' or rel.prefixURI == 'info:srw/cql-context-set/1/cql-v1.1'):
            if (rel.value == 'scr'):
                pm = db.get_path(session, 'protocolMap')
                try:
                    rel.value = pm.defaultRelation
                except AttributeError:
                    pass
            

        if (rel.value in ['any', 'all', '=', 'exact', 'window'] and (rel.prefix == 'cql' or rel.prefixURI == 'info:srw/cql-context-set/1/cql-v1.1')):
            for k, qHash in res.iteritems():
                if k[0] == '^': k = k[1:]      
                firstMask = self._locate_firstMask(k)
                while (firstMask > 0) and (k[firstMask-1] == '\\'):
                    firstMask = self._locate_firstMask(k, firstMask+1)
                # TODO: slow regex e.g. if first char is *
                if (firstMask > -1):
                    startK = k[:firstMask]
                    try: nextK = startK[:-1] + chr(ord(startK[-1])+1)
                    except IndexError:
                        # left truncation, all terms from the index
                        # TODO: we should check if there's a inversion of index keys
                        termList =  store.fetch_termList(session, self, startK, 0, '>=')
                    else:
                        termList =  store.fetch_termList(session, self, startK, 0, '>=', end=nextK)
                    
                    if len(k) > 1:
                        # filter terms by regex
                        # FIXME: need to do something cleverer than this if first character is masked
                        # this implementation will be incredibly slow for these cases...
                        if (firstMask < len(k)-1) or (k[firstMask] in ['?', '^']):
                            # not simply right hand truncation
                            kRe = re.compile(self._regexify_wildcards(k))
                            mymatch = kRe.match
                            termList = filter(lambda t: mymatch(t[0]), termList)
                    
                    maskBase = self.resultSetClass(session, [], recordStore=self.recordStore)
                    maskClause = cql.parse(clause.toCQL())
                    maskClause.relation.value = u'any'
                    if (clause.relation.value == u'='):
                        # tell combine to keep proxInfo
                        pass
                            
                    try:
                        maskResultSets = [self.construct_resultSet(session, t[1], qHash) for t in termList]
                        maskBase = maskBase.combine(session, maskResultSets, maskClause, db)
                        maskBase.queryTerm = qHash['text']
                        maskBase.queryPositions = qHash['positions']
                    except:
                        raise
                        pass
                    else:
                        matches.append(maskBase)
                                   
                elif (firstMask == 0):
                    # No longer used - better to be slow than to refuse to do a search.
                    pass
                else:
                    term = store.fetch_term(session, self, k)
                    s = self.construct_resultSet(session, term, qHash)
                    matches.append(s)
        elif (clause.relation.value in ['>=', '>', '<', '<=']):
            if (len(res) != 1):
                raise QueryException("%s %s" % (clause.relation.toCQL(), clause.term.value), 24)
            else:
                termList = store.fetch_termList(session, self, res.keys()[0], 0, clause.relation.value)
                for t in termList:
                    matches.append(self.construct_resultSet(session, t[1]))
        elif (clause.relation.value == "within"):
            if (len(res) != 2):
                raise QueryException('%s "%s"' % (clause.relation.toCQL(), clause.term.value), 24)
            else:
                termList = store.fetch_termList(session, self, res.keys()[0], end=res.keys()[1])
                matches.extend([self.construct_resultSet(session, t[1]) for t in termList])

        else:
            raise QueryException('%s "%s"' % (clause.relation.toCQL(), clause.term.value), 24)


        base = self.resultSetClass(session, [], recordStore=self.recordStore)
        base.recordStoreSizes = self.recordStoreSizes
        base.index = self
        if not matches:
            return base
        else:
            if clause.relation.value == "=" and not isinstance(self, ProximityIndex):
                # can't do prox!
                clause.relation.value = "all"
            rs = base.combine(session, matches, clause, db)
            return rs

    def scan(self, session, clause, nTerms, direction=">=", summary=1):
        # Process term.
        p = self.permissionHandlers.get('info:srw/operation/2/scan', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to scan index %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to scan index %s" % self.id)

        res = {}
        for src in self.sources.get(clause.relation.toCQL(), self.sources.get(clause.relation.value, self.sources[u'data'])):
            res.update(src[1].process(session, [[clause.term.value]]))

        if len(res) == 0:
            # no term, so start at the beginning
            res = {'' : ''}
        elif (len(res) != 1):
            raise QueryException("%s" % (clause.term.value), 24)
        store = self.get_path(session, 'indexStore')
        if direction == "=":
            k = res.keys()[0]
            if not k:
                k2 = "!"
            else:
                k2 = k[:-1] + chr(ord(k[-1])+1)
            tList = store.fetch_termList(session, self, k, nTerms=nTerms, end=k2, summary=summary, relation='>=')
        else:
            tList = store.fetch_termList(session, self, res.keys()[0], nTerms=nTerms, relation=direction, summary=summary)
        # list of (term, occs)
        return tList


    def facets(self, session, resultSet, nTerms=0):
        """ Return a list of terms from this index which co-occur within the records in resultSet.
            Terms are returned in ascending frequency (number of records) order.
        """
        termFreqs = {}
        recordFreqs = {}
        for r in resultSet:
            # use vectors to identify terms
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
                        
        # sort list by descending frequency (decorate-sort-undecorate)
        # use 1 / freq - keeps terms with same freq in alpha order
        sortList = [(1.0/v,k) for k,v in recordFreqs.iteritems()]
        sortList.sort()
        tids = [x[1] for x in sortList]
        if nTerms:
            tids = tids[:min(len(tids), nTerms)]
        terms = []
        for termId in tids:
            term = self.fetch_termById(session, termId)
            # (term, (termId, nRecs, freq))
            terms.append((term.decode('utf-8'), (termId, recordFreqs[termId], termFreqs[termId])))        
        return terms

    # Internal API for stores

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        # in: list of longs
        if not nRecs:
            nRecs = len(data) / 3
            nOccs = sum(data[2::3])
        fmt = 'lll' * (nRecs + 1)
        params = [fmt, termId, nRecs, nOccs] + data
        return struct.pack(*params)
        
    def deserialize_term(self, session, data, nRecs=-1, prox=1):
        if nRecs == -1:
            fmt = 'lll' * (len(data) / (3 * self.longStructSize))
            return struct.unpack(fmt, data)
        else:
            fmt = "lll" * (nRecs + 1)
            return struct.unpack(fmt, data[:(nRecs+1) *3 * self.longStructSize])

    def calc_sectionOffsets(self, session, start, nRecs, dataLen=0):
        #tid, recs, occs, (store, rec, freq)+
        a = (self.longStructSize * 3) + (self.longStructSize *start * 3)
        b = (self.longStructSize * 3 * nRecs)
        return [(a,b)]

    def merge_term(self, session, currentData, newData, op="replace", nRecs=0, nOccs=0):
        # structTerms = output of deserialiseTerms
        # newTerms = flat list
        # op = replace, add, delete
        # recs, occs = total recs/occs in newTerms

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
            for n in range(0,len(newData),3):
                docid = newData[n]
                storeid = newData[n+1]                
                replaced = 0
                for x in range(3, len(currentData), 3):
                    if currentData[x] == docid and currentData[x+1] == storeid:
                        currentData[x+2] == newData[n+2]
                        replaced = 1
                        break
                if not replaced:
                    currentData.extend([docid, storeid, newData[n+2]])
            trecs = len(currentData) / 3
            toccs = sum(currentData[2::3])
        elif op == 'delete':            
            for n in range(0,len(newData),3):
                docid = newData[n]
                storeid = newData[n+1]                
                for x in range(0, len(currentData), 3):
                    if currentData[x] == docid and currentData[x+1] == storeid:
                        del currentData[x:x+3]
                        break
            trecs = len(currentData) / 3
            toccs = sum(currentData[2::3])
                    
        merged = [termid, trecs, toccs] + currentData
        return merged

    def construct_resultSet(self, session, terms, queryHash={}):
        # in: unpacked
        # out: resultSet
        l = len(terms)        
        ci = self.indexStore.construct_resultSetItem

        s = self.resultSetClass(session, [])
        rsilist = []
        for t in range(3,len(terms),3):
            item = ci(session, terms[t], terms[t+1], terms[t+2])
            item.resultSet = s
            rsilist.append(item)
        s.fromList(rsilist)
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

    def construct_resultSetItem(self, session, term, rsiType="SimpleResultSetItem"):
        return self.indexStore.construct_resultSetItem(session, term[0], term[1], term[2], rsitype)

    def clear(self, session):
        self.indexStore.clear_index(session, self)

    def store_terms(self, session, data, rec):
        self.indexStore.store_terms(session, self, data, rec)

    def fetch_term(self, session, term, summary=False, prox=True):
        return self.indexStore.fetch_term(session, self, term, summary, prox)

    def fetch_termList(self, session, term, nTerms=0, relation="", end="", summary=0):
        return self.indexStore.fetch_termList(session, self, term, nTerms, relation, end, summary)

    def fetch_termById(self, session, termId):
        return self.indexStore.fetch_termById(session, self, termId)

    def fetch_vector(self, session, rec, summary=False):
        return self.indexStore.fetch_vector(session, self, rec, summary)

    def fetch_proxVector(self, session, rec, elemId=-1):
        return self.indexStore.fetch_proxVector(session, self, rec, elemId)

    def fetch_summary(self, session):
        return self.indexStore.fetch_summary(session, self)

    def fetch_termFrequencies(self, session, mType='occ', start=0, nTerms=100, direction=">"):
        return self.indexStore.fetch_termFrequencies(session, self, mType, start, nTerms, direction)

    def fetch_metadata(self, session):
        return self.indexStore.fetch_indexMetadata(session, self)

    def fetch_sortValue(self, session, rec):
        return self.indexStore.fetch_sortValue(session, self, rec)

    def merge_tempFiles(self, session):
        return self.indexStore.merge_tempFiles(session, self)

    def commit_centralIndexing(self, session, filename=""):
        return self.indexStore.commit_centralIndexing(session, self, filename)
    
        
class ProximityIndex(SimpleIndex):
    """ Need to use prox extractor """

    canExtractSection = 0
    _possibleSettings = {'nProxInts' : {'docs' : "Number of integers per occurence in this index for proximity information, typically 2 (elementId, wordPosition) or 3 (elementId, wordPosition, byteOffset)", 'type' : int}}

    def __init__(self, session, config, parent):
        SimpleIndex.__init__(self, session, config, parent)
        self.nProxInts = self.get_setting(session, 'nProxInts', 2)

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        # in: list of longs
        fmt = 'l' * (len(data) + 3)
        params = [fmt, termId, nRecs, nOccs] + data
        try:
            val =  struct.pack(*params)
        except:
            self.log_critical(session, "%s failed to pack: %r" % (self.id, params[:4]))
            raise
        return val
        
    def deserialize_term(self, session, data, nRecs=-1, prox=1):
        fmt = 'L' * (len(data) / self.longStructSize)
        flat = struct.unpack(fmt, data)
        (termid, totalRecs, totalOccs) = flat[:3]
        idx = 3
        docs = [termid, totalRecs, totalOccs]
        while idx < len(flat):
            doc = list(flat[idx:idx+3])
            nidx = idx + 3 + (doc[2]*self.nProxInts)
            doc.extend(flat[idx+3:nidx])
            idx = nidx
            docs.append(doc)
        return docs

    def merge_term(self, session, currentData, newData, op="replace", nRecs=0, nOccs=0):
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
                end = idx + 3 + (newData[idx+2]*self.nProxInts)
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
                doc = list(newData[idx:idx+3])
                idx = idx + 3 + (doc[2]*self.nProxInts)
                for x in range(len(currentData)):
                    old = currentData[x]
                    if old[0] == doc[0] and old[1] == doc[1]:
                        delOccs = delOccs + old[2]
                        del currentData[x]
                        break
            trecs = len(currentData) -3
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
        item = self.indexStore.construct_resultSetItem(session, term[0], term[1], term[2])
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
            item.proxInfo = [[pi[x:x+self.nProxInts]] for x in range(0, len(pi), self.nProxInts)]
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

    def __init__(self, session, config, parent):
        SimpleIndex.__init__(self, session, config, parent)
        # ping etree to initialize
        nothing = etree.fromstring("<xml/>")

    def _maybeCompress(self, xmlstr):
        compress = "0"
        if len(xmlstr) > 1000000:
            # compress
            compress="1"
            outDoc = StringIO.StringIO()
            zfile = gzip.GzipFile(mode = 'wb', fileobj=outDoc, compresslevel=1)
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
            zfile = gzip.GzipFile(mode = 'rb', fileobj=buff)
            xmlstr = zfile.read()
            zfile.close()
            buff.close()        
        return xmlstr

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        # in: list of longs
        val = struct.pack('lll', termId, nRecs,nOccs)
        xml = ['<rs tid="%s" recs="%s" occs="%s">' % (termId, nRecs, nOccs)]
        idx = 0
        for i in range(0, len(data), 3):
            xml.append('<r i="%s" s="%s" o="%s"/>' % data[i:i+3])
        xml.append("</rs>")
        xmlstr= ''.join(xml)
        data = self._maybeCompress(xmlstr)
        final = val + data
        return final
        
    def deserialize_term(self, session, data, nRecs=-1, prox=1):
        lss3 = 3*self.longStructSize
        fmt = 'lll'
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
        
        # parse xml
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
                
                rsi=SimpleResultSetItem(session, *vals)
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
            # not sure about this nProxInts??
	    try:
		for x in queryHash['positions'][1::self.nProxInts]:
		    rs.queryPositions.append(x)
	    except:
		# no queryPos?
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
    """Store term as XML structure:
<rs tid="" recs="" occs="">
  <r i="DOCID" s="STORE" o="OCCS">
    <p e="ELEM" w="WORDNUM" c="CHAROFFSET"/>
  </r>
</rs>
"""

    _possibleSettings = {'nProxInts' : {'docs' : "Number of integers per occurence in this index for proximity information, typically 2 (elementId, wordPosition) or 3 (elementId, wordPosition, byteOffset)", 'type' : int}}

    def __init__(self, session, config, parent):
        XmlIndex.__init__(self, session, config, parent)
        self.nProxInts = self.get_setting(session, 'nProxInts', 2)

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        # in: list of longs
        npi = self.get_setting(session, 'nProxInts', 2)
        val = struct.pack('lll', termId, nRecs,nOccs)

        xml = ['<rs tid="%s" recs="%s" occs="%s">' % (termId, nRecs, nOccs)]
        idx = 0
        while idx < len(data):
            xml.append('<r i="%s" s="%s" o="%s">' % tuple(data[idx:idx+3]))
            if npi == 3:
                for x in range(data[idx+2]):
                    xml.append('<p e="%s" w="%s" c="%s"/>' % tuple(data[idx+3+(x*3):idx+6+(x*3)]))
                idx = idx + idx+6+(x*3)
            else:
                for x in range(data[idx+2]):
                    p = tuple(data[idx+3+(x*2):idx+5+(x*2)])                    
                    xml.append('<p e="%s" w="%s"/>' % p)
                idx = idx +5+(x*2)
            xml.append('</r>')
            
        xml.append("</rs>")
        xmlstr= ''.join(xml)

        data = self._maybeCompress(xmlstr)
        final = val + data
        return final
        


class RangeIndex(SimpleIndex):
    """ Need to use a RangeTokenMerger """
    # 1 3 should make 1, 2, 3
    # a c should match a* b* c
    # unsure about this - RangeIndex only necessary for 'encloses' queries - John
    # also appropriate for 'within', so implememnted - John

    def search(self, session, clause, db):
        # check if we can just use SimpleIndex.search
        if (clause.relation.value not in ['encloses', 'within']):
            return SimpleIndex.search(self, session, clause, db)
        else:
            p = self.permissionHandlers.get('info:srw/operation/2/search', None)
            if p:
                if not session.user:
                    raise PermissionException("Authenticated user required to search index %s" % self.id)
                okay = p.hasPermission(session, session.user)
                if not okay:
                    raise PermissionException("Permission required to search index %s" % self.id)
    
            # Final destination. Process Term.
            res = {}    
            # try to get process for relation/modifier, failing that relation, fall back to that used for data
            for src in self.sources.get(clause.relation.toCQL(), self.sources.get(clause.relation.value, self.sources[u'data'])):
                res.update(src[1].process(session, [[clause.term.value]]))
    
            store = self.get_path(session, 'indexStore')
            matches = []
            rel = clause.relation

            if (len(res) != 1):
                raise QueryException("%s %s" % (clause.relation.toCQL(), clause.term.value), 24)

            keys = res.keys()[0].split('\t', 1)
            startK = keys[0]
            endK = keys[1]
            if clause.relation.value == 'encloses':
                # RangeExtractor should already return the range in ascending order
                termList = store.fetch_termList(session, self, startK, relation='<')
                termList = filter(lambda t: endK < t[0].split('\t', 1)[1], termList)
                matches.extend([self.construct_resultSet(session, t[1]) for t in termList])
            elif clause.relation.value == 'within':
                termList = store.fetch_termList(session, self, startK, end=endK)
                termList = filter(lambda t: endK > t[0].split('\t', 1)[1], termList)
                matches.extend([self.construct_resultSet(session, t[1]) for t in termList])
            else:
                # this just SHOULD NOT have happened!...
                raise QueryException('%s "%s"' % (clause.relation.toCQL(), clause.term.value), 24)
    
            base = self.resultSetClass(session, [], recordStore=self.recordStore)
            base.recordStoreSizes = self.recordStoreSizes
            base.index = self
            if not matches:
                return base
            else:
                rs = base.combine(session, matches, clause, db)
                return rs


from utils import SimpleBitfield
from resultSet import BitmapResultSet

class BitmapIndex(SimpleIndex):
    # store as hex -- fast to generate, 1 byte per 4 bits.
    # eval to go from hex to long for bit manipulation

    _possiblePaths = {'recordStore' : {"docs" : "The recordStore in which the records are kept (as this info not maintained in the index)"}}

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
        pack = struct.pack('lll', termId, nRecs, nOccs)
        val = pack + str(bf)
        return val

    def calc_sectionOffsets(self, session, start, nRecs, dataLen):
        # order is (of course) backwards
        # so we need length of data etc etc.
        start = (dataLen - (start / 4) +1)  - (nRecs/4)
        packing = dataLen - (start + (nRecs/4)+1)
        return [(start, (nRecs/4)+1, '0x', '0'*packing)]

        
    def deserialize_term(self, session, data, nRecs=-1, prox=0):
        lsize = 3 * self.longStructSize
        longs = data[:lsize]
        terms = list(struct.unpack('lll', longs))
        if len(data) > lsize:
            bf = SimpleBitfield(data[lsize:])
            terms.append(bf)
        return terms

    def merge_term(self, session, currentData, newData, op="replace", nRecs=0, nOccs=0):
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
        return self.indexStore.construct_resultSetItem(session, term[0], term[1], term[2])

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

    _possibleSettings = {'recordStore' : {"docs" : "The recordStore in which the records are kept (as this info not maintained in the index)"}}

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
        elif clause.relation.value in ['<', '<='] and clause.term.value.isdigit():
            t = long(clause.term.value)
            if clause.relation.value == '<':
                terms = range(t)
            else:
                terms = range(t+1)
                
            items = []
            for t in terms:
                if recordStore.fetch_metadata(session, t, 'wordCount') > -1:
                    item = SimpleResultSetItem(session)
                    item.id = t
                    item.database = db.id
                    item.recordStore = recordStore.id
                    items.append(item)
        else:
            raise QueryException('%s "%s"' % (clause.relation.toCQL(), clause.term.value), 24)
        
        base.fromList(items)
        base.index = self
        return base


# rec.checksumValue
class ReverseMetadataIndex(Index):

    _possiblePaths = {'recordStore' : {"docs" : "The recordStore in which the records are kept (as this info not maintained in the index)"}}
    _possibleSettings = {'metadataType' : {"docs" : "The type of metadata to provide an 'index' for. Defaults to digestReverse."}}

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
            # split on whitespace
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

    
    def _handleLxmlConfigNode(self, session, node):
        # Source
        if (node.tag == "xpath"):
            ref = node.attrib.get('ref', '')
            if ref:
                xp = self.get_object(session, ref)
            else:
                xp = SimpleXPathProcessor(session, node, self)
                xp.sources = [[xp._handleLxmlXPathNode(session, node)]]         
            self.xpath = xp

    def _handleConfigNode(self, session, node):
        # Source
        if (node.tag == "xpath"):
            ref = node.attrib('ref', '')
            if ref:
                xp = self.get_object(session, ref)
            else:
                xp = SimpleXPathProcessor(session, node, self)
                xp.sources = [[xp._handleLxmlXPathNode(session, node)]]
            self.xpath = xp

    def __init__(self, session, config, parent):
        self.xpath = None
        SimpleIndex.__init__(self, session, config, parent)
        dbStr = self.get_path(session, 'database', '')
        if not dbStr:
            raise ConfigFileException("No remote database given in %s" % self.id)
        db = session.server.get_object(session, dbStr)
        if not db:
            raise ConfigFileException("Unknown remote database given in %s" % self.id)            
        self.database = db

        idxStr = self.get_path(session, 'remoteIndex', "")
        if not idxStr:
            raise ConfigFileException("No remote index given in %s" % self.id)            
        idx = db.get_object(session, idxStr)
        if not idx:
            raise ConfigFileException("Unknown index %s in remote database %s for %s" % (idxStr, db.id, self.id))
        self.remoteIndex = idx

        idxStr = self.get_path(session, 'remoteKeyIndex', "")
        if idxStr:
            idx = db.get_object(session, idxStr)
            if not idx:
                raise ConfigFileException("Unknown index %s in remote database %s for %s" % (idxStr, db.id, self.id))
            self.remoteKeyIndex = idx
        else:
            self.remoteKeyIndex = None

        idx = self.get_path(session, 'localIndex', None)
        if not idx:
            raise ConfigFileException("No local index given in %s" % self.id)            
        self.localIndex = idx


    def search(self, session, clause, db):
        # first do search on remote index
        currDb = session.database
        session.database = self.database.id
        rs = self.remoteIndex.search(session, clause, self.database)
        # fetch all matched records
        values = {}
        for rsi in rs:
            rec = rsi.fetch_record(session)
            # process xpath
            try:
                value = self.xpath.process_record(session, rec)[0][0]
            except:
                # no data where we expect it
                continue
            if value:
                values[value] = 1

        # construct search from keys and return local search
        localq = cql.parse('c3.%s any "%s"' % (self.localIndex.id, ' '.join(values.keys())))
        session.database = currDb
        return self.localIndex.search(session, localq, db)

    def scan(self, session, clause, nTerms, direction=">="):
        # scan remote index
        # Note Well:  If term in remote doesn't appear, it's still included
        # with trecs and toccs of 0.  termid is always -1 as it's meaningless
        # in the local context -- could be multiple or 0            
        currDb = session.database
        session.database = self.database.id
        scans = self.remoteIndex.scan(session, clause, nTerms, direction, summary=0)
        #print scans
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
                # construct result set is more portable but slower
                rs = self.remoteIndex.construct_resultSet(session, termInfo)
                for rsi in rs:
                    rec = rsi.fetch_record(session)
                    # process xpath
                    try:
                        value = self.xpath.process_record(session, rec)[0][0]
                    except:
                        # no data where we expect it
                        continue
                    info  = self.localIndex.fetch_term(session, value, summary=1, prox=0)
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
                scans = self.remoteIndex.scan(session, clause, 10, direction, summary=0)
            else:
                break
        if endMarker != '' and len(newscans):
            newscans[-1].append(endMarker)
        return newscans[:nTerms]

    def fetch_sortValue(self, session, rec):
        if not self.remoteKeyIndex:
            return ''
        key = self.localIndex.fetch_sortValue(session, rec)
        if not key:
            return ''
        currDb = session.database
        session.database = self.database.id
        q = cql.parse('c3.%s exact "%s"' % (self.remoteKeyIndex.id, key))
        rs = self.remoteKeyIndex.search(session, q, self.database)
        if rs:
            sv = self.remoteIndex.fetch_sortValue(session, rs[0])
        else:
            sv =  ''
        session.database = currDb
        return sv

    # no need to do anything during indexing
    def begin_indexing(self, session):
        pass
    def commit_indexing(self, session):
        pass
    def index_record(self, session, rec):
        return record
    def delete_record(self, session, rec):
        pass



# XXX This should be deprecated by now right?
class ClusterExtractionIndex(SimpleIndex):

    def _handleConfigNode(self, session, node):
        if (node.localName == "cluster"):
            maps = []
            for child in node.childNodes:
                if (child.nodeType == elementType and child.localName == "map"):
                    t = child.getAttributeNS(None, 'type')
                    map = []
                    for xpchild in child.childNodes:
                        if (xpchild.nodeType == elementType and xpchild.localName == "xpath"):
                            map.append(flattenTexts(xpchild).strip())
                        elif (xpchild.nodeType == elementType and xpchild.localName == "process"):
                            # turn xpath chain to workflow
                            ref = xpchild.getAttributeNS(None, 'ref')
                            if ref:
                                process = self.get_object(session, ref)
                            else:
                                try:
                                    xpchild.localName = 'workflow'
                                except:
                                    # 4suite dom sets read only
                                    newTop = xpchild.ownerDocument.createElementNS(None, 'workflow')
                                    for kid in xpchild.childNodes:
                                        newTop.appendChild(kid)
                                    xpchild = newTop
                                process = CachingWorkflow(session, xpchild, self)
                                process._handleConfigNode(session, xpchild)
                            map.append(process)
                    #vxp = verifyXPaths([map[0]])
                    vxp = [map[0]]
                    if (len(map) < 3):
                        # default Extractor
                        map.append([['extractor', 'SimpleExtractor']])
                    if (t == u'key'):
                        self.keyMap = [vxp[0], map[1], map[2]]
                    else:
                        maps.append([vxp[0], map[1], map[2]])
            self.maps = maps

    def __init__(self, session, config, parent):
        self.keyMap = []
        self.maps = []
        Index.__init__(self, session, config, parent)

        for m in range(len(self.maps)):
            if isinstance(self.maps[m][2], list):
                for t in range(len(self.maps[m][2])):
                    o = self.get_object(session, self.maps[m][2][t][1])
                    if (o != None):
                        self.maps[m][2][t][1] = o
                    else:
                        raise(ConfigFileException("Unknown object %s" % (self.maps[m][2][t][1])))
        if isinstance(self.keyMap[2], list):
            for t in range(len(self.keyMap[2])):
                o = self.get_object(session, self.keyMap[2][t][1])
                if (o != None):
                    self.keyMap[2][t][1] = o
                else:
                    raise(ConfigFileException("Unknown object %s" % (self.keyMap[2][t][1])))
            

    def begin_indexing(self, session):
        path = self.get_path(session, "tempPath")
        if (not os.path.isabs(path)):
            dfp = self.get_path(session, "defaultPath")
            path = os.path.join(dfp, path)       
        self.fileHandle = codecs.open(path, "w", 'utf-8')

    def commit_indexing(self, session):
        self.fileHandle.close()
             
    def clear(self, session):
        pass

    def index_record(self, session, rec):
        # Extract cluster information, append to temp file
        # Step through .maps keys
        p = self.permissionHandlers.get('info:srw/operation/2/cluster', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to cluster using %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to cluster using %s" % self.id)

        raw = rec.process_xpath(session, self.keyMap[0])
        keyData = self.keyMap[2].process(session, [raw])
        fieldData = []
        for map in self.maps:
            raw = rec.process_xpath(session, map[0])
            fd = map[2].process(session, [raw])
            for f in fd.keys():
                fieldData.append(u"%s\x00%s\x00" % (map[1], f))
        d = u"".join(fieldData)
        for k in keyData.keys():
            try:
                self.fileHandle.write(u"%s\x00%s\n" % (k, d))
                self.fileHandle.flush()
            except:
                self.log_critical(session, "%s failed to write: %r" % (self.id, k))
                raise

    def delete_record(self, session, rec):
        pass
