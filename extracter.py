
import re
from configParser import C3Object
from baseObjects import Extracter
from dateutil import parser as dateparser
import types
from utils import saxToString

class SimpleExtracter(Extracter):
    """ Base extracter. Extracts exact text """

    _possibleSettings = {'extraSpaceElements' : {'docs' : "Space separated list of elements after which to append a space so as to not run words together."}}

    def __init__(self, session, config, parent):
        Extracter.__init__(self, session, config, parent)
        self.spaceRe = re.compile('\s+')
        extraSpaceElems = self.get_setting(session, 'extraSpaceElements', '')
        self.extraSpaceElems = extraSpaceElems.split()


    def flattenTexts(self, elem):
        texts = []
        if (hasattr(elem, 'childNodes')):
            # minidom/4suite
            for e in elem.childNodes:
                if e.nodeType == textType:
                    texts.append(e.data)
                elif e.nodeType == elementType:
                    # Recurse
                    texts.append(self.flattenTexts(e))
                    if e.localName in self.extraSpaceElems:
                        texts.append(' ')
        else:
            # elementTree/lxml
            walker = elem.getiterator()
            for c in walker:
                if c.text:
                    texts.append(c.text)
                if c.tail:
                    texts.append(c.tail)
                if c.tag in self.extraSpaceElems:
                    texts.append(' ')
        return ''.join(texts)

    def process_string(self, session, data):
        # Accept just text and extract bits from it.
        return {data: {'text' : data, 'occurences' : 1}}

    def process_node(self, session, data):
        # Walk a DOM structure and extract
        txt = self.flattenTexts(data)
        txt = txt.replace('\n', ' ')
        txt = txt.strip()
        return {txt : {'text' : txt, 'occurences' : 1}}

    def process_eventList(self, session, data):
        # Step through a SAX event list and extract
        txt = saxToString(data)
        txt = self.spaceRe.sub(' ', txt)
        return {txt:{'text' : txt, 'occurences' : 1}}

    def _mergeHash(self, a, b):
        if not a:
            return b
        if not b:
            return a
        for k in b.keys():
            try:
                a[k]['occurences'] += b[k]['occurences']
                try:
                    a[k]['positions'].extend(b[k]['positions'])
                except:
                    # Non prox
                    pass
            except:
                a[k] = b[k]
        return a

    def process_xpathResult(self, session, data):
        new = {}
        for xp in data:
            for d in xp:
                if (type(d) == types.ListType):
                    # SAX event
                    new = self._mergeHash(new, self.process_eventList(session, d))
                elif (type(d) in types.StringTypes):
                    # Attribute content
                    new = self._mergeHash(new, self.process_string(session, d))
                else:
                    # DOM nodes
                    new = self._mergeHash(new, self.process_node(session, d))
        return new


class KeywordExtracter(SimpleExtracter):
    # Word consituent: a-zA-Z0-9 $%
    """ Extracts keywords from the text """

    _possibleSettings = {'regexp' : {"docs" : "Regular expression which matches non word constituent characters to be turned into whitespace before keyword extraction."}}
    
    def __init__(self, session, parser, config):
        SimpleExtracter.__init__(self, session, parser, config)
        # compiled regex is MUCH faster than interpreted loop
        # \u2026 is unicode ellipsis character
        # \u2014 is mdash, ndash is \u2013
        # smark apos are 2018, 2019
        # smart quotes are 201c 201d

        pre = self.get_setting(session, 'regexp', u"((?<!\s)'|[-.,]((?=\s)|$)|(^|(?<=\s))[-.,']|[\".,'-][\".,'-]|[~`!@+=\#\&\^*()\[\]{}\\\|\":;<>?/\u2026\u2013\u2014\u2018\u2019\u201c\u201d])")
        self.punctuationRe = re.compile(pre)

    def _keywordify(self, session, data):
        kw = {}
        reSub = self.punctuationRe.sub
        has = kw.has_key
        for d in data.keys():
            if d:
                s = reSub(' ', d)
                for t in s.split():
                    if has(t):
                        kw[t]['occurences'] += 1
                    else:
                        kw[t] = {'text' : t, 'occurences' : 1}
        return kw

    def process_string(self, session, data):
        data = SimpleExtracter.process_string(self, session, data)
        return self._keywordify(session, data)
    def process_node(self, session, data):
        data = SimpleExtracter.process_node(self, session, data)
        return self._keywordify(session, data)
    def process_eventList(self, session, data):
        data = SimpleExtracter.process_eventList(self, session, data)
        return self._keywordify(session, data)



