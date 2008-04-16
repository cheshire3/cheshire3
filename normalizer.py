
from configParser import C3Object
from baseObjects import Normalizer
from c3errors import ConfigFileException
import types, re, os

# The following defaults should be overridden
# SimpleNormalizer should never be used (waste of CPU)
class SimpleNormalizer(Normalizer):
    """ Base normalizer.  Simply returns the data (shouldn't be used directly) """

    def __init__(self, session, config, parent):
        Normalizer.__init__(self, session, config, parent)
        

    def process_string(self, session, data):
        # normalise string into single appropriate form (eg '1' -> 1)
        return data

    def process_hash(self, session, data):
        kw = {}
        if not data:
            return kw
        has = kw.has_key
        process = self.process_string        
        #items = data.items()
        #prox = items[0][1].has_key('positions')
        for (k,d) in data.iteritems():
            dv = d['text']
            if type(dv) == list:
                new = []
                for x in range(len(dv)-1, -1, -1):
                    dvi = dv[x]
                    ndvi = process(session, dvi)
                    if ndvi:
                        new.append(ndvi)
                    else:
                        try:
                            d['charOffsets'].pop(x)
                        except KeyError:
                            pass
                new.reverse()        
                nd = d.copy()
                nd['text'] = new
                kw[k] = nd
                continue
            else:
                new = process(session, d['text'])
            if not new:
                continue
            if type(new) == types.DictType:
                # from string to hash
                for nv in new.itervalues():
                    txt = nv['text']
                    if has(txt):
                        kw[txt]['occurences'] += nv['occurences']
                        try:
                            kw[txt]['positions'].extend(nv['positions'])
                        except: pass
                        try:
                            kw[txt]['proxLoc'].extend(nv['proxLoc'])
                        except: pass
                    else:
                        kw[txt] = nv
            else:
                if new != None:
                    try:
                        kw[new]['occurences'] += d['occurences']
                        try:
                            kw[new]['positions'].extend(d['positions'])
                        except: pass
                        try:
                            kw[new]['proxLoc'].extend(d['proxLoc'])
                        except: pass
                    except KeyError:
                        d = d.copy()
                        try:
                            d['positions'] = d['positions'][:]
                        except: pass
                        try:
                            d['proxLoc'] = d['proxLoc'][:]
                        except: pass
                        d['text'] = new
                        kw[new] = d
                        
        return kw

class DataExistsNormalizer(SimpleNormalizer):
    """ Return '1' if any data exists, otherwise '0' """

    def process_string(self, session, data):
        if data:
            return "1"
        else:
            return "0"

class TermExistsNormalizer(SimpleNormalizer):
    """ Un-stoplist anonymizing normalizer. Eg for use with data mining """

    _possibleSettings = {
        'termlist' : {'docs' : "'splitChar' (defaulting to space) separated list of terms.  For each term, if it exists in this list, the normalizer returns '1', otherwise '0'", 'required' : True},
        'splitChar' : {'docs' : "Override for the character to split on"},
        'frequency' : {'docs' : 'if 1, accumulate total occurences, otherwise add one per term', 'type' : int, 'options' : "0|1"}
        }

    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        tlstr = self.get_setting(session, 'termlist', '')
        splitter = self.get_setting(session, 'splitChar', ' ')
        self.termlist = tlstr.split(splitter)
        self.frequency = self.get_setting(session, 'frequency', 0)

    def process_string(self, session, data):
        if data in self.termlist:
            return "1"
        else:
            return "0"

    def process_hash(self, session, data):
        vals = data.values()
        if not vals:
            return kw
        process = self.process_string
        total = 0
        for d in vals:
            new = process(session, d['text'])
            if new == "1":
                if self.frequency:
                    total += d['occurences']
                else:
                    total += 1
        return str(total)


class UndocumentNormalizer(SimpleNormalizer):
    """ Take a document as if it were a string and turn into a string """
    def process_string(self, session, data):
        return data.get_raw(session)
    
    
class CaseNormalizer(SimpleNormalizer):
    """ Reduce text to lower case """

    def process_string(self, session, data):
        return data.lower()

class ReverseNormalizer(SimpleNormalizer):
    """ Reverse string (eg for left truncation) """
    def process_string(self, session, data):
        return data[::-1]

    
class SpaceNormalizer(SimpleNormalizer):
    """ Reduce multiple whitespace to single space character """
    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        self.whitespace = re.compile("\s+")

    def process_string(self, session, data):
        data = data.strip()
        data = self.whitespace.sub(' ', data)
        return data

class ArticleNormalizer(SimpleNormalizer):
    """ Remove leading english articles (the, a, an) """
    def process_string(self, session, data):
        d = data.lower()
        if (d[:4] == "the "):
            return data[4:]
        elif (d[:2] == "a "):
            return data[2:]
        elif (d[:3] == "an "):
            return data[3:]
        else:
            return data


