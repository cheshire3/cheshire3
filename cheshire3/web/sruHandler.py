"""SRU ProtocolHandler."""

import sys
import os
import re

from lxml import etree
from lxml.builder import ElementMaker

from cheshire3.baseObjects import Session
from cheshire3.server import SimpleServer
from cheshire3 import cqlParser
from cheshire3.internal import cheshire3Version, cheshire3Root
from cheshire3 import exceptions as c3errors


class SRUProtocolHandler(object):
    """SRU Protocol Handling Abstract Base Class."""

    def __init__(self, session, configs):
        self.session = session
        self.configs = configs

    def record(self, schema="", packing="",
               data="", identifier="", position=""):
        rec = elemFac.record(elemFac.recordSchema(schema),
                             elemFac.recordPacking(packing))
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
        t = elemFac.term(elemFac.value(value),
                         elemFac.numberOfRecords(str(num)))
        if where:
            t.append(elemFac.whereInList(where))
        return t

    def echoedQuery(self, opts):
        oname = opts['operation']
        oname = oname[0].upper() + oname[1:]
        name = "echoed%sRequest" % oname

        echo = getattr(elemFac, name)()
        extras = []
        for (k, v) in opts.iteritems():
            if k[:2] == 'x-':
                # accumulate and include at end
                k = k[2:]
                extras.append((k, v))
            x = getattr(elemFac, k)()
            if isinstance(v, etree._Element):
                x.append(v)
            else:
                x.text = str(v)
            echo.append(x)
        if extras:
            extra = elemFac.extraRequestData()
            for x, e in enumerate(extras):
                # find real name from config
                try:
                    (ns, nm) = self.session.config.sruExtensionMap[e[0]][:2]
                except KeyError:
                    # diagnostic for unsupported extension?
                    continue
                txt = ('<extns%s:%s xmlns:extns%s="%s">%s</extns%s:%s>'
                       '' % (x + 1, nm, x + 1, ns, e[1], x + 1, nm))
                node = etree.XML(txt)
                extra.append(node)
            echo.append(extra)
        echo.append(elemFac.baseUrl(self.session.path))
        return echo

    def extraData(self, eType, opts, result, *args):
        session = self.session
        nodes = []
        for (k, v) in opts.iteritems():
            if k[:2] == "x-":
                try:
                    (typ, fn, srw) = session.config.sruExtensionMap[k]
                except KeyError:
                    try:
                        (typ, fn, srw) = session.config.sruExtensionMap[k[2:]]
                    except KeyError:
                        # Unsupported extension
                        continue

                if not isinstance(srw, tuple):
                    # Old style - i.e. in srwExtensions
                    # (uri, name) pairs previously used as keys for
                    # xxxExtensionHash
                    srw = (typ, fn)
                    hashAttr = eType + "ExtensionHash"
                    curr = getattr(session.config, hashAttr)
                    try:
                        fn = curr[srw]
                    except KeyError:
                        continue
                    else:
                        typ = eType

                if (typ == eType or
                    (eType == 'response' and typ == opts['operation'])):
                    node = fn(session, v, result, *args)
                    if node is not None:
                        nodes.append(node)
        if nodes:
            eName = 'extra%s%sData' % (eType[0].upper(), eType[1:])
            extra = getattr(elemFac, eName)()
            for n in nodes:
                extra.append(n)
            result.append(extra)

    def diagnostic(self, code, msg="", details=""):
        err = cqlParser.Diagnostic(code)
        err.message = msg
        err.details = details
        return err

    def diagnosticToXml(self, diag):
        x = diagElemFac.diagnostic(
                # URI already contains code
                #elemFac.uri("%s%s" % (diag.uri, diag.code))
                diagElemFac.uri(diag.uri)
            )
        if diag.message:
            x.append(diagElemFac.message(diag.message))
        if diag.details:
            x.append(diagElemFac.details(diag.details))
        return x

    def processUnknownOperation(self, err, config):
        result = elemFac.explainResponse(elemFac.version('1.2'))
        d = elemFac.diagnostics(self.diagnosticToXml(err))
        result.append(d)
        # add explain record
        result = self.process_explain({}, result)
        return result

    def process_explain(self, opts, result):
        session = self.session
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
            nsHash = {'zrx': "http://explain.z3950.org/dtd/2.0/",
                      'c3': "http://www.cheshire3.org/schemas/explain/"}
            et = etree.XML(filestr)
            dbNode = et.xpath('//zrx:explain/zrx:databaseInfo',
                              namespaces=nsHash)[0]
            try:
                impNode = dbNode.xpath('//zrx:implementation',
                                       namespaces=nsHash)[0]
            except IndexError:
                impNode = etree.XML(
                '<implementation identifier="http://www.cheshire3.org" '
                'version="%d.%d.%d">'
                '<title>Cheshire3 SRW/U Server</title>'
                '<agents>'
                '<agent type="vendor">The University of Liverpool</agent>'
                '</agents>'
                '</implementation>' % cheshire3Version)
                dbNode.append(impNode)

            if db.totalItems:
                try:
                    extNode = dbNode.xpath('//zrx:extent',
                                           namespaces=nsHash)[0]
                except IndexError:
                    etree.SubElement(dbNode,
                                     'extent',
                                     {'numberOfRecords': str(db.totalItems)})
                else:
                    extNode.set('numberOfRecords', str(db.totalItems))

            if db.lastModified:
                try:
                    histNode = dbNode.xpath('//zrx:history',
                                            namespaces=nsHash)[0]
                except IndexError:
                    # create history and append node
                    etree.SubElement(dbNode,
                                     'history',
                                     {'lastUpdate': db.lastModified})
                else:
                    histNode.set('lastUpdate', db.lastModified)
            # Serialize modified record to string
            filestr = etree.tostring(et)

        # Create a record object and populate
        rec = self.record(schema=recordMap['zeerex'],
                          packing=opts.get('recordPacking', 'xml'),
                          data=filestr)
        self.extraData('record', opts, rec)
        result.append(rec)
        return result

    def process_searchRetrieve(self, opts, result):
        session = self.session
        if 'query' in opts:
            q = cqlParser.parse(opts['query'])
            q.config = session.config
            opts['xQuery'] = etree.XML(q.toXCQL())
        else:
            raise self.diagnostic(7,
                                  msg="Mandatory parameter not supplied",
                                  details='query')

        db = session.config.parent
        session.database = db.id
        rss = db.get_object(session, 'defaultResultSetStore')

        recordMap.update(session.config.recordNamespaces)
        schema = opts.get('recordSchema', '')
        if not schema and hasattr(session.config, 'defaultRetrieveSchema'):
            schema = session.config.defaultRetrieveSchema
        if (schema in recordMap):
            schema = recordMap[schema]
        if (schema and not
            (schema in session.config.recordNamespaces.values())):
            raise self.diagnostic(66,
                                  msg="Unknown schema for retrieval",
                                  details=schema)
        txr = session.config.transformerHash.get(schema, None)

        recordPacking = opts.get('recordPacking', 'xml')
        if not recordPacking  in ["string", "xml"]:
            raise self.diagnostic(71,
                                  msg="Unsupported record packing",
                                  details=recordPacking)

        # Fencepost.  SRW starts at 1, C3 starts at 0
        startRecord = opts.get('startRecord', 1) - 1

        maximumRecords = opts.get('maximumRecords', -1)
        if maximumRecords < 0:
            if hasattr(session.config, 'defaultNumberOfRecords'):
                maximumRecords = session.config.defaultNumberOfRecords
            else:
                maximumRecords = 1
        ttl = opts.get('resultSetTTL', 0)

        try:
            rsn = q.getResultSetId()
        except c3errors.ConfigFileException as e:
            d = self.diagnostic(10, msg='Query syntax error.')
            if e.reason == "Zeerex does not have default context set.":
                d.message = ('Query syntax error. Database has no default '
                             'context set for indexes. You must supply a '
                             'context set for each index.')
            raise d

        try:
            rs = db.search(session, q)
        except c3errors.ObjectDoesNotExistException as e:
            raise self.diagnostic(16,
                                  msg='Unsupported index',
                                  details=e.reason)
        except c3errors.QueryException as e:
            raise self.diagnostic(24,
                                  msg='Unsupported combination of relation '
                                  'and term',
                                  details=e.reason)
        session.currentResultSet = rs
        result.append(elemFac.numberOfRecords(str(len(rs))))
        if (len(rs)):
            recs = elemFac.records()
            if (ttl and not rsn):
                rs.expires = ttl
                rsn = rss.create_resultSet(session, rs)
            end = min(startRecord + maximumRecords, len(rs))

            for rIdx in range(startRecord, end):
                rsi = rs[rIdx]
                r = rsi.fetch_record(session)

                if (txr is not None):
                    doc = txr.process_record(session, r)
                    xml = doc.get_raw(session)
                else:
                    xml = r.get_xml(session)
                xml = xmlVerRe.sub("", xml)
                # Fencepost. SRW starts at 1, C3 starts at 0
                rec = self.record(schema=schema,
                                  packing=recordPacking,
                                  data=xml,
                                  identifier=str(rsi),
                                  position=rIdx + 1)
                self.extraData('record', opts, rec, rsi, r)
                recs.append(rec)

            if rsn:
                result.append(elemFac.resultSetId(rsn))
                result.append(elemFac.resultSetIdleTime(str(ttl)))
            result.append(recs)
            nrp = end + 1
            if (nrp < len(rs) and nrp > 0):
                result.append(elemFac.nextRecordPosition(str(nrp)))
        self.extraData('searchRetrieve', opts, result, rs, db)
        return result

    def process_scan(self, opts, result):
        session = self.session
        db = session.config.parent
        session.database = db.id
        if 'scanClause' in opts:
            q = cqlParser.parse(opts['scanClause'])
            opts['xQuery'] = etree.XML(q.toXCQL())
        else:
            raise self.diagnostic(7,
                                  msg="Mandatory parameter not supplied",
                                  details='scanClause')
        mt = opts.get('maximumTerms', 20)
        rp = opts.get('responsePosition', 0)
        if (rp < 0 or rp > (mt + 1)):
            raise self.diagnostic(120,
                                  msg="Response position out of range",
                                  details=str(rp))
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
        elif (rp == mt + 1):
            data = db.scan(session, q, mt, direction="<")
            data.reverse()
        else:
            # Need to go up and down
            data1 = db.scan(session, q, mt - rp + 1, direction=">=")
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


