"""OAI-PMH server implementation to be run under mod_python.

 Apache Config:
<Directory /usr/local/apache2/htdocs/OAI/2.0>
  SetHandler mod_python
  PythonDebug On
  PythonPath "['/home/cheshire/cheshire3/code', ...]+sys.path"
  PythonHandler cheshire3.web.oaipmhApacheHandler
</Directory>
NB. SetHandler, not AddHandler.

"""

import sys
import cgitb

from oaipmhHandler import *

try:
    from mod_python import apache
    from mod_python.util import FieldStorage
except ImportError:
    pass
else:
    session.environment = "apache"
    

class reqHandler(object):

    def send_xml(self, text, req, code=200):
        req.content_type = 'text/xml'
        req.content_length = len(text)
        req.send_http_header()
        req.write(text)
        
    def dispatch(self, req):
        global session, configs, dbs, oaiDcReader, c3OaiServers
        path = req.uri[1:]
        if (path[-1] == "/"):
            path = path[:-1]
                    
        if configs.has_key(path):
            args = {}
            # Parse options out of req
            store = FieldStorage(req)            
            for qp in store.list:
                args[qp.name] = qp.value
            try:
                oaixml = MinimalOaiServer(c3OaiServers[path], c3OaiServers[path].metadataRegistry)
            except KeyError:
                oai = Cheshire3OaiServer(session, configs, dbs, path)
                c3OaiServers[path] = oai
                oaixml = MinimalOaiServer(oai, oai.metadataRegistry)
            try:
                xmlresp = oaixml.handleRequest(args)
            except DatestampError:
                try:
                    raise BadArgumentError('Invalid date format supplied.')
                except:
                    xmlresp = oaixml.handleException(args, sys.exc_info())
            except C3Exception, e:
                xmlresp = '<c3:error xmlns:c3="http://www.cheshire3.org/schemas/error" code="%s">%s</c3:error>' % (str(e.__class__).split('.')[-1], e.reason)
            self.send_xml(xmlresp, req)
        else:
            fullPath = os.path.join(apache.server_root(), 'htdocs', path)
            if os.path.exists(fullPath) and not os.path.isdir(fullPath):
                req.sendfile(os.path.join(apache.server_root(), 'htdocs', path))
            else:
                # TODO: send proper OAI error?
                dbps = ['<c3:database>{0}</c3:database>'.format(dbp) for dbp in configs]
                self.send_xml('''
<c3:error xmlns:c3="http://www.cheshire3.org/schemas/error">
    <c3:details>{0}</c3:details>
    <c3:message>Incomplete or incorrect baseURL, requires a database path from:
        <c3:databases>{1}</c3:databases>
    </c3:message>
</c3:error>'''.format(path, '\n\t'.join(dbps)), req)
                    
    #- end reqHandler -------------------------------------------------------------


def handler(req):
    global h
    # Do stuff
    try:
        h.dispatch(req)
    except:
        # Give error info
        req.content_type = "text/html"
        cgitb.Hook(file = req).handle()
    else:
        return apache.OK
    # Add AuthHandler here when necesary ------------------------------------------


#from dateutil.tz import *
# OAI-PMH friendly ISO8601 UTCdatetime obtained with the following
# datetime.datetime.now(datetime.tzutc()).strftime('%Y-%m-%dT%H:%M:%S%Z').replace('UTC', 'Z')

h = reqHandler()
