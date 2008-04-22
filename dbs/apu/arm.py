#!/home/cheshire/install/bin/python -i

import time, sys, os, re
osp = sys.path
sys.path = ["/home/cheshire/cheshire3/code"]
sys.path.extend(osp)

from baseObjects import Session
from server import SimpleServer
from documentFactory import SimpleDocumentFactory
from document import StringDocument
from PyZ3950.CQLParser import parse

import math, cPickle

session = Session()
session.database = 'db_guardian'
serv = SimpleServer(session, "../../configs/serverConfig.xml")
db = serv.get_object(session, 'db_guardian')

recStore = db.get_object(session, 'recordStore')
xmlp = db.get_object(session, 'LxmlParser')


filename = 'armdata1.txt'

#idx = db.get_object(session, 'sentence-idx-stem')
#idx2 = db.get_object(session, 'sentence-idx-stem-filter2')
#idx3 = db.get_object(session, 'sentence-idx-pos-single')

     
def disp_rules(rules, n): 
    for r in rules[:n]:
	print "%s --> %s  (%s%%)" % (' '.join(r[2]), ' '.join(r[3]), int(r[0]*100))


if '-arm' in sys.argv:
    
    adf = db.get_object(session, 'accDocFac')
    fimi2 = db.get_object(session, 'MagicFimiPreParser')
    rule = db.get_object(session, 'RulePreParser')
    renumber = db.get_object(session, 'VectorRenumberPreParser')
    unrenumber = db.get_object(session, 'UnRenumberPreParser')
    arm = db.get_object(session, 'ARMVectorPreParser')

    search = 1

    if search:
        print "searching"
        q = parse('c3.sentence-idx-stem exact "after"')
        #q = parse('c3.sentence-idx-stem-phrase-plus any "new*"')
        rs = db.search(session, q)    
        print "building (%s, %s)" % (len(rs), rs.totalOccs)
        for rsi in rs:
            adf.load(session, rsi, cache=0, format='vectorTransformer')

    else:
        print "building"
	maxr = 6140
	x = 0
	for rec in recStore:
            adf.load(session, rec, cache=0, format='vectorTransformer')
	    x += 1
	    if x > maxr:
		break
	    
    print "mining"
    for doc in adf:    
        print len(doc.text[0])

        doc = renumber.process_document(session, doc)
        doc = arm.process_document(session, doc)                
	out = file(filename, 'w')
	out.write(doc.get_raw(session))
	out.close()
	doc = fimi2.process_document(session, doc)

	print "post processing"
	doc = rule.process_document(session, doc)

	(fis, rules) = doc.get_raw(session)
	del doc

	rulehash = {}
	for r in rules:
	    for a in r[2]:
		try:
		    rulehash[a].append(r)
		except:
		    rulehash[a] = [r]
	    for c in r[3]:
		try:
		    rulehash[c].append(r)
		except:
		    rulehash[c] = [r]
				    
	fis.sort(key=lambda x: x.entropy)
        


if '-cached' in sys.argv:
    fimi2 = db.get_object(session, 'MagicFimiPreParser')
    rule = db.get_object(session, 'RulePreParser')
    
    f = file(filename)
    data = f.read()
    f.close()
    doc = StringDocument(data)

    print "mining"
    doc = fimi2.process_document(session, doc)

    print "post processing"
    doc2 = rule.process_document(session, doc)

    (fis, rules) = doc2.get_raw(session)
    del doc2
    fis.sort(key=lambda x: x.entropy)

    rulehash = {}
    for r in rules:
	for a in r[2]:
	    try:
		rulehash[a].append(r)
	    except:
		rulehash[a] = [r]
	for c in r[3]:
	    try:
		rulehash[c].append(r)
	    except:
		rulehash[c] = [r]

    fishash = {}
    for f in fis:
        for a in f.termids:
            try:
                fishash[a].append(f)
            except:
                fishash[a] = [f]

    fis.sort(key=lambda x: len(x.termids))

    outh = file('merged-data.txt', 'w')
    for f in fis:
        if len(f.termids) == 3:
            break
        l1 = set(fishash[f.termids[0]])
        l2 = set(fishash[f.termids[1]])

        l3 = l1.intersection(l2)
        # either find intersection, or union
        nhash = {}
        for l in l3:
            for t in l.termids:
                nhash[t] = 1

        nkeys = nhash.keys()
        if len(nkeys) > 2:
            nkeys.sort()
            outh.write("%s\n" % (' '.join(map(str, nkeys))))
    outh.close()
        


    
if '-rules' in sys.argv:
    # only works after cached or arm
    # dedupe FIS

    fis.sort(key=lambda x: x.entropy)
    fis.sort(key=lambda x: len(x.termids), reverse=True)

    fishash = {}
    for f in fis:
        for t in f.termids:
            try:
                fishash[t].append(f)
            except:
                fishash[t] = [f]
    print "deduping FIS"

    print "fis:  %s" % len(fis)
    
    start = time.time()
    done = {}
    new = []
    for f in fis:
        if len(f.termids) == 2:
            break
        if done.has_key(f):
            continue

        #fd = dict(zip(f.termids, f.termids))
        done[f] = 1
        for t in f.termids:
            ofis = fishash[t]
            for of in ofis:
                if done.has_key(of):
                    continue
                else:
                    # Check if subset
                    if len(set(f.termids).union(set(of.termids))) == len(f.termids):
                        f.merge(of)
                        done[of] = 1
                    #fd2 = fd.copy()
                    #ofd = dict(zip(of.termids, of.termids))
                    #fd2.update(ofd)
                    #if fd2 == fd:
                    #    f.merge(of)
                    #    done[of] = 1
        new.append(f)
    for f in fis:
        if not done.has_key(f):
            new.append(f)
    end = time.time() - start



