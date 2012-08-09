
# In Apache config, for example:
# Listen 127.0.0.1:210
# <VirtualHost 127.0.0.1:210>
#      PythonPath "sys.path+['/path/to/code/']"
#      PythonConnectionHandler filenameOfCode
#      PythonDebug On  
# </VirtualHost>

from mod_python import apache
import traceback, codecs, sys, os

from PyZ3950.asn1 import Ctx, IncrementalDecodeCtx, GeneralString 
from PyZ3950 import asn1, CQLUtils, ccl
from PyZ3950.z3950_2001 import *
from cheshire3.web.z3950_utils import *
from PyZ3950.zdefs import *
from PyZ3950 import oids

import random
rand = random.Random()

from PyZ3950 import CQLParser
asn1.register_oid(Z3950_QUERY_SQL, SQLQuery)
asn1.register_oid(Z3950_QUERY_CQL, asn1.GeneralString)

from cheshire3.baseObjects import Session, Database, Transformer, Workflow
from cheshire3.server import SimpleServer
from cheshire3 import internal
from cheshire3 import cqlParser

session = Session()
session.environment = "apache"
server = SimpleServer(session, os.path.join(internal.cheshire3Root, 'configs', 'serverConfig.xml'))
configs = {}
dbmap = {}
server._cacheDatabases(session)
for db in server.databases.values():
    if db.get_setting(session, "z3950"):
        db._cacheProtocolMaps(session)
	map1 = db.protocolMaps.get('http://www.loc.gov/z3950/', None)
	if map1:
	    configs[map1.databaseName] = map1
	    dbmap[db.id] = map1.databaseName

session.resultSetStore = server.get_path(session, 'resultSetStore')
session.logger = server.get_path(session, 'z3950Logger')
session.configs = configs

