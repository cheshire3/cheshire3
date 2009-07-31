
from mod_python import apache
from mod_python.util import FieldStorage
import urlparse, httplib
import cgitb

import os, re, sys

import simplejson as json
from rdflib import ConjunctiveGraph, URIRef, StringInputSource
import uuid
from foresite import *

remMimeTypes = ['application/atom+xml', 'application/rdf+xml', 'text/rdf+n3', 'application/x-turtle', 'text/plain']

parser = RdfLibParser()
atomp = AtomParser()
rdfap = RdfAParser()


def gen_uuid():
    return str(uuid.uuid4())

class Handler(object):

    def __init__(self):
        # load up our ORE/RDF graph
        self.graph_ORE_RDF = ConjunctiveGraph()
        os.chdir('/home/cheshire/cheshire3/www/preIngest')
        f1 = file('termsPlus.rdf')
        data1 = f1.read()
        f1.close()
        self.graph_ORE_RDF.parse(StringInputSource(data1))
        
        # load up our current ORE document graph
        #self.graphCurrentResourceMap = ConjunctiveGraph()
        #f2 = file('currentExampleResourceMap.xml')
        #data2 = f2.read()
        #f2.close()
        #self.graphCurrentResourceMap.parse(StringInputSource(data2))
        
      
        # Namespaces
        myns = {}
        myns['ore'] = URIRef('http://www.openarchives.org/ore/terms/')
        myns['rdfs'] = URIRef('http://www.w3.org/2000/01/rdf-schema#')
        myns['owl'] = URIRef('http://www.w3.org/2002/07/owl#')
        myns['dcterms'] = URIRef('http://purl.org/dc/terms/')
        myns['foaf'] = URIRef('http://xmlns.com/foaf/0.1/')
        myns['dctype'] = URIRef('http://purl.org/dc/dcmitype/')
        self.ns = myns

        self.linkre = re.compile("<(.+?)>;?")
        self.relre = re.compile('rel\s?=\s?"?(resourcemap|aggregation)(["; ]|$)?')

    def send(self, data, req, code=200, ct="text/xml"):
        req.content_type = ct
        req.content_length = len(data)
        req.send_http_header()
        if type(data) == unicode:
            req.write(data.encode('utf-8'))
        else:
            req.write(data)
            
    def process(self, req):
     
        path = req.uri[15:]
	
	#Debug method (to view, see /home/cheshire/install/logs/error_log
         #sys.stderr.write(req.uri)
         #sys.stderr.flush()

        form = FieldStorage(req)

        if path == "object":
            data = self.process_object(form['uri'])
        elif path == "triples":
            data = self.process_triples(form['uri'])
        else:
            data = self.process_object(path)
            
        self.send(data, req, ct='text/plain')
        
        
    def process_object(self, name):
        if name[:7] == "http://":
            name = "<%s>" % name
        spql = "SELECT ?rel ?propType ?rng ?minCard ?maxCard ?card ?lbl WHERE { %s rdfs:subClassOf ?restr . ?restr a owl:Restriction . ?restr owl:onProperty ?rel . ?rel a ?propType . OPTIONAL { ?restr owl:minCardinality ?minCard } . OPTIONAL { ?restr owl:maxCardinality ?maxCard } . OPTIONAL { ?restr owl:cardinality ?card } . OPTIONAL { ?rel rdfs:range ?rng } . OPTIONAL { ?rel rdfs:label ?lbl } } ORDER BY ?rel"  % name
        res = self.graph_ORE_RDF.query(spql, initNs=self.ns)

        rv = []
        for (rel, propType, rng, minCard, maxCard, card, lbl) in res:
            rv.append({'rel' : rel,
                       'propType' : str(propType)[30:],
                       'range' : rng,
                       'minCard' : minCard,
                       'maxCard' : maxCard,
                       'card' : card,
                       'label' : lbl})
        return json.dumps(rv)

    def process_rem(self, uri):

        try:
            rd = ReMDocument(uri)
        except Exception, e:
            return {'exception': str(e), 'for' : uri}
        
        try:
            if rd.format == 'atom':
                rem = atomp.parse(rd)
            elif rd.format == 'rdfa':
                rem = rdfap.parse(rd)
            else:
                rem = parser.parse(rd)
        except Exception, e:
            return {'exception': str(e), 'for' : uri}

        info = {}
        info['_:uri'] = rem.aggregation.uri
        # unset exists, as we have better info
        exists = 0
        # get all predicates for aggregation
        preds = {}
        for (p,o) in rem.aggregation.graph_ORE_RDF.predicate_objects():
            try:
                preds[p].append(o)
            except KeyError:
                preds[p] = [o]
        for (k,v) in preds.iteritems():
            # should strip ore:aggregates?
            info[str(k)] = v
        return info

    def process_triples(self, uri):
        # try to find out all we can about uri
        if uri == "uuid":
            info = {'_:uri' : "urn:uuid:%s" % (gen_uuid())}
        elif uri[:7] != 'http://':
            # blank node
            info = {'_:uri' : '_:bn_' + uri}
        else:
            # fetch uri
            info = {'_:uri' : uri}
            (host, path) = urlparse.urlsplit(uri)[1:3]
            c = httplib.HTTPConnection(host)
            c.request('HEAD', path)
            resp = c.getresponse()
            # check for redirect and follow
            hdrs = resp.getheaders()
            dhdrs = dict(hdrs)
            exists = (resp.status == 200)

            if resp.status == 303:
                new = dhdrs['location']                
                if new[:7] != "http://":
                    if new[0] != '/':
                        newuri = 'http://' + host + '/' + new
                    else:
                        newuri = 'http://' + host +  new                        
                else:
                    newuri = new
                ninfo = self.process_rem(newuri)
                if not ninfo:
                    c = httplib.HTTPConnection(host)
                    c.request('HEAD', new)
                    resp = c.getresponse()
                    hdrs = resp.getheaders()
                    dhdrs = dict(hdrs)
                    exists = (resp.status == 200)
                    uri = newuri
                else:
                    info.update(ninfo)

            if dhdrs.has_key('link'):
                for (h,d) in hdrs:
                    if h == 'link':
                        relm = self.relre.search(d)
                        if relm:
                            lnkm = self.linkre.search(d)
                            lnkinfo = []
                            if relm.groups()[0] == 'aggregation':
                                info['ore:isAggregatedBy'] = lnkm.groups()[0]
                            else:
                                remuri = lnkm.groups()[0]
                                if remuri[:7] != "http://":
                                    remuri = "http://" + remuri
                                ninfo = self.process_rem(remuri)
                                info.update(ninfo)
            
            if exists:
                mime = dhdrs.get('content-type', None)
                # split into mimeType and charset
                cidx = mime.find(';')
                if cidx > -1:
                    mime = mime[:cidx]
                mime = mime.strip()
                ninfo = {}
                if mime in remMimeTypes:
                    # see if we're a ReM
                    ninfo = self.process_rem(uri)

                if ninfo:
                    info.update(ninfo)
                else:
                    info['dc:format'] = [dhdrs.get('content-type', None)]
                    info['dcterms:extent'] = [dhdrs.get('content-length', None)]
                    info['dcterms:modified'] = [dhdrs.get('last-modified', None)]


        return json.dumps(info)
        
        


hdlr = Handler()

def handler(req):
    try:
        sys.stderr.write('called python\n')
        sys.stderr.flush()
        hdlr.process(req)
    except:
        req.content_type = "text/html"
        cgitb.Hook(file=req).handle()
    return apache.OK
    
