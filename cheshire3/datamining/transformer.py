
from cheshire3.baseObjects import Transformer, Record
from cheshire3.document import StringDocument
from cheshire3.exceptions import ConfigFileException

# XXX Need a transformer to vectors for non indexed records,
#   based on index's extraction workflow.


class VectorTransformer(Transformer):
    """Transforms a Record into a Document representing it's vector.
    
    Return a representation of the Record's vector for libSVM's python binding.
    """
    
    label = ""
    labelXPath = ""
    labelXPathProcessor = None
    vectorIndex = None
    labelMap = {}
    currLabel = -1
    termInfoCache = {}

    _possibleSettings = {
        'label': {
            'docs': "Label to assign to all records"
        },
        'labelXPath': {
            'docs': "XPath expression to retrieve label from record"
        },
        'labelXPathProcessor': {
            'docs': "XPath Object to use to retrieve label from record"
        },
        'minGlobalFreq': {'docs': "", 'type': int},
        'maxGlobalFreq': {'docs': "", 'type': int},
        'minGlobalOccs': {'docs': "", 'type': int},
        'maxGlobalOccs': {'docs': "", 'type': int},
        'minLocalFreq': {'docs': "", 'type': int},
        'maxLocalFreq': {'docs': "", 'type': int},
        'minGlobalFreqPct': {'docs': "", 'type': float},
        'maxGlobalFreqPct': {'docs': "", 'type': float},
        'minGlobalOccsPct': {'docs': "", 'type': float},
        'maxGlobalOccsPct': {'docs': "", 'type': float},
        'minPropGlobalFreqPct': {'docs': "", 'type': float},
        'maxPropGlobalFreqPct': {'docs': "", 'type': float},
        'minPropGlobalOccsPct': {'docs': "", 'type': float},
        'maxPropGlobalOccsPct': {'docs': "", 'type': float},
        'minLocalFreqPct': {'docs': "", 'type': float},
        'maxLocalFreqPct': {'docs': "", 'type': float},
        'maxNGlobalFreq': {'docs': "", 'type': int},
        'maxNGlobalOccs': {'docs': "", 'type': int},
        'maxNGlobalFreqPct': {'docs': "", 'type': float},
        'maxNGlobalOccsPct': {'docs': "", 'type': float},
        'minNLocalFreq': {'docs': "", 'type': int},
        'maxNLocalFreq': {'docs': "", 'type': int},
    }

    _possiblePaths = {
        'vectorIndex': {
            'docs': "Index from which to get the vectors"
        }
    }

    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        self.label = self.get_setting(session, 'label', '')        
        if not self.label:
            self.labelXPath = self.get_setting(session, 'labelXPath', '')
            if not self.labelXPath:
                lxpo = self.get_setting(session, 'labelXPathProcessor', '')
                if not lxpo:
                    raise ConfigFileException("No label (class) source set "
                                              "for %s" % (self.id))
                else:
                    # Will raise if not found
                    self.labelXPathProcessor = db.get_object(session, lxpo)
        # And now get vector index
        self.vectorIndex = self.get_path(session, 'vectorIndex')
        self.minGlobalFreq = self.get_setting(session, 'minGlobalFreq', -1)
        self.maxGlobalFreq = self.get_setting(session, 'maxGlobalFreq', -1)
        self.minGlobalOccs = self.get_setting(session, 'minGlobalOccs', -1)
        self.maxGlobalOccs = self.get_setting(session, 'maxGlobalOccs', -1)
        self.minLocalFreq = self.get_setting(session, 'minLocalFreq', -1)
        self.maxLocalFreq = self.get_setting(session, 'maxLocalFreq', -1)

        self.minGlobalFreqPct = self.get_setting(session,
                                                 'minGlobalFreqPct',
                                                 -1.0)
        self.maxGlobalFreqPct = self.get_setting(session,
                                                 'maxGlobalFreqPct',
                                                 -1.0)
        self.minGlobalOccsPct = self.get_setting(session,
                                                 'minGlobalOccsPct',
                                                 -1.0)
        self.maxGlobalOccsPct = self.get_setting(session,
                                                 'maxGlobalOccsPct',
                                                 -1.0)

        self.minPropGlobalFreqPct = self.get_setting(session,
                                                     'minPropGlobalFreqPct',
                                                     -1.0)
        self.maxPropGlobalFreqPct = self.get_setting(session,
                                                     'maxPropGlobalFreqPct',
                                                     -1.0)
        self.minPropGlobalOccsPct = self.get_setting(session,
                                                     'minPropGlobalOccsPct',
                                                     -1.0)
        self.maxPropGlobalOccsPct = self.get_setting(session,
                                                     'maxPropGlobalOccsPct',
                                                     -1.0)

        self.minLocalFreqPct = self.get_setting(session,
                                                'minLocalFreqPct',
                                                -1.0)
        self.maxLocalFreqPct = self.get_setting(session,
                                                'maxLocalFreqPct',
                                                -1.0)

        self.maxNGlobalFreq = self.get_setting(session,
                                               'maxNGlobalFreq',
                                               -1)
        self.maxNGlobalOccs = self.get_setting(session,
                                               'maxNGlobalOccs',
                                               -1)
        self.maxNGlobalFreq = self.get_setting(session,
                                               'maxNGlobalFreqPct',
                                               -1.0)
        self.maxNGlobalOccs = self.get_setting(session,
                                               'maxNGlobalOccsPct',
                                               -1.0)
        self.minNLocalFreq = self.get_setting(session,
                                              'minNLocalFreq',
                                              -1)
        self.maxNLocalFreq = self.get_setting(session,
                                              'maxNLocalFreq',
                                              -1)

        self.idxMetadata = self.vectorIndex.fetch_metadata(session)

        db = session.server.get_object(session, session.database)
        self.totalRecords = db.totalRecords
        
        self.clear(session)

    def clear(self, session):
        # clear data from multiple calls
        self.labelMap = {}
        self.currLabel = -1
        self.termInfoCache = {}

    def process_record(self, session, rec):
        if isinstance(rec, Record):
            v = rec.fetch_vector(session, self.vectorIndex)
        else:
            # performance hack -- given resultSetItem, not record
            v = self.vectorIndex.fetch_vector(session, rec)
        # New format:  [totalTerms, totalFreq, [(t,f),(t,f)...]]
        # Don't care about summary info, strip
        try:
            v = v[2]
        except:
            # Record is empty
            return StringDocument([None, {}])
            
        # Load absolute thresholds
        # Note that thresholds may also be set on index
        minLf = self.minLocalFreq
        maxLf = self.maxLocalFreq
        minGf = self.minGlobalFreq
        maxGf = self.maxGlobalFreq
        minGo = self.maxGlobalOccs
        maxGo = self.maxGlobalOccs

        # Term occs as percentage of tokens in record
        minLfP = self.minLocalFreqPct
        maxLfP = self.maxLocalFreqPct
        # Term total recs as percentage of total recs in db
        minGfP = self.minGlobalFreqPct
        maxGfP = self.maxGlobalFreqPct
        # Term total occs as percentage of total occs in db
        minGoP = self.maxGlobalOccsPct
        maxGoP = self.maxGlobalOccsPct
        # Term total recs as percentage of max total recs
        minPGfP = self.minPropGlobalFreqPct
        maxPGfP = self.maxPropGlobalFreqPct
        # Term total occs as percentage of max total occs
        minPGoP = self.minPropGlobalOccsPct
        maxPGoP = self.maxPropGlobalOccsPct

        # MaxN == discard above N, minN == discard below N
        # For below, will discard all at same freq
        minNLf = self.minNLocalFreq
        maxNLf = self.maxNLocalFreq
        maxNGf = self.maxNGlobalFreq
        maxNGo = self.maxNGlobalOccs
        # and as a percentage of nTerms in index
        maxNGfP = self.maxNGlobalFreqPct
        maxNGoP = self.maxNGlobalOccsPct

        # First pass on locals (fast)
        if minLf != -1 or maxLf != -1:
            if minLf != -1 and maxLf != -1:
                v = [x for x in v if (x[1] >= minLf and x[1] <= maxLf)]
            elif minLf == -1:
                v = [x for x in v if x[1] <= maxLf]
            else:
                v = [x for x in v if x[1] >= minLf]

        if minLfP != -1.0 or maxLfP != -1.0:
            # Local record percentage
            total = sum([x[1] for x in v])
            minThresh = total * (minLfP / 100)
            maxThresh = total * (maxLfP / 100)
            if minThresh > 0 and maxThresh > 0:
                v = [x for x in v if (x[1] >= minThresh and x[1] <= maxThresh)]
            elif maxThresh > 0:
                v = [x for x in v if (x[1] <= maxThresh)]
            else:
                v = [x for x in v if (x[1] >= minThresh)]

        if minNLf != -1 or maxNLf != -1:
            # discard top/bottom N values
            v.sort(key=lambda x: x[1])
            if maxNLf != -1:
                v = v[maxNLf:]
            if minNLf != -1:
                minThresh = v[2][minNLf][1]                
                v = v[:0 - minNLf]
                while v and v[-1][1] == minThresh:
                    v.pop(-1)
            v.sort(key=lambda x: x[0])

        # now check globals (v slow)

        if maxNGf != -1 or maxNGo != -1 or maxNGfP != -1 or maxNGoP != -1:
            discard = []
            # minNG* is meaningless. just discard count=1 or count=2
            if maxNGf != -1:
                # fetch maxNGf from top of rec freq list 
                tfs = self.vectorIndex.fetch_termFrequencies(session,
                                                             mType='rec',
                                                             nTerms=maxNGf)
                discard.extend([x[2] for x in tfs])
            if maxNGo != -1:
                tfs = self.vectorIndex.fetch_termFrequencies(session,
                                                             mType='occ',
                                                             nTerms=maxNGo)
                discard.extend([x[2] for x in tfs])
            if maxNGfP != -1:
                # percentage of total nTerms in index
                n = self.idxMetadata['nterms'] * (maxNGfP / 100.0)
                tfs = self.vectorIndex.fetch_termFrequencies(session,
                                                             mType='rec',
                                                             nTerms=n)
                discard.extend([x[2] for x in tfs])
            if maxNGoP != -1:
                # percentage of total nTerms in index
                n = self.idxMetadata['nterms'] * (maxNGoP / 100.0)
                tfs = self.vectorIndex.fetch_termFrequencies(session,
                                                             mType='rec',
                                                             nTerms=n)
                discard.extend([x[2] for x in tfs])

            v = [x for x in v if not x[0] in discard]

        allthresh = [minGf, maxGf,
                     minGo, maxGo,
                     minGfP, maxGfP,
                     minGoP, maxGoP]

        if sum(allthresh) != -8:
            # Fetch term from termid, fetch stats from index
            nv = []
            for x in v:
                try:
                    (tdocs, toccs) = self.termInfoCache[x[0]]
                except:
                    term = self.vectorIndex.fetch_termById(session, x[0])
                    try:
                        (termId, tdocs, toccs) = self.vectorIndex.fetch_term(
                            session,
                            term,
                            summary=True
                        )
                    except:
                        continue
                    if tdocs > 2:
                        # Only cache if going to look up more than twice anyway
                        self.termInfoCache[x[0]] = (tdocs, toccs)
                okay = 1
                if minGf != -1 and tdocs < minGf:
                    okay = 0
                elif maxGf != -1 and tdocs > maxGf:
                    okay = 0
                elif minGo != -1 and toccs < minGo:
                    okay = 0
                elif maxGo != -1 and toccs > maxGo:
                    okay = 0
                elif (
                    minGfP != -1 and
                    tdocs < self.totalRecords * (minGfP / 100)
                ):
                    okay = 0
                elif (
                    maxGfP != -1 and
                    tdocs > self.totalRecords * (maxGfP / 100)
                ):
                    okay = 0
                elif (
                    minPGfP != -1 and
                    tdocs < self.idxMetadata['maxRecs'] * (minPGfP / 100)
                ):
                    okay = 0
                elif (
                    maxPGfP != -1 and
                    tdocs > self.totalRecords['maxRecs'] * (maxPGfP / 100)
                ):
                    okay = 0
                elif (
                    minGoP != -1 and
                    toccs < self.idxMetadata['nOccs'] * (minGoP / 100)
                ):
                    okay = 0
                elif (
                    maxGoP != -1 and
                    toccs > self.idxMetadata['nOccs'] * (maxGoP / 100)
                ):
                    okay = 0
                elif (
                    minPGoP != -1 and
                    toccs < self.idxMetadata['maxOccs'] * (minPGoP / 100)
                ):
                    okay = 0
                elif (
                    maxPGoP != -1 and
                    toccs > self.idxMetadata['maxOccs'] * (maxPGoP / 100)
                ):
                    okay = 0

                if okay:
                    nv.append(x)
            v = nv

        # Phew!

        # Now convert to {}
        vhash = {}
        vhash.update(v)

        # Find label from self or data
        l = self.label
        if l == "":
            if self.labelXPath:
                l = rec.process_xpath(session, self.labelXPath)
            elif self.labelXPathProcessor:
                l = self.labelXPathProcessor.process_record(session, rec)
            else:
                # no label, should never get here
                raise ConfigFileException("No label (class) source set for "
                                          "%s" % (self.id))
            if l and type(l) == list:
                l = l[0]
            else:
                l = "missing class"

        # assign int to label
        if type(l) != int and (type(l) in [str, unicode] and not l.isdigit()):
            # assign mapping to an int
            exists = self.labelMap.get(l, None)
            if exists is not None:
                l = exists
            else:
                self.currLabel += 1
                self.labelMap[l] = self.currLabel
                l = self.currLabel
        if l.isdigit():
            l = long(l)
        data = (l, vhash)
        return StringDocument(data)