class DateExtracter(SimpleExtracter):
    """ Extracts a single date. Multiple dates, ranges not yet implemented """
    """ Now extracts multiple dates, but slowly and less reliably. Ranges dealt with by DateRangeExtracter. JPH Jan '07"""

    _possibleDefaults = {'datetime' : {"docs" : "Default datetime to use for values not supplied in the data"}}
    _possibleSettings = {'fuzzy' : {"docs" : "Should the parser use fuzzy matching."}
                         , 'dayfirst' : {"docs" : "Is the day or month first, if not otherwise clear."}}

    def __init__(self, session, config, parent):
        SimpleExtracter.__init__(self, session, config, parent)
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
        tks = {}
        has = tks.has_key
        wds = data.split()
        while (len(wds)):
            for x in range(len(wds), 0, -1):
                try:
                    t = str(dateparser.parse(' '.join(wds[:x]).encode('utf-8'), default=self.default, dayfirst=self.dayfirst, fuzzy=self.fuzzy))
                except:
                    continue
                else:
                    if has(t): tks[t]['occurences'] += 1
                    else: tks[t] = {'text' : t, 'occurences' : 1}
                    break
            wds = wds[x:]
    
        return tks

    
    def _datify(self, session, data):
        # reconstruct data word by word and feed to parser?.
        # Must be a better way to do this
        # not sure, but I'll do that for now :p - JH
        data = data.keys()[0]
        data = self.isoDateRe.sub(self._convertIsoDates, data)        # separate ISO date elements with - for better recognition by date parser
        if len(data) and len(data) < 18 and data.find('-'):
            midpoint = len(data)/2
            if data[midpoint] == '-':
                # probably a range separated by -
                data = '%s %s' % (data[:midpoint], data[midpoint+1:])
                del midpoint
                
        return self._tokenize(data)

 
    def process_string(self, session, data):
        data = SimpleExtracter.process_string(self, session, data)
        return self._datify(session, data)
    def process_node(self, session, data):
        data = SimpleExtracter.process_node(self, session, data)
        return self._datify(session, data)
    def process_eventList(self, session, data):
        data = SimpleExtracter.process_eventList(self, session, data)
        return self._datify(session, data)


class RangeExtracter(SimpleExtracter):
    """ Extracts a range for use in RangeIndexes """
    
    def _rangify(self, session, data):
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
        
    def process_string(self, session, data):
        data = SimpleExtracter.process_string(self, session, data)
        return self._rangify(session, data)
    def process_node(self, session, data):
        data = SimpleExtracter.process_node(self, session, data)
        return self._rangify(session, data)
    def process_eventList(self, session, data):
        data = SimpleExtracter.process_eventList(self, session, data)
        return self._rangify(session, data)
    
    
class DateRangeExtracter(DateExtracter, RangeExtracter):
    """ Extracts a range of dates """
    
    def __init__(self, session, config, parent):
        DateExtracter.__init__(self, session, config, parent)
    
    def process_string(self, session, data):
        data = DateExtracter.process_string(self, session, data)
        return self._rangify(session, data)
    def process_node(self, session, data):
        data = DateExtracter.process_node(self, session, data)
        return self._rangify(session, data)
    def process_eventList(self, session, data):
        data = DateExtracter.process_eventList(self, session, data)
        return self._rangify(session, data)
    

