import socket, time
socket.setdefaulttimeout(30)

from baseObjects import DocumentFactory
from document import StringDocument
from record import SaxRecord
from bootstrap import BSParser
from utils import elementType, getFirstData, flattenTexts, reader, verifyXPaths
import re, os, c3errors, tarfile, cStringIO, sys, gzip
import mimetypes, httplib, urllib, urlparse, urllib2
import commands, codecs, types
from ZSI.client import Binding
from PyZ3950 import zoom
import SRW
from c3errors import *
from ftplib import FTP
from utils import reader
import zipfile

from Ft.Xml.Domlette import Print
from lxml import etree
from xpathProcessor import SimpleXPathProcessor


mimetypes.add_type('application/marc', '.marc')

# NB:
# cache = 0:  yield, no caching
# cache = 1:  step through, cache positions in stream
# cache = 2:  step through, cache full documents
# other cache values undefined

class BaseDocumentStream:
    streamLocation = ""
    format = ""
    tagName = ""
    codec = ""
    factory = None
    filterRe = None
    stream = None
    locations = []
    documents = []
    length = 0

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        self.factory = factory
        self.format = format
        if type(tagName) == unicode:
            self.tagName = tagName.encode('utf-8')
        else:
            self.tagName = tagName
        self.codec = codec
        self.stream = self.open_stream(stream)

    def open_stream(self, stream):
        if hasattr(stream, 'read') and hasattr(stream, 'seek'):
            # is a stream
            self.streamLocation = "UNKNOWN"
            return stream
        else:
            if os.path.exists(stream):
                # is a file
                self.streamLocation = stream
                if not os.path.isdir(stream):
                    if self.codec:
                        return codecs.open(self.streamLocation, 'r', self.codec)
                    else:
                        return file(self.streamLocation)
                else:
                    return stream
            else:
                # is a string
                self.streamLocation = "STRING"
                return cStringIO.StringIO(stream)
            
    def fetch_document(self, idx):
        if self.length and idx >= self.length:
            raise StopIteration
        if self.documents:
                return self.documents[idx]
        elif self.locations:
            self.stream.seek(self.locations[idx][0])
            data = self.stream.read(self.locations[idx][1])
            return data
        else:
            raise StopIteration

    def find_documents(self, session, cache=0):
        raise(NotImplementedError)

class TermHashDocumentStream(BaseDocumentStream):

    def open_stream(self, stream):
        # is a hash...
        self.streamLocation = "TERM-STRING"
        return stream.keys()        

    def find_documents(self, session, cache=0):
        # step through terms
        if cache == 0:
            for k in self.stream:
                yield StringDocument(k)
            raise StopIteration
        elif cache == 2:
            documents = []
            for k in self.stream:
                documents.append(StringDocument(k))
            self.documents = documents
    

class XmlDocumentStream(BaseDocumentStream):
    start = None
    endtag = ""

    def __init__(self, session, stream, format, tagName="", codec="", factory=None):
        BaseDocumentStream.__init__(self, session, stream, format, tagName, codec, factory)
        if (not tagName):
            self.start = re.compile("<([-a-zA-Z0-9_.]+:)?([-a-zA-Z0-9_.]+)[\s>]")
            self.endtag = ""
        else:
            self.start = re.compile("<%s[\s>]" % tagName)
            self.endtag = "</" + tagName + ">"
            
    def find_documents(self, session, cache=0):

        docs = []
        locs = []
        endtag = self.endtag
        let = len(endtag)
        myTell = 0
        xpi = ""
        line = ""
        offOffset = 0

        self.stream.seek(0, os.SEEK_END)
        filelen = self.stream.tell()
        self.stream.seek(0, os.SEEK_SET)

        while True:
            ol = len(line)
            # if 10000 bytes of garbage between docs, then will exit
            if ol < 10000:
                line += self.stream.read(1024)
            pi = line.find("<?xml ")                
            if (pi > -1):
                # Store info
                endpi = line.find("?>")
                xpi = line[pi:endpi+2] + "\n"
                xpi= ""
            m = self.start.search(line)
            if m:
                if not self.endtag:
                    endtag = "</%s>" % m.group()[1:-1]
                    let = len(endtag)                
                s = m.start()
                line = line[s:]                
                myTell += s
                start = myTell
                end = -1
                strStart = 0
                while end == -1:
                    if strStart:
                        # allow for end tag to be broken across reads
                        end = line.find(endtag, strStart-let)
                    else:
                        end = line.find(endtag)
                    if end > 0:
                        tlen = end+len(endtag)
                        txt = line[:tlen]
                        line = line[tlen:]
                        myTell += tlen
                        try:
                            byteCount = len(txt.encode('utf-8'))
                        except:
                            byteCount = tlen
                            
                        if cache == 0:
                            yield StringDocument(xpi + txt, mimeType="text/xml", tagName=self.tagName, byteCount=byteCount, byteOffset=start+offOffset, filename=self.streamLocation)
                        elif cache == 1:
                            locs.append((start, tlen))
                        elif cache == 2:
                            docs.append(StringDocument(xpi + txt, mimeType="text/xml", tagName=self.tagName))
                        offOffset += (byteCount - tlen)
                    else:
                        strStart = len(line)
                        # check we have at least 1024 to read
                        if self.stream.tell() == filelen:
                            # we've got nuffink!
                            if cache == 0:
                                self.stream.close()
                                raise StopIteration
                            else:
                                break
                        if self.stream.tell() + 1024 < filelen:
                            line += self.stream.read(1024)
                        else:
                            line += self.stream.read()
                        
                            
            if len(line) == ol and not m:
                if cache == 0:
                    self.stream.close()
                    raise StopIteration
                else:
                    break
        self.stream.close()
        self.locations = locs
        self.documents = docs
        self.length = max(len(locs), len(docs))


