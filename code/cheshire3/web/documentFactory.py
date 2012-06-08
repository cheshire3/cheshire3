
from cheshire3.documentFactory import BaseDocumentStream, AccumulatingStream
from cheshire3.documentFactory import MultipleDocumentStream, XmlDocumentStream, TarDocumentStream, ZipDocumentStream, MarcDocumentStream
from cheshire3.document import StringDocument
from cheshire3.bootstrap import BSParser
from cheshire3.utils import elementType, getFirstData, flattenTexts

try:
    from ZSI.client import Binding
    from PyZ3950 import zoom
    import SRW
except:
    pass

import socket
import re, os, cStringIO
import mimetypes,  urllib, urlparse, urllib2
from ftplib import FTP

socket.setdefaulttimeout(30)


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

        if 'preferredRecordSyntax' in args:
            conn.preferredRecordSyntax = args['preferredRecordSyntax']
        else:
            conn.preferredRecordSyntax = 'USMARC'
        if 'elementSetName' in args:
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
                mt = mimetypes.guess_type(self.resultSet.preferredRecordSyntax)[0]
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
        if mimetype[0] is None:
            # get mimetype from stream
            s = self._fetchStream(item)
            mimetype = (s.mimetype, None)
        else:
            s = None

        if (mimetype[0] in ['text/sgml', 'text/xml', 'application/sgml', 'application/xml']):
            trip = ('stream', XmlDocumentStream, 'xml')
        elif (mimetype[0] == 'application/x-tar'):
            trip = ('stream', TarDocumentStream, ftype)
        elif (mimetype[0] == 'application/zip'):
            trip = ('stream', ZipDocumentStream, 'zip')
        elif (mimetype[0] == 'application/marc'):
            trip = ('stream', MarcDocumentStream, 'marc')
        else:
            trip = ('document', None, mimetype[0])

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
        
        if (not 'query' in args):
            raise ValueError("SruDocumentStream data requires a query param")
        if (not 'version' in args):
            args['version'] = '1.1'
        if (not 'maximumRecords' in args):
            args['maximumRecords'] = 25
        if (not 'recordPacking' in args):
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
        """Use universal feed parser to import rss, atom, etc."""

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
    

class AccHttpDocumentStream(AccumulatingStream, HttpDocumentStream):
    """AccumulatingDocumentFactory friendly version of HttpDocumentStream.
    
    Accumulate documents from a number of URLs (e.g. when web-crawling)."""
    
    urls = []
    
    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
        self.urls = []
        AccumulatingStream.__init__(self, session, stream, format, tagName=tagName, codec=codec, factory=factory)
    
    def accumulate(self, session, stream, format, tagName=None, codec=None, factory=None ):
        self.urls.append(stream)
        
    def find_documents(self, session, cache=0):
        for f in self._processFiles(session, self.urls, cache):
            yield f
    
    

streamHash = {
    "oai" : OaiDocumentStream,
    "sru" : SruDocumentStream,
    "srw" : SrwDocumentStream,
    "opensearch" : OpensearchDocumentStream,
    "z3950" : Z3950DocumentStream,
    "ftp" : FtpDocumentStream,
    "http" : HttpDocumentStream,
    "rss" : SyndicationDocumentStream
}

accStreamHash = {
     "http": AccHttpDocumentStream
}
