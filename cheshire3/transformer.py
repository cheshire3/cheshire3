
from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Transformer, Record
from cheshire3.document import StringDocument
from cheshire3.utils import nonTextToken
from cheshire3.marc_utils import MARC

import os.path, time, re


class FilepathTransformer(Transformer):
    """ Returns record.id as an identifier, in raw SAX events. For use as the inTransformer of a recordStore """
    def process_record(self, session, rec):
        sax = ['1 identifier {}', '3 ' + str(rec.id), '2 identifier']
        data = nonTextToken.join(sax)
        return StringDocument(data)

# Simplest transformation ...
class XmlTransformer(Transformer):
    """ Return the raw XML string of the record """
    def process_record(self,session, rec):
        return StringDocument(rec.get_xml(session))


class SaxTransformer(Transformer):
    def process_record(self, session, rec):
        sax = [x.encode('utf8') for x in rec.get_sax(session)]
        sax.append("9 " + pickle.dumps(rec.elementHash))
        data = nonTextToken.join(sax)       
        return StringDocument(data)


class WorkflowTransformer(Transformer):
    """Transformer to execute a workflow."""
    
    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        self.workflow = self.get_path(session, 'workflow')
        
    def process_record(self, session, record):
        u"""Apply Workflow to the Record, return the resulting Document."""
        output = self.workflow.process(session, record)
        if isinstance(output, basestring):
            output = StringDocument(output)
        elif isinstance(output, Record):
            output = StringDocument(output.get_xml(session))
        
        return output

# --- XSLT Transformers ---

from lxml import etree

def myTimeFn(dummy):
    # call as <xsl:value-of select="c3fn:now()"/>
    # with c3fn defined as http://www.cheshire3.org/ns/function/xsl/
    return time.strftime("%Y-%m-%dT%H:%M:%SZ")
 

class LxmlXsltTransformer(Transformer):
    """XSLT transformer using Lxml implementation. Requires LxmlRecord.
    
    Use Record's resultSetItem's proximity information to highlight query term matches."""

    _possiblePaths = {'xsltPath' : {'docs' : "Path to the XSLT file to use."}}
    
    _possibleSettings = {'parameter' : {'docs' : "Parameters to be passed to the transformer."}}

    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        xfrPath = self.get_path(session, "xsltPath")
        dfp = self.get_path(session, "defaultPath")
        path = os.path.join(dfp, xfrPath)
        
        ns = etree.FunctionNamespace('http://www.cheshire3.org/ns/function/xsl/')
        ns['now'] = myTimeFn
        self.functionNamespace = ns
        self.parsedXslt = etree.parse(path)
        self.txr = etree.XSLT(self.parsedXslt)
        self.params = None
        parameter = self.get_setting(session, 'parameter', None)
        if (parameter):
            self.params = {}
            kv = parameter.split(' ')
            for pair in kv:
                (k, v) = pair.split(':')
                self.params[k] = '"%s"' % v
                

    def process_record(self, session, rec):
        # return StringDocument
        dom = rec.get_dom(session)
        if (session.environment == 'apache'):
            self.txr = etree.XSLT(self.parsedXslt)
            
        if self.params:
            result = self.txr(dom, **self.params)
        else:
            result = self.txr(dom)
        return StringDocument(str(result))