def get_configsFromServer(session, serv):
    # Find configs for databases permitted to be served by SRU
    configs = {}
    if len(serv.databaseConfigs) < 25:
        # Relatively few dbs - we can safely cache them
        serv._cacheDatabases(session)
        for db in serv.databases.itervalues():
            if (db.get_setting(session, 'SRW') or db.get_setting(session, 'srw') or
                db.get_setting(session, 'SRU') or db.get_setting(session, 'sru')):
                db._cacheProtocolMaps(session)
                map = db.protocolMaps.get('http://www.loc.gov/zing/srw/', None)
                # Check that there's a path and that it can actually be requested
                # from this handler
                if (map is not None):
                    map2 = db.protocolMaps.get(
                        'http://www.loc.gov/zing/srw/update/',
                        None
                    )
                    configs[map.databaseUrl] = {
                        'http://www.loc.gov/zing/srw/': map,
                        'http://www.loc.gov/zing/srw/update/': map2
                    }
    else:
        # Too many dbs to cache in memory
        for dbid, conf in serv.databaseConfigs.iteritems():
            db = serv.get_object(session, dbid)
            session.database = dbid
            if (db.get_setting(session, 'SRW') or db.get_setting(session, 'srw') or
                db.get_setting(session, 'SRU') or db.get_setting(session, 'sru')):
                db._cacheProtocolMaps(session)
                pmap = db.protocolMaps.get('http://www.loc.gov/zing/srw/', None)
                if (pmap is not None):
                    configs[pmap.databaseUrl] = (
                        dbid,
                        {'http://www.loc.gov/zing/srw/': pmap.id}
                    )
                    pmap2 = db.protocolMaps.get(
                        'http://www.loc.gov/zing/srw/update/',
                        None
                    )
                    if pmap2 is not None:
                        configs[pmap.databaseUrl][1].update(
                            {'http://www.loc.gov/zing/srw/update/': pmap2.id}
                        )
            # Remove cached db object
            try:
                del serv.objects[dbid]
            except KeyError:
                pass
    
        del dbid, db, pmap, pmap2
    return configs


