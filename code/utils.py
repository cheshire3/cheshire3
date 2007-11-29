
import time, os, sys, types, traceback, re
from xml.dom import Node
import math

use4Suite = 1
if (use4Suite):
    try:
        from Ft.Xml.XPath import ParsedRelativeLocationPath, ParsedAbsoluteLocationPath, \
             ParsedStep, ParsedNodeTest, ParsedExpr, Compile, Context, \
             ParsedAbbreviatedAbsoluteLocationPath, ParsedAbbreviatedRelativeLocationPath, ParsedNodeTest

    except:
        os.putenv('USE_MINIDOM', '1')
        from Ft.Xml.XPath import ParsedRelativeLocationPath, ParsedAbsoluteLocationPath, \
             ParsedStep, ParsedNodeTest, ParsedExpr, Compile
else:
    from xml.xpath import *

elementType = Node.ELEMENT_NODE
textType = Node.TEXT_NODE

nonTextToken = "\x00\t"


def fixString(s):
    l = []
    for c in s:
        if (ord(c) > 31 or c in ['\n', '\t', '\r']):
            l.append(c)
    return ''.join(l)


if (0):
    from Ft.Xml.Domlette import NonvalidatingReaderBase
    class reader(NonvalidatingReaderBase):
        def fromString(self, str):
            try:
                return self.parseString(str, 'urn:foo')
            except:
                return self.parseString(fixString(str), 'urn:foo')
        def fromStream(self, stream):
            return self.parseString(stream.read(), 'urn:foo')
        def releaseNode(self, node):
            pass
else:
    from xml.dom.minidom import parseString
    class reader:
        def fromString(self, s):
            try:
                return parseString(s)
            except:
                # Somewhere is possibly a fubar character
                s = fixString(s)
                return parseString(s)
        def fromStream(self, s):
            return self.fromString(s.read())
        def releaseNose(self, s):
            pass

# --- Definitions ---



def flattenTexts(elem):
    # recurse down tree and flatten all text nodes into one string.
    # Use list + join() to avoid memory overhead in Python string addition
    texts = []
    if (hasattr(elem, 'childNodes')):
        for e in elem.childNodes:
            if e.nodeType == textType:
                texts.append(e.data)
            elif e.nodeType == elementType:
                # Recurse
                texts.append(flattenTexts(e))
    else:
        # libxml2 walker/iterator
        walker = elem.getiterator()
        for c in walker:
            if c.text:
                texts.append(c.text)
            if c.tail:
                texts.append(c.tail)
    return ''.join(texts)


def evaluateXPath(xp, dom):
    if (use4Suite):
        context = Context.Context(dom)
        return xp.evaluate(context)
    else:
        return xp.evaluate(dom)


def getFirstElement(elem):
    """ Find first child which is an Element """
    if (hasattr(elem, 'childNodes')):
        for c in elem.childNodes:
            if c.nodeType == elementType:
                return c
    else:
        for c in elem:
            if (c.type == 'element'):
                return c
    return None

def getFirstData(elem):
    """ Find first child which is Data """
    if (hasattr(elem, 'childNodes')):
        for c in elem.childNodes:
            if c.nodeType == Node.TEXT_NODE:
                return c.data.strip()
    else:
        for c in elem:
            if (c.type == "text"):
                return c.data.strip()
    return ""


def getFirstElementByTagName(node, local):
    if node.nodeType == elementType and node.localName == local:
        return node;
    for child in node.childNodes:
        recNode = getFirstElementByTagName(child, local)
        if recNode:
            return recNode
    return None

