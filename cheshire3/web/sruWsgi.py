"""SRU WSGI Application."""

from urllib import quote
from cgi import FieldStorage

from sruHandler import *


class SRUWsgiHandler(SRUProtocolHandler):
    """SRU Request Handling Class for WSGI."""

    def _app_base(self, environ):
        scheme = environ['wsgi.url_scheme']
        url = [scheme]
        url.append('://')
        try:
            url.append(environ['HTTP_HOST'])
        except KeyError:
            url.append(environ['SERVER_NAME'])
            if scheme == 'httpd':
                if environ['SERVER_PORT'] != '443':
                    url.append(':')
                    url.append(environ['SERVER_PORT'])
            else:
                if environ['SERVER_PORT'] != '80':
                    url.append(':')
                    url.append(environ['SERVER_PORT'])

        url.append(quote(environ.get('SCRIPT_NAME', '')))
        return ''.join(url)

    def _path_base(self, environ):
        url = [self._app_base(environ)]
        url.append(quote(environ.get('PATH_INFO', '')))
        return ''.join(url)

    def _reconstruct_url(self, environ):
        url = [self._path_base(environ)]
        if environ.get('QUERY_STRING'):
            url.append('?')
            url.append(environ['QUERY_STRING'])
        return ''.join(url)

    def __call__(self, environ, start_response):
        session = self.session
        path = '/'.join([
                         environ.get('SCRIPT_NAME', '').strip('/'),
                         environ.get('PATH_INFO', '').strip('/')
                         ])
        out = []
        if path not in configs:
            # Unknown endpoint
            # No specification
            out.append(
                '<databases numberOfDatabases="{0}">'.format(len(configs))
            )
            for k in sorted(configs.keys()):
                out.append("<database><path>{0}</path></database>".format(k))
            out.append('</databases>')
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
                # Rediscover objects
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
            session.path = self._path_base(environ)
            session.config = config
            store = FieldStorage(fp=environ['wsgi.input'], environ=environ)
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
            out.append('<?xml version="1.0"?>')
            if 'stylesheet' in opts:
                out.append(
                    '<?xml-stylesheet type="text/xsl" '
                    'href="{0}"?>'.format(opts['stylesheet'])
                )
            out.append(etree.tostring(result, pretty_print=True))
            if len(serv.databaseConfigs) >= 25:
                # Cleanup memory
                try:
                    del serv.objects[config.parent.id]
                except KeyError:
                    pass
        response_headers = [('Content-Type',
                             'application/xml'),
                            ('Content-Length',
                             str(sum([len(d) for d in out])))
                            ]
        start_response("200 OK", response_headers)
        return out


def environment_application(environ, start_response):
    status = '200 OK'
    output = ["{0}\n".format(i) for i in environ.iteritems()]
    response_headers = [('Content-Type', 'text/plain'),
                        ('Content-Length', str(sum([len(i) for i in output])))]
    start_response(status, response_headers)
    return output


def main():
    """Start up a simple app server to serve the SRU application."""
    from wsgiref.simple_server import make_server
    try:
        host = sys.argv[1]
    except IndexError:
        try:
            import socket
            host = socket.gethostname()
        except:
            host = 'localhost'
    try:
        port = int(sys.argv[2])
    except IndexError, ValueError:
        port = 8000
    httpd = make_server(host, port, application)
    print """You will be able to access the application at:
http://{0}:{1}""".format(host, port)
    httpd.serve_forever()


configs = get_configsFromServer(session, serv)
application = SRUWsgiHandler(session, configs)


if __name__ == "__main__":
    sys.exit(main())
