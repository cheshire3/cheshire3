from cheshire3.transformer import LxmlXsltTransformer
from lxml import etree
from cheshire3.baseObjects import Session
from cheshire3.server import SimpleServer
from cheshire3.normalizer import SimpleNormalizer
from cheshire3.tokenizer import SimpleTokenizer
from cheshire3.index import PassThroughIndex
from cheshire3.web import www_utils
from cheshire3.web.www_utils import multiReplace
from cheshire3.queryFactory import SimpleQueryFactory
import cheshire3.cqlParser as cql
import re


def encodeFormat(self, elements):
    string = ' '.join(elements)
    return string.replace('4~~', '4<sup>to</sup>').replace('8~~', '8<sup>vo</sup>').replace('f~~', 'f<sup>o</sup>').replace('bdsde', 'Broadside').replace('Bdsde', 'Broadside').replace('~~', '<sup>mo</sup>')
    

class ISTCPassThroughIndex(PassThroughIndex):

    def search(self, session, clause, db):
        # first do search on remote index
        currDb = session.database
        session.database = self.database.id
        rs = self.remoteIndex.search(session, clause, self.database)
        # fetch all matched records
        values = {}
        for rsi in rs:
            rec = rsi.fetch_record(session)
            # process xpath
            try:
                value = self.xpath.process_record(session, rec)[0][0]
            except:
                # no data where we expect it
                continue
            if value:
                values[value] = 1

        # construct search from keys and return local search
        localq = cql.parse('c3.%s exact "%s"' % (self.localIndex.id, '|'.join(values.keys())))
        session.database = currDb
        return self.localIndex.search(session, localq, db)
    
#    def search(self, session, clause, db):
#        # first do search on remote index
#        currDb = session.database
#        session.database = self.database.id
#        rs = self.remoteIndex.search(session, clause, self.database)
#        qstring = []
#        # fetch all matched records
#        values = {}
#        for rsi in rs:
#            rec = rsi.fetch_record(session)
#            # process xpath
#            try:
#                value = self.xpath.process_record(session, rec)[0][0]
#            except:
#                # no data where we expect it
#                continue
#            if value:
#                qstring.append('c3.%s exact "%s"' % (self.localIndex.id, value))
#        # construct search from keys and return local search
#        localq = cql.parse(' or '.join(qstring))
#        session.database = currDb
#        return self.localIndex.search(session, localq, db)
    
class FormatTokenizer(SimpleTokenizer):
    
    def __init__(self, session, config, parent):
        self.regexp = re.compile(' or |(?<=[\w]),| and | \(|&')
        
    def process_string(self, session, data): 
        output = []
        data = data.strip()
        if data.find(' ') > -1:
            data1 = data[:data.find(' ')]
            data2 = data[data.find(' '):]
        else:
            data1 = data
            data2 = None
        if data1:
            output.extend(self.regexp.split(data1))
        if data2:
            output.extend(self.regexp.split(data2))
        return output
             
            

class ISTCTransfomer(LxmlXsltTransformer):
    
    def __init__(self, session, config, parent):
        LxmlXsltTransformer.__init__(self, session, config, parent)
        ns = etree.FunctionNamespace('http://www.cheshire3.org/ns/xsl/')
        ns['format'] = encodeFormat
        self.functionNamespace = ns

 
class BibRefNormalizer(SimpleNormalizer):
    
    def __init__(self, session, config, parent):
        self.serv = SimpleServer(session, '/home/cheshire/cheshire3/cheshire3/configs/serverConfig.xml')
        self.db3 = self.serv.get_object(session, 'db_refs')
        self.qf = self.db3.get_object(session, 'DefaultQueryFactory')
    
    def process_string(self, session, data):
        
        ref = data.replace('*', '\*').replace('?', '\?').replace('"', ' ').replace('\'', ' ')
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
                finalRef = data
        db = self.serv.get_object(session, 'db_istc')
        session.database = db.id
        return finalRef
    

class LocCountriesNormalizer(SimpleNormalizer):
    
    def __init__(self, session, config, parent):
        self.dict = {'852' : 'British Isles',
                     '951' : 'British Isles',
                     '995' : 'Belgium',
                     '957' : 'France',
                     '997' : 'Germany',
                     '954' : 'Italy',
                     '955' : 'Spain/Portugal',
                     '996' : 'Netherlands',
                     '952' : 'U.S.A.',
                     '958' : 'Other Europe',
                     '953' : 'Other',
                     '994' : 'Doubtful'
                     }
    
    def process_string(self, session, data):
        return multiReplace(data, self.dict)


class FormatNormalizer(SimpleNormalizer):
   
    def process_string(self, session, data):
        string = data.replace('4~~', '4to').replace('8~~', '8vo').replace('f~~', 'fo').replace('bdsde', 'Broadside').replace('Bdsde', 'Broadside').replace('~~', 'mo')
        return string
    
    
