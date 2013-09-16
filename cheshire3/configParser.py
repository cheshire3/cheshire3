
import os
import sys
import time
import glob
import hashlib
import inspect
import urllib2

from string import Template
from types import MethodType
from urlparse import urlsplit

from lxml import etree

from cheshire3.session import Session
from cheshire3 import dynamic
from cheshire3.utils import getFirstData, elementType, getShellResult
from cheshire3.bootstrap import BSParser, BootstrapDocument
from cheshire3.bootstrap import BSLxmlParser
from cheshire3.exceptions import *
from cheshire3.permissionHandler import PermissionHandler
from cheshire3.internal import defaultArchitecture, get_api, cheshire3Home,\
                               cheshire3Root, cheshire3Dbs, cheshire3Www,\
                               CONFIG_NS


cheshire3Paths = {'cheshire3Home': cheshire3Home,
                  'cheshire3Root': cheshire3Root,
                  'cheshire3Dbs': cheshire3Dbs,
                  'cheshire3Www': cheshire3Www
                  } 


class CaselessDictionary(dict):
    """A case-insensitive dictionary.
    
    A dictionary that is case-insensitive when searching, but also preserves 
    the keys as inserted.
    """
    
    def __init__(self, initval={}):
        if isinstance(initval, dict):
            for key, value in initval.iteritems():
                self.__setitem__(key, value)
        elif isinstance(initval, list):
            for (key, value) in initval:
                self.__setitem__(key, value)
            
    def __contains__(self, key):
        return dict.__contains__(self, key.lower())
  
    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())['val'] 
  
    def __setitem__(self, key, value):
        return dict.__setitem__(self, key.lower(), {'key': key, 'val': value})

    def get(self, key, default=None):
        try:
            v = dict.__getitem__(self, key.lower())
        except KeyError:
            return default
        else:
            return v['val']
    
    def items(self):
        return [(v['key'], v['val']) for v in dict.itervalues(self)]
    
    def keys(self):
        return [v['key'] for v in dict.itervalues(self)]
    
    def values(self):
        return [v['val'] for v in dict.itervalues(self)]
    
    def iteritems(self):
        for v in dict.itervalues(self):
            yield v['key'], v['val']
        
    def iterkeys(self):
        for v in dict.itervalues(self):
            yield v['key']
        
    def itervalues(self):
        for v in dict.itervalues(self):
            yield v['val']
    

