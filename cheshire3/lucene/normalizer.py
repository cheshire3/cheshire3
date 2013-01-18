
# Wrap Lucene Filter in Cheshire3

from cheshire3.exceptions import ConfigFileException
from cheshire3.exceptions import  MissingDependencyException
from cheshire3.normalizer import SimpleNormalizer

try:
    import lucene
except ImportError:

    class FilterNormalizer(SimpleNormalizer):

        def __init__(self, session, config, parent):
            SimpleNormalizer.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType, "lucene")

else:
    from cheshire3.lucene.utils import SimpleTokenStream

    class FilterNormalizer(SimpleNormalizer):
    
        _possibleSettings = {
            'filter' : {
                'docs': 'Name of the Filter to use'
            },
            'argument': {
                'docs': 'An optional string argument to give to the Filter'
            }
        }
    
        def __init__(self, session, config, parent):
            SimpleNormalizer.__init__(self, session, config, parent)
            fltr = self.get_setting(session, 'filter')
            if fltr[-6:] == 'Filter' and hasattr(lucene, fltr):            
                self.filter = getattr(lucene, fltr)
            else:
                raise ConfigFileException("Unknown Filter")
    
            # eg SnowballFilter(strm, 'English')
            # For more complex filter constructors, just subclass
            # FilterNormalizer as required
    
            arg1 = self.get_setting(session, 'argument', '')
            if arg1:
                self.argument = arg1
            else:
                self.argument = None
    
        def process_string(self, session, data):
            # make a new stream with a single token
            ts = SimpleTokenStream([data])
            if self.argument:            
                res = self.filter(ts, self.argument)
            else:
                res = self.filter(ts)
            toks = [t for t in res]
            if len(toks) == 1:
                return toks[0].term()
            elif len(toks):
                print toks
                raise NotImplementedError()
            else:
                return None
    
    
class StopFilterNormalizer(FilterNormalizer):
    # Pointless but hopefully informative example

    def __init__(self, session, config, parent):
        FilterNormalizer.__init__(self, session, config, parent)
        self.filter = lucene.StopFilter

    def process_string(self, session, data):
        # Make a new stream with a single token
        ts = SimpleTokenStream([data])
        res = self.filter(ts, lucene.StopAnalyzer.ENGLISH_STOP_WORDS)
        try:
            tok = res.next()
        except:
            return None
        return tok.term()
    

### Current Filters to look at:
   
##  BrazilianStemFilter
##  ChineseFilter
##  DictionaryCompoundWordTokenFilter     Requires dictionary
##  DutchStemFilter
##  EdgeNGramTokenFilter
##  ElisionFilter               l'avion --> avion
##  FileFilter
##  FilenameFilter
##  FrenchStemFilter
##  GermanStemFilter
##  GreekLowerCaseFilter
##  HyphenationCompoundWordTokenFilter
##  ISOLatin1AccentFilter
##  IndexFileNameFilter
##  LengthFilter
##  LowerCaseFilter
##  NGramTokenFilter
##  NumericPayloadTokenFilter
##  PorterStemFilter
##  PrefixAndSuffixAwareTokenFilter
##  PrefixAwareTokenFilter
##  PrefixFilter
##  QueryFilter
##  QueryWrapperFilter
##  RangeFilter
##  RemoteCachingWrapperFilter
##  RussianLowerCaseFilter
##  RussianStemFilter
##  ShingleFilter
##  ShingleMatrixFilter
##  SpanFilter
##  SpanQueryFilter
##  StandardFilter
##  StopFilter
##  SynonymTokenFilter
##  TeeTokenFilter
##  TermsFilter
##  ThaiWordFilter
##  TokenFilter
##  TokenOffsetPayloadTokenFilter
##  TypeAsPayloadTokenFilter

##  DuplicateFilter  <-- takes fieldname as constructor


##  CachingSpanFilter
##  CachingTokenFilter
##  CachingWrapperFilter
            
        
