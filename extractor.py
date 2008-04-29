
import re, types, string, copy
from baseObjects import Extractor

class SimpleExtractor(Extractor):
    """ Base extracter. Extracts exact text """

    _possibleSettings = {'extraSpaceElements' : {'docs' : "Space separated list of elements after which to append a space so as to not run words together."},
                         'prox' : {'docs' : ''},
                         'parent' : {"docs" : "Should the parent element's identifier be used instead of the current element."},
                         'reversable' : {"docs" : "Use a hopefully reversable identifier even when the record is a DOM tree. 1 = Yes (expensive), 0 = No (default)", 'type': int, 'options' : '0|1'},
                         'stripWhitespace' : {'docs' : 'Should the extracter strip leading/trailing whitespace from extracted text. 1 = Yes, 0 = No (default)', 'type' : int, 'options' : '0|1'},
                         
                         }

    def __init__(self, session, config, parent):
        Extractor.__init__(self, session, config, parent)
        self.spaceRe = re.compile('\s+')
        extraSpaceElems = self.get_setting(session, 'extraSpaceElements', '')
        self.extraSpaceElems = extraSpaceElems.split()
        self.strip = self.get_setting(session, 'stripWhitespace', 0)
        self.cachedRoot = None
        self.cachedElems = {}

    def _mergeHash(self, a, b):
        if not a:
            return b
        if not b:
            return a
        for k in b.iterkeys():
            try:
                a[k]['occurences'] += b[k]['occurences']
                try: 
                    # XXX Is this meaningful? Yes if extractor in chain
                    a[k]['positions'].extend(b[k]['positions'])
                except:
                    try:
                        a[k]['proxLoc'].extend(b[k]['proxLoc'])
                    except:
                        # Non prox
                        pass
            except:
                a[k] = b[k]
        return a

    def _flattenTexts(self, elem):
        texts = []
        if (hasattr(elem, 'childNodes')):
            # minidom/4suite
            for e in elem.childNodes:
                if e.nodeType == textType:
                    texts.append(e.data)
                elif e.nodeType == elementType:
                    # Recurse
                    texts.append(self._flattenTexts(e))
                    if e.localName in self.extraSpaceElems:
                        texts.append(' ')
        else:
            # elementTree/lxml
            try:
                walker = elem.getiterator()
            except AttributeError:
                # lxml 1.3 or later
                try: walker = elem.iter()
                except:
                    # lxml smart string object
                    return elem
            for c in walker:
                if c.text:
                    texts.append(c.text)
                if c.tag in self.extraSpaceElems:
                    texts.append(' ')
                if c.tail:
                    texts.append(c.tail)
                if c.tag in self.extraSpaceElems:
                    texts.append(' ')
        return ''.join(texts)

    def process_string(self, session, data):
        # Accept just text and extract bits from it.
        return {data: {'text' : data, 'occurences' : 1, 'proxLoc' : [-1]}}


    def _getProxLocNode(self, session, node):
        try:
            tree = node.getroottree()
        except AttributeError:
            # lxml smart string result?
            node = node.getparent()
            tree = node.getroottree()
            
        if self.get_setting(session, 'reversable', 0):
            root = tree.getroot()

            if root == self.cachedRoot:
                lno = self.cachedElems[node]
            else:
                lno = 0
                self.cachedRoot = root
                self.cachedElems = {}
                try: walker = tree.getiterator()
                except AttributeError:
                    # lxml 1.3 or later
                    walker = tree.iter()
                for n in walker:
                    self.cachedElems[n] = lno
                    lno += 1
                lno = self.cachedElems[node]
        else:
            lno = abs(hash(tree.getpath(node)))
        return lno


    def process_node(self, session, data):
        # Walk a DOM structure and extract
        txt = self._flattenTexts(data)
        # We MUST turn newlines into space or can't index
        txt = txt.replace('\n', ' ')
        txt = txt.replace('\r', ' ')
        if self.strip:
            txt = txt.strip()
        if self.get_setting(session, 'prox', 0):
            lno = self._getProxLocNode(session, data)
        else:
            lno = -1
        return {txt : {'text' : txt, 'occurences' : 1, 'proxLoc' : [lno]}}


    def _getProxLocEventList(self, session, events):
        if (self.get_setting(session, 'parent')):
            lno = int(events[0].split()[-3])
        else:
            lno = int(events[-1].split()[-1])
        return lno

    def process_eventList(self, session, data):
        # Step through a SAX event list and extract
        txt = []
        for e in data:
            if (e[0] == "3"):
                if (len(txt) and txt[-1][-1] != ' ' and repr(e[2]).isalnum()):
                    txt.append(' ')
                txt.append(e[2:])
        txt = ''.join(txt)
        if self.strip:
            txt = self.spaceRe.sub(' ', txt)

        if self.get_setting(session, 'prox', 0):
            lno = self._getProxLocEventList(session, data)
        else:
            lno = -1
        return {txt:{'text' : txt, 'occurences' : 1, 'proxLoc' : [lno]}}
    
    
    def process_xpathResult(self, session, data):
        new = {}
        for xp in data:
            for d in xp:
                if (type(d) == types.ListType):
                    # SAX event
                    new = self._mergeHash(new, self.process_eventList(session, d))
                elif (type(d) in types.StringTypes or type(d) in [int, long, float, bool]):
                    # Attribute content
                    new = self._mergeHash(new, self.process_string(session, d))
                else:
                    # DOM nodes
                    new = self._mergeHash(new, self.process_node(session, d))
        return new