class MarcDocumentStream(BaseDocumentStream):
            
    def find_documents(self, session, cache=0):
        docs = []
        locs = []
        data = self.stream.read(1536)
        myTell = 0
        while data:
            rt = data.find("\x1D")
            while (rt > -1):
                txt = data[:rt+1]
                tlen = len(txt)
                if cache == 0:
                    yield StringDocument(txt, mimeType="application/marc")
                elif cache == 1:                    
                    locs.append((myTell, tlen))
                elif cache == 2:
                    docs.append(StringDocument(txt, mimeType="application/marc"))
                data = data[rt+1:]
                myTell += tlen
                rt = data.find("\x1D")
            dlen = len(data)
            data += self.stream.read(1536)
            if (len(data) == dlen):
                # Junk at end of file
                data = ""
        self.stream.close()
        self.locations = locs
        self.documents = docs
        self.length = max(len(locs), len(docs))
        
# XmlTapeDocStream
# ArcFileDocStream
# MetsDocStream


class MultipleDocumentStream(BaseDocumentStream):

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        BaseDocumentStream.__init__(self, session, stream, format, tagName, codec, factory)
        filterStr = factory.get_setting(session, 'filterRegexp', "\.([a-zA-Z0-9]+|tar.gz|tar.bz2)$")
        if filterStr:
            self.filterRe = re.compile(filterStr)
        else:
            self.filterRe = None

    def _fetchStream(self, path):
        return self.open_stream(path)

    def _fetchName(self, item):
        return item

    def _processFile(self, session, item):
        name = self._fetchName(item)
        if self.filterRe:
            m = self.filterRe.search(name)
            if not m:
                return None
        mimetype = mimetypes.guess_type(name, 0)

        if (mimetype[0] in ['text/sgml', 'text/xml']):
            trip = ('stream', XmlDocumentStream, 'xml')
        elif (mimetype[0] == 'application/x-tar'):
            trip = ('stream', TarDocumentStream, 'tar')
        elif (mimetype[0] == 'application/zip'):
            trip = ('stream', ZipDocumentStream, 'zip')
        elif (mimetype[0] == 'application/marc'):
            trip = ('stream', MarcDocumentStream, 'marc')
        else:
            trip = ('document', None, mimetype)

        s = self._fetchStream(item)
        if trip[0] == 'stream':
            cls = trip[1]
            nstream = cls(session, s, format=trip[2], tagName=self.tagName, codec=self.codec, factory=self.factory)
            # copy streamLocation in to copy to document
            nstream.streamLocation = item
            return ('stream', nstream)
        elif trip[0] == 'document':
            data = s.read()
            s.close()
            doc = StringDocument(data, mimeType=trip[2], filename=name)
            return ('document', doc)

    def _processFiles(self, session, items, cache=0):
        docs = []
        for item in items:
            # Look for records in these places
            stuff = self._processFile(session, item)
            if not stuff:
                # None means skip object
                continue
            (dtype, obj) = stuff
            if dtype == 'stream':
                gen = obj.find_documents(session, cache=cache)
                if cache == 0:
                    # Will yield its documents, yield back up
                    for g in gen:
                        yield g
                elif cache == 1:
                    try:
                        gen.next()
                    except:
                        pass
                    locs.append((fullname, mimetype, nstream.locs))
                elif cache == 2:
                    try:
                        gen.next()
                    except:
                        pass
                    docs.extend(nstream.docs)
            elif dtype == 'document':
                if cache == 0:
                    yield obj
                elif cache == 1:
                    raise NotImplementedError
                elif cache == 2:
                    docs.append(obj)
        self.documents = docs

class DirectoryDocumentStream(MultipleDocumentStream):

    def find_documents(self, session, cache=0):
        for root, dirs, files in os.walk(self.streamLocation):
            for d in dirs:
                if os.path.islink(os.path.join(root, d)):
                    for root2, dirs2, files2 in os.walk(os.path.join(root,d)):
                        files2.sort()
                        files2 = [os.path.join(root2, x) for x in files2]
                        # Psyco Map Reduction
                        # files2 = map(lambda x: os.path.join(root2, x), files2)
                        for f in self._processFiles(session, files2, cache):
                            yield f
            files.sort()
            files = [os.path.join(root, x) for x in files]
            # files = map(lambda x: os.path.join(root, x), files)
            for f in self._processFiles(session, files, cache):
                yield f


class TarDocumentStream(MultipleDocumentStream):

    def open_stream(self, stream):
        if self.format in ['tar.gz', 'tgz']:
            modeSuf = "gz"
        elif self.format == 'tar.bz2':
            modeSuf = "bz2"
        else:
            modeSuf = ""

        if hasattr(stream, 'read'):
            return tarfile.open(fileobj=stream, mode="r|%s" % modeSuf)
        elif os.path.exists(stream):
            return tarfile.open(stream, mode="r") # transparent 
        else:
            s = cStringIO.StringIO(stream)
            return tarfile.open(fileobj=s, mode="r|%s" % modeSuf)
            
    def _processFile(self, session, item):
        name = self._fetchName(item)
        if name[-1] == "/":
            return None
        else:
            return MultipleDocumentStream._processFile(self, session, item)

    def _fetchStream(self, path):
        return self.stream.extractfile(path)
    def _fetchName(self, item):
        return item.name

    def find_documents(self, session, cache=0):
        # NB can't reverse in stream, send each in turn
        for tarinfo in self.stream:
            for doc in self._processFiles(session, [tarinfo], cache):
                yield doc
        self.stream.close()


class ZipDocumentStream(DirectoryDocumentStream):
    def open_stream(self, stream):
        if hasattr(stream, 'read') or os.path.exists(stream):
            return zipfile.ZipFile(stream, mode="r")
        else:
            s = cStringIO.StringIO(stream)
            return zipfile.ZipFile(s, mode="r")
            
    def _fetchStream(self, path):
        return cStringIO.StringIO(self.stream.read(path))
    def _fetchName(self, item):
        return item

    def find_documents(self, session, cache=0):
        #for info in self.stream.infolist():
        for info in self.stream.namelist():
            for doc in self._processFiles(session, [info], cache):
                yield doc
        self.stream.close()

# RarDocStream

class LocateDocumentStream(DirectoryDocumentStream):
    def find_documents(self, session, cache=0):
        fl = commands.getoutput("locate %s | grep %s$" % (self.stream, self.stream))
        docs = fl.split('\n')
        while docs and docs[0][:8] == "warning:":
            docs.pop(0)
        self._processFiles("", docs, cache)


