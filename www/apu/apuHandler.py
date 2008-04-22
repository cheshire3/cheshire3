
# import mod_python stuffs
from mod_python import apache, Cookie
from mod_python.util import FieldStorage
# import generally useful modules
import sys, os, traceback, cgitb, urllib, time, smtplib, re

# separate file containing display configs + some HMTL for table rows etc.
from webConfig import *

# set sys paths 
osp = sys.path
sys.path = [os.path.join(cheshirePath, 'cheshire3', 'code')]
sys.path.extend(osp)

# import Cheshire3/PyZ3950 stuff
from server import SimpleServer
from PyZ3950 import CQLParser, SRWDiagnostics
from baseObjects import Session
from document import StringDocument
from searchHandler import SearchHandler
from browseHandler import BrowseHandler
import c3errors
# C3 web search utils
from www_utils import *

cheshirePath = '/home/cheshire'    
logPath = os.path.join(cheshirePath, 'cheshire3', 'www', databaseName, 'logs', 'searchHandler.log')
htmlPath = os.path.join(cheshirePath, 'cheshire3', 'www', databaseName, 'html')

# Discover objects...
def handler(req):
    global db, htmlPath, logPath, cheshirePath, xmlp, recordStore
    form = FieldStorage(req)
    dir = req.uri[1:].rsplit('/')[1]
    remote_host = req.get_remote_host(apache.REMOTE_NOLOOKUP)
    lgr = FileLogger(logPath, remote_host) 
    lgr.log(req.uri)
    lgr.log('directory is %s' % dir)
#    if dir == 'index.html' :
#        page = read_file(os.path.join(cheshirePath, 'cheshire3', 'www', 'apu', 'html', 'index.html'))
#        req.write(page)
#        #req.sendfile(os.path.join(cheshirePath, 'cheshire3', 'www', 'apu', 'html' + dir))
#        return apache.OK
    if dir in ['css', 'js', 'img']:
        req.sendfile(os.path.join(cheshirePath, 'cheshire3', 'www' + req.uri))
        return apache.OK
    else:        
        try:
            #remote_host = req.get_remote_host(apache.REMOTE_NOLOOKUP)     # get the remote host's IP for logging
            os.chdir(htmlPath)                                            # cd to where html fragments are
            #lgr = FileLogger(logPath, remote_host)      
            if form.get('operation', None) =='search':
                handler = SearchHandler(lgr)                                # initialise handler - with logger for this request
            elif form.get('operation', None) =='browse':
                handler = BrowseHandler(lgr)
            else:
                req.content_type = "text/html"
                page = read_file('interface.html')
                req.write(page)
                #return apache.HTTP_NOT_FOUND
                return apache.OK
            try:
                handler.handle(req)                                 # handle request
            finally:
                # clean-up
                try: lgr.flush()                                          # flush all logged strings to disk
                except: pass
                del lgr, handler                                    # delete handler to ensure no state info is retained
        except:
            req.content_type = "text/html"
            cgitb.Hook(file = req).handle()                               # give error info
        else:
            return apache.OK
    
#- end handler()
