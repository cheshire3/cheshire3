# import mod_python stuffs
from mod_python import apache, Cookie
from mod_python.util import FieldStorage
# import generally useful modules
import sys, os, traceback, cgitb, urllib, time, smtplib, re
#import cheshire3 stuff
from record import LxmlRecord
from lxml import etree


# set sys paths 
databaseName = 'apu'
cheshirePath = '/home/cheshire'
osp = sys.path
sys.path = [os.path.join(cheshirePath, 'cheshire3', 'code')]
sys.path.extend(osp)

# list of subcorpora indexes
subcorpora = ['taskOne','taskTwo','taskFour','taskFive','taskSix']



# import Cheshire3/PyZ3950 stuff
from server import SimpleServer
from PyZ3950 import CQLParser, SRWDiagnostics
from baseObjects import Session
from document import StringDocument
from  xml.sax.saxutils import escape
from concordancer import *
from collocate import *
import cPickle
import c3errors
import string
from utils import flattenTexts
# C3 web search utils
from www_utils import *

import lxml.etree as etree
from record import LxmlRecord

class SearchHandler:
    
    htmlPath = cheshirePath + '/cheshire3/www/%s/html' % databaseName
    txtStorePath = cheshirePath + '/cheshire3/www/%s/txt' % databaseName
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
        
    def sort(self, form):
        id = form.get('id', None)
        side = form.get('side', 'left')
        wordNumber = form.get('wordNumber', 1)
        concordancer = Concordancer(session, self.logger)
        id = concordancer.sort_concordance(id, side, wordNumber)       
        return '<rsid>%s</rsid>' % id

    def filter(self, form):
        self.logger.log('requesting filter')
        id = form.get('id', None)
        matchList = form.get('matchlist', None)
        self.logger.log(matchList)
        concordancer = Concordancer(session, self.logger)
        id = concordancer.filter_concordance(id, matchList)       
        return '<rsid>%s</rsid>' % id


    def search(self, req):
        global db, idxStore, resultSetStore
      
        self.logger.log('search called')
        start = time.time()
        form = FieldStorage(req)
        type = form.get('type', None)
        terms = form.get('terms', None)        
        id = form.get('id', None)    
        span = int(form.get('span', 0))
        wordWindow = int(form.get('windowsize', 10))
        gid = form.get('gid', None)
        if (id != None):
            # remove the 'kwic_grid_' that comes from LiveGrid id 
            self.logger.log('ID SUPPLIED DISPLAYING LINES') 
            id = id[10:]        
            start = int(form.get('offset', 0))
            howmany = int(form.get('page_size',100))            
            return self.kwicDisplay(id, start, howmany)
        elif (gid != None):
            start = int(form.get('offset', 0))
            howmany = int(form.get('page_size',100))            
            return self.kwicDisplay(gid, start, howmany)                   
        else:            
            if (terms == None):
                self.logger.log('no terms') 
               
            id = '%s|%s|%s|%d|%d' % (form.get('context', None), type, multiReplace(terms, {' ' : '_', '<' : '(', '>' : ')'}), span, wordWindow) 
            try :
                rs = resultSetStore.fetch_resultSet(session, id)
            except:      
                (queryString, idx) = self.build_query(id) 
                                          
                query = CQLParser.parse(queryString)
                (mins, secs) = divmod(time.time()-start, 60)
                self.logger.log('%s\nquery parsed: %s' % (queryString, secs))
                rs = db.search(session, query)
                
                (mins, secs) = divmod(time.time()-start, 60)
                self.logger.log('db searched: %s' % secs)
                
                #Save ResultSet
                resultSetStore.begin_storing(session)
                rs.id = id                   
                resultSetStore.store_resultSet(session, rs)
                resultSetStore.commit_storing(session) 
            try:
                totalOccs = rs.totalOccs
            except:
                totalOccs = 'unavailable'
            if totalOccs == 0:
                totalOccs = 'unavailable' 
          
            (mins, secs) = divmod(time.time()-start, 60)
            (hours, mins) = divmod(mins, 60) 
            self.logger.log('search complete: %s:%s:%s' % (hours, mins, secs))
            output = '<results><rsid>%s</rsid><totalDocs>%i</totalDocs><totalOccs>%s</totalOccs></results>' % (id, len(rs), str(totalOccs))        
        return output
   
   
    def build_query(self, id):
        global syntaxRe
        self.logger.log('building query')
        start = time.time()
        idArray = id.split('|')
        context = idArray[0]
        type = idArray[1]
        terms = idArray[2].replace('_', ' ')
        span = idArray[3]
        if (context == 'article'):
            idx = 'c3.article-idx'
        elif (context == 'paragraph'):
            idx = 'c3.paragraph-idx'
        elif (context == 'sentence'):
            idx = 'c3.sentence-idx'
        elif (context in subcorpora):
            idx = 'c3.%s-idx' % context
        elif (context == 'window'):
            idx = 'c3.article-idx'
        
        if context == 'window':
            queryString = '%s window/proxinfo/distance<%s "%s"' % (idx, span, terms)
                
        elif (type == 'all'):
            if terms.find('{') == -1 and terms.find('[') == -1 and terms.find('(') == -1 and len(terms.split(' ')) == 1  :
                #queryString = '%s all/proxinfo "%s"' % (idx, terms)
                termArray = terms.split(' ')
                queryList = []
                for t in termArray:
                    queryList.append('%s all/proxinfo "%s"' % (idx, t))
                queryString = ' prox/distance>0/unit=word '.join(queryList)
            else :
                iter = syntaxRe.finditer(terms)
                queryList = []
                for i in iter:
                    if i.group() != '':
                        termSet = i.group()
                        if termSet[0] == '[' :
                            queryList.append('%s-stem any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind(']')]))
                        elif termSet[0] == '(' :
                            queryList.append('%s-pos any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind(')')]))
                        elif termSet[0] == '{' :
                            queryList.append('%s any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind('}')]))
                        else :
                            queryList.append('%s any/proxinfo "%s"' % (idx, termSet))
                queryString = ' prox/distance>0/unit=word '.join(queryList)        
        else :
            if (type == 'phrase'):
                if terms.find('{') == -1 and terms.find('[') == -1 and terms.find('(') == -1 :
                    queryString = '%s =/proxinfo "%s"' % (idx, terms)
                else :
                    iter = syntaxRe.finditer(terms)
                    queryList = []
                    for i in iter:
                        if i.group() != '':
                            termSet = i.group()
                            if termSet[0] == '[' :
                                queryList.append('%s-stem any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind(']')]))
                            elif termSet[0] == '(' :
                                queryList.append('%s-pos any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind(')')]))
                            elif termSet[0] == '{' :
                                queryList.append('%s any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind('}')]))
                            else :
                                queryList.append('%s any/proxinfo "%s"' % (idx, termSet))
                    queryString = ' prox/distance=1/unit=word/ordered '.join(queryList)                             
            elif (type == 'any'):
                if terms.find('{') == -1 and terms.find('[') == -1 and terms.find('(') == -1 :
                    queryString = '%s any/proxinfo "%s"' % (idx, terms)
                else :
                    iter = syntaxRe.finditer(terms)
                    queryList = []
                    for i in iter:
                        if i.group() != '':
                            termSet = i.group()
                            if termSet[0] == '[' :
                                queryList.append('%s-stem any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind(']')]))
                            elif termSet[0] == '(' :
                                queryList.append('%s-pos any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind(')')]))
                            elif termSet[0] == '{' :
                                queryList.append('%s any/proxinfo "%s"' % (idx, termSet[1:termSet.rfind('}')]))
                            else :
                                queryList.append('%s any/proxinfo "%s"' % (idx, termSet))
                    queryString = ' or '.join(queryList)
                      
 #to do this doesn't need to return idx any more               
        return [queryString, idx]
    
    
    def kwicDisplay(self, id, start=0, nRecs=100):
        self.logger.log('displaying kwiclines')
        result = []
        extraSpaceElems = ['s', 'lead']
        replhash = { '.' : ''
                    , '"' : ''
                    , ',' : ''
                    , "'" : ''  
                    , "&" : ''                  
                    }

        count = start;
        concordancer = Concordancer(session, self.logger)
        temp = concordancer.load_concordance(id, start, nRecs)
        concordance = temp[0]
        totalOccs = temp[1]
        wordWindow = temp[2]
        
        #this isn't needed now - change to just display whatever it gets concordance does sorting out what
        for i in range(0, len(concordance)):
            count += 1;
            recStore = concordance[i][3][0]
            recid = concordance[i][3][1]           
            context = concordance[i][3][2]
            rsPage = concordance[i][3][3]
            rec = recordStore.fetch_record(session, recid)
            nodeIdxs = []
            wordOffsets = []
            for x in concordance[i][4]:
                nodeIdxs.append(x[0])
                wordOffsets.append(x[1])        
                
            #get the paragraph/sentence/article with eid that matches
            tree = rec.dom.getroottree()
            if context == 'article' :
                node = tree.xpath('//body')[0]
            elif context == 'HISC' :
                node = tree.xpath('//body/headline')[0]
            else :
                node = tree.xpath('//*[@eid=%s]' % nodeIdxs[0])[0]
    
            walker = node.getiterator()
            texts = []
            for c in walker:
                if c.tag == 'txt':                        
                    if c.text:
                        texts.append(c.text)                        
                    if c.tail:
                        texts.append(c.tail)
    
                elif c.tag in extraSpaceElems :
                    texts.append(' ')
                else :
                    continue
            text = ''.join(texts).lstrip()          
            for j in range(0, len(wordOffsets)) :
                space = False
                while not space and wordOffsets[j] > 0 :
                    if text[wordOffsets[j]-1] in string.punctuation :
                        wordOffsets[j] = wordOffsets[j]-1
                    else :
                        space = True;
                          
            if wordOffsets[1] > wordOffsets[0]:
                left = text[wordOffsets[0]:wordOffsets[1]]
                newleft = []
                left = left[::-1]
                
                for w in left.split(' '):
                    #newleft.append("&lt;span onclick=\"getCFP('%s')\"> &#x202E;%s&#x202C;&lt;/span>" % (multiReplace(w[::-1], replhash), w))                   
                    newleft.append("&lt;span onclick=\"getCFP)'%s'(\">&#x202E;%s&#x202C; &lt;/span>" % (multiReplace(w[::-1], replhash), w))                   
            
                left = ' '.join(newleft)
                #check this works for []
                left = multiReplace(left, {']' : ']]', ')' : '))', '}':'}}', '& ' : 'amp; '})
                left = multiReplace(left, {'[' : ']', '(' : ')', '{' : '}'})
                left = multiReplace(left, {']]' : '[', '))' : '(', '}}' : '{'})
                
            else :
                left = ''
                
            if wordOffsets[2]>wordOffsets[1] :
                right = text[wordOffsets[2]:wordOffsets[3]]
                newright = []
                for w in right.split(' '):
                    newright.append("&lt;span onclick=\"getCFP('%s')\">%s&lt;/span>" % (multiReplace(w, replhash), w))
                 
                right = ' '.join(newright)
                key = text[wordOffsets[1]:wordOffsets[2]]
            else :
                right = ''
                key = text[wordOffsets[1]:]
        
            keyTagged = (left + '</td><td> ' + key + ' </td><td> ' + right)
