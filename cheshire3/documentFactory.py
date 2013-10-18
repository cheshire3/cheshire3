
import os
import re
import codecs
import mimetypes
import zipfile
import tarfile
import urlparse

from lxml import etree
from xml.sax.saxutils import escape
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from cheshire3.baseObjects import DocumentFactory
from cheshire3.document import StringDocument
from cheshire3.record import SaxRecord
from cheshire3.utils import elementType, getFirstData
from cheshire3.utils import flattenTexts, getShellResult
from cheshire3.workflow import CachingWorkflow
from cheshire3.xpathProcessor import SimpleXPathProcessor
from cheshire3.exceptions import FileDoesNotExistException, \
ConfigFileException, PermissionException
from cheshire3.internal import CONFIG_NS

mimetypes.add_type('application/marc', '.marc')
sliceRe = re.compile('^(.*)\[([0-9]+):([-0-9]+)\]$')

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
    startOffset = 0
    endOffset = -1

    def __init__(self, session, stream, format_, 
                 tagName="", codec=None, factory=None):
        self.startOffset = 0
        self.endOffset = -1
        self.factory = factory
        self.format = format_
        if type(tagName) == unicode:
            self.tagName = tagName.encode('utf-8')
        else:
            self.tagName = tagName
        self.codec = codec
        self.stream = self.open_stream(stream)

    def open_stream(self, stream):
        u"""Perform any operations needed before data stream can be read."""
        if hasattr(stream, 'read') and hasattr(stream, 'seek'):
            # Is a stream
            self.streamLocation = "UNKNOWN"
            return stream
        else:
            exists = os.path.exists(stream)
            m = sliceRe.match(stream)
            if not exists and m:
                (stream, start, end) = m.groups()
                exists = os.path.exists(stream)
                self.startOffset = int(start)
                self.endOffset = int(end)
            else:
                self.startOffset = 0
                self.endOffset = -1               

            if exists:
                # is a file
                self.streamLocation = stream
                if not os.path.isdir(stream):
                    if self.codec:
                        return codecs.open(self.streamLocation, 
                                           'r', 
                                           self.codec)
                    else:
                        return file(self.streamLocation)
                else:
                    return stream
            else:
                # is a string
                self.streamLocation = "STRING"
                return StringIO(stream)

    def fetch_document(self, idx):
        if self.length and idx >= self.length:
            try:
                self.stream.close()
            except:
                # If loaded with cache == 2 will already have been closed
                pass
            raise StopIteration
        if self.documents:
                return self.documents[idx]
        elif self.locations:
            self.stream.seek(self.locations[idx][0])
            data = self.stream.read(self.locations[idx][1])
            return StringDocument(data,
                                  filename=self.streamLocation,
                                  byteOffset=self.locations[idx][0],
                                  byteCount=self.locations[idx][1])
        else:
            raise StopIteration

    def find_documents(self, session, cache=0):
        raise NotImplementedError


class FileDocumentStream(BaseDocumentStream):
    u"""Reads in a single file."""

    def find_documents(self, session, cache=0):
        doc = StringDocument(self.stream.read(),
                             filename=self.streamLocation
                             )
        # Attempt to guess the mime-type
        mimetype = mimetypes.guess_type(self.streamLocation, 0)
        if mimetype[0]:
            doc.mimeType = mimetype[0]
        if mimetype[1]:
            doc.compression = mimetype[1]
        # Return/Yield Document
        if cache == 0:
            yield doc
        elif cache == 2:
            self.documents = [doc]


