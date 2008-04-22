# import mod_python stuffs
from mod_python import apache, Cookie
from mod_python.util import FieldStorage

# import generally useful modules
import sys, os, traceback, cgitb, urllib, time, smtplib, re

# set sys paths 
databaseName = 'apu'
cheshirePath = '/home/cheshire'
osp = sys.path
sys.path = [os.path.join(cheshirePath, 'cheshire3', 'code')]
sys.path.extend(osp)

# value to normalize frequency counts by
normalizationBase = 10000
z = False
zstatSig = 3


# import Cheshire3/PyZ3950 stuff
from server import SimpleServer
from PyZ3950 import CQLParser, SRWDiagnostics
from baseObjects import Session
from document import StringDocument
from stats import *

import c3errors
# C3 web search utils

class BrowseHandler:
    
    htmlPath = cheshirePath + '/cheshire3/www/%s/html' % databaseName
    logger = None
    redirected = False
    
     
    def __init__(self, lgr):
        self.logger = lgr
        build_architecture()
    
        
    def send_html(self, data, req, code=200):
        req.content_type = 'text/html'
        req.content_length = len(data)
        if (type(data) == unicode):
          data = data.encode('utf-8')
        req.write(data)
        req.flush()    
        
        
    def send_xml(self, data, req, code=200):
        req.content_type = 'text/xml'
        req.content_length = len(data)
        if (type(data) == unicode):
          data = data.encode('utf-8')
        req.write(data)
        req.flush()   
    
    
    def create_TFP(self, form):
        word = form.get('word', None)
        indexName = form.get('index', None)
        if indexName != 'sentence':
            cql = 'c3.sentence-idx exact %s' % word
            q = CQLParser.parse(cql)
            rs_base = db.search(session,q)
            
            cql = 'c3.%s-idx exact %s' % (indexName, word)
            q = CQLParser.parse(cql)
            rs = db.search(session,q)
            subset = []
            hits = len(rs)
            if (hits>0):                
                for r in rs:
                    subset.append(r)
            hits_base = len(rs_base)
            dist_base = {}
            dist_pos = {}
            dist_neg = {}
            if (hits_base>0):
                for r in rs_base :
                    try:
                        dist_base[r.occurences]+=1
                    except:
                        dist_base[r.occurences]=1
                    if r in subset:
                        try:
                            dist_pos[r.occurences]+=1
                        except:
                            dist_pos[r.occurences]=1
                    else:
                        try:
                            dist_neg[r.occurences]+=1
                        except:
                            dist_neg[r.occurences]=1
                            
            hits_base = sum(dist_base.values())
            hits_pos = sum(dist_pos.values())
            hits_neg = sum(dist_neg.values())
            
            output = ['<table><tr><td>frequency</td><td>when in %s (%s)</td><td>when not in %s (%s)</td><td>all</td></tr>' % (indexName, '%', indexName, '%')]
            for i in [1,2,3]: 
                output.append('<tr><td>%s</td><td>%0.2f</td><td>%0.2f</td><td>%0.2f</td></tr>' % (i, max(float(dist_pos[i])/float(hits_pos) * 100.0,0), max(float(dist_neg[i])/float(hits_neg) * 100.0,0), max(float(dist_base[i])/float(hits_base) * 100.0,0)))  
            fourPlus_base=0
            fourPlus_pos=0
            fourPlus_neg=0
            for i in range(4,max(dist_base.keys())):
                try:
                    fourPlus_base += dist_base[i]
                except:
                    continue
            for i in range(4,max(dist_pos.keys())):
                try:
                    fourPlus_pos += dist_pos[i]
                except:
                    continue
            for i in range(4,max(dist_neg.keys())):
                try:
                    fourPlus_neg += dist_neg[i]
                except:
                    continue
            output.append('<tr><td>4+</td><td>%0.2f</td><td>%0.2f</td><td>%0.2f</td></tr>' % (max(float(fourPlus_pos)/float(hits_pos) * 100.0,0), max(float(fourPlus_neg)/float(hits_neg) * 100.0,0), max(float(fourPlus_base)/float(hits_base) * 100.0,0)))
            output.append('</table>')
            return ''.join(output)    
        else :
            dist = {}
            cql = 'c3.%s-idx exact %s' % (indexName, word)
            q = CQLParser.parse(cql)
            rs = db.search(session,q)
            hits = len(rs)
            if (hits>0):
                for r in rs:
                    try:
                        dist[r.occurences]+=1
                    except:
                        dist[r.occurences]=1
            hits = sum(dist.values())
            output = ['<table><tr><td>frequency</td><td>total articles</td><td>%</td></tr>']
        
            for i in [1,2,3]:
                try :
                    output.append('<tr><td>%s</td><td>%s</td><td>%0.2f</td></tr>' % (i, dist[i], float(dist[i])/float(hits) * 100.0))  
                except KeyError :
                    output.append('<tr><td>%s</td><td>0</td><td>0</td></tr>' % i)
            fourPlus=0
            for i in range(4,max(dist.keys())):
                try:
                    fourPlus += dist[i]
                except:
                    continue
            try :
                output.append('<tr><td>4+</td><td>%s</td><td>%0.2f</td></tr>' % (fourPlus, float(fourPlus)/float(hits) * 100.0))
            except KeyError:
                output.append('<tr><td>4+</td><td>0</td><td>0</td></tr>')
            output.append('</table>')
            return ''.join(output)
            #print "\n%i occurrences in %i articles" % (occs,hits)    
    
    
    def compareIndexes(self, req):
        self.logger.log('comparing indexes')
        start = time.time()
        form = FieldStorage(req)
        id = form.get('id','data_grid')
        offset = str(form.get('offset', 0))
        if offset.find('.') != -1:
            startNum = int(offset[:offset.find('.')])
            adjustValue = int(offset[offset.find('.')+1:])
        else :
            startNum = int(offset)
            adjustValue = 0       
        howMany = int(form.get('page_size', 100))
        indexStrings = form.get('index', None)
        sentenceIdx = db.get_object(session, 'sentence-idx')
        corpusSize = sentenceIdx.fetch_metadata(session)['nOccs']
        indexList = []
        addTfp = False
        if (indexStrings.__class__ == list):
            if (indexStrings[0].find('gram') == -1):
                addTfp = True
            for i in range(0, len(indexStrings)):
                indexList.append(db.get_object(session, '%s' % indexStrings[i]))  
        else :
            if (indexStrings.find('gram') == -1):
                addTfp = True
            indexList.append(db.get_object(session, '%s' % indexStrings))
        
        output = []
        firstIndex = indexList[0]
        
        firstTotal = firstIndex.fetch_metadata(session)['nOccs']
        q = CQLParser.parse('idx-foo any "bar"')
        appending = True
        if startNum < 0 :
            appending = False
            startNum = startNum/-1
        
        idxLength = firstIndex.fetch_metadata(session)['nTerms']
        completed = False
        cycles = 0;
        firstStart = startNum

        while len(output) < howMany and completed == False:     
            if appending :
                startNum = int(firstStart+(howMany*cycles))
            else :
                startNum = int(startNum-(howMany*cycles))
            cycles += 1
            if appending and idxLength-(startNum) <= howMany :
                completed = True
            if appending:
                termList = firstIndex.fetch_termFrequencies(session, 'rec', startNum, min(howMany, idxLength-(startNum)), '>')
            else :
                termList = firstIndex.fetch_termFrequencies(session, 'rec', startNum, min(howMany, startNum), '<')
                      
            for i, t in enumerate(termList):                
                cells = []
                word = firstIndex.fetch_termById(session, t[1])
                q.term.value = word
                percentage = round((float(t[2]) / float(firstTotal) * normalizationBase), 2)
                firstIndexName = indexList[0].id[:indexList[0].id.find('-')]
                
                if appending :
                    cells.append('<td>%d</td>' % (i+1+startNum))
                else :                   
                    cells.append('<td>%d</td>' % (startNum+1-i))
                try:
                    indexList[1]                
                except:     
                    if addTfp == True:                                       
                        cells.append('<td>&lt;a href="javascript:searchFor(\'%s\', \'%s\')">%s&lt;/a></td><td>&lt;a href="javascript:tfpFor(\'%s\', \'%s\')">tfp&lt;/a></td><td>%s</td>' % (word, firstIndexName, word, word, firstIndexName, percentage))                     
                    else :
                        cells.append('<td>&lt;a href="javascript:searchFor(\'%s\', \'%s\')">%s&lt;/a></td><td>%s</td>' % (word, firstIndexName, word, percentage))                     
                    cells.append('<td>%s</td>' % t[2])     
                else:  
                    if addTfp == True: 
                        cells.append('<td>&lt;a href="javascript:searchFor(\'%s\', \'%s\')">%s&lt;/a></td><td>&lt;a href="javascript:tfpFor(\'%s\', \'%s\')">tfp&lt;/a></td><td>%s</td>' % (word, firstIndexName, word, word, firstIndexName, percentage))                     
                    else :
                        cells.append('<td>&lt;a href="javascript:searchFor(\'%s\', \'%s\')">%s&lt;/a></td><td>%s</td>' % (word, firstIndexName, word, percentage))                     
                    othersTotal = 0
                    othersHits = 0               
                    for j in range(1, len(indexList)):
                        total = indexList[j].fetch_metadata(session)['nOccs']
                        othersTotal += total
                        occs = indexList[j].scan(session, q, 1)    
                        
                        if (occs[0][0] == word):
                            othersHits += occs[0][1][2]
                            #add each cell
                            normalisedOccs = round((float(occs[0][1][2]) / float(total) * normalizationBase), 2)
                            cells.append('<td>%s</td>' % normalisedOccs)
                        else :
                            cells.append('<td>0</td>')                        
                    if z :
                        zstat = zscore(othersHits, t[2], othersTotal, indexList[0].fetch_metadata(session)['nOccs'])
                        if zstat >= zstatSig:
                            cells.append('<td>%s</td>' % zstat)
                        else :
                            continue
                        
                output.append('<tr>%s</tr>' % ''.join(cells))

            if not appending:
                output.reverse()
           # output = output[adjustValue:]
        (mins, secs) = divmod(time.time()-start, 60)
        self.logger.log('scanning complete: %s' % secs) 
        return '<ajax-response><response type="object" id="%s_updater"><rows update_ui="true">%s</rows></response></ajax-response>' % (id, ''.join(output))
        
                        
    def sortFunc (self, x, y):       
        return cmp(self.getNum(x),self.getNum(y))       


    def getNum(self, str): 
        try : 
            return int(re.findall(r'\d+', str)[0])
        except :
            return 0


    def getIndexList(self, req):
        indexStore = db.get_object(session, 'indexStore')
        output = []
        for i in indexStore :
            id = i.id
            if id[0:3] != 'ARM' and id[id.rfind('-')+1:] not in ['stempos', 'stem', 'pos', 'single', 'wordpos'] and id not in ['article-idx', 'HISC-idx', 'paragraph-idx']:
                output.append('<option class="%s" value="%s">%s</option>' % (self.getNum(id), id, id[:-4]))
        output.sort()
        output.sort(self.sortFunc)
        return '<xml>%s</xml>' % ''.join(output)
   

    def handle(self, req):
        form = FieldStorage(req)
        mode = form.get('mode', None)
        if (mode == 'compare'):
            page = self.compareIndexes(req)
            self.send_xml(page, req)
        elif (mode == 'index') :
            page = self.getIndexList(req)
            self.send_xml(page, req)
        elif (mode == 'tfp') :
            page = self.create_TFP(form)
            self.send_xml(page, req)
       

def build_architecture(data=None):
    global session, serv, db, xmlp, recordStore, sentenceStore, paragraphStore, resultSetStore, articleTransformer, kwicTransformer
    session = Session()
    session.environment = 'apache'
    session.user = None
    serv = SimpleServer(session, os.path.join(cheshirePath, 'cheshire3','configs','serverConfig.xml'))
    
    session.database = 'db_' + databaseName
    db = serv.get_object(session, session.database)
    xmlp = db.get_object(session, 'LxmlParser')
    recordStore = db.get_object(session, 'recordStore')
    articleTransformer = db.get_object(session, 'article-Txr')
    kwicTransformer = db.get_object(session, 'kwic-Txr')