class ClusterDocumentStream(BaseDocumentStream):
    # Take a raw cluster file, create documents from it.

    def open_stream(self, stream):
        # stream must be the filename
        # And we don't really care about it until after sorting
        if os.path.exists(stream):
            self.streamLocation = stream
        else:
            # FIXME: API: Required None for session to get_path()
            dfp = self.factory.get_path(None, 'defaultPath')
            abspath = os.path.join(dfp, stream)
            if os.path.exists(abspath):
                self.streamLocation = abspath
            else:
                raise FileDoesNotExistException(stream)

    def find_documents(self, session, cache=0):
        if cache == 1:
            # Can't store offsets as there's no file to offset to.
            raise NotImplementedError

        data = self.streamLocation
        sortx = self.factory.get_path(session, 'sortPath', None)
        if sortx == None:
            sortx = commands.getoutput('which sort')
        sorted = data + "_SORT"
        os.spawnl(os.P_WAIT, sortx, sortx, data, '-o', sorted)

        # Now construct cluster documents.
        doc = ["<cluster>"]
        f = file(sorted)
        l = f.readline()
        # term docid recstore occs (line, posn)*
        currKey = ""
        while(l):
            docdata = {}
            ldata = l.split('\x00')
            key = ldata[0]
            if (not key):
                # Data from records with no key
                l = f.readline()
                l = l[:-1]
                continue

            doc.append("<key>%s</key>\n" % (key))
            ldata = ldata[1:-1]
            for bit in range(len(ldata)/2):
                d = docdata.get(ldata[bit*2], [])                
                d.append(ldata[bit*2+1])
                docdata[ldata[bit*2]] = d
            l = f.readline()
            l = l[:-1]
            ldata2 = l.split('\x00')
            key2 = ldata2[0]
            while key == key2:   
                ldata2 = ldata2[1:-1]
                for bit in range(len(ldata2)/2):
                    d = docdata.get(ldata2[bit*2], [])
                    d.append(ldata2[bit*2+1])
                    docdata[ldata2[bit*2]] = d
                l = f.readline()
                l = l[:-1]
                ldata2 = l.split('\x00')
                key2 = ldata2[0]
            for k in docdata.keys():
                doc.append("<%s>" % (k))
                for i in docdata[k]:                    
                    doc.append("%s" % i)
                doc.append("</%s>" % (k))
            doc.append("</cluster>")
            sdoc = StringDocument(" ".join(doc))
            if cache == 0:
                yield sdoc
            else:
                self.documents.append(sdoc)

            doc = ["<cluster>"]            
            l = f.readline()
            l = l[:-1]
        f.close()

class ComponentDocumentStream(BaseDocumentStream):
    # Accept a record, and componentize
    sources = []

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        BaseDocumentStream.__init__(self, session, stream, format, tagName, codec, factory)
        self.sources = factory.sources

    def open_stream(self, stream):
        return stream

    def find_documents(self, session, cache=0):
        # Should extract records by xpath or span and store as X/SGML
        if cache == 1:
            # nothing to offset into
            raise NotImplementedError
        rec = self.stream
        for src in self.sources:
            raw = src.process_record(session, rec)
            for xp in raw:
                for r in xp:
                    if (type(r) == types.ListType):
                        tempRec = SaxRecord(r)
                        docstr = tempRec.get_xml(session)
                        saxid = r[-1][r[-1].rfind(' ')+1:]
                        if r[0][0] == "4":
                            docstr = "<c3:component xmlns:c3=\"http://www.cheshire3.org/\" parent=\"%r\" event=\"%s\">%s</c3:component>" % (rec, saxid, docstr)
                        else:
                            docstr = "<c3component parent=\"%r\" event=\"%s\">%s</c3component>" % (rec, saxid, docstr)
                    elif (type(r) == types.StringType):
                        docstr = "<c3component parent=\"%r\"><data>%s</data></c3component>" % (rec, escape(r))
                    else:
                        if r.__class__ == etree._Element:
                            # Lxml Record
                            docstr = etree.tostring(r)
                            tree = r.getroottree()
                            path = tree.getpath(r)
                            if (r.nsmap):
                                namespaceList = []
                                for (pref, ns) in r.nsmap.iteritems():
                                    namespaceList.append("xmlns:%s=\"%s\"" % (pref, ns))
                                namespaces = " ".join(namespaceList)
                                docstr = """<c3:component xmlns:c3="http://www.cheshire3.org/" %s parent="%r" xpath="%s">%s</c3component>""" % (namespaces, rec, path, docstr)
                            else:
                                docstr = """<c3component parent="%r" xpath="%s">%s</c3component>""" % (rec, path, docstr)
                        else:
                            # 4Suite
                            # Not sure how to get path to node in 4suite
                            stream = cStringIO.StringIO()
                            Print(r, stream)
                            stream.seek(0)
                            docstr = stream.read()
                            docstr = """<c3:component xmlns:c3="http://www.cheshire3.org/" parent="%r">%s</c3:component>""" % (rec, docstr)
                    doc = StringDocument(docstr)
                    if cache == 0:
                        yield doc
                    else:
                        self.documents.append(doc)


class RemoteDocumentStream(BaseDocumentStream):
    # Heirarchical Class

    def _parse_url(self, url):
        bits = urlparse.urlsplit(url)
        transport = bits[0]
        uphp = bits[1].split('@')
        user = ''
        passwd = ''
        if len(uphp) == 2:
            (user, passwd) = uphp[0].split(':')
            uphp.pop(0)
        hp = uphp[0].split(':')
        host = hp[0]
        if len(hp) == 2:
            port = int(hp[1])
        else:
            # require subclass to default
            port = 0
        # now cwd to the directory, check if last chunk is dir or file
        (dirname,filename) = os.path.split(bits[2])
        # params = map(lambda x: x.split('='), bits[3].split('&'))
        params = [x.split('=') for x in bits[3].split('&')]
        params = dict(params)
        anchor = bits[4]
        return (transport, user, passwd, host, port, dirname, filename, params, anchor)


