import sys
import types
import math
import operator
import time
import cStringIO as StringIO
try:
    import cPickle as pickle
except ImportError:
    import pickle

from itertools import combinations
from xml.sax.saxutils import escape, unescape
from lxml import etree

from cheshire3.baseObjects import ResultSet, ResultSetItem, Index, Workflow
from cheshire3.utils import SimpleBitfield
from cheshire3 import cqlParser


def ucescape(data):
    return unicode(escape(data), 'latin-1')


srlz_typehash = {int: 'int',
                 long: 'long',
                 str: 'str',
                 unicode: 'unicode',
                 bool: 'bool',
                 type(None): 'None',
                 float: 'float'
                 }

dsrlz_typehash = {}
for k, v in srlz_typehash.iteritems():
    dsrlz_typehash[v] = k


class RankedResultSet(ResultSet):

    def _sumWeights(self, items, n):
        """Sum the values."""
        item = items[0]
        item.weight = sum([x.weight for x in items])
        return item
        #item.weight = sum([x.weight for x in items if (x.weight != 0.5)])

    def _meanWeights(self, items, n):
        """Mean average the values."""
        item = items[0]
        item.weight = sum([x.weight for x in items])
        item.weight = item.weight / n
        return item
        #trueWeightedItems = [x.weight for x in items if (x.weight != 0.5)]
        #item.weight = sum(trueWeightedItems)
        #item.weight = item.weight / len(trueWeightedItems)

    def _normWeights(self, items, n):
        """Normalize the values and average them."""
        for i in items:
            i.weight = (i.weight *
                        (i.resultSet.minWeight / i.resultSet.maxWeight)
                        )
        return self._meanWeights(items, n)

    def  _cmbzWeights(self, a, b):
        """Normalise and rescale values."""
        a.weight = a.weight * (self.minWeight / self.maxWeight)
        if b:
            b.weight = b.weight * (self.minWeight / self.maxWeight)
            a.weight = (a.weight + b.weight) * 2.0
        else:
            a.weight = a.weight / 2.0

    def _nprvWeights(self, a, b):
        """Normalise values and privilege high ranked documents."""
        a.weight = a.weight * (self.minWeight / self.maxWeight)
        if b:
            b.weight = b.weight * (self.minWeight / self.maxWeight)
            a.weight = (a.weight + b.weight) * 2.0
        else:
            # Leave high ranking ones high
            rlen = len(a.resultSet._list)
            # FIXME: item undefined
            if (
                    (rlen > 150 and item.resultSetPosition > 100) or
                    (rlen < 150 and item.resultSetPosition > rlen / 2)):
                a.weight = a.weight / 2.0

    def _pivotWeights(self, a, b):
        """Pivot weight of components if the document also occurs in the set.

        Determine which item is component set, and which item is from document
        set. If the component's parent document's id is the same as the one in
        the full document list, then adjust.

        Normalize min/max as above
        Pivot default is 0.7, but allow override
        (Pivot * documentScore) + ((1-pivot) * componentScore)

        If not in the list then just ((1-pivot) * componentScore)
        """
        raise NotImplementedError


