

from baseObjects import Transformer, Record
from document import StringDocument

# XXX Need a transformer to vectors for non indexed records,
#   based on index's extraction workflow.


class VectorTransformer(Transformer):
    """ Return a representation of the record's vector for libSVM's python binding """
    label = ""
    labelXPath = ""
    labelXPathObject = None
    vectorIndex = None
    labelMap = {}
    currLabel = -1
    termInfoCache = {}

    _possibleSettings = {'label' : {'docs' : "Label to assign to all records"},
                         'labelXPath'  : {'docs' : "XPath expression to retrieve label from record"},
                         'labelXPathObject'  : {'docs' : "XPath Object to use to retrieve label from record"},
                         'minGlobalFreq' : {'docs' : "", 'type' : int},
                         'maxGlobalFreq' : {'docs' : "", 'type' : int},
                         'minGlobalOccs' : {'docs' : "", 'type' : int},
                         'maxGlobalOccs' : {'docs' : "", 'type' : int},
                         'minLocalFreq' : {'docs' : "", 'type' : int},
                         'maxLocalFreq' : {'docs' : "", 'type' : int},
                         }

    _possiblePaths = {'vectorIndex' : {'docs' : "Index from which to get the vectors"}}

    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        self.label = self.get_setting(session, 'label', '')        
        if not self.label:
            self.labelXPath = self.get_setting(session, 'labelXPath', '')
            if not self.labelXPath:
                lxpo = self.get_setting(session, 'labelXPathObject', '')
                if not lxpo:
                    raise ConfigFileException("No label (class) source set for %s" % (self.id))
                else:
                    # Will raise if not found
                    self.labelXPathObject = db.get_object(session, lxpo)
        # And now get vector index
        self.vectorIndex = self.get_path(session, 'vectorIndex')
        self.minGlobalFreq = self.get_setting(session, 'minGlobalFreq', -1)
        self.maxGlobalFreq = self.get_setting(session, 'maxGlobalFreq', -1)
        self.minGlobalOccs = self.get_setting(session, 'minGlobalOccs', -1)
        self.maxGlobalOccs = self.get_setting(session, 'maxGlobalOccs', -1)
        self.minLocalFreq = self.get_setting(session, 'minLocalFreq', -1)
        self.maxLocalFreq = self.get_setting(session, 'maxLocalFreq', -1)

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

        # new format:  [totalTerms, totalFreq, [(t,f),(t,f)...]]
        # don't care about summary info, strip
        try:
            v = v[2]
        except:
            # record is empty
            return StringDocument([None, {}])
            
        # load thresholds from self
        # note that thresholds may also be set on index
        minLf = self.minLocalFreq
        maxLf = self.maxLocalFreq
        minGf = self.minGlobalFreq
        maxGf = self.maxGlobalFreq
        minGo = self.maxGlobalOccs
        maxGo = self.maxGlobalOccs

        # first pass on locals (v fast)
        if minLf != -1 or maxLf != -1:
            if minLf != -1 and maxLf != -1:
                v = [x for x in v if (x[1] >= minLf and x[1] <= maxLf)]
            elif minLf == -1:
                v = [x for x in v if x[1] <= maxLf]
            else:
                v = [x for x in v if x[1] >= minLf]

        # now check globals (v slow)
        if minGf != -1 or maxGf != -1 or minGo != -1 or maxGo != -1:
            # fetch term from termid, fetch stats from index
            nv = []
            for x in v:
                try:
                    (tdocs, toccs) = self.termInfoCache[x[0]]
                except:
                    term = self.vectorIndex.fetch_termById(session, x[0])
                    try:
                        (termId, tdocs, toccs) = self.vectorIndex.fetch_term(session, term, summary=True)
                    except:
                        continue
                    if tdocs > 2:
                        # only cache if going to look up more than twice anyway
                        self.termInfoCache[x[0]] = (tdocs, toccs)
                if ( (minGf == -1 or tdocs >= minGf) and
                     (maxGf == -1 or tdocs <= maxGf) and
                     (minGo == -1 or toccs >= minGo) and
                     (maxGo == -1 or toccs <= maxGo)):
                    nv.append(x)
            v = nv

        # now convert to {}
        # Slow: [vhash.__setitem__(x[0], x[1]) for x in v]

        vhash = {}
        vhash.update(v)

        # Find label from self or data
        l = self.label
        if l == "":
            if self.labelXPath:
                l = rec.process_xpath(session, self.labelXPath)
            elif self.labelXPathObject:
                l = self.labelXPathObject.process_record(session, rec)
            else:
                # no label, should never get here
                raise ConfigFileException("No label (class) source set for %s" % (self.id))
            if l and type(l) == list:
                l = l[0]
            else:
                l = "missing class"

        # assign int to label
        if type(l) != int and (type(l) in [str, unicode] and not l.isdigit()):
            # assign mapping to an int
            exists = self.labelMap.get(l, None)
            if exists != None:
                l = exists
            else:
                self.currLabel += 1
                self.labelMap[l] = self.currLabel
                l = self.currLabel
        data = (l, vhash)
        return StringDocument(data)