class NumericEntityNormalizer(SimpleNormalizer):
    """ Replace characters matching regular expression with the equivalent numeric character entity """

    _possibleSettings = {'regexp':
                         {'docs' : "Regular expression of that matches characters to turn into XML numeric character entities"}
                         }
    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        regex = self.get_setting(session, 'regexp', '([\x0e-\x1f]|[\x7b-\xff])')
        self.regexp = re.compile(regex)
        self.function = lambda x: "&#%s;" % ord(x.group(1))

    def process_string(self, session, data):
        return self.regexp.sub(self.function, data)


# Non printable characters (Printable)
# self.asciiRe = re.compile('([\x0e-\x1f]|[\x7b-\xff])')

# Non useful characters (Stripper)
# self.asciiRe = re.compile('["%#@~!*{}]')

class PointlessCharacterNormalizer(SimpleNormalizer):
    def process_string(self, session, data):
        t = data.replace(u'\ufb00', 'ff')
        t = t.replace(u'\ufb01', 'fi')
        t = t.replace(u'\xe6', 'fi')
        t = t.replace(u'\ufb02', 'fl')
        t = t.replace(u'\u201c', '"')
        t = t.replace(u'\u201d', '"')
        t = t.replace(u'\u2019', "'")
        t = t.replace(u'\u2026', " ")
        return t
    

class RegexpNormalizer(SimpleNormalizer):
    """ Either strip, replace or keep data which matches a given regular expression """

    _possibleSettings = {'char': {'docs' :"Character(s) to replace matches in the regular expression with. Defaults to empty string (eg strip matches)"},
                         'regexp': {'docs' : "Regular expression to match in the data.", 'required' : True},
                         'keep': {'docs' : "Should instead keep only the matches. Boolean, defaults to False", 'type': int, 'options' : "0|1"}
                         }

    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        self.char = self.get_setting(session, 'char', '')
        self.keep = self.get_setting(session, 'keep', 0)
        regex = self.get_setting(session, 'regexp')
        if regex:
            self.regexp = re.compile(regex)
        else:
            raise ConfigFileException('Missing regexp setting for %s.' % (self.id))

    def process_string(self, session, data):
        if self.keep:
            try:
                l = self.regexp.findall(data)
            except UnicodeDecodeError:
                data = data.decode('utf-8')
                l = self.regexp.findall(data)
            return self.char.join(l)
        else:
            try:
                return self.regexp.sub(self.char, data)
            except UnicodeDecodeError:
                data = data.decode('utf-8')
                try:
                    return self.regexp.sub(self.char, data)
                except:
                    raise
    

class NamedRegexpNormalizer(RegexpNormalizer):
    """ As RegexpNormalizer, but allow named groups and reconstruction of token using a template and those groups. """

    _possibleSettings = {'template' : {'docs' : "Template using group names for replacement, as per % substitution. Eg regexp = (?P<word>.+)/(?P<pos>.+) and template = --%(pos)s--, cat/NN would generate --NN--"}}

    def __init__(self, session, config, parent):
        RegexpNormalizer.__init__(self, session, config, parent)
        self.template = self.get_setting(session, 'template', '')
        
    def process_string(self, session, data):
        m = self.regexp.match(data)        
        if m:
            try:
                return self.template % m.groupdict()
            except:
                return ""
        else:
            return ""


class PossessiveNormalizer(SimpleNormalizer):
    """ Remove trailing 's or s' from words """
    def process_string(self, session, data):
        # Not totally correct... eg:  it's == 'it is', not 'of it'
        if (data[-2:] == "s'"):
            return data[:-1]
        elif (data[-2:] == "'s"):
            return data[:-2]
        else:
            return data

class IntNormalizer(SimpleNormalizer):
    """ Turn a string into an integer """
    def process_string(self, session, data):
        try:
            return long(data)
        except:
            return None
        
class StringIntNormalizer(SimpleNormalizer):
    """ Turn an integer into a 0 padded string, 12 chrs long """
    def process_string(self, session, data):
        try:
            d = long(data)
            return "%012d" % (d)
        except:
            return None

class StoplistNormalizer(SimpleNormalizer):
    """ Remove words that match a stopword list """
    stoplist = {}

    _possiblePaths = {'stoplist' : {'docs' : "Path file containing set of stop terms, one term per line.", 'required' : True}}

    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        p = self.get_path(session, "stoplist")
        if (not os.path.isabs(p)):
            dfp = self.get_path(session, "defaultPath")
            p = os.path.join(dfp, p)
        f = file(p)
        l = f.readlines()
        f.close()
        for sw in l:
            # chomp
            self.stoplist[sw[:-1]] = 1
            
    def process_string(self, session, data):
        if (self.stoplist.has_key(data)):
            return None
        else:
            return data     

