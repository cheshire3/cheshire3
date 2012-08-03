#
# multivalent.py
# Version: 0.04
#
# Description:
#    Cheshire3 <-> Multivalent support
#
# Author:    
#    John Harrison (john.harrison@liv.ac.uk)
#    Dr Robert Sanderson (azaroth@liv.ac.uk)
#
# Copyright: &copy; University of Liverpool 2005
#
# Version History:
# 0.01 - 2005/06/?? - JH - Multivalent protocol client scripts OO-ed and Cheshirized
# 0.02 - 2005/07/?? - RS - Reviewed, code improvements
# 0.03 - 2005/08/05 - JH - Support for UrlDocument objects
#                        - Attempt to reconnect if connection to server lost (in MultivalentPreParser.process_document)
# 0.04 - 2005/11/03 - JH - Starts and uses a local copy of multivalent server if a path to it is provided
#                        - Also provides a method close_mvServer to close the external server cleanly
#
from __future__ import absolute_import

from cheshire3.baseObjects import PreParser
from cheshire3.document import StringDocument
from cheshire3.exceptions import ExternalSystemException, ConfigFileException

import sys, os, re, socket, mimetypes, random
import atexit, commands


# Az:
# socket.setdefaulttimeout needs to be globalised at a server level
# as it affects every socket
#socket.setdefaulttimeout(1 * 60)

# XXX To multivalent.py
class MvdPdfPreParser(PreParser):
    """ Multivalent Pre Parser to turn PDF into XML """

    def process_document(self, session, doc):
        (qqq, fn) = tempfile.mkstemp('.pdf')
        fh = file(fn, 'w')
        fh.write(doc.get_raw(session))
        fh.close()	  
        cmd = "java -Djava.awt.headless=true -cp /users/azaroth/cheshire3/code/mvd/Multivalent20050929.jar tool.doc.ExtractText -output xml %s" % fn
        (i, o, err) = os.popen3(cmd)
        data = o.read()            
        os.remove(fn)
        return StringDocument(data)


class MultivalentPreParser(PreParser):

    inMimeType = ""
    outMimeType = ""
    mvClient = None
    mvHost = None
    mvPort = None
    returnPacking = ""
    source_re = None
    # for when we need to start the server locally
    mvServerPath = None

    def __init__(self, session, server, config):
        PreParser.__init__(self, session, server, config)
        self.source_re = re.compile("<open file '(.+?)', mode '.' at .*?>")
        
        # get settings from config
        # Az:  Check existence of settings and fail consistently rather than
        # die half way through execution
        self.mvServerPath = self.get_path(session, 'mvServerPath')
        if self.mvServerPath:
            # they've specified a local path to the server code
            # we should start a server locally with automatically generated port, in local-only mode
            if not os.path.exists(self.mvServerPath):
                raise ConfigFileException('Path type="mvServerPath" does not exist')

            host = '127.0.0.1'
            # find a random free port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            err = True
            while (err):
                err = False
                port = random.randrange(10000)
                try: s.bind((host,port))
                except: err = True

            s.close()
            del s
            mvStdin, mvStdout = os.popen2('java -D64 -Djava.awt.headless=true -Xms40m -Xmx256m -jar %s %d -guess -out xml -link' % (self.mvServerPath, port), 't')
            
        else:
            # get settings for remote mv server
            host = self.get_setting(session, 'host')
            port  = self.get_setting(session, 'port')
            if not port.isdigit():
                raise ConfigFileException("'port' setting for Multivalent preParser must be an integer.")
            
        pack = self.get_setting(session, 'returnPacking')
        if not (host and port and pack):
            raise ConfigFileException("'host', 'port' and 'returnPacking' settings must be set for Multivalent preParser '%s'" % self.id)
            
        self.mvHost = host
        self.mvPort = int(port)
        self.returnPacking = pack.lower()        
        if (self.returnPacking == 'xml'):
            self.outMimeType = 'text/xml'
        else:
            self.outMimeType = 'text/plain'
        # initialise and connect to multivalent client
        self.mvClient = MultivalentClient()
        try:
            self.mvClient.connect(self.mvHost, self.mvPort)
        except:
            # (Try to connect at run time)
            pass
	atexit.register(self.close_mvServer)            

    def get_mimetype(self, doc):
        if doc.mimeType: return doc.mimeType
        try:
            filepath = self.source_re.search(str(doc.handle)).group(1)
        except AttributeError:
            try:
                filepath = doc.url
            except AttributeError:
                # UHOH not a FileDocument or a UrlDocument - better think about it some more
                pass
            
        try:
            filename = filepath.split('/')[-1]
            return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        except:         
            return 'application/octet-stream'
        

    def process_document(self, session, doc):
        if not (self.mvClient.connectedToServer):
            try:
                self.mvClient.connect(self.mvHost, self.mvPort)
            except:
                raise ExternalSystemException('Could not connect to Multivalent server')

        # returns Document
        history = doc.processHistory
        # Az:  get_raw(session) maybe expensive, --> local var
        data = doc.get_raw(session)
        attrs = {'mimetype': self.get_mimetype(doc),
                 'size': str(len(data)),
                 'packaging': self.returnPacking
                }

        try:
            status, mvStr = self.mvClient.mvProtocol(data, attrs)
        except ExternalSystemException:
            try:
                # try to reconnect
                self.mvClient.disconnect()
                self.mvClient.connect(host, port)
                status, mvStr = self.mvClient.mvProtocol(data, attrs)
            except:
                raise ExternalSystemException('Could not re-establish connection to Multivalent server')
        except socket.timeout:
            # reset connection for next time
            self.mvClient.disconnect()
            #raise some kind of parsing error
            raise ExternalSystemException('Timeout to remote Multivalent server.')
            
        if (status != 'OK'):
            # raise some kind of exception?
            raise ExternalSystemException('Status from Multivalent Server: %s' % status)

        doc = StringDocument(mvStr, history=history)
        return doc

    #- end process_document()

    def close_mvServer(self):
        commands.getoutput('killall -9 java')
        # disconnect
        if (self.mvClient.connectedToServer):
            self.mvClient.disconnect()
        # close external mvServer process via it's own shutdown procedure
        mvStdout = os.popen('java -jar %s %d -stop' % (self.mvServerPath, self.mvPort), 'r')
        
    #- end close_mvServer()


