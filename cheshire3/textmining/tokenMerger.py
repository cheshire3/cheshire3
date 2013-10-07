"""Cheshire3 Textmining TokenMerger Implementations."""

import nltk

from cheshire3.exceptions import ConfigFileException
from cheshire3.tokenMerger import SimpleTokenMerger


class PosPhraseTokenMerger(SimpleTokenMerger):

    _possibleSettings = {
        'nonPhrases': {
            'docs': '',
            'type': int,
            'options': '0|1'
        }
    }

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
                lvt = len(val['text']) - 1
                for (vt, t) in enumerate(val['text']):
                    try:
                        (wd, pos) = t.split('/')
                    except:
                        print t
                        (wd, pos) = t.rsplit('/', 1)
                    pos = pos.lower()
                    if (vt != lvt and
                        (pos.startswith('jj') or pos.startswith('nn'))
                        ):
                        # XXX should split jj nn jj nn into two
                        if pos.startswith('nn'):
                            hasNoun = 1
                        acc.append(wd)
                        continue
                    elif acc:
                        # Merge wds
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
                            new[w] = {'text': w,
                                      'occurences': val['occurences'],
                                      'positions': []}
                        try:
                            pls = [(pl, x, posns[x]) for pl in val['proxLoc']]
                            for p in pls:
                                new[w]['positions'].extend(p)
                        except KeyError:
                            new[w]['positions'].extend(val['positions'])
                        x += 1
        return new


class NLTKNamedEntityTokenMerger(SimpleTokenMerger):

    _possibleSettings = {
        'entityTypes': {
            'docs': ("Space separated list of entity type to keep."
                     "Defaults to all types, i.e. "
                     "'People Places Organizations'")
        },
    }

    def __init__(self, session, node, parent):
        SimpleTokenMerger.__init__(self, session, node, parent)
        types = self.get_setting(session, 'entityTypes')
        if types:
            self.types = []
            for type_ in types.split():
                type_ = type_.lower()
                if type_.startswith('pe'):
                    self.types.append('PERSON')
                elif type_.startswith(('pl', 'g')):
                    self.types.append('GPE')
                elif type_.startswith(('org', 'co')):
                    self.types.append('ORGANIZATION')
                else:
                    msg = ("Unknown entity type setting {0} on {1} {2}"
                           "".format(type_,
                                     self.__class__.__name__,
                                     self.id)
                           )
                    raise ConfigFileException(msg)
        else:
            # Default to all
            self.types = ['PERSON', 'GPE', 'ORGANIZATION']
        # Should we keep the /POS tag or strip it
        self.keepPos = self.get_setting(session, 'pos', 0)

    def process_hash(self, session, data):
        new = {}
        pos_tag = nltk.pos_tag
        ne_chunk = nltk.chunk.ne_chunk
        for d, val in data.iteritems():
            if d:
                tagged = pos_tag(val['text'])
                # Identify named entities
                entities = ne_chunk(tagged)
                for ent in entities:
                    if isinstance(ent, nltk.tree.Tree):
                        # Is it a wanted type?
                        if ent.node in self.types:
                            # Pull out the token value
                            txts = [token[0] for token in ent.leaves()]
                            for t in txts:
                                if t in new:
                                    new[t]['occurences'] += val['occurences']
                                else:
                                    # This will discard any second or further
                                    # locations -very- minor edge case when
                                    # this will break things. If important, use
                                    # ProximityTokenMerger.
                                    try:
                                        new[t] = {
                                            'text': t,
                                            'occurences': val['occurences'],
                                            'proxLoc': val['proxLoc']
                                        }
                                    except KeyError:
                                        # May already have been tokenized and
                                        # merged
                                        new[t] = {
                                            'text': t,
                                            'occurences': val['occurences'],
                                            'positions': val['positions']
                                        }
        return new


class ProximityNLTKNamedEntityTokenMerger(NLTKNamedEntityTokenMerger):

    def process_hash(self, session, data):
        new = {}
        pos_tag = nltk.pos_tag
        ne_chunk = nltk.chunk.ne_chunk
        for d, val in data.iteritems():
            if d:
                x = 0
                tagged = pos_tag(val['text'])
                # Identify named entities
                entities = ne_chunk(tagged)
                for ent in entities:
                    if not isinstance(ent, nltk.tree.Tree):
                        x += 1
                    else:
                        # Pull out the token value
                        txts = [token[0] for token in ent.leaves()]
                        # Is it a wanted type?
                        if ent.node not in self.types:
                            x += len(txts)
                        else:
                            for t in txts:
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


class OffsetProximityNLTKNamedEntityTokenMerger(
        ProximityNLTKNamedEntityTokenMerger
    ):

    def process_hash(self, session, data):
        new = {}
        pos_tag = nltk.pos_tag
        ne_chunk = nltk.chunk.ne_chunk
        for d, val in data.iteritems():
            if d:
                x = 0
                posns = val.get('charOffsets', [])
                tagged = pos_tag(val['text'])
                # Identify named entities
                entities = ne_chunk(tagged)
                for ent in entities:
                    if not isinstance(ent, nltk.tree.Tree):
                        x += 1
                    else:
                        # Pull out the token value
                        txts = [token[0] for token in ent.leaves()]
                        # Is it a wanted type?
                        if ent.node not in self.types:
                            x += len(txts)
                        else:
                            for t in txts:
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
                                        pls = [(pl, x, posns[x])
                                               for pl
                                               in val['proxLoc']
                                               ]
                                    for p in pls:
                                        new[t]['positions'].extend(p)
                                except KeyError:
                                    new[t]['positions'].extend(val['positions'])
                                x += 1
        return new
