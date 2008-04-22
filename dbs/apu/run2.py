#!/home/cheshire/install/bin/python -i

import time, sys, os
osp = sys.path
sys.path = ["../../code"]
sys.path.extend(osp)

from baseObjects import Session
from server import SimpleServer
from documentGroup import DirectoryDocumentGroup, BigFileDocumentGroup
from document import FileDocument, StringDocument
from PyZ3950.CQLParser import parse
import random


# Build environment...
session = Session()
serv = SimpleServer(session, "../../configs/serverConfig.xml")
db = serv.get_object(session, 'db_termine')
session.database = 'db_termine'
session.server = serv
defpath = db.get_path(session, "defaultPath")

sax = db.get_object(session, 'SaxParser')
#attr = db.get_object(session, 'AttrParser')
#enju = db.get_object(session, 'EnjuTextPreParser')
#sent = db.get_object(session, 'SentenceComponentTxr')
#svo = db.get_object(session, 'SVOGroupTransformer')
if '-svo' in sys.argv:
    d = FileDocument('nhl.txt')
    d2 = enju.process_document(session, d)
    rec = sax.process_document(session, d2)
if '-index' in sys.argv:
    db.begin_indexing(session)
    for x in range(278202):
	rec = recStore.fetch_record(session, x)
	workflow.process(session, rec)
	if not x % 500:
	    print x
    db.commit_indexing(session)
    
    


if '-load' in sys.argv:
    recStore = db.get_object(session, 'recordStore')
    textXP = db.get_object(session, 'textXPath')
    exactExt = db.get_object(session, 'ExactExtractor')
    genia = db.get_object(session, 'ExactGeniaNormalizer')
    phrase = db.get_object(session, 'PosPhraseNormalizer')
    idx = db.get_object(session, 'idx-text-phrase-stem')
    idxStore = db.get_object(session, 'indexStore')

    dfp = db.get_path(session, 'defaultPath')
    print "Locating documents ..."
    dg = DirectoryDocumentGroup(dfp + "/data", "MedlineCitation")
    total = dg.get_length(session)
    print "Found: %s" % total
    db.begin_indexing(session)
    recStore.begin_storing(session)
    idxStore.begin_indexing(session, idx)

    total = 10000
    outfn = dfp + "/termineData/allfiles.genia"
    for x in range(total):
        doc = dg.get_document(session, x)
        rec = sax.process_document(session, doc)
        recStore.create_record(session, rec)
        db.add_record(session, rec)

        # doin it old skool style

        # extract abstract
        data = textXP.process_record(session, rec) # eventList
        try:
            xdata = exactExt.process_eventList(session, data[0][0]).keys()[0] # string
        except:
            continue
        # Write out extracted data to import into Termine
        try:
            fn = dfp + '/termineData/file%s.txt' % x
            f = file(fn, 'w')
            f.write(xdata.decode('utf-8'))
            f.close()
            # Run genia again as internal format is merged to other POS taggers
            # :(
            curr = os.getcwd()
            os.chdir('/home/cheshire/test/tm/geniatagger-2.0.1')
            os.system('./geniatagger < %s >> %s 2>/dev/null' % (fn, outfn))
            os.chdir(curr)
        except:
            # can't be bothered for the moment
            pass

        gdata = genia.process_string(session, xdata) # postagged
        phrases = phrase.process_string(session, gdata) # phrase hash
        # Now put into index
        idx.store_terms(session, phrases, rec)
        print "."
	
    idxStore.commit_indexing(session, idx)
    db.commit_metadata(session)
    recStore.commit_storing(session)

    # now run termine
    os.chdir(dfp)
    os.system('./termine-0.6/frontend/termine --create -F ./termine-0.6/filter.genia.txt --update-all c3termine < %s > termineResults.txt 2>/dev/null' % outfn)