class LxmlQueryTermHighlightingTransformer(Transformer):
    """Query term highlighting transformer based on Lxml implementation. Abstract Class."""
    
    _possibleSettings = {'highlightTag': {'docs' : 'Tag to indicate highlighted section (will be inserted into output document as: <highlightTag>blah blah</highlightTag>)'}
                        ,'tagAttrList': {'docs': 'Space separated list of attribute name="value" pairs (will be inserted into output document as: <highlightTag name="value">blah blah</highlightTag>)'}
                        ,'breakElementsList': {'docs': 'Space separated list of element names to break at when tagging Query Terms. This can be useful when a speedy response is more important than complete tagging.'}
                        }
    
    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        htag = self.get_setting(session, 'highlightTag', None)
        if htag is None:
            self.highlightTag = 'c3:highlight'
            self.attrs = {'xmlns:c3': "http://www.cheshire3.org/schemas/highlight/"}
        else:
            self.highlightTag = htag 
            self.attrs = {}
        
        tagAttrs = self.get_setting(session, 'tagAttrList', None)
        if tagAttrs is not None:
            for attr in tagAttrs.split(' '):
                bits = attr.split('=', 1)
                k = bits[0]
                v = bits[1][1:-1]    # strip off "s
                self.attrs[k] = v
                
        self.breakElements = self.get_setting(session, 'breakElementsList', '').split(' ')
        

class LxmlPositionQueryTermHighlightingTransformer(LxmlQueryTermHighlightingTransformer):
    """Use word position from Record's resultSetItem's proximity information to highlight query term matches.
    
    Note Well: this can be unreliable when used in conjunction with stoplists."""

    def __init__(self, session, config, parent):
        raise NotImplementedError


class LxmlOffsetQueryTermHighlightingTransformer(LxmlQueryTermHighlightingTransformer):
    """Use character offsets from Record's resultSetItem's proximity information to highlight query term matches."""
    
    def __init__(self, session, config, parent):
        LxmlQueryTermHighlightingTransformer.__init__(self, session, config, parent)
        try:
            # try to get database's own version of RegexpFindOffsetTokenizer in case config is non-default
            db = session.server.get_object(session, session.database)
            self.wordRe = db.get_object(session, 'RegexpFindOffsetTokenizer').regexp
            del db
        except:
            self.wordRe = re.compile(u"""
              (?xu)                                            #verbose, unicode
              (?:
                [a-zA-Z0-9!#$%*/?|^{}`~&'+-=_]+@[0-9a-zA-Z.-]+ #email
               |(?:[\w+-]+)?[+-]/[+-]                          #alleles
               |\w+(?:-\w+)+(?:'(?:t|ll've|ll|ve|s|d've|d|re))?  #hypenated word (maybe 'xx on the end)
               |[$\xa3\xa5\u20AC]?[0-9]+(?:[.,:-][0-9]+)+[%]?  #date/num/money/time
               |[$\xa3\xa5\u20AC][0-9]+                        #single money
               |[0-9]+(?=[a-zA-Z]+)                            #split: 8am 1Million
               |[0-9]+%                                        #single percentage 
               |(?:[A-Z]\.)+[A-Z\.]                            #acronym
               |[oOd]'[a-zA-Z]+                                #o'clock, O'brien, d'Artagnan   
               |[a-zA-Z]+://[^\s]+                             #URI
               |\w+'(?:d've|d|t|ll've|ll|ve|s|re)              #don't, we've
               |(?:[hH]allowe'en|[mM]a'am|[Ii]'m|[fF]o'c's'le|[eE]'en|[sS]'pose)
               |[\w+]+                                         #basic words, including +
              )""")
        
    
    def process_record(self, session, rec):
        recDom = rec.get_dom(session)
        if (rec.resultSetItem is not None) and (rec.resultSetItem.proxInfo is not None) and (len(rec.resultSetItem.proxInfo) > 0):
            # munge proxInfo into more useable form
            proxInfo = rec.resultSetItem.proxInfo
            proxInfo2 = set()
            for pig in proxInfo:                               # for each group of proxInfo (i.e. from each query clause)
                for pi in pig:                                 # for each item of proxInfo: [nodeIdx, wordIdx, offset, termId(?)] NB termId from spoke indexes so useless to us :( 
                    proxInfo2.add('%d %d' % (pi[0], pi[2]))    # values must be strings for sets to work

            
            proxInfo = [map(int, pis.split(' ')) for pis in proxInfo2]
            nodeIdxs = []
            wordOffsets = []
            for x in sorted(proxInfo, reverse=True):            # sort proxInfo so that nodeIdxs are sorted descending (so that offsets don't get upset when modifying text)
                nodeIdxs.append(x[0])
                wordOffsets.append(x[1])

            xps = {}
            tree = recDom.getroottree()
            walker = recDom.getiterator()
            for x, n in enumerate(walker):
                if n.tag in self.breakElements:
                    break
                if x in nodeIdxs:
                    xps[x] = tree.getpath(n)
            
            for ni, offset in zip(nodeIdxs, wordOffsets):
                wordCount = 0
                if not ni in xps:
                    continue # no XPath - must be below dsc
                
                el = recDom.xpath(xps[ni])[0]
                located = None
                for ci, c in enumerate(el.iter(tag=etree.Element)): #ignore comments processing instructions etc.
                    if c.text:
                        text = c.text
                        if len(c.text) > offset:
                            start = offset
                            try: end = self.wordRe.search(text, start).end()
                            except: pass # well I still haven't found, what I'm looking for!
                            else:
                                if end == -1:
                                    end = len(text)
                                located = 'text'
                                hel = etree.Element(self.highlightTag)
                                hel.attrib.update(self.attrs)
                                if c.tag == hel.tag and c.attrib == hel.attrib:
                                    break
                                c.text = text[:start]
                                hel.text = text[start:end]
                                hel.tail = text[end:]
                                c.insert(0, hel)
                                break
                        else:
                            # adjust offset accordingly
                            offset -= len(text)
                        
                    if c != el and c.tail and located is None:
                        text = c.tail
                        if len(c.tail) > offset:
                            start = offset
                            try: end = self.wordRe.search(text, start).end()
                            except: pass # well I still haven't found, what I'm looking for!
                            else:
                                if end == -1:
                                    end = len(text)
                                located = 'tail'
                                hel = etree.Element(self.highlightTag)
                                hel.attrib.update(self.attrs)
                                if c.tag == hel.tag and c.attrib == hel.attrib:
                                    break
                                c.tail = text[:start]
                                hel.text = text[start:end]
                                hel.tail = text[end:]
                                p = c.getparent()
                                p.insert(ci, hel)
                                break
                        else:
                            # adjust offset accordingly
                            offset -= len(text)
        
        return StringDocument(etree.tostring(recDom))


