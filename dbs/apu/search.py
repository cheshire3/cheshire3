# first attempt at search script for ead cheshire database



import sys, re
# adds the path to code to the PYTHONPATH list so that it can find the modules based in Cheshire
osp = sys.path
sys.path = ["/home/cheshire/cheshire3/cheshire3/code"]
sys.path.extend(osp)

# imports the relevant python modules from Cheshire
from server import SimpleServer
from PyZ3950 import CQLParser
from baseObjects import Session

#gets the current session
session = Session()
serv = SimpleServer(session, "../../configs/serverConfig.xml")
session.database = 'db_guardian'
db = serv.get_object(session, 'db_guardian')
recordStore = db.get_object(session, 'sentenceRecordStore')
txr = db.get_object(session, 'headlines-Txr')

searchFlag = True
concordanceFlag = False

query = 'c3.sentence-idx all/proxinfo "hearing"'
#query = 'c3.content-idx =/proxinfo "over" prox/distance=1/ordered/proxinfo c3.content-idx =/proxinfo "barrel"'
#query = 'c3.headline-keyword-idx all/relevance/proxinfo "report"'
#query = 'c3.2gram-idx any "t a"'
clause = CQLParser.parse(query)
span = 10
#search
if (searchFlag):
    punctuationRe = re.compile('([@+=;!?:*"{}()\[\]\~/\\|\#\&\^]|[-.,\'](?=\s+)|(?<=\s)[-.,\'])')
    rs = db.search(session, clause)
    hits = len(rs)
    print hits, rs.totalOccs
    rs.scale_weights
    for i, r in enumerate(rs):
        if i > 5:
            break
        rec = r.fetch_record(session)
        relv = int(rs[i].scaledWeight*100)
        prox = rs[i].proxInfo
        sax = rec.get_sax(session)
        print prox
        if (concordanceFlag):
            j=0
            while (j < len(prox)):
                begin = int(prox[j])
                end = int(sax[prox[j]].split()[-1])
                events = sax[begin:end]
                keyWordPos = prox[j+1]
                for k, e in enumerate(events):
                    if (e[0] == "3"):
                        spaced = punctuationRe.sub(' ', e[1:])       
                        spaced = spaced.replace('\'s', ' s')    
                        words = spaced.split()
                        x = keyWordPos-span  
                        if (x<0):
                            x=0
                        while x < keyWordPos+(span+1) and x < len(words):
                            if (x+1 < len(words) and words[x+1] == 's'):
                                print "%s'%s" % (words[x], words[x+1]),
                                x += 2
                            elif (x == keyWordPos):
                                print "--- %s ---" % words[x],
                                x += 1
                            else :
                                print words[x],                       
                                x += 1
                        print 
                j = j+2
    
            relvStr = str(relv) + "%"
            doc = txr.process_record(session, rec)
            output = doc.get_raw(session)
            output = output.replace('%RELV%', relvStr)
        
        else:
            print prox
            j=0
            while (j < len(prox)):
                begin = int(prox[j])
                #print begin
                end = int(sax[prox[j]].split()[-1])
                #print end
                events = sax[begin:end]
                keyWordPos = prox[j+1]
                #print keyWordPos
                #print len(events)
                flag = True
                for k, e in enumerate(events):
                    if (e[0] == "3"):
                        #print e
                        spaced = punctuationRe.sub(' ', e[1:])       
                        spaced = spaced.replace('\'s', ' s')    
                        words = spaced.split()
                      #  print len(words)
                        #hit = words[keyWordPos]
                        
                        #print hit
                j=j+2


#scan
else :
   termList = db.scan(session, clause, 50, ">=")
   print db.totalItems

   for t in termList:
       print t
#       
# record = recordStore.fetch_record(session, 0)
#Traceback (most recent call last):
#  File "<stdin>", line 1, in <module>
#NameError: name 'recordStore' is not defined
#>>> record = guardianRecordStore.fetch_record(session, 0)
#Traceback (most recent call last):
#  File "<stdin>", line 1, in <module>
#NameError: name 'guardianRecordStore' is not defined
#>>> rs = db.get_object(session, 'guardianRecordStore')
#>>> r = rs.fetch_record(session, 0)
#>>> print r
#guardianRecordStore/0
#>>> e=db.get_object(session, 'NGramExtractor')
#>>> e
#<extractor.NGramExtractor object at 0x92a8c4c>
#>>> e.process_eventList(session, r.process_xpath(session, 'head/headline'))
#{}
#>>> e.process_eventList(session, r.process_xpath(session, 'head/headline')[0])
#      
       