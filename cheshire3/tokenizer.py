"""Cheshire3 Tokenizer Implementations.

A Tokenizer converts a string to a list of tokens. Lists aren't hashable so we
maintain string key. Also we're very unlikely to duplicate at this point, and
even if we do it's not important.

A Tokenizer MUST be followed by a TokenMerger merge, however, as Normalizers
won't know what to do with a list as data.
"""


import re
import string
# Python source code tokenizer from base libs
import tokenize
import keyword
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from dateutil import parser as dateparser
from datetime import timedelta

from cheshire3.baseObjects import Tokenizer


class SimpleTokenizer(Tokenizer):

    _possibleSettings = {
        'char': {
            'docs': ('character to split with, or empty for default of '
                     'whitespace'
                     )
        }
    }

    def __init__(self, session, config, parent):
        Tokenizer.__init__(self, session, config, parent)
        self.char = self.get_setting(session, 'char', None)

    def process_string(self, session, data):
        if self.char:
            return data.split(self.char)
        else:
            return data.split()

    def process_hash(self, session, data):
        kw = {}
        for (key, val) in data.iteritems():
            nval = val.copy()
            nval['text'] = self.process_string(session, val['text'])
            kw[key] = nval
        return kw


class OffsetTokenizer(Tokenizer):

    def process_hash(self, session, data):
        kw = {}
        for (key, val) in data.iteritems():
            nval = val.copy()
            (tokens, positions) = self.process_string(session, val['text'])
            nval['text'] = tokens
            nval['charOffsets'] = positions
            kw[key] = nval
        return kw


class RegexpSubTokenizer(SimpleTokenizer):
    u"""Substitute regex matches with a character, then split on whitespace.

    A Tokenizer that replaces regular expression matches in the data with a
    configurable character (defaults to whitespace), then splits the result at
    whitespace.
    """

    _possibleSettings = {
        'regexp': {
            'docs': ("Regular expression to match and replace with instances "
                     "of 'char' before spltting on whitespace")
        },
        'char': {
            'docs': ''
        }
    }

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        pre = self.get_setting(session,
                               'regexp',
                               u"""(?x)([-.,'\")}\]]+((?=\s)|$)|(^|(?<=\s))
                                [-.,']+|[`~!@+=\#\&\^*()\[\]{}\\\|\":;<>?
                                /\u2026\u2013\u2014\u2018\u2019\u201c
                                \u201d]|\.\.\.)"""
                               )
        # all strings should be treated as unicode internally
        # this is default for lxml - primary Record implementation
        self.regexp = re.compile(pre, re.UNICODE)
        self.char = self.get_setting(session, 'char', ' ')

    def process_string(self, session, data):
        txt = self.regexp.sub(self.char, data)  # kill unwanted characters
        return txt.split()                      # split at whitespace


class RegexpSplitTokenizer(SimpleTokenizer):
    """A Tokenizer that simply splits at the regex matches."""

    _possibleSettings = {
        'regexp': {
            'docs': 'Regular expression used to split string'
        }
    }

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        pre = self.get_setting(session,
                               'regexp',
                               u"""(?x)([-.,'\")}\]]+((?=\s)|$)|(^|(?<=\s))
                                [-.,']+|[`~!@+=\#\&\^*()\[\]{}\\\|\":;<>?
                                /\u2026\u2013\u2014\u2018\u2019\u201c
                                \u201d]|\.\.\.)"""
                               )
        self.regexp = re.compile(pre, re.UNICODE)

    def process_string(self, session, data):
        return self.regexp.split(data)


class RegexpFindTokenizer(SimpleTokenizer):
    """A tokenizer that returns all words that match the regex."""
    # Some ideas thanks to NLTK's RegexpTokenizer

    # Some more ' words:
    # cat-o'-nine-tails, ne'er-do-well, will-o'-the-wisp
    #  --- ignoring
    # 'tis, 'twas, 'til, 'phone
    #  --- IMO should be indexed with leading '
    #  --- eg 'phone == phone
    #
    # XXX: Should come up with better solution
    # l'il ? y'all ?
    #

    # XXX: Decide what to do with 8am 8:00am 1.2M $1.2 $1.2M
    # As related to 8 am, 8:00 am, 1.2 Million, $ 1.2, $1.2 Million
    # vs $1200000 vs $ 1200000 vs four million dollars

    # Require acronyms to have at least TWO letters Eg U.S not just J.

    _possibleSettings = {
        'regexp': {
            'docs': 'Regular expression to match when finding tokens.'
        },
        'gaps': {
            'docs': ('Does the regular expression specify the gaps between '
                     'desired tokens. Defaults to 0 i.e. No, it specifies '
                     'tokens to keep'),
            'type': int,
            'options': "0|1"
        }
    }

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        pre = self.get_setting(session, 'regexp', u"""
        (?xu)                                            # verbose, unicode
        (?:
         [a-zA-Z0-9!#$%*/?|^{}`~&'+-=_]+@[0-9a-zA-Z.-]+ # email
         |(?:[\w+-]+)?[+-]/[+-]                         # genetic alleles
         |\w+(?:-\w+)+                                  # hypenated word
          (?:'(?:t|ll've|ll|ve|s|d've|d|re))?           # with/without 'suffix
         |[$\xa3\xa5\u20AC]?[0-9]+(?:[.,:-][0-9]+)+[%]? # date/num/money/time
         |[$\xa3\xa5\u20AC][0-9]+               # single money
         |[0-9]+(?=[a-zA-Z]+)                   # split: 8am 1Million
         |[0-9]+%                               # single percentage
         |(?:[A-Z]\.)+[A-Z\.]                   # abbreviation
         |[oOd]'[a-zA-Z]+                       # o'clock, O'Brien, d'Artagnan
         |[a-zA-Z]+://[^\s]+                    # URI
         |\w+'(?:d've|d|t|ll've|ll|ve|s|re)     # don't, we've
         |(?:[hH]allowe'en|[mM]a'am|[Ii]'m|[fF]o'c's'le|[eE]'en|[sS]'pose)
         |[\w+]+                                # basic words, including +
        )""")

        self.regexp = re.compile(pre, re.UNICODE)
        self.gaps = self.get_setting(session, 'gaps', 0)

    def process_string(self, session, data):
        if self.gaps:
            return [tok for tok in self.regexp.split(data) if tok]
        else:
            return self.regexp.findall(data)