class ZHandler:

    connection = None
    session = None
    handlers = {}
    debug = 1
    decode_ctx = None
    encode_ctx = None

    def __init__(self):
        self.session = session
        self.decode_ctx = asn1.IncrementalDecodeCtx(APDU)
        self.encode_ctx = asn1.Ctx()
        self.handlers = {"initRequest" : self.handleInit,
                         "searchRequest" : self.handleSearch,
                         "scanRequest" : self.handleScan,
                         "close" : self.handleClose,
                         "presentRequest" : self.handlePresent,
                         "sortRequest" : self.handleSort,
                         "deleteResultSetRequest" : self.handleDeleteResultSet,
                         "extendedServicesRequest" : self.handleExtendedServices
                         }

    def read(self):
        self.log("Connection starting...")
        c = self.connection.read()
        ctx = self.decode_ctx
        while (c):
            try:
                ctx.feed([ord(x) for x in c])
                while ctx.val_count() > 0:
                    # We have a PDU
                    (type, data) = ctx.get_first_decoded()
                    if (self.handlers.has_key(type)):
                        self.log("Request type: %s" % type)
                        self.log("Data: %s" % repr(data))
                        resp = self.handlers[type](self.session, data)
                        self.log("writing to connection")
                        self.connection.write(resp.tostring())
                        self.log("written")
                        del resp
                    else:                       
                        self.log("Unknown request type: %s" % type )
            except Exception, err:
                data = '\n'.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                self.log(data)
            self.log("reading...")
            c = self.connection.read()
        self.log("Nothing more to read.")

    def encode(self, resp):
        try:
            r = self.encode_ctx.encode(APDU, resp)
        except:
            # XXX Which should it be?
            #self.set_codec('utf8')
            self.encode_ctx.set_codec(asn1.GeneralString, codecs.lookup(name))
            r = self.encode_ctx.encode(APDU, resp)
        return r

    def log(self, data):
        if (self.session.logger):
            self.session.logger.log(self.session, data)

    def set_codec(self, name):
        self.encode_ctx.set_codec(asn1.GeneralString, codecs.lookup(name))
        self.decode_ctx.set_codec(asn1.GeneralString, codecs.lookup(name))

    def generate_diagnostic(self, err):
        d = DefaultDiagFormat()
        data = '\n'.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
        self.log(data)
        d.addinfo = ('v3Addinfo', data)
        d.diagnosticSetId = oids.Z3950_DIAG_BIB1_ov
        # XXX fix
        d.condition = 33
        return d


    def handleInit(self, session, req):
        resp = InitializeResponse()
        (name, resp) = negotiateCharSet(req, resp)
        # XXX Load values from ZeeRex config??
        resp.protocolVersion = ProtocolVersion()
        resp.protocolVersion['version_1'] = 1
        resp.protocolVersion['version_2'] = 1
        resp.protocolVersion['version_3'] = 1
        resp.options = Options()
        for o in ['search', 'present', 'delSet', 'scan', 'negotiation', 'sort']:
            resp.options[o] = 1
        resp.preferredMessageSize = 0x10000
        resp.exceptionalRecordSize = 0x10000
        resp.implementationId = 'Cheshire3'
        resp.implementationName = 'Cheshire3 Z39.50 Server'
        resp.implementationVersion = '.'.join([str(x) for x in internal.cheshire3Version])
        resp.result = 1
        pdu = self.encode(('initResponse', resp))
        if (name <> None):
            self.set_codec(name)
        return pdu

    def handleSearch(self, session, data):
        # Must return a response no matter what
        resp = SearchResponse()
        resp.resultCount = 0
        resp.numberOfRecordsReturned = 0
        resp.nextResultSetPosition = 1
        resp.searchStatus = 1
        resp.resultSetStatus = 1
        resp.presentStatus = PresentStatus.get_num_from_name('failure')

        try:
            queryType = data.query[0]
            query = ["", ""]
            if (queryType in ['type_1', 'type_101']):
                zQuery = data.query[1]
                attrset = zQuery.attributeSet
                query = ['rpn', zQuery.rpn]
            elif (queryType == 'type_0'):
                # A Priori external. We assume CQL
                query = ['cql', data.query[1]]
            elif (queryType == 'type_2'):
                # ISO8777  (CCL)
                rpn = ccl.mk_rpn_query(data.query[1])
                query = ['rpn', rpn]           
            elif (queryType == 'type_104'):
                # Look for CQL or SQL
                type104 = data.query[1].direct_reference
                if (type104 == Z3950_QUERY_CQL_ov):
                    query = ['cql', data.query[1].encoding[1]]
                elif (type104 == Z3950_QUERY_SQL_ov):
                    query = ['sql', data.query[1].encoding[1].queryExpression]
                    # XXX Implement direct to postgres
                    raise NotImplementedError
                else:
                    # Undefined query type
                    raise NotImplementedError
            elif (queryType in ['type_102', 'type_100']):
                # 102: Ranked List, not yet /defined/ let alone implemented
                # 100: Z39.58 query (Standard was withdrawn)
                raise NotImplementedError

            rsetname = data.resultSetName
            dbs = data.databaseNames
            resultSets = []
            if query[0] == 'cql':
                q = CQLParser.parse(query[1])
            for dbname in dbs:
                cfg = self.session.configs.get(dbname, None)
                if cfg is not None:
                    db = cfg.parent
                    if query[0] == 'rpn':
                        self.log("Trying to convert: %s" % (repr(query[1])))
                        q = CQLUtils.rpn2cql(query[1], cfg)               
                        self.log("--> " + q.toCQL())
                    session.database = db.id
                    q = cqlParser.parse(q.toCQL())
                    resultSets.append(db.search(session, q))
                else:
                    raise ValueError("%s not in %r" % (dbname, self.session.configs.keys()))
            if len(resultSets) > 1:
                rs = resultSets[0]
                for r in resultSets[1:]:
                    rs.combine(r)
            elif len(resultSets) == 1:
                rs = resultSets[0]
            else:
                # No resultset.
                return self.encode(('searchResponse', resp))

            resp.resultCount = len(rs)
            # Maybe put it into our DB
            if session.resultSets.has_key(rsetname):
                rsid = session.resultSets[rsetname]
                rs.id = rsid
                session.resultSetStore.store_resultSet(session, rs)
            else:
                rsid = session.resultSetStore.create_resultSet(session, rs)
                session.resultSets[rsetname] = rsid
            # only keep 4 at once
            keys = session.resultSetCache.keys()
            if len(keys) > 3:
                # delete one at random
                r = rand.randint(0,3)
                del session.resultSetCache[keys[r]]
            session.resultSetCache[rsid] = rs

        except Exception, err:
            # XXX add -correct- diagnostic
            resp.numberOfRecordsReturned = 1
            resp.nextResultSetPosition = 0
            resp.resultSetStatus = 3           
            d = self.generate_diagnostic(err)
            diag = ('nonSurrogateDiagnostic', d)
            resp.records = diag
        return self.encode(('searchResponse', resp))

    def handleScan(self, session, data):
        if (hasattr(data, 'stepSize')):
            step = data.stepSize
        else:
            step = 0
        resp = ScanResponse()
        resp.stepSize = step
        resp.scanStatus = 1
        resp.numberOfEntriesReturned = 0
        resp.positionOfTerm = 0

        try:
            dbs = data.databaseNames
            if len(dbs) != 1:
                # Can only scan one db at once? (XXX)
                raise ValueError
            nt = data.numberOfTermsRequested
            rp = data.preferredPositionInResponse
            if (rp < 0 or rp > (nt+1)):
                # Busted numbers (XXX)
                raise ValueError
            dbname = dbs[0]
            cfg = self.session.configs.get(dbname, None)
            db = cfg.parent
            session.database = db.id
            where = data.termListAndStartPoint
            # Make it look like part of an RPN query...
            w = ('op', ('attrTerm', where))
            clause = CQLUtils.rpn2cql(w, cfg)                     
            if not clause.term.value:
                clause.term.value = 'a'
            nstms = nt * (step + 1)
            terms = []
            clause = cqlParser.parse(clause.toCQL())
            if (rp == 1):
                data = db.scan(session, clause, nstms, direction=">=")
            elif (rp == 0):
                data = db.scan(session, clause, nstms, direction=">")
            elif (rp == mt):
                data = db.scan(session, clause, nstms, direction="<=")
                data.reverse()
            elif (rp == mt+1):
                data = db.scan(session, clause, nstms, direction="<")
                data.reverse()
            else:
                # Need to go up and down
                data1 = db.scan(session, clause, nt-rp+1, direction=">=")
                data = db.scan(session, clause, rp, direction="<=")
                if data1[0][0] == data[0][0]:
                    data = data[1:]
                data.reverse()
                data.extend(data1)
            
            for d in data[::step+1]:
                t = TermInfo()
                t.term = ('general', d[0])
                t.globalOccurrences = d[1][1]
                terms.append(('termInfo', t))
            resp.positionOfTerm = rp
            resp.numberOfEntriesReturned = len(terms)
            resp.scanStatus = 0
            l = ListEntries()
            l.entries = terms
            resp.entries = l
        except Exception, err:
            l = ListEntries()
            d = self.generate_diagnostic(err)
            d.condition = 123
            diag = [('defaultFormat', d)]
            l.nonsurrogateDiagnostics = diag
            resp.entries = l
            resp.numberOfEntriesReturned = 0
            resp.scanStatus = 6
        return self.encode(('scanResponse', resp))

    def handlePresent(self, session, data):
        resp = PresentResponse()
        resp.numberOfRecordsReturned = 0
        resp.presentStatus = 1
        try:
            rsid = self.session.resultSets[data.resultSetId]
            if session.resultSetCache.has_key(rsid):
                resultset = session.resultSetCache[rsid]
            else:
                resultset = self.session.resultSetStore.fetch_resultSet(self.session, rs)
            f = data.resultSetStartPoint
            n = data.numberOfRecordsRequested
            recSyntax = data.preferredRecordSyntax
            recSynStr = '.'.join([str(x) for x in recSyntax.lst])

            records = []
            for x in range(f-1, min(f+n-1, len(resultset))):
                rec = resultset[x].fetch_record(session)
                db = resultset[x].database
                dbname = dbmap[db]
                cfg = self.session.configs.get(dbname, None)
                if not cfg or not cfg.transformerHash.has_key(recSynStr):
                    # XXX: Diagnostic 239 // recsyn not supported
                    raise ValueError("RecordSyntax not supported: %r" % (recSynStr))
                else:
                    esns = cfg.transformerHash[recSynStr]
                recSchema = data.recordComposition
                esnType = recSchema[0]
                if (esnType == "simple"):
                    esn = recSchema[1][1].lower()
                else:
                    raise NotImplementedError
                if not esns.has_key(esn):
                    raise ValueError("%s: %s" % (esn, repr(esns)))
                else:
                    txr = esns[esn]

                if (txr):
                    self.log("starting transformation")
                    if isinstance(txr, Transformer):
                        doc = txr.process_record(session, rec)
                    elif isinstance(txr, Workflow):
                        doc = txr.process(session, rec)
                    else:
                        raise ValueError
                    docdata = doc.get_raw(session)
                    self.log("finished transform")
                else:
                    docdata = rec.get_xml(session)
                r = NamePlusRecord()
                r.name = dbname
                xr = asn1.EXTERNAL()
                xr.direct_reference= recSyntax
                if (recSynStr == "1.2.840.10003.5.105"):
                    # GRS-1
                    if not type(docdata) == type([]):
                        xr.encoding = ('single-ASN1-type', [docdata])
                    else:
                        xr.encoding = ('single-ASN1-type', docdata)
                else:                    
                    xr.encoding = ('octet-aligned', docdata)
                r.record = ('retrievalRecord', xr)
                records.append(r)
                resp.records = ('responseRecords', records)
            resp.numberOfRecordsReturned = len(records) 
            resp.nextResultSetPosition = f + len(records)
            resp.presentStatus = 0
            # Don't want to log the full records!
            # self.log(resp)
        except Exception, err:
            d = self.generate_diagnostic(err)
            d.condition = 123
            resp.records = ('nonSurrogateDiagnostic', d)
            resp.presentStatus = 5
            resp.numberOfRecordsReturned = 0
            resp.nextResultSetPosition = 0
        self.log("encoding present response")
        return self.encode(('presentResponse', resp))

    def handleClose(self, session, data):
        resp = Close()
        resp.closeReason = 0
        resp.diagnosticInformation = "Normal Close"
        return self.encode(('close', resp))

    # XXX Implement
    def handleSort(self, session, data):
        resp = SortResponse()
        resp.sortStatus = 1
        resp.resultSetStatus = 1
        resp.resultCount = 1
        return self.encode(('sortResponse', resp))

    def handleDeleteResultSet(self, data):
        resp = DeleteResultSetResponse()
        resp.deleteOperationStatus = 0
        resp.numberNotDeleted = 0
        resp.deleteMessage = "No Resultset"
        return self.encode(('deleteResultSetResponse', resp))

    def handleExtendedServices(self, data):
        # Can't generate Z's packages anywhere?!
        # Just ILL and YAZ's adm ones. Urgh.
        self.log(str(data))
        # Spit back a Dunno What You Mean response
        resp = ExtendedServicesResponse()
        resp.operationStatus = 3
        return self.encode(('extendedServicesResponse', resp))

    def search_explain(self, query):
        # Just messing around
        ti = TargetInfo()
        ti.name = "Fish"
        self.log(str(ti))



# try building just one
handler = ZHandler()



def connectionhandler(conn):
    # Apache level stuff

    if (conn.local_addr[1] not in [210, 2100]):
        return apache.DECLINED
    try:
        session.resultSets = {}
        session.resultSetCache = {}
        handler.connection = conn
        handler.read()
        handler.connection = None
        # Finished. Clean up.
	try:
	    session.resultSetStore.commit_storing(session)
	except:
	    pass


    except Exception, err:
        data = '\n'.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
        try:
            session.logger.log(session, data)
            session.logger.fileh.flush()
        except:
            sys.stderr.write(data)
            sys.stderr.flush()
    
    return apache.OK
