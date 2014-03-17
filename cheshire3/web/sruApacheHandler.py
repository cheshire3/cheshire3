"""SRU mod_python handler."""

from mod_python import apache
from mod_python.util import FieldStorage

from sruHandler import *


class reqHandler(SRUProtocolHandler):

    def send_xml(self, text, req, code=200):
        req.content_type = 'text/xml'
        req.content_length = len(text)
        req.send_http_header()
        req.write(text)

    def dispatch(self, req):
        path = req.uri.strip('/')
        if path not in configs:
            # Unknown endpoint
            # No specification
            xml = ['<databases numberOfDatabases="%d">' % (len(configs))]
            for k in sorted(configs.keys()):
                xml.append("<database><path>%s</path></database>" % k)
            xml.append('</databases>')
            txt = ''.join(xml)
            self.send_xml(txt, req)
        else:
            dbconf = configs[path]
            if isinstance(dbconf, tuple):
                dbid = dbconf[0]
                db = serv.get_object(session, dbid)
                config = db.get_object(
                    session,
                    dbconf[1]['http://www.loc.gov/zing/srw/']
                )
            else:
                config = dbconf['http://www.loc.gov/zing/srw/']
            # Check db hasn't changed since instantiated
            db = config.parent
            # Attempt to find filepath for db metadata
            fp = db.get_path(session, 'metadataPath')
            if os.stat(fp).st_mtime > db.initTime:
                # rediscover objects
                dbid = db.id
                del db
                try:
                    del serv.objects[dbid]
                except KeyError:
                    pass
                try:
                    del serv.databases[dbid]
                except KeyError:
                    pass
                db = serv.get_object(session, dbid)
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
                    'operation': 'explain',
                    'version': '1.2',
                    'recordPacking': 'xml'
                    }
            if not 'operation' in opts:
                err = self.diagnostic(7,
                                      msg="Mandatory parameter not supplied",
                                      details='operation')
                result = self.processUnknownOperation(err, config)
            elif not opts['operation'] in ['explain',
                                           'searchRetrieve',
                                           'scan']:
                err = self.diagnostic(4,
                                      msg="Unsupported Operation",
                                      details=opts['operation'])
                result = self.processUnknownOperation(err, config)
            else:
                respName = "%sResponse" % opts['operation']
                result = getattr(elemFac, respName)()
                v = elemFac.version('1.2')
                result.append(v)
                if not 'version' in opts:
                    err = self.diagnostic(
                        7,
                        msg="Mandatory parameter not supplied",
                        details='version'
                    )
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
                text = (u'<?xml version="1.0"?>\n'
                        u'<?xml-stylesheet type="text/xsl" href="%s"?>\n'
                        u'%s' % (opts['stylesheet'], text))
            else:
                text = u'<?xml version="1.0"?>\n%s' % text
            self.send_xml(text, req)
            if len(serv.databaseConfigs) >= 25:
                # cleanup memory
                try:
                    del serv.objects[config.parent.id]
                except KeyError:
                    pass


configs = get_configsFromServer(session, serv)
srwh = reqHandler(session, configs)


def handler(req):
    # do stuff
    srwh.dispatch(req)
    return apache.OK