class ArmVectorTransformer(Transformer):

    _possibleSettings = {
        'minGlobalFreq': {'docs': "", 'type': int},
        'maxGlobalFreq': {'docs': "", 'type': int},
        'minGlobalOccs': {'docs': "", 'type': int},
        'maxGlobalOccs': {'docs': "", 'type': int},
        'minLocalFreq': {'docs': "", 'type': int},
        'maxLocalFreq': {'docs': "", 'type': int},
        'stopwords': {'docs': '', 'type': str},
        'reqdwords': {'docs': '', 'type': str},
        'proxElement': {'docs': "", 'type': int, 'options': '0|1'},
        'matchesOnly': {'docs': "", 'type': int, 'options': '0|1'},
        'stripMatch': {'docs': "", 'type': int, 'options': '0|1'}
    }
    
    _possiblePaths = {
        'vectorIndex': {
            'docs': "Index from which to get the vectors"
        }
    }

    vectorIndex = None
    minGlobalFreq = -1
    maxGlobalFreq = -1
    minGlobalOccs = -1
    maxGlobalOccs = -1
    minLocalFreq = -1
    miaxLocalFreq = -1
    termInfoCache = {}

    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        self.vectorIndex = self.get_path(session, 'vectorIndex')
        self.minGlobalFreq = self.get_setting(session, 'minGlobalFreq', -1)
        self.maxGlobalFreq = self.get_setting(session, 'maxGlobalFreq', -1)
        self.minGlobalOccs = self.get_setting(session, 'minGlobalOccs', -1)
        self.maxGlobalOccs = self.get_setting(session, 'maxGlobalOccs', -1)
        self.minLocalFreq = self.get_setting(session, 'minLocalFreq', -1)
        self.maxLocalFreq = self.get_setting(session, 'maxLocalFreq', -1)
        self.prox = self.get_setting(session, 'proxElement', 0)
        self.matches = self.get_setting(session, 'matchesOnly', 0)
        self.stripMatch = self.get_setting(session, 'stripMatch', 0)

        sw = self.get_setting(session, 'stopwords', '')
        ignoreTermids = []
        for w in sw.split(' '):
            if w:
                try:
                    (tid, bla, bla2) = self.vectorIndex.fetch_term(
                        session,
                        w,
                        summary=True
                    )                    
                    ignoreTermids.append(tid)
                except ValueError:
                    # Term doesn't exist
                    pass
        self.ignoreTermids = ignoreTermids
        sw = self.get_setting(session, 'reqdwords', '')
        mandatoryTermids = []
        for w in sw.split(' '):
            if w:
                try:
                    (tid, bla, bla2) = self.vectorIndex.fetch_term(
                        session,
                        w,
                        summary=True
                    )                    
                    mandatoryTermids.append(tid)
                except ValueError:
                    # Term doesn't exist
                    pass
        self.mandatoryTermids = mandatoryTermids
        self._clear(session)

    def _clear(self, session):
        self.termInfoCache = {}

    def _processVector(self, session, v):
        # Load thresholds from self
        # Note that thresholds may also be set on index
        minLf = self.minLocalFreq
        maxLf = self.maxLocalFreq
        minGf = self.minGlobalFreq
        maxGf = self.maxGlobalFreq
        minGo = self.minGlobalOccs
        maxGo = self.maxGlobalOccs

        # First pass on locals (v fast)
        if minLf != -1 or maxLf != -1:
            if minLf != -1 and maxLf != -1:
                v = [x for x in v if (x[1] >= minLf and x[1] <= maxLf)]
            elif minLf == -1:
                v = [x for x in v if x[1] <= maxLf]
            else:
                v = [x for x in v if x[1] >= minLf]

        # Now check globals (v slow)
        if minGf != -1 or maxGf != -1 or minGo != -1 or maxGo != -1:
            # Fetch term from termid, fetch stats from index
            nv = []
            for x in v:
                try:
                    (tdocs, toccs) = self.termInfoCache[x[0]]
                except:
                    term = self.vectorIndex.fetch_termById(session, x[0])
                    try:
                        (termId, tdocs, toccs) = self.vectorIndex.fetch_term(
                            session,
                            term,
                            summary=True
                        )
                    except:
                        continue
                    if tdocs > 2:
                        # only cache if going to look up more than twice anyway
                        self.termInfoCache[x[0]] = (tdocs, toccs)
                if (
                    (minGf == -1 or tdocs >= minGf) and
                    (maxGf == -1 or tdocs <= maxGf) and
                    (minGo == -1 or toccs >= minGo) and
                    (maxGo == -1 or toccs <= maxGo)
                ):
                    nv.append(x)
            v = nv
            
        if self.ignoreTermids:
            its = self.ignoreTermids
            v = [x for x in v if not x[0] in its]
        if self.mandatoryTermids:
            mts = self.mandatoryTermids
            found = 0
            for x in v:
                if x[0] in mts:
                    found = 1
                    break
            if not found:
                v = {}

        vhash = {}
        vhash.update(v)
        return vhash

    def process_record(self, session, rec):
        if self.prox:
            if isinstance(rec, Record):
                pv = rec.fetch_proxVector(session, self.vectorIndex)
            else:
                if self.matches:
                    if self.stripMatch:
                        # This only works if search on same index as vectors
                        pv = {}
                        for pi in rec.proxInfo:
                            elm = pi[0][0]
                            if not pv.has_key(elm):
                                pv[elm] = self.vectorIndex.fetch_proxVector(
                                    session,
                                    rec,
                                    elm
                                )
                            # Delete match out of vector
                            for m in pi:
                                for pvi in pv[elm]:
                                    if pvi[0] == m[1]:
                                        # Delete, break
                                        pv[elm].remove(pvi)
                                        break
                    else:
                        elems = [x[0][0] for x in rec.proxInfo]
                        elms = set(elems)
                        pv = {}
                        for e in elms:
                            pv[e] = self.vectorIndex.fetch_proxVector(
                                session,
                                rec,
                                e
                            )
                else:
                    pv = self.vectorIndex.fetch_proxVector(session, rec)

            # Now map each element to vector format and process
            hashs = []
            for pve in pv.itervalues():
                v = {}
                for k in pve:
                    tid = k[1]
                    try:
                        v[tid] += 1
                    except:
                        v[tid] = 1
                
                vec = v.items()                
                vh = self._processVector(session, vec)
                if vh:
                    hashs.append((-1, vh))            
            # This won't chain with vector PreParsers yet
            return StringDocument(hashs)
        else:
            if isinstance(rec, Record):
                v = rec.fetch_vector(session, self.vectorIndex)
            else:
                # Performance hack -- given resultSetItem, not record
                v = self.vectorIndex.fetch_vector(session, rec)
            try:
                v = v[2]
            except:
                # record is empty
                return StringDocument((-1, {}))
            vh = self._processVector(session, v)
            if vh:
                return StringDocument((-1, vh))
            else:
                return StringDocument((-1, {}))


