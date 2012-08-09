"""Cheshire3 Extractor Implementations."""

import re
import types
import string
import copy

from lxml import etree, sax

from cheshire3.baseObjects import Extractor
from cheshire3.record import SaxContentHandler


class SimpleExtractor(Extractor):
    """Base extractor, extracts exact text."""

    _possibleSettings = {
        'extraSpaceElements': {
            'docs': ("Space separated list of elements after which to append "
                     "a space so as to not run words together.")
        },
        'prox': {
            'docs': ''
        },
        'parent': {
            "docs": ("Should the parent element's identifier be used instead "
                     "of the current element.")
        },
        'reversable': {
            "docs": ("Use a hopefully reversable identifier even when the "
                     "record is a DOM tree. 1 = Yes (expensive), 0 = No "
                     "(default)"),
            'type': int,
            'options': '0|1'
        },
        'stripWhitespace': {
            'docs': ('Should the extracter strip leading/trailing whitespace '
                     'from extracted text. 1 = Yes, 0 = No (default)'),
            'type': int,
            'options': '0|1'
        },
    }

    def __init__(self, session, config, parent):
        Extractor.__init__(self, session, config, parent)
        self.spaceRe = re.compile('\s+')
        extraSpaceElems = self.get_setting(session, 'extraSpaceElements', '')
        self.extraSpaceElems = extraSpaceElems.split()
        self.strip = self.get_setting(session, 'stripWhitespace', 0)
        self.cachedRoot = None
        self.cachedElems = {}

    def _mergeHash(self, a, b):
        if not a:
            return b
        if not b:
            return a
        for k in b.iterkeys():
            try:
                a[k]['occurences'] += b[k]['occurences']
                try:
                    a[k]['positions'].extend(b[k]['positions'])
                except:
                    try:
                        a[k]['proxLoc'].extend(b[k]['proxLoc'])
                    except:
                        # Non prox
                        pass
            except:
                a[k] = b[k]
        return a

    def _flattenTexts(self, elem):
        texts = []
        if (hasattr(elem, 'childNodes')):
            # minidom/4suite
            for e in elem.childNodes:
                if e.nodeType == textType:
                    texts.append(e.data)
                elif e.nodeType == elementType:
                    # Recurse
                    texts.append(self._flattenTexts(e))
                    if e.localName in self.extraSpaceElems:
                        texts.append(' ')
        else:
            # elementTree/lxml
            try:
                walker = elem.getiterator()
            except AttributeError:
                # lxml 1.3 or later
                try:
                    walker = elem.iter()
                except:
                    # lxml smart string object
                    return elem
            for c in walker:
                if c.text:
                    texts.append(c.text)
                if c.tag in self.extraSpaceElems:
                    texts.append(' ')
                if c.tail and c != elem:
                    texts.append(c.tail)
                    if c.tag in self.extraSpaceElems:
                        texts.append(' ')
        return ''.join(texts)

    def process_string(self, session, data):
        """Accept just text and return appropriate data structure."""
        if self.strip:
            data = data.strip()
        return {data: {'text': data, 'occurences': 1, 'proxLoc': [-1]}}

    def _getProxLocNode(self, session, node):
        try:
            tree = node.getroottree()
        except AttributeError:
            # lxml smart string result?
            node = node.getparent()
            tree = node.getroottree()

        if self.get_setting(session, 'reversable', 0):
            root = tree.getroot()
            if root == self.cachedRoot:
                lno = self.cachedElems[node]
            else:
                lno = 0
                self.cachedRoot = root
                self.cachedElems = {}
                try:
                    walker = tree.getiterator()
                except AttributeError:
                    # lxml 1.3 or later
                    walker = tree.iter()
                for n in walker:
                    self.cachedElems[n] = lno
                    lno += 1
                lno = self.cachedElems[node]
        else:
            lno = abs(hash(tree.getpath(node)))
        return lno

    def process_node(self, session, data):
        """Walk a DOM structure, extract and return."""
        txt = self._flattenTexts(data)
        # We MUST turn newlines into space or can't index
        txt = txt.replace('\n', ' ')
        txt = txt.replace('\r', ' ')
        if self.strip:
            txt = txt.strip()
        if self.get_setting(session, 'prox', 0):
            lno = self._getProxLocNode(session, data)
        else:
            lno = -1
        return {txt: {'text': txt, 'occurences': 1, 'proxLoc': [lno]}}

    def _getProxLocEventList(self, session, events):
        if (self.get_setting(session, 'parent')):
            lno = int(events[0].split()[-3])
        else:
            lno = int(events[-1].split()[-1])
        return lno

    def process_eventList(self, session, data):
        """Process a list of SAX events serialized in C3 internal format."""
        txt = []
        for e in data:
            if (e[0] == "3"):
                if (len(txt) and txt[-1][-1] != ' ' and repr(e[2]).isalnum()):
                    txt.append(' ')
                txt.append(e[2:])
        txt = ''.join(txt)
        if self.strip:
            txt = self.spaceRe.sub(' ', txt)
        if self.get_setting(session, 'prox', 0):
            lno = self._getProxLocEventList(session, data)
        else:
            lno = -1
        return {txt: {'text': txt, 'occurences': 1, 'proxLoc': [lno]}}

    def process_xpathResult(self, session, data):
        """Process the result of an XPath expression.

        Convenience function to wrap the other process_* functions and do type
        checking.
        """
        new = {}
        for xp in data:
            for d in xp:
                if (type(d) == types.ListType):
                    # SAX event
                    new = self._mergeHash(new,
                                          self.process_eventList(session, d))
                elif (type(d) in types.StringTypes or
                      type(d) in [int, long, float, bool]):
                    # Attribute content
                    new = self._mergeHash(new, self.process_string(session, d))
                else:
                    # DOM nodes
                    new = self._mergeHash(new, self.process_node(session, d))
        return new


