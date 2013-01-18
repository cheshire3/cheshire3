from __future__ import absolute_import

import os
import random
import tempfile
import commands
import math
import re
import operator

try:
    import cPickle as pickle
except ImportError:
    import pickle

from cheshire3.baseObjects import PreParser
from cheshire3.document import StringDocument
from cheshire3.exceptions import ConfigFileException
from cheshire3.exceptions import MissingDependencyException


class VectorRenumberPreParser(PreParser):

    _possibleSettings = {'termOffset': {'docs': "", 'type': int}} 
    _possiblePaths = {'modelPath': {'docs': ""}}

    def __init__(self, session, config, parent):
        PreParser.__init__(self, session, config, parent)
        # Some settings that are needed at this stage
        self.offset = self.get_setting(session, 'termOffset', 0)
        
    def process_document(self, session, doc):
        (labels, vectors) = doc.get_raw(session)

        # Find max attr
        all = {}
        for v in vectors:
            all.update(v)
        keys = all.keys()
        keys.sort()
        maxattr = keys[-1]
        nattrs = len(keys)

        # Remap vectors to reduced space
        renumbers = range(self.offset, nattrs + self.offset)
        renumberhash = dict(zip(keys, renumbers))
        newvectors = []
        for vec in vectors:
            new = {}
            for (k, v) in vec.items():
                new[renumberhash[k]] = v 
            newvectors.append(new)

        # Pickle renumberhash
        pick = pickle.dumps(renumberhash)
        filename = self.get_path(session, 'modelPath', None)
        if not filename:
            dfp = self.get_path(session, 'defaultPath')
            filename = os.path.join(dfp, self.id + "_ATTRHASH.pickle")
        f = file(filename, 'w')
        f.write(pick)
        f.close()
        return StringDocument((labels, newvectors, nattrs))


class VectorUnRenumberPreParser(PreParser):

    _possibleSettings = {'termOffset': {'docs': "", 'type': int}} 
    _possiblePaths = {'modelPath': {'docs': ""}}

    def __init__(self, session, config, parent):
        PreParser.__init__(self, session, config, parent)
        # Some settings that are needed at this stage
        self.offset = self.get_setting(session, 'termOffset', 0)
        filename = self.get_path(session, 'modelPath', None)
        if not filename:
            dfp = self.get_path(session, 'defaultPath')
            filename = os.path.join(dfp, self.id + "_ATTRHASH.pickle")
        self.modelPath = filename
        self.model = {}
        self.lastModTime = 0
        self.load_model(session)

    def load_model(self, session):
        # Store last written time, in case we change
        filename = self.modelPath
        if os.path.exists(filename):
            si = os.stat(filename)
            lastMod = si.st_mtime
            if lastMod > self.lastModTime:
                inh = file(filename)
                inhash = pickle.load(inh)
                inh.close()
                # Now reverse our keys/values
                self.model = dict(zip(inhash.values(), inhash.keys()))

                si = os.stat(filename)
                self.lastModTime = si.st_mtime
                return 1
            else:
                return 0
        else:
            return 0

    def process_document(self, session, doc):
        self.load_model(session)
        data = doc.get_raw(session)
        # Data should be list of list of ints to map
        g = self.model.get
        ndata = []
        for d in data:
            n = []
            for i in d:
                n.append(g(i))
            ndata.append(n)
        return StringDocument(ndata)
    

class ARMVectorPreParser(PreParser):

    def process_document(self, session, doc):
        (labels, vectors) = doc.get_raw(session)[:2]
        txt = []
        for v in vectors:
            k = v.keys()
            if k:
                k.sort()
                txt.append(' '.join(map(str, k)))
        return StringDocument('\n'.join(txt))


class ARMPreParser(PreParser):

    _possibleSettings = {
        'support': {
            'docs': "Support value", 'type': float
        }, 'confidence': {
            'docs': "Confidence value", 'type': float
        }, 'absoluteSupport': {
            'docs': 'Number of records for supp, not %', 'type': int
        }
    } 

    def __init__(self, session, config, parent):
        PreParser.__init__(self, session, config, parent)
        self.support = self.get_setting(session, 'support', 10.0)
        self.absSupport = self.get_setting(session, 'absoluteSupport', 0)
        self.confidence = self.get_setting(session, 'confidence', 0.0)