# Cheshire3 architecture
session = Session()
session.environment = "apache"
serv = SimpleServer(session, os.path.join(cheshire3Root,
                                          'configs',
                                          'serverConfig.xml'))

protocolMap = {
    'sru': 'http://www.loc.gov/zing/srw/',
    'diag': 'http://www.loc.gov/zing/srw/diagnostic/'
}

recordMap = {
    'dc': 'info:srw/schema/1/dc-v1.1',
    'diag': 'info:srw/schema/1/diagnostic-v1.1',
    'mods': 'info:srw/schema/1/mods-v3.0',
    'onix': 'info:srw/schema/1/onix-v2.0',
    'marcxml': 'info:srw/schema/1/marcxml-v1.1',
    'ead': 'info:srw/schema/1/ead-2002',
    'ccg': 'http://srw.o-r-g.org/schemas/ccg/1.0/',
    'marcsgml': 'http://srw.o-r-g.org/schemas/marcsgml/12.0/',
    'zthes': 'http://zthes.z3950.org/xml/zthes-05.dtd',
    'zeerex': 'http://explain.z3950.org/dtd/2.0/',
    'rec': 'info:srw/schema/2/rec-1.0',
}


elemFac = ElementMaker(namespace=protocolMap['sru'], nsmap=protocolMap)
diagElemFac = ElementMaker(namespace=protocolMap['diag'], nsmap=protocolMap)
xmlVerRe = re.compile("[ ]*<\?xml[^>]+>")