class TermHashDocumentStream(BaseDocumentStream):
    u"""Given data as a hash of terms, treat each term as a Document."""

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

    def __init__(self, session, stream, format_,
                 tagName="", codec="", factory=None):
        BaseDocumentStream.__init__(self, session, stream, format_,
                                    tagName, codec, factory)
        if (not tagName):
            tagregex = "<([-a-zA-Z0-9_.]+:)?([-a-zA-Z0-9_.]+)[\s>]"
            self.start = re.compile(tagregex)
            self.endtag = ""
        else:
            self.start = re.compile("<%s[\s>]" % tagName)
            self.endtag = "</" + tagName + ">"
        self.maxGarbageBytes = factory.get_setting(session, 
                                                   'maxGarbageBytes', 
                                                   10000)

    def _getStreamLen(self):
        # irods
        # irods tell:  strm.getPosition()
        if hasattr(self.stream, 'getSize'):
            return self.stream.getSize()
        else:
            orig = self.stream.tell()
            self.stream.seek(0, os.SEEK_END)
            fl = self.stream.tell()
            self.stream.seek(orig, os.SEEK_SET)
            return fl

    def find_documents(self, session, cache=0):
        docs = []
        locs = []
        endtag = self.endtag
        let = len(endtag)
        myTell = 0
        xpi = ""
        line = ""
        offOffset = 0

        filelen = self._getStreamLen()

        if self.startOffset > 0:
            self.stream.seek(self.startOffset, os.SEEK_SET)
        else:
            self.stream.seek(0, os.SEEK_SET)

        while True:
            ol = len(line)
            # Should exit if self.maxGarbageBytes (default 10000) bytes of 
            # garbage between docs
            if self.tagName or ol < self.maxGarbageBytes:
                line += self.stream.read(1024)
            else:
                msg = ("Exiting from XML Document Stream before end of "
                       "stream ({0}), reached maximum garbage bytes "
                       "({1})".format(self.streamLocation, 
                                      self.maxGarbageBytes))
                self.factory.log_critical(session, msg)
                break
            pi = line.find("<?xml ")                
            if (pi > -1):
                # Store info
                endpi = line.find("?>")
                xpi = line[pi:endpi + 2] + "\n"
                xpi = ""
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
                        end = line.find(endtag, strStart - let)
                    else:
                        end = line.find(endtag)
                    if end > 0:
                        tlen = end + len(endtag)
                        txt = line[:tlen]
                        line = line[tlen:]
                        myTell += tlen
                        try:
                            byteCount = len(txt.encode('utf-8'))
                        except:
                            byteCount = tlen

                        if (self.endOffset > 0 and 
                            myTell >= (self.endOffset - self.startOffset)):
                            if cache == 0:
                                self.stream.close()
                                raise StopIteration
                            else:
                                break
                        doc = StringDocument(xpi + txt,
                                             mimeType="text/xml",
                                             tagName=self.tagName,
                                             byteCount=byteCount,
                                             byteOffset=start + offOffset,
                                             filename=self.streamLocation)
                        if cache == 0:
                            yield doc
                        elif cache == 1:
                            locs.append((start, tlen))
                        elif cache == 2:
                            docs.append(doc)
                        offOffset += (byteCount - tlen)
                    else:
                        strStart = len(line)
                        # Can we get by without using 'tell()' or similar?
                        # eg for stream APIs that don't support it
                        try:
                            tll = self.stream.tell()
                        except AttributeError:
                            tll = self.stream.getPosition()
                        # Check we have at least 1024 to read
                        if tll == filelen:
                            # we've got nuffink!
                            if cache == 0:
                                self.stream.close()
                                raise StopIteration
                            else:
                                break
                        if tll + 1024 < filelen:
                            line += self.stream.read(1024)
                        else:
                            line += self.stream.read()

            if len(line) == ol and not m:
                if cache == 0:
                    self.stream.close()
                    raise StopIteration
                else:
                    break
        if cache == 2:
            # If cache == 1 , we'll need the file open later to actually read
            # Documents from the identified offsets
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
                txt = data[:rt + 1]
                tlen = len(txt)
                if cache == 0:
                    yield StringDocument(txt, mimeType="application/marc")
                elif cache == 1:                    
                    locs.append((myTell, tlen))
                elif cache == 2:
                    docs.append(StringDocument(txt, 
                                               mimeType="application/marc"))
                data = data[rt + 1:]
                myTell += tlen
                rt = data.find("\x1D")
            dlen = len(data)
            data += self.stream.read(1536)
            if (len(data) == dlen):
                # Junk at end of file
                data = ""
        if cache == 2:
            # If cache == 1 , we'll need the file open later to actually read
            # Documents from the identified offsets
            self.stream.close()
        self.locations = locs
        self.documents = docs
        self.length = max(len(locs), len(docs))

# XmlTapeDocStream
# ArcFileDocStream
# MetsDocStream


class MultipleDocumentStream(BaseDocumentStream):

    def __init__(self, session, stream, format_, 
                 tagName=None, codec=None, factory=None):
        BaseDocumentStream.__init__(self, session, stream, format_, 
                                    tagName, codec, factory)
        filterStr = factory.get_setting(session, 
                                        'filterRegexp', 
                                        "\.([a-zA-Z0-9]+|tar.gz|tar.bz2)$")
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
        if (mimetype[0] in ['text/sgml', 
                            'text/xml', 
                            'application/sgml', 
                            'application/xml']):
            if mimetype[1] == 'gzip':
                msg = '''\
XML files compressed using gzip are not yet supported. \
You could try using zip.'''
                raise NotImplementedError(msg)
            trip = ('stream', XmlDocumentStream, 'xml')
        elif (mimetype[0] == 'application/x-tar'):
            if mimetype[1] == 'gzip':
                trip = ('stream', TarDocumentStream, 'tar.gz')
            elif mimetype[1] == 'bzip2':
                trip = ('stream', TarDocumentStream, 'tar.bz2')
            else:
                trip = ('stream', TarDocumentStream, 'tar')
        elif (mimetype[0] == 'application/zip'):
            trip = ('stream', ZipDocumentStream, 'zip')
        elif (mimetype[0] == 'application/marc'):
            trip = ('stream', MarcDocumentStream, 'marc')
        else:
            if self.tagName:
                trip = ('stream', XmlDocumentStream, 'xml')
            else:
                trip = ('document', None, mimetype[0])
        s = self._fetchStream(item)
        if trip[0] == 'stream':
            cls = trip[1]
            nstream = cls(session, s, format_=trip[2], 
                          tagName=self.tagName, 
                          codec=self.codec, 
                          factory=self.factory)
            # copy streamLocation in to copy to document
            nstream.streamLocation = item
            return ('stream', nstream)
        elif trip[0] == 'document':
            data = s.read()
            s.close()
            doc = StringDocument(data, mimeType=trip[2], filename=name)
            if mimetype[1]:
                doc.compression = mimetype[1]
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
        if  not os.path.isabs(self.streamLocation):
            self.streamLocation = os.path.join(
                self.factory.get_path(session, 'defaultPath'),
                self.streamLocation)
        for root, dirs, files in os.walk(self.streamLocation):
            for d in dirs:
                if os.path.islink(os.path.join(root, d)):
                    for root2, dirs2, files2 in os.walk(os.path.join(root,
                                                                     d)):
                        # Sort for intuitive processing order
                        files2.sort()
                        files2 = [os.path.join(root2, x) for x in files2]
                        for f in self._processFiles(session, files2, cache):
                            yield f
            files.sort()
            files = [os.path.join(root, x) for x in files]
            # files = map(lambda x: os.path.join(root, x), files)
            for f in self._processFiles(session, files, cache):
                yield f


