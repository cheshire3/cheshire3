
# We need some objects that don't need configuring in order to bootstrap
# Eg:  Need a parser to parser the configuration files for parsers!
# (Also to avoid import errors in Python)

from xml.dom.minidom import parseString

class BootstrapParser:

    def process_document(self, session, doc):
        xml = doc.get_raw()
        dom = parseString(xml)
        rec = BootstrapRecord(dom, xml)
        return rec

class BootstrapRecord:
    xml = ""
    dom = None


    def __init__(self, dom, xml):
        self.dom = dom
        self.xml = xml

    def get_dom(self):
        return self.dom

    def get_xml(self):
        return self.xml

    def get_sax(self):
        raise(NotImplementedError)

class BootstrapDocument:
    handle = None
    txt = ""

    def __init__(self, fileHandle):
        # This means we have hanging file handles, but less memory usage...
        self.handle = fileHandle

    def get_raw(self):
        if (self.txt):
            return self.txt
        elif (self.handle <> None):
            self.txt =  self.handle.read()
            self.handle.close()
            return self.txt
        else:
            return None

# admin that can do anything
class BootstrapUser:
    username = "admin"
    password = ""
    flags = {'' : 'c3r:administrator'}

    def has_flag(self, session, flag, object=""):
        return True
    
class BootstrapSession:
    user = None
    inHandler = None
    outHandler = None
    def __init__(self):
        self.user = BootstrapUser()
        
BSParser = BootstrapParser()
BSSession = BootstrapSession()
