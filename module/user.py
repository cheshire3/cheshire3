
from cheshire3.baseObjects import User
from cheshire3.exceptions import ConfigFileException
from cheshire3.utils import getFirstData, elementType

import crypt
import hashlib

class SimpleUser(User):
    simpleNodes = ["username", "password", "email", "address", "tel", "realName", "description", "passwordType"]
    username = ""
    password = ""
    email = ""
    address =""
    tel = ""
    realName = ""
    description = ""
    flags = {}

    allFlags = {"c3r:administrator" : "Administrator flag. Inherits all others.",
                "info:srw/operation/1/create" : "Create record within this store",
                "info:srw/operation/1/replace" : "Replace existing record within store",
                "info:srw/operation/1/delete" : "Delete existing record from store",
                "info:srw/operation/1/metadata" : "Modify metadata of record within store",
                "info:srw/operation/2/index" : "Run indexing process for this object",
                "info:srw/operation/2/unindex" : "Run un-indexing process for this object",
                "info:srw/operation/2/cluster" : "Run clustering process for this object",
                "info:srw/operation/2/permissions" : "Permission to change permissions",
                "info:srw/operation/2/search" : "Permission to search",
                "info:srw/operation/2/retrieve" : "Permission to retrieve object",
                "info:srw/operation/2/scan" : "Permission to scan",
                "info:srw/operation/2/sort" : "Permission to sort result set",      
                "info:srw/operation/2/transform" : "Permission to transform record"            
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
                                if not flag in self.allFlags and flag[:4] != "c3fn":
                                    raise ConfigFileException("Unknown flag: %s" % flag)
                    if obj == None or flag == None:
                        raise ConfigFileException("Missing object or value element for flag for user %s" % self.username)
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
            else :
                f = self.flags.get("c3r:administrator", [])
                if object in f or f == "":
                    return True                
                return False

    def check_password(self, session, password):
        # Check password type
        if self.passwordType == 'md5':
            m = hashlib.md5(password)
            return m.hexdigest() == self.password
        else:
            return crypt.crypt(password, self.password[:2]) == self.password