class TFPPreParser(ARMPreParser):

    _possibleSettings = {
        'memory': {
            'docs': "How much memory to let Java use", 'type': int
        }
    }

    _possiblePaths = {
        'filePath': {
            'docs': 'Directory where TFP lives'
        }, 'javaPath': {
            'docs': 'Full path to java executable'
        }
    }

    def __init__(self, session, config, parent):
        ARMPreParser.__init__(self, session, config, parent)
        # Check we know where TFP is etc
        self.filePath = self.get_path(session, 'filePath', None)        
        if not self.filePath:
            raise ConfigFileException("%s requires the path: filePath"
                                      "" % self.id)
        self.java = self.get_path(session, 'javaPath', 'java')
        self.memory = self.get_setting(session, 'memory', 1000)

    def process_document(self, session, doc):
        # Write out our temp file
        (qq, infn) = tempfile.mkstemp(".tfp")
        fh = file(infn, 'w')
        fh.write(doc.get_raw(session))
        fh.close()

        # Go to TFP directory and run
        o = os.getcwd()
        os.chdir(self.filePath)
        results = commands.getoutput("%s -Xms%sm -Xmx%sm AprioriTFPapp "
                                     "-F../%s -S%s -C%s"
                                     "" % (self.java, self.memory, self.memory,
                                           infn, self.support, self.confidence)
                                     )
        os.chdir(o)
        # Process results
        resultLines = results.split('\n')
        matches = []
        for l in resultLines:
            m = freqRe.search(l)
            if m:
                (set, freq) = m.groups()
                matches.append((int(freq), set))
        if not matches:
            # No FIS for some reason, return results??
            return StringDocument(results)
        matches.sort(reverse=True)
        return StringDocument(matches)


class Fimi1PreParser(ARMPreParser):

    _possibleSettings = {
        'singleItems': {
            'docs': '', 'type': int, 'options': '0|1'
        }
    }

    _possiblePaths = {
        'filePath': {
            'docs': 'Directory where fimi01 executable (apriori) lives'
        }
    }

    def __init__(self, session, config, parent):
        ARMPreParser.__init__(self, session, config, parent)
        # Check we know where TFP is etc
        self.filePath = self.get_path(session, 'filePath', None)
        #if not self.filePath:
        #    raise ConfigFileException("%s requires the path: filePath"
        #                              "" % self.id)
        self.fisre = re.compile("([0-9 ]+) \(([0-9]+)\)")
        self.rulere = re.compile("([0-9 ]+) ==> ([0-9 ]+) "
                                 "\(([0-9.]+), ([0-9]+)\)")
        self.singleItems = self.get_setting(session, 'singleItems', 0)

    def process_document(self, session, doc):
        # write out our temp file
        (qq, infn) = tempfile.mkstemp(".arm")
        fh = file(infn, 'w')
        fh.write(doc.get_raw(session))
        fh.close()

        if self.absSupport:
            t = len(doc.get_raw(session).split('\n'))
            self.support = (float(self.absSupport) / float(t)) * 100

        (qq, outfn) = tempfile.mkstemp(".txt")
        # go to directory and run
        o = os.getcwd()
        #os.chdir(self.filePath)
        if self.confidence > 0:
            cmd = "apriori %s %s %f %s" % (infn, outfn,
                                           self.support / 100,
                                           self.confidence / 100)
        else:
            cmd = "apriori %s %s %s" % (infn, outfn,
                                        self.support / 100)
        results = commands.getoutput(cmd)
        #os.chdir(o)
        inh = file(outfn)
        fis = self.fisre
        rule = self.rulere
        singleItems = self.singleItems
        matches = []
        rules = []
        for line in inh:
            # Matching line looks like N N N (N)
            # Rules look like N N ==> N (f, N)
            m = fis.match(line)
            if m:
                (set, freq) = m.groups()
                if singleItems or set.find(' ') > -1:
                    matches.append((int(freq), set))
            elif self.confidence > 0:
                m = rule.match(line)
                if m:
                    (ante, conc, conf, supp) = m.groups()
                    al = map(int, ante.split(' '))
                    cl = map(int, conc.split(' '))
                    rules.append((float(conf), int(supp), al, cl))
        inh.close()
        # Delete temp files!
        os.remove(outfn)
        os.remove(infn)
        if not matches:
            # No FIS for some reason, return results??
            return StringDocument([results, []])
        matches.sort(reverse=True)
        rules.sort(reverse=True)
        os.chdir(o)
        doc = StringDocument([matches, rules])
        return doc


