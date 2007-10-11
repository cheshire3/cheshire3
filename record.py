
from baseObjects import Record
from c3errors import C3Exception
import types, utils, os, re
from Ft.Xml.Domlette import implementation, Print
from cStringIO import StringIO
from xml.sax.saxutils import escape
from PyZ3950.zmarc_relaxed import MARC, MARC8_to_Unicode
from xml.sax import ContentHandler

from utils import Context, flattenTexts
import unicodedata

# 1 <name> <attrHash> parent predicate end
# Element
# 4 <as 1>
# Namespaced Element
# 2 <name> <startLine>
# End Element
# 5 <as 2>
# End Namespaced
# 3 <text>
# Characters
# 9 <element hash>
# pickled hash of locations

# Split to separate object to allow for DOM->SAX direct conversion
# by throwing events from DOM tree to handler.
class SaxContentHandler(ContentHandler):
    currentText = []
    currentPath = []
    pathLines = []
    currentLine = -1
    recordWordCount = 0
    elementHash = {}
    namespaces = []
    hashAttributesNames = {}
    hashAttributes = []
    stripWS = 0
    saveElementIndexes = 1

    def __init__(self):
        self.saveElementIndexes = 1
        self.hashAttributesNames = {}
        self.hashAttributes = []
        self.stripWS = 0
        self.reinit()

    def reinit(self):
        self.currentText = []
        self.currentPath = []
        self.pathLines = []
        self.currentLine = -1
        self.recordWordCount = 0
        self.elementHash = {}
        self.elementIndexes = []
        self.namespaces = []

    def startPrefixMapping(self, pfx, uri):
        self.currentLine += 1
        if (pfx == None):
            pfx = ''
        self.currentText.append("6 %r, %r" % (pfx, uri))
        
    # We want to fwd elems to NS elem handlers with default NS?
    def startElement(self, name, attrs):
        self.currentLine += 1
        self.pathLines.append(self.currentLine)
        try:
            parent = self.pathLines[-2]
        except IndexError:
            parent = -1
        attrHash = {}
        if (attrs):
            for k in attrs.keys():
                attrHash[k] = escape(attrs[k])

        try:
            npred = self.elementIndexes[-1][name] + 1
            self.elementIndexes[-1][name] += 1
        except IndexError:
            # Empty
            npred = 1
            self.elementIndexes = [{name: npred}]
        except KeyError:
            # First occurence of Element
            npred = 1
            self.elementIndexes[-1][name] = 1
        except:
            print (name, self.elementIndexes)
            raise
        self.elementIndexes.append({})
        self.currentText.append("1 %s %s %d %d" % (name, repr(attrHash), parent, npred))
        saveAttrs = []
        try:
            hashAttrList = self.hashAttributesNames[name]
            for a in hashAttrList:
                try:
                    saveAttrs.append("%s[@%s='%s']" % (name, a, attrHash[a]))
                except:
                    pass
        except:
            pass
        try:
            starAttrList = self.hashAttributesNames['*']
            for a in starAttrList:
                try:
                    saveAttrs.append("*[@%s='%s']" % (a, attrHash[a]))
                except:
                    pass
        except:
            pass
        if saveAttrs:
            self.hashAttributes.append((self.currentLine, saveAttrs))



    def endElement(self, name):
        self.currentLine += 1
        start = self.pathLines.pop()
        self.currentText.append("2 %s %d" % (name, start))
        self.currentText[start] = "%s %d" % (self.currentText[start], self.currentLine)
        self.elementIndexes.pop()
        try:
            self.elementHash[name].append([start, self.currentLine])
        except:
            self.elementHash[name] = [[start, self.currentLine]]        
        if self.hashAttributes and self.hashAttributes[-1][0] == start:
            attrs = self.hashAttributes.pop()[1]
            for sa in attrs:
                try:
                    self.elementHash[sa].append([start, self.currentLine])
                except:
                    self.elementHash[sa] = [[start, self.currentLine]]

    def startElementNS(self, name, qname, attrs):
        self.currentLine += 1
        self.pathLines.append(self.currentLine)
        try:
            parent = self.pathLines[-2]
        except:
            parent = -1
        attrHash = {}
        # Convert from weird sax thing
        if (attrs):
            for k in attrs.keys():
                attrHash[k] = attrs[k]

        simpleName = name[1]
        try:
            npred = self.elementIndexes[-1][simpleName] + 1
            self.elementIndexes[-1][simpleName] += 1
        except IndexError:
            # Empty
            npred = 1
            self.elementIndexes = [{simpleName: npred}]
        except KeyError:
            # First occurence of Element
            npred = 1
            self.elementIndexes[-1][simpleName] = 1
        self.elementIndexes.append({})

        self.currentText.append("4 %r, %r, %r, %r %d %d" % (name[0], simpleName, qname, attrHash, parent, npred))

        saveAttrs = []
        try:
            hashAttrList = self.hashAttributesNames[simpleName]
            for a in hashAttrList:
                try:
                    saveAttrs.append("%s[@%s='%s']" % (simpleName, a, attrHash[a]))
                except:
                    pass
        except:
            pass
        try:
            starAttrList = self.hashAttributesNames['*']
            for a in starAttrList:
                try:
                    saveAttrs.append("*[@%s='%s']" % (a, attrHash[a]))
                except:
                    pass
        except:
            pass
        if saveAttrs:
            self.hashAttributes.append((self.currentLine, saveAttrs))
        

    def endElementNS(self, name, qname):
        self.currentLine += 1
        start = self.pathLines.pop()        
        self.currentText.append("5 %r, %r, %r %d" % (name[0], name[1], qname, start))
        self.currentText[start] ="%s %d" % (self.currentText[start], self.currentLine)
        self.elementIndexes.pop()
        try:
            self.elementHash[name[1]].append([start, self.currentLine])
        except:
            self.elementHash[name[1]] = [[start, self.currentLine]]
        if self.hashAttributes and self.hashAttributes[-1][0] == start:
            attrs = self.hashAttributes.pop()[1]
            for sa in attrs:
                try:
                    self.elementHash[sa].append([start, self.currentLine])
                except:
                    self.elementHash[sa] = [[start, self.currentLine]]

    def characters(self, text, start=0, length=-1):
        # if text.isspace():
        #     text = " "            
        prev = self.currentText[-1]
        if self.stripWS and text.isspace():
            return
        self.currentLine += 1
        if (len(text) != 1 and len(prev) != 3 and prev[0] == "3" and not prev[-1] in [' ', '-']):
            # Adjacent lines of text, ensure spaces
            text = ' ' + text            
        self.currentText.append("3 %s" % (text))        
        self.recordWordCount += len(text.split())
        
    def ignorableWhitespace(self, ws):
        # ... ignore! :D
        pass
                    
    def processingInstruction(self, target, data):
        pass
    def skippedEntity(self, name):
        pass
    
