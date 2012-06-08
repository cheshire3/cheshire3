
# Handlers for SRW Operations
# Version: 1.1
# Author:  Rob Sanderson (azaroth@liv.ac.uk)
#          John Harrison (john.harrison@liv.ac.uk)
#
# Version History:
# 08/10/2007 - JH - Automatic insertion of database metadata into explain response
# 06/12/2007 - JH - Some extension handling fixes
#


import os, sys, re
import SRW
import SRW.types
from ZSI import *
from PyZ3950.SRWDiagnostics import *
from xml.sax.saxutils import escape

from srwExtensions import *

from cheshire3.baseObjects import Session, RecordStore
from cheshire3.document import StringDocument
from cheshire3.utils import flattenTexts
from cheshire3 import internal
import cheshire3.cqlParser as CQLParser

# -------------------------------------------------------------------
# Data transformations
#


# NB:  Sort Keys from Version 1.0 and 1.1
# Version 1.2 uses CQL to carry sort info, so this becomes redundant
def parseSortKeys(self):
    " Parse sortKeys parameter to sortStructure "
    self.sortStructure = []
    if (self.sortKeys):
        # First try some simple parsing...
        self.sortKeys = self.sortKeys.strip()
        sks = self.sortKeys.split()
        # TODO: Maybe write better sortKey parser
        if (len(sks) > 1):
            for s in sks:
                if not (s[0] in ['"', '/']):
                    # Paths should always start with / or " something is screwed up                    
                    pass

        skObjects = []
        for skstr in sks:
            sko = SRW.types.SortKey('sortKey')
            sk = skstr.split(",")
            sko.path = sk[0]
            try:
                sko.schema = sk[1]
                sko.ascending = int(sk[2])
                sko.caseSensitive = int(sk[3])
                sko.missingValue = sk[4]
            except:
                # No problems if these fail from indexError
                pass
            skObjects.append(sko)
        self.sortStructure = skObjects

SRW.types.SearchRetrieveRequest.parseSortKeys = parseSortKeys



def process_extraData(hash, req, resp, other=None):
    for ((uri, name), fn) in hash.iteritems():
        # Check name in request, call fn
        # XXX: probably need to do this recursively...
        for node in req.extraRequestData:
            if node.localName == name and node.namespaceURI == uri:
                fn(req, resp, other)
            # XXX: too much descending here - John
#            elem = node.childNodes[0]
#            if elem.localName == name and elem.namespaceURI == uri:
#                fn(req, resp, other)
    

# ---- Main query handler ----

xmlver = re.compile("[ ]*<\?xml[^>]+>")

def process_searchRetrieve(self, session, req):

    if (not req.version):
        diag = Diagnostic7()
        diag.message = "Mandatory 'version' parameter not supplied"
        diag.details = 'version'
        raise diag

    # Get our config based on URL
    config = req.config
    db = config.parent
    session.database = db.id

    rss = db.get_object(session, 'defaultResultSetStore')

    # Setup for processing
    if (req.query != ""):
        req.queryStructure = CQLParser.parse(req.query)
    else:
        # No Query, Request is seriously Broken
        f = Diagnostic7()
        f.message = 'Request must include a query'
        f.details = 'query'
        raise f
    req.queryStructure.config = config

    req.xQuery = req.queryStructure.toXCQL()
    self.echoedSearchRetrieveRequest = req
    req.parseSortKeys()

    if (req.diagnostics):
        self.diagnostics = req.diagnostics
        return

    # Check if we recognise the record Schema
    schema = req.get('recordSchema')
    # Redirect to full value
    if (config.recordNamespaces.has_key(schema)):
        schema = config.recordNamespaces[schema]
    if (not schema in config.recordNamespaces.values()):
        diag = Diagnostic66()
        diag.details = schema
        raise diag

    txr = config.transformerHash.get(schema, None)

    recordPacking = req.get('recordPacking')
    if not recordPacking  in ["string", "xml"]:
        diag = Diagnostic71()
        diag.details = req.recordPacking;
        raise diag

    # Fencepost.  SRW starts at 1, C3 starts at 0
    startRecord = req.get('startRecord') -1
    maximumRecords = req.get('maximumRecords')
    ttl = req.get('resultSetTTL')
    nsk = len(req.sortStructure)
    rsn =  req.queryStructure.getResultSetId()
    rs = db.search(session, req.queryStructure)

    recs = []
    if (rs is not None):
        self.numberOfRecords = len(rs)
        if (ttl and not rsn):
            rs.expires = ttl
            rsn = rss.create_resultSet(session, rs)

        self.records = []
        end = min(startRecord+maximumRecords, len(rs))

        for rIdx in range(startRecord, end):
            rsi = rs[rIdx]
            r = rsi.fetch_record(session)
            ro = SRW.types.Record('record')
            ro.recordPacking = recordPacking
            ro.recordSchema = schema

            if (txr is not None):
                doc = txr.process_record(session, r)
                rec = doc.get_raw(session)
                rec = xmlver.sub("", rec)
            else:
                rec = r.get_xml(session)

            if recordPacking == "string":
                ro.recordData = escape(rec)
            else:
                ro.recordData = rec
            
            process_extraData(config.recordExtensionHash, req, ro, r)
            recs.append(ro)

        self.records = recs
        nrp = end + 1                                    # Back to SRU 1-based recordPosition
        if ( nrp < self.numberOfRecords and nrp > 0):
            self.nextRecordPosition = nrp
        if (rsn):
            self.resultSetId = rsn
            self.resultSetIdleTime = ttl
    else:
        self.numberOfRecords = 0
    
    self.extraResponseData = []    # empty to prevent data from previous requests
    process_extraData(config.searchExtensionHash, req, self, rs)
    process_extraData(config.responseExtensionHash, req, self)