class SimpleResultSet(RankedResultSet):
    _list = []

    id = ""
    termid = -1
    totalOccs = 0
    totalRecs = 0
    expires = 0
    index = None
    queryTerm = ""
    queryFreq = 0
    queryPositions = []
    queryTime = 0
    query = None
    relevancy = 0
    maxWeight = 0
    minWeight = 0
    termWeight = 0.0
    recordStore = ""
    rsiConstructor = None
    attributesToSerialize = []
    recordStoreSizes = 0
    termIdHash = {}
    fromStore = 0

    def __init__(self, session, data=None, id="", recordStore=""):
        self.rsiConstructor = SimpleResultSetItem
        self.attributesToSerialize = [('id', ''),
                                      ('termid', -1),
                                      ('totalOccs', 0),
                                      ('totalRecs', 0),
                                      ('expires', 0),
                                      ('queryTerm', ''),
                                      ('queryFreq', 0),
                                      ('queryPositions', []),
                                      ('relevancy', 0),
                                      ('maxWeight', 0),
                                      ('minWeight', 0),
                                      ('termWeight', 0.0),
                                      ('recordStore', ''),
                                      ('recordStoreSizes', 0),
                                      ('index', None),
                                      ('queryTime', 0.0),
                                      ('query', '')
                                      ]
        if data is not None:
            self._list = list(data)
        else:
            self._list = []
        self.id = id
        self.recordStore = recordStore

        self.relevanceContextSets = {
            "info:srw/cql-context-set/2/relevance-1.0": 1.0,
            "info:srw/cql-context-set/2/relevance-1.1": 1.1,
            "info:srw/cql-context-set/2/relevance-1.2": 1.2
        }

        self.termid = -1
        self.totalOccs = 0
        self.totalRecs = 0
        self.expires = 0
        self.index = None
        self.queryTerm = ""
        self.queryFreq = 0
        self.queryPositions = []
        self.queryTime = 0.0
        self.query = None
        self.relevancy = 0
        self.maxWeight = 0
        self.minWeight = 0
        self.termWeight = 0.0
        self.recordStoreSizes = 0
        self.termIdHash = {}
        self.fromStore = 0

    def __getitem__(self, k):
        return self._list[k]

    def __len__(self):
        return len(self._list)

    def fromList(self, data):
        self._list = data

    def serialise(self, session, pickleOk=1):
        """Serialize and this ResultSet as XML, return a string (utf-8).

        DEPRECATED by ``resultSet.serialize(session, pickleOk)``
        """
        return self.serialize(session, pickleOk)

    def serialize(self, session, pickleOk=1):
        """Serialize and this ResultSet as XML, return a string (utf-8)."""
        # This is pretty fast, and generates better XML than previous
        xml = [u'<resultSet>']

        rsetattrs = self.attributesToSerialize
        for (a, deft) in rsetattrs:
            val = getattr(self, a)
            if val != deft:
                if type(val) in [dict, list, tuple]:
                    # Use later version of pickle protocol to deal with
                    # new-style classes, unicode etc.
                    valstr = pickle.dumps(val)  # , pickle.HIGHEST_PROTOCOL)
                    xml.append(u'<d n="%s" t="pickle">%s</d>' %
                               (a, ucescape(valstr)))
                elif isinstance(val, Index):
                    xml.append(u'<d n="%s" t="object">%s</d>' %
                               (a, escape(val.id)))
                elif a == 'query' and val:
                    xml.append(u'<d n="%s" t="cql">%s</d>' %
                               (a, escape(val.toCQL())))
                else:
                    xml.append(u'<d n="%s" t="%s">' %
                               (a, srlz_typehash.get(type(val), '')))
                    if type(val) in [int, long, float, bool, type(None)]:
                        xml.append(escape(unicode(val)))
                    else:
                        xml.append(escape(val))
                    xml.append(u'</d>')

        for item in self:
            xml.append(item.serialize(session, pickleOk))
        xml.append(u'</resultSet>')
        all = u''.join(xml)
        return all.encode('utf-8')

    def deserialise(self, session, data):
        """Deserialize XML in ``data`` to return the populated ResultSet.

        DEPRECATED by ``resultSet.deserialize(session, data)``
        """
        return self.deserialize(session, data)

    def deserialize(self, session, data):
        """Deserialize XML in ``data`` to return the populated ResultSet."""
        # This is blindingly fast compared to old version!

        def value_of(elem):
            # typehash = {'int': int,
            #             'long': long,
            #             'bool': bool,
            #             'float': float
            #             }
            t = elem.attrib['t']
            if not elem.text:
                return elem.text
            txt = unescape(elem.text)
            if t == 'pickle':
                val = pickle.loads(txt.encode('utf-8'))
            elif t == 'None':
                val = None
            elif t == 'object':
                # dereference id
                db = session.server.get_object(session, session.database)
                val = db.get_object(session, txt)
            elif t == 'cql':
                try:
                    val = cqlParser.parse(txt)
                except:
                    raise
            elif t in dsrlz_typehash:
                if type(txt) == unicode and t != 'unicode':
                    val = dsrlz_typehash[t](txt.encode('utf-8'))
                else:
                    val = dsrlz_typehash[t](txt)
            else:
                val = txt
            return val

        root = etree.fromstring(data)
        rsiConstructor = self.rsiConstructor

        rsi = None
        pi = []
        hit = []
        for e in root.iter(tag=etree.Element):
            e2 = e
            if e.tag == 'd':
                name = e.attrib['n']
                val = value_of(e)
                if rsi:
                    setattr(rsi, name, val)
                else:
                    setattr(self, name, val)
            elif e2.tag == 'item':
                if rsi:
                    if hit:
                        pi.append(hit)
                    rsi.proxInfo = pi
                    self.append(rsi)
                rsi = rsiConstructor(session)
                pi = []
                hit = []
            elif e2.tag == 'hit':
                if hit:
                    pi.append(hit)
                hit = []
            elif e2.tag == 'w':
                hit.append([int(x) for x in e2.attrib.values()])
        if rsi:
            if hit:
                pi.append(hit)
            rsi.proxInfo = pi
            self.append(rsi)
        return self

    def append(self, item):
        item.resultSet = self
        item.resultSetPosition = len(self._list)
        self._list.append(item)

    def extend(self, itemList):
        for i in itemList:
            self.append(i)

    def _lrAssign(self, session, others, clause, cql, db):
        """Assign Logistic Regression weights and combine items in others.

        Assign Logistic Regression weights and merge items in resultSets in
        others into self in a single method.
        """
        if (db):
            totalDocs = db.totalItems
            if totalDocs == 0:
                raise ValueError("0 documents in database")
        else:
            # Uhoh
            raise NameError("Database not supplied to relevancy algorithm")

        # William S Cooper proposes:
        constants = [-3.7, 1.269, -0.31, 0.679, -0.0674, 0.223, 2.01]

        # Ray R Larson proposes:
        constants = [-3.7, 1.269, -0.31, 0.679, -0.021, 0.223, 4.01]

        # Index Configuration proposes:
        pm = db.get_path(session, 'protocolMap')
        if not pm:
            db._cacheProtocolMaps(session)
            pm = db.protocolMaps.get('http://www.loc.gov/zing/srw/')
            db.paths['protocolMap'] = pm

        idx = pm.resolveIndex(session, clause)

        if (idx):
            for x in range(7):
                temp = idx.get_setting(session, 'lr_constant%d' % x)
                if (temp):
                    constants[x] = float(temp)

        # Query proposes:
        for m in cql.modifiers:
            # Already been pinged for resolve()
            if (m.type.prefixURI in self.relevanceContextSets):
                if m.type.value.startswith("const"):
                    try:
                        constants[int(m.type.value[5])] = float(m.value)
                    except ValueError:
                        # Invalid literal for float()
                        pass
                    except IndexError:
                        # list index out of range
                        pass

        sumLogQueryFreq = 0.0
        sumQueryFreq = 0
        sumIDF = 0.0

        # Sort rss by length

        # Each rs represents one unique word in query
        for rs in others:
            sumLogQueryFreq += math.log(rs.queryFreq)
            sumQueryFreq += rs.queryFreq
            n = len(rs)
            if n:
                rs.idf = math.log(totalDocs / float(n))
        x2 = math.sqrt(sumQueryFreq)

        # ResultSets will be sorted by item already
        # Step through all concurrently

        tmplist = []
        recStores = {}
        nors = len(others)
        lens = [len(o) for o in others]
        oidxs = range(1, nors)
        positions = [0] * nors
        all = cql.value in ['all', 'and', '=', 'prox', 'adj']
        maxWeight = -1
        minWeight = 9999999999

        cont = 1
        while cont:
            items = [others[0][positions[0]]]
            rspos = [0]
            for o in oidxs:
                try:
                    nitem = others[o][positions[o]]
                except IndexError:
                    # There are no more items in this rs
                    continue

                if nitem == items[0]:
                    items.append(nitem)
                    rspos.append(o)
                elif nitem < items[0]:
                    if all:
                        # skip until equal or greater
                        positions[o] += 1
                        while (positions[o] < lens[o] and
                               others[o][positions[o]] < items[0]):
                            positions[o] += 1

                    else:
                        items = [nitem]
                        rspos = [o]
            for r in rspos:
                positions[r] += 1

            while others and positions[0] == len(others[0]) - 1:
                others.pop(0)
                positions.pop(0)
            if not others:
                cont = 0
            if all and len(items) < nors:
                continue

            # sumLogDAF = sum(map(math.log, [x.occurences for x in items]))
            sumLogDAF = sum([math.log(x)
                             for x
                             in [y.occurences
                                 for y
                                 in items
                                 ]
                             ])
            sumIdx = sum([x.resultSet.idf for x in items])

            x1 = sumLogQueryFreq / float(n)
            x3 = sumLogDAF / float(n)
            x5 = sumIDF / float(n)
            x6 = math.log(float(n))
            # FIXME: item undefined
            try:
                recStore = recStores[item.recordStore]
            except KeyError:
                db = session.server.get_object(session, session.database)
                recStore = db.get_object(session, item.recordStore)
                recStores[item.recordStore] = recStore
            doclen = recStore.fetch_recordMetadata(session,
                                                   item.id,
                                                   'wordCount')
            x4 = math.sqrt(doclen)
            logodds = (constants[0] +
                       (constants[1] * x1) +
                       (constants[2] * x2) +
                       (constants[3] * x3) +
                       (constants[4] * x4) +
                       (constants[5] * x5) +
                       (constants[6] * x6)
                       )
            item.weight = 0.75 * (math.exp(logodds) / (1 + math.exp(logodds)))
            tmplist.append(item)
            if item.weight > maxWeight:
                maxWeight = item.weight
            elif item.weight < minWeight:
                minWeight = item.weight

        self._list = tmplist
        self.minWeight = minWeight
        self.maxWeight = maxWeight
        self.relevancy = 1
        return 1

    def _coriAssign(self, session, others, clause, cql, db):
        """Assign CORI weighting to each item in each resultSet in others."""
        if (db):
            totalDocs = float(db.totalItems)
            avgSize = float(db.meanWordCount)
            if not totalDocs or not avgSize:
                raise ValueError("0 documents in database")
        else:
                raise NameError("Database not supplied to relevancy algorithm")

        rsizes = clause.relation['recstoresizes']
        if not rsizes:
            rsizes = self.recordStoreSizes

        recStoreSizes = {}

        recStores = {}
        for rs in others:
            matches = float(len(rs))
            if not matches:
                rs.minWeight = 1.0
                rs.maxWeight = -1.0
                continue
            I = (math.log((totalDocs + 0.5) / matches) /
                 math.log(totalDocs + 1.0)
                 )
            rs.minWeight = 1000000.0
            rs.maxWeight = -1.0
            for item in rs:
                df = float(item.occurences)
                recStore = recStores.get(item.recordStore, None)
                if not recStore:
                    recStore = db.get_object(session, item.recordStore)
                    recStores[item.recordStore] = recStore
                size = recStore.fetch_recordMetadata(session,
                                                     item.id,
                                                     'wordCount')
                if rsizes:
                    avgSize = recStore.meanWordCount
                T = df / (df + 50.0 + ((150.0 * size) / avgSize))
                item.weight = 0.4 + (0.6 * T * I)
                if item.weight > rs.maxWeight:
                    rs.maxWeight = item.weight
                if item.weight < rs.minWeight:
                    rs.minWeight = item.weight
        return 0

    def _tfidfAssign(self, session, others, clause, cql, db):
        """Assign TF-IDF weighting to each item in each resultSet in others."""
        # each rs in others represents records matching a single term
        # w(i,j) = tf(i,j) * (log ( N / df(i)))
        if (db):
            totalDocs = float(db.totalItems)
            if not totalDocs:
                raise ValueError("0 documents in database")
        else:
            raise NameError("Database not supplied to relevancy algorithm")

        for rs in others:
            matches = float(len(rs))
            rs.minWeight = 10000000.0
            rs.maxWeight = -1.0
            for item in rs:
                weight = item.occurences * math.log(totalDocs / matches)
                item.weight = weight
                if rs.maxWeight < weight:
                    rs.maxWeight = weight
                if rs.minWeight > weight:
                    rs.minWeight = weight
        return 0

    def _okapiAssign(self, session, others, clause, cql, db):
        """Assign Okapi BM-25 weighting to items in resultSets in others."""
        if (db):
            totalDocs = float(db.totalItems)
            avgSize = float(db.meanWordCount)
            if not totalDocs or not avgSize:
                raise ValueError("0 documents in database")
        else:
            raise NameError("Database not supplied to relevancy algorithm")

        # Tuning parameters [b, k1, k3]
        # default
        constants = [0.75, 1.5, 1.5]

        # Index Configuration proposes:
        pm = db.get_path(session, 'protocolMap')
        if not pm:
            db._cacheProtocolMaps(session)
            pm = db.protocolMaps.get('http://www.loc.gov/zing/srw/')
            db.paths['protocolMap'] = pm

        idx = pm.resolveIndex(session, clause)

        if (idx):
            for i, const in enumerate(['b', 'k1', 'k3']):
                temp = idx.get_setting(session, 'okapi_constant_' + const)
                if (temp):
                    constants[i] = float(temp)

        # Query proposes:
        for m in cql.modifiers:
            # Already been pinged for resolve()
            if (m.type.prefixURI in self.relevanceContextSets):
                if m.type.value.startswith("const"):
                    try:
                        constants[int(m.type.value[5])] = float(m.value)
                    except ValueError:
                        # Invalid literal for float()
                        pass
                    except IndexError:
                        # list index out of range
                        pass

        rsizes = clause.relation['recstoresizes']
        if not rsizes:
            rsizes = self.recordStoreSizes

        recStoreSizes = {}
        recStores = {}
        b, k1, k3 = constants
        for rs in others:
            matches = float(len(rs))
            if not matches:
                rs.minWeight = 1.0
                rs.maxWeight = -1.0
                continue

            idf = math.log(totalDocs / matches)
            # idf = max(0.0,
            #           math.log(totalDocs - matches + 0.5 / matches + 0.5)
            #           )  # give it a floor of 0

            qtw = ((k3 + 1) * rs.queryFreq) / (k3 + rs.queryFreq)

            rs.minWeight = 1000000.0
            rs.maxWeight = -1.0
            for item in rs:
                docFreq = float(item.occurences)
                recStore = recStores.get(item.recordStore, None)
                if recStore is None:
                    recStore = db.get_object(session, item.recordStore)
                    recStores[item.recordStore] = recStore
                size = recStore.fetch_recordMetadata(session,
                                                     item.id,
                                                     'wordCount')
                if rsizes:
                    avgSize = recStore.meanWordCount

                T = (((k1 + 1) * docFreq) /
                     ((k1 * ((1 - b) + b * (size / avgSize))) + docFreq)
                     )

                item.weight = idf * T * qtw

                if item.weight > rs.maxWeight:
                    rs.maxWeight = item.weight
                if item.weight < rs.minWeight:
                    rs.minWeight = item.weight

        return 0

    def combine(self, session, others, clause, db=None):
        """Combine resultSets in others into self and return."""
        try:
            cql = clause.boolean
        except AttributeError:
            cql = clause.relation

        self.query = clause

        all = cql.value in ['all', 'and', '=', 'prox', 'adj', 'window']

        # XXX: To Configuration. How?
        relSets = self.relevanceContextSets
        cqlSets = ["info:srw/cql-context-set/1/cql-v1.1",
                   "info:srw/cql-context-set/1/cql-v1.2"]

        relevancy = 0
        pi = 0
        algorithm = "cori"
        combine = "mean"
        modType = ""
        for m in cql.modifiers:
            m.type.parent = clause
            m.type.resolvePrefix()
            if (m.type.prefixURI in relSets):
                # Relevancy info
                relevancy = 1
                if m.type.value == "algorithm":
                    algorithm = m.value.lower()
                elif m.type.value == "combine":
                    combine = m.value.lower()
            elif (m.type.prefixURI in cqlSets and m.type.value == "relevant"):
                # Generic 'relevancy please' request
                relevancy = 1
            elif m.type.value == 'proxinfo':
                pi = 1

        # Check if any others are relevance ranked already and preserve
        if (not relevancy):
            for x in others:
                if (x.relevancy):
                    relevancy = 1
                    break

        # Sort result sets by length
        if not cql.value in ['not', 'prox']:
            others.sort(key=lambda x: len(x), reverse=not all)

        if (relevancy):
            self.relevancy = 1
            if (isinstance(cql, cqlParser.Relation)):
                fname = "_%sAssign" % algorithm
                if (hasattr(self, fname)):
                    fn = getattr(self, fname)
                else:
                    # We /could/ self inspect to sat what relevance algorithms
                    # are supported...
                    raise NotImplementedError("Relevance algorithm '{0}' not "
                                              "implemented".format(algorithm))
                finish = fn(session, others, clause, cql, db)
                if finish:
                    return self

        if len(others) == 1 and len(others[0].queryPositions) < 2:
            if relevancy:
                # Just adding relevance to items?
                others[0].relevancy = 1
            if pi:
                o = others[0]
                for i in o:
                    for pii in i.proxInfo:
                        [x.append(o.termid) for x in pii]
            return others[0]

        if relevancy:
            maxWeight = -1
            minWeight = 9999999999
            fname = "_%sWeights" % combine
            if (hasattr(self, fname)):
                fn = getattr(self, fname)
            else:
                raise NotImplementedError

        tmplist = []
        oidxs = range(1, len(others))
        lens = [len(x) for x in others]
        nors = len(others)
        # Fast escapes
        if all and 0 in lens:
            return self
        elif sum(lens) == 0:
            return self
        elif nors == 2 and cql.value in ['or', 'any'] and 0 in lens:
            # A or (empty) == A
            return others[int(lens[0] == 0)]

        positions = [0] * nors
        cmpHash = {'<': [-1],
                   '<=': [-1, 0],
                   '=': [0],
                   '>=': [0, 1],
                   '>': [1]
                   }
        distance = 1
        unit = "word"
        comparison = "="
        ordered = 0
        if (cql.value in ['prox', 'window'] and cql.modifiers):
            if (cql['unit']):
                unit = cql['unit'].value
            if (cql['distance']):
                distance = int(cql['distance'].value)
                comparison = cql['distance'].comparison
            if cql['ordered']:
                ordered = 1
        else:
            # for adj/=
            ordered = 1

        for o in others:
            self.termIdHash[o.termid] = o.queryTerm
            if o.fromStore:
                # Re-sort before combining as likely out of order
                if o[0].numericId is not None:
                    o.order(session, 'numericId')
                else:
                    o.order(session, 'id')

        chitem = cmpHash[comparison]
        if unit == "word":
            proxtype = 1
        elif unit == "element" and distance == 0 and comparison == "=":
            proxtype = 2
        elif unit == "character":
            # Can do this with offsets :)
            proxtype = 3
        else:
            raise NotImplementedError()
        hasGetItemList = [hasattr(o, 'get_item') for o in others]
        cont = 1

        while cont:
            items = [others[0][positions[0]]]
            rspos = [0]
            for o in oidxs:
                if o != -1:
                    if hasGetItemList[o]:
                        nitem = others[o].get_item(items[0])
                        if not nitem:
                            continue
                    else:
                        try:
                            nitem = others[o][positions[o]]
                        except IndexError:
                            oidxs[o - 1] = -1
                            continue
                        if nitem < items[0]:
                            if all or cql.value == 'not':
                                # skip until equal or greater
                                while True:
                                    positions[o] += 1
                                    if (
                                        positions[o] >= lens[o] or
                                        others[o][positions[o]] >= items[0]
                                    ):
                                        break
                                if positions[o] != lens[o]:
                                    nitem = others[o][positions[o]]
                            else:
                                items = [nitem]
                                rspos = [o]
                                continue
                    if nitem == items[0]:
                        items.append(nitem)
                        rspos.append(o)
            for r in rspos:
                positions[r] += 1

            while others and positions[0] > len(others[0]) - 1:
                others.pop(0)
                positions.pop(0)
                lens.pop(0)
            if (
                not others or
                ((cql.value == 'not' or all) and len(others) != nors)
            ):
                cont = 0
            if (all and len(items) < nors):
                continue
            elif cql.value == 'not' and len(items) != 1:
                continue
            elif cql.value in ["prox", 'adj', '=', 'window']:
                # proxInfo is hash of (docid, recStore) to list of locations in
                # record
                # Sort items by query position. Repeat set at each posn
                if cql.value != "prox":
                    newItemHash = {}
                    rsiConstructor = self.rsiConstructor
                    for i in items:
                        i.queryTerm = i.resultSet.queryTerm
                        i.queryPositions = i.resultSet.queryPositions
                        newItemHash[i.queryPositions[0]] = i
                        if len(i.queryPositions) > 1:
                            for qpi in i.queryPositions[1:]:
                                # construct new rsi
                                newi = rsiConstructor(session,
                                                      id=i.id,
                                                      recStore=i.recordStore,
                                                      occs=i.occurences,
                                                      database=i.database,
                                                      weight=i.weight,
                                                      resultSet=i.resultSet
                                                      )
                                newi.queryPositions = [qpi]
                                newi.queryTerm = i.queryTerm
                                newi.proxInfo = i.proxInfo
                                newItemHash[qpi] = newi

                    ni = newItemHash.items()
                    ni.sort()
                    newitems = [x[1] for x in ni]
                    items = newitems[:]
                else:
                    # Create a copy of items
                    newitems = items[:]

                litem = items.pop(0)
                ltermid = litem.resultSet.termid
                nomatch = 0

                while len(items):
                    ritem = items.pop(0)
                    rtermid = ritem.resultSet.termid
                    matchlocs = []
                    for rpiFull in ritem.proxInfo:
                        rpi = list(rpiFull[-1])
                        (relem, rwpos) = rpi[:2]
                        for lpiFull in litem.proxInfo:
                            lpi = list(lpiFull[-1])
                            (lelem, lwpos) = lpi[:2]
                            if lelem == relem:
                                if proxtype == 2:
                                    d = lpiFull[:]
                                    for r in rpiFull:
                                        if d[-1] != r:
                                            r.append(rtermid)
                                            d.append(r)
                                    matchlocs.append(d)
                                else:
                                    if proxtype == 3:
                                        # character distance
                                        try:
                                            loff = lpi[2]
                                            roff = rpi[2]
                                        except IndexError:
                                            # no offset in index
                                            msg = ("Cannot do character "
                                                   "proximity without offset "
                                                   "information")
                                            raise ConfigFileException(msg)
                                        piDistance = roff - loff
                                    else:
                                        # word proximity
                                        piDistance = rwpos - lwpos
                                    if ordered and piDistance < 0:
                                        # B is before A
                                        pass
                                    else:
                                        piDistance = abs(piDistance)
                                        c = cmp(piDistance, distance)
                                        if (c in chitem):
                                            # copy as we're in two deep
                                            anyOkay = 0
                                            d = lpiFull[:]
                                            # Check we're not the same word
                                            for r in rpiFull:
                                                if (
                                                    cql.value == 'window' and
                                                    len(d) > 1
                                                ):
                                                    wokay = 1
                                                    # Check that ALL in
                                                    # distance
                                                    for wd in d:
                                                        if proxtype == 3:
                                                            wpiDistance = (
                                                                roff - wd[2]
                                                            )
                                                        else:
                                                            wpiDistance = (
                                                                rwpos - wd[1]
                                                            )
                                                        if (
                                                            ordered and
                                                            wpiDistance < 0
                                                        ):
                                                            wokay = 0
                                                            break
                                                        else:
                                                            wpiDistance = abs(
                                                                wpiDistance
                                                            )
                                                            c = cmp(
                                                                wpiDistance,
                                                                distance
                                                            )
                                                            if not c in chitem:
                                                                wokay = 0
                                                                break
                                                        anyOkay = 1
                                                    if wokay and d[-1] != r:
                                                        r.append(rtermid)
                                                        d.append(r)
                                                else:
                                                    anyOkay = 1
                                                    r.append(rtermid)
                                                    if d[-1] != r:
                                                        d.append(r)
                                            if anyOkay:
                                                matchlocs.append(d)

                    if matchlocs:
                        ritem.proxInfo = matchlocs
                        litem = ritem
                    else:
                        # no match, break to next set of items
                        nomatch = 1
                        break
                if nomatch:
                    continue

                for m in matchlocs:
                    m[0].append(ltermid)
                litem.proxInfo = matchlocs
                items = [litem]

            # Do stuff on items to reduce to single representative
            if relevancy:
                item = fn(items, nors)
                if item.weight > maxWeight:
                    maxWeight = item.weight
                if item.weight < minWeight:
                    minWeight = item.weight
            else:
                item = items[0]

            if pi and cql.value != "window":
                # copy proxInfo around
                if items[0].resultSet.termid != -1:
                    for pii in items[0].proxInfo:
                        for x in pii:
                            x.append(items[0].resultSet.termid)
                for o in items[1:]:
                    if o.resultSet.termid != -1:
                        for pii in o.proxInfo:
                            for x in pii:
                                x.append(o.resultSet.termid)
                    item.proxInfo.extend(o.proxInfo)
            item.resultSet = self
            tmplist.append(item)

        self._list = tmplist
        if relevancy:
            self.relevancy = 1
            self.minWeight = minWeight
            self.maxWeight = maxWeight
        return self

    def order(self, session, spec,
              ascending=None, missing=None, case=None, accents=None):
        """Re-order based on the given specification and arguments.

        :param spec: specification on which to order the ResultSet
        :type spec: Index, xpath, Workflow, attribute of ResultSetItem
        :param ascending: sort in ascending order
        :type ascending: True, False or None (best guess)
        :param missing: behaviour when sort value is missing
        :type missing: integer (-1: low, 0: omit, 1: high) or string (default)
        :param case: case sensitive? (assuming spec permits it)
        :type case: True or False
        :param accents: exclude accented characters
        :type accents: True or False
        :rtype: None

        Not handling yet:

        * locale=VALUE
        * unicodeCollate[=VALUE]

        Clause is a CQL clause with sort attributes on the relation
        """

        l = self._list
        if not l:
            # don't try to sort empty set
            return
        if (
            isinstance(spec, Index) and
            spec.get_setting(session, 'sortStore')
        ):
            # Check pre-processed db
            tmplist = [(spec.fetch_sortValue(session, x, ascending), x)
                       for x
                       in l
                       ]
        elif isinstance(spec, Index) and spec.get_setting(session, 'vectors'):
            # This assumes termid is ordered properly
            # if it isn't write a normalizer, see pyuca normalizer
            miss = lambda x: x[2][0][0] if x[2] else None
            tmplist = [(miss(spec.fetch_vector(session, x)), x)
                       for x
                       in l
                       ]
        elif isinstance(spec, Index):
            # Extract data as per indexing, MUCH slower
            recs = []
            storeHash = {}
            for r in l:
                store = r.recordStore
                o = storeHash.get(store, spec.get_object(session, store))
                storeHash[store] = o
                recs.append(o.fetch_record(session, r.id))
            tmplist = [(spec.extract_data(session, recs[x]), l[x])
                       for x
                       in range(len(l))
                       ]
        elif isinstance(spec, Workflow):
            # Process a workflow on records
            tmplist = []
            for r in l:
                rec = r.fetch_record(session)
                tmplist.append((spec.process(session, rec), r))
        elif (isinstance(spec, basestring) and hasattr(self[0], spec)):
            # Sort by attribute of item
            tmplist = [(getattr(x, spec), x) for x in l]
            if ascending is None:
                # Check if default sort order should be ascending
                # Allow for str vs unicode
                if str(spec) in ['id', 'numericId']:
                    ascending = True
                else:
                    ascending = False
        elif isinstance(spec, basestring):
            # XPath
            tmplist = []
            for r in l:
                rec = r.fetch_record(session)
                tmplist.append((rec.process_xpath(session, spec), r))
        else:
            # Don't know what?
            raise NotImplementedError

        if missing is not None:
            if missing == -1:
                # Sort low
                val = '\x00'
            elif missing == 0:
                # Omit
                tmplist = [x for x in tmplist if x[0]]
            elif missing == 1:
                # Sort high
                val = '\xff'
            else:
                val = missing
            fill = lambda x: x if x else val
            tmplist = [(fill(x[0]), x[1]) for x in tmplist]

        if not case and case is not None:
            tmplist = [(x[0].lower(), x[1]) for x in tmplist]

        if not accents and accents is not None:
            db = session.server.get_object(session, session.database)
            n = db.get_object(session, 'DiacriticNormalizer')
            unaccent = n.process_string
            tmplist = [(unaccent(session, x[0]), x[1]) for x in tmplist]

        if ascending is None:
            # If ascending not set, assume ascending unless over-ridden
            # due to spec later...
            ascending = True

        tmplist.sort(reverse=not(ascending))
        self._list = [x for (key, x) in tmplist]

    def reverse(self, session):
        self._list.reverse()

    def scale_weights(self):
        minw = self.minWeight
        if self.maxWeight != minw:
            r = 1 / (self.maxWeight - minw)
        else:
            r = 1
        # faster than equivalent list comprehension!
        for rsi in self._list:
            rsi.scaledWeight = (rsi.weight - minw) * r