class C3Object(object):
    """Abstract Base Class for Cheshire3 Objects."""
    
    id = ""
    version = ""
    complexity = ""
    stability = ""
    checkSums = {}
    name = ""
    objectType = ""
    parent = None
    paths = {}
    subConfigs = {}  # Will be a CaselessDictionary after __init__
    objects = {}     # Will be a CaselessDictionary after __init__
    configStore = None
    settings = {}
    defaults = {}
    functionLogger = None
    permissionHandlers = {}

    unresolvedObjects = {}
    _settings = {}
    _defaults = {}
    
    # temp storage
    _includeConfigStores = []
    _objectRefs = []

    _possiblePaths = {
        'defaultPath': {
            'docs': ('Default path for this object. Almost all other paths '
                     'below this object will have this prepended if they are '
                     'relative.')
        }
    }

    _possibleSettings = {
        'debug': {
            'docs': "Set this object to debugging. Object specific results.",
                    'type': int,
                    'options': "0|1"
        },
        'log': {
            'docs': ('Space separated list of function names to enable '
                     'function logging for.')}
    }

    _possibleDefaults = {}

    def _getDomFromFile(self, session, fileName, parser=''):
        """Read, parse and return configuration from a file.

        Read in an XML file from disk to get the configuration for this
        object.

        Delegates to ``_getDomFromUrl``.
        """
        return self._getDomFromUrl(session, "file://" + fileName, parser)

    def _getDomFromUrl(self, session, url, parser=''):
        """Read, parse and return configuration from a file.

        Read in an XML file to get the configuration for this object.
        """
        # We need to be able to read in configurations
        urlparts = urlsplit(url)
        if urlparts.scheme in ('http', 'https'):
            f = urllib2.urlopen(url)
        elif urlparts.scheme == "irods":
            try:
                from cheshire3.grid.irods_utils import open_irodsUrl
            except ImportError:
                self.log_error(session,
                               "Unable to include file at {0}, "
                               "Missing Dependency: irods (PyRods)"
                               )
                return
            else:
                f = open_irodsUrl(url)
            if not f:
                self.log_error(session,
                               "Unable to include file at {0}, "
                               "File not found".format(url)
                               )
                return
        else:
            if not os.path.isfile(urlparts.path):
                raise FileDoesNotExistException(urlparts.path)
            f = open(urlparts.path, 'r')
        doc = BootstrapDocument(f)
        # Look on self for instantiated parser, otherwise use bootstrap
        p = self.get_path(session, 'parser', None)
        try:
            if (p is not None):
                record = p.process_document(session, doc)
            elif parser == 'minidom':
                record = BSParser.process_document(session, doc)
            else:
                record = BSLxmlParser.process_document(session, doc)
        except Exception as e:
            raise ConfigFileException("Cannot parse %s: %s" % (url, e))
        dom = record.get_dom(session)
        f.close()
        return dom

    def _handleConfigNode(self, session, node):
        """Handle DOM (4Suite/minidom/Domlette) configuration node.

        Handle config node when parsed as a DOM (4Suite/minidom/Domlette)
        DEPRECATED in favour of lxml.etree parsed configurations.
        """
        pass

    def _handleLxmlConfigNode(self, session, node):
        """Handle config node parsed by lxml.etree."""
        pass

    def _verifyOption(self, type, value):
        # Return parsed value (eg Int, Bool, String etc) or raise an error
        return value

    def _verifySetting(self, type, value):
        params = defaultArchitecture.find_params(self.__class__)[1]
        info = params.get(type, {})

        if not info:
            msg = "Unknown Setting on '%s': %s" % (self.id, type)
            raise ConfigFileException(msg)
        else:
            t = info.get('type', 0)
            if t:
                return t(value)
            else:
                return value

    def _verifyDefault(self, type, value):
        params = defaultArchitecture.find_params(self.__class__)[2]
        info = params.get(type, {})
        if not info:
            msg = "Unknown Default on '%s': %s" % (self.id, type)
            raise ConfigFileException(msg)
        else:
            t = info.get('type', 0)
            if t:
                return t(value)
            else:
                return value

    def _parseIncludes(self, session, path):
        if urlsplit(path).scheme:
            dom = self._getDomFromUrl(session, path)
        else:
            dom = self._getDomFromFile(session, path)
        for child2 in dom.childNodes[0].childNodes:
            if child2.nodeType == elementType:
                if child2.localName == "subConfigs":
                    self._recurseSubConfigs(session, child2)
                elif (child2.localName == "objects"):
                    # record object ref to instantiate
                    for obj in child2.childNodes:
                        if (obj.nodeType == elementType and
                            obj.localName == "path"):
                            type = obj.getAttributeNS(None, 'type')
                            id = obj.getAttributeNS(None, 'ref')
                            self._objectRefs.append((id, type))

    def _recurseSubConfigs(self, session, child):
        for mod in child.childNodes:
            if mod.nodeType == elementType and mod.localName == "subConfig":
                id = mod.getAttributeNS(None, 'id')
                self.subConfigs[id] = mod

                # Cache indexes and maps
                type = mod.getAttributeNS(None, 'type')
                if type == 'index':
                    self.indexConfigs[id] = mod
                elif type == 'protocolMap':
                    self.protocolMapConfigs[id] = mod
                elif type == 'database':
                    self.databaseConfigs[id] = mod
                elif type == '':
                    msg = "Object must have a type attribute: %s" % id
                    raise ConfigFileException(msg)

            elif mod.nodeType == elementType and mod.localName == "path":
                if (mod.hasAttributeNS(None, 'type') and
                    mod.getAttributeNS(None, 'type') == 'includeConfigs'):
                    # Import into our space
                    if (mod.hasAttributeNS(None, 'ref')):
                        # <path type="includeConfigs" ref="configStore"/>
                        self._includeConfigStores.append(
                            mod.getAttributeNS(None, 'ref')
                        )
                    else:
                        # <path type="includeConfigs">path/to/file.xml</path>
                        path = getFirstData(mod)
                        # Expand user-specific paths
                        path = os.path.expanduser(path)
                        if not (urlsplit(path).scheme or os.path.isabs(path)):
                            dfp = self.get_path(session, 'defaultPath')
                            if urlsplit(dfp).scheme:
                                path = '/'.join((dfp, path))
                            else:
                                path = os.path.join(dfp, path)
                        if os.path.isdir(path):
                            # include all configs in it at our space
                            files = glob.glob("%s/*.xml" % path)
                            for f in files:
                                self._parseIncludes(session, f)
                        else:
                            self._parseIncludes(session, path)
                else:
                    path = getFirstData(mod)
                    # Expand user-specific paths
                    path = os.path.expanduser(path)
                    if not (urlsplit(path).scheme or os.path.isabs(path)):
                        dfp = self.get_path(session, 'defaultPath')
                        if urlsplit(dfp).scheme:
                            path = '/'.join((dfp, path))
                        else:
                            path = os.path.join(dfp, path)
                    if urlsplit(path).scheme:
                        dom = self._getDomFromUrl(session, path)
                    else:
                        dom = self._getDomFromFile(session, path)
                    id = mod.getAttributeNS(None, 'id')
                    self.subConfigs[id] = dom.childNodes[0]
                    ot = mod.getAttributeNS(None, 'type')
                    if ot == 'database':
                        self.databaseConfigs[id] = dom.childNodes[0]

    def _parseLxmlIncludes(self, session, path):
        if urlsplit(path).scheme:
            dom = self._getDomFromUrl(session, path)
        else:
            dom = self._getDomFromFile(session, path)
        idt = dom.attrib.get('id', '')
        if dom.tag in ['config', '{%s}config' % CONFIG_NS] and idt:
            self.subConfigs[idt] = dom
        else:
            for e in dom.iterchildren(tag=etree.Element):
                if e.tag in ['subConfigs', '{%s}subConfigs' % CONFIG_NS]:
                    self._recurseLxmlSubConfigs(session, e)

    def _recurseLxmlSubConfigs(self, session, elem):
        for e in elem.iterchildren(tag=etree.Element):
            if e.tag in ['subConfig', '{%s}subConfig' % CONFIG_NS]:
                id = e.attrib.get('id',
                                  e.attrib.get('{%s}id' % CONFIG_NS, ''))
                typ = e.attrib.get('type',
                                   e.attrib.get('{%s}type' % CONFIG_NS, ''))
                self.subConfigs[id] = e
                if typ == 'index':
                    self.indexConfigs[id] = e
                elif typ == 'protocolMap':
                    self.protocolMapConfigs[id] = e
                elif typ == 'database':
                    self.databaseConfigs[id] = e
                elif typ == '':
                    msg = "Object must have a type attribute: %s" % id
                    raise ConfigFileException(msg)
            elif e.tag in ['path', '{%s}path' % CONFIG_NS]:
                typ = e.attrib.get('type', '')
                if typ == 'includeConfigs':
                    if 'ref' in e.attrib:
                        self._includeConfigStores.append(e.attrib['ref'])
                    else:
                        path = e.text
                        # Expand user-specific paths
                        path = os.path.expanduser(path)
                        if not (urlsplit(path).scheme or os.path.isabs(path)):
                            dfp = self.get_path(session, 'defaultPath')
                            if urlsplit(dfp).scheme:
                                path = '/'.join((dfp, path))
                            else:
                                path = os.path.join(dfp, path)
                        if os.path.isdir(path):
                            files = glob.glob("%s/*.xml" % path)
                            for f in files:
                                self._parseLxmlIncludes(session, f)
                        else:
                            self._parseLxmlIncludes(session, path)
                else:
                    path = e.text
                    # Check whether path is a URL
                    if urlsplit(path).scheme:
                        dom = self._getDomFromUrl(session, path)
                    else:
                        # A local filesystem path
                        # Expand user-specific paths
                        path = os.path.expanduser(path)
                        if not (urlsplit(path).scheme or os.path.isabs(path)):
                            dfp = self.get_path(session, 'defaultPath')
                            if urlsplit(dfp).scheme:
                                path = '/'.join((dfp, path))
                            else:
                                path = os.path.join(dfp, path)
                        if urlsplit(path).scheme:
                            dom = self._getDomFromUrl(session, path)
                        else:
                            dom = self._getDomFromFile(session, path)
                    id = e.attrib['id']
                    self.subConfigs[id] = dom
                    ot = e.attrib.get('type', '')
                    if ot == 'database':
                        self.databaseConfigs[id] = dom

    def __init__(self, session, config, parent=None):
        """Constructor inherited by all configured Cheshire3 objects.

        The constructor for all Cheshire3 objects take the same arguments:
        session:  A Session object
        topNode:  The <config> or <subConfig> domNode for the configuration
        parent:   The object that provides the scope for this object.
        """

        self.docstring = ""
        self.parent = parent
        self.subConfigs = CaselessDictionary()
        self.paths = {}
        self.objects = CaselessDictionary()
        self.settings = {}
        self.defaults = {}
        self.permissionHandlers = {}
        self.unresolvedObjects = {}
        self.functionLogger = None
        self._objectRefs = []
        self._includeConfigStores = []
        self.logger = None
        self.checkSums = {}
        self.pathCheckSums = {}

        self.version = ""
        self.complexity = ""
        self.stability = ""
        
        self.initTime = time.time()
        
        pathObjects = {}
        
        # LXML
        if hasattr(config, 'attrib'):
            self.id = config.attrib.get('id', '')
            self.version = config.attrib.get('version', '')
            self.complexity = config.attrib.get('complexity', '')
            self.stability = config.attrib.get('stability', '')

            walker = config.iterchildren(tag=etree.Element)
            for e in walker:
                if e.tag in ['name', '{%s}name' % CONFIG_NS]:
                    self.name = e.text
                elif e.tag in ['objectType', '{%s}objectType' % CONFIG_NS]:
                    self.objectType = e.text
                elif e.tag in ['checkSums', '{%s}checkSums' % CONFIG_NS]:
                    for e2 in e.iterchildren(tag=etree.Element):
                        # Store checksum on self, and hash code against it
                        pt = e2.attrib.get('pathType', '__code__')
                        ct = e2.attrib.get('type', 'md5')
                        if pt != '__code__':
                            try:
                                self.pathCheckSums[pt].append((ct, e2.text))
                            except KeyError:
                                self.pathCheckSums[pt] = [(ct, e2.text)]
                        else:
                            self.checkSums[ct] = e2.text
                    
                elif e.tag in ['paths', '{%s}paths' % CONFIG_NS]:
                    for e2 in e.iterchildren(tag=etree.Element):
                        try:
                            typ = e2.attrib['type']
                        except KeyError:
                            raise ConfigFileException("path must have type")
                        if e2.tag in ['path', '{%s}path' % CONFIG_NS]:
                            # Allow template strings in paths
                            # e.g. ${cheshire3Home}/foo/bar
                            pathTmpl = Template(e2.text)
                            sub = pathTmpl.safe_substitute
                            self.paths[typ] = sub(cheshire3Paths)
                        elif e2.tag in ['object', '{%s}object' % CONFIG_NS]:
                            try:
                                ref = e2.attrib['ref']
                            except KeyError:
                                msg = "object must have ref"
                                raise ConfigFileException(msg)
                            pathObjects[typ] = ref
                elif e.tag in ['subConfigs', '{%s}subConfigs' % CONFIG_NS]:
                    # Recurse
                    self._recurseLxmlSubConfigs(session, e)
                elif e.tag in ['options', '{%s}options' % CONFIG_NS]:
                    for e2 in e.iterchildren(tag=etree.Element):
                        try:
                            typ = e2.attrib['type']
                        except KeyError:
                            msg = "option (setting/default) must have type"
                            raise ConfigFileException(msg)
                        if e2.tag in ['setting', '{%s}setting' % CONFIG_NS]:
                            value = self._verifySetting(typ, e2.text)
                            self.settings[typ] = value
                        elif e2.tag in ['default', '{%s}default' % CONFIG_NS]:
                            value = self._verifyDefault(typ, e2.text)
                            self.defaults[typ] = value
                elif e.tag in ['actions', '{%s}actions' % CONFIG_NS]:
                    pass
                elif e.tag in ['docs', '{%s}docs' % CONFIG_NS]:
                    self.docstring = e.text
                else:
                    self._handleLxmlConfigNode(session, e)
            
            del walker
            
        else:
            if (config.hasAttributeNS(None, 'id')):
                self.id = config.getAttributeNS(None, 'id')

            for child in config.childNodes:
                if child.nodeType == elementType:
                    if child.localName == "name":
                        self.name = getFirstData(child)
                    elif (child.localName == "objectType"):
                        self.objectType = getFirstData(child)
                    elif (child.localName == "paths"):
                        # Configure self with paths
                        for child2 in child.childNodes:
                            if child2.nodeType == elementType:
                                type = child2.getAttributeNS(None, 'type')
                                if child2.localName == "path":
                                    value = getFirstData(child2)
                                    # Allow template strings in paths
                                    # e.g. ${cheshire3Home}/foo/bar
                                    pathTmpl = Template(value)
                                    sub = pathTmpl.safe_substitute
                                    self.paths[type] = sub(cheshire3Paths)
                                elif child2.localName == "object":
                                    value = child2.getAttributeNS(None, 'ref')
                                    pathObjects[type] = value
                    elif (child.localName == "subConfigs"):
                        # Pointers to dom nodes for config ids
                        self._recurseSubConfigs(session, child)

                    elif (child.localName == "objects"):
                        for obj in child.childNodes:
                            if (obj.nodeType == elementType and
                                obj.localName == "path"):
                                type = obj.getAttributeNS(None, 'type')
                                id = obj.getAttributeNS(None, 'ref')
                                self._objectRefs.append((id, type))
                    elif (child.localName == "options"):
                        # See configInfo in ZeeRex
                        for child2 in child.childNodes:
                            if (child2.nodeType == elementType):
                                type = child2.getAttributeNS(None, 'type')
                                if (child2.localName == "setting"):
                                    dc = getFirstData(child2)
                                    if (dc):
                                        value = self._verifySetting(type, dc)
                                        self.settings[type] = value
                                elif (child2.localName == "default"):
                                    dc = getFirstData(child2)
                                    if (dc):
                                        value = self._verifyDefault(type, dc)
                                        self.defaults[type] = value
                    elif (child.localName == "actions"):
                        # Permission rqmts
                        for child2 in child.childNodes:
                            if child2.nodeType == elementType:
                                p = PermissionHandler(child2, self)
                                self.permissionHandlers[p.actionIdentifier] = p
                    elif (child.localName == "docs"):
                        # Add per configuration documentation to docs stack.
                        self.docstring = getFirstData(child)
                    else:
                        self._handleConfigNode(session, child)
        
        if ('pythonPath' in self.paths):
            sys.path.append(self.paths['pythonPath'][1])

        # Allow any object to be set to debug
        # Functionality of this dependent on object
        self.debug = self.get_setting(session, "debug", 0)
        
        for p in self.permissionHandlers.keys():
            if p[0:5] == 'c3fn:':
                self.add_auth(p[5:])

        # Dynamically Instantiate objects. This is mindbending :}
        # Mindbending2: JIT building!
        if self.parent:
            self.parent.objects[self.id] = self
        for o in (self._objectRefs):
            # Instantiate
            obj = self.get_object(session, o[0])

        # Add default Object types to paths
        for t in pathObjects.keys():
            self.unresolvedObjects[t] = pathObjects[t]

        # Built, maybe set function logging
        log = self.get_setting(session,
                               'log',
                               session.server.defaultFunctionLog)
        if log:
            fl = self.get_path(session, 'functionLogger')
            if fl != self:
                self.functionLogger = fl
                logList = log.strip().split()
                for l in logList:
                    self.add_logging(session, l)
                try:
                    del self.settings['log']
                except KeyError:
                    # from default
                    pass

        # now checksum self
        if self.checkSums:
            code = inspect.getsource(self.__class__)
            for (ct, val) in self.checkSums.items():
                m = hashlib.new(ct)
                m.update(code)               
                digest = m.hexdigest()
                if digest != val:
                    raise IntegrityException(self.id + ": " + digest)

        if self.pathCheckSums:
            # step through each referenced file and check
            for (pt, chk) in self.pathCheckSums.items():
                for (ct, val) in chk:
                    m = hashlib.new(ct)
                    # read in file
                    fn = self.get_path(session, pt)
                    if not os.path.isabs(fn):
                        if pt == 'executable':
                            # search
                            dp = self.get_path('session', 'executablePath', '')
                            if not dp:
                                dp = getShellResult('which {0}'.format(fn))
                      
                        else:
                            dp = self.get_path(session, 'defaultPath')
                        fn = os.path.join(dp, fn)
                    fh = file(fn)
                    data = fh.read()
                    fh.close()

                    m.update(data)
                    digest = m.hexdigest()
                    if digest != val:
                        msg = "%s/%s (%s): %s" % (self.id, pt, fn, digest)
                        raise IntegrityException(msg)
            
        # Now check for configStore objects