class MarcTransformer(Transformer):
    """Transformer to converts records in marc21xml to marc records."""
    
    def __init__(self, session, config, parent):       
        Transformer.__init__(self, session, config, parent)
        self.session = session
    
    def _process_tagName(self, tagname):
        for i, c in enumerate(tagname):
            if c != '0':
                return int(tagname[i:])

    def process_record(self, session, rec):
        fields = {}
        tree = rec.get_dom(session)
        try:
            walker = tree.getiterator("controlfield")
        except AttributeError:
            # lxml 1.3 or later
            walker = tree.iter("controlfield")  
        for element in walker:
            tag = self._process_tagName(element.get('tag'))
            contents = element.text
            if tag in fields:
                fields[tag].append(contents)
            else:
                fields[tag] = [contents]
                
        try:
            walker = tree.getiterator("datafield")
        except AttributeError:
            # lxml 1.3 or later
            walker = tree.iter("datafield")  
        for element in walker:
            tag = self._process_tagName(element.get('tag'))
            try:
                children = element.getiterator('subfield')
            except AttributeError:
                # lxml 1.3 or later
                walker = element.iter('subfield') 
            subelements = [(c.get('code'), c.text) for c in children]
            contents = (element.get('ind1'), element.get('ind2'), subelements)         
            if tag in fields:
                fields[tag].append(contents)
            else:
                fields[tag] = [contents] 

        leader = tree.xpath('//leader')[0]
        l = leader.text
        fields[0] = [''.join([l[5:9], l[17:20]])]
        marcObject = MARC()
        marcObject.fields = fields
        return StringDocument(marcObject.get_MARC())

          

