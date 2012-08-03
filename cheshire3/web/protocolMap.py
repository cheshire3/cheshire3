# Map incoming request stuff into local objects
# Eg dc.title -> l5r-idx-cardname object

from cheshire3.protocolMap import ZeerexProtocolMap
from cheshire3.exceptions import ConfigFileException
from cheshire3.utils import elementType, textType, flattenTexts
from cheshire3.cqlParser import modifierClauseType, indexType, relationType

from PyZ3950 import z3950, asn1


class Z3950ProtocolMap(ZeerexProtocolMap):
    transformerHash = {}

    def __init__(self, session, node, parent):
        self.protocol = "http://www.loc.gov/z3950/"
        self.transformerHash = {}
        self.indexHash = {}
        self.prefixes = {}
        self.defaultAttribute = []
        ZeerexProtocolMap.__init__(self, session, node, parent)
        self.defaultAttributeHash = {}
        for x in self.defaultAttribute:
            self.defaultAttributeHash[(x[0], x[1])] = x[2]

    def _walkZeeRex(self, session, node):

        if node.localName in ['databaseInfo', 'metaInfo']:
            # Ignore
            return
        elif node.localName == 'serverInfo':
            self.version = node.getAttribute('version')
            for c in node.childNodes:
                self._walkZeeRex(session, c)
        elif node.localName == 'database':
            self.databaseName = str(flattenTexts(node))
        elif node.localName == 'host':
            self.host = str(flattenTexts(node))
        elif node.localName == 'port':
            self.port = int(flattenTexts(node))

        elif node.localName == 'recordSyntax':
            id = node.getAttribute('identifier')
            # id is string dotted OID
            thash = {}
            for c in node.childNodes:
                if (c.nodeType == elementType and c.localName == 'elementSet'):
                    name = c.getAttribute('name')
                    xsl = c.getAttributeNS(self.c3Namespace, 'transformer')
                    if (xsl):
                        txr = self.get_object(session, xsl)
                        if (txr is None):
                            raise ConfigFileException("[%s] No transformer to map to for %s" % (self.id, xsl))
                    else:
                        txr = None
                    thash[name.lower()] = txr
            self.transformerHash[id] = thash

        elif node.localName == 'set':
            name = node.getAttribute('name')
            name = name.lower()
            uri = node.getAttribute('identifier')
            if not name or not uri:
                raise ConfigFileException('Missing name or identifier for attribute set mappting.')
            if (name in self.prefixes and uri != self.prefixes[name]):
                raise(ConfigFileException('Multiple OIDs bound to same short name: %s -> %s' % (name, uri)))
            self.prefixes[str(name)] = str(uri)

        elif node.localName == 'index':
            # Process indexes
            idxName = node.getAttributeNS(self.c3Namespace, 'index')
            indexObject = self.get_object(session, idxName)
            if indexObject is None:
                raise(ConfigFileException("Could not find Index object %s" % (idxName)))
            maps = []
            defaults = []
            supports = []
            for c in node.childNodes:
                if c.nodeType == elementType:
                    if c.localName == 'map':
                        maps.append(self._walkZeeRex(session, c))
                    elif c.localName == 'configInfo':
                        for c2 in c.childNodes:
                            if c2.nodeType == elementType:
                                if c2.localName == "default":
                                    # Get default attributes
                                    for c3 in c2.childNodes:
                                        if c3.nodeType == elementType and c3.localName == 'map':
                                            defaults = self._walkZeeRex(session, c3)
                                elif c2.localName == "supports":
                                    # Get other supported attributes
                                    for c3 in c2.childNodes:
                                        if c3.nodeType == elementType and c3.localName == 'map':
                                            # Can't use c3:index to redirect here Too complicated
                                            data = self._walkZeeRex(session, c3)
                                            supports.append(data)

            # FIXME: This is wrong.  It doesn't respect combinations.
            for s in supports:
                defaults.extend(s)
            
            for m in maps:
                curr = self.indexHash.get(tuple(m), [])
                curr.append((defaults, indexObject))
                self.indexHash[tuple(m)] = curr

        elif (node.localName == 'map'):
            attrs = []
            for c in node.childNodes:
                if (c.nodeType == elementType and c.localName == 'attr'):
                    short = c.getAttribute('set')
                    short = short.lower()
                    if not short:
                        short = 'bib1'
                    oid = self.prefixes.get(short, None)
                    if not oid:
                        raise ConfigFileException('No mapping for attribute set %s in Zeerex file' % short)

                    type = c.getAttribute('type')
                    if not type:
                        raise ConfigFileException('No type attribute for Z39.50 attr mapping in Zeerex')
                    type = int(type)
                    if type < 1:
                        raise ConfigFileException('Invalid type attribute for Z39.50 attr mapping in Zeerex: %s' % type)
                    attrVal = flattenTexts(c).strip()
                    if not attrVal:
                        raise ConfigFileException('No value given for attribute in Z39.50 mapping')
                    if attrVal.isdigit():
                        attrVal = int(attrVal)
                    else:
                        attrVal = attrVal.lower()
                    attrs.append((oid, type, attrVal))
            return attrs
        elif (node.localName == 'default'):
            dtype = node.getAttribute('type')
            pname = "default" + dtype[0].capitalize() + dtype[1:]
            if dtype == 'attribute':
                # Get map instead of text
                for c in node.childNodes:
                    if c.nodeType == elementType and c.localName == 'map':
                        data = self._walkZeeRex(session, c)
            else:
                data = flattenTexts(node)
                if (data.isdigit()):
                    data = int(data)
                elif data == 'false':
                    data = 0
                elif data == 'true':
                    data = 1
                elif data.lower() in self.prefixes.keys():
                    data = self.prefixes[data.lower()]
            setattr(self, pname, data)
        elif (node.localName =='setting'):
            dtype = node.getAttribute('type')
            data = flattenTexts(node)
            if (data.isdigit()):
                data = int(data)
            elif data == 'false':
                data = 0
            elif data == 'true':
                data = 1
            setattr(self, dtype, data)
        else:
            for c in node.childNodes:
                if c.nodeType == elementType:
                    self._walkZeeRex(session, c)

    def attrsToCql(self, attrs):
        # Pull defaults off of self
        bib1 = z3950.Z3950_ATTRS_BIB1_ov
        #bib1str = '.'.join(map(str, bib1.lst))
        bib1str = '.'.join([str(x) for x in bib1.lst])
        xd1 = z3950.Z3950_ATTRS_XD1_ov
        # xd1str = '.'.join(map(str, xd1.lst))
        xd1 = '.'.join([str(x) for x in xd1.lst])
        attrHash = {}
        for c in attrs:
            if (not c[0]):
                # c[0] = asn1.OidVal(map(int, self.defaultAttributeSet.split('.')))
                c[0] = asn1.OidVal([int(x) for x in self.defaultAttributeSet.split('.')])
            attrHash[(c[0], c[1])] = c[2]
        # First check bib1

        defaultAttribs = self.defaultAttributeHash

        use = attrHash.get((bib1, 1))
        rel = attrHash.get((bib1, 2), 3)
        posn = attrHash.get((bib1, 3), None)        
        struct = attrHash.get((bib1, 4), None)
        trunc = attrHash.get((bib1, 5), None)
        comp = attrHash.get((bib1, 6), None)

        defaultPosn = self.defaultAttributeHash.get((bib1str, 3), None)            
        defaultStruct = self.defaultAttributeHash.get((bib1str, 4), None)            
        defaultTrunc = self.defaultAttributeHash.get((bib1str, 5), None)            
        defaultComp = self.defaultAttributeHash.get((bib1str, 6), None)            

        if use:
            if not isinstance(use, int) and use[:3] == "c3.":
                # Override, just grab index, if exists
                idx = self.parent.get_object(None, use[3:])
                if not idx:
                    raise ValueError(use)
                indexStr = use
            else:
                try:
                    use = use.lower()
                except:
                    pass
                info  = self.indexHash.get(((bib1str, 1, use),), None)
                if info:
                    # list of possible indexes.
                    possibleIndexes = []
                    for idx in info:
                        if posn and ( not (bib1str, 3, posn) in idx[0]):
                            continue
                        if not posn and defaultPosn and ( not (bib1str, 3, defaultPosn) in idx[0]):
                            continue
                        if struct and ( not (bib1str, 4, struct) in idx[0]):
                            continue
                        if not struct and defaultStruct and ( not (bib1str, 4, defaultStruct) in idx[0]):
                            continue
                        if trunc and ( not (bib1str, 5, trunc) in idx[0]):
                            continue
                        if not trunc and defaultTrunc and ( not (bib1str, 5, defaultTrunc) in idx[0]):
                            continue
                        if comp and ( not (bib1str, 6, comp) in idx[0]):
                            continue
                        if not comp and defaultComp and ( not (bib1str, 6, defaultComp) in idx[0]):
                            continue
                        possibleIndexes.append([idx[1], idx[0][:4]])

                    if not possibleIndexes:
                        # No match
                        raise ValueError("No matching index")
                    else:
                        # If >1 take first
                        indexInfo = possibleIndexes[0]
                        index = indexInfo[0]
                        # Assgn to struct etc.
                        if not posn:
                            posn  = indexInfo[1][0][2]
                        if not struct:
                            struct  = indexInfo[1][1][2]
                        if not trunc: 
                            trunc  = indexInfo[1][2][2]
                        if not comp:
                            comp  = indexInfo[1][3][2]
                    indexStr = "c3.%s" % index.id
                else:
                    raise ValueError("No matching index??")
        index = indexType(indexStr)
        
        relations = ['', '<', '<=', '=', '>=', '>', '<>']
        if (comp == 3):
            relation = relationType("exact")
        elif (rel > 6):
            if struct in [2, 6]:
                relation = relationType('any')
            elif (rel in [500, 501, 510, 530, 540]):
                relation = relationType('all')
            else:
                relation = relationType('=')
        else:
            relation = relationType(relations[rel])

        if (rel == 100):
            relation.modifiers.append(modifierClauseType('phonetic'))
        elif (rel == 101):
            relation.modifiers.append(modifierClauseType('stem'))
        elif (rel == 102):
            relation.modifiers.append(modifierClauseType('relevant'))
        elif (rel == 500):
            relation.modifiers.append(modifierClauseType('rel.algorithm', '=', 'okapi'))
        elif (rel == 501):
            relation.modifiers.append(modifierClauseType('rel.algorithm', '=', 'cori'))
        elif (rel == 510):
            relation.modifiers.append(modifierClauseType('rel.algorithm', '=', 'trec2'))
        elif (rel == 530):
            relation.modifiers.append(modifierClauseType('rel.algorithm', '=', 'tfidf'))
        elif (rel == 540):
            relation.modifiers.append(modifierClauseType('rel.algorithm', '=', 'tfidflucene'))


        if (struct in [2, 6]):
            relation.modifiers.append(modifierClauseType('word'))
        elif (struct in [4, 5, 100]):
            relation.modifiers.append(modifierClauseType('date'))
        elif (struct == 109):
            relation.modifiers.append(modifierClauseType('number'))
        elif (struct in [1, 108]):
            relation.modifiers.append(modifierClauseType('string'))
        elif (struct == 104):
            relation.modifiers.append(modifierClauseType('uri'))

        return (index, relation)