class RegexpFindOffsetTokenizer(OffsetTokenizer, RegexpFindTokenizer):
    """Find tokens that match regex with character offsets.

    A Tokenizer that returns all words that match the regex, and also the
    character offset at which each word occurs.
    """

    def __init__(self, session, config, parent):
        # Only init once!
        RegexpFindTokenizer.__init__(self, session, config, parent)

    def process_string(self, session, data):
        tokens = []
        positions = []
        for m in self.regexp.finditer(data):
            tokens.append(m.group())
            positions.append(m.start())
        return (tokens, positions)


class RegexpFindPunctuationOffsetTokenizer(RegexpFindOffsetTokenizer):

    def process_string(self, session, data):
        tokens = []
        positions = []
        for m in self.regexp.finditer(data):
            tokens.append(m.group())
            i = m.start()
            while i > 0 and data[i - 1] in string.punctuation:
                i = i - 1
            positions.append(i)
        return (tokens, positions)


# Was a text mining util, now should reformulate workflows
class SentenceTokenizer(SimpleTokenizer):

    def __init__(self, session, config, parent):
        self.paraRe = re.compile('\n\n+', re.UNICODE)
        self.sentenceRe = re.compile(
            '.+?(?<!\.\.)[\.!?:]["\'\)]?(?=\s+|$)(?![a-z])',
            re.UNICODE | re.DOTALL
        )
        self.abbrMashRe = re.compile(
            '''
            (?xu)                                      # verbose, unicode
            (^|\s)                                     # leading spaces
            ([^\s]+?\.[a-zA-Z]+|
                Prof|Dr|Sr|Mr|Mrs|Ms|Jr|Capt|Gen|Col|Sgt|  # common abbrevs
                [ivxjCcl]+|[A-Z]
            )\.                                        # Acronyms?
            (\s|$)                                     # trailing space
            ''',
            re.UNICODE
        )

    def process_string(self, session, data):
        ps = self.paraRe.split(data)
        sents = []
        for p in ps:
            s = self.abbrMashRe.sub('\\1\\2&#46;\\3', p)
            sl = self.sentenceRe.findall(s)
            if not sl:
                s += '.'
                sl = self.sentenceRe.findall(s)
            sents.extend(sl)
        ns = []
        for s in sents:
            ns.append(s.replace("&#46;", '.'))
        return ns


class LineTokenizer(SimpleTokenizer):
    "Trivial but potentially useful Tokenizer to split data on whitespace."

    def process_string(self, session, data):
        return data.split('\n')


