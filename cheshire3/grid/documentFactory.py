
from cheshire3.documentFactory import MultipleDocumentStream, FileDocumentStream
from cheshire3.document import StringDocument
from cheshire3.exceptions import ConfigFileException
from cheshire3.grid.irods_utils import icatValToPy

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

        instream = stream
        # check if abs path to home dir
        if stream.startswith(home):
            stream = stream[len(home):]
            if stream[0] == "/":
                stream = stream[1:]
        colls = stream.split('/')
        for i, cln in enumerate(colls):
            exit_status = c.openCollection(cln)
            if exit_status < 0:
                if (i < len(colls) - 1) or \
                    (cln not in [obj[0] for obj in c.getObjects()]):
                    raise IOError("When opening {0}: {1} does not exists in collection {2}".format(instream, cln, c.getCollName()))
        

class IrodsFileDocumentStream(IrodsStream, FileDocumentStream):
    u"""DocumentStream to load a Document from a file in iRODS."""

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        
        IrodsStream.__init__(self, session, stream)
        FileDocumentStream.__init__(self, session, stream, format, tagName, codec, factory)

    def open_stream(self, path):
        # filename in current directory
        fn = os.path.basename(path)
        if path:
            return self.coll.open(fn)

    def find_documents(self, session, cache=0):
        # read in single file
        doc = StringDocument(self.stream.read(), filename=self.stream.getName())
        # attach any iRODS metadata
        umd = self.stream.getUserMetadata()
        self.stream.close()
        self.cxn.disconnect()
        md = {}
        for x in umd:
            md[x[0]] = icatValToPy(x[1], x[2])
        if len(md):
            doc.metadata['iRODS'] = md
        if cache == 0:
            yield doc
        elif cache == 2:
            self.documents = [doc]


class IrodsDirectoryDocumentStream(IrodsStream, MultipleDocumentStream):
    u"""DocumentStream to load Documents from a directory/collection in iRODS."""

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):

        IrodsStream.__init__(self, session, stream)
        MultipleDocumentStream.__init__(self, session, stream, format, tagName, codec, factory)

    def open_stream(self, path):
        # filename in current directory
        if path:            
            strm = self.coll.open(path)
            return strm

    def find_documents(self, session, cache=0):
        # given a location in irods, go there and descend looking for files
        c = self.coll
        files = c.getObjects()
        files = [x[0] for x in files]
        files.sort()
        for f in self._processFiles(session, files):
            md = {}
            for x in irods.getFileUserMetadata(self.cxn, '{0}/{1}'.format(c.getCollName(), f.filename)):
                md[x[0]] = icatValToPy(x[1], x[2])
            if len(md):
                f.metadata['iRODS'] = md
            yield f

        dirs = c.getSubCollections()
        while dirs:
            d = dirs.pop(0)
            upColls = 0
            for dx in d.split('/'):
                c.openCollection(dx)
                upColls += 1

            files = c.getObjects()
            files = [x[0] for x in files]
            files.sort()
            for f in self._processFiles(session, files):
                md = {}
                for x in irods.getFileUserMetadata(self.cxn, '{0}/{1}'.format(c.getCollName(), f.filename)):
                    md[x[0]] = icatValToPy(x[1], x[2])
                if len(md):
                    f.metadata['iRODS'] = md
                yield f

            ndirs = c.getSubCollections()
            dirs.extend(["%s/%s" % (d, x) for x in ndirs])
            for x in range(upColls):
                c.upCollection()


class IrodsConsumingFileDocumentStream(IrodsFileDocumentStream):
    u"""DocumentStream to load a Document from a file in iRODS and delete the file afterwards. USE WITH EXTREME CAUTION!"""

    def find_documents(self, session, cache=0):
	# read in single file
        doc = StringDocument(self.stream.read(), filename=self.stream.getName())
        # attach any iRODS metadata
        umd = self.stream.getUserMetadata()
        md = {}
        for x in umd:
            md[x[0]] = icatValToPy(x[1], x[2])
        if md:
            doc.metadata['iRODS'] = md
        # delete the file
        self.stream.close()
        self.stream.delete()
        self.cxn.disconnect()
        if cache == 0:
            yield doc
        elif cache == 2:
            self.documents = [doc]


class IrodsConsumingDirectoryDocumentStream(IrodsDirectoryDocumentStream):
    u"""DocumentStream to load Documents from a directory/collection in iRODS consuming (deleting) the files as it does so. USE WITH EXTREME CAUTION!"""

    def find_documents(self, session, cache=0):
        # given a location in irods, go there and descend looking for files
        c = self.coll
        files = c.getObjects()
        files.sort()
        for i, f in enumerate(self._processFiles(session, [x[0] for x in files])):
            md = {}
            for x in irods.getFileUserMetadata(self.cxn, '{0}/{1}'.format(c.getCollName(), f.filename)):
                md[x[0]] = icatValToPy(x[1], x[2])
            if len(md):
                f.metadata['iRODS'] = md
            c.delete(files[i][0], files[i][1]) # delete the file on its resource
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
            for i, f in enumerate(self._processFiles(session, [x[0] for x in files])):
                md = {}
                for x in irods.getFileUserMetadata(self.cxn, '{0}/{1}'.format(c.getCollName(), f.filename)):
                    md[x[0]] = icatValToPy(x[1], x[2])
                if len(md):
                    f.metadata['iRODS'] = md
                c.delete(files[i][0], files[i][1]) # delete the file on its resource
                yield f

            ndirs = c.getSubCollections()
            
            dirs.extend(["%s/%s" % (d, x) for x in ndirs])

            for x in range(upColls):
                c.upCollection()


class SrbDocumentStream(MultipleDocumentStream):
    # SRB://user.domain:pass@host:port/path/to/object?DEFAULTRESOURCE=res
    pass


streamHash = {"ifile": IrodsFileDocumentStream
             ,"idir" : IrodsDirectoryDocumentStream
             ,"ifile-": IrodsConsumingFileDocumentStream
             ,"idir-": IrodsConsumingDirectoryDocumentStream
             }