class MagicFimi1PreParser(Fimi1PreParser):
    
    _possibleSettings = {
        'minRules': {
            'docs': "",
            'type': int
        },
        'minItemsets': {
            'docs': "",
            'type': int
        }
    }

    def __init__(self, session, config, parent):
        Fimi1PreParser.__init__(self, session, config, parent)
        self.minRules = self.get_setting(session, 'minRules', -1)
        self.minFIS = self.get_setting(session, 'minItemsets', -1)

        if self.minRules > 0 and self.confidence <= 0:
            raise ConfigFileException("minRules setting not allowed without "
                                      "confidence setting on %s" % (self.id))

    def process_document(self, session, doc):
        # try to find our best support threshold
        s = self.get_setting(session, 'support', 12.0)
        lr = -1
        lf = -1
        maxiters = 12
        iters = 0
        minRules = self.minRules
        minFIS = self.minFIS

        while True:
            iters += 1
            if iters > maxiters:
                break
            lasts = self.support
            lastlr = lr
            lastlf = lf
            self.support = s
            d2 = Fimi1PreParser.process_document(self, session, doc)
            (fis, rules) = d2.get_raw(session)

            lr = len(rules)
            lf = len(fis)
            print "%s --> %s, %s" % (s, lr, lf)

            if minRules != -1:
                if lr == lastlr:
                    # Keep going back, change didn't make any difference
                    s = s * 1.5
                elif lr >= minRules * 2:
                    # go back
                    s = (lasts + s) / 2.0
                elif lr >= minRules:
                    # Stop
                    break
                elif lr * 3 < minRules:
                    # Go forward a bit
                    s = s / 2.0
                elif lr * 7 < minRules:
                    # Go forward a lot
                    s = s / 3.0
                else:
                    s = s / 1.5
                if minFIS != -1 and lf > minFIS:
                    break
            elif minFIS != -1:
                if lf == lastlf:
                    # Keep going back, change didn't make any difference
                    s = s * 1.5
                elif lf >= minFIS * 2:
                    # Go back
                    s = (lasts + s) / 2.0
                elif lf >= minFIS:
                    # Stop
                    break
                elif lf * 3 < minFIS:
                    # Go forward a bit
                    s = s / 2.0
                elif lf * 7 < minFIS:
                    # Go forward a lot
                    s = s / 3.0
                else:
                    s = s / 1.5
                if minRules != -1 and lf > minRules:
                    break
        self.support = s
        return d2


class FrequentSet(object):

    freq = 0
    termids = []
    avgs = []
    avg = 0
    pctg = 0
    opctg = 0
    ll = 0
    surprise = 0
    entropy = 0
    gini = 0
    termidFreqs = {}
    termidRules = {}
    document = None

    def __repr__(self):
        termList = []
        ts = self.termidRules.items()
        ts.sort(key=lambda x: x[1], reverse=True)

        for t in ts:
            termList.append("%s %s" % (self.document.termHash[t[0]], t[1]))
        terms = " ".join(termList)
        return "<Rule Object:  %s (%s)>" % (terms, self.freq)

    def __str__(self):
        termList = []
        ts = self.termidRules.items()
        ts.sort(key=lambda x: x[1], reverse=True)

        for t in ts:
            termList.append(repr(self.document.termHash[t[0]]))
        return " ".join(termList)

    def toXml(self):
        termList = []
        ts = self.termids[:]
        ts.sort()
        items = ['<item tid="%s">%s</item>' % (x, self.document.termHash[x])
                 for x
                 in ts
                 ]
        itemstr = ''.join(items)
        return ('<set support="%s" ll="%s" entropy="%s" surprise="%s" '
                'gini="%s">%s</set>'
                '' % (self.freq, self.ll, self.entropy,
                      self.surprise, self.gini, itemstr)
                )

    def __init__(self, session, m, doc, unrenumber):
        self.document = doc
        self.freq = m[0]
        # Unmap termids
        termids = m[1].split()
        termids = map(int, termids)
        if unrenumber:
            doc = StringDocument([termids])
            doc2 = unrenumber.process_document(session, doc)
            termids = doc2.get_raw(session)[0]
        termids.sort()
        self.termids = termids
        self.termidFreqs = dict(zip(termids, [self.freq] * len(termids)))
        self.termidRules = dict(zip(termids, [1] * len(termids)))
        self.combinations = [termids]

    def merge(self, orule):
        self.combinations.extend(orule.combinations)
        for t in orule.termids:
            if self.termidRules.has_key(t):
                self.termidRules[t] += orule.termidRules[t]
            else:
                self.termidRules[t] = orule.termidRules[t]
                self.termids.append(t)


