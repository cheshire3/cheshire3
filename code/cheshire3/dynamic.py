"""Cheshire3 configured object dynamic creation.

Module to support dynamic creation of Cheshire3 objects based on XML
configurations.
"""

import sys

from types import ModuleType

from cheshire3.utils import getFirstData, elementType
from cheshire3.exceptions import ConfigFileException
from cheshire3.internal import CONFIG_NS


def makeObjectFromDom(session, topNode, parentObject):
    # Lots of indirections from xml to object
    objectType = None
    try:
        objectType = topNode.xpath('./objectType/text()')[0]
    except IndexError:
        # May have namespace
        try:
            objectType = topNode.xpath('./c3:objectType/text()', 
                                       namespaces={'c3': CONFIG_NS})[0]
        except IndexError:
            from lxml import etree
            print etree.tostring(topNode)
    except AttributeError:
        # Not an Lxml config node
        for c in topNode.childNodes:
            if (c.nodeType == elementType and c.localName == "objectType"):
                # Here's what we want to instantiate
                objectType = getFirstData(c)
                break
    if objectType is None:
        raise(ConfigFileException('No objectType set in config file.'))
    else:
        objectType = objectType.strip()
    return buildObject(session, objectType, [topNode, parentObject])


def importObject(session, objectType):
    try:
        (modName, className) = objectType.rsplit('.', 1)
    except:
        msg = "Need module.class instead of %s" % objectType
        raise ConfigFileException(msg)
    try:
        m = __import__(modName)
    except ImportError as e:
        if not objectType.startswith("cheshire3"):
            try:
                return importObject(session, "cheshire3.%s" % objectType)
            except:
                pass
        try:
            raise e
        finally:
            try:
                session.logger.log_lvl(session,
                                       50,
                                       "Module %s does not define class "
                                       "%s" % (modName, className))
            except AttributeError:
                # Most likely session is None or session.logger is None
                pass
    # Now split and fetch bits
    mods = modName.split('.')
    for mn in mods[1:]:
        try:
            m = getattr(m, mn)
        except AttributeError as e:
            if not objectType.startswith("cheshire3"):
                try:
                    return importObject(session, "cheshire3.%s" % objectType)
                except:
                    pass
            try:
                raise e
            finally:
                try:
                    session.logger.log_lvl(session,
                                           50,
                                           "Module %s does not define class "
                                           "%s" % (modName, className))
                except AttributeError:
                    # Most likely session is None or session.logger is None
                    pass
    try:
        parentClass = getattr(m, className)
    except AttributeError as e:
        if not objectType.startswith("cheshire3"):
            try:
                return importObject(session, "cheshire3.%s" % objectType)
            except:
                pass
        msg = "Module %s does not define class %s" % (modName, className)
        try:
            raise ConfigFileException(msg)
        finally:
            try:
                session.logger.log_lvl(session,
                                       50,
                                       msg)
            except AttributeError:
                # Most likely session is None or session.logger is None
                pass
    else:
        if isinstance(parentClass, ModuleType):
            raise ConfigFileException("%s defines a module, should define a "
                                      "class within a module" % objectType) 
    return parentClass


def buildObject(session, objectType, args):
    parentClass = importObject(session, objectType)
    try:
        return parentClass(session, *args)
    except:
        try:
            raise
        finally:
            try:
                session.logger.log_lvl(session,
                                       50,
                                       "Failed to create object of type: "
                                       "'{0}'".format(parentClass.__name__))
            except AttributeError:
                # Most likely session is None or session.logger is None
                pass
