import cPickle
import os, re, hashlib

from server import SimpleServer
from document import StringDocument
from operator import itemgetter

cheshirePath = '/home/cheshire'


maxSize = 5000;


class Concordancer :
    
    db = None
    serv = None
    session = None
    concStore = None
    idxStore = None
    logger = None
    wordNumber = 1
    sortList = 0
    wn = 1
    
      
    def __init__(self, session, logger):
        self.session = session
        session.database = 'db_apu'
        self.serv = SimpleServer(session, os.path.join(cheshirePath, 'cheshire3','configs','serverConfig.xml'))
        self.db = self.serv.get_object(session, session.database)
        self.resultSetStore = self.db.get_object(session, 'resultSetStore')
        self.concStore = self.db.get_object(session, 'concordanceStore')
        self.idxStore = self.db.get_object(session, 'indexStore')
        self.matches = []
        self.logger = logger
        
    
    def filter_concordance(self, id, matchList):
        self.logger.log('concordance filtering')
        matchArray = matchList.split(' ')
        self.logger.log(matchArray)
        idx = id.split('|')[0]
        if idx == 'window':
            index = self.db.get_object(self.session, 'article-idx')
        else :
            index = self.db.get_object(self.session, '%s-idx' % idx)
        try :
            rs = self.resultSetStore.fetch_resultSet(self.session, id)
        except :
            self.logger.log('no resultSet')
            pass       
        else :
            for r in rs :
                prox = r.proxInfo
                for m in prox :
                    vec = self.idxStore.fetch_proxVector(self.session, index, r, m[0][0])
                    ids = [v[1] for v in vec]
                    match = True
                    for i in matchArray:
                        if not int(i) in ids:                           
                            match = False
                            break
                    if match == True:
                        self.logger.log([r.id, m[0][0]])
                        self.matches.append([r.id, m[0][0]])
            self.logger.log(self.matches)
            concordance = self.load_concordance(id)[0]
            concordance.sort(self.filterFunc)            
            id = self.save_concordance(concordance, id, 5)
            self.logger.log('filtering complete - %s' % id)
            return id



    def filterFunc(self, x, y):
        if [x[3][1], x[4][0][0]] in self.matches and [y[3][1], y[4][0][0]] in self.matches :            
            return 0
        elif [x[3][1], x[4][0][0]] in self.matches and not [y[3][1], y[4][0][0]] in self.matches :
            return -1
        elif not [x[3][1], x[4][0][0]] in self.matches and [y[3][1], y[4][0][0]] in self.matches :
            return 1
        else :
            return 0




    def sort_concordance(self, id, side='left', wn=1):
        self.logger.log('sorting concordance')
        self.wn = int(wn)
        if side=='left':
            self.sortList = 0
            self.wordNumber = int(wn)/-1
        elif side =='node':
            self.sortList = 1
            self.wordNumber = int(wn)-1
        else :
            self.sortList = 2
            self.wordNumber = int(wn)-1
        self.logger.log('side and number set')
        temp = self.load_concordance(id)
        self.logger.log('concordance loaded')
        concordance = temp[0]
        totalOccs = temp[1]
        wordWindow = temp[2]
        self.logger.log('sorting length = %d wordWindow %d' % (totalOccs, wordWindow))
        if self.wordNumber > wordWindow:
            self.wordNumber = wordWindow
        concordance.sort(self.sortFunc)
        id = self.save_concordance(concordance, id, wordWindow)
        self.logger.log('sorting complete - %s' % id)
        return id
  
  
  
    def sortFunc(self, x, y):
        if x[self.sortList] and y[self.sortList]:
            if len(x[self.sortList]) >= self.wn  and len(y[self.sortList]) >= self.wn:
                return cmp(x[self.sortList][self.wordNumber][0], y[self.sortList][self.wordNumber][0])       
            elif len(x[self.sortList]) >= self.wn  and not len(y[self.sortList]) >= self.wn:
                return 1               
            elif not len(x[self.sortList]) >= self.wn  and len(y[self.sortList]) >= self.wn:
                return -1
            else:
                return 0
        elif x[self.sortList] and not y[self.sortList] :
            return 1
        elif not x[self.sortList] and y[self.sortList] :
            return -1
        else :
            return 0

    
    
    def create_concordance(self, id):
        self.logger.log('CREATING CONCORDANCE')     
        syntaxRe = re.compile('[\w]* |[\w]*$|[[(][ ]?[\w]*[ ]?[])][\s$]?|{[\w\s]+}[\s$]?')
        session = self.session
        idxStore = self.idxStore
        variableArray = id.split('|')
        idx = variableArray[0]
        type = variableArray[1]
        terms = variableArray[2].replace('_', ' ')
        slots = []
        if idx == 'window':
            idx = 'article'
            type = 'window'
        syntax = False
        if (type == 'phrase' and (terms.find('(') > -1 or terms.find('{') > -1 or terms.find('[') > -1)) :
            syntax = True
            iter = syntaxRe.finditer(terms)
            counter = 0
            for i in iter:
                if i.group() != '':
                    termSet = i.group()
                    self.logger.log(termSet)
                    if termSet[0] == '[' or termSet[0] == '(' or termSet[0] == '{' :
                        slots.append([counter, termSet[0], {}])
                counter += 1
            
        wordWindow = int(variableArray[4])
        index = self.db.get_object(session, '%s-idx' % idx)
        try :
            rs = self.resultSetStore.fetch_resultSet(session, id)
        except:
            self.logger.log('NO RS EXISTS')
        else :
            if (len(rs) > 0):
                clines = []        
                #for each rsItem
                for k, i in enumerate(rs):
                   
                    #first we need to get a set of the first number in the first list of each list
                    temp = []
                    for m in i.proxInfo:
                        temp.append(m[0][0])
                    elems = set(temp)
                    vecs = {}
                    #for each time the word occurs in the record 
                    for e in elems:
                        #get the prox vector for the node of the record
                        vecs[e] = idxStore.fetch_proxVector(session, index, i, e)
                    
                    for m in i.proxInfo:
                        
                        (e, w) = (m[0][0], m[0][1])
                        if type == 'all' or type == 'window':              
                            nodeLength = 1
                        else :
                            nodeLength = len(m)
                        v = vecs[e]
                        
                       #for word numbers 
                        before = [[x[1], x[0]] for x in v[max(0, w-wordWindow):w]]
                        node = [[x[1], x[0]] for x in v[w: min(w+nodeLength, len(v))]]
                        after = [[x[1], x[0]] for x in v[min(w+nodeLength, len(v)):min(w+nodeLength+wordWindow, len(v))]]
                        
     #                   before = [[x[1], x[2]] for x in v[max(0, w-wordWindow):w]]
     #                   node = [[x[1], x[2]] for x in v[w: min(w+nodeLength, len(v))]]
     #                   after = [[x[1], x[2]] for x in v[min(w+nodeLength, len(v)):min(w+nodeLength+wordWindow, len(v))]]
                        
                        finalOffset=0
                        try:
                            tid = vecs[e][w+nodeLength+wordWindow]
                            finalOffset=tid[2]
                        except:
                            finalOffset = None
                       
                        lastNodeOffset = v[w+nodeLength-1][2]
                          
                        rhsOffset = v[min(w+nodeLength, len(v)-1)][2]
                        if rhsOffset == lastNodeOffset:
                            rhsOffset = None
                          
                        loc = [i.recordStore, i.id, idx, k]
                        
                        proxOffset = [[e, v[max(0, w-wordWindow)][2]], [e, v[w][2]], [e, rhsOffset], [e, finalOffset]]                                                                                                                                            
                        conc = [before, node, after, loc, proxOffset]                    
                        clines.append(conc)
                #self.logger.log('|||||||||||||||||||||||||||||||||||||||||||||')
                #self.logger.log(slots)
                if syntax :
                    for s in slots:
                        d = s[2]
                        for c in clines:
                            try:
                                d[c[1][s[0]][0]] += 1
                            except:
                                d[c[1][s[0]][0]] = 1 
                        #self.logger.log(d.items())
                        string = []
                        
                        klist = d.items()
                        klist.sort(key=itemgetter(1),reverse=True)
                        
                        for k in klist:
                            #self.logger.log(k)
                            total = k[1]
                            word = index.fetch_termById(session, k[0])
                            string.append('<tr><td>%s</td><td>%s</td></tr>' % (word, total))
                        table = '<table class="frameTable">%s</table>' % ''.join(string)    
                else:
                    table = ''                                                              
                self.save_concordance(clines, id, wordWindow)                                 
                return (len(clines)-1, table) # add slots