class TeiExtractor(SimpleExtractor):


    def process_node(self, session, data):
        raise NotImplementedError
    

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
        
        if self.get_setting(session, 'prox', 0):
            lno = self._getProxLocEventList(session, data)
        else:
            lno = -1
        return {txt:{'text' : txt, 'occurences' : 1, 'proxLoc' : lno}}



class TaggedTermExtractor(SimpleExtractor):
    """Each term has been tagged in XML already, extract information."""
    

    def _getProxLocNode(self, session, node):
        try:
            return int(node.attrib.get('eid'))
        except:
            return 0

    def _flattenTexts(self, elem):
        # XXX This only implements LXML version
        texts = []
        ws = elem.xpath('.//toks/w')
        lastOffset = 10000000000
        totalOffset = 0
        thisOffset = 0
        for w in ws:
            bits = {}
            attr = w.attrib
            bits['text'] = w.text
            bits['pos'] = attr.get('p', '??')
            bits['stem'] = attr.get('s', w.text)
            o = int(attr.get('o', '-1'))
            if o < lastOffset:
                totalOffset += thisOffset
                thisOffset = len(w.xpath('../../txt/text()')[0]) + 1
            lastOffset = o
            o += totalOffset
            bits['offset'] = o
            texts.append("%(text)s/%(pos)s/%(stem)s/%(offset)s" % bits)
        return ' '.join(texts)

        

    def process_eventList(self, session, data):
        # Step through a SAX event list and extract
        txt = []
        wordOffs = []
        tagRe = re.compile('([\w]+)')
        attribRe = re.compile('({[^}]+})')
#        attribRe = re.compile('(\{[[\S]+\s[\S]+:\s[\S]+]*\})')
#        attribRe = re.compile('(\{[\S]+\s[\S]+:\s[\S]+[\s]?[\S]+\s[\S]+:\s[\S]+\})')
#        lastOffset = 10000000000
#        totalOffset = 0
#        thisOffset = 0
        currentOffset = 0
        previousOffset = -1
        firstOffset = -1
        spanStartOffset = 0
        wordCount = 0
        elem = None     
        previousText = ''
        bitsText = None  
        for i, e in enumerate(data): 
            bitsText = ''
            bitsOffset = None              
            if i == 0:
                a = re.search(attribRe, data[0])
                dictStr =  str(a.group())
                d = eval(dictStr)
                spanStartOffset = int(d[(None, 'offset')])   
                wordCount = int(d[(None, 'wordOffset')])
#                print 'qs offset'
#                print spanStartOffset      
            elif e[0] == "4" :
                m = re.search(tagRe, e.split()[3])
                if m.group() == 'w':
                    #get the text node for the w element
#                    print '++++++++++++++++++++'
                    el = data[i+1]
                    if el[0] == "3":
                        bitsText = el[2:] 
