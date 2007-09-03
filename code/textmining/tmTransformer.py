
import os, re
from utils import getFirstData, elementType, verifyXPaths

from TsujiiC3 import TsujiiObject
from baseObjects import Transformer
from document import StringDocument

class PosTransformer(Transformer):
    pass

class TsujiiTextPosTransformer(PosTransformer, TsujiiObject):

    def __init__(self, session, node, parent):
        PosTransformer.__init__(self, session, node, parent)
        TsujiiObject.__init__(self, session, node, parent)

    def process_record(self, session, rec):
        """ Oooooh.  Try to step through all text nodes and tag? """
        pass


class TsujiiXPathTransformer(PosTransformer, TsujiiObject):

    # <xpath type="copy"> ...
    # <xpath type="tag"> ...
    copyElems = []
    tagElems = []

    def _handleConfigNode(self, session, node):
        # Source
        if (node.localName == "xpath"):
            xpath = getFirstData(node)
            maps = {}
            for a in node.attributes.keys():
                if (a[:6] == "xmlns:"):
                    pref = a[6:]
                    uri = node.getAttribute(a)
                    maps[pref] = uri
                elif a == "type":
                    tc = node.getAttribute(a)
            cxp = verifyXPaths([xpath])
            if tc == 'copy':
                self.copyElems.append([cxp[0], maps])
            else:
                self.tagElems.append([cxp[0], maps])

    def __init__(self, session, node, parent):
        self.copyElems = []
        self.tagElems = []
        PosTransformer.__init__(self, session, node, parent)
        TsujiiObject.__init__(self, session, node, parent)

    def process_record(self, session, rec):
        doc = []
        for c in self.copyElems:
            res = rec.process_xpath(c[0], c[1])
            for match in res:
                txt = rec.get_xml(match)
                doc.append(txt)
        for t in self.tagElems:
            res = rec.process_xpath(t[0], t[1])
            for match in res:
                # Process all text nodes together
                totag = []
                for event in match:
                    if event[0] == '3':
                        totag.append(event[1:])
                tagtxt = ''.join(totag)
                tagged = self.tag(session, tagtxt)
                tagged = ''.join(tagged)
                if match[0][0] != '3':
                    (name, attrhash) = rec._convert_elem(match[0])
                    attrs = []
                    for a in attrhash:
                        attrs.append('%s="%s"' % (a, attribs[a]))
                    attribtxt = ' '.join(attrs)
                    if (attribtxt):
                        attribtxt = " " + attribtxt
                    txt = "<%s%s>%s</%s>" % (name, attribtxt, tagged, name)
                else:
                    txt = "<text>%s</text>" % (tagged)
                doc.append(txt)
        doctxt = "<record>%s</record>" % '\n'.join(doc)
        strdoc =  StringDocument(doctxt, self.id, rec.processHistory, 'text/xml')
        return strdoc

