
from cheshire3.workflow import SimpleWorkflow

import lucene

# Analyzer is a 'workflow' of string -> keywords + normalization
# hence comes after Extractor

class AnalyzerWorkflow(SimpleWorkflow):

    def __init__(self, session, config, parent):
        SimpleWorkflow.__init__(self, session, config, parent)
        anlr = self.get_setting(session, 'analyzer')
        if anlr[-8:] == 'Analyzer' and hasattr(lucene, anlr):            
            self.analyzer = getattr(lucene, anlr)
        else:
            raise ConfigFileException("Unknown Lucene Analyzer")
        pass

    def process(self, session, data):
        # input should be:
        #   {txt : {'text' : txt, 'occurences' : 1, 'proxLoc' : []}}
        # only thing we can push through is txt

        if type(data) == dict:
            for k in data.keys():                
                rdr = lucene.StringReader(data[k]['text'])        
                res = self.analyzer(rdr)
                toks = [t.term() for t in res]
                print repr(toks)



### Available Analyzers:
##   BrazilianAnalyzer
##   CJKAnalyzer
##   ChineseAnalyzer
##   CzechAnalyzer
##   DutchAnalyzer
##   FrenchAnalyzer
##   GermanAnalyzer
##   GreekAnalyzer
##   KeywordAnalyzer
##   PatternAnalyzer
##   QueryAutoStopWordAnalyzer
##   RussianAnalyzer
##   SimpleAnalyzer
##   SnowballAnalyzer
##   StandardAnalyzer
##   StopAnalyzer
##   ThaiAnalyzer
##   WhitespaceAnalyzer
