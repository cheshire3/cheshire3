"""ProtocolMap implemetations

A ProtocolMap maps incoming requests into local objects in order to handle
those requests.
e.g. dc.title -> l5r-idx-cardname object
"""

import sys
import os

from cheshire3.baseObjects import ProtocolMap
from cheshire3.exceptions import ConfigFileException,\
                                 ObjectDoesNotExistException
from cheshire3.utils import elementType, textType, flattenTexts
from cheshire3.cqlParser import modifierClauseType, indexType, relationType
from cheshire3 import dynamic

try:
    import cheshire3.web.srwExtensions as srwExtensions
except:
    srwExtensions = None


class ZeerexProtocolMap(ProtocolMap):
    """Abstract Base Class for ProtocolMaps based on the ZeeRex specification.
    
    http://zeerex.z3950.org/
    """
    protocol = ""
    version = ""
    c3Namespace = "http://www.cheshire3.org/schemas/explain/"

    _possiblePaths = {'zeerexPath': {'docs': "Path to ZeeRex file."}}

    def __init__(self, session, node, parent):
        ProtocolMap.__init__(self, session, node, parent)
        p = self.get_path(session, 'zeerexPath')
        if (p is None):
            raise ConfigFileException('ZeerexPath not specified for '
                                      'CQLConfig.')
        else:
            if not os.path.isabs(p):
                dfp = self.get_path(session, 'defaultPath')
                p = os.path.join(dfp, p)
            dom = self._getDomFromFile(session, p, parser='minidom')
        for c in dom.childNodes:
            if c.nodeType == elementType:
                self._walkZeeRex(session, c)    


class UpdateProtocolMap(ZeerexProtocolMap):
    """ProtocolMap for the SRU Record Update protocol.
    
    http://www.loc.gov/standards/sru/record-update/index.html
    """
    
    transformerHash = {}
    workflowHash = {}

    def __init__(self, session, node, parent):
        self.protocol = "http://www.loc.gov/zing/srw/update/"
        self.protocolNamespaces = protocolNamespaces
        self.recordNamespaces = recordNamespaces
        self.extensionNamespaces = extensionNamespaces
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
                if (txr is None):
                    raise ConfigFileException("No transformer to map to for "
                                              "%s" % (xsl))
                self.transformerHash[id] = txr
            self.recordNamespaces[name] = id
        elif node.localName == "supports":
            stype = node.getAttribute('type')
            data = flattenTexts(node)
            if (stype == 'operation'):
                wflw = node.getAttributeNS(self.c3Namespace, 'workflow')
                if (wflw):
                    flow = self.get_object(session, wflw)
                    if (flow is None):                        
                        raise ConfigFileException("No workflow to map to for "
                                                  "%s" % wflw)
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
        elif (node.localName == 'setting'):
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
    """ProtocolMap for the Contextual Query Language.
    
    http://www.loc.gov/standards/sru/specs/cql.html
    """
    
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
        self.protocolNamespaces = protocolNamespaces
        self.recordNamespaces = {}
        self.contextSetNamespaces = contextSetNamespaces
        self.profileNamespaces = profileNamespaces
        self.extensionNamespaces = extensionNamespaces

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
                raise ConfigFileException('Zeerex does not have default '
                                          'context set.')
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
        elif (uri in ['info:srw/cql-context-set/1/cql-v1.1',
                     'info:srw/cql-context-set/1/cql-v1.2'] and
              name == 'serverchoice' and
              hasattr(self, 'defaultIndex')):
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
            idx = self.indexHash.get((uri, name,
                                      ('relationModifier', 'relevant')),
                                     None)
        if (not idx and stem):
            idx = self.indexHash.get((uri, name,
                                      ('relationModifier', 'stem')),
                                     None)
        if (not idx and rms):
            for rm in rms:
                idx = self.indexHash.get((uri, name,
                                          ('relationModifier', rm)),
                                         None)
                if (idx):
                    break
        if (not idx):
            idx = self.indexHash.get((uri, name, ('relation', rel)), None)
        if (not idx):
            idx = self.indexHash.get((uri, name), None)
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
                if (txr is None):
                    raise ConfigFileException("No transformer to map to for "
                                              "%s" % (xsl))
                self.transformerHash[id] = txr
            self.recordNamespaces[name] = id
        elif node.localName == 'set':
            name = node.getAttribute('name')
            uri = node.getAttribute('identifier')
            if (name in self.prefixes and uri != self.prefixes[name]):
                raise ConfigFileException('Multiple URIs bound to same short '
                                          'name: %s -> %s' % (name, uri))
            self.prefixes[str(name)] = str(uri)
        elif node.localName == 'index':
            # Process indexes
            idxName = node.getAttributeNS(self.c3Namespace, 'index')
            indexObject = self.get_object(session, idxName)
            if indexObject is None:
                raise(ConfigFileException("[%s] No Index to map to for "
                                          "%s" % (self.id, idxName)))
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
                        if (c2.nodeType == elementType and
                            c2.localName == 'supports'):
                            idxName2 = c2.getAttributeNS(self.c3Namespace,
                                                         'index')
                            if (not idxName2):
                                indexObject2 = indexObject
                            else:
                                indexObject2 = self.get_object(session,
                                                               idxName2)
                                if indexObject2 is None:
                                    raise ConfigFileException(
                                              "[%s] No Index to map to for "
                                              "%s" % (self.id, idxName2)
                                    )
                            st = str(c2.getAttribute('type'))
                            val = str(flattenTexts(c2))
                            for m in maps:
                                self.indexHash[(m[0],
                                                m[1],
                                                (st, val))] = indexObject2

        elif (node.localName == 'map'):
            for c in node.childNodes:
                if (c.nodeType == elementType and c.localName == 'name'):
                    short = c.getAttribute('set')
                    index = flattenTexts(c)
                    index = index.lower()
                    uri = self.resolvePrefix(short)
                    if (not uri):
                        raise ConfigFileException("No mapping for %s in "
                                                  "Zeerex" % (short))
                    return (str(uri), str(index))
        elif (node.localName == 'default'):
            dtype = node.getAttribute('type')
            # XXX: would dtype.title() be nicer!?
            pname = "default" + dtype[0].capitalize() + dtype[1:]
            data = flattenTexts(node)
            if (data.isdigit()):
                data = int(data)
            elif data == 'false':
                data = 0
            elif data == 'true':
                data = 1
            setattr(self, pname, data)
        elif (node.localName == 'setting'):
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
            if stype in ['extraData', 'extraSearchData', 'extraScanData',
                         'extraExplainData', 'extension']:
                # function, xnType, sruName

                xn = node.getAttributeNS(self.c3Namespace, 'type')
                if (not xn in ['record', 'term', 'searchRetrieve', 'scan',
                               'explain', 'response']):
                    raise ConfigFileException('Unknown extension type %s' % xn)               
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
                        raise ConfigFileException("Cannot find handler "
                                                  "function %s (in %s)" %
                                                  (fn, repr(sys.path)))
                    self.sruExtensionMap[sru] = (xn, fn, data)
                else:
                    if (hasattr(srwExtensions, fn)):
                        fn = getattr(srwExtensions, fn)
                    else:
                        raise ConfigFileException('Cannot find handler '
                                                  'function %s in '
                                                  'srwExtensions.' % fn)
                    xform = node.getAttributeNS(self.c3Namespace,
                                                'sruFunction')
                    if not xform:
                        sruFunction = srwExtensions.simpleRequestXform
                    elif hasattr(srwExtensions, xform):
                        sruFunction = getattr(srwExtensions, xform)
                    else:
                        raise ConfigFileException('Cannot find transformation '
                                                  'function %s in '
                                                  'srwExtensions.' % xform)
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