class SaxToDomHandler:
    nodeStack = []
    document = None
    currText = ""

    def initState(self):
        self.nodeStack = []
        self.document=None
        self.top = None
        
    def startElement(self, name, attribs={}):
        if (not self.document):
            self.document = implementation.createDocument(None, name, None)
            elem = self.document.childNodes[0]
        else:
            elem = self.document.createElementNS(None,name)
        for a in attribs:
            elem.setAttributeNS(None,a,attribs[a])
        if (self.nodeStack):
            self.nodeStack[-1].appendChild(elem)
        else:
            self.document.appendChild(elem)
        self.nodeStack.append(elem)
        
    def endElement(self, foo):
        self.nodeStack.pop()

    def characters(self, text, zero=0, length=0):
        if (self.nodeStack):
            if (text.isspace()):
                text = " "
            # Is this escape necessary?
            text = escape(text)
            d = self.document.createTextNode(text)
            self.nodeStack[-1].appendChild(d)

    def startElementNS(self, name, qname, attribs):
        if (not self.document):
            self.document = implementation.createDocument(name[0], name[1], None)
            elem = self.document.childNodes[0]
        else:
            elem = self.document.createElementNS(name[0],name[1])

        for a in attribs:
            elem.setAttributeNS(a[0],a[1],attribs[a])
        if (self.nodeStack):
            self.nodeStack[-1].appendChild(elem)
        else:
            self.document.appendChild(elem)
        self.nodeStack.append(elem)

    def endElementNS(self, name,qname):
        self.nodeStack.pop()
        
    def startPrefixMapping(self, pref, uri):
        pass

    def getRootNode(self):
        return self.document

