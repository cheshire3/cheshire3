
from cheshire3.baseObjects import Extractor
from cheshire3.extractor import SimpleExtractor
import re, types, string, copy


class SpanXPathTaggedTermExtractor(SimpleExtractor):
    
    """Each term has been tagged in XML already (using the corpus transformer), extract information."""
    _possibleSettings = {"pos" : {'docs' : "do you want to extract part of speech (should be in attribute p)? 1|0"},
                         "stem" : {'docs' : "do you want to extract stem (should be in attribute s)? 1|0"},
                         "offset" : {'docs' : "do you want to extract offset (should be in attribute o)? 1|0"}
                         }
    
    #NB does not implement extraSpaceElements option but rather puts spaces between every tagged term.
    
    def __init__(self, session, config, parent):
        SimpleExtractor.__init__(self, session, config, parent)
        self.pos = self.get_setting(session, 'pos', 0)
        self.stem = self.get_setting(session, 'stem', 0)
        self.offset = self.get_setting(session, 'offset', 0)
        
        
    def _getProxLocNode(self, session, node):
        try:
            return int(node.attrib.get('eid'))
        except:
            return 0
        
        
    def process_xpathResult(self, session, data):
        new = {}
        root = None
        for xp in data:
            lastOffset = 10000000000
            totalOffset = 0
            thisOffset = 0
            lastLen = 0
            startNode = xp[0]
            endNode = xp[1]
            if root is None:
                for n in startNode.iterancestors():
                    root = n
            inrange = False
            text = []
            for el in root.iter():
                bits = {}
                if el.tag not in ['txt', '{%s}txt' % CONFIG_NS]:
                    if el == startNode:
                        inrange = True
                    elif el == endNode:
                        inrange = False
                        break
                    elif inrange == True and el.tag in ['w',
                                                        '{%s}w' % CONFIG_NS]:                        
                        if el.text is not None:
                            attr = el.attrib
                            bits['text'] = el.text
                            if self.pos:
                                bits['pos'] = attr.get('p', '??')
                            if self.stem:
                                bits['stem'] = attr.get('s', el.text)
                            if self.offset:
                                o = int(attr.get('o', '-1'))           
                                if o < lastOffset + lastLen:               
                                    totalOffset += thisOffset
                                    thisOffset = len(el.xpath('../../txt/text()')[0]) + 1
                                lastLen = len(el.text)
                                lastOffset = o
                                o += totalOffset
                            
                                bits['offset'] = o 
                                
                        output = [bits['text']]
                        if self.pos:
                            output.append('/%s' % bits['pos'])      
                        if self.stem:
                            output.append('/%s' % bits['stem'])
                        if self.offset:
                            output.append('/%s' % bits['offset'])
                        text.append(''.join(output))
                
            txt = ' '.join(text)    
            
            if self.get_setting(session, 'prox', 0):
                lno = self._getProxLocNode(session, startNode)
            else:
                lno = -1
            new = self._mergeHash(new, {txt : {'text' : txt, 'occurences' : 1, 'proxLoc' : [lno]}})                                 
        return new        
    
    


class TaggedTermExtractor(SimpleExtractor):
    """Each term has been tagged in XML already (using the corpus transformer), extract information."""
    
    _possibleSettings = {"pos" : {'docs' : "do you want to extract part of speech (should be in attribute p)? 1|0"},
                         "stem" : {'docs' : "do you want to extract stem (should be in attribute s)? 1|0"},
                         "offset" : {'docs' : "do you want to extract offset (should be in attribute o)? 1|0"}
                         }
    def __init__(self, session, config, parent):
        SimpleExtractor.__init__(self, session, config, parent)
        self.pos = self.get_setting(session, 'pos', 0)
        self.stem = self.get_setting(session, 'stem', 0)
        self.offset = self.get_setting(session, 'offset', 0)
        
        
    def _getProxLocNode(self, session, node):
        try:
            return int(node.attrib.get('eid'))
        except:
            return 0

    def _flattenTexts(self, elem):
        texts = []
        
        ws = elem.xpath('.//toks/w')
        lastOffset = 10000000000
        totalOffset = 0
        thisOffset = 0
        lastLen = 0
        for w in ws:
            bits = {}
            attr = w.attrib
            bits['text'] = w.text
            if self.pos:
                bits['pos'] = attr.get('p', '??')
            if self.stem:
                bits['stem'] = attr.get('s', w.text)
            if self.offset:
                o = int(attr.get('o', '-1'))           
                if o < lastOffset + lastLen:               
                    totalOffset += thisOffset
                    thisOffset = len(w.xpath('../../txt/text()')[0]) + 1
                lastLen = len(w.text)
                lastOffset = o
                o += totalOffset
            
                bits['offset'] = o
            output = [bits['text']]
            if self.pos:
                output.append('/%s' % bits['pos'])      
            if self.stem:
                output.append('/%s' % bits['stem'])
            if self.offset:
                output.append('/%s' % bits['offset'])
            texts.append(''.join(output))     
        return ' '.join(texts)

        

    def process_eventList(self, session, data):
        # Step through a SAX event list and extract
        txt = []
        wordOffs = []
        tagRe = re.compile('([\w]+)')
        attribRe = re.compile('({[^}]+})')
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
                try:
                    eid = int(d[(None, 'eid')])  
                except:
                    eid = 0
            elif e[0] == "4" :
                m = re.search(tagRe, e.split()[3])
                if m.group() == 'w':
                    #get the text node for the w element
                    el = data[i+1]
                    if el[0] == "3":
                        bitsText = el[2:]                              
                        if previousOffset == -1:
                            a = re.search(attribRe, e)
                            dictStr =  str(a.group())
                            d = eval(dictStr)
                            o = spanStartOffset
                            previousOffset = int(d[(None, 'o')])
                            firstOffset = int(d[(None, 'o')])
                        else:
                            a = re.search(attribRe, e)
                            dictStr =  str(a.group())
                            d = eval(dictStr)
                            currentOffset = int(d[(None, 'o')])
                            if currentOffset < previousOffset: 
                                spanStartOffset = spanStartOffset + (((previousOffset + len(previousText) + punctCount)) - spanStartOffset) + (spanStartOffset - firstOffset)
                                o = spanStartOffset + currentOffset 
                                firstOffset = 0
                            else:
                                o = spanStartOffset + (currentOffset - firstOffset)
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
                        
            if bitsText and not bitsOffset is None:
                previousText = bitsText
                txt.append("%s/%s" % (bitsText, bitsOffset))
                wordOffs.append(bitsWord)

        txt = ' '.join(txt)

        if self.strip:
            txt = self.spaceRe.sub(' ', txt)

        if self.get_setting(session, 'prox', 0):
            lno = eid
        else:
            lno = -1
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
        