class TarDocumentStream(MultipleDocumentStream):
    u"""Unpacks a tar file."""

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
            # Transparent
            return tarfile.open(stream, mode="r") 
        else:
            s = StringIO(stream)
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
    u"""Unzips a ZIP file."""
    def open_stream(self, stream):
        if hasattr(stream, 'read') or os.path.exists(stream):
            return zipfile.ZipFile(stream, mode="r")
        else:
            s = StringIO(stream)
            return zipfile.ZipFile(s, mode="r")

    def _fetchStream(self, path):
        return StringIO(self.stream.read(path))

    def _fetchName(self, item):
        return item

    def find_documents(self, session, cache=0):
        # For info in self.stream.infolist():
        for info in self.stream.namelist():
            for doc in self._processFiles(session, [info], cache):
                yield doc
        self.stream.close()

# RarDocStream


class LocateDocumentStream(DirectoryDocumentStream):
    u"""Find files whose name matches the data argument to 'load'."""
    def find_documents(self, session, cache=0):
        fl = getShellResult("locate {0} | grep {1}$".format(self.stream, 
                                                            self.stream))
        docs = fl.split('\n')
        while docs and docs[0][:8] == "warning:":
            docs.pop(0)
        self._processFiles("", docs, cache)


class ClusterDocumentStream(BaseDocumentStream):
    u"""Takes a raw cluster file, create documents from it."""

    def open_stream(self, stream):
        # stream must be the filename
        # And we don't really care about it until after sorting
        if os.path.exists(stream):
            self.streamLocation = stream
        else:
            # FIXME: API: Required None for session to get_path()
            dfp = self.factory.get_path(None, 'defaultPath')
            # TODO: testme
            # dfp = self.factory.get_path(self.factory.loadSession, 
            #                             'defaultPath')
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
        if sortx is None:
            sortx = getShellResult('which sort')
        sortedFn = data + "_SORT"
        os.spawnl(os.P_WAIT, sortx, sortx, data, '-o', sortedFn)

        # Now construct cluster documents.
        doc = ["<cluster>"]
        f = file(sortedFn)
        l = f.readline()
        # Term docid recstore occs (line, posn)*
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
            for bit in range(len(ldata) / 2):
                d = docdata.get(ldata[bit * 2], [])
                d.append(ldata[bit * 2 + 1])
                docdata[ldata[bit * 2]] = d
            l = f.readline()
            l = l[:-1]
            ldata2 = l.split('\x00')
            key2 = ldata2[0]
            while key == key2:   
                ldata2 = ldata2[1:-1]
                for bit in range(len(ldata2) / 2):
                    d = docdata.get(ldata2[bit * 2], [])
                    d.append(ldata2[bit * 2 + 1])
                    docdata[ldata2[bit * 2]] = d
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
    u"""Accepts a record, and componentize."""

    sources = []

    def __init__(self, session, stream, format_, 
                 tagName=None, codec=None, factory=None):
        BaseDocumentStream.__init__(self, session, stream, format_, 
                                    tagName, codec, factory)
        self.sources = factory.sources

    def open_stream(self, stream):
        return stream
    
    def _make_startTag(self, element, addText=True):
        # Return a string representing the start tag for this element
        if not isinstance(element, etree._Element):
            raise TypeError("called _make_startTag on non-etree element")
        if addText and element.text:
            text = element.text
        else:
            text = ""
        # Serialize attributes
        attrs = ' '.join(['%s="%s"' % x
                          for x in element.attrib.items()])
        if attrs:
            attrs = ' ' + attrs
        if element.nsmap:
            ns = element.tag[1:element.tag.find('}') + 1]
            tag = element.tag[element.tag.find('}') + 1:]
            for prefix, namespace in element.nsmap.iteritems():
                if ns == namespace:
                    break
            if prefix is None:
                return "<{0}{1}>{2}".format(tag, attrs, text)
            else:
                return "<{0}:{1}{2}>{3}".format(prefix, tag, attrs, text)
        else:
            return "<{0}{1}>{2}".format(element.tag,
                                        attrs,
                                        text
                                        )
    
    def _make_endTag(self, element, addTail=True):
        # Return a string representing the end tag for this element
        if not isinstance(element, etree._Element):
            raise TypeError("called _make_endTag on non-etree element")
        if addTail and element.tail:
            tail = element.tail
        else:
            tail = ""
        if element.nsmap:
            ns = element.tag[1:element.tag.find('}') + 1]
            tag = element.tag[element.tag.find('}') + 1:]
            for prefix, namespace in element.nsmap.iteritems():
                if ns == namespace:
                    break
            if prefix is None:
                return "</{0}>{1}".format(tag, tail)
            else:
                return "</{0}:{1}>{2}".format(prefix, tag, tail)
        else:
            return "</{0}>{1}".format(element.tag,
                                        tail
                                        )

    def find_documents(self, session, cache=0):
        # Should extract records by xpath or span and store as X/SGML
        if cache == 1:
            # Nothing to offset into
            raise NotImplementedError
        rec = self.stream
        hasNsRe = re.compile('<([a-zA-Z1-9_-]+:[a-zA-Z1-9_-])[ >]')
        for src in self.sources:
            raw = src.process_record(session, rec)
            for xp in raw:
                if (isinstance(xp, tuple) and 
                    len(xp) == 2 and 
                    isinstance(xp[0], etree._Element)):
                    # Result of a SpanXPathSelector: (startNode, endNode)
                    startNode, endNode = xp
                    # Find common ancestor
                    sancs = list(startNode.iterancestors())
                    eancs = list(endNode.iterancestors())
                    # Common ancestor must exist in the shorter of the 2 lists
                    # Trim both to this size
                    sancs.reverse()
                    eancs.reverse()
                    minlen = min(len(sancs), len(eancs))
                    sancs = sancs[:minlen]
                    eancs = eancs[:minlen]
                    # Iterate through both, simultaneously
                    for sanc, eanc in zip(sancs, eancs):
                        if sanc == eanc:
                            common_ancestor = sanc
                            break
                    # Should include start and end tags
                    includeStartTag = self.factory.get_setting(session,
                                                               "keepStart",
                                                               1)
                    includeEndTag = self.factory.get_setting(session,
                                                             "keepEnd",
                                                             1)
                    recording = False
                    doc = []
                    opened = []
                    closed = []
                    # Walk events (start element, end element etc.)
                    for evt, el in etree.iterwalk(common_ancestor,
                                                  events=('start', 'end',
                                                          'start-ns',
                                                          'end-ns')):
                        if (el == startNode and not recording):
                            if (includeStartTag and
                                evt in ['start', 'start-ns']):
                                recording = True
                            elif (not includeStartTag and 
                                  evt in ['end', 'end-ns']):
                                # No start node
                                # Append tail and skip to next node
                                recording = True
                                if el.tail:
                                    doc.append(el.tail)
                                continue
                        elif (el == endNode and 
                              evt in ['start', 'start-ns']):
                            if includeEndTag:
                                doc.append(self._make_startTag(el))
                                doc.append(self._make_endTag(el,
                                                             addTail=False))
                            break
                        if recording and isinstance(el.tag, str):
                            if evt in ['start', 'start-ns']:
                                doc.append(self._make_startTag(el))
                                opened.append(el)
                            else:
                                doc.append(self._make_endTag(el))
                                if el in opened:
                                    opened.remove(el)
                                else:
                                    closed.append(el)
                    # Close opened things
                    opened.reverse()
                    for el in opened:
                        doc.append(self._make_endTag(el, addTail=False))
                    # Open closed things
                    for el in closed:
                        doc.insert(0, self._make_startTag(el, addText=False))
                    docstr = ''.join(doc)
                    r = startNode
                    tree = r.getroottree()
                    path = tree.getpath(r)
                    if (r.nsmap):
                        namespaceList = []
                        for (pref, ns) in r.nsmap.iteritems():
                            if pref is None:
                                namespaceList.append("xmlns=\"%s\"" % (ns))
                            else:
                                namespaceList.append("xmlns:%s=\"%s\"" % (pref, 
                                                                          ns))
                        namespaces = " ".join(namespaceList)
                        docstr = """\
<c3:component xmlns:c3="http://www.cheshire3.org/schemas/component/" \
%s parent="%r" xpath="%s">%s</c3:component>""" % (namespaces,
                                                 rec,
                                                 path,
                                                 docstr)
                    else:
                        docstr = """\
<c3component parent="%r" xpath="%s">%s</c3component>""" % (rec, path, docstr)
                    doc = StringDocument(docstr)
                    if cache == 0:
                        yield doc
                    else:
                        self.documents.append(doc)
                    continue
                # Iterate through selected data
                for r in xp:
                    if isinstance(r, list):
                        tempRec = SaxRecord(r)
                        docstr = tempRec.get_xml(session)
                        hasNs = hasNsRe.search(docstr)
                        saxid = r[-1][r[-1].rfind(' ') + 1:]
                        if hasNs:
                            docstr = """\
<c3:component xmlns:c3=\"http://www.cheshire3.org/schemas/component/\" \
parent=\"%r\" event=\"%s\">%s</c3:component>""" % (rec, saxid, docstr)
                        else:
                            docstr = """\
<c3component parent=\"%r\" event=\"%s\">%s</c3component>""" % (rec, 
                                                               saxid, 
                                                               docstr)
                    elif isinstance(r, basestring):
                        docstr = """\
<c3component parent=\"%r\"><data>%s</data></c3component>""" % (rec, escape(r))
                    else:
                        if isinstance(r, etree._Element):
                            # Lxml Record
                            docstr = etree.tostring(r)
                            tree = r.getroottree()
                            path = tree.getpath(r)
                            if (r.nsmap):
                            #if hasNs:
                                namespaceList = []
                                for (pref, ns) in r.nsmap.iteritems():
                                    namespaceList.append(
                                        'xmlns:%s="%s"' % (pref, ns)
                                    )
                                namespaces = " ".join(namespaceList)
                                docstr = """\
<c3:component xmlns:c3="http://www.cheshire3.org/schemas/component/" \
%s parent="%r" xpath="%s">%s</c3component>""" % (namespaces, rec, path, docstr)
                            else:
                                docstr = """\
<c3component parent="%r" xpath="%s">%s</c3component>""" % (rec, path, docstr)
                        else:
                            raise ValueError("Unknown Record Type")
                    doc = StringDocument(docstr)
                    if cache == 0:
                        yield doc
                    else:
                        self.documents.append(doc)


