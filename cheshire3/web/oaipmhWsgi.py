"""OAI-PMH WSGI Application."""

from urllib import quote
from cgi import FieldStorage
from xml.sax.saxutils import escape

from oaipmhHandler import *


class OAIPMHWsgiApplication(object):

    def __init__(self, session, configs, dbs):
        self.session = session
        self.configs = configs
        self.dbs = dbs

    def __call__(self, environ, start_response):
        global configs, oaiDcReader, c3OaiServers
        response_headers = [('Content-Type',
                             'application/xml')]
        path = '/'.join([
                         environ.get('SCRIPT_NAME', '').strip('/'),
                         environ.get('PATH_INFO', '').strip('/')
                         ])
        out = []
        if path not in self.configs:
            # Unknown endpoint
            # No specification
            # TODO: send proper OAI error?
            out.extend([
                '<c3:error xmlns:c3="http://www.cheshire3.org/schemas/error">'
                '<c3:details>{0}</c3:details>'.format(path),
                ('<c3:message>Incomplete or incorrect baseURL, requires a '
                 'database path from:'),
                '<c3:databases numberOfDatabases="{0}">'
                ''.format(len(self.configs))
            ])
            out.extend(['<c3:database>{0}</c3:database>'.format(dbp)
                        for dbp
                        in self.configs
                        ])
            out.extend([
                '</c3:databases>',
                '</c3:message>',
                '</c3:error>'
            ])
            start_response('404 NOT FOUND', response_headers)
            return out
        else:
            args = {}
            # Parse options out of request environ
            store = FieldStorage(fp=environ['wsgi.input'], environ=environ)            
            for qp in store.list:
                args[qp.name] = qp.value
            try:
                oaixml = MinimalOaiServer(c3OaiServers[path],
                                          c3OaiServers[path].metadataRegistry)
            except KeyError:
                oai = Cheshire3OaiServer(self.session, self.configs,
                                         self.dbs, path)
                c3OaiServers[path] = oai
                oaixml = MinimalOaiServer(oai, oai.metadataRegistry)
            try:
                out.append(oaixml.handleRequest(args))
            except DatestampError:
                try:
                    raise BadArgumentError('Invalid date format supplied.')
                except:
                    out.append(oaixml.handleException(args, sys.exc_info()))
            except C3Exception, e:
                out = ['<c3:error '
                       'xmlns:c3="http://www.cheshire3.org/schemas/error" ',
                       'code="{0}">'
                       ''.format(str(e.__class__.__name__).split('.')[-1]),
                       escape(e.reason),
                       '</c3:error>'
                ]
            response_headers.append(('Content-Length',
                                     str(sum([len(d) for d in out]))
                                     )
                                    )
            start_response('200 OK', response_headers)
            return out

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


application = OAIPMHWsgiApplication(session, configs, dbs)


if __name__ == "__main__":
    sys.exit(main())
