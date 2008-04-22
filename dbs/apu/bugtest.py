# import mod_python stuffs

# import generally useful modules
import sys, os, traceback, cgitb, urllib, time, smtplib, re

# set sys paths 
databaseName = 'guardian'
cheshirePath = '/home/cheshire/cheshire3'
osp = sys.path
sys.path = [os.path.join(cheshirePath, 'cheshire3', 'code')]
sys.path.extend(osp)

# import Cheshire3/PyZ3950 stuff
from server import SimpleServer
from PyZ3950 import CQLParser, SRWDiagnostics
from baseObjects import Session
from document import StringDocument

import c3errors
# C3 web search utils
from wwwSearch import *

session = Session()
serv = SimpleServer(session, os.path.join(cheshirePath, 'cheshire3','configs','serverConfig.xml'))

session.database = 'db_' + databaseName
db = serv.get_object(session, 'db_guardian')
xmlp = db.get_object(session, 'LxmlParser')
recordStore = db.get_object(session, 'guardianRecordStore')
sentenceStore = db.get_object(session, 'sentenceRecordStore')
paragraphStore = db.get_object(session, 'paragraphRecordStore')
resultSetStore = db.get_object(session, 'guardianResultSetStore')
articleTransformer = db.get_object(session, 'article-Txr')
kwicTransformer = db.get_object(session, 'kwic-Txr')
cheshirePath = '/home/cheshire/cheshire3'
tisc = db.get_object(session, 'TISC-idx')
pisc = db.get_object(session, 'PISC-idx')
nisc = db.get_object(session, 'NISC-idx')
#query = 'c3.sentence-idx all/prox "the"'
#clause = CQLParser.parse(query)
#rs = db.search(session, clause)
#rsid = resultSetStore.create_resultSet(session, rs)
#while (True):
#    firstrec = 0
#    numreq = 20
#    result = []
#    proxList = []
#    for i in range(firstrec, min(len(rs), firstrec + numreq)):
#        rec = rs[i].fetch_record(session)
#        sax = rec.get_sax(session)
#        parent = rec.process_xpath(session, '/c3component/@parent')[0]
#        prox = rs[i].proxInfo
#        
#        j=0
#        while(j<len(prox)):
#            proxList.append(str(prox[j]))
#            proxList.append(str(prox[j+1]))
#            for e in enumerate(sax):
#                if (e[1].split()[0] == '3'):
#                    line = []
#                    text = e[1].split()[1:]
#                    temp = ' '.join(text)
#                    temp = temp.replace('\'s', ' s')
#                          
#                    text = temp.split()
#                    nodePos = prox[j+1]
#                    nodePos += text[0:nodePos+1].count('-')
#                    text[nodePos] = '<node>%s</node>' % text[nodePos]
#                    for k in range(len(text)):
#                        if ((k+1 < len(text)) and (text[k+1] == 's')):
#                            line.append('<w>%s\'%s</w>' % (text[k], text[k+1]))
#                        elif (text[k] != 's'):
#                            line.append('<w>%s</w>' % text[k])
#                    line = ' '.join(line)
#                    result.append('<line  parent="%s">%s</line>' % (parent, line))
#                resultString = '<results rsid="%s" start="%i" totalLines="%i">%s</results>' % (rsid, firstrec, rs.totalOccs,' '.join(result)) 
#                                       
#            j+=2
#                
#        proxListString = ' '.join(proxList)
#        doc = StringDocument(resultString)
#        rec = xmlp.process_document(session, doc)
#        output = kwicTransformer.process_record(session, rec)
#        
#        
#        print output.get_raw(session)

for j, i in enumerate(tisc):
    if (j<200):
        
        q = CQLParser.parse('c3.NISC-idx all "%s"' % i.queryTerm)
        n = db.scan(session,q,1, '=')
        q = CQLParser.parse('c3.PISC-idx all "%s"' % i.queryTerm)
        p = db.scan(session,q,1)
        
        print i.queryTerm, i.totalOccs,    
        
        word = p[0][0]
        if (word == i.queryTerm):
            print p[0][1][2],
        else :
            print 0,
        
        word = n[0][0]
        if (word == i.queryTerm):
            print n[0][1][2]
        else :
            print 0
        


    
#- Some stuff to do on initialisation
# Discover objects...








    