def traversePath(node):

    if (isinstance(node, ParsedRelativeLocationPath.ParsedRelativeLocationPath)):
        left  = traversePath(node._left)
        right = traversePath(node._right)
        if (left == []):
            # self::node()
            return [right]
        elif (type(left[0]) in types.StringTypes):
            return [left, right]
        else:
            left.append(right)
            return left
    
    elif (isinstance(node, ParsedAbsoluteLocationPath.ParsedAbsoluteLocationPath)):
        left = ['/']
        if (node._child):
            right = traversePath(node._child)
        else:
            return left
        if (type(right[0]) == types.StringType):
            return [left, right]
        else:
            left.extend(right)
            return left
    elif (isinstance(node, ParsedAbbreviatedRelativeLocationPath.ParsedAbbreviatedRelativeLocationPath)):
        left  = traversePath(node._left)
        right = traversePath(node._right)
        right[0] = 'descendant'
        if (left == []):
            # self::node()
            return [right]
        elif (type(left[0]) in types.StringTypes):
            return [left, right]
        else:
            left.append(right)
            return left

    elif (isinstance(node, ParsedStep.ParsedStep)):
        # TODO: Check that axis is something we can parse
        a = node._axis._axis
        if (a == 'self'):
            return []
        
        n = node._nodeTest
        if use4Suite:
            local = ParsedNodeTest.LocalNameTest
            nameattr = "_name"
        else:
            local = ParsedNodeTest.NodeNameTest
            nameattr = "_nodeName"
        if (isinstance(n, local)):
            n = getattr(n, nameattr)
        elif (isinstance(n, ParsedNodeTest.TextNodeTest)):
            n = "__text()"
        elif (isinstance(n, ParsedNodeTest.QualifiedNameTest)):
            n = n._prefix + ":" + n._localName
        elif (isinstance(n, ParsedNodeTest.PrincipalTypeTest)):
            n = "*"
        else:
            raise(NotImplementedError)
            
        preds = node._predicates

        pp = []
        if (preds):
            for pred in preds:
                pp.append(traversePath(pred))

        return [a, n, pp]
        
    elif (isinstance(node, ParsedExpr.ParsedEqualityExpr) or isinstance(node, ParsedExpr.ParsedRelationalExpr)):
        # @id="fish"
        op = node._op

        # Override check for common: [position()=int]
        if (op == '=' and isinstance(node._left, ParsedExpr.FunctionCall) and node._left._name == 'position' and isinstance(node._right, ParsedExpr.ParsedNLiteralExpr)):
            return node._right._literal

        left = traversePath(node._left)
        if (type(left) == types.ListType and left[0] == "attribute"):
            left = left[1]
        right = traversePath(node._right)
        if not op in ('=', '!='):
            op = ['<', '<=', '>', '>='][op]
        return [left, op, right]

    elif (isinstance(node, ParsedExpr.ParsedNLiteralExpr) or isinstance(node, ParsedExpr.ParsedLiteralExpr)):
        # 7 or "fish"
        return node._literal
    elif (isinstance(node, ParsedExpr.FunctionCall)):
        if (node._name == 'last'):
            # Override for last using Pythonic expr
            return -1
        elif node._name == 'name':
            return ['FUNCTION', '__name()']
        elif node._name == 'starts-with':
            # only for foo[starts-with(@bar, 'baz')]
            return ['FUNCTION', 'starts-with', traversePath(node._arg0)[1], node._arg1._literal]
        elif node._name == 'regexp':
            return ['FUNCTION', 'regexp', traversePath(node._arg0)[1], re.compile(node._arg1._literal)]
        elif node._name == 'count':
            return ['FUNCTION', 'count', traversePath(node._arg0)]
        else:
            raise(NotImplementedError)

    elif (isinstance(node, ParsedExpr.ParsedAndExpr)):
        return [traversePath(node._left), 'and', traversePath(node._right)]
    elif (isinstance(node, ParsedExpr.ParsedOrExpr)):
        return [traversePath(node._left), 'or', traversePath(node._right)]
    else:
        # We'll need to do full XPath vs DOM
        raise(NotImplementedError)


def verifyXPaths(paths):
    compiled = []
    for p in paths:
            allAbsolute = 1
#        try:
            plist = []
            xpObj= Compile(p)
            plist.append(xpObj)
            try:
                t = traversePath(xpObj)
                if (t[0] <> '/' and type(t[0]) in types.StringTypes):
                    # a single Step
                    t = [t]
                plist.append(t)
            except NotImplementedError:
                # We can't handle it!
                plist.append(None)
            compiled.append(plist)
 #       except:
 #           # Utoh, invalid path. Warn.
 #           print sys.exc_info()[2]
 #           print "Invalid XPath: " + p
 #           raise(sys.exc_info()[1])
    return compiled


# ------------- Bitfield ---------------


nonbinaryre = re.compile('[2-9a-f]')

