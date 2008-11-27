 
from mod_python import apache
from mod_python.util import FieldStorage
import os, re
from xml.sax.saxutils import escape
from lxml import etree
from lxml.builder import ElementMaker

from cheshire3.server import SimpleServer
from cheshire3.baseObjects import Session
from cheshire3.utils import flattenTexts
from cheshire3 import cqlParser
from cheshire3 import internal

cheshirePath = os.environ.get('C3HOME', '/home/cheshire')

session = Session()
session.environment = "apache"
serv = SimpleServer(session, os.path.join(cheshirePath, 'cheshire3', 'configs', 'serverConfig.xml'))

configs = {}
serv._cacheDatabases(session)
for db in serv.databases.values():
    if db.get_setting(session, 'SRW') or db.get_setting(session, 'srw'):
        db._cacheProtocolMaps(session)
        map = db.protocolMaps.get('http://www.loc.gov/zing/srw/', None)
        map2 = db.protocolMaps.get('http://www.loc.gov/zing/srw/update/', None)
        configs[map.databaseUrl] = {'http://www.loc.gov/zing/srw/' : map,
                                    'http://www.loc.gov/zing/srw/update/' : map2}

protocolMap ={
    'sru' : 'http://www.loc.gov/zing/srw/',
    'diag' : 'http://www.loc.gov/zing/srw/diagnostic/'
    }

recordMap = {
    'dc' : 'info:srw/schema/1/dc-v1.1',
    'diag' : 'info:srw/schema/1/diagnostic-v1.1',
    'mods' : 'info:srw/schema/1/mods-v3.0',
    'onix' : 'info:srw/schema/1/onix-v2.0',
    'marcxml' : 'info:srw/schema/1/marcxml-v1.1',
    'ead' : 'info:srw/schema/1/ead-2002',
    'ccg' : 'http://srw.o-r-g.org/schemas/ccg/1.0/',
    'marcsgml' : 'http://srw.o-r-g.org/schemas/marcsgml/12.0/',
    'zthes' : 'http://zthes.z3950.org/xml/zthes-05.dtd',
    'zeerex' : 'http://explain.z3950.org/dtd/2.0/',
    'rec' : 'info:srw/schema/2/rec-1.0',
    }

elemFac = ElementMaker(namespace=protocolMap['sru'], nsmap=protocolMap)
xmlVerRe = re.compile("[ ]*<\?xml[^>]+>")

