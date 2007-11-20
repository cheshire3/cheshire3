
from configParser import C3Object
from baseObjects import Parser
from xml.dom.minidom import parseString as domParseString
from record import SaxRecord, MinidomRecord, FtDomRecord, SaxContentHandler, LxmlRecord

from xml.sax import ContentHandler, make_parser, parseString as saxParseString, ErrorHandler, InputSource as SaxInput
from xml.sax.saxutils import escape


from utils import flattenTexts, elementType
import re
import cStringIO, StringIO


# utility function to update data on record from document
    

class BaseParser(Parser):
    def _copyData(self, doc, rec):
        rec.filename = doc.filename
        rec.tagName = doc.tagName
        rec.processHistory = doc.processHistory
        rec.processHistory.append(self.id)
        if doc.documentStore:
            rec.parent = ('document', doc.documentStore, doc.id)
        elif doc.parent:
            rec.parent = doc.parent


class MinidomParser(BaseParser):
    """ Use default Python Minidom implementation to parse document """

    def process_document(self, session, doc):
        xml = doc.get_raw(session)
        dom = domParseString(xml)
        rec = MinidomRecord(dom, xml)
        self._copyData(doc, rec)
        return rec


class SaxParser(BaseParser):
    """ Default SAX based parser. Creates SaxRecord """

    _possibleSettings = {'namespaces' : {'docs' : "Enable namespace processing in SAX"},
                         'stripWhitespace' : {'docs' : "Strip additional whitespace when processing."},
			 'attrHash' : {'docs' : "Tag/Attribute combinations to include in hash."}
			 }

    def __init__(self, session, config, parent):
        Parser.__init__(self, session, config, parent)
        self.parser = make_parser()
        self.errorHandler = ErrorHandler()
        self.parser.setErrorHandler(self.errorHandler)
        self.inputSource = SaxInput()
        ch = SaxContentHandler()
        self.contentHandler  = ch
        self.parser.setContentHandler(ch)
        self.keepError = 1

        if (self.get_setting(session, 'namespaces')):
            self.parser.setFeature('http://xml.org/sax/features/namespaces', 1)
        p = self.get_setting(session, 'attrHash')
        if (p):
            l = p.split()
            for i in l:
                (a,b) = i.split("@")
                try:
                    ch.hashAttributesNames[a].append(b)
                except:
                    ch.hashAttributesNames[a] = [b]
        if self.get_setting(session, 'stripWhitespace'):
            ch.stripWS = 1

    def process_document(self, session, doc):

        xml = doc.get_raw(session)        
        self.inputSource.setByteStream(cStringIO.StringIO(xml))        
        ch = self.contentHandler
        ch.reinit()
        try:
            self.parser.parse(self.inputSource)
        except:
            # Splat.  Reset self and reraise
            if self.keepError:
                # Work out path
                path = []
                for l in ch.pathLines:
                    line = ch.currentText[l]
                    elemName = line[2:line.index('{')-1]
                    path.append("%s[@SAXID='%s']" % (elemName, l))
                self.errorPath = '/'.join(path)
            else:
                ch.reinit()
                
            raise        
        rec = SaxRecord(ch.currentText, xml, wordCount=ch.recordWordCount)
        rec.elementHash = ch.elementHash
        rec.byteCount = len(xml)
        self._copyData(doc, rec)
        ch.reinit()
        return rec

try:
    from lxml import etree

    class LxmlParser(BaseParser):
        """ lxml based Parser.  Creates LxmlRecords """
        def process_document(self, session, doc):
            # input must be stream
            data = doc.get_raw(session)
            try:
                et = etree.XML(data)
            except AssertionError:
                data = data.decode('utf8')
                et = etree.XML(data)
            rec = LxmlRecord(et)
            rec.byteCount = len(data)
            self._copyData(doc, rec)
            return rec

    class LxmlSchemaParser(Parser):
        pass
    class LxmlRelaxNGParser(Parser):
        pass

    class LxmlHtmlParser(BaseParser):
        """ lxml based parser for HTML documents """

        def __init__(self, session, config, parent):
            BaseParser.__init__(self, session ,config, parent)
            self.parser = etree.HTMLParser()

        def process_document(self, session, doc):
            data = doc.get_raw(session)
            et = etree.parse(StringIO.StringIO(data), self.parser)
            rec = LxmlRecord(et)
            rec.byteCount = len(data)
            self._copyData(doc, rec)
            return rec
    
except:
    # Define empty classes
    class LxmlParser(Parser):
	pass


from Ft.Xml import Sax, InputSource as FtInput
from Ft.Xml.Domlette import NonvalidatingReaderBase

class FtParser(BaseParser, NonvalidatingReaderBase):
    """ 4Suite based Parser.  Creates FtDomRecords """
    def __init__(self, session, config, parent):
        Parser.__init__(self, session, config, parent)
        NonvalidatingReaderBase.__init__(self)

    def process_document(self, session, doc):
        data = doc.get_raw(session)
        dom = self.parseString(data, 'urn:foo')
        rec = FtDomRecord(dom, data)
        rec.byteCount = len(data)
        self._copyData(doc, rec)
        return rec

