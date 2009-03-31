
import lucene

class SimpleTokenStream(lucene.PythonTokenStream):
    def __init__(self, terms, incrs=[]):
        super(SimpleTokenStream, self).__init__()
        self.tokens = terms
        self.increments = incrs            
        self.i = 0
        
    def next(self):
        if self.i == len(self.tokens):
            return None
        t = lucene.Token(self.tokens[self.i], self.i, self.i)
        # t.setPositionIncrement(n)   -- num words from last token, dflt 1
        self.i += 1
        return t

    def reset(self):
        self.i = 0

    def close(self):
        pass
    