# XXX This whole setup is kinda kludgey, ya know? :(
# This should be a workflow somehow?

class MatchToObjectPreParser(PreParser):
    
    _possiblePaths = {
        'renumberPreParser': {
            'docs': ''
        },
        'recordStore': {
            'docs': ''
        },
        'index': {
            'docs': ''
        }
    }
    
    _possibleSettings = {
        'calcRuleLengths': {
            'docs': '',
            'type': int
        },
        'calcRankings': {
            'docs': '',
            'type': int
        },
        'sortBy': {
            'docs': '',
            'options': 'gini|entropy|ll|surprise|length|support|totalFreq'
        }
    }
    
    def __init__(self, session, config, parent):
        PreParser.__init__(self, session, config, parent)
        # need to know which unrenumber preParser to use
        self.unrenumber = self.get_path(session, 'unRenumberPreParser', None)
        self.recordStore = self.get_path(session, 'recordStore', None)
        self.calcRuleLengths = self.get_setting(session, 'calcRuleLengths', 0)
        self.index = self.get_path(session, 'index', None)
        self.calcRankings = self.get_setting(session, 'calcRankings', 0)
        self.sortBy = self.get_setting(session, 'sortBy', '')

        self.sortFuncs = {
            'll': lambda x: x.ll,
            'surprise': lambda x: x.surprise,
            'entropy': lambda x: x.entropy,
            'gini': lambda x: x.gini,
            'length': lambda x: len(x.termids),
            'support': lambda x: x.freq,
            'totalFreq': lambda x: sum(x.freqs)
        }

    def process_document(self, session, doc):
        # Take in Doc with match list, return doc with rule object list
        (matches, armrules) = doc.get_raw(session)
        out = StringDocument([])
        # Initial setup
        termHash = {}
        termFreqHash = {}
        termRuleFreq = {}
        rules = []
        ruleLengths = {}

        if self.recordStore:
            totalDocs = self.recordStore.get_dbSize(session)
        else:
            # get default from session's database
            db = session.server.get_object(session, session.database)
            recStore = db.get_path(session, 'recordStore', None)
            if recStore:
                totalDocs = recStore.get_dbSize(session)
        if totalDocs == 0:
            # avoid e_divzero
            totalDocs = 1
        totalDocs = float(totalDocs)

        # step through rules and turn into objects, do math, do global stats
        for m in matches:
            r = FrequentSet(session, m, out, self.unrenumber)
            
            freqs = []
            for t in r.termids:
                try:
                    termFreq = termFreqHash[t]
                    termRuleFreq[t] += 1
                except:
                    termRuleFreq[t] = 1
                    term = self.index.fetch_termById(session, t)
                    termHash[t] = term
                    termFreq = self.index.fetch_term(session,
                                                     term,
                                                     summary=True)[1]
                    termFreqHash[t] = termFreq
                freqs.append(termFreq)
            r.freqs = freqs

            if self.calcRankings:
                if self.calcRuleLengths:
                    try:
                        ruleLengths[(len(r.termids))] += 1
                    except:
                        ruleLengths[(len(r.termids))] = 1

                # some basic stats needed
                avgs = []
                entropy = []
                gini = []
                ftd = float(totalDocs)
                for t in freqs:
                    bit = float(t) / ftd
                    avgs.append(bit)
                    entropy.append((0 - bit) * math.log(bit, 2))
                    gini.append(bit ** 2)

                r.pctg = reduce(operator.mul, avgs)
                r.avg = r.pctg * float(totalDocs)
                r.opctg = (float(r.freq) / ftd)
                r.entropy = reduce(operator.add, entropy)
                r.gini = 1.0 - reduce(operator.add, gini)

                # This is log-likelihood. Better than just support
                ei = float(totalDocs * (r.avg + r.freq)) / (totalDocs * 2.0)
                g2 = (
                    2 *
                    (
                        (r.avg * math.log(r.avg / ei, 10)) +
                        (r.freq * math.log(r.freq / ei, 10))
                    )
                )
                if r.freq < r.avg:
                    g2 = 0 - g2
                r.ll = g2
                # Dunno what this is but it works quite well (for some things)
                r.surprise = (totalDocs / r.avg) * r.freq
                # r.surprise2 = (1.0/r.pctg) * r.freq
            rules.append(r)

        if self.sortBy:
            rules.sort(key=self.sortFuncs[self.sortBy], reverse=True)

        nrules = []
        if armrules:
            # unrenumber arm found rules
            # conf, supp, [antes], [concs]
            for r in armrules:
                d = StringDocument([r[2], r[3]])
                if self.unrenumber:
                    d = self.unrenumber.process_document(session, d)
                antes = []
                concs = []
                renmbrd = d.get_raw(session)
                for a in renmbrd[0]:
                    antes.append(termHash[a])
                for c in renmbrd[1]:
                    concs.append(termHash[c])
                nrules.append([r[0], r[1], antes, concs])

        out.text = [rules, nrules]
        out.termHash = termHash
        out.termRuleFreq = termRuleFreq
        out.ruleLengths = ruleLengths
        # XXX this is even nastier, but useful
        out.sortFuncs = self.sortFuncs

        return out


