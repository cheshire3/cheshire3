#
# Program:   workflowApacheHandler.py
# Version:   0.02a
# Description:
#            Apache Handler to accept Cheshire3 workflow XML and some inputs to run through it.
#
# Language:  Python
# Author:    John Harrison <john.harrison@liv.ac.uk>
#
# Date:      09/02/2006
#
# Copyright: &copy; University of Liverpool 2006
#
# Version History:
# 0.01 - 09/02/2006 - JH - Workflow and input objects configured and built
#                        - Workflow run on each specified input object
#                        - Workflow execution protocol developed in collaboration with:
#                           Fabio Corubolo, John Palmer, Robert Sanderson
# 0.02 - ??/02/2006 - JH - Lots more exception handling
#
#

# Apache Config (assumes standard installation):
#<Directory /home/cheshire/cheshire3/install/htdocs/workflow>
#  SetHandler mod_python
#  PythonDebug On
#  PythonPath "['/home/cheshire/cheshire3/cheshire3/code'+sys.path"]
#  PythonHandler workflowApacheHandler
#</Directory>

# NB. SetHandler, not AddHandler.

from mod_python import apache
from mod_python.util import FieldStorage

from xml.dom.minidom import parseString as domParseString, Document as DomDocument
import time, os
import cStringIO as StringIO

from cheshire3.server import SimpleServer
from cheshire3.utils import elementType
from cheshire3.baseObjects import Session
from cheshire3 import document
from cheshire3.workflow import SimpleWorkflow, CachingWorkflow
from cheshire3 import dynamic
from cheshire3.exceptions import *
from cheshire3.internal import cheshire3Root

session = Session()
session.environment = "apache"
serv = SimpleServer(session, os.path.join(cheshire3Root, 'configs', 'serverConfig.xml'))
mdp = serv.get_object(session, 'defaultParser')

configs = {}
serv._cacheDatabases(session)
for db in serv.databases.values():
    #if db.get_setting(session, 'C3WEP'):
    if db.get_setting(session, 'remoteWorkflow'):
        db._cacheProtocolMaps(session)
        #map = db.protocolMaps.get('c3WorflowExecutionProtocol', None)
        #configs[map.databaseUrl] = {'c3WorflowExecutionProtocol' : map}
        map = db.protocolMaps.get('http://www.cheshire3.org/protocols/workflow/1.0/', None)
        configs[map.databaseUrl] = {'http://www.cheshire3.org/protocols/workflow/1.0/' : map}
        

class reqHandler:
    log = None

    def __init__(self):
        self.log = open('/home/cheshire/tempWorkflow.log', 'a')
        pass

    def send_text(self, text, req, code=200):
        req.content_type = 'text/plain'
        #req.content_length = len(text)
        req.send_http_header()
        req.write(text)
        
    def handle_workflowRequest(self, config, req):
        postdata = FieldStorage(req)
            
        xmlstr = postdata.get('requestxml', None)
        
        if not (xmlstr):
            # throw some sensible error
            time.sleep(1)
            req.write('ERROR : No request XML submitted\n')
            return
#        else:
#            self.log.write(xmlstr)
            
        doc = document.StringDocument(xmlstr)
        rec = mdp.process_document(session, doc)
        
        self.log.write('rec.get_xml():\n%s\n' % rec.get_xml(session))
        
        dom = rec.get_dom(session)
        #now do some clever dynamic object stuff
        wfNode = dom.childNodes[0]
        wfNode = dom.getElementsByTagName('workflow')[0]
        wfConf = self._generateWorkflowConfigNode(wfNode)
        wfobj = SimpleWorkflow(session, wfConf, serv)
        inputs = dom.getElementsByTagName('inputs')[0]
                        
        time.sleep(1);                      
        if not (wfobj): req.write('ERROR : Junk XML - must contain workflow element\n'); return
        elif not (inputs): req.write('ERROR : Junk XML - must contain inputs element\n'); return
        
        iCount = 1
        wfmsgs = []
        self.log.write('inputs:%s\n' % inputs.toxml())
        for input in inputs.childNodes:
            self.log.write('input:%s\n' % input.toxml())
            if (input.nodeType == elementType):
                objectType = input.getAttribute('type')
            else:
                continue
            
            if objectType == 'document.StringDocument':
                try: 
                    f = postdata.get('file', None)
                    data = f.value
                except: 
                    data = None
            else: 
                data = input.firstChild.toxml()
                
            if not data: req.write('ERROR : No input data provided\n'); return
                
            time.sleep(5);
            #req.write('PROGRESS : %s\n' % (objectType))
            modName = objectType[:objectType.rfind('.')]
            clName = objectType[objectType.rfind('.')+1:]
            mod = dynamic.globalImport(modName, [])
            cl = getattr(mod, clName)
            inobj = cl(data)
            try:
                msg = wfobj.process(session, inobj)
            except ObjectAlreadyExistsException, e:
                time.sleep(1);
                req.write('ERROR : One or more records in input %d already exist in the database : %s\n' % (iCount, e))
                continue
            except Exception, e:
                time.sleep(1);
                msg = e
                req.write('ERROR : Something went wrong while processing input %d : %s\n' % (iCount, e))
                continue
                

            #wfmsgs.append(repr(msg))
            time.sleep(1);
            req.write('PROGRESS : processed input %d : %s\n' % (iCount, msg))
            iCount += 1
        
        #self.log.close()
        return msg
    
    
    def _generateWorkflowConfigNode(self, wfNode):
        # need a document to creat elements
        doc = DomDocument()
        subConfigNode = doc.createElement('subConfig')
        # top node MUST have an id attribute
        if wfNode.hasAttribute('id'):
            subConfigNode.setAttribute('id', wfNode.getAttribute('id'))
        else:
            subConfigNode.setAttribute('id', 'tempWorkflow')
            
        objectTypeNode = doc.createElement('objectType')
        objectTypeNode.appendChild(doc.createTextNode('workflow.SimpleWorkflow'))
        subConfigNode.appendChild(objectTypeNode)
        subConfigNode.appendChild(wfNode)
        #doc.appendChild(subConfigNode)
        return subConfigNode
        
    
    def handle(self, req):
        path = req.uri[1:]

        if (path[-1] == "/"):
            path = path[:-1]
                    
        if not configs.has_key(path):
            self.send_text('ERROR : Unknown Database Path, available Databases: %s' % (repr(configs.keys())), req)
            return
        else:
            config = configs[path]
            
        self.send_text('ACCEPTED : %s\n' % (path), req)
        config = configs[path]
        db = config['c3WorflowExecutionProtocol'].parent
        session.database = db.id
        returnstuff = self.handle_workflowRequest(config, req)
        # if a document is return, we probably want to return the contents rather than the object
        try:
            returnstuff = returnstuff.get_raw(session)
        except:
            pass
        
        time.sleep(1);
        req.write('COMPLETE : %s\n' % (returnstuff))
        
        return
        
        
#- end reqHandler -------------------------------------------------------------
    

c3WepHandler = reqHandler()
   
def handler(req):
    # do stuff
    c3WepHandler.handle(req)
    return apache.OK