class FtpDocumentStream(RemoteDocumentStream, MultipleDocumentStream):
    # FTP://user:pass@host:port/path/to/object
    def open_stream(self, stream):
        # streamLocation is a ftp URL
        (transport, user, passwd, host, port, dirname, filename, params, anchor) = self._parse_url(self.streamLocation)
        self.stream = FTP(host, port)
        if user:
            self.stream.login(user, passwd)
        else:
            self.stream.login()
        self.dirname = dirname
        self.file = filename

    def _fetchStream(self, path):
        currItem = []
        self.stream.retrbinary(path, lambda x: currItem.append(x))
        return cStringIO.StringIO(''.join(self.currItem))

    def _fetchName(self, item):
        return item

    def _descend(self, session, dirname, cache=0):
        self.stream.cwd(dirname)
        lines = []
        self.stream.retrlines('LIST', lambda x: lines.append(x))
        filelist = []
        for l in lines:
            # CHECKME:  Think that the uncommented version works
            # name = ' '.join(l.split()[8:])
            name = l[54:]
            if l[0] == 'l':
                # symlink, ignore?
                pass
            elif l[0] == 'd':
                # directory
                self._descend(session, name, cache)
            elif l[0] == '-':
                filelist.append(name)
            else:
                # unknown, ignore
                pass
        yield self._processFiles(session, filelist, cache)
        self.stream.cwd('..')

    def find_documents(self, session, cache=0):
        yield self._descend(session, self.dirname, cache)
        self.stream.quit()


class Z3950DocumentStream(RemoteDocumentStream):
    # Z3950://host:port/database?query=cql&...
    # (NB ... not official)

    def open_stream(self, stream):
        server = stream.replace('z3950', 'https')
        (transport, user, passwd, host, port, dirname, filename, args, anchor) = self._parse_url(server)

        conn = zoom.Connection(host, port)        
        conn.databaseName = dirname
        q = args['query']
        qo = zoom.Query('CQL', q)

        if args.has_key('preferredRecordSyntax'):
            conn.preferredRecordSyntax = args['preferredRecordSyntax']
        else:
            conn.preferredRecordSyntax = 'USMARC'
        if args.has_key('elementSetName'):
            conn.elementSetName = args['elementSetName']
        else:
            conn.elementSetName = 'F'
        rs = conn.search(qo)
        self.total = len(rs)
        return rs

    def find_documents(self, session, cache=0):
        # stream is ZOOM.resultSet
        docs = []
        for item in self.stream:
            if self.resultSet.preferredRecordSyntax == 'USMARC':
                mt = "application/marc"
            else:
                mt = mimetypes.guess_type(self.resultSet.preferredRecordSyntax)
            doc = StringDocument(item.data, mimeType=mt)
            if cache == 0:
                yield doc
            elif cache == 2:
                docs.append(doc)
            else:
                raise NotImplementedError
        self.documents = docs
        raise StopIteration


class UrllibUnicodeFileThing:
    def __init__(self, real):
        self.real = real
        self.charset = real.headers.getparam('charset')
        self.mimetype = real.headers.type

    def __getattr__(self, item):
        return getattr(self.real, item)
        
    def read(self):
        data = self.real.read()
        if self.charset:
            try:
                data = unicode(data, self.charset)                
            except:
                pass
        return data
        

class HttpDocumentStream(RemoteDocumentStream, MultipleDocumentStream):

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        MultipleDocumentStream.__init__(self, session, stream, format, tagName, codec, factory)


    def _processFile(self, session, item):
        if self.filterRe:
            m = self.filterRe.search(item)
            if not m:
                return None
            
        mimetype = mimetypes.guess_type(item, 0)
        if mimetype[0] == None:
            # get mimetype from stream
            s = self._fetchStream(item)
            mimetype = (s.mimetype, None)
        else:
            s = None

        if (mimetype[0] in ['text/sgml', 'text/xml']):
            trip = ('stream', XmlDocumentStream, 'xml')
        elif (mimetype[0] == 'application/x-tar'):
            trip = ('stream', TarDocumentStream, ftype)
        elif (mimetype[0] == 'application/zip'):
            trip = ('stream', ZipDocumentStream, 'zip')
        elif (mimetype[0] == 'application/marc'):
            trip = ('stream', MarcDocumentStream, 'marc')
        else:
            trip = ('document', None, mimetype)

        if not s:
            s = self._fetchStream(item)
        if trip[0] == 'stream':
            cls = trip[1]
            nstream = cls(session, s, format=trip[2], tagName=self.tagName, codec=self.codec, factory=self.factory)
            return ('stream', nstream)
        elif trip[0] == 'document':
            data = s.read()
            s.close()
            doc = StringDocument(data, mimeType=trip[2], filename=s.url)
            return ('document', doc)


    def find_documents(self, session, cache=0):
        url = self.stream.read()
        self.stream.close()
        for f in self._processFiles(session, [url], cache):
            yield f

    def _fetchName(self, item):
        # lookup fake name from mimetype, so we can then reguess mimetype
        mt = item.mimetype
        ext = mimetypes.guess_extension(mt)
        return "remote%s" % ext
            
    def _fetchStream(self, path):
        u = urllib2.urlopen(path)
        return UrllibUnicodeFileThing(u)


