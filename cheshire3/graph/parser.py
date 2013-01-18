
from xml.dom import minidom
import StringIO

from cheshire3.parser import BaseParser
from cheshire3.exceptions import MissingDependencyException
from cheshire3.graph.record import GraphRecord, OreGraphRecord

try:
    from rdflib import StringInputSource, URIRef, ConjunctiveGraph as Graph
except ImportError:
    
    class RdfGraphParser(BaseParser):
        
        def __init__(self, session, config, parent):
            BaseParser.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType,
                                             'rdflib')
    
else:

    class RdfGraphParser(BaseParser):
    
        _possibleSettings = {
            'format': {
                'docs': 'Format to parse. One of xml, trix, nt, n3, rdfa'
            }
        }
    
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
    from pyRdfa import parseRDFa, Options
except ImportError:
    
    class RdfaParser(BaseParser):
        
        def __init__(self, session, config, parent=None):
            BaseParser.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType,
                                             'pyRdfa')

else:
    
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


try:
    from foresite import RdfLibParser
except ImportError:
    
    class OreRdfGraphParser(RdfGraphParser):
        
        def __init__(self, session, config, parent=None):
            try:
                # For more accurate error message, check if rdflib also missing 
                super(OreRdfGraphParser, self).__init__(session,
                                                        config,
                                                        parent)
            except MissingDependencyException as e:
                raise MissingDependencyException(self.__class__.__name__,
                                                 ['rdflib', 'foresite'])
            else:
                raise MissingDependencyException(self.objectType,
                                                 'foresite')
    
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
