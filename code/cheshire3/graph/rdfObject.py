
from rdflib import ConjunctiveGraph, URIRef, BNode, Literal, Namespace, StringInputSource

namespaces = {'ore' : Namespace('http://www.openarchives.org/ore/terms/'),
              'dc' : Namespace('http://purl.org/dc/elements/1.1/'),
              'dcterms' : Namespace('http://purl.org/dc/terms/'),
              'owl' : Namespace('http://www.w3.org/2002/07/owl#'),
              'rdf' : Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
              'rdfs' : Namespace('http://www.w3.org/2001/01/rdf-schema#'),
              'xsd' : Namespace('http://www.w3.org/2001/XMLSchema'),
              'oac' : Namespace('http://www.openannotation.org/ns/'),
              'skos' : Namespace('http://www.w3.org/2004/02/skos/core#'),
              'foaf' : Namespace('http://xmlns.com/foaf/0.1/'),
              'bibo' : Namespace('http://purl.org/ontology/bibo/'),
              'dcmitype' : Namespace('http://purl.org/dc/dcmitype/'),
              'atom' : Namespace('http://www.w3.org/2005/Atom'),
              'xhtml' : Namespace('http://www.w3.org/1999/xhtml'),
              'grddl' : Namespace('http://www.w3.org/2003/g/data-view#'),
              'eurepo' : Namespace('info:eu-repo/semantics/'),
              'at' : Namespace('http://purl.org/syndication/atomtriples/1/'),
              'iana' : Namespace('http://www.iana.org/assignments/relation/'),
              'mesur' : Namespace('http://www.mesur.org/schemas/2007-01/mesur#'),
              'swap' : Namespace('http://purl.org/eprint/type/'),
              'swetodblp' : Namespace('http://lsdis.cs.uga.edu/projects/semdis/opus#'),
              'prism' : Namespace('http://prismstandard.org/namespaces/1.2/basic/'),
              'vcard' : Namespace('http://nwalsh.com/rdf/vCard#'),
              'zotero' : Namespace('http://www.zotero.org/namespaces/exprt#')              
              }

### Elements commonly used
### If an element is in this list, you can do object.predicate,
### rather than object._namespace.predicate
### (Not complete for most namespaces, just common terms)
elements = {
    'ore' : ['describes', 'isDescribedBy', 'aggregates', 'isAggregatedBy', 'similarTo', 'proxyFor', 'proxyIn', 'lineage'],
    'orex' : ['isAuthoritativeFor', 'AnonymousAgent', 'page', 'follows', 'firstPage', 'lastPage'],
    'dc' : ['coverage', 'date', 'description', 'format', 'identifier', 'language', 'publisher', 'relation', 'rights', 'source', 'subject', 'title'],  # no creator, contributor
    'dcterms': ['abstract', 'accessRights', 'accrualMethod', 'accrualPeriodicity', 'accrualPolicy', 'alternative', 'audience', 'available', 'bibliographicCitation', 'conformsTo', 'contributor', 'created', 'creator', 'dateAccepted', 'dateCopyrighted', 'dateSubmitted', 'educationLevel', 'extent', 'hasFormat', 'hasPart', 'hasVersion', 'instructionalMethod', 'isFormatOf', 'isPartOf', 'isReferencedBy', 'isReplacedBy', 'isRequiredBy', 'issued', 'isVersionOf', 'license', 'mediator', 'medium', 'modified', 'provenance', 'references', 'replaces', 'requires', 'rights', 'rightsHolder', 'spatial', 'tableOfContents', 'temporal', 'valid'],  # also rights
    'foaf' : ['accountName', 'aimChatID', 'birthday', 'depiction', 'depicts', 'family_name', 'firstName', 'gender', 'givenname', 'homepage', 'icqChatID', 'img', 'interest', 'jabberID', 'knows', 'logo', 'made', 'maker', 'mbox', 'member', 'msnChatID', 'name', 'nick', 'openid', 'page', 'phone', 'surname', 'thumbnail', 'weblog', 'yahooChatID'],
    'owl' : ['sameAs'],
    'rdf' : ['type'],
    'rdfs' : ['seeAlso', 'label', 'isDefinedBy'],
    'oac' : ['hasContent', 'body', 'hasTarget', 'hasSegmentDescription', 'when', 'transcribes', 'isTranscribedBy', 'hasTargetContext', 'hasContentContext', 'contextAbout', 'predicate'],
    'mesur' : ['hasAccess', 'hasAffiliation', 'hasIssue', 'hasVolume', 'used', 'usedBy'],
    'skos' : ['prefLabel', 'inScheme', 'broader', 'narrower', 'related', 'Concept', 'ConceptScheme', 'changeNote', 'editorialNote'],
    'iana' : ['alternate', 'current' ,'enclosure', 'edit', 'edit-media', 'first', 'last',  'next', 'next-archive', 'previous', 'payment', 'prev-archive', 'related', 'replies', 'service', 'via'],  # -self, -license
    'bibo' : ['Article', 'Issue', 'Journal', 'pageStart', 'pageEnd', 'volume']
    }

