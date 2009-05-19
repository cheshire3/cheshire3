
from cheshire3.selector import SimpleSelector
from cheshire3.graph.record import GraphRecord

class SparqlSelector(SimpleSelector):

    def __init__(self, session, config, parent):
        SimpleSelector.__init__(self, session, config, parent)

    def process_record(self, session, record):
        if not isinstance(record, GraphRecord):
            raise SomeException("Can only process GraphRecords")
        else:
            vals = []
            for src in self.sources:
                for xp in src:
                    # this will be a SparqlQueryResult object
                    mv = record.process_sparql(session, xp['string'], xp['maps'])
                    vals.extend(mv.selected)
            return vals
    

