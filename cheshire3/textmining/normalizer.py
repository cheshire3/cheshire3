
import os
import types
import re
import nltk

from cheshire3.configParser import C3Object
from cheshire3.exceptions import ConfigFileException
from cheshire3.normalizer import SimpleNormalizer
from cheshire3.textmining.TsujiiC3 import TsujiiObject, GeniaObject, EnjuObject


# Wordnet Normalizers
# Use our own hacked pyWordNet
try:
    from wn import wordnet, wntools
except ImportError:
    pass
else:

    class WordNetNormalizer(SimpleNormalizer):
        """Use Wordnet to expand terms."""

        _possibleSettings = {
            'prox': {
                'docs': "Should the normalizer maintain proximity information",
                'type': int,
                'options': "0|1"
            }
        }

        def process_string(self, session, data):
            # Assume that string is of the form word/POS if / in data
            # Then reduce and look up, otherwise look up in all
            try:
                (word, pos) = data.rsplit('/', 1)
            except:
                word = data
                pos = ""
            if pos:
                if pos[0] == "N":
                    # Noun
                    dbs = [wordnet.N]
                elif pos[0] == "V":
                    dbs = [wordnet.V]
                elif pos[0] == "J":
                    dbs = [wordnet.ADJ]
                elif pos == "RB":
                    dbs = [wordnet.ADV]
                else:
                    # can't process term
                    return None
            else:
                dbs = [wordnet.N, wordnet.V, wordnet.ADJ, wordnet.ADV]

            kw = {}
            has = kw.has_key
            for db in dbs:
                # We don't know which sense. Need WSD
                try:
                    senses = db[word]
                except KeyError:
                    continue
                for sense in senses:
                    for syn in sense.synset:
                        t = syn.form
                        if has(t):
                            kw[t]['occurences'] += 1
                        else:
                            kw[t] = {'text': t,
                                     'occurences': 1}
            return kw

        def process_hash(self, session, data):
            kw = {}
            vals = data.values()
            if not vals:
                return {}
            prox = ('positions' in vals[0] or
                    self.get_setting(session, 'prox'))
            pos = 'pos' in vals[0]
            process = self.process_string
            has = kw.has_key
            for d in vals:
                if pos:
                    d['text'] = "%s/%s" % (d['text'], d['pos'])
                new = process(session, d['text'])
                if type(new) == types.DictType:
                    # from string to hash
                    for k in new.values():
                        txt = k['text']
                        if has(txt):
                            kw[txt]['occurences'] += k['occurences']
                            if prox:
                                kw[txt]['positions'].extend(k['positions'])
                        else:
                            kw[txt] = k
                else:
                    if new is not None:
                        try:
                            kw[new]['occurences'] += d['occurences']
                            if prox:
                                kw[new]['positions'].extend(d['positions'])
                        except KeyError:
                            d = d.copy()
                            if prox:
                                d['positions'] = d['positions'][:]
                            d['text'] = new
                            kw[new] = d
            return kw

    class HypernymNormalizer(WordNetNormalizer):
        def process_string(self, session, data):
            try:
                (word, pos) = data.rsplit('/', 1)
            except:
                word = data
                pos = ""

            if pos:
                if pos[0] == "N":
                    # Noun
                    dbs = [wordnet.N]
                elif pos[0] == "V":
                    dbs = [wordnet.V]
                elif pos[0] == "J":
                    dbs = [wordnet.ADJ]
                elif pos == "RB":
                    dbs = [wordnet.ADV]
                else:
                    # can't process term
                    return None
            else:
                dbs = [wordnet.N, wordnet.V, wordnet.ADJ, wordnet.ADV]

            kw = {}
            has = kw.has_key

            for db in dbs:
                # We don't know which sense. Need WSD
                # grab all hypernyms for all senses
                try:
                    senses = db[word]
                except KeyError:
                    continue
                for sense in senses:
                    try:
                        hyps = wntools.closure(sense, wordnet.HYPERNYM)
                    except KeyError:
                        # something busted in pyWordNet :/
                        continue
                    for hyp in hyps[1:]:
                        for syn in hyp:
                            t = syn.getWord().form
                            if has(t):
                                kw[t]['occurences'] += 1
                            else:
                                kw[t] = {'text': t,
                                         'occurences': 1}
            return kw


class PosNormalizer(SimpleNormalizer):
    """ Base class for deriving Part of Speech Normalizers """
    pass


class TsujiiPosNormalizer(PosNormalizer, TsujiiObject):

    def __init__(self, session, node, parent):
        PosNormalizer.__init__(self, session, node, parent)
        TsujiiObject.__init__(self, session, node, parent)

    def process_string(self, session, data):
        tl = self.tag(session, data)
        return ' '.join(tl)