### The order in which to search the above hash
namespaceSearchOrder = ['ore', 'dc', 'dcterms', 'foaf', 'rdf', 'rdfs', 'owl', 'oac', 'mesur', 'skos', 'iana', 'bibo']

### Predicates that shouldn't be serialized
internalPredicates = []
unconnectedAction = 'ignore'

mimetypeHash = {'rdfa' : 'application/xhtml+xml',
                'xml' : 'application/rdf+xml',
                'nt' : 'text/plain',
                'n3' : 'text/rdf+n3',
                'turtle' : 'application/x-turtle',
                'pretty-xml' : 'application/rdf+xml',
                'json' : 'application/rdf+json',
                'pretty-json' : 'application/rdf+json'
                }

formatHash = {'application/xhtml+xml' : 'rdfa',
              'application/rdf+xml' : 'pretty-xml',
              'application/rdf+json' : 'pretty-json',
              'application/x-turtle' : 'turtle',
              'text/plain' : 'nt',
              'text/rdf+n3' : 'n3'}

# XXX Register plugins for RDFa and  JSON


# --- Object Class Definitions ---

class Graph(ConjunctiveGraph):
    def __init__(self, store=None, id=None):
        if store is not None and id is not None:
            ConjunctiveGraph.__init__(self, store, id)
        else:
            ConjunctiveGraph.__init__(self)
        for (key,val) in namespaces.iteritems():
            self.bind(key, val)

    def find_namespace(self, name):
        # find best namespace
        for k in namespaceSearchOrder:
            v = elements[k]
            if name in v:
                return namespaces[k]
        return ''

    def split_uri(self, uri):
        # given namespaced uri, find base property name
        slsplit = uri.split('/')
        hsplit = slsplit[-1].split('#')
        return (uri[:0-len(hsplit[-1])], hsplit[-1])
        