class SruDocumentStream(HttpDocumentStream):

    def open_stream(self, stream):
        # streamLocation is an SRU search
        (transport, user, passwd, host, port, dirname, filename, args, anchor) = self._parse_url(stream)
        if not port:
            port = 80
        if user:
            self.server = "%s://%s:%s@%s:%s/%s/%s?" % (transport, user, passwd, host, port, dirname, filename)
        else:
            self.server = "%s://%s:%s%s/%s?" % (transport, host, port, dirname, filename)
        
        if (not args.has_key('query')):
            raise ValueError("SruDocumentStream data requires a query param")
        if (not args.has_key('version')):
            args['version'] = '1.1'
        if (not args.has_key('maximumRecords')):
            args['maximumRecords'] = 25
        if (not args.has_key('recordPacking')):
            args['recordPacking'] = 'string'
        args['operation'] = 'searchRetrieve'

        self.args = args
        self.xmlver = re.compile("[ ]*<\?xml[^>]+>")
        return None

    
    def find_documents(self, session, cache=0):
        # Construct SRU url, fetch, parse.
        start = 1
        docs = []
        while True:            
            self.args['startRecord'] = start
            params = urllib.urlencode(self.args)
            req = urllib2.Request(url="%s%s" % (self.server, params))
            f = urllib2.urlopen(req)
            data = f.read()
            f.close()
            # subst out xmldecl
            data = self.xmlver.sub("", data);
            soapy = '<SOAP:Envelope xmlns:SOAP="http://schemas.xmlsoap.org/soap/envelope/"><SOAP:Body>%s</SOAP:Body></SOAP:Envelope>' % data
            ps = ZSI.ParsedSoap(soapy, readerclass=reader)
            resp = ps.Parse(SRW.types.SearchRetrieveResponse)

            self.total = resp.numberOfRecords
            for d in resp.records:
                doc = StringDocument(d.recordData, mimeType='text/xml')
                if cache == 0:
                    yield doc
                elif cache==2:
                    docs.append(doc)
                else:
                    raise NotImplementedError
            start += len(resp.records)
            if start > self.total:
                if cache == 0:
                    raise StopIteration
                else:
                    break
        self.documents = docs

class SrwDocumentStream(HttpDocumentStream):
    # same as Sru, but use request object and ZSI to fetch
    namespaces = {}

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        self.namespaces = SRW.protocolNamespaces
        HttpDocumentStream.__init__(self, session, stream, format, tagName,codec, factory)

    def open_stream(self, stream):
        # stream is SRU style URL to be opened as SRW
        (transport, user, passwd, host, port, dirname, filename, args, anchor) = self._parse_url(stream)
        if not port:
            port = 80
        database = os.path.join(dirname, filename)

        self.binding = Binding(host=host, port=port, url=database, nsdict=self.namespaces)
        return SRW.types.SearchRetrieveRequest('searchRetrieveRequest', opts=args)
    
    def find_documents(self, session, cache=0):
        docs = []
        curr = 1
        while True:
            self.stream.startRecord = curr
            resp = self.binding.RPC(self.binding.url,
                                    "searchRetrieveRequest",
                                    self.stream,
                                    requestclass=SRW.types.SearchRetrieveRequest,
                                    replytype=SRW.types.SearchRetrieveResponse.typecode,
                                    readerclass=reader)
            total = resp.numberOfRecords
            curr += len(resp.records)
            for d in resp.records:
                doc = StringDocument(d.recordData,  mimeType='text/xml')
                doc.recordSchema = d.recordSchema
                if cache ==0:
                    yield doc
                elif cache == 2:
                    docs.append(doc)
                else:
                    raise NotImplementedError
            if curr > total:
                if cache == 0:
                    raise StopIteration
                else:
                    break
        self.documents = docs



class OaiDocumentStream(HttpDocumentStream):
    def open_stream(self, stream):
        # nothing to do yet
        return None

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        BaseDocumentStream.__init__(self, stream, format, tagName, codec, factory)

        # stream is URL to ListIdentifiers
        # possible params: metadataPrefix, set, from, until
        bits = urlparse.urlsplit(stream)
        #self.params = dict(map(lambda x: x.split('='), bits[3].split('&')))
        self.params = [x.split('=') for x in bits[3].split('&')]
        self.metadataPrefix = params.get('metadataPrefix', 'oai_dc')
        base = bits[0] + "://" + bits[1] + '/' + bits[2] + '?'
        self.server = base

    def find_documents(self, session, cache=0):
        if cache != 0:
            raise NotImplementedError
        
        self._listIdentifiers()
        while self.idcache:
            for rec in self._getRecord():
                yield rec
            self._listIdentifiers()
        raise StopIteration


    def _listIdentifiers(self):
        s = "%sverb=ListIdentifiers&" % (self.server)
        s += urllib.urlencode(self.params)
        resp = self._fetchStream(s)
        data = resp.read()

        # self.lastResponse = resp
        # Now use existing infrastructure to parse
        doc = StringDocument(data, self.id, mimeType='text/xml')
        rec = BSParser.process_document(None, doc)
        dom = rec.get_dom(session)
        for top in dom.childNodes:
            if (top.nodeType == elementType):
                break
        for c in top.childNodes:
            if (c.nodeType == elementType and c.localName == 'ListIdentifiers'):
                for c2 in c.childNodes:
                    if (c2.nodeType == elementType and c2.localName == 'header'):
                        for c3 in c2.childNodes:
                            if (c3.nodeType == elementType and c3.localName == 'identifier'):
                                self.ids.append(getFirstData(c3))
                    elif (c2.nodeType == elementType and c2.localName == 'resumptionToken'):
                        t = getFirstData(c2)
                        if (t):
                            self.token = t
                        try:
                            self.total = c2.getAttr('completeListSize')
                        except:
                            pass
        
    def _getRecord(self):
        for oaiid in self.idcache:
            s = "%sverb=GetRecord&%s" % (self.server, urllib.urlencode({'metadataPrefix': self.metadataPrefix, 'identifier': oaiid}))
            resp = self._fetchStream(s)
            data = resp.read()
            doc = StringDocument(data, self.id, mimeType='text/xml')
            rec = BSParser.process_document(None, doc)
            dom = rec.get_dom(session)
            for top in dom.childNodes:
                if top.nodeType == elementType:
                    break
            for c in top.childNodes:
                if (c.nodeType == elementType and c.localName == 'GetRecord'):
                    for c2 in c.childNodes:        
                        if (c2.nodeType == elementType and c2.localName == 'record'):
                            for c3 in c2.childNodes:
                                if (c3.nodeType == elementType and c3.localName == 'metadata'):
                                    for c4 in c3.childNodes:
                                        if (c4.nodeType == elementType):
                                            data = c4.toxml()
                                            yield StringDocument(data, self.id, mimeType='text/xml')
                                            break
                            break
                    break
        raise StopIteration



