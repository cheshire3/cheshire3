
import nltk

from cheshire3.tokenizer import SimpleTokenizer


class UnparsedGeniaTokenizer(SimpleTokenizer):
    # take tab delimmed lines and turn into list of words ?

    _possibleSettings = {
        'useStem': {
            "docs": ("Should the text be reconstructed with the stem (1)"
                     " or not (0, default)"),
            'type': int,
            'options': "0|1"
        },
        'pos': {
            "docs": 'Should the text include the PoS tag',
            'type': int,
            'options': "0|1"
        },
        'structuredOutput': {
            'docs': '',
            'type': int,
            'options': '0|1'
        },
        'justPos': {
            "docs": 'Should the text be JUST the PoS tag',
            'type': int,
            'options': "0|1"
        }
    }

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        self.structure = self.get_setting(session, 'structuredOutput', 0)
        self.stem = self.get_setting(session, 'useStem', 0)
        self.pos = self.get_setting(session, 'pos', 0)
        self.justPos = self.get_setting(session, 'justPos', 0)

    def process_string(self, session, data):
        lines = data.split('\n')
        results = []
        for l in lines:
                try:
                    (word, stem, pos, phr, ner) = l.split('\t', 4)
                except:
                    continue
                if self.structure:
                    txt = (word, stem, pos, phr)
                else:
                    if self.stem:
                        txt = stem
                    elif self.justPos:
                        txt = pos
                    else:
                        txt = word
                    if self.pos:
                        txt = "%s/%s" % (txt, pos)
                results.append(txt)
        return results


class PhraseUnparsedGeniaTokenizer(UnparsedGeniaTokenizer):
    # re-concatenate tokens into phrases based on 'phr'
    # B-XP I-XP I-XP is a 3 token X phrase

    def __init__(self, session, config, parent):
        UnparsedGeniaTokenizer.__init__(self, session, config, parent)
        self.minWords = self.get_setting(session, 'minimumWords', 2)
        pt = self.get_setting(session, 'phraseTypes', 'N')
        self.phraseTypes = pt.split(' ')

    def process_string(self, session, data):
        lines = data.split('\n')
        results = []
        curr = []
        currType = ""
        for l in lines:
                try:
                    (word, stem, pos, phr, ner) = l.split('\t', 4)
                except:
                    continue

                if len(phr) < 3 or not phr[2] in self.phraseTypes:
                    if len(curr) >= self.minWords:
                        results.append(' '.join(curr))
                        curr = []
                    continue

                if self.stem:
                    txt = stem
                elif self.justPos:
                    txt = pos
                else:
                    txt = word
                if self.pos:
                    txt = "%s/%s" % (txt, pos)

                if phr[0] == "B":
                    # check if keep curr
                    if len(curr) >= self.minWords:
                        results.append(' '.join(curr))
                    curr = [txt]
                else:
                    curr.append(txt)

        if len(curr) >= self.minWords:
            results.append(' '.join(curr))
        return results


class NltkPunktWordTokenizer(SimpleTokenizer):

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        self.punkt = nltk.tokenize.PunktWordTokenizer()

    def process_string(self, session, data):
        return self.punkt.tokenize(data)


class NltkPunktSentenceTokenizer(SimpleTokenizer):
    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        self.punkt = nltk.data.load('tokenizers/punkt/english.pickle')

    def process_string(self, session, data):
        return self.punkt.tokenize(data)


# Backward compatibility
PunktWordTokenizer = NltkPunktWordTokenizer
PunktSentenceTokenizer = NltkPunktSentenceTokenizer