class ProximityExtracter(KeywordExtracter):
    """ Extract keywords and maintain information for proximity searches """

    _possibleSettings = {'parent' : {"docs" : "Should the parent element's identifier be used instead of the current element."},
                         'reversable' : {"docs" : "Use a hopefully reversable identifier even when the record is a DOM tree. 1 = Yes (expensive), 0 = No (default)", 'type': int, 'options' : '0|1'}
                         }

    def __init__(self, session, config, parent):
        KeywordExtracter.__init__(self, session, config, parent)
        self.cachedElems = {}
        self.cachedRoot = None

    def process_string(self, session, data):
        kw = {}
        w = 0
        hash = {data: {'text' : data, 'occurences' : 1}}
        # Now keywordify with Prox
        reSub = self.punctuationRe.sub
        has = kw.has_key

        for d in hash.keys():
            if d:
                s = reSub(' ', d)
                for wd in s.split():
                    if has(wd):
                        kw[wd]['occurences'] += 1
                        kw[wd]['positions'].extend([-1, w])
                    else:
                        kw[wd] = {'text' : wd, 'occurences' : 1, 'positions' : [-1, w]}
                    w += 1
        return kw


    def process_node(self, session, data):
        node = data
        reversable = self.get_setting(session, 'reversable', 1)

        if reversable:
            tree = node.getroottree()
            root = tree.getroot()

            if root == self.cachedRoot:
                lno = self.cachedElems[node]
            else:
                lno = 0
                self.cachedRoot = root
                self.cachedElems = {}
                for n in tree.getiterator():
                    self.cachedElems[n] = lno
                    lno += 1
                lno = self.cachedElems[node]
        else:
            tree = node.getroottree()
            lno = abs(hash(tree.getpath(node)))
        w = 0

        kwhash = SimpleExtracter.process_node(self, session, data)
        # Now keywordify with Prox
        kw = {}
        reSub = self.punctuationRe.sub
        for d in kwhash.keys():
            if d:
                s = reSub(' ', d)
                for wd in s.split():
                    try:
                        kw[wd]['occurences'] += 1
                        kw[wd]['positions'].extend([lno, w])
                    except:
                        kw[wd] = {'text' : wd, 'occurences' : 1, 'positions' : [lno, w]}
                    w += 1
        return kw

    def process_eventList(self, session, data):
        # Treat parent element as line, not indexed element
        # EG map in  <map><attrType>1</attrType><attrVal>4</attrVal></map>
        # For attrType or attrVal

        if (self.get_setting(session, 'parent')):
            lno = int(data[0].split()[-3])
        else:
            lno = int(data[-1].split()[-1])
        w = 0

        hash = SimpleExtracter.process_eventList(self, session, data)
        # Now keywordify with Prox
        kw = {}
        reSub = self.punctuationRe.sub
        has = kw.has_key
        for d in hash.keys():
            if d:
                s = reSub(' ', d)
                for wd in s.split():
                    try:
                        kw[wd]['occurences'] += 1
                        kw[wd]['positions'].extend([lno, w])
                    except:
                        kw[wd] = {'text' : wd, 'occurences' : 1, 'positions' : [lno, w]}
                    w += 1
        return kw

# Useful for element proximity, or for pre-keywording normalisation

class ExactProximityExtracter(ProximityExtracter):
    """ Extract exact text with proximity information.  For example, to check nestedness/adjacency of elements """

    _possibleSettings = {'parent' : {"docs" : "Should the parent element's identifier be used instead of the current element."}}

    def process_string(self, session, data):
        return {data : {'text' : data,
                        'positions' : [-1, 0],
                        'occurences' : 1
                        }
                }

    def process_node(self, session, data):
        # need unique integer for this node.
        # generate full path to node, and hash()
        # UGLY!
        path = []
        node = data
        while True:
            parent = node.getparent()
            if not parent:
                break
            kids = parent.getchildren()
            idx = kids.index(node)
            path.append(idx)
            node = parent;
        pstr= '/'.join(map(str,path))
        lno = abs(hash(pstr))

        kwhash = SimpleExtracter.process_node(self, session, data)
        # Now keywordify with Prox
        for d in kwhash.keys():
            kwhash[d]['positions'] = [lno,0]
        return kwhash


    def process_eventList(self, session, data):
        # Treat parent element as line, not indexed element
        # EG map in  <map><attrType>1</attrType><attrVal>4</attrVal></map>
        # For attrType or attrVal
        parent = self.get_setting(session, 'parent')
        if (parent <> None):
            lno = int(data[0].split()[-3])
        else:
            lno = int(data[-1].split()[-1])

        txtList = []
        for e in data:
            if (e[0] == "3"):
                txtList.append(e[2:])
        txt = ''.join(txtList)
        return {txt : {'text' : txt,
                       'positions' : [lno, 0],
                       'occurences' : 1
                       }
                }





