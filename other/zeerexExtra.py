
from baseObjects import Transformer
from record import s2xhandler as s2x
from document import StringDocument

class ZeerexTransformer(Transformer):

    def initState(self):
        self.setHash = {}
        self.schemaHash = {}
        self.closeElems = []
        self.mapToSchema = 0
        self.mapToSet = 0
        self.namespace = "http://explain.z3950.org/dtd/2.0/"

    def startPrefixMapping(self, pref, uri):
        pass

    def startElementNS(self, name, qname, attribs):
        (ns, name) = name
        if (ns == self.namespace):
            # Strip non ZeeRex attrs
            attrs = {}
            for a in attribs:
                if (not a[0] or a[0] == self.namespace):
                    attrs[a[1]] = attribs[a]
            self.startElement(name, attrs)

    def endElementNS(self, name, qname):
        (ns, name) = name
        if (ns == self.namespace):
            self.endElement(name)

    def startElement(self, name, attribs):
        idx = name.find(":")
        if (idx > -1):
            name = name[idx+1:]

        if (name == "set"):
            # Extract name/identifer
            if (attribs.has_key('name') and attribs.has_key('identifier')):
                self.setHash[attribs['name']] = attribs['identifier']
            s2x.startElement(name, attribs)
        elif (name =="schema"):
            if (attribs.has_key('name') and attribs.has_key('identifier')):
                self.schemaHash[attribs['name']] = attribs['identifier']
            s2x.startElement(name, attribs)
        elif (name == "name"):
            # Extract set, rewrite.
            s2x.startElement("name", {})
            if (attribs.has_key('set') and self.setHash.has_key(attribs['set'])):
                s2x.startElement("set", {})
                s2x.characters(self.setHash[attribs['set']])
                s2x.endElement("set")
            s2x.startElement("value",{})
            self.closeElems.append("value")
        elif (name == "attr"):
            # Extract set and type, rewrite
            # default set is Bib1: 1.2.840.10003.3.1
            s2x.startElement("attr", {})
            s2x.startElement("set",{})
            if (attribs.has_key('set')):
                s2x.characters(attribs['set'])
            else:
                s2x.characters("1.2.840.10003.3.1")
            s2x.endElement("set")
            s2x.startElement("type",{})
            s2x.characters(attribs['type'])
            s2x.endElement("type")
            s2x.startElement("value",{})
            self.closeElems.append("value")
        elif (name in ['supports', 'default']):
            type = attribs['type']
            if (type in ['sortSchema', 'retrieveSchema']):
                self.mapToSchema = 1
            elif (type in ["contextSet",'index','relation','relationModifier','booleanModifier']):
                self.mapToSet = 1 
            s2x.startElement(name, attribs)
        else:
            s2x.startElement(name, attribs)
            
    def endElement(self, name):
        idx = name.find(":")
        if (idx > -1):
            name = name[idx+1:]
        while (self.closeElems):
            s2x.endElement(self.closeElems.pop())
        s2x.endElement(name)

    def characters(self, text, foo, bar):
        if (self.mapToSchema):
            if (self.schemaHash.has_key(text.strip())):
                s2x.characters(self.schemaHash[text.strip()])
            self.mapToSchema = 0
        elif (self.mapToSet):
            # <supports><set>foo</set><val>bar</val></supports>
            idx = text.find('.')
            if (idx > -1):
                (set, text) = text.split(".", 1)
                if (self.setHash.has_key(set.strip())):
                    s2x.startElement("set", {})
                    s2x.characters(self.setHash[set.strip()])
                    s2x.endElement("set")
            s2x.startElement("value", {})
            s2x.characters(text)
            s2x.endElement("value")            
            self.mapToSet = 0
        else:
            s2x.characters(text)
        
    def process_record(self, session, rec):
        # turn all occurences of context set abbreviations
        # into the expanded form
        # Turn some attributes into elements

        self.initState()
        s2x.initState()
        try:
            rec.saxify(self)
        except:
            # XXX Better error for couldn't transform document
            raise 
        return StringDocument(s2x.get_raw(), self.id)