##         for csid in self._includeConfigStores:
##             confStore = self.get_object(session, csid)
##             if confStore is not None:
##                 for rec in confStore:
##                     # do something with config
##                     node = rec.get_dom(session)
##                     node= node.childNodes[0]
##                     nid = node.getAttributeNS(None, 'id')
##                     node.setAttributeNS(None, 'configStore', confStore.id)
##                     self.subConfigs[nid] = node
##                     ntype = node.getAttributeNS(None, 'type')
##                     if ntype == 'index':
##                         self.indexConfigs[nid] = node
##                     elif ntype == 'protocolMap':
##                         self.protocolMapConfigs[nid] = node
##                     elif ntype == 'database':
##                         self.databaseConfigs[nid] = node
##                     elif ntype == '':
##                         msg = ("Object must have a type attribute: %s  -- "
##                                "in configStore %s" % (nid, csid))
##                         raise ConfigFileException(msg)

    def get_setting(self, session, id, default=None):
        """Return the value for a setting on this object."""
        return self.settings.get(id, default)
    
    def get_default(self, session, id, default=None): 
        """Return the default value for an option on this object"""
        return self.defaults.get(id, default)

    def get_object(self, session, id):
        """Return the object with the given id.
        
        Searches first within this object's scope, or search upwards for it.
        """
        if (id in self.objects):
            return self.objects[id]
        else:
            config = self.get_config(session, id)
            if config is not None:
                try:
                    obj = dynamic.makeObjectFromDom(session, config, self)
                except (ConfigFileException, AttributeError, ImportError):
                    # Push back up as is
                    self.log_critical(session,
                                      "... while trying to build object with "
                                      "id '%s'" % id)
                    self.log_critical(session,
                                      "... while getting it from object "
                                      "'%s'" % (self.id))
                    raise
                return obj
            elif (self.parent is not None):
                return self.parent.get_object(session, id)
            else:
                raise ObjectDoesNotExistException(id)

    def get_config(self, session, id):
        """Return a configuration for the given object."""
        if (id in self.subConfigs):
            return self.subConfigs[id]
        else:
            return None

    def get_path(self, session, id, default=None):
        """Return the named path"""
        if (id in self.paths):
            path = self.paths[id]
            # Handle user-relative paths
            try:
                path = os.path.expanduser(path)
            except (TypeError, AttributeError):
                pass
            # Special handling for defaultPath :/
            if (id == "defaultPath" and
                not (urlsplit(path).scheme or os.path.isabs(path))
            ):
                p1 = self.parent.get_path(session, id, default)
                if urlsplit(p1).scheme:
                    path = '/'.join((p1, path))
                else:
                    path = os.path.join(p1, path)
            return path
        elif (id in self.unresolvedObjects):
            o = self.get_object(session, self.unresolvedObjects[id])
            self.paths[id] = o
            try:
                del self.unresolvedObjects[id]
            except KeyError:
                pass
            return o
        elif (self.parent is not None):
            return self.parent.get_path(session, id, default)
        else:
            return default

    def add_logging(self, session, name):
        """ Set a named function to log invocations."""
        if (name == "__all__"):
            names = get_api(self, True)
        elif name == "__api__":
            names = get_api(self)
        else:
            names = [name]
        for name in names:
            if (hasattr(self, name) and
                callable(getattr(self, name)) and
                name[0] != '_'):
                func = getattr(self, name)
                setattr(self, "__postlog_%s" % (name), getattr(self, name))
                code = """
def mylogfn(self, *args, **kw):
    if (isinstance(args[0], Session)):
        sess = args[0]
    else:
        sess = None
    fl = self.functionLogger
    if (fl):
        fl.log_fn(sess, self, '%s', *args, **kw);
    return self.__postlog_%s(*args, **kw);""" % (name, name)
                exec(code)
                setattr(self, name,
                        MethodType(locals()['mylogfn'], self, self.__class__))

    def remove_logging(self, session, name):
        """Remove the logging from a named function."""
        if (name == "__all__"):
            names = dir(self)
        else:
            names = [name]
        for name in names:
            if (hasattr(self, name) and callable(getattr(self, name)) and
                name[0] != '_' and hasattr(self, '__postlog_%s' % name)):
                setattr(self, name, getattr(self, '__postlog_%s' % name))
                delattr(self, '__postlog_%s' % name)

    def add_auth(self, session, name):
        """Add an authorisation layer on top of a named function."""
        if (hasattr(self, name) and callable(getattr(self, name)) and
            name[0] != '_'):
            func = getattr(self, name)
            setattr(self, "__postauth_%s" % (name), func)
            code = """\
def myauthfn(self, session, *args, **kw):
    p = self.permissionHandlers['c3fn:%s']
    if (p):
        if not session or not session.user:
            raise PermissionException('Authenticated user required to call %s')
        if not p.hasPermission(session, session,user):
            raise PermissionException('Permission required to call %s')   
    return self.__postauth_%s(*args, **kw);
""" % (name, name, name, name)
            exec(code)
            setattr(self, name,
                    MethodType(locals()['myauthfn'], self, self.__class__))

    def remove_auth(self, session, name):
        """Remove the authorisation requirement from the named function."""
        if (name == "__all__"):
            names = dir(self)
        else:
            names = [name]
        for name in names:
            if (hasattr(self, name) and callable(getattr(self, name)) and
                name[0] != '_' and hasattr(self, '__postauth_%s' % name)):
                setattr(self, name, getattr(self, '__postauth_%s' % name))
                delattr(self, '__postauth_%s' % name)

    def log_lvl(self, session, lvl, msg, *args, **kw):
        if session.logger:
            session.logger.log_lvl(session, lvl, msg, *args, **kw)
        elif self.logger:
            self.logger.log_lvl(session, lvl, msg, *args, **kw)
        else:
            if type(msg) == unicode:
                msg = msg.encode('utf8')
            sys.stdout.write(msg)
            sys.stdout.flush()
            #logger = self.get_path(session, 'logger')
            #if logger:
            #    self.logger = logger
            #    logger.log_lvl(session, lvl, msg, *args, **kw)

    def log(self, session, msg, *args, **kw):
        self.log_lvl(session, 0, *args, **kw)

    def log_debug(self, session, msg, *args, **kw):
        self.log_lvl(session, 10, msg, *args, **kw)

    def log_info(self, session, msg, *args, **kw):
        self.log_lvl(session, 20, msg, *args, **kw)

    def log_warning(self, session, msg, *args, **kw):
        self.log_lvl(session, 30, msg, *args, **kw)

    def log_error(self, session, msg, *args, **kw):
        self.log_lvl(session, 40, msg, *args, **kw)

    def log_critical(self, session, msg, *args, **kw):
        self.log_lvl(session, 50, msg, *args, **kw)
