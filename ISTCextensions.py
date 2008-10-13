from cheshire3.transformer import LxmlXsltTransformer
from lxml import etree
from cheshire3.server import SimpleServer
from cheshire3.normalizer import SimpleNormalizer
from cheshire3.web import www_utils
from cheshire3.web.www_utils import multiReplace
import re




#cgiReplacements = {
#'+': '%2B',
#' ': '%20',
#'<': '%3C',
#'>': '%3E',
#'#': '%23',
#'{': '%7B',
#'}': '%7D',
#'|': '%7C',
#'"': '%22',
#"'": '%27',
#'^': '%5E',
#'~': '%7E',
#'[': '%5B',
#']': '%5D',
#'`': '%60',
#';': '%3B',
#'/': '%2F',
#'?': '%3F',
#':': '%3A',
#'@': '%40',
#'=': '%3D',
#'&': '%26',
#'$': '%24'
#}
#
#def myURIEncoder(dummy, txt):
#    global cgiReplacements
#    
#    if isinstance(txt, list):
#        txt = ' '.join(txt)
##    else :
##        txt = elements
#    txt = txt.replace('%', '%25')
#    #txt = txt.strip()
#    for key, val in cgiReplacements.iteritems():
#        txt =  txt.replace(key, val)
#
#    return txt

def encodeFormat(self, elements):
    string = ' '.join(elements)
    return string.replace('4~~', '4<sup>to</sup>').replace('8~~', '8<sup>vo</sup>').replace('f~~', 'f<sup>o</sup>').replace('bdsde', 'Broadside').replace('Bdsde', 'Broadside').replace('~~', '<sup>mo</sup>')
    

class ISTCTransfomer(LxmlXsltTransformer):
    
    def __init__(self, session, config, parent):
        LxmlXsltTransformer.__init__(self, session, config, parent)
        ns = etree.FunctionNamespace('http://www.cheshire3.org/ns/xsl/')
        #ns['uri'] = myURIEncoder
        ns['format'] = encodeFormat
        self.functionNamespace = ns
        
 
class BibRefNormalizer(SimpleNormalizer):
    
    def __init__(self, session, config, parent):
        self.serv = SimpleServer(session, '/home/cheshire/cheshire3/cheshire3/configs/serverConfig.xml')
        self.db3 = self.serv.get_object(session, 'db_refs')
        self.qf = self.db3.get_object(session, 'DefaultQueryFactory')
    
    def process_string(self, session, data):
        
        ref = data.replace('*', '\*').replace('"', ' ').replace('\'', ' ')
        session.database = self.db3.id
        q = self.qf.get_query(session, 'c3.idx-key-refs exact "%s"' % (ref))
        rs = self.db3.search(session, q)
        if len(rs):
            finalRef = ref
        else :
            while ref.rfind(' ') != -1 and not len(rs):
                ref = ref[:ref.rfind(' ')].strip()
                q.term.value = ref
                rs = self.db3.search(session, q)
            if len(rs):
                finalRef = ref
            else:
                finalRef = data.replace('*', '\*').replace('"', ' ').replace('\'', ' ')
        db = self.serv.get_object(session, 'db_istc')
        session.database = db.id
        return finalRef
    
#    def process_string(self, session, data):
#        list = data.split(' ')
#        new = []
#        for l in list:
#            if re.search('^(p){1,2}.?[0-9]*.?-?,?\(?[0-9]*\)?,?$|^[a-z]{0,1}[0-9]+[a-z]{0,3}.?-?,?[0-9]*,?$|^[ixlcv]+,?-?[ixlcv]+$|^\(?suppl.?\)?$|^\(?[a-z]-[0-9]+[a-z]{0,3}\)?,?$|^[a-z]$', l):
#                break
#            else:
#                new.append(l)
#        return ' '.join(new)

class FormatNormalizer(SimpleNormalizer):
   
    def process_string(self, session, data):
        string = data.replace('4~~', '4to').replace('8~~', '8vo').replace('f~~', 'fo').replace('bdsde', 'Broadside').replace('Bdsde', 'Broadside').replace('~~', 'mo')
        return string
    
    
class LanguageNormalizer(SimpleNormalizer):
    def __init__(self, session, config, parent):
        self.dict = {"eng":'English',             
                     "bre":'Breton',
                     "cat":'Catalan',
                     "chu":'Church Slavonic',
                     "cze":'Czech',
                     "dan":'Danish',
                     "dut":'Dutch',
                     "fri":'Frisian',
                     "fre":'French',
                     "ger":'German',
                     "ita":'Italian',
                     "lat":'Latin',
                     "por":'Portuguese',
                     "sar":'Sardinian',
                     "spa":'Spanish',
                     "swe":'Swedish'
                     }
    
    def process_string(self, session, data):       
        return multiReplace(data, self.dict).replace("heb",'Hebrew')