# [[words#, wordOffsets][words#, wordOffsets][words#, wordOffsets][recordStore, recId, index][[elem#, charOff],[elem#, charOff],[elem#, charOff],[elem#, charOff]]] 
            
            
    def save_concordance(self, clines, id, wordWindow):
        global maxSize
        self.logger.log('saving concordance - %d' % len(clines))
        if len(clines) > maxSize :
            i = 1
            for j in range(0, len(clines), maxSize):
                slice = clines[j:j+maxSize]
                slice.insert(0, [len(clines), wordWindow])
                string = cPickle.dumps(slice)
                doc = StringDocument(string)
                doc.id = '%s_%d' % (id, i)
                i += 1
                self.concStore.store_document(self.session, doc)
        else :
            clines.insert(0, [len(clines), wordWindow])
            string = cPickle.dumps(clines)
            doc = StringDocument(string)
            doc.id = '%s_1' % id
            self.concStore.store_document(self.session, doc)
        self.concStore.commit_storing(self.session)
        return id
    
        

    def load_concordance(self, id, offset=0, pageSize=None):
        global maxSize
        self.logger.log('loading concordance with id %s ' % id )

        wordWindow = None
        totalOccs = None
        if pageSize == None and offset == 0 :
            self.logger.log('loading complete set')
            list = []
            for c in self.concStore :
                if c.id[:c.id.rfind('_')] == id :
                    list.append(c.id)
            list.sort(lambda x, y: cmp(x[x.rfind('_')+1:],y[y.rfind('_')+1:]))
            concordance = []
            for i in list :
                string = self.concStore.fetch_document(self.session, i).get_raw(self.session)
                temp = cPickle.loads(string)
                for x, j in enumerate(temp) :
                    if x == 0 :
                        wordWindow = j[1]
                        totalOccs = j[0]
                    else :  
                        concordance.append(j)
        else :
            slice = (offset/maxSize)+1
            if (offset + pageSize)-(maxSize*slice) < maxSize : #only one slice needed
                self.logger.log('loading 1 slice')
                string = self.concStore.fetch_document(self.session, '%s_%d' % (id, slice)).get_raw(self.session)
                clines = cPickle.loads(string)
                if wordWindow == None :
                    wordWindow = clines[0][1]
                if totalOccs == None :
                    wordWindow = clines[0][0]
                concordance = clines[(offset-((slice-1)*maxSize))+1:(offset-((slice-1)*maxSize)+pageSize)+1]
            else:
                startSlice = slice
                self.logger.log('loading multiple slices')
                conc = []
                while len(conc) < offset + pageSize :
                    string = self.concStore.fetch_document(self.session, '%s_%d' % (id, slice)).get_raw(self.session)
                    temp = cPickle.loads(string)
                    for x, j in enumerate(temp) :
                        if x == 0:
                            wordWindow = j[1]
                            totalOccs = j[0]
                        else:
                            conc.append(j)
                    if len(conc) == totalOccs :
                        break
                    slice += 1                    
                concordance = conc[offset-((startSlice-1)*maxSize):offset-((startSlice-1)*maxSize)+pageSize]
        return [concordance, totalOccs, wordWindow]
        
