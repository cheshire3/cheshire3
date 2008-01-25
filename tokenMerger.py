
from baseObjects import TokenMerger

class SimpleTokenMerger(TokenMerger):

    def process_string(self, session, data):
        return data

    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        for d, val in data.iteritems():
            if d:
                for t in val['text']:
                    if has(t):
                        new[t]['occurences'] += 1
                    else:
                        # this will discard any second or further locations
                        # -very- minor edge case when this will break things
                        # if important, use ProximityTokenMerger.
                        try:
                            new[t] = {'text' : t, 'occurences' : 1,
                                      'proxLoc' : val['proxLoc']}
                        except KeyError:
                            # may already have been tokenized and merged
                            new[t] = {'text' : t, 'occureces' : 1,
                                      'positions' : val['positions']}
                        
        return new

class ProximityTokenMerger(SimpleTokenMerger):
    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        for d, val in data.iteritems():
            if d:
                x = 0
                for t in val['text']:
                    if has(t):
                        new[t]['occurences'] += val['occurences']
                        try:
                            pls = [(pl,x) for pl in val['proxLoc']]
                            for p in pls:
                                new[t]['positions'].extend(p)
                        except KeyError:
                            new[t]['positions'].extend(val['positions'])
                    else:
                        try:
                            pls = [(pl,x) for pl in val['proxLoc']]
                            new[t] = {'text' : t, 'occurences' : len(pls), 'positions' : []}
                            for p in pls:
                                new[t]['positions'].extend(p)
                        except KeyError:
                            new[t] = {'text' : t, 'occurences' : val['occurences'],
                                      'positions' : val['positions'][:]}
                    x += 1
        return new

class OffsetProximityTokenMerger(ProximityTokenMerger):
    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        for d, val in data.iteritems():
            if d:
                x = 0
                posns = val.get('charOffsets', [])
                for t in val['text']:
                    if has(t):
                        new[t]['occurences'] += val['occurences']
                    else:
                        new[t] = {'text' : t, 'occurences' : val['occurences'], 'positions' : []}
                    try:
                        pls =[(pl,x, posns[x]) for pl in val['proxLoc']]
                        for p in pls:
                            new[t]['positions'].extend(p)
                    except KeyError:
                        new[t]['positions'].extend(val['positions'])
                    x += 1
        return new
        
##class PositionTokenMerger(ProximityTokenMerger):
##    def process_hash(self, session, data):
##        new = {}
##        has = new.has_key
##        for d, val in data.iteritems():
##            if d:
##                x = 0
##                for t in val['text']:
##                    if has(t):
##                        new[t]['occurences'] += 1
##                        try:
##                            new[t]['positions'].extend((val['proxLoc'], x))
##                        except KeyError:
##                            new[t]['positions'].extend(val['positions'])
##                    else:
##                        try:
##                            new[t] = {'text' : t, 'occurences' : 1, 'positions' : [val['proxLoc'],x]}
##                        except KeyError:
##                            new[t] = {'text' : t, 'occurences' : 1,
##                                      'positions' : val['positions']}
##                    x += 1
##        return new
    


class SequenceRangeTokenMerger(SimpleTokenMerger):
    # assume that we've tokenized a single value into pairs,
    #   which need to be concatenated into ranges.

    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        for d, val in data.iteritems():
            l = val['text']
            for x in range(0, len(l), 2):
                try:
                    newkey = "%s\t%s" % (l[x], l[x+1])
                except IndexError:
                    newkey = "%s\t " % (l[x])
                if has(newkey):
                    new[newkey]['occurences'] += 1
                else:
                    nval = val.copy()
                    nval['text'] = newkey                
                    new[newkey] = nval
        return new


class MinMaxRangeTokenMerger(SimpleTokenMerger):
    """ Extracts a range for use in RangeIndexes """
    
    def process_hash(self, session, data):
        # TODO: decide whether to accept more/less than 2 terms
        # e.g. a b c --> a c OR a b OR a b, b c 
        # John implements 1st option...
        keys = data.keys()
        if (not len(keys)):
            return {}
        
        startK = str(min(keys))
        endK = str(max(keys))
        newK = '%s\t%s' % (startK, endK)
        val = data[startK]
        val['text'] = newK
        return {
                newK: val
                }
               
class NGramTokenMerger(SimpleTokenMerger):

    _possibleSettings = {'nValue' : {'docs' : '', 'type' : int}}

    def __init__(self, session, config, parent):
        SimpleTokenMerger.__init__(self, session, config, parent)
        self.n = self.get_setting(session, 'nValue', 2)
               
    def process_hash(self, session, data):
        kw = {}
        has = kw.has_key
        n = self.n
        for k, val in data.iteritems():
            split = val['text']
            for i in range(len(split)-(n-1)):
                nGram = split[i:(i+n)]
                nGramStr = ' '.join(nGram)
                if has(nGramStr):
                    kw[nGramStr]['occurences'] += 1
                else:
                    kw[nGramStr] = {'text' : nGramStr, 'occurences' : 1}
        return kw

class ReconstructTokenMerger(SimpleTokenMerger):

    def process_hash(self, session, data):
        kw = {}
        for (k, val) in data.iteritems():
            pl = val.has_key('charOffsets')
            # XXX FIX ME for faked offsets
            pl = 0
            currLen = 0
            new = []
            for (w, word) in enumerate(val['text']):
                if pl:
                    new.append('%s%s' % (' ' * (val['charOffsets'][w] - currLen), word))
                    currLen = val['charOffsets'][w] + len(word)
                else:
                    new.append('%s ' % (word))
            txt = ''.join(new)
            kval = val.copy()
            kval['text'] = txt
            kw[k] = kval
        return kw