class SimpleBitfield(object):
    def __init__(self,value=0):
        if not value:
            value = 0
        if type(value) == types.StringType:
            if value[0:2] == "0x":
                value = int(value, 16)                
            elif nonbinaryre.search(value):
                value = int("0x" + value, 16)
            else:
                value = int(value, 2)
        self._d = value

    def __getitem__(self, index):
        # Necessary to end for loop
        # eg:  for x in bf:  print bf[x]
        # would continue indefinitely
        if index >= len(self):
            raise IndexError(index)
        return (self._d >> index) & 1 

    def __setitem__(self,index, value):
        if value:
            self._d  = self._d | (1L<<index)
        else:
            self._d = self._d ^ (1L <<index)

    def __int__(self):
        return self._d

    def __str__(self):
        # eval(string) to return
        s = hex(self._d)
        if s[-1] == "L":
            return s[:-1]
        else:
            return s

    def __nonzero__(self):
        return self._d != 0

    def __len__(self):
        # Precision hack
        # NB len(str(self))-3 / 4 == capacity, not actual
        split = math.modf(math.log(self._d, 2))
        if (split[0] > 0.9999999999):
            return int(split[1]) + 1
        else:
            return int(split[1])

    def union(self, other):
        self._d = self._d | other._d

    def intersection(self, other):
        self._d = self._d & other._d

    def difference(self, other):
        andnot = self._d & other._d
        self._d = self._d ^ andnot

    def lenTrueItems(self):
        string = str(self)[2:]
        string = string.replace('0', '')
        string = string.lower()
        l = 0
        for quad in string:
            if quad in ['1','2', '4', '8']:
                l += 1
            elif quad in ['3', '5', '6', '9', 'a', 'c']:
                l += 2
            elif quad in ['7', 'b', 'd', 'e']:
                l += 3
            else:
                l += 4
        return l

    def trueItems(self):
        string = str(self)
        posn = 0
        ids = []
        # reverse w/o leading 0x
        string = string[2:][::-1]
        # string exception throwing is slower
        string = string.lower()
        for quad in string:
            if quad == '0':
                pass
            elif quad == '1': # 0001
                ids.append(posn)
            elif quad == '2': # 0010
                ids.append(posn+1)
            elif quad == '3': # 0011
                ids.extend([posn, posn+1])                    
            elif quad == '4': # 0100
                ids.append(posn+2)
            elif quad == '5': # 0101
                ids.extend([posn, posn+2])
            elif quad == '6': # 0110
                ids.extend([posn+1, posn+2])
            elif quad == '7': # 0111
                ids.extend([posn, posn+1, posn+2])
            elif quad == '8': # 1000
                ids.append(posn+3)
            elif quad == '9': # 1001
                ids.extend([posn, posn+3])
            else:
                if quad == 'a': # 1010
                    ids.extend([posn+1, posn+3])                    
                elif quad == 'b': # 1011
                    ids.extend([posn, posn+1, posn+3])                    
                elif quad == 'c': # 1100
                    ids.extend([posn+2, posn+3])
                elif quad == 'd': # 1101
                    ids.extend([posn, posn+2, posn+3])
                elif quad == 'e': # 1110
                    ids.extend([posn+1, posn+2, posn+3])
                elif quad == 'f': # 1111
                    ids.extend([posn, posn+1, posn+2, posn+3])
                else:
                    # WTF?
                    raise ValueError(quad)
            posn += 4
        return ids


# -------------- SRB URL Parser -------------

import urlparse
def parseSrbUrl(data):
    info = {'user' : None, 'passwd' : None, 'domain' : None,
            'host' : None, 'port' : None, 'path' : None,
            'resource' : None, 'authType' : None}
    if data[:6] == 'srb://':
        data = 'http://' + data[6:]
    else:
        # Bad. Hope for the best
        data = "http://" + data

    try:
        (scheme, net, info['path'], param, qry, fraq) = urlparse.urlparse(data)
    except:
        # Splat
        return info
    try:
        (auth, hp) = net.split('@')
        try:
            (info['user'], info['passwd']) = auth.split(':')
            info['authType'] = 'ENCRYPT1'
            try:
                (info['user'], info['domain']) = info['user'].split('.')
            except:
                pass
        except:
            info['authType'] = 'DN'
    except:
        hp = net
        auth = ""
    try:
        (info['host'], port) = hp.split(':')
        info['port'] = int(port)
    except:
        info['host'] = hp
        info['port'] = 5544
    stuff = qry.split('&')    
    resource = ""
    for item in stuff:
        try:
            (typ, val) = item.split("=")
            if typ == "resource":
                info['resource'] = val
            elif typ == "domain":
                info['domain'] = val
            elif typ == "replica":
                info['replica'] = val
            elif typ == "fileType":
                info['fileType'] = val
        except:
            pass
    return info
