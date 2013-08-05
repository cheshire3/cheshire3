"""Cheshire3 User Implementations."""

import crypt
import hashlib

from lxml import etree

from paste.auth.digest import digest_password as http_digest_password

from cheshire3.baseObjects import User
from cheshire3.exceptions import ConfigFileException
from cheshire3.internal import CONFIG_NS
from cheshire3.utils import getFirstData, elementType, flattenTexts


class SimpleUser(User):
    simpleNodes = ["username", '{%s}username' % CONFIG_NS,
                   "password", '{%s}password' % CONFIG_NS,
                   "email", '{%s}email' % CONFIG_NS,
                   "address", '{%s}address' % CONFIG_NS,
                   "tel", '{%s}tel' % CONFIG_NS,
                   "realName", '{%s}realName' % CONFIG_NS,
                   "description", '{%s}description' % CONFIG_NS,
                   "passwordType", '{%s}passwordType' % CONFIG_NS
                   ]
    username = ""
    password = ""
    passwordType = ""
    email = ""
    address = ""
    tel = ""
    realName = ""
    description = ""
    flags = {}

    allFlags = {
        "c3r:administrator": "Administrator flag. Inherits all others.",
        "info:srw/operation/1/create": "Create record within this store",
        "info:srw/operation/1/replace": "Replace existing record within store",
        "info:srw/operation/1/delete": "Delete existing record from store",
        "info:srw/operation/1/metadata": ("Modify metadata of record within "
                                          "store"),
        "info:srw/operation/2/index": "Run indexing process for this object",
        "info:srw/operation/2/unindex": ("Run un-indexing process for this "
                                         "object"),
        "info:srw/operation/2/cluster": ("Run clustering process for this "
                                         "object"),
        "info:srw/operation/2/permissions": "Permission to change permissions",
        "info:srw/operation/2/search": "Permission to search",
        "info:srw/operation/2/retrieve": "Permission to retrieve object",
        "info:srw/operation/2/scan": "Permission to scan",
        "info:srw/operation/2/sort": "Permission to sort result set",
        "info:srw/operation/2/transform": "Permission to transform record"
    }
    # Plus c3fn:(functionName) for function on object

    resultSetIds = []

    def _handleConfigNode(self, session, node):
        if (node.localName in self.simpleNodes):
            setattr(self, node.localName, getFirstData(node))
        elif (node.localName == "flags"):
            # Extract Rights info
            # <flags> <flag> <object> <value> </flag> </flags>
            for c in node.childNodes:
                if c.nodeType == elementType and c.localName == "flag":
                    obj = None
                    flag = None
                    for c2 in c.childNodes:
                        if c2.nodeType == elementType:
                            if c2.localName == "object":
                                obj = getFirstData(c2)
                            elif c2.localName == "value":
                                flag = getFirstData(c2)
                                if ((flag not in self.allFlags) and
                                    (flag[:4] != "c3fn")):
                                    msg = "Unknown flag: %s" % flag
                                    raise ConfigFileException(msg)
                    if obj is None or flag is None:
                        msg = ("Missing object or value element for flag for "
                               "user %s" % self.username)
                        raise ConfigFileException(msg)
                    if (obj):
                        f = self.flags.get(flag, [])
                        if f != "":
                            f.append(obj)
                            self.flags[flag] = f
                    else:
                        self.flags[flag] = ""
        elif (node.localName == "history"):
            # Extract user history
            pass
        elif (node.localName == "hostmask"):
            # Extract allowed hostmask list
            pass

    def _handleLxmlConfigNode(self, session, node):
        if node.tag in self.simpleNodes:
            setattr(self,
                    node.tag[node.tag.find('}') + 1:],
                    flattenTexts(node).strip())
        elif node.tag in ["flags", '{%s}flags' % CONFIG_NS]:
            # Extract Rights info
            # <flags> <flag> <object> <value> </flag> </flags>
            for c in node.iterchildren(tag=etree.Element):
                if c.tag in ["flag", '{%s}flag' % CONFIG_NS]:
                    obj = None
                    flag = None
                    for c2 in c.iterchildren(tag=etree.Element):
                        if c2.tag in ["object", '{%s}object' % CONFIG_NS]:
                            obj = flattenTexts(c2).strip()
                        elif c2.tag in ["value", '{%s}value' % CONFIG_NS]:
                            flag = flattenTexts(c2).strip()
                            if (flag not in self.allFlags and
                                flag[:4] != "c3fn"):
                                msg = "Unknown flag: %s" % flag
                                raise ConfigFileException(msg)
                    if obj is None or flag is None:
                        msg = ("Missing object or value element for flag for "
                               "user %s" % self.username)
                        raise ConfigFileException()
                    f = self.flags.get(flag, [])
                    if (obj):
                        f.append(obj)
                    self.flags[flag] = f
        elif node.tag in ["history", '{%s}history' % CONFIG_NS]:
            # Extract user history
            pass
        elif node.tag in ["hostmask", '{%s}hostmask' % CONFIG_NS]:
            # Extract allowed hostmask list
            pass

    def __init__(self, session, config, parent):
        self.flags = {}
        User.__init__(self, session, config, parent)

    def has_flag(self, session, flag, object=""):
        # Does the user have the flag for this object/all objects
        f = self.flags.get(flag, [])
        if object in f:
            return True
        else:
            # Does the user have a global flag for this object/all objects
            f = self.flags.get("", [])
            if object in f:
                return True
            else:
                f = self.flags.get("c3r:administrator", [])
                if object in f or f == "":
                    return True
                return False

    def check_password(self, session, password):
        """Check the supplied en-clair password.
        
        Check the supplied en-clair password by obfuscating it using the same
        algorithm and comparing it with the stored version. Return True/False. 
        """
        # Check password type
        try:
            h = hashlib.new(self.passwordType)
        except ValueError:
            # Not a hashlib supported algorithm
            if self.passwordType == 'http':
                # HTTP Digest algorithm
                return http_digest_password('cheshire3',
                                            self.username,
                                            password) == self.password
            else:
                #  UNIX-style salted password encryption
                cryptedpasswd = crypt.crypt(password, self.password[:2]) 
                return cryptedpasswd == self.password
        else:
            h.update(password)
            return h.hexdigest() == self.password
