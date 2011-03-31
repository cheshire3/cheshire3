import time

from lxml import etree

from cheshire3.baseObjects import Selector
from cheshire3.record import LxmlRecord
from cheshire3.exceptions import ConfigFileException

# location types:  'xpath', 'attribute', 'function', 'sparql' (in graph)

class SimpleSelector(Selector):

    def _handleLocationNode(self, session, child):
        data = {'maps': {}, 'string' : '', 'type': ''}
        xp = getFirstData(child)
        data['string'] = xp

        if child.localName == 'xpath':
            data['type'] = 'xpath'
        else:
            try:
                data['type'] = child.getAttribute('type').lower()
            except:
                raise ConfigFileException("Location element in {0} must have 'type' attribute".format(self.id))
            
        if data['type'] == 'xpath':
            for a in child.attributes.keys():
                # ConfigStore using 4Suite
                if type(a) == tuple:
                    attrNode = child.attributes[a]
                    a = attrNode.name
                if (a[:6] == "xmlns:"):
                    pref = a[6:]
                    uri = child.getAttributeNS('http://www.w3.org/2000/xmlns/', pref)
                    if not uri:
                        uri = child.getAttribute(a)
                    data['maps'][pref] = uri
                else:
                    data[a] = child.getAttributeNS(None, a)
        return data

    def _handleLxmlLocationNode(self, session, child):
        data = {'maps': {}, 'string' : '', 'type': ''}
        data['string'] = child.text

        if child.tag == 'xpath':
            data['type'] = 'xpath'
        else:
            try:
                data['type'] = child.attrib['type'].lower()
            except KeyError:
                raise ConfigFileException("Location element in {0} must have 'type' attribute".format(self.id))

        if data['type'] in ['xpath', 'sparql']:
            for a in child.nsmap:
                data['maps'][a] = child.nsmap[a]
        for a in child.attrib:
            if not a in ['type', 'maps', 'string']:
                data[a] = child.attrib['a']
        return data

    def _handleConfigNode(self, session, node):    
        if (node.localName == "source"):
            paths = []
            for child in node.childNodes:
                if child.nodeType == elementType:
                    if child.localName in ["xpath", 'location']:
                        # add XPath Location
                        xp = self._handleLocationNode(session, child)
                        paths.append(xp)
            self.sources.append(xpaths)

    def _handleLxmlConfigNode(self, session, node):    
        if (node.tag == "source"):
            xpaths = []
            for child in node.iterchildren(tag=etree.Element):
                if child.tag in ["xpath", "location"]:
                    # add XPath
                    xp = self._handleLxmlLocationNode(session, child)
                    xpaths.append(xp)
            self.sources.append(xpaths)

    def __init__(self, session, config, parent):
        self.sources = []
        Selector.__init__(self, session, config, parent)


class TransformerSelector(SimpleSelector):
    u"""Selector that applies a Transformer to the Record to select data."""
    
    def __init__(self, session, config, parent):
        SimpleSelector.__init__(self, session, config, parent)
        self.transformer = self.get_path(session, 'transformer')

    def process_record(self, session, record):
        u"""Apply Transformer to the Record, return the resulting data."""
        doc = self.transformer.process_record(session, record)
        try:
            return [[doc.text.decode('utf-8')]]
        except:
            return [[doc.text]]


class MetadataSelector(SimpleSelector):
    u"""Selector that specifies an attribute or function to select data from Records."""

    def process_record(self, session, record):
        u"""Extract the attribute, or run the specified function, return the resulting data."""
        # Check name against record metadata
        vals = []
        for src in self.sources:
            # list of {}s
            for xp in src:
                name = xp['string']
                typ = xp['type']
                if typ == 'xpath':
                    # handle old style
                    if hasattr(record, name):
                        vals.append([getattr(record, name)])
                    elif name  == 'now':
                        # eg for lastModified/created etc
                        now = time.strftime("%Y-%m-%d %H:%M:%S")
                        vals.append([now])
                    else:
                        vals.append(None)
                elif typ == 'attribute':
                    if hasattr(record, name):
                        vals.append([getattr(record, name)])
                elif typ == 'function':
                    if name in ['now', 'now()']:
                        now = time.strftime("%Y-%m-%d %H:%M:%S")
                        vals.append([now])
                    else:
                        # nothing else defined?
                        raise ConfigFileException("Unknown function: %s" % name)
                else:
                    raise ConfigFileException("Unknown metadata selector type: %s" % typ)

        return vals


class XPathSelector(SimpleSelector):
    u"""Selects data specified by XPath(s) from Records."""

    def __init__(self, session, config, parent):
        self.sources = []
        SimpleSelector.__init__(self, session, config, parent)
    
    def process_record(self, session, record):
        """Select and return data from elements matching all configured XPaths."""
        if not isinstance(record, LxmlRecord):
            raise TypeError("XPathSelector '{0}' only supports selection from LxmlRecords")
        vals = []
        
        for src in self.sources:
            # list of {}s
            for xp in src:
                vals.append(record.process_xpath(session, xp['string'], xp['maps']))
        return vals    
    

class SpanXPathSelector(SimpleSelector):
    u"""Selects data from between two given XPaths.
    
    Requires exactly two XPaths.
    The span starts at first configured XPath and ends at the second.
    The same XPath may be given as both start and end point, in which case 
    each matching element acts as a start and stop point (e.g. an XPath for a 
    page break).
    """
    
    def __init__(self, session, config, parent):
        self.sources = []
        SimpleSelector.__init__(self, session, config, parent)
        if len(self.sources[0]) != 2:
            raise ConfigFileException("SpanXPathSelector '{0}' requires exactly two XPaths".format(self.id))
        
    def process_record(self, session, record):
        vals = []
        startPath = self.sources[0][0]['string']
        endPath = self.sources[0][1]['string']
        tree = etree.fromstring(record.get_xml(session))
        # get all the start nodes
        startNodes = tree.xpath(startPath)
        # get all the end nodes or copy the start nodes if the paths are the same
        if endPath != startPath:
            endNodes = tree.xpath(endPath)
        else:
            endNodes = startNodes[:]
        
        tuple = (None, None)
        if startPath == endPath:
            # start path and end path are the same, treat as break points
            for elem in tree.iter():
                # if we hit a node from the start node list
                if elem in startNodes:
                    # if we don't have a start node in our tuple put this one 
                    # in the start node
                    if tuple[0] == None:
                        tuple = (elem, tuple[1])
                    # if we do have a start node add this as the end node, 
                    # start a new tuple and add this also as the start node 
                    # of the next tuple
                    else :
                        tuple = (tuple[0], elem)
                        vals.append(tuple)
                        tuple = (elem, None)
        else:
            # start path and end path are different - more complex
            for elem in tree.iter():
                # if we hit a node from the start node list put it in first 
                # position of the tuple 
                # N.B. the shortest span is always selected, if another start 
                # node is hit before an end node it will overwrite the first
                if elem in startNodes:
                    tuple = (elem, tuple[1])
                # if we hit an end node and we already have a start node in 
                # our tuple add the end node append the tuple to the list and 
                # start a new one
                # N.B. developers: this works slightly differently from the 
                # previous SAX version which treated the end of the record 
                # as an end tag this does not
                elif elem in endNodes and tuple[0] != None:
                    tuple = (tuple[0], elem)
                    vals.append(tuple)
                    tuple = (None, None)       
        return vals
    