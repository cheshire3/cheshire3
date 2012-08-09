
from cheshire3.tokenMerger import SimpleTokenMerger

class PosPhraseTokenMerger(SimpleTokenMerger):

    _possibleSettings = {'nonPhrases' : {'docs' : '', 'type' : int, 'options' : '0|1'}}

    def __init__(self, session, config, parent):
        SimpleTokenMerger.__init__(self, session, config, parent)
        self.nonPhrases = self.get_setting(session, 'nonPhrases', 0)
        self.nounRequired = self.get_setting(session, 'nounRequired', 0)
        # self.keepPos = self.get_setting(session, 'keepPos', 0)

    def process_hash(self, session, data):
        new = {}
        has = new.has_key
        all = self.nonPhrases
        noun = self.nounRequired
        for d, val in data.iteritems():
            if d:
                x = 0
                posns = val.get('charOffsets', [])
                acc = []
                hasNoun = 0
                lvt = len(val['text']) -1
                for (vt, t) in enumerate(val['text']):
                    try:
                        (wd, pos) = t.split('/')
                    except:
                        print t
                        (wd, pos) = t.rsplit('/', 1)
                    pos = pos.lower()
                    if vt != lvt and ( pos.startswith('jj') or pos.startswith('nn')):   
                        # XXX should split jj nn jj nn into two
                        if pos.startswith('nn'):
                            hasNoun = 1
                        acc.append(wd)
                        continue
                    elif acc:
                        # merge wds
                        if (pos.startswith('jj') or pos.startswith('nn')):
                            if pos.startswith('nn'):
                                hasNoun = 1
                            acc.append(wd)
                            skipall = 1
                        else:
                            skipall = 0
                        if noun and not hasNoun:
                            wds = acc[:]
                        else:
                            wds = [' '.join(acc)]
                        if all and not skipall:
                            wds.append(wd)
                        acc = []
                        hasNoun = 0
                    elif all:
                        wds = [wd]
                    else:
                        continue
                    for w in wds:
                        if has(w):
                            new[w]['occurences'] += val['occurences']
                        else:
                            new[w] = {'text' : w, 'occurences' : val['occurences'], 'positions' : []}
                        try:
                            pls =[(pl,x, posns[x]) for pl in val['proxLoc']]
                            for p in pls:
                                new[w]['positions'].extend(p)
                        except KeyError:
                            new[w]['positions'].extend(val['positions'])
                        x += 1
        return new

        
    