try:
    import txngstemmer as Stemmer

    class StemNormalizer(SimpleNormalizer):
        """ Use a Snowball stemmer to stem the terms """
        stemmer = None

        _possibleSettings = {'language' : {'docs' : "Language to create a stemmer for, defaults to english.", 'options' : 'danish|dutch|english|finnish|french|german|italian|norwegian|porter|portuguese|russian|spanish|swedish'}}

        def __init__(self, session, config, parent):
            SimpleNormalizer.__init__(self, session, config, parent)
            lang = self.get_setting(session, 'language', 'english')
            try:
                self.stemmer = Stemmer.Stemmer(lang)
            except:
                raise(ConfigFileException("Unknown stemmer language: %s" % (lang)))

        def process_string(self, session, data):
            if (type(data) != type(u"")):
                data = unicode(data, 'utf-8')            
            return self.stemmer.stem([data])[0]

    class PhraseStemNormalizer(SimpleNormalizer):
        """ Use a Snowball stemmer to stem multiple words in a phrase (eg from PosPhraseNormalizer).
        Deprecated: Should instead use normalizer after tokenizer and before tokenMerger.
        """
        

        stemmer = None

        def __init__(self, session, config, parent):
            SimpleNormalizer.__init__(self, session, config, parent)
            lang = self.get_setting(session, 'language', 'english')
            self.punctuationRe = re.compile("((?<!s)'|[-.,]((?=\s)|$)|(^|(?<=\s))[-.,']|[~`!@+=\#\&\^*()\[\]{}\\\|\":;<>?/])")
            try:
                self.stemmer = Stemmer.Stemmer(lang)
            except:
                raise(ConfigFileException("Unknown stemmer language: %s" % (lang)))

        def process_string(self, session, data):
            if (type(data) != type(u"")):
                data = unicode(data, 'utf-8')            
            s = self.punctuationRe.sub(' ', data)
            wds = data.split()
            stemmed = self.stemmer.stem(wds)
            return ' '.join(stemmed)

except:

    class StemNormalizer(SimpleNormalizer):
        def __init__(self, session, config, parent):
            raise(ConfigFileException('Stemmer library not available'))



class DateStringNormalizer(SimpleNormalizer):
    """ Turns a Date object into ISO8601 format """
    
    def process_string(self, session, data):
        # str() defaults to iso8601 format
        return str(data)   



class RangeNormalizer(SimpleNormalizer):
    """ TODO XXX: Should normalise ranges?... unfinished??? delete??? """ 

    def process_hash(self, session, data):
        # Need to step through positions in order
        kw = {}
        vals = data.values()
        if not vals:
            return kw
        prox = vals[0].has_key('positions')
        if not prox:
            # Bad. Assume low -> high order
            tmplist = [(d['text'], d) for d in vals]
        else:
            # Need to duplicate across occs, as all in same hash from record
            tmplist = []
            for d in vals:
                for x in range(0, len(d['positions']), 2):
                    tmplist.append(("%s-%s" % (d['positions'][x], d['positions'][x+1]), d))
        tmplist.sort()

        for t in range(0,len(tmplist),2):
            base = tmplist[t][1]
            try:
                text = base['text'] + " " + tmplist[t+1][1]['text']
            except:
                text = base['text'] + " " + base['text']
            base['text'] = text
            try:
                del base['positions']
            except:
                pass
            kw[text] = base

        return kw
        


class ExactExpansionNormalizer(SimpleNormalizer):
    # Expand stuff within a string
    # Then maybe pass to keyworder
    map = {
        'USA' :'United States of America',
        'UK' : 'United Kingdom',
        'NZ' : 'New Zealand',
        'XML' : 'Extensible Markup Language',
        'SOAP' : 'Simple Object Access Protocol',
        'SRW' : 'Search Retrieve Webservice',
        'CQL' : 'Common Query Language',
        "isn't" : 'is not',
        "don't" : "do not",
        "won't" : "will not",
        "can't" : "can not",
        "wasn't" : "was not",
        "hasn't" : "has not",
        "I'm" : "I am",
        "you're" : "you are",
        "he's" : "he is",
        "she's" : "she is",
        "they're" : "they are",
        "we're" : "we are",
        "I'd" : "I would",
        "she'd" : "she would",
        "he'd" : "he would",
        "we'd" : "we would",
        "they'd" : "they would",
        "you'd" : "you would"
        }       

    def process_string(self, session, data):
        for m in self.map.iteritems():
            data = data.replace(m[0], m[1])
        return data
       


