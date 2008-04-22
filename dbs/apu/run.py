#!/home/cheshire/install/bin/python 

import time, sys, os, traceback, cgitb, urllib, smtplib, re 

osp = sys.path
sys.path = ["/home/cheshire/cheshire3/code"]
sys.path.extend(osp)

from baseObjects import Session
from server import SimpleServer
from documentFactory import SimpleDocumentFactory
from PyZ3950 import CQLParser
from document import StringDocument
from lxml import etree
from www_utils import *
import traceback
import string

session = Session()
session.database = 'db_apu'
serv = SimpleServer(session, "../../configs/serverConfig.xml")
db = serv.get_object(session, 'db_apu')


df = db.get_object(session, 'SimpleDocumentFactory')

concStore = db.get_object(session, 'concordanceStore')

recStore = db.get_object(session, 'recordStore')
ampPreP = db.get_object(session, 'AmpPreParser')
xmlp = db.get_object(session, 'LxmlParser')




if ('-load' in sys.argv):
    geniaTxr = db.get_object(session, 'corpusTransformer')
    indexWF = db.get_object(session, 'indexWorkflow')
    if len(sys.argv) < 3 :
        df.load(session)
    else :
        data = '/home/cheshire/cheshire3/dbs/apu/data/%s' % sys.argv[2]
        df.load(session, data)
    recStore.begin_storing(session)
    db.begin_indexing(session) 
    
    for d in df :
        doc = ampPreP.process_document(session, d)
        try :
            rec = xmlp.process_document(session, doc)
            genia = geniaTxr.process_record(session, rec)
            rec2 = xmlp.process_document(session, genia)
            recStore.create_record(session, rec2)
            db.add_record(session, rec2)
            indexWF.process(session, rec2)
        except:
            print 'Error'
            traceback.print_exc(file=sys.stdout)
                   
    recStore.commit_storing(session)                
    db.commit_indexing(session)
    


if ('-loadAll' in sys.argv):
    geniaTxr = db.get_object(session, 'corpusTransformer')
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
            rec2 = xmlp.process_document(session, genia)
            recStore.create_record(session, rec2)
            db.add_record(session, rec2)
            indexWF.process(session, rec2)
        except:
            print 'Error'
            traceback.print_exc(file=sys.stdout)
                   
    recStore.commit_storing(session)                
    db.commit_indexing(session)
    


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
    for i in range(0, 100):
        rec = recStore.fetch_record(session, '%d' % i)
        try :
            indexWF.process(session, rec)
        except :
            print 'Error'
          
    db.commit_indexing(session)

