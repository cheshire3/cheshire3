
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
      
        # Namespaces        
        self.ns = self.get_namespaces()

        self.linkre = re.compile("<(.+?)>;?")
        self.relre = re.compile('rel\s?=\s?"?(resourcemap|aggregation)(["; ]|$)?')
    
    def get_namespaces(self):
        myns = {}
        myns['foaf'] = URIRef('http://xmlns.com/foaf/0.1/')
        myns['dcterms'] = URIRef('http://purl.org/dc/terms/')
        myns['bibo'] = URIRef('http://purl.org/ontology/bibo/')
        myns['pms'] = URIRef('http://id.loc.gov/standards/premis/rdf/')
        myns['dc'] = URIRef('http://purl.org/dc/elements/1.1/')
        myns['rdf'] = URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        myns['ore'] = URIRef('http://www.openarchives.org/ore/terms/')
        myns['rdfs'] = URIRef('http://www.w3.org/2000/01/rdf-schema#')
        myns['owl'] = URIRef('http://www.w3.org/2002/07/owl#')       
        myns['dctype'] = URIRef('http://purl.org/dc/dcmitype/')
        return myns

    def send(self, data, req, code=200, ct="text/xml"):
        req.content_type = ct
        req.content_length = len(data)
        req.send_http_header()
        if type(data) == unicode:
            req.write(data.encode('utf-8'))
        else:
            req.write(data)

    def getRDFTypeFromIdentifier(self, rdfIdentifier):
        spql = "SELECT ?rdfType WHERE { %s a ?rdfType }"  % rdfIdentifier
        res = self.graph_ORE_RDF.query(spql, initNs=self.ns)

        for (rdfType) in res:
            return rdfType[0]
            
    def process(self, req):
        form = FieldStorage(req)
        query_type = req.uri[18:26] 
        rdf_id = req.uri[27:]
        rdf_type = self.getRDFTypeFromIdentifier(rdf_id)
        
        if query_type == "children":
            if rdf_type.strip() == "http://www.w3.org/2002/07/owl#Class":
                data = self.process_class_children_query(rdf_id)
            elif rdf_type.strip() == "http://www.w3.org/2002/07/owl#ObjectProperty":
                data = self.process_object_property_children_query()
            else:
                data = rdftype + ' is not processed by this script' 
        elif  query_type == 'nodeInfo':
            if rdf_type.strip() == "http://www.w3.org/2002/07/owl#Class":
                data = self.process_class_nodeinfo_query(rdf_id)
            elif rdf_type.strip() == "http://www.w3.org/2002/07/owl#ObjectProperty":
                data = self.process_object_property_nodeinfo_query(rdf_id)
            else:
                data = rdf_type + ' is not processed by this script'
        else:
            data = query_type + ' is not processed by this script' 
           

        #Not yet used, but here is the call example:
        #data = self.process_triples(form['uri'])

        self.send(data, req, ct='text/plain')
        
    def process_class_children_query(self, name):
        spql = "SELECT ?rel ?propType ?rng ?minCard ?maxCard ?card ?lbl ?comment WHERE { %s rdfs:subClassOf ?restr . ?restr a owl:Restriction . ?restr owl:onProperty ?rel . ?rel a ?propType . OPTIONAL { ?restr owl:minCardinality ?minCard } . OPTIONAL { ?restr owl:maxCardinality ?maxCard } . OPTIONAL { ?restr owl:cardinality ?card } . OPTIONAL { ?rel rdfs:range ?rng } . OPTIONAL { ?rel rdfs:label ?lbl } . OPTIONAL {?rel rdfs:comment ?comment} } ORDER BY ?rel"  % name
        res = self.graph_ORE_RDF.query(spql, initNs=self.ns)

        rv = []
        for (   rel, propType, rng, minCard, maxCard, card, lbl, comment) in res:
                if rng:
                    rng = self.getNamespaceAndLabelFromURI(rng)
                rv.append({ 'rel' : rel,
                            'propType' : str(propType)[30:],
                            'range' : rng,
                            'minCard' : minCard,
                            'maxCard' : maxCard,
                            'card' : card,
                            #'label' : lbl --> lbl is not always present so unreliable.
                            'nsLabel' : self.getNamespaceAndLabelFromURI(rel),
                            'label' : self.getRDFSLabelFromURI(rel),
                            'comment' : comment})
        return json.dumps(rv)

    def process_object_property_children_query(self):
        spql = "SELECT ?className ?lbl ?comment WHERE { ?className a owl:Class . OPTIONAL { ?className rdfs:label ?lbl} . OPTIONAL { ?className rdfs:comment ?comment }} ORDER BY ?className" 
        res = self.graph_ORE_RDF.query(spql, initNs=self.ns)

        rv = []
        for (   className, lbl, comment) in res:
                rv.append({ 'className' : className,
                            'nsLabel' : self.getNamespaceAndLabelFromURI(className),
                            'label' : self.getRDFSLabelFromURI(className),  
                            'comment' : comment })
        return json.dumps(rv)

    def process_object_property_nodeinfo_query(self, name):
        spql = "SELECT DISTINCT ?rel ?propType ?rng ?minCard ?maxCard ?card ?lbl ?comment WHERE { ?restr a owl:Restriction . ?restr owl:onProperty %s . %s a ?propType . ?restr owl:onProperty ?rel . OPTIONAL { ?restr owl:minCardinality ?minCard } . OPTIONAL { ?restr owl:maxCardinality ?maxCard } . OPTIONAL { ?restr owl:cardinality ?card } . OPTIONAL { ?rel rdfs:range ?rng } . OPTIONAL { ?rel rdfs:label ?lbl } . OPTIONAL { ?restr rdfs:comment ?comment }}"   % (name, name)
        res = self.graph_ORE_RDF.query(spql, initNs=self.ns)

        rv = []
        for (   rel, propType, rng, minCard, maxCard, card, lbl, comment) in res:
                if rng:
                    rng = self.getNamespaceAndLabelFromURI(rng)
                rv.append({ 'rel' : rel,
                            'propType' : str(propType)[30:],
                            'range' : rng,
                            'minCard' : minCard,
                            'maxCard' : maxCard,
                            'card' : card,
                            'comment' : comment,
                            'label' : lbl, #--> lbl is not always present so unreliable.
                            'nsLabel' : name })
        return json.dumps(rv)

    def process_class_nodeinfo_query(self, name):
        # To-do: Using 'label' to get the info, which should work in most cases, but 
        #  a bit of a hack. Should be using the URI in the rdf:about attribute of
        #  of the owl:Class specification, but couldn't figure out, yet. AG
        label = "'" + self.getRDFSLabelFromURI(name) + "'"
        spql = "SELECT ?comment WHERE {?className rdfs:comment ?comment . ?className rdfs:label %s}" % label

        res = self.graph_ORE_RDF.query(spql, initNs=self.ns)

        rv = []
        for (   comment) in res:
                rv.append({ 'className' : self.getFullURIFromName(name),
                            'nsLabel' : name,
                            'label' : label.strip("'"),  
                            'comment' : comment })
        return json.dumps(rv)

    def getNamespaceAndLabelFromURI(self, uri):
        #myns['ore'] = URIRef('http://www.openarchives.org/ore/terms/')
        #myns['rdfs'] = URIRef('http://www.w3.org/2000/01/rdf-schema#')
        #myns['owl'] = URIRef('http://www.w3.org/2002/07/owl#')
        #myns['dcterms'] = URIRef('http://purl.org/dc/terms/')
        #myns['dcelems'] = URIRef('http://purl.org/dc/elements/1.1/')
        #myns['foaf'] = URIRef('http://xmlns.com/foaf/0.1/')
        #myns['dctype'] = URIRef('http://purl.org/dc/dcmitype/')

        for k, v in self.ns.items():
            if uri.find(v) > -1:                
                return k + ':' + self.getLastFromURI(uri)
        return uri

    def getFullURIFromName(self, namespaceId):
        #myns['ore'] = URIRef('http://www.openarchives.org/ore/terms/')
        #myns['rdfs'] = URIRef('http://www.w3.org/2000/01/rdf-schema#')
        #myns['owl'] = URIRef('http://www.w3.org/2002/07/owl#')
        #myns['dcterms'] = URIRef('http://purl.org/dc/terms/')
        #myns['dcelems'] = URIRef('http://purl.org/dc/elements/1.1/')
        #myns['foaf'] = URIRef('http://xmlns.com/foaf/0.1/')
        #myns['dctype'] = URIRef('http://purl.org/dc/dcmitype/')

        for k, v in self.ns.items():
            if namespaceId.find(k) > -1:                
                return v + self.getIdFromNamespaceId(namespaceId)
        return null
    
    def getLastFromURI(self, uri):
        splitURI = uri.split('/')
        return splitURI[len(splitURI)-1]

    def getNamespaceFromNamespaceId(self, namespaceId):
        splitName = namespaceId.split(':')
        return splitName[0]

    def getIdFromNamespaceId(self, namespaceId):
        splitName = namespaceId.split(':')
        return splitName[len(splitName)-1]

    def getRDFSLabelFromURI(self, uri):
        name = self.getLastFromURI(uri)
        apostdName = self.getIdFromNamespaceId(name)
        return re.sub("([A-Z])", r' \1', apostdName).strip()
        
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
    
