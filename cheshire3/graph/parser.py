
from cheshire3.parser import BaseParser
from cheshire3.graph.record import GraphRecord, OreGraphRecord

from rdflib import StringInputSource, URIRef
from rdflib import ConjunctiveGraph as Graph
from pyRdfa import parseRDFa, Options
from xml.dom import minidom
import StringIO


class RdfGraphParser(BaseParser):

    _possibleSettings = {'format' : {'docs' : 'Format to parse. One of xml, trix, nt, n3, rdfa'}}

    def process_document(self, session, doc):
        fmt = self.get_setting(session, 'format', '')
        data = doc.get_raw(session)
        graph = Graph()
        inpt = StringInputSource(data)
        if fmt:
            graph.parse(inpt, fmt)
        else:
            graph.parse(inpt)
        rec = GraphRecord(graph)
        return rec

try:
    from foresite import RdfLibParser
except ImportError:
    class OreRdfGraphParser(RdfGraphParser):
        pass
else:
    class OreRdfGraphParser(RdfGraphParser):
        
        def __init__(self, session, config, parent=None):
            super(OreRdfGraphParser, self).__init__(session, config, parent)
            self.fsParser = RdfLibParser()
        
        def process_document(self, session, doc):
            fmt = self.get_setting(session, 'format', '')
            data = doc.get_raw(session)
            graph = Graph()
            inpt = StringInputSource(data)
            if fmt:
                graph.parse(inpt, fmt)
            else:
                graph.parse(inpt)
            rec = OreGraphRecord(graph)
            # drop into foresite to turn graph into ORE objects
            rem = self.fsParser.process_graph(graph)
            rec.aggregation = rem.aggregation
            return rec
    

class RdfaParser(BaseParser):
    options = None

    def __init__(self, session, config, parent):
        BaseParser.__init__(self, session, config, parent)
        rdfaOptions = Options(warnings=False)
        rdfaOptions.warning_graph = None
        self.options = rdfaOptions

    def process_document(self, session, doc):
        data = doc.get_raw(session)
        uri = "not-sure-what-to-do-here"
        root = minidom.parse(StringIO.StringIO(data))
        graph = parseRDFa(root, uri, options=self.options)
        rec = GraphRecord(graph)
        return rec
        
