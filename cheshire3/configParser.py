
import os, sys, time, glob
import hashlib
import inspect
from types import MethodType

from cheshire3.session import Session

from cheshire3 import dynamic
from cheshire3.utils import getFirstData, elementType
from cheshire3.bootstrap import BSParser, BootstrapDocument
from cheshire3.bootstrap import BSLxmlParser
from cheshire3.exceptions import *
from cheshire3.permissionHandler import PermissionHandler
from cheshire3.internal import defaultArchitecture, get_api


from lxml import etree

class CaselessDictionary(dict):
    """ Uses lower case keys, but preserves keys as inserted."""
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
    """Base Class of Cheshire3 Object"""
    id = ""
    version = ""
    complexity = ""
    stability = ""
    checkSums = {}
    name = ""
    objectType = ""
    parent = None
    paths = {}
    subConfigs = {} # Will be a CaselessDictionary after __init__
    objects = {} # Will be a CaselessDictionary after __init__
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

    _possiblePaths = {'defaultPath' : {'docs' : 'Default path for this object.  Almost all other paths below this object will have this prepended if they are relative.'}}

    _possibleSettings = {'debug': {'docs' : "Set this object to debugging. Object specific results.", 'type' : int, 'options' : "0|1"},
                         'log' : {'docs' : 'Space separated list of function names to enable function logging for.'}
                         }
    _possibleDefaults = {}


    def _getDomFromFile(self, session, fileName, parser=''):
        """Read in an XML file from disk to get the configuration for this object."""
        # We need to be able to read in configurations from disk

        if not os.path.exists(fileName):
            raise(FileDoesNotExistException(fileName))
        
        f = file(fileName)
        doc = BootstrapDocument(f)

        # Look on self for instantiated parser, otherwise use bootstrap
        p = self.get_path(session, 'parser', None)
        try:
            if (p != None):
                record = p.process_document(session, doc)
            elif parser == 'minidom':
                record = BSParser.process_document(session, doc)
            else:
                record = BSLxmlParser.process_document(session,doc)
        except Exception as e:
            raise ConfigFileException("Cannot parse %s: %s" % (fileName, e))
        dom = record.get_dom(session)
        f.close()
        return dom


    def _handleConfigNode(self, session, node):
        pass

    def _handleLxmlConfigNode(self, session, node):
        pass

    # Return parsed value (eg Int, Bool, String etc)
    # Or raise an error
    def _verifyOption(self, type, value):
        return value

    def _verifySetting(self, type, value):
        params = defaultArchitecture.find_params(self.__class__)[1]
        info = params.get(type, {})

        if not info:
            raise ConfigFileException("Unknown Setting on '%s': %s" % (self.id, type))
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
            raise ConfigFileException("Unknown Default on '%s': %s" % (self.id, type))
        else:
            t = info.get('type', 0)
            if t:
                return t(value)
            else:
                return value


    def _parseIncludes(self, session, path):
        dom = self._getDomFromFile(session, path)
        for child2 in dom.childNodes[0].childNodes:
            if child2.nodeType == elementType:
                if child2.localName == "subConfigs":
                    self._recurseSubConfigs(session, child2)
                elif (child2.localName == "objects"):
                    # record object ref to instantiate
                    for obj in child2.childNodes:
                        if (obj.nodeType == elementType and obj.localName == "path"):
                            type = obj.getAttributeNS(None,'type')
                            id = obj.getAttributeNS(None,'ref')
                            self._objectRefs.append((id, type))

    def _recurseSubConfigs(self, session, child):
        for mod in child.childNodes:
            if mod.nodeType == elementType and mod.localName == "subConfig":
                id = mod.getAttributeNS(None,'id')
                self.subConfigs[id] = mod

                # Cache indexes and maps
                type = mod.getAttributeNS(None,'type')
                if type == 'index':
                    self.indexConfigs[id] = mod
                elif type == 'protocolMap':
                    self.protocolMapConfigs[id] = mod
                elif type == 'database':
                    self.databaseConfigs[id] = mod
                elif type == '':
                    raise ConfigFileException("Object must have a type attribute: %s" % id)
                    
            elif mod.nodeType == elementType and mod.localName == "path":
                if (mod.hasAttributeNS(None, 'type') and mod.getAttributeNS(None,'type') == 'includeConfigs'):
                    # Import into our space
                    if (mod.hasAttributeNS(None, 'ref')):
                        # <path type="includeConfigs" ref="configStore"/>
                        self._includeConfigStores.append(mod.getAttributeNS(None,'ref'))
                    else:
                        # <path type="includeConfigs">path/to/some/file.xml</path>
                        path = getFirstData(mod)
                        if  not os.path.isabs(path):
                            path = os.path.join(self.get_path(session, 'defaultPath'), path)
                        if os.path.isdir(path):
                            # include all configs in it at our space
                            files = glob.glob("%s/*.xml" % path)
                            for f in files:
                                self._parseIncludes(session, f)
                        else:
                            self._parseIncludes(session, path)
                else:
                    path = getFirstData(mod)
                    if  not os.path.isabs(path):
                        path = os.path.join(self.get_path(session, 'defaultPath'), path)
                    dom = self._getDomFromFile(session, path)
                    id = mod.getAttributeNS(None,'id')
                    self.subConfigs[id] = dom.childNodes[0]
                    ot = mod.getAttributeNS(None,'type')
                    if ot == 'database':
                        self.databaseConfigs[id] = dom.childNodes[0]


    def _parseLxmlIncludes(self, session, path):
        dom = self._getDomFromFile(session, path)
        for e in dom.iterchildren(tag=etree.Element):
            if e.tag == 'subConfigs':
                self._recurseLxmlSubConfigs(session, e)

    def _recurseLxmlSubConfigs(self, session, elem):
        for e in elem.iterchildren(tag=etree.Element):
            if e.tag == 'subConfig':
                id = e.attrib.get('id', '')
                typ = e.attrib.get('type', '')
                self.version = e.attrib.get('version', '')
                self.complexity = e.attrib.get('complexity', '')
                self.stability = e.attrib.get('stability', '')
                self.subConfigs[id] = e
                if typ == 'index':
                    self.indexConfigs[id] = e
                elif typ == 'protocolMap':
                    self.protocolMapConfigs[id] = e
                elif typ == 'database':
                    self.databaseConfigs[id] = e
                elif typ == '':
                    raise ConfigFileException("Object must have a type attribute: %s" % id)
            elif e.tag == 'path':
                typ = e.attrib.get('type', '')
                if typ == 'includeConfigs':
                    if 'ref' in e.attrib:
                        self._includeConfigStores.append(e.attrib['ref'])
                    else:
                        path = e.text
                        if not os.path.isabs(path):
                            path = os.path.join(self.get_path(session, 'defaultPath'), path)
                        if os.path.isdir(path):
                            files = glob.glob("%s/*.xml" % path)
                            for f in files:
                                self._parseLxmlIncludes(session, f)
                        else:
                            self._parseLxmlIncludes(session, path)
                else:
                    path = e.text
                    if not os.path.isabs(path):
                        path = os.path.join(self.get_path(session, 'defaultPath'), path)
                    dom = self._getDomFromFile(session, path)
                    id = e.attrib['id']
                    self.subConfigs[id] = dom
                    ot = e.attrib.get('type', '')
                    if ot == 'database':
                        self.databaseConfigs[id] = dom
 

               

    def __init__(self, session, config, parent=None):
        """The constructor for all Cheshire3 objects take the same arguments:
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
        
        pathObjects = {}
        
        # LXML
        if hasattr(config, 'attrib'):
            self.id = config.attrib.get('id', '')
            walker = config.iterchildren(tag=etree.Element)
            for e in walker:
                if e.tag == 'name':
                    self.name = e.text
                elif e.tag == 'objectType':
                    self.objectType = e.text
                elif e.tag == 'checkSums':
                    for e2 in e.iterchildren(tag=etree.Element):
                        # store checksum on self, and hash code against it
                        pt = e2.attrib.get('pathType', '__code__')
                        ct = e2.attrib.get('type', 'md5')
                        if pt != '__code__':
                            try:
                                self.pathCheckSums[pt].append((ct, e2.text))
                            except KeyError:
                                self.pathCheckSums[pt] = [(ct, e2.text)]
                        else:
                            self.checkSums[ct] = e2.text
                    
                elif e.tag == 'paths':
                    for e2 in e.iterchildren(tag=etree.Element):
                        try:
                            typ = e2.attrib['type']
                        except KeyError:
                            raise ConfigFileException("path must have type")
                        if e2.tag == 'path':
                            self.paths[typ] = e2.text
                        elif e2.tag == 'object':
                            try:
                                ref = e2.attrib['ref']
                            except KeyError:
                                raise ConfigFileException("object must have ref")
                            pathObjects[typ] = ref
                elif e.tag == 'subConfigs':
                    # recurse
                    self._recurseLxmlSubConfigs(session, e)
                elif e.tag == 'options':
                    for e2 in e.iterchildren(tag=etree.Element):
                        try:
                            typ = e2.attrib['type']
                        except KeyError:
                            raise ConfigFileException("option (setting/default) must have type")
                        if e2.tag == 'setting':
                            value = self._verifySetting(typ, e2.text)
                            self.settings[typ] = value
                        elif e2.tag == 'default':
                            value = self._verifyDefault(typ, e2.text)
                            self.defaults[typ] = value
                elif e.tag == 'actions':
                    pass
                elif e.tag == 'docs':
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
                                    self.paths[type] = value
                                elif child2.localName == "object":
                                    value = child2.getAttributeNS(None,'ref')
                                    pathObjects[type] = value
                    elif (child.localName == "subConfigs"):
                        # Pointers to dom nodes for config ids
                        self._recurseSubConfigs(session, child)

                    elif (child.localName == "objects"):
                        for obj in child.childNodes:
                            if (obj.nodeType == elementType and obj.localName == "path"):
                                type = obj.getAttributeNS(None,'type')
                                id = obj.getAttributeNS(None,'ref')
                                self._objectRefs.append((id, type))
                    elif (child.localName == "options"):
                        # See configInfo in ZeeRex
                        for child2 in child.childNodes:
                            if (child2.nodeType == elementType):
                                type = child2.getAttributeNS(None,'type')
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
                        # permission rqmts
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
        # functionality of this dependent on object
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
        log = self.get_setting(session, 'log', session.server.defaultFunctionLog)
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
                                dp = commands.getoutput('which %s' % fn)                        
                        else:
                            dp = self.get_path(session, 'defaultPath')
                        fn = os.path.join(dp, fn)
                    fh = file(fn)
                    data = fh.read()
                    fh.close()

                    m.update(data)
                    digest = m.hexdigest()
                    if digest != val:
                        raise IntegrityException("%s/%s (%s): %s" % (self.id, pt, fn, digest))
                
            
        
            
        # Now check for configStore objects
##         for csid in self._includeConfigStores:
##             confStore = self.get_object(session, csid)
##             if confStore != None:
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
##                         raise ConfigFileException("Object must have a type attribute: %s  -- in configStore %s" % (nid, csid))
                        

    def get_setting(self, session, id, default=None):
        """Return the value for a setting on this object."""
        return self.settings.get(id, default)
    
    def get_default(self, session, id, default=None): 
        """Return the default value for an option on this object"""
        return self.defaults.get(id, default)

    def get_object(self, session, id):
        """Return an object with the given id within this object's scope, or search upwards for it."""
        if (id in self.objects):
            return self.objects[id]
        else:
            config = self.get_config(session, id)
            if config is not None:
                try:
                    obj = dynamic.makeObjectFromDom(session, config, self)
                except (ConfigFileException, AttributeError, ImportError):
                    # Push back up as is 
                    self.log_critical(session, "... while trying to build object with id '%s'" % id)
                    self.log_critical(session, "... while getting it from object '%s'" % (self.id))
                    raise
                return obj
            elif (self.parent != None):
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
            # Special handling for defaultPath :/
            if (id == "defaultPath" and not os.path.isabs(path)):
                p1 = self.parent.get_path(session, id, default)
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
        elif (self.parent != None):
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
            if (hasattr(self, name) and callable(getattr(self,name)) and name[0] != '_'):
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
                setattr(self, name, MethodType(locals()['mylogfn'], self, self.__class__))

    def remove_logging(self, session, name):
        """Remove the logging from a named function."""
        if (name == "__all__"):
            names = dir(self)
        else:
            names = [name]
        for name in names:
            if (hasattr(self, name) and callable(getattr(self,name)) and name[0] != '_' and hasattr(self, '__postlog_%s' % name)):
                setattr(self, name, getattr(self, '__postlog_%s' % name))
                delattr(self, '__postlog_%s' % name)

    def add_auth(self, session, name):
        """Add an authorisation layer on top of a named function."""
        if (hasattr(self, name) and callable(getattr(self,name)) and name[0] != '_'):
            func = getattr(self, name)
            setattr(self, "__postauth_%s" % (name), func)
            code = """
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
            setattr(self, name, MethodType(locals()['myauthfn'], self, self.__class__))


    def remove_auth(self, session, name):
        """Remove the authorisation requirement from the named function."""
        if (name == "__all__"):
            names = dir(self)
        else:
            names = [name]
        for name in names:
            if (hasattr(self, name) and callable(getattr(self,name)) and name[0] != '_' and hasattr(self, '__postauth_%s' % name)):
                setattr(self, name, getattr(self, '__postauth_%s' % name))
                delattr(self, '__postauth_%s' % name)

    def log_lvl(self, session, lvl, msg, *args, **kw):
        if session.logger:
            session.logger.log_lvl(session, lvl, msg, *args, **kw)
        elif self.logger:
            self.logger.log_lvl(session, lvl, msg, *args, **kw)
        else:
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
    