class ClassificationPreParser(PreParser):
    """ Parent for all C12n PreParsers """

    model = None
    predicting = 0

    _possiblePaths = {
        'modelPath': {
            'docs': "Path to where the model is (to be) stored"
        }
    }

    _possibleSettings = {
        'termOffset': {
            'docs': "",
            'type': int
        }
    }

    def __init__(self, session, config, parent):
        PreParser.__init__(self, session, config, parent)
        self.offset = self.get_setting(session, 'termOffset', 0)
        modelPath = self.get_path(session, 'modelPath', '')
        if not modelPath:
            raise ConfigFileException("Classification PreParser (%s) does not "
                                      "have a modelPath" % self.id)
        if (not os.path.isabs(modelPath)):
            dfp = self.get_path(session, 'defaultPath')
            modelPath = os.path.join(dfp, modelPath)
            self.paths['modelPath'] = modelPath
        if os.path.exists(modelPath):
            # load model
            self.load_model(session, modelPath)
        else:
            self.model = None

        self.renumber = {}
            
    def process_document(self, session, doc):
        if self.model is not None and self.predicting:
            # Predict
            return self.predict(session, doc)
        else:
            # Train
            return self.train(session, doc)

    def load_model(self, session, path):
        # Should set self.model to not None
        raise NotImplementedError

    def train(self, session, doc):
        # Should set self.model to new model, return doc
        raise NotImplementedError

    def predict(self, session, doc):
        # Use self.model to predict class and return annotated doc
        raise NotImplementedError

    def renumber_train(self, session, vectors):
        # Find max attr
        all = {}
        for v in vectors:
            all.update(v)
        keys = all.keys()
        keys.sort()
        maxattr = keys[-1]
        nattrs = len(keys)

        if nattrs < (maxattr / 2):
            # Remap vectors to reduced space
            renumbers = range(self.offset, nattrs + self.offset)
            renumberhash = dict(zip(keys, renumbers))
            newvectors = []
            for vec in vectors:
                new = {}
                for (k, v) in vec.items():
                    new[renumberhash[k]] = v
                newvectors.append(new)
            # need this to map for future docs!
            self.renumber = renumberhash
        else:
            newvectors = vectors

        # pickle renumberhash
        pick = pickle.dumps(renumberhash)
        f = file(self.get_path(session, 'modelPath') + "_ATTRHASH.pickle", 'w')
        f.write(pick)
        f.close()
        return (nattrs, newvectors)

    def renumber_test(self, vector):
        if self.renumber:
            new = {}
            for (a, b) in vector.items():
                try:
                    new[self.renumber[a]] = b
                except:
                    # token not present in training, ignore
                    pass
            return new
        else:
            return vector

try:
    import svm
except ImportError:
    pass
