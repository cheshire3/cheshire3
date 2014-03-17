
from cheshire3.document import StringDocument
from cheshire3.exceptions import MissingDependencyException
from cheshire3.transformer import Transformer

from cheshire3.graph.record import GraphRecord

try:
    from rdflib import plugin, syntax
except ImportError:

    class RdfXmlTransformer(Transformer):

        def __init__(self, session, config, parent=None):
            Transformer.__init__(self, session, config, parent=parent)
            raise MissingDependencyException(self.objectType, "rdflib")

else:    

    class RdfXmlTransformer(Transformer):
        """Transformer to take GraphRecord and serialize to a Document."""

        _possibleSettings = {
            'format': {
                'docs': 'format to serialize to, default to simple xml.'
            }
        }

        def process_record(self, session, rec):
            if isinstance(rec, GraphRecord):
                fmt = self.get_setting(session, 'format', 'xml')
                data = rec.graph.serialize(format=fmt)
                return StringDocument(data)
            else:
                raise NotImplementedError("Can only transform GraphRecords")


    # Load json extensions to rdflib
    plugin.register('json',
                    syntax.serializers.Serializer,
                    'cheshire3.graph.JsonSerializer',
                    'JsonSerializer')
    plugin.register('pretty-json',
                    syntax.serializers.Serializer,
                    'cheshire3.graph.JsonSerializer',
                    'PrettyJsonSerializer')