SRW.types.SearchRetrieveResponse.processQuery = process_searchRetrieve

def process_scan(self, session, req):
    # Process a scan query

    config = req.config
    db = config.parent
    session.database = db.id

    self.terms = []
    if (not req.version):
        diag = Diagnostic7()
        diag.message = "Mandatory 'version' parameter not supplied"
        diag.details = 'version'
        raise diag

    if req.scanClause:
        #convert clause into SearchClause object
        clause = CQLParser.parse(req.scanClause)
        # Stupid schema.
        xsc = []
        xsc.append(clause.index.toXCQL())
        xsc.append(clause.relation.toXCQL())
        xsc.append(clause.term.toXCQL())
        req.xScanClause = "".join(xsc)
    else:
        # Seriously broken request.
        f = Diagnostic7()
        f.message = 'Request must include a query'
        f.details = 'scanClause'
        raise f

    self.echoedScanRequest = req
    if (req.diagnostics):
        self.diagnostics = req.diagnostics
        return

    mt = req.get('maximumTerms')
    rp = req.get('responsePosition')
    if (rp < 0 or rp > (mt+1)):
        f = Diagnostic120()
        f.message = "Response position out of range"
        f.details = str(rp)
        raise f

    if (not clause.term.value):
        clause.term.value = chr(0)
    
    clause.config = config

    if (rp == 1):
        data = db.scan(session, clause, mt, direction=">=")
    elif (rp == 0):
        data = db.scan(session, clause, mt, direction=">")
    elif (rp == mt):
        data = db.scan(session, clause, mt, direction="<=")
        data.reverse()
    elif (rp == mt+1):
        data = db.scan(session, clause, mt, direction="<")
        data.reverse()
    else:
        # Need to go up and down
        data1 = db.scan(session, clause, mt-rp+1, direction=">=")
        data = db.scan(session, clause, rp, direction="<=")
        if data1[0][0] == data[0][0]:
            data = data[1:]
        data.reverse()
        data.extend(data1)

    for d in data:
        t = SRW.types.ScanTerm('ScanTerm')
        t.value = d[0]
        t.numberOfRecords = d[1][1]
        process_extraData(config.termExtensionHash, req, t, d)
        self.terms.append(t)
    process_extraData(config.scanExtensionHash, req, self)
    process_extraData(config.responseExtensionHash, req, self)

SRW.types.ScanResponse.processQuery = process_scan

def process_explain(self, session, req):
    if (not req.version):
        diag = Diagnostic7()
        diag.message = "Mandatory 'version' parameter not supplied"
        diag.details = 'version'
        raise diag

    config = req.config

    self.echoedExplainRequest = req

    p = config.get_path(session, 'zeerexPath')
    if (not os.path.isabs(p)):
        p2 = config.get_path(session, 'defaultPath')
        p = os.path.join(p2, p)
    f = open(p, "r")
    if f:
        filestr = f.read()
        # insert some database metadata
        db = config.parent
        session.database = db.id
        try:
            from lxml import etree
        except ImportError:
            # possibly try a slower DOM API, but for now...
            pass
        else:
            nsHash = {'zrx':"http://explain.z3950.org/dtd/2.0/" ,'c3':"http://www.cheshire3.org/schemas/explain/"}
            et = etree.XML(filestr)
            dbNode = et.xpath('//zrx:explain/zrx:databaseInfo', namespaces=nsHash)[0]
            try: impNode = dbNode.xpath('//zrx:implementation', namespaces=nsHash)[0]
            except IndexError:
                impNode = etree.XML('''<implementation identifier="http://www.cheshire3.org" version="%d.%d.%d">
                <title>Cheshire3 SRW/U Server</title>
                <agents>
                    <agent type="vendor">The University of Liverpool</agent>
                </agents>
                </implementation>''' % internal.cheshire3Version)
                dbNode.append(impNode)
                
            if db.totalItems:
                try: extNode = dbNode.xpath('//zrx:extent', namespaces=nsHash)[0]
                except IndexError:
                    etree.SubElement(dbNode, 'extent', {'numberOfRecords': str(db.totalItems)})
                else:
                    extNode.set('numberOfRecords', str(db.totalItems))
                
            if db.lastModified:
                try: histNode = dbNode.xpath('//zrx:history', namespaces=nsHash)[0]
                except IndexError:
                    # create history and append node
                    etree.SubElement(dbNode, 'history', {'lastUpdate': db.lastModified})
                else:
                    histNode.set('lastUpdate', db.lastModified)
            

            filestr = etree.tostring(et) # serialise modified record to string
            
        # Create a record object and populate
        rec = SRW.types.Record('record')
        rec.recordPacking = req.recordPacking
        if (req.recordPacking == 'string'):
            filestr = escape(filestr)
        rec.recordSchema = config.recordNamespaces['zeerex']
        rec.recordData = filestr
        self.record = rec
    process_extraData(config.explainExtensionHash, req, self)
    process_extraData(config.responseExtensionHash, req, self)