class SplitArmVectorTransformer(ArmVectorTransformer):
    
    _possibleSettings = {
        'splitIds': {
            'docs': 'space separated termids to split on'
        }
    }
    
    _possiblePaths = {
        'vectorIndex2': {
            'docs': "Index on which to split"
        }
    }

    vectorIndex = None
    minGlobalFreq = -1
    maxGlobalFreq = -1
    minGlobalOccs = -1
    maxGlobalOccs = -1
    minLocalFreq = -1
    miaxLocalFreq = -1
    termInfoCache = {}

    def __init__(self, session, config, parent):
        ArmVectorTransformer.__init__(self, session, config, parent)
        self.vectorIndex2 = self.get_path(session, 'vectorIndex2')
        tids = self.get_setting(session, 'splitIds', "")
        self.splitIds = map(int, tids.split(' '))
        self._clear(session)

    def _clear(self, session):
        self.termInfoCache = {}

    def _processVector(self, session, v):
        # Load thresholds from self
        # Note that thresholds may also be set on index
        minLf = self.minLocalFreq
        maxLf = self.maxLocalFreq
        minGf = self.minGlobalFreq
        maxGf = self.maxGlobalFreq
        minGo = self.minGlobalOccs
        maxGo = self.maxGlobalOccs

        # First pass on locals (v fast)
        if minLf != -1 or maxLf != -1:
            if minLf != -1 and maxLf != -1:
                v = [x for x in v if (x[1] >= minLf and x[1] <= maxLf)]
            elif minLf == -1:
                v = [x for x in v if x[1] <= maxLf]
            else:
                v = [x for x in v if x[1] >= minLf]

        # Now check globals (v slow)
        if minGf != -1 or maxGf != -1 or minGo != -1 or maxGo != -1:
            # Fetch term from termid, fetch stats from index
            nv = []
            for x in v:
                try:
                    (tdocs, toccs) = self.termInfoCache[x[0]]
                except:
                    term = self.vectorIndex.fetch_termById(session, x[0])
                    try:
                        (termId, tdocs, toccs) = self.vectorIndex.fetch_term(
                            session,
                            term,
                            summary=True
                        )
                    except:
                        continue
                    if tdocs > 2:
                        # Only cache if going to look up more than twice anyway
                        self.termInfoCache[x[0]] = (tdocs, toccs)
                if (
                    (minGf == -1 or tdocs >= minGf) and
                    (maxGf == -1 or tdocs <= maxGf) and
                    (minGo == -1 or toccs >= minGo) and
                    (maxGo == -1 or toccs <= maxGo)
                ):
                    nv.append(x)
            v = nv
        vhash = {}
        vhash.update(v)
        return vhash

    def process_record(self, session, rec):
        if self.prox:
            if isinstance(rec, Record):
                pv = rec.fetch_proxVector(session, self.vectorIndex)
                pv2 = rec.fetch_proxVector(session, self.vectorIndex2)
            else:
                if self.matches:
                    elems = [x[0][0] for x in rec.proxInfo]
                    elms = set(elems)
                    pv = {}
                    pv2 = {}
                    for e in elms:
                        pv[e] = self.vectorIndex.fetch_proxVector(session,
                                                                  rec,
                                                                  e)
                        pv2[e] = self.vectorIndex2.fetch_proxVector(session,
                                                                    rec,
                                                                    e)
                else:
                    pv = self.vectorIndex.fetch_proxVector(session, rec)
                    pv2 = self.vectorIndex2.fetch_proxVector(session, rec)
            # Now map each element to vector format and process

            splits = self.splitIds
            hashs = []
            for (e, pvi2) in pv2.iteritems():
                try:
                    pvi = pv[e]
                    try:
                        pvihash = dict(pvi)
                    except:
                        # Might be triples w/ offset
                        pvi = [(x[0], x[1]) for x in pvi]
                        pvihash = dict(pvi)
                except KeyError:
                    # vector in pv is empty
                    continue
                v = {}
                
                # step through pvi2, find splitId
                # write from pvi to v
                for k in pvi2:
                    if k[1] in splits:
                        # finish
                        vec = v.items()
                        v = {}
                        vh = self._processVector(session, vec)
                        if vh:
                            hashs.append((-1, vh))
                    elif pvihash.has_key(k[0]):
                        pvik = pvihash[k[0]]
                        try:
                            v[pvik] += 1
                        except:
                            v[pvik] = 1
                
                # this will catch end of vector
                vec = v.items()                
                vh = self._processVector(session, vec)
                if vh:
                    hashs.append((-1, vh))            
            # This won't chain with vector PreParsers yet
            return StringDocument(hashs)
        else:
            raise NotImplementedError()
            if isinstance(rec, Record):
                v = rec.fetch_vector(session, self.vectorIndex)
            else:
                # Performance hack -- given resultSetItem, not record
                v = self.vectorIndex.fetch_vector(session, rec)
            try:
                v = v[2]
            except:
                # Record is empty
                return StringDocument((-1, {}))
            vh = self._processVector(session, v)
            if vh:
                return StringDocument((-1, vh))
            else:
                return StringDocument((-1, {}))


