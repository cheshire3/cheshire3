
from cheshire3.transformer import Transformer
from cheshire3.graph.record import GraphRecord
from cheshire3.document import StringDocument


#load json extensions to rdflib
from rdflib import plugin, syntax
plugin.register('json', syntax.serializers.Serializer, 'cheshire3.graph.JsonSerializer', 'JsonSerializer')
plugin.register('pretty-json', syntax.serializers.Serializer, 'cheshire3.graph.JsonSerializer', 'PrettyJsonSerializer')

class RdfXmlTransformer(Transformer):
    # take GraphRecord and serialize to doc

    _possibleSettings = {'format' : {'docs' : 'format to serialize to, default to simple xml.'}}

    def process_record(self, session, rec):
        if isinstance(rec, GraphRecord):
            fmt = self.get_setting(session, 'format', 'xml')
            data = rec.graph.serialize(format=fmt)
            return StringDocument(data)
        else:
            raise NotImplementedError("Can only transform GraphRecords")