s2dhandler = SaxToDomHandler()

class SaxToXmlHandler:
    xml = []
    currNs = 0
    newNamespaces = {}

    def initState(self):
        self.xml = []
        self.namespaces = {}
        self.currNs = 0
        self.newNamespaces = {}
        
    def startPrefixMapping(self, pref, uri):
        self.namespaces[uri] = pref
        self.newNamespaces[pref] =  uri

    def startElement(self, name, attribs={}):
        attrs = []
        for a in attribs:
            attrs.append('%s="%s"' % (a, attribs[a]))
        attribtxt = ' '.join(attrs)
        if (attribtxt):
            attribtxt = " " + attribtxt
        self.xml.append("<%s%s>" % (name, attribtxt))
        
    def endElement(self, name):
        self.xml.append("</%s>" % (name))

    def _getPrefix(self, ns):
        if (not ns):
            return ""
        pref = self.namespaces.get(ns, None)
        if (pref == None):
            self.currNs += 1
            pref = "ns%d" % (self.currNs)
            self.namespaces[ns] = pref
            self.newNamespaces[pref] = ns
        return pref

    def startElementNS(self, n, qn=None, attrs={}):
        pref = self._getPrefix(n[0])
        if (pref):
            name = "%s:%s" % (pref, n[1])
        else:
            name = n[1]
        attrlist = []
        for ns,aname in attrs:
            p2 = self._getPrefix(ns)
            if (p2):
                nsaname = "%s:%s" % (p2, aname)
            else:
                nsaname = aname
            attrlist.append('%s="%s"' % (nsaname, attrs[(ns,aname)]))
        for x in self.newNamespaces.items():
            if (x[0]):
                attrlist.append('xmlns:%s="%s"' % (x[0], x[1]))
            else:
                attrlist.append('xmlns="%s"' % (x[1]))
        self.newNamespaces = {}
        attribtxt = ' '.join(attrlist)
        if (attribtxt):
            attribtxt = " " + attribtxt
        self.xml.append("<%s%s>" % (name,attribtxt))
        
    def endElementNS(self, n, qn=None):
        pref = self._getPrefix(n[0])
        if (pref):
            name = "%s:%s" % (pref, n[1])
        else:
            name = n[1]
        self.xml.append("</%s>" % (name))
        
    def characters(self, text, zero=0, length=0):
        text = escape(text)
        self.xml.append(text)

    def get_raw(self):
        return ''.join(self.xml)


s2xhandler = SaxToXmlHandler()


class NumericPredicateException(C3Exception):
    pass



class DomRecord(Record):
    context = None
    size = 0    

    def __init__(self, domNode, xml="", docid=None):
        self.dom = domNode
        self.xml = xml
        self.id = docid
        self.parent = ('','',-1)
        self.context = None
        try:
            # Sometimes this blows up
            self.wordCount = len(flattenTexts(domNode).split())
        except:
            self.wordCount = 0
        self.byteCount = 0


    def _walk(self, node):
        pass

    def get_sax(self):
        if (not self.sax):
            self.handler = SaxContentHandler()
            for c in self.dom.childNodes:
                self._walkTop(c)
            self.sax = self.handler.currentText
            self.sax.append("9 %r" % self.handler.elementHash)
            self.handler = None            
        return self.sax

    def get_dom(self):
        return self.dom

    def fetch_vector(self, session, index, summary=False):
        return index.indexStore.fetch_vector(session, index, self, summary)