#                        print 'bitsText'
#                        print bitsText                              
                        if previousOffset == -1:
 #                           print 'no previous'
                            a = re.search(attribRe, e)
                            dictStr =  str(a.group())
                            d = eval(dictStr)
                            o = spanStartOffset
                            previousOffset = int(d[(None, 'o')])
#                            print 'previousOffset'
#                            print previousOffset
                            firstOffset = int(d[(None, 'o')])
#                            print 'firstOffset'
#                            print firstOffset
                        else:
                            a = re.search(attribRe, e)
                            dictStr =  str(a.group())
                            d = eval(dictStr)
                            currentOffset = int(d[(None, 'o')])
#                            print 'currentOffset'
#                            print currentOffset
#                            print 'previousOffset'
#                            print previousOffset
                            if currentOffset < previousOffset: 
#                                print 'adjusting offset'
#                                print 'old span start'
#                                print spanStartOffset
#                                print previousText
#                                print 'inter'
#                                print spanStartOffset + (previousOffset + len(previousText) + punctCount)-spanStartOffset
                                spanStartOffset = spanStartOffset + (((previousOffset + len(previousText) + punctCount)) - spanStartOffset) + (spanStartOffset - firstOffset)
#                                print '-----'
#                                print 'new span start'
#                                print spanStartOffset
                                o = spanStartOffset + currentOffset 
#                                print 'o'
#                                print o
                                firstOffset = 0
                            else:
                                o = spanStartOffset + (currentOffset - firstOffset)
                                #o = spanStartOffset + currentOffset
#                                print 'o'
#                                print o
                            previousOffset = currentOffset     
                        bitsOffset = o
                        bitsWord = wordCount
                        wordCount += 1
                        punctCount = 0
                        for j in range(i+1, len(data)):
                            if data[j][0] == "4":
                                m = re.search(tagRe, data[j].split()[3])
                                if m.group() == 'w' or m.group() == 's':
                                    break
                                if m.group() == 'n':                                 
                                    punctCount += len(data[j+1][2:])
                        

            if bitsText and bitsOffset:
                previousText = bitsText
                txt.append("%s/%s" % (bitsText, bitsOffset))
                wordOffs.append(bitsWord)

        txt = ' '.join(txt)
        
        if self.strip:
            txt = self.spaceRe.sub(' ', txt)

        if self.get_setting(session, 'prox', 0):
            lno = 0
        return {txt:{'text' : txt, 'occurences' : 1, 'proxLoc' : [lno], 'wordOffs' : wordOffs}}




class TemplateTermExtractor(SimpleExtractor):
    """Each term has been tagged in XML already, extract information."""

    _possibleSettings = {"template" : {'docs' : "template to return term as, after % substitution for names (eg via %(name)s)"},
                         "xpath" : {'docs' : "xpath to extract individual term"},
                         "subXpaths" : {'docs' : "space separated named fields:  name|xpath|default-if-not-present"}
                         }

    def __init__(self, session, config, parent):
        SimpleExtractor.__init__(self, session, config, parent)
        # default:  <w p="POS" s="STEM" o="OFFSET">TEXT</w>
        #     -->   TEXT/POS/STEM/OFFSET

        # XXX Can we xpathProcessor-ify these xpaths?
        # too computationally expensive to bother?
        xpaths = self.get_setting(session, 'subXpaths', 'word|./text()| pos|./@p|XX stem|./@s|./text() offset|./@o|-1')
        xps = xpaths.split(' ')
        self.xpaths = [x.split('|') for x in xps]
        self.xpath = self.get_setting(session, 'xpath', 'toks/w')
        self.template = self.get_setting(session, 'template', '%(word)s/%(pos)s/%(stem)s/%(offset)s')

    def _flattenTexts(self, elem):
        # XXX This only implements LXML version
        texts = []
        tmpl = self.template
        xps = self.xpaths
        ws = elem.xpath(self.xpath)
        for w in ws:
            bits = {}
            for xpi in xps:
                val = w.xpath(xpi[1])
                if not val:
                    if xpi[2][0] == '.':                        
                        val = w.xpath(xpi[2])
                    else:
                        val = xpi[2]
                if type(val) == list:
                    val = val[0]
                bits[xpi[0]] = val
            texts.append(tmpl % bits)
        return ' '.join(texts)
        