class SimpleResultSetItem(ResultSetItem):

    id = 0
    numericId = None
    recordStore = ""
    database = ""
    occurences = 0
    weight = 0.5
    scaledWeight = 0.5
    diagnostic = None
    proxInfo = []
    attributesToSerialize = []

    def __init__(self, session, id=0, recStore="", occs=0, database="",
                 diagnostic=None, weight=0.5, resultSet=None, numeric=None):
        self.attributesToSerialize = [('id', 0),
                                      ('numericId', None),
                                      ('recordStore', ''),
                                      ('database', ''),
                                      ('occurences', 0),
                                      ('weight', 0.5),
                                      ('scaledWeight', 0.5)
                                      ]
        self.id = id
        self.recordStore = recStore
        self.occurences = occs
        self.weight = weight
        self.scaledWeight = 0.5
        self.database = database
        self.resultSet = resultSet
        self.proxInfo = []
        self.numericId = numeric

    def serialize(self, session, pickleOk=1):
        xml = [u'<item>']
        itemattrs = self.attributesToSerialize
        for (a, deft) in itemattrs:
            val = getattr(self, a)
            if val != deft:
                if type(val) in [dict, list, tuple]:
                    if pickleOk:
                        # Use latest version of pickle protocol to deal with
                        # new-style classes, unicode etc.
                        # valstr = pickle.dumps(val, pickle.HIGHEST_PROTOCOL)
                        valstr = pickle.dumps(val)
                        escaped_valstr = ucescape(valstr)
                        xml.append(u'<d n="{0}" t="pickle">{1}</d>'
                                   u''.format(a, escaped_valstr))
                else:
                    try:
                        valstr = unicode(val, 'utf-8')
                    except TypeError:
                        valstr = unicode(val)
                    escaped_valstr = escape(valstr)
                    xml.append(u'<d n="{0}" t="{1}">{2}</d>'
                               u''.format(a,
                                          srlz_typehash.get(type(val), ''),
                                          escaped_valstr)
                               )
        val = getattr(self, 'proxInfo')
        if val:
            # Serialize to XML
            xml.append(u'<proxInfo>')
            for hit in val:
                xml.append(u'<hit>')
                for w in hit:
                    if len(w) == 4:
                        xml.append(u'<w e="%s" w="%s" o="%s" t="%s"/>' %
                                   tuple(w))
                    elif len(w) == 3:
                        xml.append(u'<w e="%s" w="%s" o="%s"/>' %
                                   tuple(w))
                    else:
                        try:
                            xml.append(u'<w e="%s" w="%s"/>' %
                                       tuple(w))
                        except:
                            # Should really error!
                            xml.append(u'<w e="%s" w="%s" o="%s" t="%s"/>' %
                                       tuple(w[:4]))

                xml.append(u'</hit>')
            xml.append(u'</proxInfo>')
        xml.append(u'</item>')
        return u''.join(xml)

    def fetch_record(self, session):
        # Return record from store
        if (session.server):
            # db = session.server.get_object(session, self.database)
            db = session.server.get_object(session, session.database)
            recStore = db.get_object(session, self.recordStore)
            rec = recStore.fetch_record(session, self.id)
            rec.resultSetItem = self
            return rec

    def __eq__(self, other):
        try:
            return (self.id == other.id and
                    self.recordStore == other.recordStore)
        except:
            # Not comparing two RSIs
            return False

    def __str__(self):
        return "%s/%s" % (self.recordStore, self.id)

    def __repr__(self):
        return "Ptr:%s/%s" % (self.recordStore, self.id)

    def __cmp__(self, other):
        # Default sort by docid
        if self.numericId is not None:
            if other.numericId is not None:
                oid = other.numericId
            else:
                oid = other.id
            c = cmp(self.numericId, oid)
        else:
            c = cmp(self.id, other.id)
        if not c:
            return cmp(self.recordStore, other.recordStore)
        else:
            return c

    def __hash__(self):
        # Hash of recordstore + id
        return hash(str(self))