class DocumentFactoryIter(object):
    factory = None
    session = None

    def __init__(self, factory):
        self.factory = factory
        self.session = factory.loadSession

    def next(self):
        try:
            return self.factory.get_document(self.session)
        except IndexError:
            raise StopIteration


streamHash = {"xml": XmlDocumentStream,
              "marc": MarcDocumentStream,
              "dir": DirectoryDocumentStream,
              "tar": TarDocumentStream,
              "zip": ZipDocumentStream,
              "cluster": ClusterDocumentStream,
              "locate": LocateDocumentStream,
              "component": ComponentDocumentStream,
              "termHash": TermHashDocumentStream,
              "file": FileDocumentStream
              }


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

    _possibleDefaults = {
        'cache': {
            'docs': "Default value for cache parameter for load()", 
            'type': int, 
            'options': "0|1|2"
        }, 
        'format': {
            'docs': "Default value for format parameter"
        },
        'tagName': {
            'docs': "Default value for tagName parameter"
        },
        'codec': {
            'docs': "Default value for codec parameter"
        },
        'data': {
            'docs': "Default value for data parameter"
        }
    }

    _possibleSettings = {
        'filterRegexp': {
            'docs': ("Filename filter for files to attempt to load in a "
                     "multiple document stream (eg from a directory)")
        },
        'googleKey': {
            'docs': ("Key supplied by Google for using their web service "
                     "interface")
        },
        'osdUrl': {
            'docs': "URL to the OpenSearch description document"
        },
        'linkedItem': {
            'docs': ("Should the factory return the RSS/ATOM item, or the "
                     "item which it is linked to.")
        },
        'maxGarbageBytes': {
            'docs': ('Number of bytes of non document content after which to '
                     'exit'), 
            'type': int}
        }

    def __init__(self, session, config, parent):
        DocumentFactory.__init__(self, session, config, parent)
        self.docStream = None
        self.generator = None
        self.cache = int(self.get_default(session, 'cache', 0))
        self.format = self.get_default(session, 'format', '').encode('utf-8')
        self.tagName = self.get_default(session, 'tagName', '')
        self.codec = self.get_default(session, 'codec', "")
        self.dataPath = self.get_default(session, 'data', '')
        self.previousIdx = -1

    @classmethod
    def register_stream(cls, format_, streamClass):
        cls.streamHash[format_] = streamClass

    def load(self, session, data=None, cache=None, 
             format_=None, tagName=None, codec=None):
        self.loadSession = session
        if data is None:
            data = self.dataPath

        if format_ is None:
            format_ = self.format
        if cache is None:
            cache = self.cache
        if tagName is None:
            tagName = self.tagName
        if codec is None:
            codec = self.codec

        # Some laziness checking
        if not format_:
            if os.path.exists(data):
                if data.endswith('.zip'):
                    format_ = 'zip'
                elif data.endswith('.tar'):
                    format_ = 'tar'
                elif data.endswith('.xml'):
                    format_ = 'xml'
                elif data.endswith('.marc'):
                    format_ = 'marc'
                elif os.path.isdir(data):
                    format_ = 'dir'
            else:
                if data.startswith("ftp://"):
                    format_ = 'ftp'
                elif data.startswith("srb://"):
                    format_ = 'srb'
                elif data.startswith(("irods://", "rods://")):
                    format_ = 'irods'
                elif data.startswith(("http://", "https://")):
                    if hasattr(data, '_formatter_parser'):
                        # RDF URIRef
                        data = str(data)
                    format_ = "http"
                    if data.find('?') > -1:
                        # Parse url and extract param names
                        bits = urlparse.urlsplit(data)
                        plist = [x.split('=')[0] for x in bits[3].split('&')]
                        if 'verb' in plist and 'metadataPrefix' in plist:
                            format_ = 'oai'
                        elif ('operation' in plist and 
                              'version' in plist and 
                              'query' in plist):
                            format_ = 'sru'

        try:
            cls = self.streamHash[format_]
        except KeyError:
            # Just assume single binary data file path
            cls = self.streamHash['file']

        ds = cls(session, data, format_, tagName, codec, self)
        # Store and call generator on first ping
        self.docStream = ds
        self.generator = ds.find_documents(session, cache=cache)
        if cache:
            # Need to run generator to completion to actually find the
            # documents. Do this now rather than when 1st document requested
            for doc in self.generator:
                # Nothing to do, just populate df.locations or df.documents
                pass
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
        else:
            return self.docStream.fetch_document(idx)