try:
    # OS feed for open OS feeds: http://a9.com/-/opensearch/public/osrss
    # http://a9.com/-/opensearch/public/osd

    from opensearch import Client
    class OpensearchDocumentStream(HttpDocumentStream):
        # Need to know OSD location and query params
        # stream should be (osd location, query)
        # or just query if osd is set on factory config

        def _toXml(self, i):
            xml = ['<sdc:dc xmlns:sdc="info:srw/schema/1/dc-schema" xmlns:dc="http://purl.org/dc/elements/1.1/">']
            # title, description, date, link
            keys = i.keys()
            if 'title' in keys:
                xml.append('<dc:title>%s</dc:title>' % i.title)
            if 'link' in keys:
                xml.append('<dc:source>%s</dc:source>' % i.link)
            if 'author' in keys:
                xml.append('<dc:creator>%s</dc:creator>' % i.author)
            if 'updated_parsed' in keys:
                xml.append('<dc:date>%d-%02d-%02d %02d:%02d:%02d</dc:date>' % i.updated_parsed[:6])
            if 'summary' in keys:
                xml.append('<dc:description><![CDATA[%s]]></dc:description>' % i.summary)

            xml.append("</sdc:dc>")
            return '\n'.join(xml)

        def open_stream(self, stream):
            if type(self.streamLocation) == tuple:
                c = Client(self.streamLocation[0])
                self.query = streamLocation[1]
            else:
                osd = self.factory.get_setting(session, 'osdUrl', '')
                if osd:
                    c = Client(osd)
                else:
                    raise ConfigFileException
                self.query = streamLocation
            return c

        def find_documents(self, session, cache=0):
            results = self.stream.search(self.query)
            docs = []
            for r in results:
                doc = self._toXml(r)
                if cache == 0:
                    yield StringDocument(doc)
                elif cache == 2:
                    docs.append(StringDocument(doc))
                else:
                    raise NotImplementedError
            self.documents = docs
except:
    class OpensearchDocumentStream:
        pass

try:
    import feedparser
    class SyndicationDocumentStream(HttpDocumentStream):
        # Use universal feed parser to import rss, atom, etc

        def _toXml(self, i):
            xml = ['<sdc:dc xmlns:sdc="info:srw/schema/1/dc-schema" xmlns:dc="http://purl.org/dc/elements/1.1/">']
            # title, description, date, link
            keys = i.keys()
            if 'id' in keys:
                xml.append('<dc:identifier>%s</dc:identifier>' % i.id)
            if 'title' in keys:
                xml.append('<dc:title>%s</dc:title>' % i.title)
            if 'link' in keys:
                xml.append('<dc:source>%s</dc:source>' % i.link)
            if 'author' in keys:
                xml.append('<dc:creator>%s</dc:creator>' % i.author)
            if 'updated_parsed' in keys:
                xml.append('<dc:date>%d-%02d-%02d %02d:%02d:%02d</dc:date>' % i.updated_parsed[:6])
            if 'summary' in keys:
                xml.append('<dc:description><![CDATA[%s]]></dc:description>' % i.summary)
            xml.append("</sdc:dc>")
            return '\n'.join(xml)

        def open_stream(self, stream):
            # stream may be URL, filename or buffer. Nice.
            c = feedparser.parse(stream)
            return c

        def find_documents(self, session, cache=0):
            docs = []
            linked = self.factory.get_setting(session, 'linkedItem', 0)
            for e in self.stream.entries:
                if linked == 0:
                    doc = self._toXml(e)
                else:
                    s = self._fetchStream(e.link)
                    doc = s.read()
                if cache == 0:
                    yield StringDocument(doc)
                elif cache == 2:
                    docs.append(StringDocument(doc))
                else:
                    raise NotImplementedError
            self.documents = docs

except:
    class SyndicationDocumentStream(RemoteDocumentStream):
        pass
    


class DocumentFactoryIter(object):
    factory = None
    session = None

    def __init__(self, factory):
        self.factory = factory
        self.session = factory.loadSession

    def next(self):
        return self.factory.get_document(self.session)


class SimpleDocumentFactory(DocumentFactory):
    cache = 0
    format = ""
    tagName = ""
    codec = ""
    dataPath = ""
    previousIdx = -1
    streamHash = {}
    docStream = None
    generator = None
    loadSession = None
    
    _possibleDefaults = {'cache' : {'docs' : "Default value for cache parameter for load()", 'type' : int, 'options' : "0|1|2"}
                         , 'format' : {'docs' : "Default value for format parameter"}
                         , 'tagName' : {'docs' : "Default value for tagName parameter"}
                         , 'codec' : {'docs' : "Default value for codec parameter"}
                         , 'data' : {'docs' : "Default value for data parameter"}}


    _possibleSettings = {'filterRegexp' : {'docs' : "Filename filter for files to attempt to load in a multiple document stream (eg from a directory)"}
                         , 'googleKey' : {'docs' : "Key supplied by Google for using their web service interface"}
                         , 'osdUrl' : {'docs' : "URL to the OpenSearch description document"}
                         , 'linkedItem' : {'docs' : "Should the factory return the RSS/ATOM item, or the item which it is linked to."}
                         }

    
    def __init__(self, session, config, parent):
        DocumentFactory.__init__(self, session, config, parent)
        self.docStream = None
        self.generator = None
        self.streamHash = {"xml" : XmlDocumentStream,
                               "marc" : MarcDocumentStream,
                               "dir" : DirectoryDocumentStream,
                               "tar" : TarDocumentStream,
                               "zip" : ZipDocumentStream,
                               "cluster" : ClusterDocumentStream,
                               "locate" : LocateDocumentStream,
                               "component" : ComponentDocumentStream,
                               "oai" : OaiDocumentStream,
                               "sru" : SruDocumentStream,
                               "srw" : SrwDocumentStream,
                               "opensearch" : OpensearchDocumentStream,
                               "z3950" : Z3950DocumentStream,
                               "ftp" : FtpDocumentStream,
                               "http" : HttpDocumentStream,
                               "termHash" : TermHashDocumentStream,
                               "rss" : SyndicationDocumentStream
                               }
        self.cache = int(self.get_default(session, 'cache', 0))
        self.format = self.get_default(session, 'format', '').encode('utf-8')
        self.tagName = self.get_default(session, 'tagName', '')
        self.codec = self.get_default(session, 'codec', "")
        self.dataPath = self.get_default(session, 'data', '')
        self.previousIdx = -1

    def register_stream(self, session, format, cls):
        self.streamHash[format] = cls

    def load(self, session, data=None, cache=None, format=None, tagName=None, codec=None):
        self.loadSession = session
        if data == None:
            data = self.dataPath

        if format == None:
            format = self.format
        if cache == None:
            cache = self.cache
        if tagName == None:
            tagName = self.tagName
        if codec == None:
            codec = self.codec

        # Some laziness checking
        if not format:
            if os.path.exists(data):
                if data[-4:] == '.zip':
                    format = 'zip'
                elif data[-4:] == '.tar':
                    format = 'tar'
                elif data[-4:] == '.xml':
                    format = 'xml'
                elif data[-5:] == '.marc':
                    format = 'marc'
                elif os.path.isdir(data):
                    format = 'dir'
            else:
                if data[:6] == "ftp://":
                    format = 'ftp'
                elif data[:6] == "srb://":
                    format = 'srb'
                elif data[:7] == "http://" or data[:8] == "https://":
                    format = "http"
                    if data.find('?') > -1:
                        # parse url and extract param names
                        bits = urlparse.urlsplit(data)
                        # plist = map(lambda x: x.split('=')[0], bits[3].split('&'))
                        plist = [x.split('=')[0] for x in bits[3].split('&')]
                        if 'verb' in plist and 'metadataPrefix' in plist:
                            format = 'oai'
                        elif 'operation' in plist and 'version' in plist and 'query' in plist:
                            format = 'sru'

        cls = self.streamHash[format]
        ds = cls(session, data, format, tagName, codec, self)
        
        # Store and call generator on first ping
        self.docStream = ds
        self.generator = ds.find_documents(session, cache=cache)
        self.previousIdx = -1
        self.cache = cache
        # Return self for workflows, mostly can ignore
        return self

    def __iter__(self):
        return DocumentFactoryIter(self)

    def get_document(self, session, n=-1):
        if n == -1:
            self.previousIdx += 1
            idx = self.previousIdx
        if self.cache == 0:
            # gen will yield, return
            return self.generator.next()
        elif self.cache == 1:
            return self.docStream.fetch_document(idx)
        elif self.cache == 2:
            if not self.docStream.documents and self.generator:
                try:
                    self.generator.next()
                except StopIteration:
                    pass
            return self.docStream.documents[n]