class reqHandler:

    def send_xml(self, text, req, code=200):
        req.content_type = 'text/xml'
        req.content_length = len(text)
        req.send_http_header()
        req.write(text)


    def diagnostic(self, code, msg="", details=""):
        err = cqlParser.Diagnostic()
        err.code = code
        err.message = msg
        err.details = details
        return err

    def record(self, schema="", packing="", data="", identifier="", position=""):
        rec = elemFac.record(elemFac.recordSchema(schema), elemFac.recordPacking(packing))
        if packing == "xml":
            data = etree.XML(data)
            d = elemFac.recordData()
            d.append(data)
            rec.append(d)
        else:
            rec.append(elemFac.recordData(data))
        if identifier:
            rec.append(elemFac.recordIdentifier(str(identifier)))
        if position:
            rec.append(elemFac.recordPosition(str(position)))
        return rec                      

        
    def term(self, value="", num="", where=""):
        t = elemFac.term(elemFac.value(value), elemFac.numberOfRecords(str(num)))
        if where:
            t.append(elemFac.whereInList(where))
        return t


    def echoedQuery(self, opts):
        oname = opts['operation']
        oname = oname[0].upper() + oname[1:]
        name = "echoed%sRequest" % oname

        echo = getattr(elemFac, name)()
        extras = []
        for (k,v) in opts.items():
            if k[:2] == 'x-':
                # accumulate and include at end
                extras.append((k,v))
            x = getattr(elemFac, k)()
            if isinstance(v, etree._Element):
                x.append(v)
            else:
                x.text = str(v)
            echo.append(x)
        if extras:
            extra = elemFac.extraRequestData()
            x = 1
            for e in extras:
                # find real name from config
                (ns, nm) = session.config.sruExtensionMap[e[0]][2]
                txt = '<extns%s:%s xmlns:extns%s="%s">%s</extns%s:%s>' % (x, nm, x, ns, e[1], x, nm)
                x += 1
                node = etree.XML(txt)
                extra.append(node)
            echo.append(extra)
        echo.append(elemFac.baseUrl(session.path))
        return echo

    def extraData(self, eType, opts, result, *args):
        nodes = []
        for (k,v) in opts.items():
            if k[:2] == "x-" and k in session.config.sruExtensionMap:
                (typ, fn, srw) = session.config.sruExtensionMap[k]
                if typ == eType or (eType == 'response' and typ == opts['operation']):
                    node = fn(session, v, result, *args)
                    if node != None:
                        nodes.append(node)
        if nodes:
            eName = 'extra%s%sData' % (eType[0].upper(), eType[1:])
            extra = getattr(elemFac, eName)()
            for n in nodes:
                extra.append(n)
            result.append(extra)
                        

    def diagnosticToXml(self, diag):
        x = elemFac.diagnostic(
            elemFac.uri("%s%s" % (diag.uri, diag.code))
            )
        if diag.details:
            x.append(elemFac.details(diag.details))
        if diag.message:
            x.append(elemFac.message(diag.message))
        return x

    def processUnknownOperation(self, err):
        result = elemFac.explainResponse(elemFac.version('1.2'))
        # add explain record
        result = self.process_explain({}, result)
        d = elemFac.diagnostics(self.diagnosticToXml(err))
        result.append(d)
        return result

    def process_explain(self, opts, result):
        p = session.config.get_path(session, 'zeerexPath')
        if (not os.path.isabs(p)):
            p2 = session.config.get_path(session, 'defaultPath')
            p = os.path.join(p2, p)
        try:
            f = open(p, "r")
        except:
            pass
        else:
            filestr = f.read()
            f.close()
            # insert some database metadata
            db = session.config.parent
            session.database = db.id

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
                </implementation>''' % internal.cheshireVersion)
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
        rec = self.record(schema=recordMap['zeerex'],
                          packing=opts.get('recordPacking', 'xml'),
                          data=filestr)
        self.extraData('record', opts, rec)
        result.append(rec)
        return result

    def process_searchRetrieve(self, opts, result):

        if 'query' in opts:
            q = cqlParser.parse(opts['query'])
            q.config = session.config
            opts['xQuery'] = etree.XML(q.toXCQL())
        else:
            raise self.diagnostic(7, "Mandatory 'query' parameter not supplied", 'query')

        db = session.config.parent
        session.database = db.id
        rss = db.get_object(session, 'defaultResultSetStore')

        schema = opts.get('recordSchema', '')
        if not schema and hasattr(session.config, 'defaultRetrieveSchema'):
            schema = session.config.defaultRetrieveSchema
        if (schema in recordMap):
            schema = recordMap[schema]
        if (schema and not schema in recordMap.values()):
            raise self.diagnostic(66, details=schema)
        txr = session.config.transformerHash.get(schema, None)

        recordPacking = opts.get('recordPacking', 'xml')
        if not recordPacking  in ["string", "xml"]:
            raise self.diagnostic(71, details=recordPacking)

        # Fencepost.  SRW starts at 1, C3 starts at 0
        startRecord = opts.get('startRecord', 1) -1

        maximumRecords = opts.get('maximumRecords', -1)
        if maximumRecords < 0:
            if hasattr(session.config, 'defaultNumberOfRecords'):
                maximumRecords = session.config.defaultNumberOfRecords
            else:
                maximumRecords = 1
        ttl = opts.get('resultSetTTL', 0)
        rsn = q.getResultSetId()

        rs = db.search(session, q)        
        session.currentResultSet = rs
        result.append(elemFac.numberOfRecords(str(len(rs))))

        if (len(rs)):
            recs = elemFac.records()
            if (ttl and not rsn):
                rs.expires = ttl
                rsn = rss.create_resultSet(session, rs)
            end = min(startRecord+maximumRecords, len(rs))

            for rIdx in range(startRecord, end):
                rsi = rs[rIdx]
                r = rsi.fetch_record(session)

                if (txr != None):
                    doc = txr.process_record(session, r)
                    xml = doc.get_raw(session)
                else:
                    xml = r.get_xml(session)
                xml = xmlVerRe.sub("", xml)
                rec = self.record(schema=schema, packing=recordPacking,
                                  data=xml, identifier=str(rsi), position=rIdx)
                self.extraData('record', opts, rec, rsi, r)
                recs.append(rec)

            if rsn:
                result.append(elemFac.resultSetId(rsn))
                result.append(elemFac.resultSetIdleTime(str(ttl)))
            result.append(recs)
            
            nrp = end + 1
            if ( nrp < len(rs) and nrp > 0):
                result.append(elemFac.nextRecordPosition(str(nrp)))
        return result


    def process_scan(self, opts, result):
        db = session.config.parent
        session.database = db.id

        if 'scanClause' in opts:
            q = cqlParser.parse(opts['scanClause'])
            opts['xQuery'] = etree.XML(q.toXCQL())
        else:
            raise self.diagnostic(7, "Missing 'scanClause' parameter", 'scanClause')

        mt = opts.get('maximumTerms', 20)
        rp = opts.get('responsePosition', 0)
        if (rp < 0 or rp > (mt+1)):
            raise self.diagnostic(120, "Response position out of range", str(rp))

        if (not q.term.value):
            q.term.value = chr(0)

        q.config = session.config

        if (rp == 1):
            data = db.scan(session, q, mt, direction=">=")
        elif (rp == 0):
            data = db.scan(session, q, mt, direction=">")
        elif (rp == mt):
            data = db.scan(session, q, mt, direction="<=")
            data.reverse()
        elif (rp == mt+1):
            data = db.scan(session, q, mt, direction="<")
            data.reverse()
        else:
            # Need to go up and down
            data1 = db.scan(session, q, mt-rp+1, direction=">=")
            data = db.scan(session, q, rp, direction="<=")
            if data1[0][0] == data[0][0]:
                data = data[1:]
            data.reverse()
            data.extend(data1)

        terms = elemFac.terms()
        for d in data:
            t = self.term(value=d[0], num=d[1][1])
            self.extraData('term', opts, t, d)
            terms.append(t)
        result.append(terms)
        return result


    def dispatch(self, req):
        path = req.uri[1:]
        if (path[-1] == "/"):
            path = path[:-1]
            
        if not configs.has_key(path):
            # unknown endpoint
            # no specification
            xml = ['<databases numberOfDatabases="%d">' % (len(configs))]
            for k in sorted(configs.keys()):
                xml.append("<database><path>%s</path></database>" % k)
            xml.append('</databases>')
            txt = ''.join(xml)
            self.send_xml(txt, req)
        
        else:
            config = configs[path]['http://www.loc.gov/zing/srw/']
            session.path = "http://%s/%s" % (req.hostname, path)
            session.config = config
            store = FieldStorage(req)
            opts = {}
            for qp in store.list:
                if qp.value.isdigit():
                    opts[qp.name] = int(qp.value)
                else:
                    opts[qp.name] = qp.value
                
            if not opts:
                opts = {
                    'operation' : 'explain',
                    'version' : '1.2',
                    'recordPacking' : 'xml'
                    }
            if not 'operation' in opts:
                err = self.diagnostic(7, "Mandatory 'operation' parameter not supplied", 'operation')
                result = self.processUnknownOperation(err, config)
            elif not opts['operation'] in ['explain', 'searchRetrieve', 'scan']:
                err = self.diagnostic(4, "Unknown Operation", opts['operation'])
                result = self.processUnknownOperation(err, config)
            else:
                respName = "%sResponse" % opts['operation']
                result = getattr(elemFac, respName)()
                v = elemFac.version('1.2')
                result.append(v)
                
                if not 'version' in opts:
                    err = self.diagnostic(7, "Mandatory 'version' parameter not supplied", 'version')
                    dx = self.diagnosticToXml(err)
                    x = elemFac.diagnostics()
                    x.append(dx)
                    result.append(x)
                else:
                    fn = getattr(self, 'process_%s' % opts['operation'])
                    try:
                        fn(opts, result)
                    except cqlParser.Diagnostic as d:
                        diags = elemFac.diagnostics(self.diagnosticToXml(d))
                        result.append(diags)
                    result.append(self.echoedQuery(opts))
                    self.extraData('response', opts, result)
                    session.currentResultSet = None

            text = etree.tostring(result, pretty_print=True)
            if 'stylesheet' in opts:
                text = u'<?xml version="1.0"?>\n<?xml-stylesheet type="text/xsl" href="%s"?>\n%s' % (opts['stylesheet'], text) 
            else:
                text = u'<?xml version="1.0"?>\n%s' % text

            self.send_xml(text, req)
        

srwh = reqHandler()        
def handler(req):
    # do stuff
    srwh.dispatch(req)
    return apache.OK