class C3WepProtocolMap(ZeerexProtocolMap):
    
    def __init__(self, session, node, parent):
        self.protocol = "http://www.cheshire3.org/protocols/workflow/1.0/"
        ZeerexProtocolMap.__init__(self, session, node, parent)
        
    def _walkZeeRex(self, session, node):

        if node.localName in ['databaseInfo', 'metaInfo']:
            # Ignore
            return
        elif node.localName == 'serverInfo':
            self.version = node.getAttribute('version')
            for c in node.childNodes:
                self._walkZeeRex(session, c)
        elif node.localName == 'database':
            self.databaseUrl = str(flattenTexts(node))
        elif node.localName == 'host':
            self.host = str(flattenTexts(node))
        elif node.localName == 'port':
            self.port = int(flattenTexts(node))           
        else:
            for c in node.childNodes:
                if c.nodeType == elementType:
                    self._walkZeeRex(session, c)


class OAIPMHProtocolMap(ZeerexProtocolMap):
    
    def __init__(self, session, node, parent):
        self.protocol = "http://www.openarchives.org/OAI/2.0/OAI-PMH"
        self.recordNamespaces = {}    # key: metadataPrefix, value: XML Namespace
        self.schemaLocations = {}     # key: XML Namespace, value: Schema Location
        self.transformerHash = {}     # key: XML Namespace, value: Cheshire3 Transformer Object
        self.contacts = []
        ZeerexProtocolMap.__init__(self, session, node, parent)
        # some validation checks
        try:
            self.baseURL = 'http://%s:%d/%s' % (self.host, self.port, self.databaseName)
        except:
            raise ConfigFileException("Unable to derive baseURL from host, port, database")
        # metadatPrefix oai_dc is mandatory
        if not 'oai_dc' in self.recordNamespaces:
            raise ConfigFileException("Schema configuration for mandatory metadataPrefix 'oai_dc' required in schemaInfo.")
        # at least 1 adminEmail address is mandatory for Identify response
        if not len(self.contacts):
            raise ConfigFileException("Contact e-mail address of a database administrator required in databaseInfo.")
        
        
    def _walkZeeRex(self, session, node):
        if node.localName in ['indexInfo']:
            # Ignore
            return
        elif node.localName == 'serverInfo':
            self.version = node.getAttribute('version')
            for c in node.childNodes:
                self._walkZeeRex(session, c)
        elif node.localName == 'database':
            self.databaseName = str(flattenTexts(node))
        elif node.localName == 'host':
            self.host = str(flattenTexts(node))
        elif node.localName == 'port':
            self.port = int(flattenTexts(node))
        elif node.localName == 'title':
            self.title = str(flattenTexts(node))
        elif node.localName == 'contact':
            self.contacts.append(str(flattenTexts(node)))
        elif node.localName == 'schema':
            id = node.getAttribute('identifier')
            location = node.getAttribute('location')
            name = node.getAttribute('name')
            txrid = node.getAttributeNS(self.c3Namespace, 'transformer')
            if (txrid):
                txr = self.get_object(session, txrid)
                if (txr is None):
                    raise ConfigFileException("No transformer to map to for %s" % (txrid))
                self.transformerHash[id] = txr
            self.recordNamespaces[name] = id
            self.schemaLocations[id] = location
        else:
            for c in node.childNodes:
                if c.nodeType == elementType:
                    self._walkZeeRex(session, c)
