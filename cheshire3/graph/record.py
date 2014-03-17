from lxml import etree

from cheshire3.baseObjects import Record
from cheshire3.record import LxmlRecord


class GraphRecord(LxmlRecord):

    graph = None

    def __init__(self, data, xml="", docId=None, wordCount=0, byteCount=0):
        self.dom = None
        self.graph = data
        self.xml = xml
        self.id = docId
        self.parent = ('','',-1)
        self.context = None
        if wordCount:
            self.wordCount = wordCount
        self.byteCount = byteCount

    def process_sparql(self, session, q, map={}):
        return self.graph.query(q, initNs=map)

    def get_graph(self, session):
        return self.graph

    def process_xpath(self, session, q, map={}):
        if self.dom is None:
            self.get_xml(session)
        try:
            return LxmlRecord.process_xpath(self, session, q, map)
        except etree.XPathEvalError:
            return self.process_sparql(session, q, map)

    def get_xml(self, session):
        if self.xml:
            data = self.xml
        else:
            data = self.graph.serialize(format='pretty-xml')
        if not self.dom:
            try:
                et = etree.XML(data)
            except AssertionError:
                data = data.decode('utf8')
                et = etree.XML(data)            
            self.dom = et
        return data

    def get_dom(self, session):
        if not self.dom:
            self.get_xml(session)
        return self.dom


class OreGraphRecord(GraphRecord):
    aggregation = None