for (k, v) in streamHash.items():
    SimpleDocumentFactory.register_stream(k, v)


class ComponentDocumentFactory(SimpleDocumentFactory):

    _possibleSettings = {
        'keepStart': {
            'docs': ("Should the factory include the starting element of the "
                     "selected span component in the output Document. "
                     "Default: yes"),
            'type': int,
            'options': "0|1"
        },
        'keepEnd': {
            'docs': ("Should the factory include the ending element of the "
                     "selected span component in the output Document. "
                     "Default: yes"),
            'type': int,
            'options': "0|1"
        },
    }

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

    def _handleLxmlConfigNode(self, session, node):
        # Source
        if node.tag in ["source", '{%s}source' % CONFIG_NS]:
            xpaths = []
            for child in node.iterchildren(tag=etree.Element):
                if child.tag in ["xpath", '{%s}xpath' % CONFIG_NS]:
                    # add XPath
                    ref = child.attrib.get(
                             'ref',
                             child.attrib.get('{%s}ref' % CONFIG_NS, '')
                    )
                    if ref:
                        xp = self.get_object(session, ref)
                    else:
                        xp = SimpleXPathProcessor(session, node, self)
                        xp._handleLxmlConfigNode(session, node)
                    self.sources.append(xp)

    def __init__(self, session, config, parent):
        self.sources = []
        SimpleDocumentFactory.__init__(self, session, config, parent)