class DateTokenizer(SimpleTokenizer):
    """Tokenizer to identify date tokens, and return only these.

    Capable of extracting multiple dates, but slowly and less reliably than
    single ones.
    """

    _possibleDefaults = {
        'datetime': {
            "docs": ("Default datetime to use for values not supplied in the "
                     "data")
        }
    }

    _possibleSettings = {
        'fuzzy': {
            "docs": "Should the parser use fuzzy matching.",
            'type': int,
            'options': '0|1'
        },
        'dayfirst': {
            "docs": ("Is the day before the month (when ambiguous). "
                     "1 = Yes, 0 = No (default)"),
            'type': int,
            'options': '0|1'
        }
    }

    def __init__(self, session, config, parent):
        SimpleTokenizer.__init__(self, session, config, parent)
        default = self.get_default(session, 'datetime')
        self.fuzzy = self.get_setting(session, 'fuzzy')
        self.dayfirst = self.get_setting(session, 'dayfirst')
        self.normalisedDateRe = re.compile('(?<=\d)xx+', re.UNICODE)
        self.isoDateRe = re.compile('''
        ([0-2]\d\d\d)        # match any year up to 2999
        (0[1-9]|1[0-2]|xx)?      # match any month 01-12 or xx
        (0[1-9]|[1-2][0-9]|3[0-1]|xx)?  # match any date up to 01-31 or xx
        ''', re.VERBOSE | re.IGNORECASE | re.UNICODE)
        if default:
            self.default = dateparser.parse(default.encode('utf-8'),
                                            dayfirst=self.dayfirst,
                                            fuzzy=self.fuzzy)
        else:
            self.default = dateparser.parse('2000-01-01', fuzzy=True)

    def _convertIsoDates(self, mo):
        dateparts = [mo.group(1)]
        for x in range(2, 4):
            if mo.group(x):
                dateparts.append(mo.group(x))
        return '-'.join(dateparts)

    def _tokenize(self, data, default=None):
        if default is None:
            default = self.default
        # Deconstruct data word by word and feed to parser until success.
        # Must be a better way to do this..., but for now...
        tks = []
        wds = data.split()
        while (len(wds)):
            for x in range(len(wds), 0, -1):
                txt = ' '.join(wds[:x]).encode('utf-8')
                try:
                    t = dateparser.parse(txt,
                                         default=default,
                                         dayfirst=self.dayfirst,
                                         fuzzy=self.fuzzy
                                         ).isoformat()
                except:
                    continue
                else:
                    tks.append(t)
                    break
            wds = wds[x:]
        return tks

    def process_string(self, session, data):
        # Convert ISO 8601 date elements to extended format (YYYY-MM-DD) for
        # better recognition by date parser
        data = self.isoDateRe.sub(self._convertIsoDates, data)
        if len(data):
            # a range?
            bits = []
            if data.count('/') == 1:
                bits = data.split('/')
            # ISO allows YYYY-MM and YYYY-Www
            elif data.count('-') == 1 and (data.find('-') < len(data) - 4):
                bits = data.split('-')
            if len(bits):
                # Use a new default, just under a year on for the end of the
                # range
                td = timedelta(days=365, hours=23, minutes=59, seconds=59,
                               microseconds=999999)
                tks = self._tokenize(bits[0]) + \
                    self._tokenize(bits[1], self.default + td)
            else:
                tks = []
            if len(tks):
                return tks
        return self._tokenize(data)


class DateRangeTokenizer(DateTokenizer):
    """Tokenizer to identify ranges of date tokens, and return only these.

    e.g.

    >>> self.process_string(session, '2003/2004')
    ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']
    >>> self.process_string(session, '2003-2004')
    ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']
    >>> self.process_string(session, '2003 2004')
    ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']
    >>> self.process_string(session, '2003 to 2004')
    ['2003-01-01T00:00:00', '2004-12-31T23:59:59.999999']

    For single dates, attempts to expand this into the largest possible range
    that the data could specify. e.g. 1902-04 means the whole of April 1902.

    >>> self.process_string(session, "1902-04")
    ['1902-04-01T00:00:00', '1902-04-30T23:59:59.999999']

    """

    def process_string(self, session, data):
        # Convert ISO 8601 date elements to extended format (YYYY-MM-DD)
        # for better recognition by date parser
        data = self.isoDateRe.sub(self._convertIsoDates, data)
        if not data:
            return []
        midpoint = len(data) / 2
        if data[midpoint] in ['/', '-', ' ']:
            startK = data[:midpoint]
            endK = data[midpoint + 1:]
        elif len(data.split(' to ')) == 2:
            startK, endK = data.split(' to ')
        elif data.count('/') == 1:
            startK, endK = data.split('/')
        # ISO allows YYYY-MM and YYYY-Www
        elif data.count('-') == 1 and (data.find('-') < len(data) - 4):
            startK, endK = data.split('-')
        else:
            startK = endK = data
        starts = self._tokenize(startK)
        ends = []
        days = 365
        # For end point use a new default, just under a year on for the end
        # of the range. Also account for varying month lengths.
        while not ends and days > 361:
            td = timedelta(days=days,
                           hours=23,
                           minutes=59,
                           seconds=59,
                           microseconds=999999
                           )
            ends = self._tokenize(endK, self.default + td)
            days -= 1
        return starts + ends


class PythonTokenizer(OffsetTokenizer):
    """ Tokenize python source code into token/TYPE with offsets """

    def __init__(self, session, config, parent):
        OffsetTokenizer.__init__(self, session, config, parent)
        self.ignoreTypes = [tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE,
                            tokenize.NL, tokenize.ENDMARKER]

    def process_string(self, session, data):
        io = StringIO.StringIO(data)
        toks = []
        posns = []
        totalChrs = 0
        currLine = 0
        prevLineLen = 0
        for tok in tokenize.generate_tokens(io.readline):
            (ttype, txt, start, end, lineTxt) = tok
            if start[0] != currLine:
                totalChrs += prevLineLen
                prevLineLen = len(lineTxt)
                currLine = start[0]
            # maybe store token
            if not ttype in self.ignoreTypes:
                tname = tokenize.tok_name[ttype]
                if tname == "NAME" and keyword.iskeyword(txt):
                    toks.append("%s/KEYWORD" % (txt))
                else:
                    toks.append("%s/%s" % (txt, tokenize.tok_name[ttype]))
                posns.append(totalChrs + start[1])
        return (toks, posns)
