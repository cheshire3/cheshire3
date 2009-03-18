
from cheshire3.record import LxmlRecord
from cheshire3.baseObjects import Record

class GraphRecord(Record):
    graph = None

    def __init__(self, session, data, xml="", docId=None, wordCount=0, byteCount=0):
        self.graph = data
        self.xml = xml
        self.id = docId
        self.parent = ('','',-1)
        self.context = None

    def get_graph(self, session):
        return self.graph

    