SRW.types.ExplainResponse.processQuery = process_explain


# ----- Update v0.4 -----

# TODO:  Update record update implementation

SRW.update.ExplainResponse.processQuery = process_explain

def unpack_record(self, session, req):
    declre = re.compile('<\?xml(.*?)\?>')
    if req.record:
        packing = req.record.recordPacking
        if packing == "string":
            data = req.record.recordData
            data = declre.sub('', data)            
            doc = StringDocument(data)
        elif packing == "url":
            raise NotImplementedError
        elif packing == "xml":
            # Should be a DOM node, not string repr?
            doc = StringDocument(req.record.recordData)
        else:
            diag = Diagnostic1()
            raise diag
        doc._schema = req.record.recordSchema
    else:
        doc = None
    return doc

SRW.update.UpdateResponse.unpack_record = unpack_record

def fetch_record(self, session, req):
    if (req.recordIdentifier):
        db = req._db
        recStore = db.get_path(session, 'recordStore')
        val = req.recordIdentifier
        if val.isdigit():
            val = int(val)
        else:
            try:
                (storeid, id) =  val.split('/', 1)
                recStore = db.get_object(session, storeid)
                if (id.isdigit()):
                    id = int(id)
            except ValueError, e:
                diag = Diagnostic1()
                diag.details = "Could not parse record id"
                raise diag
        if not isinstance(recStore, RecordStore):
            diag = Diagnostic1()
            raise diag
        else:
            return recStore.fetch_record(session, id)
    else:
        return None

SRW.update.UpdateResponse.fetch_record = fetch_record

def handle_create(self, session, req):
    db = req._db
    rec = self.fetch_record(session, req)
    if rec:
        # Record already exists.
        diag = Diagnostic1()        
        diag.details = "Already exists"
        raise diag   
    doc = self.unpack_record(session, req)
    # Need to get a 'create' workflow   
    if doc:
        flow = req.config.workflowHash['info:srw/operation/1/create']
        rec = flow.process(session, doc)
    else:
        # Create an empty record
        recStore = db.get_path(session, 'recordStore')
        rec = recStore.create_record(session, None)
        recStore.commit_storing()
    self.recordIdentifier = repr(rec)
    self.operationStatus = "success"

SRW.update.UpdateResponse.handle_create = handle_create

def handle_delete(self, session, req):
    db = req._db
    rec = self.fetch_record(session, req)
    if not rec:
        diag = Diagnostic1()
        raise diag
    else:
        flow = req.config.workflowHash['info:srw/operation/1/delete']
        flow.process(session, rec)
        self.operationStatus = "success"

SRW.update.UpdateResponse.handle_delete = handle_delete

def handle_replace(self, session, req):
    db = req._db
    rec = self.fetch_record(session, req)
    doc = self.unpack_record(session, req)
    if not rec:
        diag = Diagnostic1()
        diag.details = "No record found"
        raise diag
    elif not doc:
        diag = Diagnostic1()
        diag.details = "No replacement"
        raise diag   
    else:
        flow = req.config.workflowHash['info:srw/operation/1/delete']
        flow.process(session, rec)
        flow2 = req.config.workflowHash['info:srw/operation/1/create']
        flow2.process(session, doc)
        self.operationStatus = "success"

SRW.update.UpdateResponse.handle_replace = handle_replace


def handle_metadata(self, session, req):
    diag = Diagnostic1()
    diag.details = "Not yet supported"
    self.diagnostics = [diag]

SRW.update.UpdateResponse.handle_metadata = handle_metadata


def process_update(self, req):
    self.version = "1.1"
    self.operationStatus = "fail"

    if (not req.version):
        diag = Diagnostic7()
        diag.message = "Mandatory 'version' parameter not supplied"
        diag.details = 'version'
        raise diag
    config = req.config
    db = config.parent
    req._db = db
    session = Session()
    session.environment = "apache"
    session.database = db.id

    if req.operation == "info:srw/operation/1/create":
        # Do Create
        self.handle_create(session, req)
    elif req.operation == "info:srw/operation/1/replace":
        # Do Replace
        self.handle_replace(session, req)
    elif req.operation == "info:srw/operation/1/delete":
        # Do Delete
        self.handle_delete(session, req)
    elif req.operation == "info:srw/operation/1/metadata":
        # Do Metadata update
        self.handle_metadata(session, req)
    else:
        # Barf
        diag = SRWDiagnostics.Diagnostic1()
        diag.details = "Unknown operation: %s" % req.operation
        self.diagnostics = [diag]
         
SRW.update.UpdateResponse.processQuery = process_update
