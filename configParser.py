
import os, sys, dynamic, time, glob
from utils import getFirstData, elementType
from bootstrap import BSParser, BootstrapDocument
from c3errors import FileDoesNotExistException, ConfigFileException, PermissionException, ObjectDoesNotExistException
from types import MethodType
from permissionHandler import PermissionHandler

from internal import defaultArchitecture

class C3Object(object):
    id = ""
    name = ""
    objectType = ""
    parent = None
    paths = {}
    subConfigs = {}
    objects = {}
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


    def _getDomFromFile(self, session, fileName):
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
            else:
                record = BSParser.process_document(session,doc)
        except Exception, e:
            raise ConfigFileException("Cannot parse %s: %s" % (fileName, e))
        dom = record.get_dom(session)

        return dom


    def _handleConfigNode(self, session, node):
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

    def __init__(self, session, config, parent=None):
        """The constructor for all Cheshire3 objects take the same arguments:
        session:  A Session object
        topNode:  The <config> or <subConfig> domNode for the configuration
        parent:   The object that provides the scope for this object.
        """

        self.docstring = ""
        self.parent = parent
        self.subConfigs = {}
        self.paths = {}
        self.objects = {}
        self.settings = {}
        self.defaults = {}
        self.permissionHandlers = {}
        self.unresolvedObjects = {}
        self.functionLogger = None
        self._objectRefs = []
        self._includeConfigStores = []
        
        pathObjects = {}
        
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
                elif (child.localName == "imports"):
                    # Do this now so we can reference
                    for mod in child.childNodes:
                        if mod.nodeType == elementType and mod.localName == "module":
                            name, objects, withname = ('', [], None)
                            for n in mod.childNodes:
                                if (n.nodeType == elementType):
                                    if (n.localName == 'name'):
                                        name = getFirstData(n)
                                    elif (n.localName == 'object'):
                                        objects.append(getFirstData(n))
                                    elif (n.localName == 'withName'):
                                        withname = getFirstData(n)
                            if (name):
                                dynamic.globalImport(name, objects, withname)
                            else:
                                raise(ConfigFileException('No name given for module to import in configFile for %s' % (self.id)))

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

        if (self.paths.has_key("pythonPath")):
            sys.path.append(self.paths['pythonPath'][1])

        # Allow any object to be set to debug
        # functionality of this dependent on object
        self.debug = self.get_setting(session, "debug", 0)
        
        for p in self.permissionHandlers.keys():
            if p[0:5] == 'c3fn:':
                self.add_auth(p[5:])

        # Built, maybe set function logging
        log = self.get_setting(session, 'log')
        if (log):
            logList = log.strip().split()
            for l in logList:
                self.add_logging(l)
            del self.settings['log']

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
            
        # Now check for configStore objects
        for csid in self._includeConfigStores:
            confStore = self.get_object(session, csid)
            if confStore != None:
                for rec in confStore:
                    # do something with config
                    node = rec.get_dom(session)
                    node= node.childNodes[0]
                    nid = node.getAttributeNS(None, 'id')
                    node.setAttributeNS(None, 'configStore', confStore.id)
                    self.subConfigs[nid] = node
                    ntype = node.getAttributeNS(None, 'type')
                    if ntype == 'index':
                        self.indexConfigs[nid] = node
                    elif ntype == 'protocolMap':
                        self.protocolMapConfigs[nid] = node
                    elif ntype == 'database':
                        self.databaseConfigs[nid] = node
                    elif ntype == '':
                        raise ConfigFileException("Object must have a type attribute: %s  -- in configStore %s" % (nid, csid))
                        

    def get_setting(self, session, id, default=None):
        """Return the value for a setting on this object."""
        return self.settings.get(id, default)
    
    def get_default(self, session, id, default=None): 
        """Return the default value for an option on this object"""
        return self.defaults.get(id, default)

    def get_object(self, session, id):
        """Return an object with the given id within this object's scope, or search upwards for it."""
        if (self.objects.has_key(id)):
            return self.objects[id]
        else:
	    config = self.get_config(session, id)
            if config:
                try:
                    obj = dynamic.makeObjectFromDom(session, config, self)
                except (ConfigFileException, AttributeError, ImportError):
                    # Push back up as is 
                    print "... while trying to build object with id '%s'" % id
                    print "... while getting it from object '%s'" % (self.id)
                    raise
                return obj
            elif (self.parent != None):
                return self.parent.get_object(session, id)
            else:
                raise ObjectDoesNotExistException(id)

    def get_config(self, session, id):
        """Return a configuration for the given object."""
        if (self.subConfigs.has_key(id)):
            return self.subConfigs[id]
        else:
            return None

    def get_path(self, session, id, default=None):
        """Return the named path"""
        if (self.paths.has_key(id)):
            path = self.paths[id]
            # Special handling for defaultPath :/
            if (id == "defaultPath" and not os.path.isabs(path)):
                p1 = self.parent.get_path(session, id, default)
                path = os.path.join(p1, path)
            return path
        elif (self.unresolvedObjects.has_key(id)):
            o = self.get_object(session, self.unresolvedObjects[id])
            self.paths[id] = o
            del self.unresolvedObjects[id]
            return o
        elif (self.parent != None):
            return self.parent.get_path(session, id, default)
        else:
            return default

    def add_logging(self, name):
        """ Set a named function to log invocations."""
        if (name == "__all__"):
            names = dir(self)
        else:
            names = [name]
        for name in names:
            if (hasattr(self, name) and callable(getattr(self,name)) and name[0] <> '_'):
                func = getattr(self, name)
                setattr(self, "__postlog_%s" % (name), getattr(self, name))
                code = """def mylogfn(self, *args, **kw):\n  if (hasattr(self,'__postlog_get_path')):\n    fn = self.__postlog_get_path\n  else:\n    fn = self.get_path\n  fl = fn(None, 'functionLogger');\n  if (fl):\n    fl.log(self, '%s', *args, **kw);\n  return self.__postlog_%s(*args, **kw);""" % (name, name)
                exec code
                setattr(self, name, MethodType(locals()['mylogfn'], self, self.__class__))

    def remove_logging(self, name):
        """Remove the logging from a named function."""
        if (name == "__all__"):
            names = dir(self)
        else:
            names = [name]
        for name in names:
            if (hasattr(self, name) and callable(getattr(self,name)) and name[0] <> '_' and hasattr(self, '__postlog_%s' % name)):
                setattr(self, name, getattr(self, '__postlog_%s' % name))
                delattr(self, '__postlog_%s' % name)

    def add_auth(self, name):
        """Add an authorisation layer on top of a named function."""
        if (hasattr(self, name) and callable(getattr(self,name)) and name[0] <> '_'):
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
            exec code
            setattr(self, name, MethodType(locals()['myauthfn'], self, self.__class__))


    def remove_auth(self, name):
        """Remove the authorisation requirement from the named function."""
        if (name == "__all__"):
            names = dir(self)
        else:
            names = [name]
        for name in names:
            if (hasattr(self, name) and callable(getattr(self,name)) and name[0] <> '_' and hasattr(self, '__postauth_%s' % name)):
                setattr(self, name, getattr(self, '__postauth_%s' % name))
                delattr(self, '__postauth_%s' % name)