class WindowArmVectorTransformer(ArmVectorTransformer):

    _possibleSettings = {
        'windowSize': {'docs': '', 'type': int},
        'step': {'docs': '', 'type': int},
        'onlyAroundMatches': {'docs': '', 'type': int}
    }

    def __init__(self, session, config, parent):
        ArmVectorTransformer.__init__(self, session, config, parent)
        self.window = self.get_setting(session, 'windowSize', 10)
        self.step = self.get_setting(session, 'stepSize', 10)
        self.onlyMatches = self.get_setting(session, 'onlyAroundMatches', 0)

    def process_record(self, session, rec):

        n = self.window
        step = self.step
        if self.prox:
            if isinstance(rec, Record):
                pv = rec.fetch_proxVector(session, self.vectorIndex)
            else:
                if self.matches:
                    elems = [x[0][0] for x in rec.proxInfo]
                    elms = set(elems)
                    pv = {}
                    for e in elms:
                        pv[e] = self.vectorIndex.fetch_proxVector(session,
                                                                  rec,
                                                                  e)
                else:
                    pv = self.vectorIndex.fetch_proxVector(session, rec)

            hashs = []
            if not self.onlyMatches:
                for pve in pv.itervalues():
                    # Split into chunks of size N, overlapping at step
                    for s in range(0, len(pve), step):
                        chunk = pve[s:s + n]
                        v = {}
                        for c in chunk:
                            try:
                                v[c[1]] += 1
                            except:
                                v[c[1]] = 1
                        vec = v.items()
                        vh = self._processVector(session, vec)
                        if vh:
                            hashs.append((-1, vh))            
            else:
                tids = {}
                for pii in rec.proxInfo:
                    for t in [x[-1] for x in pii]:
                        tids[t] = 1

                all = []
                start = -1
                hn = n / 2
                for (x, pve) in enumerate(pv.itervalues()):
                    lpve = len(pve)
                    for pvi in pve:
                        if tids.has_key(pvi[1]):
                            start = max(x - hn, 0)
                            diff = hn - (x - start)
                            end = min(x + hn + diff, lpve)
                            if start != 0:
                                diff2 = n - (end - start)
                                if diff2:
                                    start = min(start - diff2, 0)
                            chunk = pve[start:end + 1]
                            v = {}
                            for c in chunk:
                                try:
                                    v[c[1]] += 1
                                except:
                                    v[c[1]] = 1
                            vec = v.items()
                            vh = self._processVector(session, vec)
                            if vh:
                                hashs.append((-1, vh))            
            return StringDocument(hashs)
        else:
            raise NotImplementedError()


class SVMFileTransformer(VectorTransformer):
    "Return a representation of the record's vector for libSVM's C programs"

    def process_record(self, session, rec):
        doc = BaseSVMTransformer.process_record(self, session, rec)
        (l, v) = doc.get_raw(session)
        full = v.items()
        full.sort()
        vstr = ' '.join(["%s:%s" % tuple(x) for x in full])
        data = "%s %s\n" % (l, vstr)
        return StringDocument(data)