if '-save' in sys.argv:
    print "saving"
    doc = new[0].document
    for n in new:
        n.document = None
    outh = file('fislist-%s.pickle' % filename, 'w')
    cPickle.dump(new, outh)
    outh.close()
    thh = file('termhash-%s.pickle' % filename, 'w')
    cPickle.dump(doc.termHash, thh)
    thh.close()
    for n in new:
        n.document = doc

if '-pickled' in sys.argv:
    print "Unpickling"
    inh = file('fislist-%s.pickle' % filename)
    new = cPickle.load(inh)
    inh.close()
    
    thh = file('termhash-%s.pickle' % filename)
    termHash = cPickle.load(thh)
    thh.close()
    
    doc = StringDocument("")
    doc.termHash = termHash

    for n in new:
        n.document = doc

if '-search' in sys.argv:
    allPhrases = []
    maxr = 2000
    mr = 0
    totalLen = 0
    totalPhr = 0
    maxLen = 0
    lens = {}
    termHash = new[0].document.termHash
    print "Searching for Phrases in Text.  New:  %s" % len(new)

    for r in new:
        mr += 1
        if mr > maxr:
            break
        if not r.phraseWeight:
            continue
        terms = ' '.join([r.document.termHash.get(x) for x in r.termids])
        try:
            q = parse('c3.sentence-idx-stem all/proxInfo "%s"' % terms)
        except:
            continue
        # print "searching: %s" % q.toCQL()
        sys.stdout.write('.')
        sys.stdout.flush()
        rs = db.search(session, q)
        phrases = []
        for rsi in rs:
            rsi.proxInfo.sort()
            rsihash = {}
            for v in rsi.proxInfo:
                (e,l,bla) = v[0]
                try:
                    rsihash[e].append(l)
                except:
                    rsihash[e] = [l]
            for (e,vals) in rsihash.iteritems():
                if len(vals) >= (len(r.termids) / 2):
                    # worth checking
                    pv = idx.fetch_proxVector(session, rsi, e)
                    pv = [(x[0], x[1]) for x in pv]
                    pvd = dict(pv)
                    # vals is sorted, start at first
                    v = 0
                    while v < len(vals):
                        startv = v
                        start = vals[v]
                        while v+1 < len(vals) and (vals[v+1] - start) <= 3:
                            v += 1
                        if start != vals[v]:
                            tids = []
                            locs = range(start, vals[v]+1)

                            # Check if just same word multiple times:
                            foundTids = []
                            for x in vals[startv:v+1]:
                                foundTids.append(pvd[x])
                            if len(set(foundTids)) == 1:
                                continue
                            if expand:
                                # look backwards for jj*, nn*
                                posvec = idx3.fetch_proxVector(session, rsi, e)
                                posvec = [(x[0], x[1]) for x in posvec]
                                posvecd = dict(posvec)
                                s = start -1
                                while posvecd.has_key(s) and posvecd[s] in [18,19,20,23,24,25,26]:
                                    try:
                                        tids.append(pvd[s])
                                    except:
                                        break
                                    s -= 1
                                tids.reverse()
                            for l in locs:
                                try:
                                    tids.append(pvd[l])
                                except:
                                    pass
                            # look forwards for nn*
                            if expand:
                                l += 1
                                while posvecd.has_key(l) and posvecd[l] in [23,24,25,26]:
                                    try:
                                        tids.append(pvd[l])
                                    except:
                                        # stoplisted for a reason
                                        break
                                    l+= 1
                            lt = len(tids)
                            if lt < 11: 
                                phrases.append(tids)
                                totalLen += lt
                                try:
                                    lens[lt] += 1
                                except:
                                    lens[lt] = 1
                                totalPhr += 1
                                if lt > maxLen:
                                    maxLen = lt
                        v += 1
        txtPhrases = []
        for p in phrases:
            phr = []
            for tid in p:
                try:
                    phr.append(termHash[tid])
                except:
                    termHash[tid] = idx.fetch_termById(session, tid)
                    phr.append(termHash[tid])
            txtPhrases.append(' '.join(phr))
        allPhrases.append((r, txtPhrases))


    flat = []
    exp = ['noExpand', 'expand'][expand]
    out = file('results/clusters-%s-%s' % (exp, filename), 'w')
    for x in allPhrases:
        flat.extend(x[1])
        out.write("RULE %s\n" % x[0])
        for p in x[1]:
            out.write('  %s\n' % p)
        out.write('\n\n')
    out.close()

    flatd = {}
    for f in flat:
        try:
            flatd[f] += 1
        except:
            flatd[f] = 1
    items = flatd.items()
    items.sort(key=lambda x: x[1])
    
    out = file('results/phrases-%s-%s' % (exp, filename), 'w')
    for i in items:
        out.write("%s\t%s\n" % i)
    out.close()