class RdfObject(object):
    graph = None
    uri = ""
    currNs = ""
    public = True
    objects = {}

    def __init__(self, uri=None):
        graph = Graph()
        self._graph_ = graph
        if isinstance(uri, URIRef) or isinstance(uri, BNode):
            self._uri_ = uri
        elif uri is None:
            self._uri_ = BNode()
        elif type(uri) in [str, unicode]:
            self._uri_ = URIRef(uri)
        else:
            raise ValueError("URI for object must be string, unicode, URIRef, BNode, or None")

        self._currNs_ = ''
        self._objects_ = {}
        self._public_ = True

    def __str__(self):
        return str(self.uri)

    def __getattr__(self, name):
        # fetch value from graph
        cns = self.currNs
        if name[0] == "_" and name[-1] == "_":
            return getattr(self, name[1:-1])
        elif name[0] == "_" and namespaces.has_key(name[1:]):
            # we're looking for self.namespace.property
            self._currNs_ = name[1:]
            return self
        elif cns:
            val = self.get_value(name, cns)
            self._currNs_ = ''
        else:
            val = self.get_value(name)
        return val

    def __setattr__(self, name, value):
        if name[0] == "_" and name[-1] == "_":            
            return object.__setattr__(self, name[1:-1], value)
        elif name[0] == "_" and namespaces.has_key(name[1:]):
            # we're looking for self.namespace.property
            object.__setattr__(self, 'currNs', name[1:])
            return self
        elif self.currNs:
            val = self.set_value(name, value, self.currNs)        
        else:
            val = self.set_value(name, value)
        object.__setattr__(self, 'currNs', '')
        return val

    def __iter__(self):
        l = [x for x in self._graph_]
        return l.__iter__()

    def __len__(self):
        return len(self._graph_)

    def set_value(self, name, value, ns=None):
        if ns:
            nsobj = namespaces[ns]
        else:
            nsobj = self.graph.find_namespace(name)

        if value == []:
            for val in self.graph.objects(self.uri, nsobj[name]):
                self.graph.remove((self.uri, nsobj[name], val))
        else:
            if isinstance(value, RdfObject):
                self.add_object(value)
                value = value._uri_
            if not isinstance(value, URIRef) and not isinstance(value, BNode):
                value = Literal(value)
            self.graph.add((self.uri, nsobj[name], value))
        return 1

    def get_value(self, name, ns=None):        
        if ns:
            nsobj = namespaces[ns]
        else:
            nsobj = self.graph.find_namespace(name)
        l = []
        for obj in self.graph.objects(self.uri, nsobj[name]):
            l.append(obj)
        return l

    def add_object(self, what):
        self._objects_[what._uri_] = what

    def remove_object(self, what):
        del self._objects_[what._uri_]

    def predicates(self):
        return list(self.graph.predicates())

    def serialize(self, format="", uri=None, mimeType=""):
        if not format and not mimeType:
            format = 'pretty-xml'
        if not format and mimeType:
            try:
                format = formatHash[mimeType]
            except:
                raise ValueError("Unknown mimeType: %s" % mimeType)
        elif not mimeType :
            try:
                mimeType = mimetypeHash[format]
            except:
                raise ValueError("Unknown format: %s" % format)

        g = self.merge_graphs()
        data = g.serialize(format=format)        
        rd = GraphSerialization(data, uri=uri, format=format, mimeType=mimeType)
        return rd

    def merge_graphs(self):
        g = Graph()
        stack = [self]
        done = []
        while stack:
            what = stack.pop(0)
            if what is None or what in done:
                continue
            done.append(what)            
            g += what._graph_
            for at in what._objects_.values():
                stack.append(at)
                
        if self.public:
            # Remove internal methods
            for p in internalPredicates:
                for (s,o) in g.subject_objects(p):
                    g.remove((s,p,o))
            
        g = self.connected_graph(g)
        return g

    def connected_graph(self, graph):
        if unconnectedAction == 'ignore':
            return graph

        g = Graph()
        all_nodes = list(graph.all_nodes())
        all_nodes = filter(lambda y: not isinstance(y, Literal), all_nodes)
        discovered = {}
        visiting = [uri]
        while visiting:
            x = visiting.pop()
            if not discovered.has_key(x):
                discovered[x] = 1
            for (p, new_x) in graph.predicate_objects(subject=x):
                g.add((x,p,new_x))
                if (isinstance(new_x, URIRef) or isinstance(new_x, BNode)) and not discovered.has_key(new_x) and not new_x in visiting:
                    visiting.append(new_x)
            for (new_x, p) in graph.subject_predicates(object=x):
                g.add((new_x,p,x))
                if (isinstance(new_x, URIRef) or isinstance(new_x, BNode)) and not discovered.has_key(new_x) and not new_x in visiting:
                    visiting.append(new_x)
        if len(discovered) != len(all_nodes):
            if unconnectedAction == 'warn':
                print "Warning: Graph is unconnected, some nodes being dropped"
            elif unconnectedAction == 'raise':
                raise OreException('Graph to be serialized is unconnected')
            elif unconnectedAction != 'drop':
                raise ValueError('Unknown unconnectedAction setting: %s' % unconnectedAction)
        return g

    def do_sparql(self, sparql):
        # first merge graphs
        g = self.merge_graphs()
        # now do sparql query on merged graph
        sparql = sparql.replace('??self', '<%s>' % str(self.uri))
        return g.query(sparql, initNs=namespaces)


class GraphSerialization(object):
    def __init__(self, data, uri=None, format="", mimeType=""):
        self.data = data
        self.uri = uri
        self.format = format
        self.mimeType = mimeType

    def parse(self):
        # parse to find graph
        graph =  Graph()
        data = StringInputSource(self.data)
        if self.format and self.format != 'pretty-xml':
            graph.parse(data, format=self.format)
        else:
            graph.parse(data)
        return self.process_graph(graph)

    def process_graph(self, graph):
        # make one object per subject
        objs = {}
        refs = {}
        for (s,p,o) in graph:
            try:
                obj = objs[s]
            except KeyError:
                obj = RdfObject(s)
                objs[s] = obj
            obj.graph.add((s,p,o))
            if isinstance(o, URIRef):
                try:
                    refs[s].append(o)
                except KeyError:
                    refs[s] = [o]
        # now join up
        for (k, v) in refs.items():
            for targ in v:
                try:
                    k.add_object(objs[targ])
                except:
                    pass
        return objs
                    
if __name__ == '__main__':        
    book = RdfObject('book')
    book.type = namespaces['bibo']['Book']
    book.title = "Title"
    book.subject = "Some Subject"
    book._dc.subject = "Some Other Subject"
    book.extent = 1
    who = RdfObject('bob')
    who.type = namespaces['foaf']['Agent']
    who.name = "Bob Smith"
    book.creator = who

    rd = book.serialize('turtle')
    print rd.data
    
    rs = book.do_sparql('select ?ttl ?aname where {??self dc:title ?ttl . ??self dcterms:creator ?w . ?w foaf:name ?aname .}')
    for x in rs:
        print x
