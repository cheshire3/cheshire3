
from cheshire3.tokenizer import SimpleTokenizer
from cheshire3.exceptions import MissingDependencyException

try:
    import lucene
except ImportError:

    class LuceneTokenizer(SimpleTokenizer):
    
        _possibleSettings = {'tokenizer': {'docs': ''}}
    
        def __init__(self, session, config, parent):
            SimpleTokenizer.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType, "lucene")

else:
    class LuceneTokenizer(SimpleTokenizer):
    
        _possibleSettings = {'tokenizer': {'docs': ''}}
    
        def __init__(self, session, config, parent):
            SimpleTokenizer.__init__(self, session, config, parent)
            tknr = self.get_setting(session, 'tokenizer')
            if tknr[-9:] == 'Tokenizer' and hasattr(lucene, tknr):            
                self.tokenizer = getattr(lucene, tknr)
            else:
                raise ConfigFileException("Unknown Lucene Tokenizer")
            
        def process_string(self, session, data):
            rdr = lucene.StringReader(data)
            toks = self.tokenizer(rdr)
            return [t.term() for t in toks]


# This doesn't work as expected!
# offset here is /word/ offset, not byte or character offset
# this looks like a bug, compared to Lucene documentation

class LuceneOffsetTokenizer(LuceneTokenizer):

    def process_string(self, session, data):
        rdr = lucene.StringReader(data)
        toks = self.tokenizer(rdr)
        return zip([(t.term(), t.startOffset()) for t in toks])


### Current Tokenizers:    
##   CJKTokenizer
##   ChineseTokenizer
##   DateRecognizerSinkTokenizer
##   EdgeNGramTokenizer   # --- needs non stringreader input?
##   KeywordTokenizer
##   LetterTokenizer
##   LowerCaseTokenizer
##   NGramTokenizer
##   RussianLetterTokenizer
##   SinkTokenizer
##   StandardTokenizer
##   TokenRangeSinkTokenizer
##   TokenTypeSinkTokenizer
##   WhitespaceTokenizer
