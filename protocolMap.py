# Map incoming request stuff into local objects
# Eg dc.title -> l5r-idx-cardname object

from baseObjects import ProtocolMap, Extractor
from configParser import C3Object
from c3errors import ConfigFileException, ObjectDoesNotExistException
from utils import elementType, textType, flattenTexts
import sys, os, SRW

import srwExtensions

from PyZ3950.CQLParser import modifierClauseType, indexType, relationType
from PyZ3950 import z3950, asn1

class ZeerexProtocolMap(ProtocolMap):
    protocol = ""
    version = ""
    c3Namespace = "http://www.cheshire3.org/schemas/explain/"


    _possiblePaths = {'zeerexPath' : {'docs' : "Path to ZeeRex file."}}

    def __init__(self, session, node, parent):
        ProtocolMap.__init__(self, session, node, parent)
        p = self.get_path(session, 'zeerexPath')
        if (p == None):
            raise(ConfigFileException('ZeerexPath not specified for CQLConfig.'))
        else:
            if ( not os.path.isabs(p)):
                dfp = self.get_path(session, 'defaultPath')
                p = os.path.join(dfp, p)
            dom = self._getDomFromFile(session, p)
        for c in dom.childNodes:
            if c.nodeType == elementType:
                self._walkZeeRex(session, c)    

class Z3950ProtocolMap(ZeerexProtocolMap):
    transformerHash = {}

    def __init__(self, session, node, parent):
        self.protocol = "http://www.loc.gov/z3950/"
        self.transformerHash = {}
        self.indexHash = {}
        self.prefixes = {}
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
                        if (txr == None):
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
            if (self.prefixes.has_key(name) and uri <> self.prefixes[name]):
                raise(ConfigFileException('Multiple OIDs bound to same short name: %s -> %s' % (name, uri)))
            self.prefixes[str(name)] = str(uri)

        elif node.localName == 'index':
            # Process indexes
            idxName = node.getAttributeNS(self.c3Namespace, 'index')
            indexObject = self.get_object(session, idxName)
            if indexObject == None:
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
        bib1str = '.'.join(map(str, bib1.lst))
        xd1 = z3950.Z3950_ATTRS_XD1_ov
        xd1str = '.'.join(map(str, xd1.lst))
        attrHash = {}
        for c in attrs:
            if (not c[0]):
                c[0] = asn1.OidVal(map(int, self.defaultAttributeSet.split('.')))
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


class UpdateProtocolMap(ZeerexProtocolMap):
    transformerHash = {}
    workflowHash = {}

    def __init__(self, session, node, parent):
        self.protocol = "http://www.loc.gov/zing/srw/update/"
        self.protocolNamespaces = SRW.protocolNamespaces
        self.recordNamespaces = SRW.recordNamespaces
        self.profileNamespaces = SRW.update.profileNamespaces
        self.extensionNamespaces = SRW.update.extensionNamespaces

        self.transformerHash = {}
        self.workflowHash = {}

        ZeerexProtocolMap.__init__(self, session, node, parent)

    def _walkZeeRex(self, session, node):

        if node.localName in ['databaseInfo', 'metaInfo', 'indexInfo']:
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
        elif node.localName == 'schema':
            id = node.getAttribute('identifier')
            name = node.getAttribute('name')
            xsl = node.getAttributeNS(self.c3Namespace, 'transformer')
            if (xsl):
                txr = self.get_object(session, xsl)
                if (txr == None):
                    raise ConfigFileException("No transformer to map to for %s" % (xsl))
                self.transformerHash[id] = txr
            self.recordNamespaces[name] = id
        elif node.localName == "supports":
            stype = node.getAttribute('type')
            data = flattenTexts(node)
            if (stype == 'operation'):
                wflw = node.getAttributeNS(self.c3Namespace, 'workflow')
                if (wflw):
                    flow = self.get_object(session, wflw)
                    if (flow == None):                        
                        raise ConfigFileException("No workflow to map to for %s" % wflw)
                    self.workflowHash[data] = self.get_object(session, wflw)
        elif (node.localName == 'default'):
            dtype = node.getAttribute('type')
            pname = "default" + dtype[0].capitalize() + dtype[1:]
            data = flattenTexts(node)
            if (data.isdigit()):
                data = int(data)
            elif data == 'false':
                data = 0
            elif data == 'true':
                data = 1
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
                    