else:
    class LibSVMPreParser(ClassificationPreParser):
    
        _possibleSettings = {
            'c-param': {
                'docs': "Parameter for SVM",
                'type': int
            },
            'gamma-param': {
                'docs': "Parameter for SVM",
                'type': float
            },
            'degree-param': {
                'docs': "Parameter for SVM",
                'type': int
            },
            'cache_size-param': {
                'docs': "Parameter for SVM",
                'type': int
            },
            'shrinking-param': {
                'docs': "Parameter for SVM",
                'type': int
            },
            'probability-param': {
                'docs': "Parameter for SVM",
                'type': int
            },
            'nu-param': {
                'docs': "Parameter for SVM",
                'type': float
            },
            'p-param': {
                'docs': "Parameter for SVM",
                'type': float
            },
            'eps-param': {
                'docs': "Parameter for SVM",
                'type': float
            },
            'svm_type-param': {
                'docs': "Parameter for SVM"
            },
            'kernel_type-param': {
                'docs': "Parameter for SVM"
            }
        }
    
        def __init__(self, session, config, parent):
            ClassificationPreParser.__init__(self, session, config, parent)
            c = self.get_setting(session, 'c-param', 32)
            g = self.get_setting(session, 'gamma-param', 0.00022)
            # XXX check for other params
            self.param = svm.svm_parameter(C=c, gamma=g)
    
        def _verifySetting(self, type, value):
            # svm_type, kernel_type, degree, gamma, coef0, nu, cache_size,
            # C, eps, p, shrinking, nr_weight, weight_label, and weight.
    
            if type in ('svm_type-param', 'kernel_type-param'):
                name = value.toupper()
                if hasattr(svm, name):
                    return getattr(svm, name)
                else:
                    raise ConfigFileException("No such %s '%s' for object "
                                              "%s" % (type, value, self.id))
            else:
                return ClassificationPreParser._verifySetting(self,
                                                              type,
                                                              value)
    
        def load_model(self, session, path):
            try:
                self.model = svm.svm_model(path.encode('utf-8'))
                self.predicting = 1
            except:
                raise ConfigFileException(path)
    
        def train(self, session, doc):
            # doc here is [[class, ...], [{vector}, ...]]
            (labels, vectors) = doc.get_raw(session)
            problem = svm.svm_problem(labels, vectors)
            self.model = svm.svm_model(problem, self.param)
            modelPath = self.get_path(session, 'modelPath')
            self.model.save(str(modelPath))
            self.predicting = 1
    
        def predict(self, session, doc):
            # doc here is {vector}
            vector = doc.get_raw(session)
            doc.predicted_class = int(self.model.predict(vector))
            return doc


try:
    from reverend import thomas
except ImportError:
    
    class ReverendPreParser(ClassificationPreParser):
    
        def __init__(self, session, config, parent):
            ClassificationPreParser.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType, "reverend")
    
else:
    
    class ReverendPreParser(ClassificationPreParser):
    
        def __init__(self, session, config, parent):
            ClassificationPreParser.__init__(self, session, config, parent)
            # create empty model
            self.model = thomas.Bayes()
    
        def load_model(self, session, path):
            try:
                self.model.load(str(path))
                self.predicting = 1
            except:
                raise ConfigFileException(path)
    
        def train(self, session, doc):
            (labels, vectors) = doc.get_raw(session)
            for (l, v) in zip(labels, vectors):
                vstr = ' '.join(map(str, v.keys()))
                self.model.train(l, vstr)
            self.model.save(str(self.get_setting(session, 'modelPath')))
            self.predicting = 1
    
        def predict(self, session, doc):
            v = ' '.join(map(str, doc.get_raw(session).keys()))
            probs = self.model.guess(v)
            doc.predicted_class = probs[0][0]
            doc.probabilities = probs
            return doc


try:
    from bpnn import NN
except ImportError:

    class BpnnPreParser(ClassificationPreParser):
        
        def __init__(self, session, config, parent):
            ClassificationPreParser.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType, "bpnn")

