#!/home/cheshire/install/bin/python 

import time, sys, os

osp = sys.path
sys.path = ["/home/cheshire/cheshire3/code"]
sys.path.extend(osp)

from baseObjects import Session
from server import SimpleServer
from documentFactory import SimpleDocumentFactory
from PyZ3950 import CQLParser
from document import StringDocument

session = Session()
session.database = 'db_guardian'
serv = SimpleServer(session, "../../configs/serverConfig.xml")
db = serv.get_object(session, 'db_guardian')


df = db.get_object(session, 'SimpleDocumentFactory')

concordanceStore = db.get_object(session, 'concordanceStore')
concStore = db.get_object(session, 'concStore')

recStore = db.get_object(session, 'recordStore')
ampPreP = db.get_object(session, 'AmpPreParser')
xmlp = db.get_object(session, 'LxmlParser')


if ('-load' in sys.argv):
    geniaTxr = db.get_object(session, 'geniaTransformer')
    indexWF = db.get_object(session, 'indexWorkflow')
    df.load(session)
    recStore.begin_storing(session)
    db.begin_indexing(session) 
    
    for d in df :
        doc = ampPreP.process_document(session, d)
        try :
            rec = xmlp.process_document(session, doc)
            print rec
            genia = geniaTxr.process_record(session, rec)
            print 'genia complete'
            rec2 = xmlp.process_document(session, genia)
            print 'lxml complete'
            recStore.create_record(session, rec2)
            db.add_record(session, rec2)
            print 'recordAdded'
            indexWF.process(session, rec2)
            print 'indexed'
        except:
            print 'Error'
                    
    db.commit_indexing(session)
    recStore.commit_storing(session)


if ('-indexAll' in sys.argv):
    indexWF = db.get_object(session, 'indexWorkflow')
    db.begin_indexing(session)
    for rec in recStore :
        try :
            indexWF.process(session, rec)
        except :
            print 'Error'
    db.commit_indexing(session)


if ('-index' in sys.argv):
    indexWF = db.get_object(session, 'indexWorkflow')
    db.begin_indexing(session)
    for i in range(0, 500):
        rec = recStore.fetch_record(session, '%d' % i)
        try :
            indexWF.process(session, rec)
        except :
            print 'Error'
          
    db.commit_indexing(session)