class DiacriticNormalizer(SimpleNormalizer):
    """ Slow implementation of Unicode 4.0 character decomposition. Eg that &amp;eacute; -> e """

    # Decomposition as per Unicode 4.0 Data file
    map = {
        u"\u00C0" : u"\u0041",
        u"\u00C1" : u"\u0041",
        u"\u00C2" : u"\u0041",
        u"\u00C3" : u"\u0041",
        u"\u00C4" : u"\u0041",
        u"\u00C5" : u"\u0041",
        u"\u00C7" : u"\u0043",
        u"\u00C8" : u"\u0045",
        u"\u00C9" : u"\u0045",
        u"\u00CA" : u"\u0045",
        u"\u00CB" : u"\u0045",
        u"\u00CC" : u"\u0049",
        u"\u00CD" : u"\u0049",
        u"\u00CE" : u"\u0049",
        u"\u00CF" : u"\u0049",
        u"\u00D1" : u"\u004E",
        u"\u00D2" : u"\u004F",
        u"\u00D3" : u"\u004F",
        u"\u00D4" : u"\u004F",
        u"\u00D5" : u"\u004F",
        u"\u00D6" : u"\u004F",
        u"\u00D9" : u"\u0055",
        u"\u00DA" : u"\u0055",
        u"\u00DB" : u"\u0055",
        u"\u00DC" : u"\u0055",
        u"\u00DD" : u"\u0059",
        u"\u00E0" : u"\u0061",
        u"\u00E1" : u"\u0061",
        u"\u00E2" : u"\u0061",
        u"\u00E3" : u"\u0061",
        u"\u00E4" : u"\u0061",
        u"\u00E5" : u"\u0061",
        u"\u00E6" : u"\u0061\u0065",
        u"\u00E7" : u"\u0063",
        u"\u00E8" : u"\u0065",
        u"\u00E9" : u"\u0065",
        u"\u00EA" : u"\u0065",
        u"\u00EB" : u"\u0065",
        u"\u00EC" : u"\u0069",
        u"\u00ED" : u"\u0069",
        u"\u00EE" : u"\u0069",
        u"\u00EF" : u"\u0069",
        u"\u00F1" : u"\u006E",
        u"\u00F2" : u"\u006F",
        u"\u00F3" : u"\u006F",
        u"\u00F4" : u"\u006F",
        u"\u00F5" : u"\u006F",
        u"\u00F6" : u"\u006F",
        u"\u00F8" : u"\u006F",
        u"\u00F9" : u"\u0075",
        u"\u00FA" : u"\u0075",
        u"\u00FB" : u"\u0075",
        u"\u00FC" : u"\u0075",
        u"\u00FD" : u"\u0079",
        u"\u00FF" : u"\u0079",
        u"\u0100" : u"\u0041",
        u"\u0101" : u"\u0061",
        u"\u0102" : u"\u0041",
        u"\u0103" : u"\u0061",
        u"\u0104" : u"\u0041",
        u"\u0105" : u"\u0061",
        u"\u0106" : u"\u0043",
        u"\u0107" : u"\u0063",
        u"\u0108" : u"\u0043",
        u"\u0109" : u"\u0063",
        u"\u010A" : u"\u0043",
        u"\u010B" : u"\u0063",
        u"\u010C" : u"\u0043",
        u"\u010D" : u"\u0063",
        u"\u010E" : u"\u0044",
        u"\u010F" : u"\u0064",
        u"\u0112" : u"\u0045",
        u"\u0113" : u"\u0065",
        u"\u0114" : u"\u0045",
        u"\u0115" : u"\u0065",
        u"\u0116" : u"\u0045",
        u"\u0117" : u"\u0065",
        u"\u0118" : u"\u0045",
        u"\u0119" : u"\u0065",
        u"\u011A" : u"\u0045",
        u"\u011B" : u"\u0065",
        u"\u011C" : u"\u0047",
        u"\u011D" : u"\u0067",
        u"\u011E" : u"\u0047",
        u"\u011F" : u"\u0067",
        u"\u0120" : u"\u0047",
        u"\u0121" : u"\u0067",
        u"\u0122" : u"\u0047",
        u"\u0123" : u"\u0067",
        u"\u0124" : u"\u0048",
        u"\u0125" : u"\u0068",
        u"\u0128" : u"\u0049",
        u"\u0129" : u"\u0069",
        u"\u012A" : u"\u0049",
        u"\u012B" : u"\u0069",
        u"\u012C" : u"\u0049",
        u"\u012D" : u"\u0069",
        u"\u012E" : u"\u0049",
        u"\u012F" : u"\u0069",
        u"\u0130" : u"\u0049",
        u"\u0132" : u"\u0049",
        u"\u0133" : u"\u0069",
        u"\u0134" : u"\u004A",
        u"\u0135" : u"\u006A",
        u"\u0136" : u"\u004B",
        u"\u0137" : u"\u006B",
        u"\u0139" : u"\u004C",
        u"\u013A" : u"\u006C",
        u"\u013B" : u"\u004C",
        u"\u013C" : u"\u006C",
        u"\u013D" : u"\u004C",
        u"\u013E" : u"\u006C",
        u"\u013F" : u"\u004C",
        u"\u0140" : u"\u006C",
        u"\u0143" : u"\u004E",
        u"\u0144" : u"\u006E",
        u"\u0145" : u"\u004E",
        u"\u0146" : u"\u006E",
        u"\u0147" : u"\u004E",
        u"\u0148" : u"\u006E",
        u"\u0149" : u"\u02BC",
        u"\u014C" : u"\u004F",
        u"\u014D" : u"\u006F",
        u"\u014E" : u"\u004F",
        u"\u014F" : u"\u006F",
        u"\u0150" : u"\u004F",
        u"\u0151" : u"\u006F",
        u"\u0154" : u"\u0052",
        u"\u0155" : u"\u0072",
        u"\u0156" : u"\u0052",
        u"\u0157" : u"\u0072",
        u"\u0158" : u"\u0052",
        u"\u0159" : u"\u0072",
        u"\u015A" : u"\u0053",
        u"\u015B" : u"\u0073",
        u"\u015C" : u"\u0053",
        u"\u015D" : u"\u0073",
        u"\u015E" : u"\u0053",
        u"\u015F" : u"\u0073",
        u"\u0160" : u"\u0053",
        u"\u0161" : u"\u0073",
        u"\u0162" : u"\u0054",
        u"\u0163" : u"\u0074",
        u"\u0164" : u"\u0054",
        u"\u0165" : u"\u0074",
        u"\u0168" : u"\u0055",
        u"\u0169" : u"\u0075",
        u"\u016A" : u"\u0055",
        u"\u016B" : u"\u0075",
        u"\u016C" : u"\u0055",
        u"\u016D" : u"\u0075",
        u"\u016E" : u"\u0055",
        u"\u016F" : u"\u0075",
        u"\u0170" : u"\u0055",
        u"\u0171" : u"\u0075",
        u"\u0172" : u"\u0055",
        u"\u0173" : u"\u0075",
        u"\u0174" : u"\u0057",
        u"\u0175" : u"\u0077",
        u"\u0176" : u"\u0059",
        u"\u0177" : u"\u0079",
        u"\u0178" : u"\u0059",
        u"\u0179" : u"\u005A",
        u"\u017A" : u"\u007A",
        u"\u017B" : u"\u005A",
        u"\u017C" : u"\u007A",
        u"\u017D" : u"\u005A",
        u"\u017E" : u"\u007A",
        u"\u01A0" : u"\u004F",
        u"\u01A1" : u"\u006F",
        u"\u01AF" : u"\u0055",
        u"\u01B0" : u"\u0075",
        u"\u01C4" : u"\u0044",
        u"\u01C5" : u"\u0044",
        u"\u01C6" : u"\u0064",
        u"\u01C7" : u"\u004C",
        u"\u01C8" : u"\u004C",
        u"\u01C9" : u"\u006C",
        u"\u01CA" : u"\u004E",
        u"\u01CB" : u"\u004E",
        u"\u01CC" : u"\u006E",
        u"\u01CD" : u"\u0041",
        u"\u01CE" : u"\u0061",
        u"\u01CF" : u"\u0049",
        u"\u01D0" : u"\u0069",
        u"\u01D1" : u"\u004F",
        u"\u01D2" : u"\u006F",
        u"\u01D3" : u"\u0055",
        u"\u01D4" : u"\u0075",
        u"\u01D5" : u"\u0055",
        u"\u01D6" : u"\u0075",
        u"\u01D7" : u"\u0055",
        u"\u01D8" : u"\u0075",
        u"\u01D9" : u"\u0055",
        u"\u01DA" : u"\u0075",
        u"\u01DB" : u"\u0055",
        u"\u01DC" : u"\u0075",
        u"\u01DE" : u"\u0041",
        u"\u01DF" : u"\u0061",
        u"\u01E0" : u"\u0226",
        u"\u01E1" : u"\u0227",
        u"\u01E2" : u"\u00C6",
        u"\u01E3" : u"\u00E6",
        u"\u01E6" : u"\u0047",
        u"\u01E7" : u"\u0067",
        u"\u01E8" : u"\u004B",
        u"\u01E9" : u"\u006B",
        u"\u01EA" : u"\u004F",
        u"\u01EB" : u"\u006F",
        u"\u01EC" : u"\u004F",
        u"\u01ED" : u"\u006F",
        u"\u01EE" : u"\u01B7",
        u"\u01EF" : u"\u0292",
        u"\u01F0" : u"\u006A",
        u"\u01F1" : u"\u0044",
        u"\u01F2" : u"\u0044",
        u"\u01F3" : u"\u0064",
        u"\u01F4" : u"\u0047",
        u"\u01F5" : u"\u0067",
        u"\u01F8" : u"\u004E",
        u"\u01F9" : u"\u006E",
        u"\u01FA" : u"\u0041",
        u"\u01FB" : u"\u0061",
        u"\u01FC" : u"\u00C6",
        u"\u01FD" : u"\u00E6",
        u"\u01FE" : u"\u00D8",
        u"\u01FF" : u"\u00F8",
        u"\u0200" : u"\u0041",
        u"\u0201" : u"\u0061",
        u"\u0202" : u"\u0041",
        u"\u0203" : u"\u0061",
        u"\u0204" : u"\u0045",
        u"\u0205" : u"\u0065",
        u"\u0206" : u"\u0045",
        u"\u0207" : u"\u0065",
        u"\u0208" : u"\u0049",
        u"\u0209" : u"\u0069",
        u"\u020A" : u"\u0049",
        u"\u020B" : u"\u0069",
        u"\u020C" : u"\u004F",
        u"\u020D" : u"\u006F",
        u"\u020E" : u"\u004F",
        u"\u020F" : u"\u006F",
        u"\u0210" : u"\u0052",
        u"\u0211" : u"\u0072",
        u"\u0212" : u"\u0052",
        u"\u0213" : u"\u0072",
        u"\u0214" : u"\u0055",
        u"\u0215" : u"\u0075",
        u"\u0216" : u"\u0055",
        u"\u0217" : u"\u0075",
        u"\u0218" : u"\u0053",
        u"\u0219" : u"\u0073",
        u"\u021A" : u"\u0054",
        u"\u021B" : u"\u0074",
        u"\u021E" : u"\u0048",
        u"\u021F" : u"\u0068",
        u"\u0226" : u"\u0041",
        u"\u0227" : u"\u0061",
        u"\u0228" : u"\u0045",
        u"\u0229" : u"\u0065",
        u"\u022A" : u"\u004F",
        u"\u022B" : u"\u006F",
        u"\u022C" : u"\u004F",
        u"\u022D" : u"\u006F",
        u"\u022E" : u"\u004F",
        u"\u022F" : u"\u006F",
        u"\u0230" : u"\u004F",
        u"\u0231" : u"\u006F",
        u"\u0232" : u"\u0059",
        u"\u0233" : u"\u0079",
        u"\u1E00" : u"\u0041",
        u"\u1E01" : u"\u0061",
        u"\u1E02" : u"\u0042",
        u"\u1E03" : u"\u0062",
        u"\u1E04" : u"\u0042",
        u"\u1E05" : u"\u0062",
        u"\u1E06" : u"\u0042",
        u"\u1E07" : u"\u0062",
        u"\u1E08" : u"\u0043",
        u"\u1E09" : u"\u0063",
        u"\u1E0A" : u"\u0044",
        u"\u1E0B" : u"\u0064",
        u"\u1E0C" : u"\u0044",
        u"\u1E0D" : u"\u0064",
        u"\u1E0E" : u"\u0044",
        u"\u1E0F" : u"\u0064",
        u"\u1E10" : u"\u0044",
        u"\u1E11" : u"\u0064",
        u"\u1E12" : u"\u0044",
        u"\u1E13" : u"\u0064",
        u"\u1E14" : u"\u0045",
        u"\u1E15" : u"\u0065",
        u"\u1E16" : u"\u0045",
        u"\u1E17" : u"\u0065",
        u"\u1E18" : u"\u0045",
        u"\u1E19" : u"\u0065",
        u"\u1E1A" : u"\u0045",
        u"\u1E1B" : u"\u0065",
        u"\u1E1C" : u"\u0045",
        u"\u1E1D" : u"\u0065",
        u"\u1E1E" : u"\u0046",
        u"\u1E1F" : u"\u0066",
        u"\u1E20" : u"\u0047",
        u"\u1E21" : u"\u0067",
        u"\u1E22" : u"\u0048",
        u"\u1E23" : u"\u0068",
        u"\u1E24" : u"\u0048",
        u"\u1E25" : u"\u0068",
        u"\u1E26" : u"\u0048",
        u"\u1E27" : u"\u0068",
        u"\u1E28" : u"\u0048",
        u"\u1E29" : u"\u0068",
        u"\u1E2A" : u"\u0048",
        u"\u1E2B" : u"\u0068",
        u"\u1E2C" : u"\u0049",
        u"\u1E2D" : u"\u0069",
        u"\u1E2E" : u"\u0049",
        u"\u1E2F" : u"\u0069",
        u"\u1E30" : u"\u004B",
        u"\u1E31" : u"\u006B",
        u"\u1E32" : u"\u004B",
        u"\u1E33" : u"\u006B",
        u"\u1E34" : u"\u004B",
        u"\u1E35" : u"\u006B",
        u"\u1E36" : u"\u004C",
        u"\u1E37" : u"\u006C",
        u"\u1E38" : u"\u004C",
        u"\u1E39" : u"\u006C",
        u"\u1E3A" : u"\u004C",
        u"\u1E3B" : u"\u006C",
        u"\u1E3C" : u"\u004C",
        u"\u1E3D" : u"\u006C",
        u"\u1E3E" : u"\u004D",
        u"\u1E3F" : u"\u006D",
        u"\u1E40" : u"\u004D",
        u"\u1E41" : u"\u006D",
        u"\u1E42" : u"\u004D",
        u"\u1E43" : u"\u006D",
        u"\u1E44" : u"\u004E",
        u"\u1E45" : u"\u006E",
        u"\u1E46" : u"\u004E",
        u"\u1E47" : u"\u006E",
        u"\u1E48" : u"\u004E",
        u"\u1E49" : u"\u006E",
        u"\u1E4A" : u"\u004E",
        u"\u1E4B" : u"\u006E",
        u"\u1E4C" : u"\u004F",
        u"\u1E4D" : u"\u006F",
        u"\u1E4E" : u"\u004F",
        u"\u1E4F" : u"\u006F",
        u"\u1E50" : u"\u004F",
        u"\u1E51" : u"\u006F",
        u"\u1E52" : u"\u004F",
        u"\u1E53" : u"\u006F",
        u"\u1E54" : u"\u0050",
        u"\u1E55" : u"\u0070",
        u"\u1E56" : u"\u0050",
        u"\u1E57" : u"\u0070",
        u"\u1E58" : u"\u0052",
        u"\u1E59" : u"\u0072",
        u"\u1E5A" : u"\u0052",
        u"\u1E5B" : u"\u0072",
        u"\u1E5C" : u"\u0052",
        u"\u1E5D" : u"\u0072",
        u"\u1E5E" : u"\u0052",
        u"\u1E5F" : u"\u0072",
        u"\u1E60" : u"\u0053",
        u"\u1E61" : u"\u0073",
        u"\u1E62" : u"\u0053",
        u"\u1E63" : u"\u0073",
        u"\u1E64" : u"\u0053",
        u"\u1E65" : u"\u0073",
        u"\u1E66" : u"\u0053",
        u"\u1E67" : u"\u0073",
        u"\u1E68" : u"\u0053",
        u"\u1E69" : u"\u0073",
        u"\u1E6A" : u"\u0054",
        u"\u1E6B" : u"\u0074",
        u"\u1E6C" : u"\u0054",
        u"\u1E6D" : u"\u0074",
        u"\u1E6E" : u"\u0054",
        u"\u1E6F" : u"\u0074",
        u"\u1E70" : u"\u0054",
        u"\u1E71" : u"\u0074",
        u"\u1E72" : u"\u0055",
        u"\u1E73" : u"\u0075",
        u"\u1E74" : u"\u0055",
        u"\u1E75" : u"\u0075",
        u"\u1E76" : u"\u0055",
        u"\u1E77" : u"\u0075",
        u"\u1E78" : u"\u0055",
        u"\u1E79" : u"\u0075",
        u"\u1E7A" : u"\u0055",
        u"\u1E7B" : u"\u0075",
        u"\u1E7C" : u"\u0056",
        u"\u1E7D" : u"\u0076",
        u"\u1E7E" : u"\u0056",
        u"\u1E7F" : u"\u0076",
        u"\u1E80" : u"\u0057",
        u"\u1E81" : u"\u0077",
        u"\u1E82" : u"\u0057",
        u"\u1E83" : u"\u0077",
        u"\u1E84" : u"\u0057",
        u"\u1E85" : u"\u0077",
        u"\u1E86" : u"\u0057",
        u"\u1E87" : u"\u0077",
        u"\u1E88" : u"\u0057",
        u"\u1E89" : u"\u0077",
        u"\u1E8A" : u"\u0058",
        u"\u1E8B" : u"\u0078",
        u"\u1E8C" : u"\u0058",
        u"\u1E8D" : u"\u0078",
        u"\u1E8E" : u"\u0059",
        u"\u1E8F" : u"\u0079",
        u"\u1E90" : u"\u005A",
        u"\u1E91" : u"\u007A",
        u"\u1E92" : u"\u005A",
        u"\u1E93" : u"\u007A",
        u"\u1E94" : u"\u005A",
        u"\u1E95" : u"\u007A",
        u"\u1E96" : u"\u0068",
        u"\u1E97" : u"\u0074",
        u"\u1E98" : u"\u0077",
        u"\u1E99" : u"\u0079",
        u"\u1E9A" : u"\u0061",
        u"\u1E9B" : u"\u017F",
        u"\u1EA0" : u"\u0041",
        u"\u1EA1" : u"\u0061",
        u"\u1EA2" : u"\u0041",
        u"\u1EA3" : u"\u0061",
        u"\u1EA4" : u"\u0041",
        u"\u1EA5" : u"\u0061",
        u"\u1EA6" : u"\u0041",
        u"\u1EA7" : u"\u0061",
        u"\u1EA8" : u"\u0041",
        u"\u1EA9" : u"\u0061",
        u"\u1EAA" : u"\u0041",
        u"\u1EAB" : u"\u0061",
        u"\u1EAC" : u"\u0041",
        u"\u1EAD" : u"\u0061",
        u"\u1EAE" : u"\u0041",
        u"\u1EAF" : u"\u0061",
        u"\u1EB0" : u"\u0041",
        u"\u1EB1" : u"\u0061",
        u"\u1EB2" : u"\u0041",
        u"\u1EB3" : u"\u0061",
        u"\u1EB4" : u"\u0041",
        u"\u1EB5" : u"\u0061",
        u"\u1EB6" : u"\u0041",
        u"\u1EB7" : u"\u0061",
        u"\u1EB8" : u"\u0045",
        u"\u1EB9" : u"\u0065",
        u"\u1EBA" : u"\u0045",
        u"\u1EBB" : u"\u0065",
        u"\u1EBC" : u"\u0045",
        u"\u1EBD" : u"\u0065",
        u"\u1EBE" : u"\u0045",
        u"\u1EBF" : u"\u0065",
        u"\u1EC0" : u"\u0045",
        u"\u1EC1" : u"\u0065",
        u"\u1EC2" : u"\u0045",
        u"\u1EC3" : u"\u0065",
        u"\u1EC4" : u"\u0045",
        u"\u1EC5" : u"\u0065",
        u"\u1EC6" : u"\u0045",
        u"\u1EC7" : u"\u0065",
        u"\u1EC8" : u"\u0049",
        u"\u1EC9" : u"\u0069",
        u"\u1ECA" : u"\u0049",
        u"\u1ECB" : u"\u0069",
        u"\u1ECC" : u"\u004F",
        u"\u1ECD" : u"\u006F",
        u"\u1ECE" : u"\u004F",
        u"\u1ECF" : u"\u006F",
        u"\u1ED0" : u"\u004F",
        u"\u1ED1" : u"\u006F",
        u"\u1ED2" : u"\u004F",
        u"\u1ED3" : u"\u006F",
        u"\u1ED4" : u"\u004F",
        u"\u1ED5" : u"\u006F",
        u"\u1ED6" : u"\u004F",
        u"\u1ED7" : u"\u006F",
        u"\u1ED8" : u"\u004F",
        u"\u1ED9" : u"\u006F",
        u"\u1EDA" : u"\u004F",
        u"\u1EDB" : u"\u006F",
        u"\u1EDC" : u"\u004F",
        u"\u1EDD" : u"\u006F",
        u"\u1EDE" : u"\u004F",
        u"\u1EDF" : u"\u006F",
        u"\u1EE0" : u"\u004F",
        u"\u1EE1" : u"\u006F",
        u"\u1EE2" : u"\u004F",
        u"\u1EE3" : u"\u006F",
        u"\u1EE4" : u"\u0055",
        u"\u1EE5" : u"\u0075",
        u"\u1EE6" : u"\u0055",
        u"\u1EE7" : u"\u0075",
        u"\u1EE8" : u"\u0055",
        u"\u1EE9" : u"\u0075",
        u"\u1EEA" : u"\u0055",
        u"\u1EEB" : u"\u0075",
        u"\u1EEC" : u"\u0055",
        u"\u1EED" : u"\u0075",
        u"\u1EEE" : u"\u0055",
        u"\u1EEF" : u"\u0075",
        u"\u1EF0" : u"\u0055",
        u"\u1EF1" : u"\u0075",
        u"\u1EF2" : u"\u0059",
        u"\u1EF3" : u"\u0079",
        u"\u1EF4" : u"\u0059",
        u"\u1EF5" : u"\u0079",
        u"\u1EF6" : u"\u0059",
        u"\u1EF7" : u"\u0079",
        u"\u1EF8" : u"\u0059",
        u"\u1EF9" : u"\u0079"
        }


    def process_string(self, session, data):
        d = []
        # TODO: Horrifically slow implementation. Improve.
        if not data:
            return None
        for c in data:
            if (self.map.has_key(c)):
                d.append(self.map[c])
            else:
                d.append(c)
        return ''.join(d)
        

