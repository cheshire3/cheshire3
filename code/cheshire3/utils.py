import  types, re
from xml.dom import Node
from lxml import etree
import math

elementType = Node.ELEMENT_NODE
textType = Node.TEXT_NODE
nonTextToken = "\x00\t"


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
        # libxml2
        try:
            return etree.tostring(elem, method='text')
        except (TypeError, UnicodeEncodeError):
            # predates lxml 1.3 - fall back to tree iteration
            walker = elem.getiterator()
            for c in walker:
                if c.text:
                    texts.append(c.text)
                if c.tail:
                    texts.append(c.tail)
    return ''.join(texts)


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

try:
    # only in Python 2.5+
    import uuid
    def gen_uuid():
        return str(uuid.uuid4())
except:
    # Try 4Suite if installed (2.4 and below)
    try:
        from Ft.Lib.Uuid import GenerateUuid, UuidAsString
        def gen_uuid():
            return UuidAsString(GenerateUuid())
    except:
        # No luck, try to generate using unix command
        
        import commands
        def gen_uuid():
            return commands.getoutput('uuidgen')

        uuidre = re.compile("[0-9a-fA-F-]{36}")
        uuid = gen_uuid()

        if not uuidre.match(uuid):
            # probably sh: command not found or other similar
            # weakest version: just build random token
            import random
            chrs = ['0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f']
            def gen_uuid():
                uuidl = []
                for y in [8,4,4,4,12]:
                    for x in range(y):
                        uuidl.append(random.choice(chrs))
                    uuidl.append('-')
                uuidl.pop(-1)  # strip trailing -
                return ''.join(uuidl)

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")



# ------------- Bitfield ---------------


nonbinaryre = re.compile('[2-9a-f]')

class SimpleBitfield(object):
    def __init__(self,value=0):
        if not value:
            value = 0
        if type(value) == types.StringType:
            if value[0:2] == "0x":
                value = int(value, 16)                
            elif value[0:2] == "0b":
                value = int(value, 2)
            elif nonbinaryre.search(value):
                value = int("0x" + value, 16)
            else:
                value = int(value, 2)
        self._d = value

    def __getitem__(self, index):
        # Necessary to end for loop
        # would continue indefinitely
        if index >= len(self):
            raise IndexError(index)
        return (self._d >> index) & 1 

    def __setitem__(self,index, value):
        if value:
            self._d  = self._d | (long(1)<<index)
        else:
            self._d = self._d ^ (long(1)<<index)

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