else:

    class BpnnPreParser(ClassificationPreParser):
    
        _possibleSettings = {
            'iterations': {'docs': "Number of iterations", 'type': int},
            'hidden-nodes': {'docs': "Number of hidden nodes", 'type': int},
            'learning-param': {'docs': "NN param", 'type': float},
            'momentum-param': {'docs': "NN param", 'type': float}
        }

        def __init__(self, session, config, parent):
            ClassificationPreParser.__init__(self, session, config, parent)
            # now get bpnn variables
            self.iterations = int(self.get_setting(session, 'iterations', 500))
            self.hidden = int(self.get_setting(session, 'hidden-nodes', 5))
            self.learning = float(self.get_setting(session,
                                                   'learning-param',
                                                   0.5))
            self.momentum = float(self.get_setting(session,
                                                   'momentum-param',
                                                   0.1))

        def load_model(self, session, path):
            # Load from pickled NN
            self.model = pickle.load(path)

        def train(self, session, doc):
            # Modified bpnn to accept dict as sparse input
            (labels, vectors) = doc.get_raw(session)
            (nattrs, vectors) = self.renumber_train(session, vectors)
            labelSet = set(labels)
            lls = len(labelSet)
            if lls == 2:
                patts = [(vectors[x], [labels[x]])
                         for x
                         in xrange(len(labels))
                         ]
                noutput = 1
            else:
                if lls < 5:
                    templ = ((0, 0),
                             (1, 0),
                             (0, 1),
                             (1, 1))
                elif lls < 9:
                    templ = ((0, 0, 0),
                             (1, 0, 0),
                             (0, 1, 0),
                             (1, 1, 0),
                             (0, 0, 1),
                             (1, 0, 1),
                             (0, 1, 1),
                             (1, 1, 1))
                else:
                    # Hopefully not more than 16 classes!
                    templ = ((0, 0, 0, 0),
                             (1, 0, 0, 0),
                             (0, 1, 0, 0),
                             (1, 1, 0, 0),
                             (0, 0, 1, 0),
                             (1, 0, 1, 0),
                             (0, 1, 1, 0),
                             (1, 1, 1, 0),
                             (0, 0, 0, 1),
                             (1, 0, 0, 1),
                             (0, 1, 0, 1),
                             (1, 1, 0, 1),
                             (0, 0, 1, 1),
                             (1, 0, 1, 1),
                             (0, 1, 1, 1),
                             (1, 1, 1, 1))
                rll = range(len(labels))
                patts = [(vectors[x], templ[labels[x]]) for x in rll]
                noutput = len(templ[0])
                
            # Shuffle to ensure not all of class together
            r = random.Random()
            r.shuffle(patts)
    
            # Only way this is at all usable is with small datasets run in
            # psyco but is at least fun to play with...
            if maxattr * len(labels) > 2000000:
                print "Training NN is going to take a LONG time..."
                print "Make sure you have psyco enabled..."
    
            n = NN(maxattr, self.hidden, noutput)
            self.model = n
            n.train(patts, self.iterations, self.learning, self.momentum)
    
            modStr = pickle.dumps(n)
            f = file(mp, 'w')
            f.write(modStr)
            f.close()
            self.predicting = 1
    
        def predict(self, session, doc):
            invec = doc.get_raw(session)
            vec = self.renumber_test(invec)
            resp = self.model.update(vec)
            # this is the outputs from each output node
            print resp


class PerceptronPreParser(ClassificationPreParser):
    """Quick implementation of perceptron using numarray
    
    DEPRECATED -- no longer distribute numarray
    """
    
    def load_model(self, session, path):
        self.model = na.fromfile(path)

    def train(self, session, doc):
        # modified bpnn to accept dict as sparse input
        (labels, vectors) = doc.get_raw(session)
        (nattrs, vectors) = self.renumber_train(session, vectors)

        labelSet = set(labels)
        lls = len(labelSet)
        if lls != 2:
            raise ValueError("Perceptron can only do two classes")
        else:
            patts = [(vectors[x], [labels[x]]) for x in xrange(len(labels))]
        r = random.Random()

        # Assume that dataset is too large to fit in memory non-sparse
        # numarray makes this very easy... and *fast*

        weights = na.zeros(nattrs + 1)
        iterations = 100
        it = 0
        for i in xrange(iterations):
            it += 1
            r.shuffle(patts)
            wrong = 0
            for (vec, cls) in patts:
                va = na.zeros(nattrs + 1)
                for (a, b) in vec.items():
                    va[a] = b
                va[-1] = 1  # Bias
                bits = weights * va
                total = bits.sum()
                cls = cls[0]
                if total >= 0 and cls == 0:
                    weights = weights - va
                    wrong = 1
                elif total < 0 and cls == 1:
                    weights = weights + va
                    wrong = 1
            if not wrong:
                # Reached perfection
                break
        self.model = weights
        # save model
        weights.tofile(self.get_path(session, 'modelPath'))
        self.predicting = 1

    def predict(self, session, doc):
        invec = doc.get_raw(session)
        vec = self.renumber_test(invec)
        va = na.zeros(len(self.model))
        for (a, b) in vec.items():
            va[a] = b
        va[-1] = 1  # bias
        bits = self.model * va
        total = bits.sum()

        pred = int(total >= 0)
        doc.predicted_class = pred
        return doc


class CarmPreParser(ClassificationPreParser):
    # Call Frans's code and read back results
    pass
