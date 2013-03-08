"""OAI-PMH WSGI Application."""

from urllib import quote
from cgi import FieldStorage

from oaipmhHandler import *


class OAIPMHWsgiApplication(object):
    
    def __call__(self, environ, start_response):
        global configs, oaiDcReader, c3OaiServers
        response_headers = [('Content-Type',
                             'application/xml')]
        path = environ.get('PATH_INFO', '').strip('/')
        out = []
        if path not in configs:
            # Unknown endpoint
            # No specification
            
            out.extend([
                '<c3:error xmlns:c3="http://www.cheshire3.org/schemas/error">'
                '<c3:details>{0}</c3:details>'.format(path),
                '<databases numberOfDatabases="{0}">'.format(len(configs)),
                ('<c3:message>Incomplete or incorrect baseURL, requires a '
                 'database path from:'),
                '<c3:databases>'
            ])
            out.extend(['<c3:database>{0}</c3:database>'.format(dbp)
                        for dbp
                        in configs
                        ])
            out.extend([
                '</c3:databases>',
                '</c3:message>',
                '</c3:error>'
            ])
            # TODO: send proper OAI error?
            start_response('404 NOT FOUND', response_headers)
            return out
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
            args = {}
            # parse options out of req
            store = FieldStorage(fp=environ['wsgi.input'], environ=environ)            
            for qp in store.list:
                args[qp.name] = qp.value
            try:
                oaixml = MinimalOaiServer(c3OaiServers[path],
                                          c3OaiServers[path].metadataRegistry)
            except KeyError:
                oai = Cheshire3OaiServer(path)
                c3OaiServers[path] = oai
                oaixml = MinimalOaiServer(oai, oai.metadataRegistry)
            try:
                xmlresp = [oaixml.handleRequest(args)]
            except DatestampError:
                try:
                    raise BadArgumentError('Invalid date format supplied.')
                except:
                    xmlresp = [oaixml.handleException(args, sys.exc_info())]
            except C3Exception, e:
                xmlresp = [
                    '<c3:error xmlns:c3="http://www.cheshire3.org/schemas/error"',
                    'code="{0}">'.format(str(e.__class__.__name__).split('.')[-1]),
                    e.reason,
                    '</c3:error>'
                ]
            response_headers.append(('Content-Length',
                                     str(sum([len(d) for d in out])
                                     ))
            start_response('200 OK', response_headers)
            return out
            self.send_xml(xmlresp, req)
