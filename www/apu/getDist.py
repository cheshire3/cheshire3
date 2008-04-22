#!/home/cheshire/install/bin/python -i

import time,sys,os
osp = sys.path
sys.path = ["../../code"]
sys.path.extend(osp)

from baseObjects import Session
from server import SimpleServer
from PyZ3950.CQLParser import parse


def getDist(word, indexName):
	dist = {}
	cql = 'c3.idx-text-' + stem + ' exact ' + word
	q = parse('')
	rs = db.search(session,q)
	hits = len(rs)
	if (hits>0):
		for r in rs:
			try:
				dist[r.occurences]+=1
			except:
				dist[r.occurences]=1
	return dist

def printDist(dist):
	hits = sum(dist.values())
	for i in dist:
		print "%s,%s,%0.2f" % (i, dist[i], float(dist[i])/float(hits) * 100.0)    


def groupDist(dist):
	hits = sum(dist.values())

	occs=0
	for v in dist:
		occs += int(v) * int(dist[v])

	for i in [1,2,3]:
		print "%s\t%s\t%0.2f" % (i, dist[i], float(dist[i])/float(hits) * 100.0)    
	
	fourPlus=0
	for i in range(4,max(dist.keys())):
		try:
			fourPlus += dist[i]
		except:
			continue
	print "4+\t%s\t%0.2f" % (fourPlus, float(fourPlus)/float(hits) * 100.0)    
	
	print "\n%i occurrences in %i articles" % (occs,hits)	

session = Session()
serv = SimpleServer(session, "../../configs/serverConfig.xml")
db = serv.get_object(session, 'db_news')
session.database = 'db_news'

idxStore = db.get_object(session, 'indexStore')
recStore = db.get_object(session, 'recordStore')



