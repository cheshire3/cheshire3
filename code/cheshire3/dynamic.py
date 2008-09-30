
# Module wrapper into which we're going to import anything
# defined in configfiles
from cheshire3.utils import getFirstData, elementType
from cheshire3.exceptions import ConfigFileException
import sys

def makeObjectFromDom(session, topNode, parentObject):
    # Lots of indirections from xml to object
    objectType = None
    try:
        objectType = topNode.xpath('./objectType/text()')[0]
    except IndexError:
        from lxml import etree
        print etree.tostring(topNode)            
    except AttributeError:
        for c in topNode.childNodes:
            if (c.nodeType == elementType and c.localName == "objectType"):
                # Here's what we want to instantiate
                objectType = getFirstData(c)
                break
    if objectType == None:
        raise(ConfigFileException('No objectType set in config file.'))
    return buildObject(session, objectType, [topNode, parentObject])



def importObject(session, objectType):
    try:
        (modName, className) = objectType.rsplit('.', 1)
    except:
        raise ConfigFileException("Need module.class instead of %s" % objectType)

    try:
        m = __import__(modName)
    except ImportError as e:
        if objectType[:9] != "cheshire3":
            try:
                return importObject(session, "cheshire3.%s" % objectType)
            except: pass
        if session.logger:
            session.logger.log_critical(session, "Failed to import '%s'" % modName)
        raise e

    # now split and fetch bits
    mods = modName.split('.')
    for mn in mods[1:]:
        try:
            m = getattr(m, mn)
        except AttributeError as e:
            if objectType[:9] != "cheshire3":
                try:
                    return importObject(session, "cheshire3.%s" % objectType)
                except: pass
            if session.logger:
                session.logger.log_critical(session, "Failed to import %s during %s" % (m, modName))
            raise e

    try:
        parentClass = getattr(m, className)
    except AttributeError as e:
        if objectType[:9] != "cheshire3":
            try:
                return importObject(session, "cheshire3.%s" % objectType)
            except: pass
        if session.logger:
            session.logger.log_critical(session, "Module %s does not define class %s" % (modName, className))
        raise e
    return parentClass


def buildObject(session, objectType, args):

    parentClass = importObject(session, objectType)
    try:
        return parentClass(session, *args)    
    except:
        if session.logger:
            session.logger.log_critical(session, "Failed to create '%s' type of object" % (parentClass))
        raise