class AccumulatingStream(BaseDocumentStream):
    def __init__(self, session, stream, format_, 
                 tagName=None, codec=None, factory=None):
        self.factory = factory
        self.format = format_
        self.tagName = tagName
        self.codec = codec
        # And call accumulate to record stream
        self.accumulate(session, stream, format_, tagName, codec, factory)

    def accumulate(self, session, stream, format_, 
                   tagName=None, codec=None, factory=None):
        raise NotImplementedError


class AccTransformerStream(AccumulatingStream):
    """Call a transformer on each input record and concatenate results.

    Transformer should return a string.
    """

    def __init__(self, session, stream, format_,
                 tagName=None, codec=None, factory=None):
        if not factory:
            msg = """\
Cannot build transformer stream without associated documentFactory"""
            raise ValueError(msg)
        self.transformer = factory.get_path(session, 
                                            'accumulatingTransformer', 
                                            None)
        if not self.transformer:
            msg = """\
DocumentFactory does not have 'accumulatingTransformer' path \
for AccTransformerStream"""
            raise ConfigFileException(msg)
        self.data = []

        # now init the AccStream after discovering txr
        AccumulatingStream.__init__(self, session, stream, format_, 
                                    tagName, codec, factory)

    def accumulate(self, session, stream, format_, 
                   tagName=None, codec=None, factory=None):
        # stream should be record instance
        doc = self.transformer.process_record(session, stream)
        self.data.append(doc.get_raw(session))

    def find_documents(self, session, cache=0):
        yield StringDocument(''.join(self.data))


class AccVectorTransformerStream(AccumulatingStream):
    """Accumulate data to be fed to DM, via a vector transformer."""

    def __init__(self, session, stream, format_, 
                 tagName=None, codec=None, factory=None):
        if not factory:
            msg = """\
Cannot build transformer stream without associated documentFactory"""
            raise ValueError(msg)
        self.transformer = factory.get_path(session, 
                                            'accumulatingTransformer', 
                                            None)
        if not self.transformer:
            msg = """\
DocumentFactory does not have 'accumulatingTransformer' path \
for AccTransformerStream"""
            raise ConfigFileException()
        self.classes = []
        self.vectors = []
        self.totalAttributes = 0
        # now init the AccStream after discovering txr
        AccumulatingStream.__init__(self, session, stream, format_, 
                                    tagName, codec, factory)

    def accumulate(self, session, stream, format_, 
                   tagName=None, codec=None, factory=None):
        # session should be record instance
        doc = self.transformer.process_record(session, stream)
        raw = doc.get_raw(session)
        if type(raw) == list:
                # multiple from proxVector (etc)
                for (l, v) in raw:
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