class MinidomRecord(DomRecord):
    useNamespace = 1

    def get_xml(self):
        if (self.xml):
            return self.xml
        else:
            self.xml = self.dom.toxml()
            return self.xml

    def _walkTop(self, node):
        # top level node
        if node.nodeType == utils.elementType:
            self.namespaces = node.namespaceURI != None
            self._walk(node)
        
    def _walk(self, node):
        if (node.nodeType == utils.elementType):
            name = node.localName
            ns = node.namespaceURI
            attrHash = {}
            for ai in range(node.attributes.length):
                attr = node.attributes.item(ai)                
                if self.namespaces:
                    if attr.namespaceURI == 'http://www.w3.org/2000/xmlns/':
                        self.handler.startPrefixMapping(attr.localName, attr.value)
                    else:
                        attrHash[(attr.namespaceURI, attr.localName)] = attr.value
                else:
                    attrHash[attr.localName] = attr.value
            if self.namespaces:
                self.handler.startElementNS((node.namespaceURI, node.localName), None, attrHash)
            else:
                self.handler.startElement(node.localName, attrHash)
            for c in node.childNodes:
                self._walk(c)
            if self.namespaces:
                self.handler.endElementNS((node.namespaceURI, node.localName), None)
            else:
                self.handler.endElement(node.localName)
        elif node.nodeType == utils.textType:
            self.handler.characters(node.data)
            
    def process_xpath(self, tuple, maps={}):
        raise NotImplementedError

class FtDomRecord(DomRecord):

    def get_xml(self):
        if (self.xml):
            return self.xml
        else:
            stream = StringIO()
            Print(self.dom, stream)
            stream.seek(0)
            self.xml = stream.read()
            return self.xml


    def process_xpath(self, tuple, maps={}):
        xp = tuple[0]
        if (not self.context):
            self.context = Context.Context(self.dom)
        return xp.evaluate(self.context)

try:
    from lxml import etree, sax
    class LxmlRecord(DomRecord):

        def process_xpath(self, xpath, maps={}):
            global prefixRe
            if (isinstance(xpath, list)):
                xpath = repr(xpath[0])
            if xpath[0] != "/" and xpath[-1] != ')':
                xpath = "//" + xpath
            if maps:
        		return self.dom.xpath(xpath, maps)
    	    else:
                return self.dom.xpath(xpath)

        def get_xml(self):
            return etree.tostring(self.dom)

        def get_sax(self):
            if (not self.sax):
                handler = SaxContentHandler()
                sax.saxify(self.dom, handler)
                self.sax = handler.currentText
                self.sax.append("9 %r" % handler.elementHash)
            return self.sax

except:
    class LxmlRecord(DomRecord):
        pass