protocolNamespaces = {
  'srw': 'http://www.loc.gov/zing/srw/',
  'xcql': 'http://www.loc.gov/zing/srw/xcql/',
  'diag': 'http://www.loc.gov/zing/srw/diagnostic/',
  'ucp': 'http://www.loc.gov/zing/srw/update/'
}

recordNamespaces = {
  'dc': 'info:srw/schema/1/dc-v1.1',
  'diag': 'info:srw/schema/1/diagnostic-v1.1',
  'mods': 'info:srw/schema/1/mods-v3.0',
  'onix': 'info:srw/schema/1/onix-v2.0',
  'marcxml': 'info:srw/schema/1/marcxml-v1.1',
  'ead': 'info:srw/schema/1/ead-2002',
  'ccg': 'http://srw.o-r-g.org/schemas/ccg/1.0/',
  'marcsgml': 'http://srw.o-r-g.org/schemas/marcsgml/12.0/',
  'metar': 'http://srw.o-r-g.org/schemas/metar/1.0/',
  'unesco': 'http://srw.o-r-g.org/schemas/unesco/1.0/',
  'zthes': 'http://zthes.z3950.org/xml/zthes-05.dtd',
  'zeerex': 'http://explain.z3950.org/dtd/2.0/',
  'rec': 'info:srw/schema/2/rec-1.0',
  'xpath': 'info:srw/schema/1/xpath-1.0'
}

contextSetNamespaces = {
  'cql': 'info:srw/cql-context-set/1/cql-v1.2',
  'srw': 'info:srw/cql-context-set/1/cql-v1.1',
  'dc': 'info:srw/cql-context-set/1/dc-v1.1',
  'bath': 'http://www.loc.gov/zing/cql/context-sets/bath/v1.1/',
  'zthes': 'http://zthes.z3950.org/cql/1.0/',
  'ccg': 'http://srw.cheshire3.org/contextSets/ccg/1.1/',
  'ccg_l5r': 'http://srw.cheshire3.org/contextSets/ccg/l5r/1.0/',
  'rec': 'info:srw/cql-context-set/2/rec-1.0',
  'net': 'info:srw/cql-context-set/2/net-1.0'
}

profileNamespaces = {
  'bath': 'http://zing.z3950.org/srw/bath/2.0/',
  'zthes': ' http://zthes.z3950.org/srw/0.5',
  'ccg': 'http://srw.cheshire3.org/profiles/ccg/1.0/',
  'srw': 'info:srw/profiles/1/base-profile-v1.1'
}

extensionNamespaces = {
  'schemaNegotiation': 'info:srw/extension/2/schemaNegotiation-1.0',
  'authenticationToken': 'info:srw/extension/2/auth-1.0'
}
