
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

#from cheshire3.utils import reader as domReader
#reader = domReader()
from lxml import etree
from lxml.builder import ElementMaker

# Simple SRU->SRW transformation

def simpleRequestXform(item, config):
    data = config.sruExtensionMap.get(item[0], None)
    if data:
        xml = '<%s:%s xmlns:%s="%s">%s</%s:%s>' % (data[1], data[1], data[1], data[0], item[1], data[1], data[1])
        val = reader.fromString(xml)
        return val
    return None

namespaces = {
    'sru' : 'http://www.loc.gov/zing/srw/',
    'diag' : 'http://www.loc.gov/zing/srw/diagnostic/'
    }

sruElemFac = ElementMaker(namespace=namespaces['sru'], nsmap=namespaces)
diagElemFac = ElementMaker(namespace=namespaces['diag'], nsmap=namespaces)
# Diagnostic XML formatter
def diagnosticToXML(diag):
    el = diagElemFac.diagnostic(
        diagElemFac.uri(diag.uri)
        )
    if diag.message:
        el.append(diagElemFac.message(diag.message))
    if diag.details:
        el.append(diagElemFac.details(diag.details))
    return el


# Extension Handler Functions:

import cheshire3.internal
def implementationResponseHandler(session, val, resp, other=None):
    """ Put our implementation id into the response """
    # Stored in ZeeRex, so on config object
    txt = """
    <ident:serverInfo xmlns:ident="info:srw/extensions/1/ident-v1.0">
      <ident:institution>University of Liverpool</ident:institution>
      <ident:vendor>Cheshire3 Project</ident:vendor>
      <ident:application>Cheshire3 SRW Server</ident:application>
      <ident:version>%s</ident:version>
    </ident:serverInfo>
    """ % ('.'.join([str(x) for x in internal.cheshire3Version]))
    return etree.XML(txt)


# Record
def docidRecordHandler(session, val, resp, rec):
    """ Put the record identifier into extraRecordData"""
    txt = '<docid:recordIdentifier xmlns:docid="info:srw/extension/2/docid-v1.0">%s</docid:recordIdentifier>' % escape(str(rec))
    return etree.XML(txt)


def recordMetadataHandler(session, val, resp, rsi, rec):
    """ Put resultSetItem info into extraRecordData"""
    mdBits = ['<rec:metaData xmlns:rec="info:srw/extension/2/record-1.1">']
    # ids may contain nasties - escape them
    mdBits.append('<rec:identifier>%s</rec:identifier>' % escape(unicode(rec.id, 'utf-8')))
    if rec.recordStore:
        mdBits.append('<rec:locationIdentifier>%s</rec:locationIdentifier>' % escape(rec.recordStore))
    if rec.wordCount:
        mdBits.append('<rec:wordCount>%d</rec:wordCount>' % rec.wordCount)
    if rec.wordCount:
        mdBits.append('<rec:byteCount>%d</rec:byteCount>' % rec.byteCount)
    # now get stuff from resultSetItem
    if rsi.weight:
        mdBits.append('<rec:relevanceValue rec:relevanceType="raw">%f</rec:relevanceValue>' % rsi.weight)
    if rsi.scaledWeight:
        mdBits.append('<rec:relevanceValue rec:relevanceType="scaled">%f</rec:relevanceValue>' % rsi.scaledWeight)
    if rsi.occurences:
        mdBits.append('<rec:termOccurences>%d</rec:termOccurences>' % rsi.occurences)
    if rsi.proxInfo:
        mdBits.append('<rec:termPositionList>%r</rec:termPositionList>' % (rsi.proxInfo))
        
    mdBits.append('</rec:metaData>')
    return etree.XML(''.join(mdBits))


# SearchRetrieve    
def resultSetSummaryHandler(session, val, resp, resultSet=[], db=None):
    """ Put summary of resultSet into extraSearchRetrieveData"""
    if not len(resultSet):
        return
    
    mdBits = ['<rs:resultSetData xmlns:rs="info:srw/extension/2/resultSet-1.1">']
    if hasattr(resultSet[0], 'weight'):
        allids = [escape(r.id) for r in resultSet] # ids may contain nasties - escape them
        mdBits.append('<rs:ids>%r</rs:ids>' % allids)
    if hasattr(resultSet[0], 'weight'):
        allweights = [r.weight for r in resultSet]
        mdBits.append('<rs:weights>%r</rs:weights>' % allweights)
    if hasattr(resultSet[0], 'proxInfo') and resultSet[0].proxInfo:
        prox = [r.proxInfo for r in resultSet]
        mdBits.append('<rs:proxInfo>%r</rs:proxInfo>' % prox)
        
    mdBits.append('</rs:resultSetData>')
    return etree.XML(''.join(mdBits))


import cheshire3.cqlParser as cql
def resultSetFacetsHandler(session, val, resp, resultSet=[], db=None):
    """Put facet for requested index into extraSearchRetrieveData
       val is a CQL query. 
           Boolean used is meaningless, facets are returned for each clause.
           Term in each clause is also meaningless and need be nothing more than *
       Result looks something like browse response e.g.
    <facets>
        <facetByIndex index="dc.subject" relation"exact">
            <term>
                <value>Genetics</value>
                <numberOfRecords>2</numberOfRecords>
            </term>
            ...
        </facet>
        ...
    </facets>
    """
    # quick escapes
    if not len(resultSet) or db is None:
        return
    
    global namespaces, sruElemFac
    myNamespaces = namespaces.copy()
    myNamespaces['fct'] = "info:srw/extension/2/facets-1.0"
    
    pm = db.get_path(session, 'protocolMap')
    if not pm:
        db._cacheProtocolMaps(session)
        pm = db.protocolMaps.get('http://www.loc.gov/zing/srw/')
        self.paths['protocolMap'] = pm
        
    fctElemFac = ElementMaker(namespace=myNamespaces['fct'], nsmap=myNamespaces)

    def getFacets(query):
        if (isinstance(query, cql.SearchClause)):
            fctEl = fctElemFac.facetsByIndex({'index': query.index.toCQL(), 'relation': query.relation.toCQL()})
#            fctEl.append(sruElemFac.index(query.index.toCQL()))
#            fctEl.append(sruElemFac.relation(query.relation.toCQL()))
            idx = pm.resolveIndex(session, query)
            if idx is None:
                fctEl.append(diagnosticToXML(cql.Diagnostic(code=16, message="Unsupported Index", details=query.index.toCQL())))
                return fctEl
            
            try:
                facets = idx.facets(session, resultSet)
            except:
                # index doesn't support facets
                # TODO: diagnostic?
                facets = []
                
            termsEl = sruElemFac.terms()
            for f in facets:
                termsEl.append(sruElemFac.term(
                                               sruElemFac.value(f[0]),
                                               sruElemFac.numberOfRecords(str(f[1][1]))
                                               )
                               )
                
            fctEl.append(termsEl)
            return [fctEl]
        else:
            fctEls = getFacets(query.leftOperand)
            fctEls.extend(getFacets(query.rightOperand))
            return fctEls
        
    fctsEl = fctElemFac.facets()
    try:
        query = cql.parse(val)
    except cql.Diagnostic as d:
        fctsEl.append(diagnosticToXML(d))
        return fctsEl
    
    for el in getFacets(query):
        fctsEl.append(el)
        
    return fctsEl
