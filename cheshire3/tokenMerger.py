
import os
try:
    import cPickle as pickle
except ImportError:
    import pickle
    

from cheshire3.baseObjects import TokenMerger
from cheshire3.exceptions import ConfigFileException, FileDoesNotExistException


class SimpleTokenMerger(TokenMerger):

    def process_string(self, session, data):
        return data

    def process_hash(self, session, data):
        new = {}
        for d, val in data.iteritems():
            if d:
                for t in val['text']:
                    if t in new:
                        new[t]['occurences'] += val['occurences']
                    else:
                        # This will discard any second or further locations
                        # -very- minor edge case when this will break things
                        # If important, use ProximityTokenMerger.
                        try:
                            new[t] = {
                                'text': t,
                                'occurences': val['occurences'],
                                'proxLoc': val['proxLoc']
                            }
                        except KeyError:
                            # May already have been tokenized and merged
                            new[t] = {
                                'text': t,
                                'occurences': val['occurences'],
                                'positions': val['positions']
                            }            
        return new


class ProximityTokenMerger(SimpleTokenMerger):

    def process_hash(self, session, data):
        new = {}
        for d, val in data.iteritems():
            if d:
                x = 0
                for t in val['text']:
                    if t in new:
                        new[t]['occurences'] += val['occurences']
                        try:
                            pls = [(pl, x) for pl in val['proxLoc']]
                            for p in pls:
                                new[t]['positions'].extend(p)
                        except KeyError:
                            new[t]['positions'].extend(val['positions'])
                    else:
                        try:
                            pls = [(pl, x) for pl in val['proxLoc']]
                            new[t] = {
                                'text': t,
                                'occurences': len(pls),
                                'positions': []
                            }
                            for p in pls:
                                new[t]['positions'].extend(p)
                        except KeyError:
                            new[t] = {
                                'text': t,
                                'occurences': val['occurences'],
                                'positions': val['positions'][:]
                            }
                    x += 1
        return new


class OffsetProximityTokenMerger(ProximityTokenMerger):

    def process_hash(self, session, data):
        new = {}
        for d, val in data.iteritems():
            if d:
                x = 0
                posns = val.get('charOffsets', [])
                for t in val['text']:
                    try:
                        wordOffs = val['wordOffs']
                    except:
                        wordOffs = []
                    
                    if t in new:
                        new[t]['occurences'] += val['occurences']
                    else:
                        new[t] = {
                            'text': t,
                            'occurences': val['occurences'],
                            'positions': []
                        }
                    try:
                        if len(wordOffs):
                            pls = [(pl, wordOffs[x], posns[x])
                                  for pl in val['proxLoc']
                                  ]
                        else:
                            pls = [(pl, x, posns[x]) for pl in val['proxLoc']]
                        for p in pls:
                            new[t]['positions'].extend(p)
                    except KeyError:
                        new[t]['positions'].extend(val['positions'])
                    x += 1
        return new
        
        
class RangeTokenMerger(SimpleTokenMerger):
    
    _possibleSettings = {
        'char': {
            'docs': ('Character to use as the interval designator. Defaults '
                     'to forward slash (/) after ISO 8601.'),
            'type': str
        }
    }
    
    def __init__(self, session, config, parent):
        SimpleTokenMerger.__init__(self, session, config, parent)
        self.char = self.get_setting(session, 'char', '/')


class SequenceRangeTokenMerger(RangeTokenMerger):
    """Merges tokens into a range for use in RangeIndexes.
    
    Assumes that we've tokenized a single value into pairs,
    which need to be concatenated into ranges.
    """
    
    def process_hash(self, session, data):
        new = {}
        for d, val in data.iteritems():
            l = val['text']
            for x in range(0, len(l), 2):
                try:
                    newkey = "{0}{1}{2}".format(l[x], self.char, l[x + 1])
                except IndexError:
                    # Uneven number of points :/
                    newkey = "{0}{1}{0}".format(l[x], self.char)
                if newkey in new:
                    new[newkey]['occurences'] += 1
                else:
                    nval = val.copy()
                    nval['text'] = newkey                
                    new[newkey] = nval
        return new


