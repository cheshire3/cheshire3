
from cheshire3.baseObjects import XPathProcessor
from cheshire3.record import LxmlRecord, SaxRecord
from cheshire3.utils import elementType, getFirstData

import time
from lxml import etree

class SimpleXPathProcessor(XPathProcessor):
    sources = []

    def _handleXPathNode(self, session, child):
        data = {'tagName' : '', 'maps': {}, 'string' : ''}

        xp = getFirstData(child)
        data['string'] = xp

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

    def _handleLxmlXPathNode(self, session, child):
        data = {'tagName' : '', 'maps': {}, 'string' : ''}
        xp = child.text
        data['string'] = xp
        # already in nsmap
        for a in child.nsmap:
            data['maps'][a] = child.nsmap[a]
        return data

    def _handleConfigNode(self, session, node):    
        if (node.localName == "source"):
            xpaths = []
            for child in node.childNodes:
                if child.nodeType == elementType:
                    if child.localName == "xpath":
                        # add XPath
                        xp = self._handleXPathNode(session, child)
                        xpaths.append(xp)
            self.sources.append(xpaths)


    def _handleLxmlConfigNode(self, session, node):    
        if (node.tag == "source"):
            xpaths = []
            for child in node.iterchildren(tag=etree.Element):
                if child.tag == "xpath":
                    # add XPath
                    xp = self._handleLxmlXPathNode(session, child)
                    xpaths.append(xp)
            self.sources.append(xpaths)


    def __init__(self, session, config, parent):
        self.sources = []
        self.tagName = ""
        XPathProcessor.__init__(self, session, config, parent)

    def process_record(self, session, record):
        # Extract XPath and return values
        vals = []
        for src in self.sources:
            # list of {}s
            for xp in src:
                if xp['tagName'] and record.tagName != xp['tagName']:
                    continue                
                if isinstance(record, LxmlRecord):
                    vals.append(record.process_xpath(session, xp['string'], xp['maps']))
                else:
                    raise ValueError("Only LXML")
                    # vals.append(record.process_xpath(session, xp['xpath'], xp['maps']))
        return vals


class TransformerXPathProcessor(SimpleXPathProcessor):
    def __init__(self, session, config, parent):
        SimpleXPathProcessor.__init__(self, session, config, parent)
        self.transformer = self.get_path(session, 'transformer')

    def process_record(self, session, record):
        # give record to txr, and then return data
        doc = self.transformer.process_record(session, record)
        try:
            return [[doc.text.decode('utf-8')]]
        except:
            return [[doc.text]]


# two xpaths, span between them
class SpanXPath(SimpleXPathProcessor):
    # extra attributes on xpath:
    #   slide="N"    -- slide this many between components.
    #                   Defaults to window  (eg non overlapping)
    #                   On first xpath, = slide this many before first comp.
    #                   Defaults to 0 (eg start at beginning)
    #   window="N"   -- This is the number of elements in a single comp.
    #                   Defaults to 1  (eg adjacent)
    
    def process_record(self, session, rec):
        if isinstance(rec, LxmlRecord):
            sax = rec.get_sax(session)
            record = SaxRecord(sax)
            record.elementHash = eval(sax[-1][2:])
        else:
            record = rec
        raw = record.process_xpath(session, self.sources[0][0]['xpath'])
        initialSlide = int(self.sources[0][0].get('slide', 0))
        endTag = self.sources[0][1]['xpath'][-1][0][1]
        endNum = int(self.sources[0][1].get('window', '1'))
        slide = int(self.sources[0][1].get('slide', endNum))
        comps = []
        # check if start and end are the same

        for r in raw[initialSlide::slide]:
            start = int(r[-1][r[-1].rfind(' ')+1:])            
            comp = r
            startTag = record._convert_elem(comp[0])[0]
            usingNs = comp[0][0]
            n = len(comp)-1
            currNum = 0
            okay = 1
            saxlen = len(record.sax) -1
            openTags = []
            while okay and start + n < saxlen:
                n += 1
                line = record.sax[start+n]
                if(line[0] in ['1', '4']):
                    # Check it                            
                    if (record._checkSaxXPathLine(self.sources[0][1]['xpath'][1], start + n)):
                        # Matched end
                        currNum += 1
                        if currNum >= endNum:
                            okay = 0
                            continue
                    # Add tags to close if not end or not endNum reached
                    if line[0] == '4':
                        end = line.rfind("}")
                        stuff = eval(line[2:end+1])
                        ns, tag = stuff[0], stuff[1]
                        openTags.append((ns, tag))
                    #*** added by Cat Rob needs to check - no openning tags showing in returned fragment
                        comp.append(line)
                    else:
                        openTags.append(record._convert_elem(line)[0])
                        comp.append(line)                       
                elif (line[0] in ['2', '5']):
                    # check we're open
                    if (line[0] == '2'):
                        end = line.rfind(' ')
                        tag = line[2:end]
                    else:
                        tag = eval(line[2:line.rfind(',')])[0:2]
                    if ((n == 1 and tag[1] == startTag) or (openTags and openTags[-1] == tag)):
                        comp.append(line)
                        if openTags:
                            openTags.pop(-1)
                elif (line[0] == '3'):
                    comp.append(line)
            if (openTags):
                openTags.reverse()
                for o in openTags:
                    if usingNs == '1':
                        comp.append("2 %s %s" % (o, start))
                    else:
                        comp.append("5 u'%s', u'%s', u'', None" % o)
            comps.append(comp)
        
        return [comps]


class MetadataXPath(SimpleXPathProcessor):

    def process_record(self, session, record):
        # Check xpath name against record metadata
        vals = []
        for src in self.sources:
            # list of {}s
            for xp in src:
                # just use last item
                #full = xp['xpath']
                #name = full[1][-1][1]
                name = xp['string']
                if hasattr(record, name):
                    vals.append([getattr(record, name)])
                elif name == 'now':
                    # eg for lastModified/created etc
                    now = time.strftime("%Y-%m-%d %H:%M:%S")
                    vals.append([now])
                else:
                    vals.append(None)
        return vals

        
    
