
# Module wrapper into which we're going to import anything
# defined in configfiles
from utils import getFirstData, elementType
from c3errors import ConfigFileException
import sys

def makeObjectFromDom(session, topNode, parentObject):
    # Lots of indirections from xml to object
    objectType = None
    for c in topNode.childNodes:
        if (c.nodeType == elementType and c.localName == "objectType"):
            # Here's what we want to instantiate
            objectType = getFirstData(c)
            break
    if objectType == None:
        raise(ConfigFileException('No objectType set in config file.'))
    return buildObject(session, objectType, [topNode, parentObject])


def buildObject(session, objectType, args):
    objs = objectType.split('.')
    if len(objs) < 2:
        raise ConfigFileException("Need module.class instead of %s" % objectType) 
    try:
        globalImport(objs[0], [objs[1]])
    except ImportError:
        print "ERROR: Failed to import '%s'" % objs[0]
        raise
    parentClass = globals()[objs[0]]
    for o in objs[1:]:
        parentClass = getattr(parentClass, o)
    try:
        return parentClass(session, *args)    
    except:
        print "ERROR: Failed to create '%s' type of object" % (objs[0])
        raise

	
def globalImport(module, objects=[], name=None):
    # With thanks to:
    # http://pleac.sourceforge.net/pleac_python/packagesetc.html

    nname = module
    loaded = __import__(module)
    for mod in (module.split(".")[1:]):
        nname = mod
        loaded = getattr(loaded, mod)
    if name != None:
        globals()[name] = loaded
    else:
        globals()[nname] = loaded

    if (len(objects) == 1 and objects[0] == "*"):
        objects = dir(loaded)

    for o in objects:
        if (o[0] != "_"):
            try:
                globals()[o] = getattr(loaded, o)
            except AttributeError:
                print "ERROR: Failed to load class '%s' from module '%s'" % (o, loaded.__name__)
                raise

    return loaded