#            result.append('<tr><td>&lt;a href="/apu/search?operation=search&amp;mode=article&amp;parent=%d&amp;elem=%d&amp;os1=%d&amp;os2=%d" target="_article">%d&lt;/a></td><td> %s</td></tr>' % (recid, nodeIdxs[0], max(wordOffsets[1], -1), max(wordOffsets[2], -1), count, keyTagged))
            result.append('<tr><td>&lt;a href="javascript:displayArticle(\'%s\', %d, %d, \'%s\')">%d&lt;/a></td><td> %s</td></tr>' % (id, rsPage, nodeIdxs[0], '_'.join([str(x[1]) for x in  concordance[i][1]]), count, keyTagged))
        
           # keyTagged = (left + '&#x202C; </td><td> ' + key + ' </td><td> ' + right)
           # result.append('<tr><td>&lt;a href="/apu/search?operation=search&amp;mode=article&amp;parent=%d&amp;elem=%d&amp;os1=%d&amp;os2=%d" target="_article">%d&lt;/a></td><td> &#x202E; %s</td></tr>' % (recid, nodeIdxs[0], max(wordOffsets[1], -1), max(wordOffsets[2], -1), count, keyTagged))
        resultString = '<ajax-response><response type="object" id="%s"><rows update_ui="true">%s</rows></response></ajax-response>' % (id, ' '.join(result))
        return resultString 



    def concordance(self, form):
        id = form.get('id', None)
        concordance = Concordancer(session, self.logger)
        (lines, table) = concordance.create_concordance(id)
        if table == '':
            return '<xml><lines>%s</lines></xml>' % lines
        else :
            return '<xml><lines>%s</lines>%s</xml>' % (lines, table)
        
        

    def collocates(self, form):
		id = form.get('id', None)
		gid = form.get('gid', None)
		start = int(form.get('offset', 0))
		howmany = int(form.get('page_size',50))
		
		# sort params from LiveGrid come in the form
		# 's1: ASC' or 's5: ASC' - with num = to column in table
		sort = re.compile('^s\d+')
		sortList = filter(lambda x: sort.match(x), form.keys())
		
		sortby = int(len(sortList)>0 and sortList[0][1:] or 3)
		sortdir = form.get('sort_dir','desc')
		self.logger.log('IN COLLOCATES Function %s' % id)

		if id!=None:
			# remove the 'collocate_grid_' that comes from LiveGrid id         
			id = id[15:]    
		    
			coll = Collocate(session,self.logger)
			return self.collocatesDisplay(id,coll.get_collocateTable(id,sortby),start,howmany,sortby)	
		elif gid != None:
			coll = Collocate(session,self.logger)
			collocateId = coll.create_collocateTable(gid)
			return collocateId
		else:
			return '<error>No concordance object with id: %s</error>' % id



    def collocatesDisplay(self, id, collocates,start=0, numRows=10, sortby=1):
		lines = []
		
		for n in range(start, min(len(collocates), start + numRows)):
			l = collocates[n]
			left = "<td>%s</td>" % ('</td><td>'.join(map(lambda x: str(x), l[4])))
			right = "<td>%s</td>" % ('</td><td>'.join(map(lambda x: str(x), l[5])))
			lines.append('<tr><td>%i</td><td>%s</td><td>%i</td><td>%i</td><td>%i</td>%s%s</tr>' % (n+1,l[0],l[1],l[2],l[3],left,right))
		
		resultString = '<ajax-response><response type="object" id="%s"><rows update_ui="true">%s</rows></response></ajax-response>' % (id, ' '.join(lines))
		return resultString
    
    
    
    def create_cfp(self, form):
        term = string.lower(form.get('term', None).value)
        q = CQLParser.parse('c3.sentence-idx any "%s"' % term)
        output = []
        for i in subcorpora :
            output.append('<tr>')
            output.append('<td>%s</td>' % i)
            idx = db.get_object(session, '%s-idx' % i)
            total = float(idx.fetch_metadata(session)['nOccs'])
            entry = idx.scan(session, q, 1, '=')
            if entry[0][0] == term:
                perc = round(float(entry[0][1][2]*10000.00)/total, 2)
                output.append('<td>%0.2f</td>' % perc)
            else:
                output.append('<td>0</td>')
            output.append('</tr>')
        return '<table><th>subcorpus</th><th>total occs</th>%s</table>' % ''.join(output)
        
    