class AccumulatingDocumentFactory(SimpleDocumentFactory):
    """Accumulate data across multiple .load() calls to produce 1+  documents.

    Call load() repeatedly before fetching document(s)
    """

    _possiblePaths = {
        'accumulatingTransformer':
            {'docs': ("Transformer through which to pass records before "
                      "accumulating.")
            }
        }

    def __init__(self, session, config, parent):
        SimpleDocumentFactory.__init__(self, session, config, parent)

    def loadMany(self, session, data=None, cache=None, 
                 format_=None, tagName=None, codec=None):
        for item in data:
            self.load(session, item, cache, format_, tagName, codec)
        # Return self for workflows, mostly can ignore
        return self

    def load(self, session, data=None, cache=None, 
             format_=None, tagName=None, codec=None):

        self.loadSession = session
        if data is None:
            data = self.dataPath
        if format_ is None:
            format_ = self.format
        if cache is None:
            cache = self.cache
        if tagName is None:
            tagName = self.tagName
        if codec is None:
            codec = self.codec
        # Some laziness checking
        if not format_:
            if os.path.exists(data):
                if data[-4:] == '.zip':
                    format_ = 'zip'
                elif data[-4:] == '.tar':
                    format_ = 'tar'
                elif data[-4:] == '.xml':
                    format_ = 'xml'
                elif data[-5:] == '.marc':
                    format_ = 'marc'
                elif os.path.isdir(data):
                    format_ = 'dir'
            else:
                if data[:6] == "ftp://":
                    format_ = 'ftp'
                elif data[:6] == "srb://":
                    format_ = 'srb'
                elif data[:7] == "http://" or data[:8] == "https://":
                    format_ = "http"
                    if data.find('?') > -1:
                        # parse url and extract param names
                        bits = urlparse.urlsplit(data)
                        plist = [x.split('=')[0] for x in bits[3].split('&')]
                        if 'verb' in plist and 'metadataPrefix' in plist:
                            format_ = 'oai'
                        elif ('operation' in plist and 
                              'version' in plist and 
                              'query' in plist):
                            format_ = 'sru'
        if not self.docStream:
            cls = self.streamHash[format_]
            self.docStream = cls(session, data, format_, tagName, codec, self)
        else:
            self.docStream.accumulate(session, data, format_, 
                                      tagName, codec, self)
        self.previousIdx = -1
        self.cache = cache
        # Return self for workflows, mostly can ignore
        return self

    def get_document(self, session, n=-1):
        if self.previousIdx == -1:
            # call find docs for real
            self.generator = self.docStream.find_documents(session, 
                                                           cache=self.cache)
        return SimpleDocumentFactory.get_document(self, session, n)


AccumulatingDocumentFactory.register_stream('transformer', 
                                            AccTransformerStream)
AccumulatingDocumentFactory.register_stream('vectorTransformer', 
                                            AccVectorTransformerStream)


