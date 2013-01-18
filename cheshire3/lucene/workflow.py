
from cheshire3.workflow import SimpleWorkflow
from cheshire3.exceptions import MissingDependencyException

try:
    import lucene
except ImportError:

    class AnalyzerWorkflow(SimpleWorkflow):

        def __init__(self, session, config, parent):
            SimpleWorkflow.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType, "lucene")

else:
    
    class AnalyzerWorkflow(SimpleWorkflow):
        """Workflow to utilize a Lucene Analyzer.
        
        Analyzer is a 'workflow' of string -> keywords + normalization
        hence comes after an Extractor. Available Analyzers:
        
        * BrazilianAnalyzer
        * CJKAnalyzer
        * ChineseAnalyzer
        * CzechAnalyzer
        * DutchAnalyzer
        * FrenchAnalyzer
        * GermanAnalyzer
        * GreekAnalyzer
        * KeywordAnalyzer
        * PatternAnalyzer
        * QueryAutoStopWordAnalyzer
        * RussianAnalyzer
        * SimpleAnalyzer
        * SnowballAnalyzer
        * StandardAnalyzer
        * StopAnalyzer
        * ThaiAnalyzer
        * WhitespaceAnalyzer
        """
    
        _possibleSettings = {
            'analyzer': {
                'docs': 'An Analyzer wrapped as a workflow'
            }
        }
    
        def __init__(self, session, config, parent):
            SimpleWorkflow.__init__(self, session, config, parent)
            anlr = self.get_setting(session, 'analyzer')
            if anlr[-8:] == 'Analyzer' and hasattr(lucene, anlr):            
                anlzClass = getattr(lucene, anlr)
                self.analyzer = anlzClass()
            else:
                raise ConfigFileException("Unknown Lucene Analyzer")
            pass
    
        def process(self, session, data):
            # input should be:
            #   {txt : {'text' : txt, 'occurences' : 1, 'proxLoc' : []}}
            # only thing we can push through is txt
            # output is as from tokenizer (eg to be merged)
    
            if not data:
                return data
            
            kw = {}
            first = data.popitem()
            prox = first[1].has_key('proxLoc')
            data[first[0]] = first[1]
            if type(data) == dict:
                for k in data.keys():                
                    rdr = lucene.StringReader(data[k]['text'])        
                    res = self.analyzer.tokenStream('data', rdr)
    
                    # can also get offset information from terms
                    toks = [t.term() for t in res]
    
                    kw[k] = {'text' :toks, 'occurences' : 1}
                    if prox:
                        kw[k]['proxLoc'] = data[k]['proxLoc']
            return kw
