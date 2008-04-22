import cPickle
import os, re

from server import SimpleServer
from document import StringDocument

from operator import itemgetter

import concordancer


cheshirePath = '/home/cheshire'



class Collocate:
    
    db = None
    serv = None
    session = None
    concStore = None
    collStore = None
    idxStore = None
    logger = None
    sortList = 0
    wordNumber = 1
      
    def __init__(self, session, logger):
        self.session = session
        session.database = 'db_apu'
        self.serv = SimpleServer(session, os.path.join(cheshirePath, 'cheshire3','configs','serverConfig.xml'))
        self.db = self.serv.get_object(session, session.database)
        self.concStore = self.db.get_object(session, 'concordanceStore')
        self.collStore = self.db.get_object(session, 'collocateStore')
        self.idxStore = self.db.get_object(session, 'indexStore')
        self.logger = logger

        
    def save_collocates(self, collocates, id):
        string = cPickle.dumps(collocates)
        doc = StringDocument(string)
        doc.id = id
        self.collStore.store_document(self.session, doc)
        self.collStore.commit_storing(self.session)
        return id
       
        
    def load_collocates(self, id):
        
        string = self.collStore.fetch_document(self.session, id).get_raw(self.session)
        wordWindow = id[id.rfind('_')+1:]
        collocates = cPickle.loads(string)
        self.logger.log(collocates)
        
        return collocates


    def create_collocateTable(self,id,window=5):
        
        def emptyList():
            return map(lambda x: int(x), list('0' * window))
        
       
        try:
            self.collStore.fetch_document(self.session, id)
        except:
        
            conc = concordancer.Concordancer(self.session, self.logger)
            
            self.logger.log('Creating collocate table')
            (conc, totalOccs, win) = conc.load_concordance(id)
            
            collocates = {}
            table = []
            
            for line in conc:
                left = line[0]
                right = line[2]
            
                for pos,w in enumerate(left[-window:][::-1]):
                    wordID = w[0]
                    try:
                        collocates[wordID][0][pos]+=1
                    except:
                        collocates[wordID]=[emptyList(),emptyList()]
                        collocates[wordID][0][pos]+=1
                         
                for pos,w in enumerate(right[0:window]):
                    wordID = w[0]
                    try:
                        collocates[wordID][1][pos]+=1
                    except:
                        collocates[wordID]=[emptyList(),emptyList()]
                        collocates[wordID][1][pos]+=1
    
    
            for i in collocates.items():
                left = list(i[1][0])
                left.reverse()
                right = list(i[1][1])
                collocates[i[0]] = [sum(i[1][0]) + sum(i[1][1]), sum(i[1][0]), sum(i[1][1]), left, right]

            self.save_collocates(collocates,id)

        return '<rsid>%s</rsid>' % id
    
    
    def get_collocateTable(self, id, sort=1, offset=0, pageSize=None):
    
        def flatten(x):
            result = []
            for el in x:
                if hasattr(el, "__iter__") and not isinstance(el, basestring):
                    result.extend(flatten(el))
                else:
                    result.append(el)
            return result
        
               
        try:
            self.collStore.fetch_document(self.session, id)
        except:
            self.create_collocateTable(id)
            
        collocates = self.load_collocates(id)
        
        idx=self.db.get_object(self.session,'%s-idx' % id.split('|')[0])
        
        # flatten collocate table structure
        colls=[]
        for i in collocates.items():
            colls.append(flatten(i))
            
        colls = sorted(colls, key=itemgetter(sort-1), reverse=True)
        collocateTable = []
 
        for l in colls:
            collocateTable.append((idx.fetch_termById(self.session,l[0]), l[1], l[2], l[3], l[4:9], l[9:]))
        
        return collocateTable
    
    

        