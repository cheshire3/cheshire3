
from cheshire3.selector import SimpleSelector, MetadataSelector, TransformerSelector, SpanXPathSelector
from cheshire3.record import LxmlRecord, SaxRecord
from cheshire3.utils import elementType, getFirstData

class XPathProcessor(SimpleSelector):
    """An XPathProcessor is a simple wrapper around an XPath.  It is used
    to evaluate the XPath expression according to a given record in
    workflows"""


class SimpleXPathProcessor(XPathProcessor):
    sources = []

    def __init__(self, session, config, parent):
        self.sources = []
        XPathProcessor.__init__(self, session, config, parent)

    def process_record(self, session, record):
        # Extract XPath and return values
        vals = []
        for src in self.sources:
            # list of {}s
            for xp in src:
                if isinstance(record, LxmlRecord):
                    vals.append(record.process_xpath(session, xp['string'], xp['maps']))
                else:
                    raise ValueError("Only LXML")
                    # vals.append(record.process_xpath(session, xp['xpath'], xp['maps']))
        return vals

## two xpaths, span between them
#class SpanXPathProcessor(SimpleXPathProcessor):
#    # extra attributes on xpath:
#    #   slide="N"    -- slide this many between components.
#    #                   Defaults to window  (eg non overlapping)
#    #                   On first xpath, = slide this many before first comp.
#    #                   Defaults to 0 (eg start at beginning)
#    #   window="N"   -- This is the number of elements in a single comp.
#    #                   Defaults to 1  (eg adjacent)
#    
#    def process_record(self, session, rec):
#        if isinstance(rec, LxmlRecord):
#            sax = rec.get_sax(session)
#            record = SaxRecord(sax)
#            record.elementHash = eval(sax[-1][2:])
#        else:
#            record = rec
#
#        startTag = self.sources[0][0]['string']
#        raw = record.process_xpath(session, startTag)
#
#        endTag = self.sources[0][1]['string']
#        if endTag != startTag:
#            endRaw = record.process_xpath(session, self.sources[0][1]['string'])
#        else:
#            #copy all the stuff from raw
#            endRaw = raw[:]
#
#        #get the first thing in the list for every thing in endraw
#        endRawStarts = [x[0] for x in endRaw]
#
#        initialSlide = int(self.sources[0][0].get('slide', 0))
#        endNum = int(self.sources[0][1].get('window', '1'))
#        slide = int(self.sources[0][1].get('slide', endNum))
#        comps = []
#        #raw is all the opening tags
#        for r in raw[initialSlide::slide]:
#            
#            start = int(r[-1][r[-1].rfind(' ')+1:])            
#            comp = r
#            startTag = record._convert_elem(comp[0])[0]
#            usingNs = comp[0][0]
#            actualNs = 0
#            n = len(comp)-1
#            currNum = 0
#            okay = 1
#            
#            saxlen = len(record.sax) -1
#            openTags = []
#            
#            while okay and start + n < saxlen:
#                n += 1
#                line = record.sax[start+n]
#                if(line[0] in ['1', '4']):
#                    if (line in endRawStarts):
#                        # Matched end
#                        currNum += 1
#                        if currNum >= endNum:
#                            okay = 0
#                            continue
#
#                    # Add tags to close if not end or not endNum reached
#                    if line[0] == '4':
#                        end = line.rfind("}")
#                        stuff = eval(line[2:end+1])
#                        ns, tag = stuff[0], stuff[1]
#                        if ns is not None:
#                            actualNs = 1
#                        openTags.append((ns, tag))
#                        comp.append(line)
#                    else:
#                        openTags.append(record._convert_elem(line)[0])
#                        comp.append(line)                       
#                elif (line[0] in ['2', '5']):
#                    # check we're open
#                    if (line[0] == '2'):
#                        end = line.rfind(' ')
#                        tag = line[2:end]
#                    else:
#                        tag = eval(line[2:line.rfind(',')])[0:2]
#                    if ((n == 1 and tag[1] == startTag) or (openTags and openTags[-1] == tag)):
#                        comp.append(line)
#                        if openTags:
#                            openTags.pop(-1)
#                elif (line[0] == '3'):
#                    comp.append(line)
#            if (openTags):
#                openTags.reverse()
#                for o in openTags:
#                    if usingNs == '4':
#                        if actualNs:
#                            comp.append("5 u'%s', u'%s', u'', None" % o)
#                        else:
#                            comp.append("2 %s %s" % (o[1], start))
#                    else:
#                        comp.append("2 %s %s" % (o, start))
#            comps.append(comp)
#        
#        return [comps]
    

# DEPRECATED:  Should use selectors
MetadataXPathProcessor = MetadataSelector
TransformerXPathProcessor = TransformerSelector
SpanXPathProcessor = SpanXPathSelector
MetadataXPath = MetadataSelector
TransformerXPath = TransformerSelector
SpanXPath = SpanXPathSelector

