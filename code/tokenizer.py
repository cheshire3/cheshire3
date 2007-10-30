
from baseObjects import Tokenizer
from dateutil import parser as dateparser
import re

# swap a string over to a list of tokens
# lists aren't hashable so we maintain string key
# also we're very unlikely to duplicate at this point,
#   and even if we do it's not important.
# This MUST be followed by a merge, however.
# as normalisers won't know what to do with a list as data


class SimpleTokenizer(Tokenizer):

    def process_string(self, session, data):
        return data.split()

    def process_hash(self, session, data):
        kw = {}
        for (key, val) in data.items():
            nval = val.copy()
            nval['text'] = self.process_string(session, val['text'])
            kw[key] = nval
        return kw


class RegexpSubTokenizer(SimpleTokenizer):
    # pre = self.get_setting(session, 'regexp', u"((?<!\s)'|[-.,]((?=\s)|$)|(^|(?<=\s))[-.,']|[\".,'-][\".,'-]|[~`!@+=\#\&\^*()\[\]{}\\\|\":;<>?/\u2026\u2013\u2014\u2018\u2019\u201c\u201d])")

    _possibleSettings = {'regexp' : {'docs' : ''},
                         'char' : {'docs' : ''}}

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        pre = self.get_setting(session, 'regexp', u"""([-.,'\")}\]]+((?=\s)|$)|(^|(?<=\s))[-.,']+|[`~!@+=\#\&\^*()\[\]{}\\\|\":;<>?/\u2026\u2013\u2014\u2018\u2019\u201c\u201d]|\.\.\.)""")
        self.regexp = re.compile(pre)
        self.char = self.get_setting(session, 'char', ' ')

    def process_string(self, session, data):
        # kill unwanted characters
        txt = self.regexp.sub(self.char, data)
        return txt.split()



# Medline terms that fail:
# Cbl-/- B cells      -- can be +/+, +/-, or -/-
# Na+-K+-ATPase, alphabeta+ blocker   (or whatever?!)
# R(0) transitions

        
class RegexpFindTokenizer(SimpleTokenizer):
    # Simple re-implementation of NLTK's RegexpTokenizer

    _possibleSettings = {'regexp' : {'docs' : ''},
                         'gaps' : {'docs' : '', 'type' : int, 'options' : "0|1"}
                         }

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        pre = self.get_setting(session, 'regexp', u"""
          (?xu)                                            #verbose, unicode
          (?:
            [a-zA-Z0-9!#$%*/?|^{}`~&'+-=_]+@[0-9a-zA-Z.-]+ #email
           |(?:[\w+-]+)?[+-]/[+-]                          #alleles
           |\w+(?:-\w+)+                                   #hypenated word
           |[$\xa3\xa5\u20AC]?[0-9]+(?:[.,:-][0-9]+)+[%]?  #date/num/money/time
           |[$\xa3\xa5\u20AC][0-9]+                        #single money
           |[0-9]+%                                        #single percentage 
           |(?:[A-Z]\.)+[A-Z]?                             #acronym
           |[oO]'[a-zA-Z]+                                 #o'clock, o'brien   
           |[a-z]+://[^\s]+                                #URI
           |\w+'(?:t|ll|ve|s|m)                            #don't, we've
           |[\w+]+                                         #basic words, including +
          )""")

        self.regexp = re.compile(pre)
        self.gaps = self.get_setting(session, 'gaps', 0)

    def process_string(self, session, data):
        if gaps:
            return [tok for tok in self._regexp.split(text) if tok]
        else:
            return self.regexp.findall(data)


class RegexpFindOffsetTokenizer(RegexpFindTokenizer):

    def process_string(self, session, data):
        tokens = []
        positions = []
        for m in self.regexp.finditer(data):
            tokens.append(m.group())
            positions.append(m.start())
        return (tokens, positions)
                         
    def process_hash(self, session, data):
        kw = {}
        for (key, val) in data.items():
            nval = val.copy()
            (tokens, positions) = self.process_string(session, val['text']) 
            nval['text'] = tokens
            nval['charOffsets'] = positions
            kw[key] = nval
        return kw



