
from baseObjects import TokenMerge

class SimpleTokenMerge(TokenMerge):

    def process_string(self, session, data):
        return data

    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        for (d, val) in data.items():
            if d:
                for t in val['text']:
                    if has(t):
                        new[t]['occurences'] += 1
                    else:
                        # this will discard any second or further locations
                        # -very- minor edge case when this will break things
                        # if important, use ProximityTokenMerge.
                        try:
                            new[t] = {'text' : t, 'occurences' : 1,
                                      'proxLoc' : val['proxLoc']}
                        except KeyError:
                            # may already have been tokenized and merged
                            new[t] = {'text' : t, 'occureces' : 1,
                                      'positions' : val['positions']}
                        
        return new

class ProximityTokenMerge(SimpleTokenMerge):
    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        for (d, val) in data.items():
            if d:
                x = 0
                for t in val['text']:
                    if has(t):
                        new[t]['occurences'] += 1
                        try:
                            new[t]['positions'].extend((val['proxLoc'], x))
                        except KeyError:
                            new[t]['positions'].extend(val['positions'])
                    else:
                        try:
                            new[t] = {'text' : t, 'occurences' : 1, 'positions' : [val['proxLoc'],x]}
                        except KeyError:
                            new[t] = {'text' : t, 'occurences' : 1,
                                      'positions' : val['positions']}
                    x += 1
        return new

class OffsetProximityTokenMerge(ProximityTokenMerge):
    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        for (d, val) in data.items():
            if d:
                x = 0
                posns = val.get('charOffsets', [])
                for t in val['text']:
                    if has(t):
                        new[t]['occurences'] += 1
                        new[t]['positions'].extend((val['proxLoc'], x, posns[x]))
                    else:
                        new[t] = {'text' : t, 'occurences' : 1, 'positions' : [val['proxLoc'],x, posns[x]]}
                    x += 1
        return new
    
    

class SequenceRangeTokenMerge(SimpleTokenMerge):
    # assume that we've tokenized a single value into pairs,
    #   which need to be concatenated into ranges.

    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        for (d, val) in data.items():
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


class MinMaxRangeTokenMerge(SimpleTokenMerge):
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
               
class NGramTokenMerge(SimpleTokenMerge):

    _possibleSettings = {'nValue' : {'docs' : '', 'type' : int}}

    def __init__(self, session, config, parent):
        SimpleTokenMerge.__init__(self, session, config, parent)
        self.n = self.get_setting(session, 'nValue', 2)
               
    def process_hash(self, session, data):
        kw = {}
        has = kw.has_key
        n = self.n
        for (k, val) in data.items():
            split = val['text']
            for i in range(len(split)-(n-1)):
                nGram = split[i:(i+n)]
                nGramStr = ' '.join(nGram)
                if has(nGramStr):
                    kw[nGramStr]['occurences'] += 1
                else:
                    kw[nGramStr] = {'text' : nGramStr, 'occurences' : 1}
        return kw


