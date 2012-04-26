
from mod_python import apache
from mod_python.util import FieldStorage
from ZSI import Fault, FaultFromException, ParsedSoap, SoapWriter, ParseException
import sys, traceback, os, StringIO
import SRW
import SRW.types
import srwHandler as SRWHandlers
from PyZ3950 import SRWDiagnostics
import cStringIO as StringIO

from cheshire3.server import SimpleServer
# from cheshire3.utils import reader
from cheshire3.baseObjects import Session
from cheshire3.internal import cheshire3Root

# Apache Config:
#<Directory /usr/local/apache2/htdocs/srw>
#  SetHandler mod_python
#  PythonDebug On
#  PythonPath "['/home/cheshire/c3/code', '/usr/local/lib/python2.3/lib-dynload']+sys.path"
#  PythonHandler srwApacheHandler
#</Directory>

# NB. SetHandler, not AddHandler.

session = Session()
session.environment = "apache"
serv = SimpleServer(session, os.path.join(cheshire3Root, 'configs', 'serverConfig.xml'))

configs = {}
serv._cacheDatabases(session)
for db in serv.databases.values():
    if db.get_setting(session, 'SRW') or db.get_setting(session, 'srw'):
        db._cacheProtocolMaps(session)
        map = db.protocolMaps.get('http://www.loc.gov/zing/srw/', None)
        map2 = db.protocolMaps.get('http://www.loc.gov/zing/srw/update/', None)
        configs[map.databaseUrl] = {'http://www.loc.gov/zing/srw/' : map,
                                    'http://www.loc.gov/zing/srw/update/' : map2}