class MinMaxRangeTokenMerger(RangeTokenMerger):
    """Merges tokens into a range for use in RangeIndexes.
    
    Uses a forward slash (/) as the interval designator after ISO 8601.
    """
    
    def process_hash(self, session, data):
        keys = data.keys()
        if (not len(keys)):
            return {}
        startK = str(min(keys))
        endK = str(max(keys))
        newK = '{0}{1}{2}'.format(startK, self.char, endK)
        val = data[startK]
        val['text'] = newK
        return {newK: val}


class NGramTokenMerger(SimpleTokenMerger):

    _possibleSettings = {
        'nValue': {
            'docs': '',
            'type': int
        }
    }

    def __init__(self, session, config, parent):
        SimpleTokenMerger.__init__(self, session, config, parent)
        self.n = self.get_setting(session, 'nValue', 2)
               
    def process_hash(self, session, data):
        kw = {}
        n = self.n
        for k, val in data.iteritems():
            split = val['text']
            for i in range(len(split) - (n - 1)):
                nGram = split[i:(i + n)]
                nGramStr = ' '.join(nGram)
                if nGramStr in kw:
                    kw[nGramStr]['occurences'] += val['occurences']
                else:
                    kw[nGramStr] = {
                        'text': nGramStr,
                        'occurences': val['occurences']
                    }
        return kw


class ReconstructTokenMerger(SimpleTokenMerger):

    def process_hash(self, session, data):
        kw = {}
        for (k, val) in data.iteritems():
            pl = 'charOffsets' in val
            # FIXME: XXX for faked offsets 
            pl = 0
            currLen = 0
            new = []
            for (w, word) in enumerate(val['text']):
                if pl:
                    space = ' ' * (val['charOffsets'][w] - currLen)
                    new.append('%s%s' % (space, word))
                    currLen = val['charOffsets'][w] + len(word)
                else:
                    new.append('%s' % (word))
                    if w < len(val['text']) - 1:
                        new.append(' ')
            txt = ''.join(new)
            kval = val.copy()
            kval['text'] = txt
            kw[k] = kval
        return kw


class PhraseTokenMerger(ProximityTokenMerger):

    _possiblePaths = {
        'mergeHashPickle': {
            'docs': 'Pickled hash of words to merge'
        }
    }

    def __init__(self, session, config, parent):
        ProximityTokenMerger.__init__(self, session, config, parent)
        mp = self.get_path(session, 'mergeHashPickle', '')
        if not mp:
            msg = "%s needs path: mergeHashPickle" % self.id
            raise ConfigFileException(msg)
        elif not os.path.exists(mp):
            msg = " mergeHashPickle path on %s does not exist" % self.id
            raise FileDoesNotExistException(msg)
            
        inh = file(mp)
        data = inh.read()
        inh.close()
        self.mergeHash = pickle.loads(data)

    def process_hash(self, session, data):
        new = {}
        for d, val in data.iteritems():
            if d:
                x = 0
                merging = []
                for t in val['text']:
                    # Check if t in self.mergeHash
                    if self.mergeHash.has_key(t) and len(val['text']) > x + 1:
                        nexts = self.mergeHash[t]
                        next = val['text'][x + 1]
                        if next in nexts:
                            merging.append(t)
                            continue
                    elif merging:
                        merging.append(t)
                        t = "_".join(merging)
                        merging = []

                    if t in new:
                        new[t]['occurences'] += val['occurences']
                        try:
                            pls = [(pl, x) for pl in val['proxLoc']]
                            for p in pls:
                                new[t]['positions'].extend(p)
                        except KeyError:
                            new[t]['positions'].extend(val['positions'])
                    else:
                        try:
                            pls = [(pl, x) for pl in val['proxLoc']]
                            new[t] = {
                                'text': t,
                                'occurences': len(pls),
                                'positions': []
                            }
                            for p in pls:
                                new[t]['positions'].extend(p)
                        except KeyError:
                            new[t] = {
                                'text': t,
                                'occurences': val['occurences'],
                                'positions': val['positions'][:]
                            }
                    x += 1
        return new