class BitmapResultSet(ResultSet):
    bitfield = None
    currItems = None
    recordStore = None
    fromStore = 0
    relevancy = 0
    termid = -1
    totalOccs = 0
    totalRecs = 0
    id = ""
    index = None
    queryTerm = ""
    queryFreq = 0
    queryPositions = []
    relevancy = 0
    maxWeight = 0
    minWeight = 0

    def __init__(self, session, data=0, recordStore=None):
        if isinstance(data, SimpleBitfield):
            self.bitfield = data
        else:
            self.bitfield = SimpleBitfield(data)
        self.currItems = None
        self.recordStore = recordStore
        self.relevancy = 0

    def __getitem__(self, k):
        if self.currItems is None:
            self.currItems = self.bitfield.trueItems()
        return SimpleResultSetItem(None,
                                   self.currItems[k],
                                   self.recordStore,
                                   1)

    def __len__(self):
        return self.bitfield.lenTrueItems()

    def serialise(self, session):
        return self.serialize(session)

    def serialize(self, session):
        return str(self.bitfield)

    def deserialise(self, data):
        return self.deserialize(data)

    def deserialize(self, data):
        self.bitfield = SimpleBitfield(data)

    def get_item(self, item):
        try:
            if self.bitfield[item.id]:
                return item
        except IndexError:
            pass
        return None

    def combine(self, session, others, clause, db=None):
        if (isinstance(clause, cqlParser.Triple)):
            cql = clause.boolean
        else:
            cql = clause.relation
        v = cql.value

        # Check if all are bitmaps
        if v in ['=', 'exact', 'prox']:
            if len(others) == 1:
                return others[0]
            else:
                raise NotImplementedError()

        allbits = 1
        for o in others:
            if not hasattr(o, 'bitfield'):
                allbits = 0
                break

        if allbits:
            if (v in ['all', 'and']):
                s = others[0].bitfield
                for o in others[1:]:
                    s.intersection(o.bitfield)
            elif (v in ['any', 'or', '>', '>=', '<', '<=']):
                s = others[0].bitfield
                for o in others[1:]:
                    s.union(o.bitfield)
            elif (v == 'not'):
                s = others[0].bitfield
                for o in others[1:]:
                    s.difference(o.bitfield)
            else:
                raise NotImplementedError()
            self.bitfield = s
        else:
            # XXX Merging Bitmap with non bitmap
            pass
        return self

    def order(self, spec):
        # Reorder a bitmap?!
        raise NotImplementedError()

    def retrieve(self, numReq, start, cache=0):
        end = min(start + numReq + 1, len(self))
        recs = []
        # XXX This should cache server, db and resultSet
        for r in range(start, end):
            recs.append(self[r].fetch_record(session))
        return recs
