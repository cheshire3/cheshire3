
from extractor import SimpleExtractor

class TaggedExtractor(SimpleExtractor):
    # if not stem, then use word

    _possibleSettings = {"format" : {'doc' : "%(word), %(stem), %(pos), %(type) from  <w l=STEM p=POS t=TYPE>WORD</w>"}}

    def __init__(self, session, config, parent):
        SimpleExtractor.__init__(self, session, config, parent)
        self.format = self.get_setting(session, 'format', "%(word)s")


    def _flattenTexts(self, elem):
        texts = []
        fmt = self.format
        if (hasattr(elem, 'childNodes')):
            # minidom/4suite
            for e in elem.childNodes:
                if e.nodeType == textType:
                    texts.append(e.data)
                elif e.nodeType == elementType:
                    # Recurse
                    texts.append(self.flattenTexts(e))
                    if e.localName in self.extraSpaceElems:
                        texts.append(' ')
        else:
            # elementTree/lxml
            walker = elem.getiterator()
            for c in walker:
                if c.tag == 'w':
                    attr = c.attrib
                    try:
                        h = {'word' : c.text,
                             'stem' : attr['l'],
                             'pos' : attr['p'],
                             'type' : attr['t']}
                    except:
                        h = {'word' : c.text,
                             'stem' : c.text,
                             'pos' : attr['p'],
                             'type' : attr['t']}
                    texts.append(fmt % h)
                else:
                    if c.text:
                        texts.append(c.text)
                if c.tag in self.extraSpaceElems:
                    texts.append(' ')
                if c.tail:
                    texts.append(c.tail)
                if c.tag in self.extraSpaceElems:
                    texts.append(' ')
        return ''.join(texts)

