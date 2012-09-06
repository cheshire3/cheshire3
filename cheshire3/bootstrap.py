
# We need some objects that don't need configuring in order to bootstrap
# E.g.: Need a parser to parse the configuration files for parsers!
# (Also to avoid import errors in Python)

from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
from lxml import etree

from cheshire3.exceptions import XMLSyntaxError

class BootstrapParser:

    def process_document(self, session, doc):
        xml = doc.get_raw(session)
        try:
            dom = parseString(xml)
        except ExpatError as e:
            raise XMLSyntaxError(e.message)
        rec = BootstrapRecord(dom, xml)
        return rec


class BootstrapLxmlParser:

    def process_document(self, session, doc):
        data = doc.get_raw(session)
        try:
            try:
                et = etree.XML(data)
            except AssertionError:
                data = data.decode('utf8')
                et = etree.XML(data)
        except etree.XMLSyntaxError as e:
            raise XMLSyntaxError(e.message)
        return BootstrapRecord(et, data)


class BootstrapRecord:

    xml = ""
    dom = None

    def __init__(self, dom, xml):
        self.dom = dom
        self.xml = xml

    def get_dom(self, session):
        return self.dom

    def get_xml(self, session):
        return self.xml

    def get_sax(self, session):
        raise(NotImplementedError)


class BootstrapDocument:

    handle = None
    txt = ""

    def __init__(self, fileHandle):
        # This means we have hanging file handles, but less memory usage...
        self.handle = fileHandle

    def get_raw(self, session):
        if (self.txt):
            return self.txt
        elif (self.handle is not None):
            self.txt = self.handle.read()
            self.handle.close()
            return self.txt
        else:
            return None


class BootstrapUser:
    """A Bootstrap admin User that can do anything."""
    username = "admin"
    password = ""
    flags = {'': 'c3r:administrator'}

    def has_flag(self, session, flag, object=""):
        return True


class BootstrapSession:

    user = None
    inHandler = None
    outHandler = None

    def __init__(self):
        self.user = BootstrapUser()


# Initialize some bootstrap objects.
BSParser = BootstrapParser()
BSLxmlParser = BootstrapLxmlParser()
BSSession = BootstrapSession()