class reqHandler:
    def send_xml(self, text, req, code=200):
        req.content_type = 'text/xml'
        req.content_length = len(text)
        req.send_http_header()
        req.write(text)

    def send_fault(self, f, req):
        self.send_xml(f.AsSOAP(), req, 500)

    def processUnknownOperation(self, operation, err, config):
        result = SRW.types.ExplainResponse('explainResponse')
        req = SRW.types.ExplainRequest('explainRequest', opts={'recordPacking' : 'xml', 'version' : "1.1"}, config=config)
        result.processQuery(session, req)
        if isinstance(err, SRWDiagnostics.SRWDiagnostic):
            result.diagnostics = [err]
        else:
            diag = SRWDiagnostics.Diagnostic4()
            diag.uri = diag.uri
            diag.details = operation + ": " + str(err)
            diag.message = diag.message
            result.diagnostics = [diag]
        return result

    def dispatch(self, req):
        path = req.uri[1:]
        if (path[-1] == "/"):
            path = path[:-1]
                    
        if not configs.has_key(path):
            if req.method == "POST":
                self.send_fault(Fault(Fault.Client, "Unknown Database Path %s" % (repr(configs.keys()))), req)
            else:
                # Construct simple table of contents page
                xml = ['<databases>']
                for k in configs:
                    xml.append("<database><path>%s</path></database>" % k)
                xml.append('</databases>')
                txt = ''.join(xml)
                self.send_xml(txt, req)
        else:
            xreq = None
            config = configs[path] 
            if (req.method == "POST"):
                try:
                    data = req.read()
                    dstr = StringIO.StringIO(data)
                    ps = ParsedSoap(dstr, readerclass=reader)
                except Exception, e:
                    try:
                        self.send_fault(FaultFromException(e, 0), req)
                    except Exception, e:
                        self.send_fault(FaultFromException(e, 0), req)
                    return
                callname = ps.body_root.localName
                classname = callname[0].upper() + callname[1:]
                try:
		    try:
			mod = SRW.protocolModules[ps.body_root.namespaceURI]
		    except KeyError:
			log("%r -> %r" % (ps.body_root.namespaceURI, data))
			self.send_fault(Fault(Fault.Client, 'Bad Namespace'), req)
			return
		    config = config[ps.body_root.namespaceURI]
                    objType = getattr(mod, classname)
                    xreq = ps.Parse(objType)
                    xreq.configure(config)
                    xreq.calledAt = path
                    result = self.call(xreq)
                except AttributeError, err:
                    # result = self.processUnknownOperation(classname, err, config)
                    self.send_fault(Fault(Fault.Client, 'Unknown Operation (%s)' % str(err)), req)
                    return
		except Exception, err:
		    self.send_fault(Fault(Fault.Client, 'Broken request %s: (%s)' % (err, data)), req)
		    return
	    elif (req.method == "GET"):
                # parse options out of req
                config = config['http://www.loc.gov/zing/srw/']
                store = FieldStorage(req)
                opts = {}
                for qp in store.list:
                    opts[qp.name] = [qp.value]
                if not opts:
                    opts = {
                        'operation' : ['explain'],
                        'version' : ['1.1'],
                        'recordPacking' : ['xml']
                        }
                if not opts.has_key('operation'):
                    # Be rigourous and error ... somehow
                    err = SRWDiagnostics.Diagnostic7()
                    err.uri = err.uri
                    err.message = "Mandatory 'operation' parameter not supplied"
                    err.details = "operation"
                    result = self.processUnknownOperation('', err, config)
                else:
                    operation = opts['operation'][0]
                    classname = operation[0].upper() + operation[1:] + "Request"
                    try:
                        objType = getattr(SRW.types, classname)
                        xreq = objType(operation + "Request", opts=opts,
                                       config=config, protocol="SRU")
                        xreq.calledAt = path
                        result = self.call(xreq)
			style = ""
                    except AttributeError, err:
                        result = self.processUnknownOperation(operation, err, config)


            reply = StringIO.StringIO()

            if (req.method == "GET"):
                sw = SoapWriter(reply, envelope=0)	    
            else:
                sw = SoapWriter(reply, nsdict=SRW.protocolNamespaces)
            try:
                sw.serialize(result, inline=1)
                sw.close()
                text = reply.getvalue()
            except Exception, err:
                self.send_fault(Fault(Fault.Client, 'Busted (%s)' % str(err)), req)
                return

            if (req.method == "GET"):
                if xreq and hasattr(xreq, 'stylesheet') and xreq.stylesheet:
                    headerText = u'<?xml version="1.0"?>\n<?xml-stylesheet type="text/xsl" href="%s"?>\n' % (xreq.stylesheet) 
                elif xreq and hasattr(xreq, 'defaultStylesheet') and xreq.defaultStylesheet:
                    headerText = u'<?xml version="1.0"?>\n<?xml-stylesheet type="text/xsl" href="%s"?>\n' % (xreq.defaultStylesheet) 
                else:
                    headerText = u""
                    
                text = text.replace('Response>',  'Response xmlns:srw="%s" xmlns:diag="%s" xmlns:xcql="%s" xmlns:xsi="%s" xmlns:xsd="%s">' % (config.protocolNamespaces['srw'], config.protocolNamespaces['diag'], config.protocolNamespaces['xcql'], 'http://www.w3.org/2001/XMLSchema', 'http://www.w3.org/2001/XMLSchema-instance'), 1)
		if headerText:
		    text = headerText + text
		
            self.send_xml(text, req)
        
        
    def call(self, req):
        result = req.responseType(req.responseName)
        # ??! Necessary garbage
        result.extraResponseData = result.extraResponseData
        try:
            result.processQuery(session, req)
        except SRWDiagnostics.SRWDiagnostic, diag:
            diag.uri = diag.uri
            diag.details = diag.details
            diag.message = diag.message
            result.diagnostics = [diag]
        except Exception, err:
            diag = SRWDiagnostics.Diagnostic1()
            diag.uri = diag.uri
            diag.details = '\n'.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            diag.message = "Doh! Something went Really Badly"
            result.diagnostics = [diag]

        return result


srwh = reqHandler()        

def handler(req):
    # do stuff
    srwh.dispatch(req)
    return apache.OK

