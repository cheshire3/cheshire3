
from cheshire3.selector import SimpleSelector
from cheshire3.exceptions import C3ObjectTypeError

from cheshire3.graph.record import GraphRecord


class SparqlSelector(SimpleSelector):

    def __init__(self, session, config, parent):
        SimpleSelector.__init__(self, session, config, parent)

    def process_record(self, session, record):
        if not isinstance(record, GraphRecord):
            raise C3ObjectTypeError("Object of type {0.objectType} can only "
                                    "process GraphRecords; "
                                    "{1.__class__.__name__} supplied"
                                    "".format(self, record)
                                    )
        else:
            vals = []
            for src in self.sources:
                for xp in src:
                    # this will be a SparqlQueryResult object
                    mv = record.process_sparql(session, xp['string'], xp['maps'])
                    vals.append(mv.selected)
            return vals