class SaxRecord(Record):

    def __init__(self, saxList, xml="", docid=None, wordCount=0, byteCount=0):
        self.sax = saxList
        self.id = docid
        self.xml = xml
        self.history = []
        self.rights = []
        self.elementHash = {}
        self.wordCount = wordCount
        self.byteCount = byteCount
        self.parent = ('','',-1)
        self.attrRe = re.compile("u['\"](.+?)['\"]: u['\"](.*?)['\"](, |})")
        #self.attrRe = re.compile("u(?P<quote>['\"])(.+?)(?P=quote): u(?P<quoteb>['\"])(.*?)(?P=quoteb)(, |})")
        self.recordStore = ""

        
    def process_xpath(self, xpTuple, maps={}):
        if (not isinstance(xpTuple, list)):
            # Raw XPath
            c = utils.verifyXPaths([xpTuple])
            if (not c or not c[0][1]):
		print "BAD XPATH"
		return []
            else:
                xpTuple = c[0]

        xp = xpTuple[1]
        try:
            flatten = 0
            if xp[0][0] == "FUNCTION" and xp[0][1] == 'count':
                # process xpath and return number of matches
                if isinstance(xp[0][2][0], str) and xp[0][2][0] != '/':
                    data = self.process_xpath([None, [xp[0][2]]], maps)
                else:
                    data = self.process_xpath([None, xp[0][2]], maps)
                    
                return len(data)

            if (xp[-1][0] == 'child' and xp[-1][1] == "__text()"):
                flatten = 1
                xp = xp[:-1]

            if (xp[-1][0] == 'attribute'):
                return self._handleAttribute(xp, maps)
            elif (xp[-1][0] == "/"):
                # Return top level element
                for x in range(len(self.sax)):
                    if self.sax[x][0] in ['1', '4']:
                        return self.sax[x:]                                    
            elif(xp[-1][0] in ['child', 'descendant']):
                data = []
                # Extracting element
                elemName = xp[-1][1]

                nselem = elemName.split(":")
                if (len(nselem) == 2):
                    # Namespaced.
                    nsUri = maps[nselem[0]]
                    elemName = nselem[1]
                else:
                    nsUri = ""

                attr = xp[-1][2]
                elemLines = []
                if elemName == '*' and attr:
                    for p in attr:
                        if p[0] == 'FUNCTION' and p[2] == '__name()':
                            names = self.elementHash.keys()                            
                            if p[1] == 'starts-with' and p[2] == '__name()':
                                for x in names:
                                    if x.find(p[3]) == 0:
                                        elemLines.extend(self.elementHash[x])
                            elif p[1] == 'regexp' and p[2] == '__name()':
                                for x in names:
                                    if p[3].search(x):
                                        elemLines.extend(self.elementHash[x])
                elif (not self.elementHash.has_key(elemName)):
		    return []

                if (len(attr) == 1 and type(attr[0]) == types.ListType and attr[0][1] == "="):
                    n = u"%s[@%s='%s']" % (elemName, attr[0][0], attr[0][2])
                    elemLines = self.elementHash.get(n, [])

                if elemLines == []:
                    try:
                        elemLines = self.elementHash[elemName]
                    except:
                        # might really be empty
                        pass
                for e in elemLines:
                    if (not nsUri or self.sax[e[0]][4:4+len(nsUri)] == nsUri):
                        match = self._checkSaxXPathLine(xp, e[0])
                        if (match):
                            # Return event chunk
                            l = self.sax[e[0]]
                            end = int(l[l.rfind(' ')+1:])
                            data.append(self.sax[e[0]:end+1])                        
            else:
                # Unsupported final axis
                raise(NotImplementedError)

            if flatten and data:
                # Flatten to text nodes
                ndata = []
                for match in data:
                    txt = []
                    for ev in match:
                        if ev[0] == '3':
                            txt.append(ev[2:])
                    ndata.append(''.join(txt))
                return ndata
            else:
                return data
        except NotImplementedError:
            # Convert to DOM (slow) and reapply (slower still)
            dom = self.get_dom()
            xp = xpTuple[0]
            try:
		return utils.evaluateXPath(xp, dom)
            except:
                print "Buggy Xpath!..."
                return []
        # Otherwise just fall over as we've hit a real bug


    def _handleAttribute(self, xp, maps={}):
        attrName = xp[-1][1]
        nselem = attrName.split(":")
        if (len(nselem) == 2):
            # Namespaced attribute
            nsUri = maps[nselem[0]]
            attrName = nselem[1]
        else:
            nsUri = None

        data = []

        if (len(xp) == 1):
            # Extracting all occs of attribute anywhere!?
            # Check predicates... (only support one numeric predicate)
            if (len(xp[0][2]) == 1 and type(xp[0][2][0]) == types.FloatType):
                nth = int(xp[0][2][0])
            elif (len(xp[0][2])):
                # Non index or multiple predicates??
                raise(NotImplementedError)
            else:
                nth = 0

            currn = 0
            for l in self.sax:
                if (l[0] == "1"):
                    (name, attrs) = self._convert_elem(l)
                    if (attrs.has_key(attrName)):
                        currn += 1
                        content = attrs[attrName]
                        if (currn == nth):
                            data.append(content)
                            break
                        elif (not nth):
                            data.append(content)
                                
        else:
            elemName = xp[-2][1]
            flatten = 0
            if (elemName == "*"):
                # Let DOM code handle this monstrosity :P
                raise(NotImplementedError)

            nselem = elemName.split(":")
            if (len(nselem) == 2):
                # Namespaced.
                elemNsUri = maps[nselem[0]]
                elemName = nselem[1]
            else:
                elemNsUri = ""

            if (self.elementHash.has_key(elemName)):
                elemLines = self.elementHash[elemName]
                for e in elemLines:
                    if (not elemNsUri or self.sax[e[0]][4:4+len(elemNsUri)] == elemNsUri):
                        line = self.sax[e[0]]
                        (name, attrs) = self._convert_elem(line)
                        if (attrName == '*'):
                            # All attributes' values
                            match = self._checkSaxXPathLine(xp[:-1], e[0])
                            if (match):
                                for k in attrs.keys():
                                    data.append(attrs[k])
                        else:
                            if (not attrs.has_key(attrName)):
                                attrName = (nsUri, attrName)
                            if (not attrs.has_key(attrName) and not nsUri):
                                # step through and take first
                                content = None
                                for key in attrs:
                                    if key[1] == attrName[1]:
                                        content = attrs[key]
                            else:
                                content = attrs.get(attrName, None)
                                if (content):
                                    # Now check rest of path
                                    match = self._checkSaxXPathLine(xp[:-1], e[0])
                                    if (match):
                                        data.append(content)
        
        return data

    def _checkSaxXPathLine(self, xp, line):
        # Check that event at line in record matches xpath up tree
        # Pass by reference, need a copy to pop! Looks like a hack...
        xpath = xp[:]
        climb = False
        while (xpath):
            posn = len(xpath)
            node = xpath.pop()
            if (line == -1):
               if node != "/" and node != ['/']:
                    return 0
            else:
                elem = self.sax[line]
                (name, attrs) = self._convert_elem(elem)
                match = self._checkSaxXPathNode(node, name, attrs, line, posn)
                if not match:
                    if not climb:
                        return 0
                    else:
                        # Previous was a descendant, keep looking
                        while not match:
                            start = elem.rfind("}") + 2
                            end = elem.find(" ", start)
                            line = int(elem[start:end])
                            if line != -1:
                                elem = self.sax[line]                            
                                (name, attrs) = self._convert_elem(elem)
                                match = self._checkSaxXPathNode(node, name, attrs, line, posn)
                            else:
                                return 0
                                
                if xpath:
                    start = elem.rfind("}") + 2
                    end = elem.find(" ", start)
                    line = int(elem[start:end])
                climb = (node and node[0] == "descendant")
                
        return 1


    def _checkSaxXPathNode(self, step, name, attrs, line, posn):
        # name already checked, strip
        if step in ['/', ['/']] and name:
            return 0
        if (step[1] <> name and step[1] <> '*' and step[1][step[1].find(":")+1:] <> name):
            return 0
        elif (not step[0] in ['child', 'descendant']):
            # Unsupported axis
            raise(NotImplementedError)
        elif (step[2]):
            # Check predicates
            predPosn = 0
            for pred in (step[2]):
                predPosn += 1
                m = self._checkSaxXPathPredicate(pred, name, attrs, line, posn, predPosn)
                if (not m):
                    return 0
        return 1

    def _checkSaxXPathPredicate(self, pred, name, attrs, line, posn, predPosn):

        if (type(pred) != types.ListType):
            # Numeric Predicate. (eg /foo/bar[1])
            if (predPosn != 1):
                # Can't do numeric predicate on already predicated nodeset
                # eg:  text[@type='main'][2]
                raise(NotImplementedError)

            if (posn == 1):
                # First position in relative path.
                # Check against position in elementHash
                if (self.elementHash.has_key(name)):
                    all = self.elementHash[name]
                    p = int(pred)
                    if (len(all) < p):
                        return 0
                    return all[int(pred)-1][0] == line
                return 0
            else:
                # Not first position, so it applies to parent elem
                # Which we record during parsing
                elem = self.sax[line]
                end = elem.rfind("}") + 2
                start = elem.find(' ', end) + 1
                end = elem.find(' ', start)
                npred = float(elem[start:end])
                return npred == pred
        elif (pred[1] in ['=', '!=', '<', '>', '<=', '>=']):
            # Single attribute
            return self._checkSaxXPathAttr(pred, attrs)
        elif (pred[1] in ['and', 'or']):
            # Attribute combinations
            left = self._checkSaxXPathPredicate(pred[0], name, attrs, line, posn, predPosn)
            right = self._checkSaxXPathPredicate(pred[2], name, attrs, line, posn, predPosn)
            if (pred[1] == 'and' and left and right):
                return 1
            elif (pred[1] == 'or' and (left or right)):
                return 1
            return 0
        elif (pred[0] == 'attribute'):
            # Attribute exists test
            return attrs.has_key(pred[1])
        elif (pred[0] == 'FUNCTION'):
            if pred[2] == "__name()":
                return True
            if pred[1] == 'starts-with':
                if attrs.has_key(pred[2]):
                    val = attrs[pred[2]]
                    return not val.find(pred[3])
                else:
                    return False
            elif pred[1] == 'regexp':
                if attrs.has_key(pred[2]):
                    return pred[3].search(attrs[pred[2]]) != None
                else:
                    return False
            raise NotImplementedError
        else:
            # No idea!!
            raise(NotImplementedError)
        return 1
        
    def _checkSaxXPathAttr(self, pred, attrs):

        # Namespacey
        if (not attrs.has_key(pred[0])):
            if (attrs.has_key((None, pred[0]))):
                pred[0] = (None, pred[0])
            else:
                return 0
        rel = pred[1]

        # -Much- faster than eval
        if (type(pred[2]) == types.FloatType):
            attrValue = float(attrs[pred[0]])
        else:
            attrValue = attrs[pred[0]]

        comp = cmp(attrValue, pred[2])
        if rel == "=":
            return comp == 0
        elif rel == ">":
            return comp == 1
        elif rel == "<":
            return comp == -1
        elif rel == "<=":
            return comp in (-1, 0)
        elif rel == ">=":
            return comp in (1, 0)
        elif rel == "!=":
            return comp in (1, -1)
        else:
            raise(NotImplementedError)


    def _convert_elem(self, line):
        # Currently: 1 name {attrs} parent npred end
        if (line[0] == '1'):           
            start = line.find("{")
            name = line[2:start-1]
            if line[start+1] == '}':
                attrs = {}
            else:
                attrList = self.attrRe.findall(line)
                attrs = {}
                for m in attrList:
                    attrs[unicode(m[0])] = unicode(m[1])
            return [name, attrs]
        elif (line[0] == '4'):
            end = line.rfind("}")
            stuff = eval(line[2:end+1])
            return [stuff[1], stuff[3]]        
        else:
            raise ValueError("Called convert on non element.")

    def saxify(self, handler=None, sax=[]):
        if handler == None:
            handler = self
        if not sax:
            sax = self.get_sax()
            
	for l in sax:
            line = l
            # line = l.strip()
            if line[0] == "1":
                # String manipulation method
                (name, attrs) = self._convert_elem(line)
                handler.startElement(name, attrs)
            elif line[0] == "3":
                handler.characters(line[2:], 0, len(line)-2)
            elif line[0] == "2":
                end = line.rfind(' ')
                handler.endElement(line[2:end])
            elif line[0] == "9":
                pass
            elif line[0] == '4':
                # 4 ns,name,qname, {}
                idx = line.rfind(' ')
                idx = line[:idx].rfind(' ')
                idx = line[:idx].rfind(' ')
                line = line[:idx]
                (ns, name, qname, attrs) = eval(line[2:])
                handler.startElementNS((ns,name), qname, attrs)
            elif line[0] == '5':
                # 5 ns,name,qname parent pred end
                idx = line.rfind(' ')
                line = line[:idx]
                (ns, name, qname) = eval(line[2:])
                handler.endElementNS((ns,name),qname)
            elif line[0] == '6':
                # 6 pref, uri
                pref, uri = eval(line[2:])
                handler.startPrefixMapping(pref, uri)
            else:
                # Unknown type
                raise ValueError(line)


    def get_dom(self):
        if (self.dom):
            return self.dom
        else:
            # Turn SAX into DOM and cache
            s2dhandler.initState()
            self.saxify(s2dhandler);
            self.dom = s2dhandler.getRootNode()
            return self.dom

    def get_xml(self, events=[]):
        if (not events and self.xml):
            return self.xml
        else:
            # Turn SAX into XML and cache
            if not events:
                process = self.sax
            else:
                process = events
            s2xhandler.initState()
            self.saxify(s2xhandler, process)
            if not events:
                self.xml = s2xhandler.get_raw()
                return self.xml
            else:
                return s2xhandler.get_raw()
            
    def get_sax(self):
        return self.sax

    def fetch_vector(self, session, index, summary=False):
        return index.indexStore.fetch_vector(session, index, self, summary)


