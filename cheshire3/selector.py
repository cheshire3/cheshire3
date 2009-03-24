
from cheshire3.baseObjects import Selector
from lxml import etree
import time

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
                raise ConfigFileException("Location element in %s must have 'type' attribute")
            
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
                raise ConfigFileException("Location element in %s must have 'type' attribute" % self.id)

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
