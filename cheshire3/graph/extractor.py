
from cheshire3.extractor import SimpleExtractor
from cheshire3.exceptions import MissingDependencyException

try:
    from rdflib import Literal, BNode, URIRef
except ImportError:

    class RdfExtractor(SimpleExtractor):
        
        def __init__(self, session, config, parent):
            SimpleExtractor.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType, 'rdflib')
        
else:
    
    class RdfExtractor(SimpleExtractor):
    
        _possibleSettings = {'joinCharacter' : {'docs' : 'Character to join multiple nodes in a single result with'}}
    
        def __init__(self, session, config, parent):
            SimpleExtractor.__init__(self, session, config, parent)
            self.jchr = self.get_setting(session, 'joinCharacter', u'  ')
    
        def process_node(self, session, data):
            # could be a tuple of N results
    
            if type(data) in [Literal, BNode, URIRef]:
                data = [data]
    
            vallst = []
            for node in data:
                if isinstance(node, tuple):
                    for t in tuple:
                        val = self.process_value(session, t)
                        vallst.append(val)
                else:
                    vallst.append(self.process_value(session, node))
            val = self.jchr.join(vallst)
            return {val: {'text' : val, 'occurences' : 1, 'proxLoc' : [-1]}}
    
        def process_value(self, session, node):
            if isinstance(node, BNode):
                val = u'bnode:' + unicode(node)        
            else:
                val = unicode(node)
    
            val = val.replace('\n', ' ')
            val = val.replace('\r', ' ')
            if self.strip:
                val = val.strip()
            return val
