import os

from cheshire3.document import StringDocument
from cheshire3.documentFactory import MultipleDocumentStream
from cheshire3.documentFactory import FileDocumentStream
from cheshire3.exceptions import ConfigFileException
from cheshire3.exceptions import MissingDependencyException

from cheshire3.grid.irods_utils import icatValToPy, parse_irodsUrl

try:
    import irods
except ImportError:
    irods = None

class IrodsStream(object):
    u"""Base class DocumentStream to load from iRODS."""

    def __init__(self, session, stream):
        # Check for dependency
        if irods is None:
            raise MissingDependencyException(
                '{0.__module__}.{0.__class__.__name__}'.format(self),
                'irods (PyRods)'
            )
        # Check for URL
        if stream.startswith(('irods://', 'rods://')):
            myEnv = parse_irodsUrl(stream)
            stream = myEnv.relpath
        else:
            # Get parameters from env
            status, myEnv = irods.getRodsEnv()
        try:
            host = myEnv.getRodsHost()
            port = myEnv.getRodsPort()
            username = myEnv.getRodsUserName()
            zone = myEnv.getRodsZone()
            home = myEnv.getRodsHome()
        except AttributeError:
            host = myEnv.rodsHost
            port = myEnv.rodsPort
            username = myEnv.rodsUserName
            zone = myEnv.rodsZone
            home = myEnv.rodsHome
        conn, errMsg = irods.rcConnect(host, port, username, zone)
        status = irods.clientLogin(conn)
        if status:
            raise ConfigFileException("Cannot connect to iRODS: ({0}) {1}"
                                      "".format(status, errMsg)
                                      )

        c = irods.irodsCollection(conn)
        self.cxn = conn
        self.coll = c
        instream = stream
        # Check if abs path to home dir
        if stream.startswith(home):
            stream = stream[len(home):]
            if stream[0] == "/":
                stream = stream[1:]
        colls = stream.split('/')
        for i, cln in enumerate(colls):
            exit_status = c.openCollection(cln)
            if exit_status < 0:
                if (
                    (i < len(colls) - 1) or
                    (cln not in [obj[0] for obj in c.getObjects()])
                ):
                    raise IOError("When opening {0}: {1} does not exists in "
                                  "collection {2}".format(instream,
                                                          cln,
                                                          c.getCollName()
                                                          )
                                  )


class IrodsFileDocumentStream(IrodsStream, FileDocumentStream):
    u"""DocumentStream to load a Document from a file in iRODS."""

    def __init__(self, session, stream, format,
                 tagName=None, codec=None, factory=None):
        IrodsStream.__init__(self, session, stream)
        FileDocumentStream.__init__(self, session, stream, format,
                                    tagName, codec, factory)

    def open_stream(self, path):
        # Filename in current directory
        fn = os.path.basename(path)
        if path:
            return self.coll.open(fn)

    def find_documents(self, session, cache=0):
        # Read in single file
        doc = StringDocument(self.stream.read(),
                             filename=self.stream.getName()
                             )
        # Attach any iRODS metadata
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
    u"""DocumentStream to load Documents from an iRODS directory/collection."""

    def __init__(self, session, stream, format,
                 tagName=None, codec=None, factory=None):

        IrodsStream.__init__(self, session, stream)
        MultipleDocumentStream.__init__(self, session, stream, format,
                                        tagName, codec, factory)

    def open_stream(self, path):
        # Filename in current directory
        if path:
            strm = self.coll.open(path)
            return strm

    def find_documents(self, session, cache=0):
        # Given a location in iRODS, go there and descend looking for files
        c = self.coll
        files = c.getObjects()
        files = [x[0] for x in files]
        files.sort()
        for f in self._processFiles(session, files):
            md = {}
            irodsFilePath = '{0}/{1}'.format(c.getCollName(), f.filename)
            for x in irods.getFileUserMetadata(self.cxn, irodsFilePath):
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
                irodsFilePath = '{0}/{1}'.format(c.getCollName(), f.filename)
                for x in irods.getFileUserMetadata(self.cxn, irodsFilePath):
                    md[x[0]] = icatValToPy(x[1], x[2])
                if len(md):
                    f.metadata['iRODS'] = md
                yield f

            ndirs = c.getSubCollections()
            dirs.extend(["%s/%s" % (d, x) for x in ndirs])
            for x in range(upColls):
                c.upCollection()