# XML output
class EnjuNormalizer(PosNormalizer, EnjuObject):
    def __init__(self, session, node, parent):
        PosNormalizer.__init__(self, session, node, parent)
        EnjuObject.__init__(self, session, node, parent)

    def process_string(self, session, data):
        tl = self.tag(session, data)
        return tl


# unparsed \t delimited, \n per word
class GeniaNormalizer(PosNormalizer, GeniaObject):
    def __init__(self, session, node, parent):
        PosNormalizer.__init__(self, session, node, parent)
        GeniaObject.__init__(self, session, node, parent)
        self.unparsedOutput = 1

    def process_string(self, session, data):
        tl = self.tag(session, data)
        return ''.join(tl)

    def process_hash(self, session, data):
        # If text is list of single words, concat with ' '
        # otherwise pass up
        for (k, v) in data.iteritems():
            if type(v['text']) == list and v['text'][0].find(' ') == -1:
                data[k]['text'] = ' '.join(v['text'])
        return PosNormalizer.process_hash(self, session, data)


class NLTKPosNormalizer(PosNormalizer):
    """Use NTLK to normalize tokens to parts of speech."""

    _possibleSettings = {
        'taggerClass': {
            'docs': ("Class of NLTK Tagger to use for PoS tagging. "
                     "If absent use NLTK's standard PoS tagger."),
            'type': str
        },
        'justPos': {
            "docs": ('Should the normalized value be just the PoS (0) '
                     'or the original token annotated with a PoS tag '
                     '(1 default)'),
            'type': int,
            'options': "0|1"
        }
    }

    def __init__(self, session, node, parent):
        PosNormalizer.__init__(self, session, node, parent)
        cls = self.get_setting(session, 'taggerClass', None)
        if cls is not None:
            try:
                taggerClass = getattr(nltk.tag, cls)
            except AttributeError as e:
                raise ConfigFileException("nltk.tag does not define class "
                                          "{0} as specified in 'taggerClass' "
                                          "setting for {1} object with id {2}"
                                          "".format(cls,
                                                    self.__class__.__name__,
                                                    self.id))
            else:
                self.tagger = taggerClass()
        else:
            # Use standard tagger
            try:
                self.tagger = nltk.tag.load(nltk.tag._POS_TAGGER)
            except LookupError:
                nltk.download('maxent_treebank_pos_tagger')
        self.justPos = self.get_setting(session, 'justPos', 0)

    def process_string(self, session, data):
        if isinstance(data, list):
            tagged = self.tagger.tag(data)
        else:
            # Not yet tokenized / single token
            # Tokenizing does no harm done if already tokenized
            # Sentence tokenize
            tagged = []
            for sent in nltk.tokenize.sent_tokenize(data):
                # Word tokenize
                tokens = nltk.tokenize.word_tokenize(sent)
                tagged.extend(self.tagger.tag(tokens))
        # Are tagged tokens wanted, or just the tags themselves?
        if self.justPos:
            tagged = [tup[1] for tup in tagged]
        else:
            tagged =  [nltk.tag.util.tuple2str(tup) for tup in tagged]
        # Outgoing should be same type as incoming, make it so
        if isinstance(data, list):
            return tagged
        else:
            return ' '.join(tagged)


class ReconstructGeniaNormalizer(SimpleNormalizer):
    """Reconstruct Document with stems and/or PoS tags.

    Take the unparsed output from Genia and reconstruct the document,
    maybe with stems ('useStem' setting) and/or PoS tags ('pos' setting).
    """

    _possibleSettings = {
        'useStem': {
            "docs": ("Should the text be reconstructed with the stem (1) or"
                     " not (0, default)"),
            'type': int,
            'options': "0|1"
        },
        'pos': {
            "docs": 'Should the text include the PoS tag?',
            'type': int,
            'options': "0|1"
        },
        'justPos': {
            "docs": 'Should the text be JUST the PoS tag?',
            'type': int,
            'options': "0|1"
        },
        'xml': {
            'docs': 'Output the results as XML.',
            'type': int,
            'options': '0|1'
        }
    }

    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        self.stem = self.get_setting(session, 'useStem', 0)
        self.pos = self.get_setting(session, 'pos', 0)
        self.onlyPos = self.get_setting(session, 'justPos', 0)
        self.puncRe = re.compile('[ ]([.,;:?!][ \n])')
        self.xml = self.get_setting(session, 'xml', 0)

    def process_string(self, session, data):
        # not worth a tokenizer just to split lines!
        lines = data.split('\n')
        words = []
        for l in lines:
                try:
                    (word, stem, pos, phr, rest) = l.split('\t', 4)
                except ValueError:
                    # empty line
                    words.append(l)
                    continue
                if self.onlyPos:
                    w = pos
                elif self.xml:
                    if stem == word:
                        w = '<w p="{0}" t="{1}">{2}</w>'.format(pos, phr, word)
                    else:
                        w = '<w p="{0}" l="{1}" t="{2}">{3}</w>'.format(pos,
                                                                        stem,
                                                                        phr,
                                                                        word)
                else:
                    if self.stem:
                        w = stem
                    else:
                        w = word
                    if self.pos:
                        w = "%s/%s" % (w, pos)
                words.append(w)
        txt = ' '.join(words)
        txt = self.puncRe.sub('\\1', txt)
        return txt