class ArmVectorTransformer(Transformer):
    # no classes

    _possibleSettings = {
                         'minGlobalFreq' : {'docs' : "", 'type' : int},
                         'maxGlobalFreq' : {'docs' : "", 'type' : int},
                         'minGlobalOccs' : {'docs' : "", 'type' : int},
                         'maxGlobalOccs' : {'docs' : "", 'type' : int},
                         'minLocalFreq' : {'docs' : "", 'type' : int},
                         'maxLocalFreq' : {'docs' : "", 'type' : int},
                         'proxElement' : {'docs' : "", 'type' :int, 'options' : '0|1'},
                         'matchesOnly' : {'docs' : "", 'type' :int, 'options' : '0|1'}

                         }
    _possiblePaths = {'vectorIndex' : {'docs' : "Index from which to get the vectors"}}

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
        self._clear(session)

    def _clear(self, session):
        self.termInfoCache = {}


    def _processVector(self, session, v):
        # load thresholds from self
        # note that thresholds may also be set on index
        minLf = self.minLocalFreq
        maxLf = self.maxLocalFreq
        minGf = self.minGlobalFreq
        maxGf = self.maxGlobalFreq
        minGo = self.maxGlobalOccs
        maxGo = self.maxGlobalOccs

        # first pass on locals (v fast)
        if minLf != -1 or maxLf != -1:
            if minLf != -1 and maxLf != -1:
                v = [x for x in v if (x[1] >= minLf and x[1] <= maxLf)]
            elif minLf == -1:
                v = [x for x in v if x[1] <= maxLf]
            else:
                v = [x for x in v if x[1] >= minLf]

        # now check globals (v slow)
        if minGf != -1 or maxGf != -1 or minGo != -1 or maxGo != -1:
            # fetch term from termid, fetch stats from index
            nv = []
            for x in v:
                try:
                    (tdocs, toccs) = self.termInfoCache[x[0]]
                except:
                    term = self.vectorIndex.fetch_termById(session, x[0])
                    try:
                        (termId, tdocs, toccs) = self.vectorIndex.fetch_term(session, term, summary=True)
                    except:
                        continue
                    if tdocs > 2:
                        # only cache if going to look up more than twice anyway
                        self.termInfoCache[x[0]] = (tdocs, toccs)
                if ( (minGf == -1 or tdocs >= minGf) and
                     (maxGf == -1 or tdocs <= maxGf) and
                     (minGo == -1 or toccs >= minGo) and
                     (maxGo == -1 or toccs <= maxGo)):
                    nv.append(x)
            v = nv

        vhash = {}
        vhash.update(v)
        return vhash

    def process_record(self, session, rec):
        if self.prox:
            if isinstance(rec, Record):
                pv = rec.fetch_proxVector(session, self.vectorIndex)
            else:
                if self.matches:
                    elems = [x[0][0] for x in rec.proxInfo]
                    elms = set(elems)
                    pv = {}
                    for e in elms:
                        pv[e] = self.vectorIndex.fetch_proxVector(session, rec, e)
                else:
                    pv = self.vectorIndex.fetch_proxVector(session, rec)
            # now map each element to vector format and process

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
                # performance hack -- given resultSetItem, not record
                v = self.vectorIndex.fetch_vector(session, rec)
            try:
                v = v[2]
            except:
                # record is empty
                return StringDocument((-1, {}))
            vh  = self._processVector(session, v)
            if vh:
                return StringDocument((-1, vh))
            else:
                return StrindDocument((-1, {}))

        
    


class SVMFileTransformer(VectorTransformer):
    """ Return a representation of the record's vector for libSVM's C programs """

    def process_record(self, session, rec):
        doc = BaseSVMTransformer.process_record(self, session, rec)
        (l,v) = doc.get_raw(session)
        full = v.items()
        full.sort()
        vstr = ' '.join(["%s:%s" % tuple(x) for x in full])
        data = "%s %s\n" % (l, vstr)
        return StringDocument(data)