class IrodsDeterminingDocumentStream(IrodsFileDocumentStream,
                                     IrodsDirectoryDocumentStream):
    """DocumentStream to load a Document from a file or directory in iRODS."""

    def __init__(self, session, stream, format,
                 tagName=None, codec=None, factory=None):
        IrodsStream.__init__(self, session, stream)
        # Check the stream location to init correct subclass
        fn = os.path.basename(stream)
        if fn in self.coll.getObjects():
            # Fake dynamic inheritance
            self.baseClass = IrodsFileDocumentStream
            FileDocumentStream.__init__(self, session, stream, format,
                                        tagName, codec, factory)
        else:
            # Fake dynamic inheritance
            self.baseClass = IrodsDirectoryDocumentStream
            MultipleDocumentStream.__init__(self, session, stream, format,
                                            tagName, codec, factory)

    def open_stream(self, path):
        return self.baseClass.open_stream(self, path)

    def find_documents(self, session, cache=0):
        return self.baseClass.find_documents(self, session, cache=0)


class IrodsConsumingFileDocumentStream(IrodsFileDocumentStream):
    u"""DocumentStream to load a Document by consuming a file in iRODS.

    DocumentStream to load a Document from a file in iRODS, consuming (i.e.
    deleting the source file from iRODS) as it does so.

    USE WITH EXTREME CAUTION!
    """

    def find_documents(self, session, cache=0):
        # Read in single file
        doc = StringDocument(self.stream.read(),
                             filename=self.stream.getName())
        # Attach any iRODS metadata
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
    u"""DocumentStream to consume Documents from an iRODS directory/collection.

    DocumentStream to load Documents from a directory/collection in iRODS,
    consuming (that is to say deleting) the source files as it does so.

    USE WITH EXTREME CAUTION!
    """

    def find_documents(self, session, cache=0):
        # Given a location in irods, go there and descend looking for files
        c = self.coll
        files = c.getObjects()
        files.sort()
        fList = [x[0] for x in files]
        for i, f in enumerate(self._processFiles(session, fList)):
            md = {}
            irodsFilePath = '{0}/{1}'.format(c.getCollName(), f.filename)
            for x in irods.getFileUserMetadata(self.cxn, irodsFilePath):
                md[x[0]] = icatValToPy(x[1], x[2])
            if len(md):
                f.metadata['iRODS'] = md
            # Delete the file on its resource
            c.delete(files[i][0], files[i][1])
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
            fList = [x[0] for x in files]
            for i, f in enumerate(self._processFiles(session, fList)):
                md = {}
                irodsFilePath = '{0}/{1}'.format(c.getCollName(), f.filename)
                for x in irods.getFileUserMetadata(self.cxn, irodsFilePath):
                    md[x[0]] = icatValToPy(x[1], x[2])
                if len(md):
                    f.metadata['iRODS'] = md
                # Delete the file on its resource
                c.delete(files[i][0], files[i][1])
                yield f
            ndirs = c.getSubCollections()
            dirs.extend(["%s/%s" % (d, x) for x in ndirs])
            for x in range(upColls):
                c.upCollection()


class SrbDocumentStream(MultipleDocumentStream):
    # SRB://user.domain:pass@host:port/path/to/object?DEFAULTRESOURCE=res
    pass


streamHash = {"irods": IrodsDeterminingDocumentStream,
              "ifile": IrodsFileDocumentStream,
              "idir": IrodsDirectoryDocumentStream,
              "ifile-": IrodsConsumingFileDocumentStream,
              "idir-": IrodsConsumingDirectoryDocumentStream
              }
