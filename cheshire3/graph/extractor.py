
from cheshire3.extractor import SimpleExtractor
from rdflib import Literal, BNode, URIRef

class RdfExtractor(SimpleExtractor):

    _possibleSettings = {'joinCharacter' : {'docs' : 'Character to join multiple nodes in a single result with'}}

    def __init__(self, session, config, parent):
        SimpleExtractor.__init__(self, session, config, parent)
        self.jchr = self.get_setting(session, 'joinCharacter', u' ')

    def process_node(self, session, data):
        # could be a tuple of N results

        if not isinstance(data, tuple):
            data = [data]

        vallst = []
        for node in data:
            if isinstance(node, BNode):
                val = u'bnode:' + unicode(node)
            else:
                val = unicode(node)
            val = val.replace('\n', ' ')
            val = val.replace('\r', ' ')
            if self.strip:
                val = val.strip()
            vallst.append(val)
        val = self.jchr.join(vallst)

        return {val: {'text' : val, 'occurences' : 1, 'proxLoc' : [-1]}}