class TeiExtractor(SimpleExtractor):

    _possibleSettings = {
        'imageSections': {
            'docs': 'put in {{ at each new image section',
            'type': int
        }
    }

    def process_node(self, session, data):
        """Walk a DOM structure, extract and return.

        Turn into SAX and process_eventList() for the mean time.
        """
        handler = SaxContentHandler()
        sax.saxify(data, handler)
        saxl = handler.currentText
        return self.process_eventList(session, saxl)

    def process_eventList(self, session, data):
        """Process a list of SAX events serialized in C3 internal format."""
        # Easy to find image sections
        includeBraces = self.get_setting(session, 'imageSections', 0)
        attrRe = re.compile("u?['\"](.+?)['\"]\)?: u?['\"](.*?)['\"](, |})")
        txt = []
        # None == skip element.  Otherwise fn to call on txt
        processStack = []
        # Step through a SAX event list and extract
        for e in data:
            if e[0] in ["1", '4']:
                start = e.find("{")
                name = e[2:start - 1]
                sp = name.split(',')
                if len(sp) == 4:
                    name = sp[1][2:-1]
                if e[start + 1] == '}':
                    attrs = {}
                else:
                    attrList = attrRe.findall(e[start:])
                    attrs = {}
                    for m in attrList:
                        attrs[unicode(m[0])] = unicode(m[1])
                if includeBraces and 'img.x' in attrs and name != "initial":
                    txt.append(' {{ ')

                if name == "uc":
                    processStack.append((name, string.upper))
                elif name == "lc":
                    processStack.append((name, string.lower))
                elif name == "sic":
                    # Replace contents with corr attribute
                    if 'corr' in attrs:
                        txt.append(attrs['corr'])
                    processStack.append((name, None))
                elif name == "p":
                    txt.append(' ')
                elif name == "abbr":
                    # Replace contents with expan attribute
                    if 'expan' in attrs:
                        txt.append(attrs['expan'])
                    processStack.append((name, None))
                elif name == "figdesc":
                    processStack.append((name, None))
            elif (e[0] == "2"):
                if (processStack and
                    processStack[-1][0] == e[2:len(processStack[-1][0]) + 2]):
                    processStack.pop()
            elif e[0] == '5':
                if (processStack and
                    processStack[-1][0] == e[9:len(processStack[-1][0]) + 9]):
                    processStack.pop()
            elif (e[0] == "3"):
                if (len(txt) and txt[-1] and
                    txt[-1][-1] != ' ' and repr(e[2]).isalnum()):
                    txt.append(' ')
                bit = e[2:]
                if processStack:
                    if processStack[-1][1] is None:
                        continue
                    else:
                        bit = processStack[-1][1](bit)
                txt.append(bit)
        txt = ''.join(txt)
        txt = self.spaceRe.sub(' ', txt)
        txt = txt.replace('- ', '')
        if self.get_setting(session, 'prox', 0):
            lno = self._getProxLocEventList(session, data)
        else:
            lno = -1
        return {txt: {'text': txt, 'occurences': 1, 'proxLoc': [lno]}}


class SpanXPathExtractor(SimpleExtractor):
    """Select all text that occurs between a pair of selections."""

    def process_xpathResult(self, session, data):
        new = {}
        root = None
        for xp in data:
            startNode, endNode = xp
            # Find common ancestor
            sancs = list(startNode.iterancestors())
            try:
                eancs = list(endNode.iterancestors())
            except AttributeError:
                # Maybe endNode not matched
                # Should continue to the end
                common_ancestor = sancs[-1] 
            else:
                # Common ancestor must exist in the shorter of the 2 lists
                # Trim both to this size
                sancs.reverse()
                eancs.reverse()
                minlen = min(len(sancs), len(eancs))
                sancs = sancs[:minlen]
                eancs = eancs[:minlen]
                # Iterate through both, simultaneously
                for sanc, eanc in zip(sancs, eancs):
                    if sanc == eanc:
                        common_ancestor = sanc
                        break
            inrange = False
            text = []
            extraSpaceNodes = []
            for evt, el in etree.iterwalk(common_ancestor,
                                          events=('start', 'end',
                                                  'start-ns', 'end-ns')):
                if el.tag in self.extraSpaceElems:
                    iter = el.itersiblings()
                    try:
                        extraSpaceNodes.append(iter.next())
                    except:
                        pass
                if evt in ['start', 'start-ns']:
                    if el == startNode:
                        inrange = True
                        if el in extraSpaceNodes:
                            text.append(' ')
                        if el.text is not None:
                            text.append(el.text)
                    elif el == endNode:
                        inrange = False
                        break
                    elif inrange:
                        if el in extraSpaceNodes:
                            text.append(' ')
                        if el.text is not None:
                            text.append(el.text)
                elif evt in ['end', 'end-ns'] and inrange:
                    if el.tail is not None:
                        if el in extraSpaceNodes:
                            text.append(' ')
                        text.append(el.tail)
            
            txt = ''.join(text)
            # We MUST turn newlines into space or can't index
            txt = txt.replace('\n', ' ')
            txt = txt.replace('\r', ' ')
            if self.strip:
                txt = txt.strip()
            if self.get_setting(session, 'prox', 0):
                lno = self._getProxLocNode(session, xp[0])
            else:
                lno = -1
            new = self._mergeHash(new,
                                  {txt: {'text': txt,
                                         'occurences': 1,
                                         'proxLoc': [lno]}})
        return new