class MarcRecord(Record):

    def __init__(self, doc, docid=0, store=""):
        txt = doc.get_raw()
        self.marc = MARC(txt)
        self.id = docid
        self.recordStore = store
        # Estimate number of words...
        display = str(self.marc)
        self.wordCount = len(display.split()) - ( len(display.split('\n')) * 2)
        self.byteCount = len(display)
        self.decoder = MARC8_to_Unicode()
        self.asciiRe = re.compile('([\x0e-\x1f]|[\x7b-\xff])')

    def process_xpath(self, xpTuple, maps={}):
        if (not isinstance(xpTuple, list)):
            # Raw XPath
            c = utils.verifyXPaths([xpTuple])
            if (not c or not c[0][1]):
                return []
            else:
                xpTuple = c[0]

        xp = xpTuple[1]
        # format:  fldNNN/a
        try:
            fld = int(xp[0][1][3:])
        except ValueError:
            # not a NNN not an int
            return []
        if self.marc.fields.has_key(fld):
            data = self.marc.fields[fld]        
        else:
            return []
        if len(xp) > 1:
            subfield = xp[1][1]
        else:
            subfield = ""

        vals = []
        if fld in [0,1]:
            vals = data
        else:
            for d in data:
                if not subfield:
                    vals.append(' '.join([x[1] for x in d[2]]))
                elif subfield == 'ind1':
                    vals.append(d[0])
                elif subfield == 'ind2':
                    vals.append(d[1])
                elif fld == 8:
                    if not subfield:
                        vals.append(d)
                    elif subfield == 'lang':
                        vals.append(d[35:38])
                    elif subfield == 'date':
                        vals.append(d[:6])
                    elif subfield == 'pubStatus':
                        vals.append(d[6])
                    elif subfield == 'date1':
                        vals.append(d[7:11])
                    elif subfield == 'date2':
                        vals.append(d[11:15])
                    elif subfield == 'pubPlace':
                        vals.append(d[15:18])
                else:
                    for x in d[2]:
                        try:
                            if x[0] == subfield:
                                vals.append(x[1])
                        except:
                            # broken
                            pass
        nvals = []
        for v in vals:
            try:
                nvals.append(v.decode('utf-8'))
            except:
                try:
                    convtd = self.decoder.translate(v)
                    nvals.append(unicodedata.normalize('NFC', convtd))
                except:
                    # strip out any totally @^%(ed characters
                    v = self.asciiRe.sub('?', v) 
                    nvals.append(v)
        return nvals

    def get_dom(self):
        raise(NotImplementedError)
    def get_sax(self):
        raise(NotImplementedError)
    def get_xml(self):
        return self.marc.toMARCXML()
    def fetch_vector(self, session, index, summary=False):
        return index.indexStore.fetch_vector(session, index, self, summary)
