
from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Transformer
from cheshire3.document import StringDocument
from cheshire3.internal import CONFIG_NS
from cheshire3.utils import elementType, flattenTexts

from PyZ3950 import z3950, grs1
from lxml import etree

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
        if node.tag in ["transform", '{%s}transform' % CONFIG_NS]:
            self.tagset = node.attrib.get('tagset', '')
            maps = []
            for child in node.iterchildren(tag=etree.Element):
                if child.tag in ['map', '{%s}map' % CONFIG_NS]:
                    map = []                    
                    for xpchild in child.iterchildren(tag=etree.Element):
                        if xpchild.tag in ["xpath", '{%s}xpath' % CONFIG_NS]:
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
                parent = rec.process_xpath(session, '/c3:component/@parent', {'c3':'http://www.cheshire3.org/schemas/component/'})[0]
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