class ComponentDocumentFactory(SimpleDocumentFactory):

    def _handleConfigNode(self, session, node):
        # Source
        if (node.localName == "source"):
            xpaths = []
            for child in node.childNodes:
                if child.nodeType == elementType:
                    if child.localName == "xpath":
                        # add XPath
                        ref = child.getAttributeNS(None, 'ref')
                        if ref:
                            xp = self.get_object(session, ref)
                        else:
                            xp = SimpleXPathProcessor(session, node, self)
                            xp._handleConfigNode(session, node)
                        self.sources.append(xp)

    def __init__(self, session, config, parent):
        self.sources = []
        SimpleDocumentFactory.__init__(self, session, config, parent)


class AccumulatingStream(BaseDocumentStream):
    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        self.factory = factory
        self.format = format
        self.tagName = tagName
        self.codec = codec
        # And call accumulate to record stream
        self.accumulate(session, stream, format, tagName, codec, factory)

    def accumulate(self, session, stream, format, tagName=None, codec=None, factory=None ):
        raise NotImplementedError



class AccTransformerStream(AccumulatingStream):
    """ Call a transformer on each input record and concatenate results
    Transformer should return a string
    """

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        if not factory:
            raise ValueError("Cannot build transformer stream without associated documentFactory")
        self.transformer = factory.get_path(session, 'accumulatingTransformer', None)
        if not self.transformer:
            raise ConfigFileException("DocumentFactory does not have 'accumulatingTransformer' path for AccTransformerStream")
        self.data = []

        # now init the AccStream after discovering txr
        AccumulatingStream.__init__(self, session, stream, format, tagName, codec, factory)

    def accumulate(self, session, stream, format, tagName=None, codec=None, factory=None ):
        # session should be record instance
        doc = self.transformer.process_record(session, stream)
        self.data.append(doc.get_raw(session))

    def find_documents(self, session, cache=0):
        yield StringDocument(''.join(self.data))


class AccVectorTransformerStream(AccumulatingStream):
    """
    Accumulate data to be fed to DM, via a vector transformer
    """

    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        if not factory:
            raise ValueError("Cannot build transformer stream without associated documentFactory")
        self.transformer = factory.get_path(session, 'accumulatingTransformer', None)
        if not self.transformer:
            raise ConfigFileException("DocumentFactory does not have 'accumulatingTransformer' path for AccTransformerStream")
        self.classes = []
        self.vectors = []
        self.totalAttributes = 0
        # now init the AccStream after discovering txr
        AccumulatingStream.__init__(self, session, stream, format, tagName, codec, factory)

    def accumulate(self, session, stream, format, tagName=None, codec=None, factory=None ):
        # session should be record instance
        doc = self.transformer.process_record(session, stream)
        raw  = doc.get_raw(session)
        if type(raw) == list:
                # multiple from proxVector (etc)
                for (l,v) in raw:
                    self.classes.append(l)
                    self.vectors.append(v)
                    self.totalAttributes += len(v.keys())                
        else:
            # we're a tuple
            self.classes.append(raw[0])
            self.vectors.append(raw[1])
            self.totalAttributes += len(raw[1].keys())


    def find_documents(self, session, cache=0):
        doc = StringDocument([self.classes, self.vectors])
        doc.totalAttributes = self.totalAttributes
        yield doc