class CQLProtocolMap(ZeerexProtocolMap):
    
    prefixes = {}
    indexHash = {}
    transformerHash = {}
    recordExtensionHash = {}
    termExtensionHash = {}
    searchExtensionHash = {}
    scanExtensionHash = {}
    explainExtensionHash = {}
    responseExtensionHash = {}

    
    def __init__(self, session, node, parent):
        self.protocol = "http://www.loc.gov/zing/srw/"
        self.indexHash = {}
        self.transformerHash = {}
        self.prefixes = {}
        self.protocolNamespaces = SRW.protocolNamespaces
        self.recordNamespaces = SRW.recordNamespaces
        self.contextSetNamespaces = SRW.contextSetNamespaces
        self.profileNamespaces = SRW.profileNamespaces
        self.extensionNamespaces = SRW.extensionNamespaces

        self.recordExtensionHash = {}
        self.termExtensionHash = {}
        self.searchExtensionHash = {}
        self.scanExtensionHash = {}
        self.explainExtensionHash = {}
        self.responseExtensionHash = {}
	self.sruExtensionMap = {}
	
        ZeerexProtocolMap.__init__(self, session, node, parent)


    def resolvePrefix(self, name):
        if (self.prefixes.has_key(name)):
            return self.prefixes[name]
        elif not name:
            # Look for default
            if not hasattr(self, 'defaultContextSet'):
                raise ConfigFileException('Zeerex does not have default context set.')
            default = self.defaultContextSet
            if (self.prefixes.has_key(default)):
                return self.prefixes[default]
            else:
                return default
        else:
            # YYY: Should step up to other config objects?
            raise(ConfigFileException("Unknown prefix: %s" % (name)))

    def resolveIndex(self, session, query):

	if query.index.prefix == "c3":
            # Override
	    try:
		idx = self.parent.get_object(session, query.index.value)
	    except ObjectDoesNotExistException:
		# origValue is complete token
		val = query.index.origValue.split('.')[1]
		idx = self.parent.get_object(session, val)
	    return idx

        target = query
        while (target.parent):
            target = target.parent
        target.config = self

        query.index.resolvePrefix()
        uri = query.index.prefixURI
        name = query.index.value
        rel = query.relation.value
        relMods = query.relation.modifiers

        # FIXME:  Better CQL->Index resolution
        # Check relevance, check stem, check str/word, check relation,
        # Check index

        relv = stem = 0
        rms = []
        for r in relMods:
            # FIXME: Check context set!
            if (r.type.value == 'relevant'):
                relv = 1
            elif (r.type.value == 'stem'):
                stem = 1
            else:
                rms.append(r.type.value)

        idx = None
        if (relv):
            idx = self.indexHash.get((uri, name, ('relationModifier', 'relevant')), None)
        if (not idx and stem):
            idx = self.indexHash.get((uri, name, ('relationModifier', 'stem')), None)
        if (not idx and rms):
            for rm in rms:
                idx = self.indexHash.get((uri, name, ('relationModifier', rm)), None)
                if (idx):
                    break
        if (not idx):
            idx = self.indexHash.get((uri, name, ('relation', rel)), None)
        if (not idx):
            idx = self.indexHash.get((uri,name), None)
        return idx


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
        elif node.localName == 'schema':
            id = node.getAttribute('identifier')
            name = node.getAttribute('name')
            xsl = node.getAttributeNS(self.c3Namespace, 'transformer')
            if (xsl):
                txr = self.get_object(session, xsl)
                if (txr == None):
                    raise ConfigFileException("No transformer to map to for %s" % (xsl))
                self.transformerHash[id] = txr
            self.recordNamespaces[name] = id
        elif node.localName == 'set':
            name = node.getAttribute('name')
            uri = node.getAttribute('identifier')
            if (self.prefixes.has_key(name) and uri <> self.prefixes[name]):
                raise(ConfigFileException('Multiple URIs bound to same short name: %s -> %s' % (name, uri)))
            self.prefixes[str(name)] = str(uri)
        elif node.localName == 'index':
            # Process indexes
            idxName = node.getAttributeNS(self.c3Namespace, 'index')
            indexObject = self.get_object(session, idxName)
            if indexObject == None:
                raise(ConfigFileException("[%s] No Index to map to for %s" % (self.id, idxName)))
            maps = []

            for c in node.childNodes:
                if (c.nodeType == elementType and c.localName == 'map'):
                    maps.append(self._walkZeeRex(session, c))
            for m in maps:
                self.indexHash[m] = indexObject
            # Need to generate all relations and modifiers
            for c in node.childNodes:
                if (c.nodeType == elementType and c.localName == 'configInfo'):
                    for c2 in c.childNodes:
                        if (c2.nodeType == elementType and c2.localName == 'supports'):
                            idxName2 = c2.getAttributeNS(self.c3Namespace, 'index')
                            if (not idxName2):
                                indexObject2 = indexObject
                            else:
                                indexObject2 = self.get_object(session, idxName2)
                                if indexObject2 == None:
                                    raise(ConfigFileException("[%s] No Index to map to for %s" % (self.id, idxName2)))
                            st = str(c2.getAttribute('type'))
                            val = str(flattenTexts(c2))
                            for m in maps:
                                self.indexHash[(m[0], m[1], (st, val))] = indexObject2

        elif (node.localName == 'map'):
            for c in node.childNodes:
                if (c.nodeType == elementType and c.localName == 'name'):
                    short = c.getAttribute('set')
                    index = flattenTexts(c)
                    index = index.lower()
                    uri = self.resolvePrefix(short)
                    if (not uri):
                        raise(ConfigFileException("No mapping for %s in Zeerex" % (short)))
                    return (str(uri), str(index))
        elif (node.localName == 'default'):
            dtype = node.getAttribute('type')
            pname = "default" + dtype[0].capitalize() + dtype[1:]
            data = flattenTexts(node)
            if (data.isdigit()):
                data = int(data)
            elif data == 'false':
                data = 0
            elif data == 'true':
                data = 1
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
        elif (node.localName == 'supports'):
            stype = node.getAttribute('type')
            if stype in ['extraData', 'extraSearchData', 'extraScanData', 'extraExplainData', 'extension']:
                # function, xnType, sruName
                fn = node.getAttributeNS(self.c3Namespace, 'function')
                if (hasattr(srwExtensions, fn)):
                    fn = getattr(srwExtensions, fn)
                else:
                    raise(ConfigFileException('Cannot find handler function %s in srwExtensions.' % fn))
                xn = node.getAttributeNS(self.c3Namespace, 'type')
                if (not xn in ['record', 'term', 'search', 'scan', 'explain', 'response']):
		    raise (ConfigFileException('Incorrect extension type %s' % xn))               
                xform = node.getAttributeNS(self.c3Namespace, 'sruFunction')
                if not xform:
                    sruFunction = srwExtensions.simpleRequestXform
                elif hasattr(srwExtensions, xform):
                    sruFunction = getattr(srwExtensions, xform)
                else:
                    raise(ConfigFileException('Cannot find transformation function %s in srwExtensions.' % xform))
                    
                sru = node.getAttributeNS(self.c3Namespace, 'sruName')
                data = flattenTexts(node)
                data = data.strip()
                data = tuple(data.split(' '))
                hashAttr = xn + "ExtensionHash"                
		curr = getattr(self, hashAttr)
		curr[data] = fn
		setattr(self, hashAttr, curr)
                self.sruExtensionMap[sru] = (data[0], data[1], sruFunction)
        else:
            for c in node.childNodes:
                if c.nodeType == elementType:
                    self._walkZeeRex(session, c)
                    

    def parseExtraData(self, extra):
        nodes = []
        for item in extra.iteritems():
            name = item[0]
            map = self.sruExtensionMap.get(name, None)
            if map:
                nodes.append(map[2](item, self))
        return nodes


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
        if not self.recordNamespaces.has_key('oai_dc'):
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
                if (txr == None):
                    raise ConfigFileException("No transformer to map to for %s" % (txrid))
                self.transformerHash[id] = txr
            self.recordNamespaces[name] = id
            self.schemaLocations[id] = location
        else:
            for c in node.childNodes:
                if c.nodeType == elementType:
                    self._walkZeeRex(session, c)