#    def articleDisplay(self, req):
#        form = FieldStorage(req)
#        parent = form.get('parent', None)
#        elem = form.get('elem','')
#        os1 = form.get('os1','')
#        os2 = form.get('os2','')
#        highlight = etree.fromstring("<highlight><elem>%s</elem><os1>%s</os1><os2>%s</os2></highlight>" % (elem,os1,os2))
#        rec = recordStore.fetch_record(session, parent)
#        et = etree.fromstring(rec.get_xml(session))
#        et.append(highlight)
#        rec = LxmlRecord(et)
#        doc = articleTransformer.process_record(session, rec)
#        output = doc.get_raw(session)
#        return '<html><head></head><body><p>%s</p></body></html>' % output
#    


    def articleDisplay(self, form):
        self.logger.log('ARTICLE DISPLAY REQUESTED')
        page = int(form.get('page', 1))-1
        id = form.get('id', None)
        elem = form.get('elem', '')
        words = form.get('words', '').split('_')
        context = form.get('id', '').split('|')[0]
        rs = resultSetStore.fetch_resultSet(session, id)
        rec = rs[page].fetch_record(session)
        #rec = recordStore.fetch_record(session, parent)
        tree = rec.dom.getroottree()
        if context == 'article' or context == 'window':
            baseXPath = '//body/descendant::w[WOFFSET]'
        elif context == 'HISC':
            baseXPath = '/article/body/headline/descendant::w[WOFFSET]'
            el = tree.xpath('/article/body/headline')[0]
            el.set('highlight', 'true')
        else :
            baseXPath = '//*[@eid=%s]/descendant::w[WOFFSET]' % elem
            el = tree.xpath('//*[@eid=%s]' % elem)[0]
            el.set('highlight', 'true')
        for w in words :
            word = tree.xpath(baseXPath.replace('WOFFSET', str(int(w)+1)))[0]
            word.set('inv', 'node')       
        return '<html><head></head><body><p>%s</p></body></html>' % articleTransformer.process_record(session, rec).get_raw(session)

    
    def articleBrowse(self, form):
        id = form.get('id', None)
        context = id.split('|')[0]
        type=id.split('|')[1]
        page = int(form.get('page', 1))-1
        rs = resultSetStore.fetch_resultSet(session, id)
        proxInfo = rs[page].proxInfo
        rec = rs[page].fetch_record(session)
        tree = rec.dom.getroottree()
        if context == 'article' or context == 'window':
            baseXPath = '//body/descendant::w[WOFFSET]'
        elif context == 'HISC':
            baseXPath = '//headline/descendant::w[WOFFSET]'
        else :
            baseXPath = '//*[@eid=EIDVALUE]/descendant::w[WOFFSET]'
        for m in rs[page].proxInfo :
            if type == 'phrase' or type == 'any' and context != 'window':
                for p in m:
                    word = tree.xpath(multiReplace(baseXPath, {'EIDVALUE' : p[0], 'WOFFSET' : p[1]+1}))[0]
                    word.set('inv', 'node')
            elif type == 'all' or context == 'window':
                word = tree.xpath(multiReplace(baseXPath, {'EIDVALUE' : m[0][0], 'WOFFSET' : m[0][1]+1}))[0]
                word.set('inv', 'node')
                for i in range(1, len(m)):
                    word = tree.xpath(multiReplace(baseXPath, {'EIDVALUE' : m[i][0], 'WOFFSET' : m[i][1]+1}))[0]
                    word.set('inv', 'other')
        return '<html><head></head><body><p>%s</p></body></html>' % articleTransformer.process_record(session, rec).get_raw(session)

    
    def arm(self, form):
        id = form.get('id', 'test')
        vecTxr.vectorIndex = db.get_object(session, '%s-idx' % id.split('|')[0])
        self.logger.log(vecTxr.vectorIndex)
        if id.split('|')[1] == 'any' and id.find('_') != -1 :
            vecTxr.stripMatch = 0
        else :
            vecTxr.stripMatch = 1    
        try :
            doc2 = vectorStore.fetch_document(session, id)
        except:
            (qs, idx) = self.build_query(id)                       
            q = CQLParser.parse(qs)
            rs = db.search(session, q)   
            for rsi in rs: 
                adf.load(session, rsi, cache=0, format='vectorTransformer')
            for doc in adf:
                doc2 = arm.process_document(session, doc)
                doc2.id = id    
                vectorStore.store_document(session, doc2)
                vectorStore.commit_storing(session)
        return '<rsid>%s</rsid>' % id
        
        
    
    def armTable(self, form):
 #       global vectorStore, arm, fimi2, rule
        id = form.get('id', 'test')     
        rule.index = db.get_object(session, '%s-idx' % id.split('|')[0])   
        try :
            doc2 = vectorStore.fetch_document(session, id)
        except : 
            (qs, idx) = self.build_query(id)                       
            q = CQLParser.parse(qs)
            rs = db.search(session, q)
    #        rs = resultSetStore.fetch_resultSet(session, id)       
            for rsi in rs: 
                adf.load(session, rsi, cache=0, format='vectorTransformer')
            for doc in adf:
                doc2 = arm.process_document(session, doc)
                self.logger.log('ARM process complete')              
                doc2.id = id
                vectorStore.store_document(session, doc2)
                vectorStore.commit_storing(session)
                try :
                    doc2 = fimi2.process_document(session, doc2)
                except :
                    pass
                try:
                    doc2 = rule.process_document(session, doc2)
                except:
                    pass
                (fis, rules) = doc2.get_raw(session)
                output = [] 
                count = 0
                for f in fis:
                    output.append(f.toXml())
                output = '<fis>%s</fis>' % ' '.join(output)
                rec = LxmlRecord(etree.fromstring(output))
                doc = armTableTxr.process_record(session, rec)
        else :
            try :
                doc2 = fimi2.process_document(session, doc2)
            except :
                pass
            try:
                doc2 = rule.process_document(session, doc2)
            except:
                pass
            (fis, rules) = doc2.get_raw(session)
            output = [] 
            count = 0
            for f in fis:
                output.append(f.toXml())
            output = '<fis>%s</fis>' % ' '.join(output)
            rec = LxmlRecord(etree.fromstring(output))
            doc = armTableTxr.process_record(session, rec)
        return '<rsid>%s</rsid>' % doc.get_raw(session).replace('%%ID%%', id)
   
    
    
    def handle(self, req):
        form = FieldStorage(req)        
        mode = form.get('mode', None)
        if (mode=='search'):
            page = self.search(req)
            self.send_xml(page,req)
        elif (mode=='collocates'):
        	page = self.collocates(form)
        	self.send_xml(page,req)
        elif (mode == 'concordance'):
            page = self.concordance(form)
            self.send_xml(page, req)
        elif (mode=='arm'):
            page = self.arm(form)
            self.send_xml(page,req)
        elif (mode=='armtable'):
            page = self.armTable(form)
            self.send_xml(page,req)
        elif (mode=='article'):
            page = self.articleDisplay(form)
            self.send_html(page, req)
        elif (mode=='browse'):
            page = self.articleBrowse(form)
            self.send_html(page, req)
        elif (mode=='sort'):
            page = self.sort(form)
            self.send_xml(page, req)
        elif (mode=='filter'):
            page = self.filter(form)
            self.send_xml(page, req)
        elif (mode=='cfp'):
            page = self.create_cfp(form)
            self.send_xml(page, req)
        else :
            page = read_file('search.html')
            self.send_html(page, req)
        # send the display
        
