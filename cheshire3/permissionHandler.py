"""PermissionHandler implementations."""

from types import MethodType

from cheshire3.utils import elementType, getFirstData


class PermissionHandler:
    """Object to facilitate persmissions checking

    Generate dynamic code to run for permissions checking.
    """

    actionIdentifier = ""
    codeText = []
    hasPermission = None

    def __init__(self, node, parent):
        self.parent = parent
        self._walkNode(node)

    def _walkNode(self, node):

        if node.localName == "action":
            # top node
            self.actionIdentifier = node.getAttributeNS(None, 'identifier')
            if not self.actionIdentifier:
                raise ConfigFileException("No action identifier")
            self.code = ["  if "]
            for c in node.childNodes:
                if c.nodeType == elementType:
                    self._walkNode(c)
            self.code.append(":")
            cstring = " ".join(self.code)
            fncode = '\n'.join(["def handler(self, session, user):",
                                cstring,
                                "    return True",
                                "  else:",
                                "    return False"])
            exec(fncode)
            setattr(self, 'hasPermission',
                    MethodType(locals()['handler'], self, self.__class__))
        elif node.localName in ["all", "any"]:
            if node.localName == "all":
                bool = "and"
            else:
                bool = "or"
            self.code.append("(")
            for c in node.childNodes:
                if c.nodeType == elementType:
                    self._walkNode(c)
                    self.code.append(bool)
            self.code.pop()
            self.code.append(")")
        elif node.localName == "flag":
            f = getFirstData(node)
            self.code.append("user.has_flag(session, \"%s\", object)" % f)
        elif node.localName == "environment":
            e = getFirstData(node)
            self.code.append("session.environment == \"%s\"" % e)
        elif node.localName == "hostmask":
            e = getFirstData(node)
            self.code.append("user.connectedFrom(session, \"%s\")" % e)