# XXX This should be in TextMining, and NLTK should auto install
try:
    import nltk
    class PunktWordTokenizer(SimpleTokenizer):

        def __init__(self, session, config, parent):
            SimpleTokenizer.__init__(self, session, config, parent)
            self.punkt = nltk.tokenize.PunktWordTokenizer()

        def process_string(self, session, data):
            return self.punkt.tokenize(data)


    class PunktSentenceTokenizer(SimpleTokenizer):
        def __init__(self, session, config, parent):
            SimpleTokenizer.__init__(self, session, config, parent)
            self.punkt = nltk.data.load('tokenizers/punkt/english.pickle')

        def process_string(self, session, data):
            return self.punkt.tokenize(data)
except:
    pass


# Was a text mining util, now should reformulate workflows
class SentenceTokenizer(SimpleTokenizer):

    def __init__(self, session, config, parent):
        self.paraRe = re.compile('\n\n+')
        self.sentenceRe = re.compile('.+?(?<!\.\.)[\.!?:]["\'\)]?(?=\s+|$)(?![a-z])')
        self.abbrMashRe = re.compile('(^|\s)([^\s]+?\.[a-zA-Z]+|Prof|Dr|Sr|Mr|Mrs|Ms|Jr|Capt|Gen|Col|Sgt|[ivxjCcl]+|[A-Z])\.(\s|$)')

    def process_string(self, data):
        ps = self.paraRe.split(data)
        sents = []
        for p in ps:
            s = self.abbrMashRe.sub('\\1\\2&#46;\\3', p)
            sl = self.sentenceRe.findall(s)
            if not sl:
                s += '.'
                sl = self.sentenceRe.findall(s)
            sents.extend(sl)
        return sents


class DateTokenizer(SimpleTokenizer):
    """ Extracts a single date. Multiple dates, ranges not yet implemented """
    """ Now extracts multiple dates, but slowly and less reliably. Ranges dealt with by DateRangeExtracter. JPH Jan '07"""

    _possibleDefaults = {'datetime' : {"docs" : "Default datetime to use for values not supplied in the data"}}
    _possibleSettings = {'fuzzy' : {"docs" : "Should the parser use fuzzy matching."}
                         , 'dayfirst' : {"docs" : "Is the day or month first, if not otherwise clear."}}

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        default = self.get_default(session, 'datetime')
        self.fuzzy = self.get_setting(session, 'fuzzy')
        self.dayfirst = self.get_setting(session, 'dayfirst')
        self.normalisedDateRe = re.compile('(?<=\d)xx+')
        self.isoDateRe = re.compile('''
        ([0-2]\d\d\d)        # match any year up to 2999
        (0[1-9]|1[0-2]|xx)?      # match any month 00-12 or xx
        ([0-2][0-9]|3[0-1]|xx)?  # match any date up to 00-31 or xx
        ''', re.VERBOSE|re.IGNORECASE)
        if default:
            self.default = dateparser.parse(default.encode('utf-8'), dayfirst=self.dayfirst, fuzzy=self.fuzzy)
        else:
            self.default = dateparser.parse('2000-01-01', fuzzy=True)
            
    def _convertIsoDates(self, mo):
        dateparts = [mo.group(1)]
        for x in range(2,4):
            if mo.group(x):
                dateparts.append(mo.group(x))
        return '-'.join(dateparts)
    
    def _tokenize(self, data):
        tks = []
        wds = data.split()
        while (len(wds)):
            for x in range(len(wds), 0, -1):
                try:
                    t = str(dateparser.parse(' '.join(wds[:x]).encode('utf-8'), default=self.default, dayfirst=self.dayfirst, fuzzy=self.fuzzy))
                except:
                    continue
                else:
                    tks.append(t)
                    break
            wds = wds[x:]
        return tks

    
    def process_string(self, session, data):
        # reconstruct data word by word and feed to parser?.
        # Must be a better way to do this
        # not sure, but I'll do that for now :p - JH

        data = self.isoDateRe.sub(self._convertIsoDates, data)        # separate ISO date elements with - for better recognition by date parser
        if len(data) and len(data) < 18 and data.find('-'):
            midpoint = len(data)/2
            if data[midpoint] == '-':
                # probably a range separated by -
                data = '%s %s' % (data[:midpoint], data[midpoint+1:])
                del midpoint                
        return self._tokenize(data)