class StemGeniaNormalizer(SimpleNormalizer):
    """Take output from HashGeniaNormalizer and return stems as terms."""
    def process_hash(self, session, data):
        results = {}
        for d in data.itervalues():
            try:
                results[d['stem']]['occurences'] += d['occurences']
            except:
                results[d['stem']] = {'text': d['stem'],
                                      'occurences': 1}
        return results


class PosPhraseNormalizer(SimpleNormalizer):
    """Extract statistical multi-word noun phrases from full pos tagged text.

    Default phrase is one or more nouns preceded by zero or more adjectives.
    Don't tokenize first.
    """

    _possibleSettings = {
        'regexp': {
            'docs': 'Regular expression to match phrases'
        },
        'pattern': {
            'docs': ('Pattern to match phrases. Possible components: '
                    ' JJ NN * + ?')
        },
        'minimumWords': {
            'docs': "Minimum number of words that constitute a phrase.",
            'type': int,
            'options': "0|1|2|3|4|5"
        },
        'subPhrases': {
            'docs': "Extract all sub-phrases (1) or not (0, default)",
            'type': int,
            'options': "0|1"
        }
    }

    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        match = self.get_setting(session, 'regexp', '')
        if not match:
            match = self.get_setting(session, 'pattern')
            if not match:
                match = "((?:[ ][^\\s]+/JJ[SR]?)*)((?:[ ][^\\s]+/NN[SP]?)+)"
            else:
                match = match.replace('*', '*)')
                match = match.replace('+', '+)')
                match = match.replace('?', '?)')
                match = match.replace('JJ', '((?:[ ][^\\s]+/JJ[SR]?)')
                match = match.replace('NN', '((?:[ ][^\\s]+/NN[SP]*)')
        self.pattern = re.compile(match)
        self.strip = re.compile('/(JJ[SR]?|NN[SP]*)|/(jj[sr]?|nn[sp]*)')
        self.minimum = self.get_setting(session, 'minimumWords', 0)
        self.subPhrases = self.get_setting(session, 'subPhrases', 0)

    def process_string(self, session, data):
        # input is tagged string, pre keywording
        # output: hash of phrases
        kw = {}
        has = kw.has_key
        strp = self.strip.sub
        minm = self.minimum

        matches = self.pattern.findall(data)
        for phrase in matches:
            phrases = []
            if type(phrase) == tuple:
                phrase = ' '.join(phrase)
            phrase = phrase.strip()
            # Strip tags
            # XXX Can't tell it what to use for NN required in subphrase
            if self.subPhrases:
                # find all minimum+ length sub phrases that include a noun
                words = phrase.split()
                idx = 0
                while idx < len(words) + 1:
                    idx2 = idx + 1
                    while idx2 < len(words) + 1:
                        curr = words[idx:idx2]
                        phrase = ' '.join(curr)
                        noun = (phrase.find('/NN') > -1)
                        if len(curr) >= minm and noun:
                            phrases.append(phrase)
                        idx2 += 1
                    idx += 1
            else:
                phrases = [phrase]

            for phrase in phrases:
                phrase = strp('', phrase)
                phrase = phrase.replace("  ", ' ')
                phrase = phrase.strip()
                if not minm or phrase.count(' ') >= (minm - 1):
                    if has(phrase):
                        kw[phrase]['occurences'] += 1
                    else:
                        kw[phrase] = {'text': phrase,
                                      'occurences': 1,
                                      'positions': []}
        return kw


class PosTypeNormalizer(SimpleNormalizer):
    """Normalizer to filter by part of speech tags.

    Default: keep only nouns.
    """

    types = []
    keepPos = 0

    _possibleSettings = {
        'posTypes': {
            'docs': ("Space separated list of PoS tags to keep. Defaults to "
                     "'NN NNP NNS'")
        },
        'pos': {
            'docs': ("Should the PoS tag be kept (1) or thrown away "
                     "(0)? Default: 0"),
            'type': int,
            'options': "0|1"
        }
    }

    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        # Load types from config
        types = self.get_setting(session, 'posTypes')
        if types:
            self.types = types.split()
        else:
            # Default to nouns
            self.types = ['NN', 'NNP', 'NNS']
        # Should we keep the /POS tag or strip it
        self.keepPos = self.get_setting(session, 'pos', 0)

    def process_string(self, session, data):
        try:
            (w, t) = data.rsplit('/', 1)
        except ValueError:
            print "%s failed to get xxx/YY: %s" % (self.id, data)
            return ""
        if t in self.types:
            if self.keepPos:
                return data
            else:
                return w
        else:
            return ""