if 0:
    # XXX Fix Me!

    class ClassClusterDocumentStream(AccumulatingStream):
        """ Give it lots of documents, it will cluster and then read back in the cluster documents. Niiiiiiiice. [in theory] """

        def _handleConfigNode(self, session, node):
            if (node.localName == "cluster"):
                maps = []
                for child in node.childNodes:
                    if (child.nodeType == elementType and child.localName == "map"):
                        t = child.getAttributeNS(None, 'type')
                        map = []
                        for xpchild in child.childNodes:
                            if (xpchild.nodeType == elementType and xpchild.localName == "xpath"):
                                map.append(flattenTexts(xpchild))
                            elif (xpchild.nodeType == elementType and xpchild.localName == "process"):
                                # turn xpath chain to workflow
                                ref = xpchild.getAttributeNS(None, 'ref')
                                if ref:
                                    process = self.get_object(session, ref)
                                else:
                                    try:
                                        xpchild.localName = 'workflow'
                                    except:
                                        # 4suite dom sets read only
                                        newTop = xpchild.ownerDocument.createElementNS(None, 'workflow')
                                        for kid in xpchild.childNodes:
                                            newTop.appendChild(kid)
                                        xpchild = newTop
                                    process = CachingWorkflow(session, xpchild, self)
                                    process._handleConfigNode(session, xpchild)
                                map.append(process)
                        vxp = verifyXPaths([map[0]])
                        if (len(map) < 3):
                            # default ExactExtractor
                            map.append([['extractor', 'SimpleExtractor']])
                        if (t == u'key'):
                            self.keyMap = [vxp[0], map[1], map[2]]
                        else:
                            maps.append([vxp[0], map[1], map[2]])
                self.maps = maps

        def __init__(self, session, stream, format, tagName, codec, factory):
            # XXX FIX ME:  Used to be an index!
            self.keyMap = []
            self.maps = []
            Index.__init__(self, session, config, parent)

            for m in range(len(self.maps)):
                if isinstance(self.maps[m][2], list):
                    for t in range(len(self.maps[m][2])):
                        o = self.get_object(session, self.maps[m][2][t][1])
                        if (o <> None):
                            self.maps[m][2][t][1] = o
                        else:
                            raise(ConfigFileException("Unknown object %s" % (self.maps[m][2][t][1])))
            if isinstance(self.keyMap[2], list):
                for t in range(len(self.keyMap[2])):
                    o = self.get_object(session, self.keyMap[2][t][1])
                    if (o <> None):
                        self.keyMap[2][t][1] = o
                    else:
                        raise(ConfigFileException("Unknown object %s" % (self.keyMap[2][t][1])))


        def begin_indexing(self, session):
            path = self.get_path(session, "tempPath")
            if (not os.path.isabs(path)):
                dfp = self.get_path(session, "defaultPath")
                path = os.path.join(dfp, path)       
            self.fileHandle = codecs.open(path, "w", 'utf-8')

        def commit_indexing(self, session):
            self.fileHandle.close()


        def index_record(self, session, rec):
            # Extract cluster information, append to temp file
            # Step through .maps keys
            p = self.permissionHandlers.get('info:srw/operation/2/cluster', None)
            if p:
                if not session.user:
                    raise PermissionException("Authenticated user required to cluster using %s" % self.id)
                okay = p.hasPermission(session, session.user)
                if not okay:
                    raise PermissionException("Permission required to cluster using %s" % self.id)

            raw = rec.process_xpath(session, self.keyMap[0])
            keyData = self.keyMap[2].process(session, [raw])
            fieldData = []
            for map in self.maps:
                raw = rec.process_xpath(session, map[0])
                fd = map[2].process(session, [raw])
                for f in fd.keys():
                    fieldData.append("%s\x00%s\x00" % (map[1], f))
            d = "".join(fieldData)
            for k in keyData.keys():
                try:
                    self.fileHandle.write(u"%s\x00%s\n" % (k, d))
                    self.fileHandle.flush()
                except:
                    print "%s failed to write: %r" % (self.id, k)
                    raise
            


class AccumulatingDocumentFactory(SimpleDocumentFactory):
    """ Will accumulate data across multiple .load() calls to produce 1 or more documents
    Just call load() repeatedly before fetching document(s)
    """

    _possiblePaths = {'accumulatingTransformer' : {'docs' : "Transformer through which to pass records before accumulating."}}


    def __init__(self, session, config, parent):
        SimpleDocumentFactory.__init__(self, session, config, parent)
        self.register_stream(session, 'transformer', AccTransformerStream)
        self.register_stream(session, 'vectorTransformer', AccVectorTransformerStream)

    def loadMany(self, session, data=None, cache=None, format=None, tagName=None, codec=None):
        for item in data:
            self.load(session, item, cache, format, tagName, codec)

    def load(self, session, data=None, cache=None, format=None, tagName=None, codec=None):

        self.loadSession = session

        if data == None:
            data = self.dataPath
        if format == None:
            format = self.format
        if cache == None:
            cache = self.cache
        if tagName == None:
            tagName = self.tagName
        if codec == None:
            codec = self.codec

        # Some laziness checking

        if not format:
            if os.path.exists(data):
                if data[-4:] == '.zip':
                    format = 'zip'
                elif data[-4:] == '.tar':
                    format = 'tar'
                elif data[-4:] == '.xml':
                    format = 'xml'
                elif data[-5:] == '.marc':
                    format = 'marc'
                elif os.path.isdir(data):
                    format = 'dir'
            else:
                if data[:6] == "ftp://":
                    format = 'ftp'
                elif data[:6] == "srb://":
                    format = 'srb'
                elif data[:7] == "http://" or data[:8] == "https://":
                    format = "http"
                    if data.find('?') > -1:
                        # parse url and extract param names
                        bits = urlparse.urlsplit(data)
                        # plist = map(lambda x: x.split('=')[0], bits[3].split('&'))
                        plist = [x.split('=')[0] for x in bits[3].split('&')]
                        if 'verb' in plist and 'metadataPrefix' in plist:
                            format = 'oai'
                        elif 'operation' in plist and 'version' in plist and 'query' in plist:
                            format = 'sru'

        if not self.docStream:
            cls = self.streamHash[format]
            self.docStream = cls(session, data, format, tagName, codec, self)
        else:
            self.docStream.accumulate(session, data, format, tagName, codec, self)
        self.previousIdx = -1
        self.cache = cache
        # Return self for workflows, mostly can ignore
        return self


    def get_document(self, session, n=-1):
        if self.previousIdx == -1:
            # call find docs for real
            self.generator = self.docStream.find_documents(session, cache=self.cache)
        return SimpleDocumentFactory.get_document(self, session, n)

