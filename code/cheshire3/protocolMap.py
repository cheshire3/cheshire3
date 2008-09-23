# Map incoming request stuff into local objects
# Eg dc.title -> l5r-idx-cardname object

from cheshire3.baseObjects import ProtocolMap, Extractor
from cheshire3.exceptions import ConfigFileException, ObjectDoesNotExistException
from cheshire3.utils import elementType, textType, flattenTexts
from cheshire3.cqlParser import modifierClauseType, indexType, relationType
from cheshire3 import dynamic

try:
    import cheshire3.web.srwExtensions
except:
    srwExtensions = None

import sys, os, SRW

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
            dom = self._getDomFromFile(session, p, parser='minidom')
        for c in dom.childNodes:
            if c.nodeType == elementType:
                self._walkZeeRex(session, c)    

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
    searchRetrieveExtensionHash = {}
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
        self.extensionTypeMap = {}
        ZeerexProtocolMap.__init__(self, session, node, parent)


    def resolvePrefix(self, name):
        if (name in self.prefixes):
            return self.prefixes[name]
        elif not name:
            # Look for default
            if not hasattr(self, 'defaultContextSet'):
                raise ConfigFileException('Zeerex does not have default context set.')
            default = self.defaultContextSet
            if (default in self.prefixes):
                return self.prefixes[default]
            else:
                return default
        elif (name == 'c3'):
            return 'http://www.cheshire3.org/cql-context-set/internal'
        else:
            # YYY: Should step up to other config objects?
            raise(ConfigFileException("Unknown prefix: %s" % (name)))

    def resolveIndex(self, session, query):
        target = query
        while (target.parent):
            target = target.parent
        target.config = self
        
        query.index.resolvePrefix()
        uri = query.index.prefixURI
        name = query.index.value

        if uri == 'http://www.cheshire3.org/cql-context-set/internal':
            # Override
            try:
                idx = self.parent.get_object(session, name)
            except ObjectDoesNotExistException:
                # origValue is complete token
                val = query.index.origValue.split('.')[1]
                idx = self.parent.get_object(session, val)
            return idx
        elif uri == 'info:srw/cql-context-set/1/cql-v1.1' and name == 'serverchoice' and hasattr(self, 'defaultIndex'):
            dp, dn = self.defaultIndex.split('.')
            du = self.resolvePrefix(dp)
            query.index.prefix = dp
            query.index.value = dn
            query.index.prefixURI = du
            return self.resolveIndex(session, query)
        
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
            if (name in self.prefixes and uri != self.prefixes[name]):
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
            pname = "default" + dtype[0].capitalize() + dtype[1:] # XXX: would dtype.title() be nicer!?
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

                xn = node.getAttributeNS(self.c3Namespace, 'type')
                if (not xn in ['record', 'term', 'searchRetrieve', 'scan', 'explain', 'response']):
                    raise (ConfigFileException('Unknown extension type %s' % xn))               
                sru = node.getAttributeNS(self.c3Namespace, 'sruName')
                fn = node.getAttributeNS(self.c3Namespace, 'function')
                data = flattenTexts(node)
                data = data.strip()
                data = tuple(data.split(' '))

                if fn.find('.') > -1:
                    # new version
                    try:
                        fn = dynamic.importObject(session, fn)
                    except ImportError:
                        raise ConfigFileException("Cannot find handler function %s (in %s)" % (fn, repr(sys.path)))
                    self.sruExtensionMap[sru] = (xn, fn, data)
                else:
                    if (hasattr(srwExtensions, fn)):
                        fn = getattr(srwExtensions, fn)
                    else:
                        raise(ConfigFileException('Cannot find handler function %s in srwExtensions.' % fn))
                    xform = node.getAttributeNS(self.c3Namespace, 'sruFunction')
                    if not xform:
                        sruFunction = srwExtensions.simpleRequestXform
                    elif hasattr(srwExtensions, xform):
                        sruFunction = getattr(srwExtensions, xform)
                    else:
                        raise(ConfigFileException('Cannot find transformation function %s in srwExtensions.' % xform))
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
                if (txr == None):
                    raise ConfigFileException("No transformer to map to for %s" % (txrid))
                self.transformerHash[id] = txr
            self.recordNamespaces[name] = id
            self.schemaLocations[id] = location
        else:
            for c in node.childNodes:
                if c.nodeType == elementType:
                    self._walkZeeRex(session, c)


