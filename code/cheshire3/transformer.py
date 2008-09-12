
from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Transformer
from cheshire3.document import StringDocument
from cheshire3.exceptions import ConfigFileException
from cheshire3.utils import nonTextToken
from cheshire3.utils import elementType, flattenTexts, nonTextToken

#from xml.sax.saxutils import escape
import os.path, time, types, re

from PyZ3950 import z3950, grs1
from PyZ3950.zmarc import MARC

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

# --- XSLT Transformers ---

from lxml import etree

def myTimeFn(dummy):
    # call as <xsl:value-of select="c3fn:now()"/>
    # with c3fn defined as http://www.cheshire3.org/ns/xsl/
    return time.strftime("%Y-%m-%dT%H:%M:%SZ")

class LxmlXsltTransformer(Transformer):
    """ XSLT transformer using Lxml implementation. Requires LxmlRecord """

    _possiblePaths = {'xsltPath' : {'docs' : "Path to the XSLT file to use."}}
    
    _possibleSettings = {'parameter' : {'docs' : "Parameters to be passed to the transformer."}}

    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        xfrPath = self.get_path(session, "xsltPath")
        dfp = self.get_path(session, "defaultPath")
        path = os.path.join(dfp, xfrPath)
        
        ns = etree.FunctionNamespace('http://www.cheshire3.org/ns/xsl/')
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


# --- GRS1 Transformers for Z39.50 ---

class GRS1Transformer(Transformer):
    """ Create representation of the XML tree in Z39.50's GRS1 format """

    # have to be called these due to SaxContentHandler regulations

    def initState(self):
        self.top = None
        self.nodeStack = []

    def startElement(self, name, attribs):
        node = z3950.TaggedElement()
        node.tagType = 3
        node.tagValue = ('string', name)
        node.content = ('subtree', [])

        for a in attribs:
            # Elements with Metadata
            anode = z3950.TaggedElement()
            md = z3950.ElementMetaData()
            anode.tagType = 3
            anode.tagValue = ('string', a)
            md.message = 'attribute'
            anode.metaData = md
            anode.content = ('octets', attribs[a])
            node.content[1].append(anode)

        if (self.nodeStack):
            self.nodeStack[-1].content[1].append(node)
        else:
            self.top = node
        self.nodeStack.append(node)

        
    def endElement(self, elem):
        if (self.nodeStack[-1].content[1] == []):
            self.nodeStack[-1].content = ('elementEmpty', None)
        self.nodeStack.pop()

    def characters(self, text, zero, length):
        if (self.nodeStack):
            if (text.isspace()):
                text = " "
            # pre-encode to utf8 to avoid charset/encoding headaches
            # eg these are now octets, not unicode
            text = text.encode('utf8')
            node = z3950.TaggedElement()
            node.tagType = 2
            node.tagValue = ('numeric', 19)
            node.content = ('octets', text)
            self.nodeStack[-1].content[1].append(node)


    def process_record(self, session, rec):
        p = self.permissionHandlers.get('info:srw/operation/2/transform', None)
        if p:
            if not session.user:
                raise PermissionException("Authenticated user required to transform using %s" % self.id)
            okay = p.hasPermission(session, session.user)
            if not okay:
                raise PermissionException("Permission required to transform using %s" % self.id)
        self.initState()
        try:
            rec.saxify(session, self)
        except AttributeError:
            saxp = session.server.get_object(session, 'SaxParser')
            saxRec = saxp.process_document(session, StringDocument(rec.get_xml(session)))
            saxRec.saxify(session, self)
        return StringDocument(self.top, self.id, rec.processHistory, parent=rec.parent)


class GrsMapTransformer(Transformer):
    """ Create a particular GRS1 instance, based on a configured map of XPath to GRS1 element. """

    def _handleConfigNode(self,session, node):
        if (node.localName == "transform"):
            self.tagset = node.getAttributeNS(None, 'tagset')
            maps = []
            for child in node.childNodes:
                if (child.nodeType == elementType and child.localName == "map"):
                    map = []
                    for xpchild in child.childNodes:
                        if (xpchild.nodeType == elementType and xpchild.localName == "xpath"):
                            map.append(flattenTexts(xpchild))
                    if map[0][0] != "#":
                        # vxp = verifyXPaths([map[0]])
                        vxp = [map[0]]
                    else:
                        # special case to process
                        vxp = [map[0]]
                    maps.append([vxp[0], map[1]])
            self.maps = maps

    def _handleLxmlConfigNode(self,session, node):
        if (node.tag == "transform"):
            self.tagset = node.attrib.get('tagset', '')
            maps = []
            for child in node.iterchildren(tag=etree.Element):
                if child.tag == 'map':
                    map = []                    
                    for xpchild in child.iterchildren(tag=etree.Element):
                        if xpchild.tag == "xpath":
                            map.append(flattenTexts(xpchild))
                    if map[0][0] != "#":
                        vxp = [map[0]]
                    else:
                        # special case to process
                        vxp = [map[0]]
                    maps.append([vxp[0], map[1]])
            self.maps = maps


    def __init__(self, session, config, parent):
        self.maps = []
        self.tagset = ""
        Transformer.__init__(self, session, config, parent)
    
    def _resolveData(self, session, rec, xpath):
        if xpath[0] != '#': 
            data = rec.process_xpath(session, xpath)
            try: data = ' '.join(data)
            except TypeError:
                # data isn't sequence, maybe a string or integer
                pass
            try:
                data = data.encode('utf-8')
            except:
                data = str(data)
        elif xpath == '#RELEVANCE#':
            data = rec.resultSetItem.scaledWeight
        elif xpath == '#RAWRELEVANCE#':
            data = rec.resultSetItem.weight
        elif xpath == '#DOCID#':
            data = rec.id
        elif xpath == '#RECORDSTORE#':
            data = rec.recordStore
        elif xpath == '#PROXINFO#':
            data = repr(rec.resultSetItem.proxInfo)
        elif xpath[:8] == '#PARENT#':
            # Get parent docid out of record
            try: 
                parent = rec.process_xpath(session, '/c3:component/@parent', {'c3':'http://www.cheshire3.org/'})[0]
            except IndexError:
                # probably no namespaces
                parent = rec.process_xpath(session, '/c3component/@parent')[0]
            parentStore, parentId = parent.split('/', 1)

            xtrapath = xpath[8:]
            if xtrapath:
                # actually get parent record to get stuff out of
                # TODO: not sure the best way to do this yet :(
                parentRec = self.parent.get_object(session, parentStore).fetch_record(session, parentId)
                # strip leading slash from xtra path data
                # N.B. double slash needed to root xpath to doc node (e.g. #PARENT#//root/somenode)
                if parentRec:
                    xtrapath = xtrapath[1:]
                    data = self._resolveData(session, parentRec, xtrapath)
            else:
                # by default just return id of parent record
                data = parentId
        return data

    
    def process_record(self, session, rec):
        elems = []
        for m in self.maps:
            (xpath, tagPath) = m
            node = z3950.TaggedElement()            
            data = self._resolveData(session, rec, xpath)
            node.content = ('string', str(data))
            node.tagType = 2
            node.tagValue = ('numeric', int(tagPath))
            elems.append(node)
        return StringDocument(elems, self.id, rec.processHistory, parent=rec.parent)


#converts records in marc21xml to marc records 
class MarcTransformer(Transformer):
    
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

          