class NGramExtracter(SimpleExtracter):
    # Word consituent: a-zA-Z0-9 $%
    """ Extracts nGrams from the text """
   
    def __init__(self, session, parser, config):
        SimpleExtracter.__init__(self, session, parser, config)
        # compiled regex is MUCH faster than interpreted loop
        self.n = int(self.get_setting(session, 'nValue', 2))
        pre = self.get_setting(session, 'regexp', "((?<!\s)'|[-.,]((?=\s)|$)|(^|(?<=\s))[-.,']|[.,'-][.,'-]|[~`!@+=\#\&\^*()\[\]{}\\\|\":;<>?/])")
        self.punctuationRe = re.compile(pre)


    def _nGramExtract(self, session, data):
        kw = {}
        nGram = []
        reSub = self.punctuationRe.sub
        has = kw.has_key
        for d in data.keys():
            if d:
                s = reSub(' ', d)
                split = s.split()
                for i in range(len(split)-(self.n-1)):
                    nGram = split[i:(i+self.n)]
                    nGramStr = ' '.join(nGram)
                    if has(nGramStr):
                        kw[nGramStr]['occurences'] += 1
                    else:
                        kw[nGramStr] = {'text' : nGramStr, 'occurences' : 1}
        return kw

    def process_string(self, session, data):
        data = SimpleExtracter.process_string(self, session, data)
        return self._nGramExtract(session, data)
    def process_node(self, session, data):
        data = SimpleExtracter.process_node(self, session, data)
        return self._nGramExtract(session, data)
    def process_eventList(self, session, data):
        data = SimpleExtracter.process_eventList(self, session, data)
        return self._nGramExtract(session, data)



import string

class M804SimpleExtracter(SimpleExtracter):

    def process_eventList(self, session, data):
        # Step through a SAX event list and extract
        attrRe = re.compile("u['\"](.+?)['\"]: u['\"](.*?)['\"](, |})")
        txt = []
        # None == skip element.  Otherwise fn to call on txt
        processStack = []
        for e in data:
            if e[0] == "1":
                start = e.find("{")
                name = e[2:start-1]                
                if e[start+1] == '}':
                    attrs = {}
                else:
                    attrList = attrRe.findall(e)
                    attrs = {}
                    for m in attrList:
                        attrs[unicode(m[0])] = unicode(m[1])

                if name == "uc":
                    processStack.append((name, string.upper))
                elif name == "lc":
                    processStack.append((name, string.lower))
                elif name == "sic":
                    # replace contents with corr attribute
                    if attrs.has_key('corr'):
                        txt.append(attrs['corr'])
                    processStack.append((name, None))
                elif name == "p":
                    txt.append(' ')
                elif name == "abbr":
                    # replace contents with expan attribute
                    if attrs.has_key('expan'):
                        txt.append(attrs['expan'])
                    processStack.append((name, None))
                elif name == "figdesc":
                    processStack.append((name, None))
            elif (e[0] == "2"):                
                if processStack and processStack[-1][0] == e[2:len(processStack[-1][0])+2]:
                    processStack.pop()
            elif (e[0] == "3"):
                if (len(txt) and txt[-1] and txt[-1][-1] != ' ' and repr(e[2]).isalnum()):
                    txt.append(' ')
                bit = e[2:]
                if processStack:
                    if processStack[-1][1] == None:
                        continue
                    else:
                        bit = processStack[-1][1](bit)
                txt.append(bit)
        txt = ''.join(txt)
        txt = self.spaceRe.sub(' ', txt)
        txt = txt.replace('- ', '')

        return {txt:{'text' : txt, 'occurences' : 1}}

    
class M804KeywordExtracter(M804SimpleExtracter):
    # Word consituent: a-zA-Z0-9 $%
    """ Extracts keywords from the text """

    _possibleSettings = {'regexp' : {"docs" : "Regular expression which matches non word constituent characters to be turned into whitespace before keyword extraction."}}
    
    def __init__(self, session, parser, config):
        SimpleExtracter.__init__(self, session, parser, config)
        pre = self.get_setting(session, 'regexp', u"((?<!\s)'|[-.,]((?=\s)|$)|(^|(?<=\s))[-.,']|[\".,'-][\".,'-]|[~`!@+=\#\&\^*()\[\]{}\\\|\":;<>?/\u2026\u2013\u2014\u2018\u2019\u201c\u201d])")
        self.punctuationRe = re.compile(pre)

    def _keywordify(self, session, data):
        kw = {}
        reSub = self.punctuationRe.sub
        has = kw.has_key
        for d in data.keys():
            if d:
                s = reSub(' ', d)
                for t in s.split():
                    if has(t):
                        kw[t]['occurences'] += 1
                    else:
                        kw[t] = {'text' : t, 'occurences' : 1}
        return kw

    def process_string(self, session, data):
        data = M804SimpleExtracter.process_string(self, session, data)
        return self._keywordify(session, data)
    def process_node(self, session, data):
        data = M804SimpleExtracter.process_node(self, session, data)
        return self._keywordify(session, data)
    def process_eventList(self, session, data):
        data = M804SimpleExtracter.process_eventList(self, session, data)
        return self._keywordify(session, data)