class CountryofPrintNormalizer(SimpleNormalizer):
    
    def __init__(self, session, config, parent):
        self.Balkans = ['cetinje', 'kosinj', 'senj']
        self.BohemiaMoravia = ['pilsen', 'prague', 'winterberg', 'kuttenberg', 'brunn', 'olmutz']
        self.England = ['london', 'westminster', 'st albans', 'st. albans', 'oxford']
        self.France = ['abbeville', 'albi', 'angers', 'angouleme', 'avignon', 'besancon', 'brehan-loudeac', 'caen', 'chablis', 'chalons-sur-marne', 'chambery', 'chartres', 'cluny', 'dijon', 'dole', 'embrun',
                        'geneva', 'goupillieres', 'grenoble', 'lantenac', 'lausanne', 'limoges', 'lyons', 'macon', 'moutiers', 'nantes', 'narbonne', 'orleans', 'paris', 'perigueux', 'perpignan', 'poitiers', 'promenthoux', 'provins', 'rennes', 
                        'rouen', 'rougemont', 'salins', 'sion', 'toulouse', 'tours', 'treguier', 'troyes', 'uzes', 'valence', 'valenciennes', 'vienne', 'france']
        
        self.Germany = ['augsburg', 'bamberg', 'basel', 'beromunster', 'blaubeuren', 'breslau', 'burgdorf', 'cologne', 'constance', 'danzig', 'dillingen', 'eichstatt', 'eltville', 'erfurt', 'esslingen', 'freiberg', 'freising', 'freiburg im breisgau',
                        'hagenau', 'hamburg', 'heidelberg', 'ingolstadt', 'kirchheim in elsass', 'lauingen', 'leipzig', 'lubeck', 'luneburg', 'magdeburg', 'mainz', 'marienburg', 'marienthal', 'meissen', 'memmingen', 'merseburg', 'metz', 'munster', 'munich',
                        'nuremberg', 'offenburg', 'oppenheim', 'passau', 'pforzheim', 'regensburg', 'reutlingen', 'rostock', 'schleswig', 'schussenried', 'speyer', 'stendal', 'strassburg', 'stuttgart', 'sursee', 'trier', 'tubingen', 'ulm', 'urach', 'vienna', 
                        'wurttemberg', 'wurzburg', 'zinna', 'zurich', 'zweibrucken', 'bavaria', 'germany']
        self.Hungary = ['bratislava', 'buda', 'hungary']
        self.Italy = ['aquila', 'ascoli piceno', 'barco', 'bologna', 'brescia', 'cagli', 'cagliari', 'capua', 'carmagnola', 'casal di san vaso', 'casal maggiore', 'caselle', 'castano primo', 'cesena', 'cividale', 'chivasso', 'colle', 'colle di valdelsa', 'como', 'cosenza',
                     'cremona', 'faenza', 'fano', 'ferrara', 'florence', 'fivizzano', 'foligno', 'forli', 'gaeta', 'genoa', 'iesi', 'lucca', 'mantua', 'matelica', 'messina', 'milan', 'modena', 'mondovi', 'naples', 'nonantola', 'novi', 'nozzano', 'padua', 'palermo',
                     'parma', 'pavia', 'perugia', 'pescia', 'piacenza', 'pinerolo', 'piove di sacco', 'pisa', 'pojano', 'portese', 'reggio di calabria', 'reggio emilia', 'rome', 'saluzzo', 'san cesario', 'san germano', 'santorso', 'savigliano', 'savona', 'scandiano',
                     'siena', 'soncino', 'subiaco', 'turin', 'torrebelvicino', 'toscolano', 'trent', 'trevi', 'treviso', 'udine', 'urbino', 'venice', 'vercelli', 'verona', 'vicenza', 'viterbo', 'voghera', 'italy']   
        self.LowCountries = ['alost', 'antwerp', 'audenarde', 'bruges', 'brussels', 'culemborg', 'delft', 'deventer', 'ghent', 'gouda', 'haarlem', 'hasselt', 's-hertogenbosch', 'leiden', 'liege', 'louvain', 'nijmegen', 'st maartensdijk', 'schiedam', 'schoonhoven', 'utrecht',
                             'valenciennes', 'zwolle', 'netherlands']
        self.Poland = ['breslau', 'chelmno', 'cracow', 'danzig', 'marienburg']
        self.Portugal = ['braga', 'chaves', 'faro', 'leiria', 'lisbon', 'oporto', 'portugal']
        self.Scandinavia = ['copenhagen', 'gripsholm', 'odense', 'ribe', 'schleswig', 'stockholm', 'vadstena']
        self.Spain = ['barcelona', 'burgos', 'coria', 'gerona', 'granada', 'guadalajara', 'hijar', 'huete', 'lerida', 'mallorca', 'monterrey', 'montserrat', 'murcia', 'orense', 'oviedo', 'pamplona', 'perpignan', 'salamanca', 'segovia', 'seville', 'tarragona', 'toledo',
                      'tortosa', 'valencia', 'valladolid', 'valldemusa', 'zamora', 'zaragoza', 'castile', 'spain']

    
    def process_string(self, session, data):
        if data in self.Balkans:
            return 'Balkans'
        elif data in self.BohemiaMoravia:
            return 'Bohemia and Moravia'
        elif data in self.England:
            return 'England'
        elif data in self.France or 'france' in data.split():
            return 'France'
        elif data in self.Germany or 'germany' in data.split():
            return 'Germany'
        elif data in self.Hungary:
            return 'Hungary'
        elif data in self.Italy or 'italy' in data.split():
            return 'Italy'
        elif data in self.LowCountries or 'netherlands' in data.split():
            return 'Low Countries'
        elif data in self.Poland:
            return 'Poland'
        elif data in self.Portugal:
            return 'Portugal'
        elif data in self.Scandinavia:
            return 'Scandinavia'
        elif data in self.Spain:
            return 'Spain'
        else :
            return data
        
        
            
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
                     "ger":'German',
                     "ita":'Italian',
                     "lat":'Latin',
                     "por":'Portuguese',
                     "pro":'Provencal / Occitan',
                     "sar":'Sardinian',
                     "spa":'Spanish',
                     "swe":'Swedish',
                     "src":'Croatian',
                     "frm": 'French',
                     "grc": 'Greek'
                     }
    
    def process_string(self, session, data):       
        return multiReplace(data, self.dict).replace("heb",'Hebrew').replace("fre", 'French')