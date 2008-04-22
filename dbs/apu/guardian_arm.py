#!/home/cheshire/install/bin/python -i

import time, sys, os, re
osp = sys.path
sys.path = ["/home/cheshire/cheshire3/code"]
sys.path.extend(osp)

from baseObjects import Session
from server import SimpleServer
from PyZ3950.CQLParser import parse

session = Session()
session.database = 'db_guardian'
serv = SimpleServer(session, "../../configs/serverConfig.xml")
db = serv.get_object(session, 'db_guardian')
resStore = db.get_object(session, 'resultSetStore')
recStore = db.get_object(session, 'recordStore')

if '-arm' in sys.argv:
    
    adf = db.get_object(session, 'accDocFac')
    fimi2 = db.get_object(session, 'MagicFimiPreParser')
    rule = db.get_object(session, 'RulePreParser')
    arm = db.get_object(session, 'ARMVectorPreParser')
    
    print "searching"
    q = parse('c3.sentence-idx any/proxinfo "today"')
    #q = parse('c3.sentence-idx-stem-phrase-plus any "new*"')
    rs = db.search(session, q)   
#    id='testarm1'
#    rs.id = id
#    resStore.begin_storing(session)
#    resStore.store_resultSet(session, rs)
#    resStore.commit_storing(session)
#    print 'stored result set'
#    rs = resStore.fetch_resultSet(session, id)
    print "building (%s, %s)" % (len(rs), rs.totalOccs)
    for rsi in rs:
        adf.load(session, rsi, cache=0, format='vectorTransformer')
    print 'adf created doc'    

    for doc in adf:
       doc2 = arm.process_document(session, doc)
       # store document here
       start =time.time()       
       doc2 = fimi2.process_document(session, doc2)
       doc2 = rule.process_document(session, doc2)
       end = time.time()
       print end - start
       
       (fis, rules) = doc2.get_raw(session) 
       
    fis.sort(key=lambda x: x.termids)
    fis.sort(key=lambda x: len(x.termids))
    
    lenHash  = {}
    for x in fis:
        try:
            lenHash[len(x.termids)].append(x)
        except:
            lenHash[len(x.termids)] = [x]
    itemHashs = []
    for l in lenHash.keys():
        nh = {}
        for x in lenHash[l]:
            for t in x.termids:
                try:
                    nh[t].append(x)
                except:
                    nh[t] = [x]
        itemHashs.append(nh)
    
        
    
    
    
    
    
    
    