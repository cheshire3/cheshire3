import irods

from cheshire3.user import SimpleUser

try:
    from rdflib import Literal, URIRef, BNode, ConjunctiveGraph, Namespace
    from rdflib import StringInputSource
except:
    pass
else:
    NS = {
        'ore': Namespace('http://www.openarchives.org/ore/terms/'),
        'orex': Namespace('http://foresite.cheshire3.org/orex/terms/'),
        'dc': Namespace('http://purl.org/dc/elements/1.1/'),
        'mesur': Namespace('http://www.mesur.org/schemas/2007-01/mesur#'),
        'dcterms': Namespace('http://purl.org/dc/terms/'),
        'swap': Namespace('http://purl.org/eprint/type/'),
        'rdf': Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
        'foaf': Namespace('http://xmlns.com/foaf/0.1/'),
        'rdfs': Namespace('http://www.w3.org/2001/01/rdf-schema#'),
        'dcmitype': Namespace('http://purl.org/dc/dcmitype/'),
        'atom': Namespace('http://www.w3.org/2005/Atom'),
        'owl': Namespace('http://www.w3.org/2002/07/owl#'),
        'xsd': Namespace('http://www.w3.org/2001/XMLSchema'),
        'xhtml': Namespace('http://www.w3.org/1999/xhtml'),
        'grddl': Namespace('http://www.w3.org/2003/g/data-view#'),
        'swetodblp': Namespace('http://lsdis.cs.uga.edu/projects/semdis/'
                               'opus#'),
        'skos': Namespace('http://www.w3.org/2004/02/skos/core#'),
        'eurepo': Namespace('info:eu-repo/semantics/'),
        'at': Namespace('http://purl.org/syndication/atomtriples/1/'),
        'iana': Namespace('http://www.iana.org/assignments/relation/'),
        'bibo': Namespace('http://purl.org/ontology/bibo/'),
        'prism': Namespace('http://prismstandard.org/namespaces/1.2/basic/'),
        'vcard': Namespace('http://nwalsh.com/rdf/vCard#'),
        'zotero': Namespace('http://www.zotero.org/namespaces/expert#'),
        'pms': Namespace('http://id.loc.gov/standards/premis/rdf/'),
        'demo': Namespace('http://shaman.cheshire3.org/ns/demo/'),
        'shmn': Namespace('http://shaman.cheshire3.org/ns/shaman/'),
        'shmn-group': Namespace('http://shaman.cheshire3.org/ns/shaman/'
                                'groupType/'),
        'shmn-user': Namespace('http://shaman.cheshire3.org/ns/shaman/'
                               'userType/')
    }

    predicateMap = {
        NS['foaf']['name']: 'realName',
        NS['dc']['description']: 'description',
        NS['vcard']['TEL']: 'tel',
        NS['vcard']['ADR']: 'address',
        NS['vcard']['EMAIL']: 'email'
    }


class IrodsUser(SimpleUser):
    
    simpleFields = ['email', 'address', 'tel', 'realName', 'description']
    
    username = ""
    email = ""
    address = ""
    tel = ""
    realName = ""
    description = ""
    flags = {}

    def __init__(self, conn, name):
        user = irods.irodsUser(conn, name)
        self.id = user.getId()
        self.username = id
        self.email = ""
        self.address = ""
        self.tel = ""
        self.realName = ""
        self.description = ""
        self.flags = {}

        umd = user.getUserMetadata()
        for u in umd:
            if u[0] == 'rdf':
                # Try to parse
                try:
                    g = ConjunctiveGraph()
                except:
                    continue
                for (key, val) in NS.iteritems():
                    g.bind(key, val)
                data = StringInputSource(umd[1])
                try:
                    if umd[2]:
                        g.parse(data, umd[2])
                    else:
                        g.parse(data)
                    me = NS['demo']['users/%s'] % self.id
                    for (p, o) in g.predicate_objects(me):
                        if predicateMap.has_key(p):
                            setattr(self, predicateMap[p], str(o))
                except:
                    # RDF exists, could parse, but is broken
                    raise
            elif u[0] in self.simpleFields:
                setattr(self, u[0], u[1])
            elif u[0] == 'flags':
                # Should be a {} of flag : [obj, obj]
                pass

    def has_flag(self, session, flag, object=""):
        # Does the user have the flag for this object/all objects
        f = self.flags.get(flag, [])
        if object in f:
            return True
        else:
            # Does the user have a global flag for this object/all objects
            f = self.flags.get("", [])
            if object in f:
                return True
            else:
                f = self.flags.get("c3r:administrator", [])
                if object in f or f == "":
                    return True                
                return False

    def check_password(self, session, password):
        # Check password in iRODS
        return False
