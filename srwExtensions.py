
# All extension functions for SRW should be imported into this space
# even if they're defined elsewhere.

# Functions should modify extra*Data in place.
# Add DOM node for serialization by ZSI. 
# Fr'ex:
# object.extraFooData.append(r.fromString('<a:b c="d">e</a:b>'))

# Configuration in SRW ZeeRex file should look like:
#
#  <zeerex:supports type="extension"
#                   c3:type="record"
#                   c3:function="docidRecordHandler"
#                   c3:sruName="x-info-2-docid"
#                   c3:sruFunction="docidRequestXform">
#     info:srw/extension/2/docid-v1.0 docid
#  </zeerex:supports>
# 
# Where c3:type is one of: record, term, search, scan, explain, response

# Useful tools:
from xml.sax.saxutils import escape
from utils import reader as domReader
reader = domReader()

# Simple SRU->SRW transformation

def simpleRequestXform(item, config):
    data = config.sruExtensionMap.get(item[0], None)
    if data:
        xml = '<%s:%s xmlns:%s="%s">%s</%s:%s>' % (data[1], data[1], data[1], data[0], item[1], data[1], data[1])
        val = reader.fromString(xml)
        return val
    return None

# Extension Handler Functions:

import internal
def implementationResponseHandler(req, resp, other=None):
    # Put our implementation id into the response
    # Stored in ZeeRex, so on config object
    txt = """
    <ident:serverInfo xmlns:ident="info:srw/extensions/1/ident-v1.0">
      <ident:institution>University of Liverpool</ident:institution>
      <ident:vendor>Cheshire3 Project</ident:vendor>
      <ident:application>Cheshire3 SRW Server</ident:application>
      <ident:version>%s</ident:version>
    </ident:serverInfo>
    """ % ('.'.join(map(str, internal.cheshireVersion)))
    resp.extraResponseData.append(reader.fromString(txt))

def docidRecordHandler(req, ro, other):
    # Put the record identifier into extraRecordData
    txt = '<docid:recordIdentifier xmlns:docid="info:srw/extension/2/docid-v1.0">%s</docid:recordIdentifier>' % escape(str(other))
    xrdn = reader.fromString(txt)
    try:
        ro.extraRecordData.append(xrdn)
    except AttributeError:
        ro.extraRecordData = [xrdn]

def recordMetadataHandler(req, ro, rec):
    # Put resultSetItem info into extraRecordData
    mdBits = ['<rec:metaData xmlns:rec="http://www.archiveshub.ac.uk/srw/extension/2/record-1.1">']
    # ids may contain nasties - escape them
    mdBits.append('<rec:identifier>%s</rec:identifier>' % escape(unicode(rec.id, 'utf-8')))
    if rec.recordStore:
        mdBits.append('<rec:locationIdentifier>%s</rec:locationIdentifier>' % escape(rec.recordStore))
    if rec.wordCount:
        mdBits.append('<rec:wordCount>%d</rec:wordCount>' % rec.wordCount)
    if rec.wordCount:
        mdBits.append('<rec:byteCount>%d</rec:byteCount>' % rec.byteCount)
    # now get stuff from resultSetItem
    rsi = rec.resultSetItem
    if rsi.weight:
        mdBits.append('<rec:relevanceValue rec:relevanceType="raw">%f</rec:relevanceValue>' % rsi.weight)
    if rsi.scaledWeight:
        mdBits.append('<rec:relevanceValue rec:relevanceType="scaled">%f</rec:relevanceValue>' % rsi.scaledWeight)
    if rsi.occurences:
        mdBits.append('<rec:termOccurences>%d</rec:termOccurences>' % rsi.occurences)
    if rsi.proxInfo:
        mdBits.append('<rec:termPositionList>%r</rec:termPositionList>' % (rsi.proxInfo))
        
    mdBits.append('</rec:metaData>')
    txt = ''.join(mdBits)
    xrd = reader.fromString(txt)
    try:
        ro.extraRecordData.append(xrd)
    except AttributeError:
        ro.extraRecordData = [xrd]
    
    
def resultSetSummaryHandler(req, ro, rs):
    # puts summary of resultSet nto extraSearchData
    if not len(rs):
        return
    
    mdBits = ['<rs:resultSetData xmlns:rs="http://www.archiveshub.ac.uk/srw/extension/2/resultSet-1.1">']
    if hasattr(rs[0], 'weight'):
        allids = [escape(r.id) for r in rs] # ids may contain nasties - escape them
        mdBits.append('<rs:ids>%r</rs:ids>' % allids)
    if hasattr(rs[0], 'weight'):
        allweights = [r.weight for r in rs]
        mdBits.append('<rs:weights>%r</rs:weights>' % allweights)
    if hasattr(rs[0], 'proxInfo') and rs[0].proxInfo:
        prox = [r.proxInfo for r in rs]
        mdBits.append('<rs:proxInfo>%r</rs:proxInfo>' % prox)
        
    mdBits.append('</rs:resultSetData>')
    txt = ''.join(mdBits)
    xsd = reader.fromString(txt)
    try:
        ro.extraResponseData.append(xsd)
    except AttributeError:
        ro.extraResponseData = [xsd]