class FtSaxParser(BaseParser):
    """ 4Suite SAX based Parser.  Creates SaxRecords """

    _possibleSettings = {'attrHash' : {'docs' : "list of attributes to include in the hash. element@attr, space separated"}
                         , 'stripWhitespace' : {'docs' : "Should the parser strip extra whitespace."}}

    def __init__(self, session, config, parent):
        Parser.__init__(self, session, config, parent)
        self.parser = Sax.CreateParser()
        ch = SaxContentHandler()
        self.contentHandler  = ch
        self.parser.setContentHandler(ch)
        p = self.get_setting(session, 'attrHash')
        if (p):
            l = p.split()
            for i in l:
                (a,b) = i.split("@")
                try:
                    ch.hashAttributesNames[a].append(b)
                except:
                    ch.hashAttributesNames[a] = [b]
        if self.get_setting(session, 'stripWhitespace'):
            ch.stripWS = 1
        

    def process_document(self, session, doc):

        xml = doc.get_raw(session)
        src = FtInput.InputSource(StringIO.StringIO(xml))        
        ch = self.contentHandler
        ch.reinit()
        try:
            self.parser.parse(src)
        except:
            # Splat.  Reset self and reraise
            ch.reinit()
            raise
            
        rec = SaxRecord(ch.currentText, xml, recordSize=ch.recordSize)
        rec.elementHash = ch.elementHash
        rec.byteCount = len(xml)
        self._copyData(doc, rec)
        return rec
    

class PassThroughParser(BaseParser):
    """ Copy the data from a document (eg list of sax events or a dom tree) into an appropriate record object """

    def process_document(self, session, doc):
        # Simply copy data into a record of appropriate type
        data = doc.get_raw(session)
        if (typeof(data) == types.ListType):
            rec = SaxRecord(data)
        else:
            rec = DomRecord(data)
        self._copyData(doc, rec)
        return rec


# Copy
from record import MarcRecord
class MarcParser(BaseParser):
    """ Creates MarcRecords which fake the Record API for Marc """
    def process_document(self, session, doc):
        return MarcRecord(doc)





from utils import nonTextToken
# Semi-Worthless
class XmlRecordStoreParser(BaseParser):
    """ Metadata wrapping Parser for RecordStores.  Not recommended """

    # We take in stuff and return a Record, that makes us a Parser.
    # Retrieve metadata and sax list from XML structure

    _possibleSettings = {'saxOnly' : {'docs' : "Should the parser return only the SAX and not the metadata"}}


    def __init__(self, session, config, parent):
        Parser.__init__(self, session, config, parent)
        self.saxre = re.compile("<c3:saxEvents>(.+)</c3:saxEvents>", re.S)            

    def process_document(self, session, doc):
        # Take xml wrapper and convert onto object
        # Strip out SAX events first

        data = doc.get_raw(session)

        # Strip out sax to list
        match = self.saxre.search(data)
        elemHash = {}
        if match:
            sax = match.groups(1)[0]
            sax = unicode(sax, 'utf-8').split(nonTextToken)
	    # Now check if last is an element hash                
	    if sax[-1][0] == "9":
                elemHash = eval(sax[-1][2:])
                sax = sax[:-1]
        else:
            sax = []
        
        # Build base Record
        rec = SaxRecord(sax)
        rec.elementHash = elemHash

        # Maybe quit
        if (self.get_setting(session, 'saxOnly')):
            return rec

        # Otherwise parse the metadata
        data = self.saxre.sub("", data)
        dom = domParseString(data)
        for c in dom.childNodes[0].childNodes:
            if c.nodeType == elementType:
                if (c.localName == "id"):
                    rec.id = flattenTexts(c)
                    if (rec.id.isdigit()):
                        rec.id = long(rec.id)
                elif (c.localName == "baseUri"):
                    rec.baseUri = flattenTexts(c)
                elif (c.localName == "parent"):
                    # triple:  type, store, id
                    # store must be string here, as we don't necessarily have access to all objects
                    type = store = ""
                    id = -1
                    for c2 in c.childNodes:
                        if (c2.nodeType == elementType):
                            if (c2.localName == "type"):
                                type = flattenTexts(c2)
                            elif (c2.localName == "store"):
                                store = flattenTexts(c2)
                            elif (c2.localName == "id"):
                                id = long(flattenTexts(c2))
                    rec.parent = (type, store, id)
                elif (c.localName == "processHistory"):
                    foo = []
                    for c2 in c.childNodes:
                        if (c2.nodeType == elementType and c2.localName == 'object'):
                            foo.append(flattenTexts(c2))
                    rec.processHistory = foo
                elif (c.localName == "tagName"):
                    rec.tagName = flattenTexts(c)
                elif (c.localName == "size"):
                    rec.wordCount = long(flattenTexts(c))
                elif (c.localName == "technicalRights"):
                    for c2 in c.childNodes:
                        if (c2.nodeType == elementType):
                            entry = (flattenTexts(c2), c2.localName, c2.getAttribute('role'))
                            rec.rights.append(entry)
                elif (c.localName == "history"):
                    for c2 in c.childNodes:
                        if (c2.nodeType == elementType):
                            # A modification
                            entry = ['', '', c2.getAttribute('type')]
                            for c3 in c2.childNodes:
                                if (c3.nodeType == elementType):
                                    if (c3.localName == "agent"):
                                        entry[0] = flattenTexts(c3)
                                    elif (c3.localName == "date"):
                                        entry[1] = flattenTexts(c3)
                            rec.history.append(entry)

        return rec