class ClusterExtractionDocumentFactory(AccumulatingDocumentFactory):
    """Load lots of records, cluster and return the cluster documents."""

    _possiblePaths = {
        'tempPath': {
            'docs': 
                """Path to a file where cluster data will be stored \
temporarily during subsequent load() calls."""
        }
    }

    def __init__(self, session, config, parent):
        self.keyMap = []
        self.maps = []
        AccumulatingDocumentFactory.__init__(self, session, config, parent)

        # Architecture object existance checking
        for m in range(len(self.maps)):
            if isinstance(self.maps[m][2], list):
                for t in range(len(self.maps[m][2])):
                    o = self.get_object(session, self.maps[m][2][t][1])
                    if (o is not None):
                        self.maps[m][2][t][1] = o
                    else:
                        msg = "Unknown object %s" % (self.maps[m][2][t][1])
                        raise ConfigFileException(msg)

        if isinstance(self.keyMap[2], list):
            for t in range(len(self.keyMap[2])):
                o = self.get_object(session, self.keyMap[2][t][1])
                if (o is not None):
                    self.keyMap[2][t][1] = o
                else:
                    msg = "Unknown object %s" % (self.keyMap[2][t][1])
                    raise ConfigFileException(msg)

        path = self.get_path(session, "tempPath")
        if (not os.path.isabs(path)):
            dfp = self.get_path(session, "defaultPath")
            path = os.path.join(dfp, path)

        self.fileHandle = codecs.open(path, "w", self.codec)
        self.tempPath = path

    def _handleConfigNode(self, session, node):
        if (node.localName == "cluster"):
            maps = []
            for child in node.childNodes:
                if (child.nodeType == elementType and 
                    child.localName == "map"):
                    t = child.getAttributeNS(None, 'type')
                    map_ = []
                    for xpchild in child.childNodes:
                        if (xpchild.nodeType == elementType and 
                            xpchild.localName == "xpath"):
                            map_.append(flattenTexts(xpchild))
                        elif (xpchild.nodeType == elementType and 
                              xpchild.localName == "process"):
                            # Turn xpath chain to workflow
                            ref = xpchild.getAttributeNS(None, 'ref')
                            if ref:
                                process = self.get_object(session, ref)
                            else:
                                try:
                                    xpchild.localName = 'workflow'
                                except:
                                    # 4suite dom sets read only
                                    cel = xpchild.ownerDocument.createElementNS
                                    newTop = cel(None, 'workflow')
                                    for kid in xpchild.childNodes:
                                        newTop.appendChild(kid)
                                    xpchild = newTop
                                process = CachingWorkflow(session, 
                                                          xpchild, 
                                                          self)
                                process._handleConfigNode(session, xpchild)
                            map_.append(process)
                    # XXX FIX ME 
                    # vxp = verifyXPaths([map_[0]])
                    vxp = [map_[0]]
                    if (len(map_) < 3):
                        # Default ExactExtractor
                        map_.append([['extractor', 'SimpleExtractor']])
                    if (t == u'key'):
                        self.keyMap = [vxp[0], map_[1], map_[2]]
                    else:
                        maps.append([vxp[0], map_[1], map_[2]])
            self.maps = maps

    def _handleLxmlConfigNode(self, session, node):
        if node.tag in ["cluster", '{%s}cluster' % CONFIG_NS]:
            maps = []
            for child in node.iterchildren(tag=etree.Element):
                if child.tag in ["map", '{%s}map' % CONFIG_NS]:
                    t = child.attrib.get(
                        'type',
                        child.attrib.get('{%s}type' % CONFIG_NS, '')
                    )  
                    map_ = []
                    for xpchild in child.iterchildren(tag=etree.Element):
                        if xpchild.tag in ["xpath", '{%s}xpath' % CONFIG_NS]:
                            map_.append(flattenTexts(xpchild).strip())
                        elif xpchild.tag in ["process",
                                             '{%s}process' % CONFIG_NS]:
                            # turn xpath chain to workflow
                            ref = xpchild.attrib.get(
                                'ref',
                                xpchild.attrib.get('{%s}ref' % CONFIG_NS, None)
                            ) 
                            if ref is not None:
                                process = self.get_object(session, ref)
                            else:
                                xpchild.tag = 'workflow'
                                process = CachingWorkflow(session, 
                                                          xpchild, 
                                                          self)
                                process._handleLxmlConfigNode(session, 
                                                              xpchild)
                            map_.append(process)

                    #vxp = [map_[0]]
                    if (len(map_) < 3):
                        # default ExactExtractor
                        map_.append([['extractor', 'SimpleExtractor']])
                    if (t == u'key'):
                        self.keyMap = [map_[0], map_[1], map_[2]]
                    else:
                        maps.append([map_[0], map_[1], map_[2]])
            self.maps = maps

    def load(self, session, data=None, cache=None, 
             format_=None, tagName=None, codec=None):
        # Extract cluster information, append to temp file
        # data must be a record
        p = self.permissionHandlers.get('info:srw/operation/2/cluster', None)
        if p:
            if not session.user:
                msg = ("Authenticated user required to cluster using "
                       "%s" % self.id)
                raise PermissionException(msg)
            okay = p.hasPermission(session, session.user)
            if not okay:
                msg = "Permission required to cluster using %s" % self.id
                raise PermissionException(msg)

        rec = data
        raw = rec.process_xpath(session, self.keyMap[0])
        keyData = self.keyMap[2].process(session, [raw])
        fieldData = []
        for map_ in self.maps:
            raw = rec.process_xpath(session, map_[0])
            fd = map_[2].process(session, [raw])
            for f in fd.keys():
                fieldData.append(u"%s\x00%s\x00" % (map_[1], f))
        d = u"".join(fieldData)
        for k in keyData.iterkeys():
            try:
                self.fileHandle.write(u"%s\x00%s\n" % (k, d))
                self.fileHandle.flush()
            except ValueError:
                self.fileHandle = codecs.open(self.tempPath, "w", self.codec)
                try:
                    self.fileHandle.write(u"%s\x00%s\n" % (k, d))
                    self.fileHandle.flush()
                except:
                    self.log_critical(session, 
                                      "%s failed to write: %r" % (self.id, k))
                    raise

    def get_document(self, session, n=-1):
        if self.previousIdx == -1:
            self.fileHandle.close()
            # now store and call generator
            ds = ClusterDocumentStream(session, self.tempPath, 'cluster', 
                                       'cluster', self.codec, self)
            self.docStream = ds

        return AccumulatingDocumentFactory.get_document(self, session, n)
