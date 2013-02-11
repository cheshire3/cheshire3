"""Cheshire3 Selector Implementations.

possible location types:  'xpath', 'attribute', 'function', 'sparql' (in graph)
"""

import time

from lxml import etree

from cheshire3.baseObjects import Selector
from cheshire3.record import LxmlRecord
from cheshire3.exceptions import ConfigFileException
from cheshire3.internal import CONFIG_NS
from cheshire3.utils import getFirstData, elementType


class SimpleSelector(Selector):

    def _handleLocationNode(self, session, child):
        data = {'maps': {}, 'string': '', 'type': ''}
        xp = getFirstData(child)
        data['string'] = xp

        if child.localName == 'xpath':
            data['type'] = 'xpath'
        else:
            try:
                data['type'] = child.getAttribute('type').lower()
            except:
                raise ConfigFileException("Location element in {0} must have "
                                          "'type' attribute".format(self.id))
            
        if data['type'] == 'xpath':
            for a in child.attributes.keys():
                # ConfigStore using 4Suite
                if type(a) == tuple:
                    attrNode = child.attributes[a]
                    a = attrNode.name
                if (a[:6] == "xmlns:"):
                    pref = a[6:]
                    uri = child.getAttributeNS('http://www.w3.org/2000/xmlns/',
                                               pref)
                    if not uri:
                        uri = child.getAttribute(a)
                    data['maps'][pref] = uri
                else:
                    data[a] = child.getAttributeNS(None, a)
        return data

    def _handleLxmlLocationNode(self, session, child):
        data = {'maps': {}, 'string': '', 'type': ''}
        data['string'] = child.text

        if child.tag in ['xpath', '{%s}xpath' % CONFIG_NS]:
            data['type'] = 'xpath'
        else:
            try:
                data['type'] = child.attrib['type'].lower()
            except KeyError:
                raise ConfigFileException("Location element in {0} must have "
                                          "'type' attribute".format(self.id))

        if data['type'] in ['xpath', 'sparql']:
            for a in child.nsmap:
                if a is not None:
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
            self.sources.append(paths)

    def _handleLxmlConfigNode(self, session, node):    
        if node.tag in ["source", '{%s}source' % CONFIG_NS]:
            xpaths = []
            for child in node.iterchildren(tag=etree.Element):
                if child.tag in ["xpath", '{%s}xpath' % CONFIG_NS,
                                 "location", '{%s}location' % CONFIG_NS]:
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
    u"""Selector specifying and attribute or function.
    
    Selector that specifies an attribute or function to use to select data from
    Records.
    """

    def process_record(self, session, record):
        u"Extract the attribute, or run the specified function, return data."
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
                    elif name == 'now':
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
                        raise ConfigFileException("Unknown function: "
                                                  "%s" % name)
                else:
                    raise ConfigFileException("Unknown metadata selector type:"
                                              " %s" % typ)

        return vals


class XPathSelector(SimpleSelector):
    u"""Selects data specified by XPath(s) from Records."""

    def __init__(self, session, config, parent):
        self.sources = []
        SimpleSelector.__init__(self, session, config, parent)
    
    def process_record(self, session, record):
        u"Select and return data from elements matching configured XPaths."
        if not isinstance(record, LxmlRecord):
            raise TypeError("XPathSelector '{0}' only supports selection from "
                            "LxmlRecords")
        vals = []
        
        for src in self.sources:
            # list of {}s
            for xp in src:
                vals.append(record.process_xpath(session,
                                                 xp['string'],
                                                 xp['maps']))
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
        try:
            if len(self.sources[0]) != 2:
                raise ConfigFileException("SpanXPathSelector '{0}' requires "
                                          "exactly two XPaths".format(self.id))
        except IndexError:
            raise ConfigFileException("SpanXPathSelector '{0}' requires "
                                      "exactly 1 <source>".format(self.id))
        
    def process_record(self, session, record):
        vals = []
        startPath = self.sources[0][0]['string']
        startMaps = self.sources[0][0]['maps']
        if not startPath.startswith('/'):
            # Not absolute path, prepend //
            startPath = '//{0}'.format(startPath)
        endPath = self.sources[0][1]['string']
        endMaps = self.sources[0][1]['maps']
        if not endPath.startswith('/'):
            # Not absolute path, prepend //
            endPath = '//{0}'.format(endPath)
        if isinstance(record, LxmlRecord):
            # Avoid unnecessary re-parsing
            tree = record.get_dom(session)
        else:
            # Parse to an lxml.etree
            tree = etree.fromstring(record.get_xml(session))
        # Find all of the start nodes
        startNodes = tree.xpath(startPath, namespaces=startMaps)
        # Initialize empty startEndPair
        startEndPair = (None, None)
        if startPath == endPath:
            # Paths are the same - copy the start nodes
            endNodes = startNodes[:]
            # Start path and end path are the same, treat as break points
            for elem in tree.iter():
                if elem in startNodes:
                    # When we hit a node from the start node list
                    if startEndPair[0] is None:
                        # we don't have a start node in our startEndPair
                        # put this one in as the start node
                        startEndPair = (elem, startEndPair[1])
                    else:
                        # We already have a start node
                        # Add this as the end node
                        startEndPair = (startEndPair[0], elem)
                        # Append the startEndPair to the list
                        vals.append(startEndPair) 
                        # Start a new startEndPair with this as the start node 
                        startEndPair = (elem, None)
        else:
            # Start path and end path are different
            #
            # N.B. this algorithm is non-greedy.
            # The shortest span is always selected. If another start node is 
            # hit before an end node occurs it will overwrite the first
            #
            # N.B. developers: this works slightly differently from the 
            # previous SAX base version which treated the end of the record 
            # as an end tag, this does not
            #
            # Find all the end nodes
            endNodes = tree.xpath(endPath, namespaces=endMaps)
            for elem in tree.iter():
                if elem in startNodes:
                    # When we hit a node from the start node list
                    # put this one in as the start node
                    startEndPair = (elem, startEndPair[1])
                elif elem in endNodes and startEndPair[0] is not None:
                    # When we hit an end node and we already have a start node
                    # Add this as the end node
                    startEndPair = (startEndPair[0], elem)
                    # Append the startEndPair to the list
                    vals.append(startEndPair)
                    # Reset the startEndPair
                    startEndPair = (None, None)       
        return vals
    