#    
##- Some stuff to do on initialisation
#rebuild = True
#serv = None
#session = None
#db = None
#xmlp = None
#recordStore = None
#sentenceStore = None
#paragraphStore = None
#resultSetStore = None
#articleTransformer = None
#kwicTransformer = None
#
punctuationRe = re.compile('([@+=;!?:*"{}()\[\]\~/\\|\#\&\^]|[-.,\'](?=\s+)|(?<=\s)[-.,\'])')   # this busts when there are accented chars
wordRe = re.compile('\s*\S+')
syntaxRe = re.compile('[\w]* |[\w]*$|[[(][ ]?[\w]*[ ]?[])][\s$]?|{[\w\s]+}[\s$]?')
#
#cheshirePath = '/home/cheshire/cheshire3'    
#logPath = os.path.join(cheshirePath, 'cheshire3', 'www', databaseName, 'logs', 'searchHandler.log')
#htmlPath = os.path.join(cheshirePath, 'cheshire3', 'www', databaseName, 'html')


def build_architecture(data=None):
    global session, serv, db, xmlp, recordStore, resultSetStore, idxStore, articleTransformer, kwicTransformer, proxExtractor, simpleExtractor, adf, fimi2, rule, arm, vecTxr, vectorStore, armTableTxr
    session = Session()
    session.environment = 'apache'
    session.user = None
    serv = SimpleServer(session, os.path.join(cheshirePath, 'cheshire3','configs','serverConfig.xml'))
    
    session.database = 'db_' + databaseName
    db = serv.get_object(session, session.database)
    xmlp = db.get_object(session, 'LxmlParser')
    recordStore = db.get_object(session, 'recordStore')
    resultSetStore = db.get_object(session, 'resultSetStore')
    
    simpleExtractor = db.get_object(session, 'SimpleExtractor')
    proxExtractor = db.get_object(session, 'ProxExtractor')
    articleTransformer = db.get_object(session, 'article-Txr')
    kwicTransformer = db.get_object(session, 'kwic-Txr')
    idxStore = db.get_object(session, 'indexStore')
    
    #adf = db.get_object(session, 'accDocFac')
    #fimi2 = db.get_object(session, 'MagicFimiPreParser')
    #rule = db.get_object(session, 'RulePreParser')
    #arm = db.get_object(session, 'ARMVectorPreParser')
    #vecTxr = db.get_object(session, 'Vector1Txr')
    #vectorStore = db.get_object(session, 'vectorStore')
    
    #armTableTxr = db.get_object(session, 'armTable-Txr')
# Discover objects...
#def handler(req):
#    global db, htmlPath, logPath, cheshirePath, xmlp, recordStore
#    try:
#        try:
#            fp = recordStore.get_path(session, 'databasePath')
#            assert (rebuild)
#            assert (os.path.exists(fp) and time.time() - os.start(fp).st_mtime > 60*60)
#        except :
#            build_architecture()
#            
#        remote_host = req.get_remote_host(apache.REMOTE_NOLOOKUP)     # get the remote host's IP for logging
#        os.chdir(htmlPath)                                            # cd to where html fragments are
#        lgr = FileLogger(logPath, remote_host)                        # initialise logger object
#        searchHandler = SearchHandler(lgr)                            # initialise handler - with logger for this request
#        try:
#            searchHandler.handle(req)                                 # handle request
#        finally:
#            # clean-up
#            try: lgr.flush()                                          # flush all logged strings to disk
#            except: pass
#            del lgr, searchHandler                                    # delete handler to ensure no state info is retained
#    except:
#        req.content_type = "text/html"
#        cgitb.Hook(file = req).handle()                               # give error info
#    else:
#        return apache.OK
    
#- end handler()