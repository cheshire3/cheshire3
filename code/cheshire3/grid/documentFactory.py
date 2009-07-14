
from cheshire3.documentFactory import MultipleDocumentStream, FileDocumentStream
from cheshire3.exceptions import ConfigFileException

import irods, irods_error
import os


class IrodsStream(object):

    def __init__(self, session, stream):
        myEnv, status = irods.getRodsEnv()
        conn, errMsg = irods.rcConnect(myEnv.getRodsHost(), myEnv.getRodsPort(), 
                                       myEnv.getRodsUserName(), myEnv.getRodsZone())
        status = irods.clientLogin(conn)
        if status:
            raise ConfigFileException("Cannot connect to iRODS: (%s) %s" % (status, errMsg))
        
        home = myEnv.getRodsHome()
        c = irods.irodsCollection(conn, home)
        self.cxn = conn
        self.coll = c

        # check if abs path to home dir
        if stream.startswith(home):
            stream = stream[len(home):]
            if stream[0] == "/":
                stream = stream[1:]
        colls = stream.split('/')
        for cln in colls:
            c.openCollection(cln)
        

class IrodsFileDocumentStream(IrodsStream, FileDocumentStream):

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        
        IrodsStream.__init__(self, session, stream)
        FileDocumentStream.__init__(self, session, stream, format, tagName, codec, factory)

    def open_stream(self, path):
        # filename in current directory
        fn = os.path.basename(path)
        if path:
            return self.coll.open(fn)
    


class IrodsDirectoryDocumentStream(IrodsStream, MultipleDocumentStream):


    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):

        IrodsStream.__init__(self, session, stream)
        MultipleDocumentStream.__init__(self, session, stream, format, tagName, codec, factory)

    def open_stream(self, path):
        # filename in current directory
        if path:
            return self.coll.open(path)

    def find_documents(self, session, cache=0):
        # given a location in irods, go there and descend looking for files
        c = self.coll

        files = c.getObjects()
        files.sort()
        for f in self._processFiles(session, files):
            yield f

        dirs = c.getSubCollections()
        while dirs:
            d = dirs.pop(0)
            upColls = 0
            for dx in d.split('/'):
                c.openCollection(dx)
                upColls += 1

            files = c.getObjects()
            files.sort()
            for f in self._processFiles(session, files):
                yield f

            ndirs = c.getSubCollections()
            
            dirs.extend(["%s/%s" % (d, x) for x in ndirs])

            for x in range(upColls):
                c.upCollection()

            
