
from cheshire3.selector import SimpleSelector
from cheshire3.graph.record import GraphRecord

class SparqlSelector(SimpleSelector):

    def __init__(self, session, config, parent):
        SimpleSelector.__init__(self, session, config, parent)
        for src in self.sources:
            print src

    def process_record(self, session, record):
        if not isinstance(record, GraphRecord):
            raise SomeException("Can only process GraphRecords")
        else:
            g = record.graph
            vals = []
            for src in self.sources:
                for xp in src:
                    # this will be a SparqlQueryResult object
                    res = g.query(xp['string'], initNs=xp['maps'])
                    print len(res)
                    vals.extend(res.selected)
            return vals
    