class MultivalentClient:
    sock = None
    connectedToServer = False

    def __init__(self):
        self.sock = None
        self.connectedToServer = False
        
    def connect(self, host, port):           
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.connectedToServer = True

    def disconnect(self):
        self.sock.close()
        self.sock = None
        self.connectedToServer = False

    def mvProtocol(self, data, attrs):
        for attrName, attrVal in attrs.iteritems():
            self.sock.sendall('%s = %s\n' % (attrName, attrVal))
            recvd = self.sock.recv(1024)
            if (recvd.lower()[:2] != 'ok'):
                raise ExternalSystemException('KO - server would not accept attributes')

        # send command that we are ready to send data
        self.sock.sendall('DATA\n')
        recvd = self.sock.recv(1024)

        if (recvd.lower()[:4] != 'send'):
            raise ExternalSystemException('KO - server not prepared to accept data')
        
        # ok, server is ready for data
        try:
            self.sock.sendall(data)
        except socket.timeout:
            raise ExternalSystemException('Timeout to Multivalent server')

        inAttrs = {}
        attr = self.sock.recv(1024)
        
        while (attr.lower()[:4] != 'data'):
            # Az:  XXX Risky to expect non garbage over the wire
	    try:
                attrName = attr.split(" = ", 1)[0].lower()
                attrVal = attr.split(" = ", 1)[1]
                inAttrs[attrName] = attrVal
                self.sock.sendall('OK\n')
                attr = self.sock.recv(1024)
	    except:
	        # XXX log("BUSTED PROTOCOL: %r" % attr)
		break

        if inAttrs['status'][:2] != 'OK':
            return (inAttrs['status'][2:], None)

        # OK we're ready to receive formatted data
        self.sock.sendall('SEND\n')
        expLen = int(inAttrs['size'])
        recvd = self.sock.recv(expLen)
        txtPacks = []
        txtPacks.append(recvd)
        cumLen = len(recvd)
        while cumLen < expLen:
            try:
                recvd = self.sock.recv(expLen)
            except:
                raise ExternalSystemException('Timeout during receive from Multivalent server.')
            txtPacks.append(recvd)
            cumLen += len(recvd)

        txt = ''.join(txtPacks)
        return ('OK', txt)    
