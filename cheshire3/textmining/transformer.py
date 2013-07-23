"""Cheshire3 Textmining Transformer Implementations."""

import sys
import os
import re
import traceback

from lxml import etree
from xml.sax.saxutils import escape

from cheshire3.textmining.TsujiiC3 import TsujiiObject
from cheshire3.baseObjects import Transformer
from cheshire3.document import StringDocument
from cheshire3.utils import getFirstData, elementType


class PosTransformer(Transformer):
    pass


class TsujiiTextPosTransformer(PosTransformer, TsujiiObject):

    def __init__(self, session, node, parent):
        PosTransformer.__init__(self, session, node, parent)
        TsujiiObject.__init__(self, session, node, parent)

    def process_record(self, session, rec):
        """Oooooh.  Try to step through all text nodes and tag?"""
        pass


class TsujiiXPathTransformer(PosTransformer, TsujiiObject):

    # <xpath type="copy"> ...
    # <xpath type="tag"> ...
    copyElems = []
    tagElems = []

    def _handleConfigNode(self, session, node):
        # Source
        if (node.localName == "xpath"):
            xpath = getFirstData(node)
            maps = {}
            for a in node.attributes.keys():
                if (a[:6] == "xmlns:"):
                    pref = a[6:]
                    uri = node.getAttribute(a)
                    maps[pref] = uri
                elif a == "type":
                    tc = node.getAttribute(a)
            cxp = verifyXPaths([xpath])
            if tc == 'copy':
                self.copyElems.append([cxp[0], maps])
            else:
                self.tagElems.append([cxp[0], maps])

    def __init__(self, session, node, parent):
        self.copyElems = []
        self.tagElems = []
        PosTransformer.__init__(self, session, node, parent)
        TsujiiObject.__init__(self, session, node, parent)

    def process_record(self, session, rec):
        doc = []
        for c in self.copyElems:
            res = rec.process_xpath(session, c[0], c[1])
            for match in res:
                txt = rec.get_xml(session, match)
                doc.append(txt)
        for t in self.tagElems:
            res = rec.process_xpath(session, t[0], t[1])
            for match in res:
                # Process all text nodes together
                totag = []
                for event in match:
                    if event[0] == '3':
                        totag.append(event[1:])
                tagtxt = ''.join(totag)
                tagged = self.tag(session, tagtxt)
                tagged = ''.join(tagged)
                if match[0][0] != '3':
                    (name, attrhash) = rec._convert_elem(match[0])
                    attrs = []
                    for a in attrhash:
                        attrs.append('%s="%s"' % (a, attribs[a]))
                    attribtxt = ' '.join(attrs)
                    if (attribtxt):
                        attribtxt = " " + attribtxt
                    txt = "<%s%s>%s</%s>" % (name, attribtxt, tagged, name)
                else:
                    txt = "<text>%s</text>" % (tagged)
                doc.append(txt)
        doctxt = "<record>%s</record>" % '\n'.join(doc)
        strdoc = StringDocument(doctxt,
                                self.id,
                                rec.processHistory,
                                'text/xml')
        return strdoc


class GeniaTransformer(Transformer):

    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        self.session = session
        self.rfot = self.get_path(session, 'tokenizer')
        self.tupg = self.get_path(session, 'geniaNormalizer')
        self.dashre = re.compile("""([^ ]+[-/*=(`] )""")
        self.enddashre = re.compile("""\W+[-('`]\W*$""")
        self.urlre = re.compile('\[[ ]*a .*?\[/a\]')
        self.debug = 0

    def process_record(self, session, rec):
        doc = []
        doc.append('<article id="%s" date="%s">\n',
                   '' % (rec.process_xpath(session, '/article/@id')[0],
                         rec.process_xpath(session, '/article/@date')[0]))
        head = rec.process_xpath(session, '/article/head')[0]
        headstr = etree.tounicode(head)
        doc.append(headstr.encode('utf-8'))
        doc.append("\n<body>\n")
        body = rec.process_xpath(session, '/article/body')[0]
        # walk tree looking for <s> tags, and duplicate out any non s tag
        eid = 0
        for sub in body:
            if sub.tag == "p":
                bits = ['<p eid="%s"' % eid]
                eid += 1
                for (name, val) in sub.items():
                    bits.append("%s=\"%s\"" % (name, val))
                bits.append(">")
                doc.append(' '.join(bits))
                for s in sub:
                    # sentences
                    bits = ['<s eid="%s"' % eid]
                    eid += 1
                    for (name, val) in s.items():
                        bits.append("%s=\"%s\"" % (name, val))
                    bits.append(">")
                    doc.append(' '.join(bits))
                    t = s.text
                    if t:
                        try:
                            toks = self.geniafy(t)
                            ttxt = ''.join(toks)
                            val = '<txt>%s</txt><toks>%s</toks>' % (escape(t),
                                                                    ttxt)
                            doc.append(val.encode('utf8'))
                        except:
                            raise
                    doc.append("</s>")
                doc.append("</p>\n")
            elif sub.tag in ["headline", "lead"]:
                # tag headline and lead too
                doc.append('<%s>' % sub.tag)
                t = sub.text
                if t:
                    try:
                        toks = self.geniafy(t)
                        ttxt = ''.join(toks)
                        val = '<txt>%s</txt><toks>%s</toks>' % (escape(t),
                                                                ttxt)
                        doc.append(val.encode('utf8'))
                    except:
                        raise
                doc.append('</%s>' % sub.tag)
            else:
            # just useless <br/> tags
                pass
        doc.append("\n</body>\n</article>\n")
        return StringDocument(''.join(doc))

    def get_toks(self, nwtxt):
        alltoks = []
        cnw = []
        space = 1
        for c in nwtxt:
            csp = c.isspace()
            if (space and csp) or (not space and not csp):
                cnw.append(c)
            else:
                if cnw:
                    alltoks.append("<n>%s</n>" % (escape(''.join(cnw))))
                cnw = [c]
                space = csp
        if cnw:
            alltoks.append("<n>%s</n>" % (escape(''.join(cnw))))
        return alltoks

    def geniafy(self, text):
        print text
        t = self.rfot.process_string(self.session, text)
        words = t[0]
        offsets = t[1]

        if words and words[-1][-1] == '.':
            words[-1] = words[-1][:-1]

        text2 = text
        for o in t[1][::-1]:
            text2 = text2[:o] + " " + text2[o:]
        text2 = text2.replace("'ll've", " 'll 've")
        text2 = text2.replace("'d've", " 'd 've")
        text2 = self.enddashre.sub(' ', text2)
        text2 = text2.replace(u'\u2026', ' ')
        text2 = self.urlre.sub(' ', text2)
        text2 = text2.replace(' % ', '   ')
        text2 = text2.replace('\n', ' ')

        m = self.dashre.search(text2)
        while m:
            if m:
                txt = m.groups()[0]
                text2 = text2.replace(txt, "%s  " % txt[:-2])
            m = self.dashre.search(text2)
        t2 = self.tupg.process_string(self.session, text2)

        lines = t2.split('\n')
        if lines[-1] == '':
            lines = lines[:-1]
        puncts = [':', "''", "``", '.', ',', ';', '(', ')', 'HYPH']
        stemfix = {"'ll": "be",
                   "'re": 'be',
                   "'ve": 'have',
                   "'d": "be"}
        curr = 0
        toks = []
        xmls = []
        try:
            for (w, word) in enumerate(words):
                ntok = ""
                pos = []
                offset = -1
                stem = []
                skip = 0
                while ntok != word:
                    line = lines[curr]
                    bits = line.split('\t')
                    if bits[2] == "CD" and len(lines) > curr + 2:
                        b1 = lines[curr + 1].split('\t')
                        b2 = lines[curr + 2].split('\t')
                        if b1[2] == ',' and b2[2] == 'CD':
                            # 500, three is 2 tokens (3 in genia)
                            # 1,000,000 is 1 token (5 in genia)
                            lb2 = len(b2[0])
                            if len(offsets) <= w + 1:
                                doit = 1
                            else:
                                noff = offsets[w + 1]
                                doit = text[noff:noff + lb2] != b2[0]
                            if doit:
                                skip = 1
                                if ntok:
                                    if pos[-1] == 'CD':
                                        ntok += ",%s" % (b2[0])
                                    else:
                                        ntok += "%s,%s" % (bits[0], b2[0])
                                else:
                                    ntok = "%s,%s" % (bits[0], b2[0])
                                if not pos or (pos and pos[-1] != 'CD'):
                                    pos.append('CD')
                                if offset == -1:
                                    offset = offsets[w]
                                curr += 2
                                continue
                    curr += 1
                    if bits[2] in puncts:
                        continue
                    elif bits[2] == "SYM" and not bits[0].isalpha():
                        continue
                    elif bits[0] in ["'", '&']:
                        continue
                    if bits[0][-1] == '.' and bits[0] != word:
                        bits[0] = bits[0][:-1]
                    ntok += bits[0]
                    if bits[1] in stemfix:
                        stem.append(stemfix[bits[1]])
                    elif bits[2] == "POS":
                        pass
                    else:
                        stem.append(bits[1])
                    pos.append(bits[2])
                    if offset == -1:
                        offset = offsets[w]
                nstem = ""
                if stem and stem[0] != ntok:
                    nstem = ' s="%s"' % ('+'.join(stem))
                term = '<w p="%s" o="%s"%s>%s</w>' % (escape('+'.join(pos)),
                                                      offset,
                                                      escape(nstem),
                                                      escape(ntok))
                toks.append(term)
                if skip:
                    curr += 1
                    skip = 0
        except:
            if self.debug:
                print 'text input', text2
                print 'our tokenized', words
                print 'index in words', w
                print 'found tokens', toks
                print 'current token', ntok
                print 'pos', pos
                print 'stem', stem
                print 'lines', lines
                print 'curr', curr
                print 'len lines', len(lines)
                print '\n'.join(traceback.format_exception(sys.exc_type,
                                                           sys.exc_value,
                                                           sys.exc_traceback))
                raise e
            else:
                # Generate rest of toks without stem/pos
                t = len(toks)
                for (w, word) in enumerate(words[t:]):
                    toks.append('<w o="%s">%s</w>' % (offsets[w + t],
                                                      escape(word)))

        # Now step through original string and generate <nw> elems
        # one nw elem for consecutive whitespace or punctuation
        alltoks = []
        start = 0
        for (o, off) in enumerate(offsets):
            if off > start:
                nwtxt = text[start:off]
                alltoks.extend(self.get_toks(nwtxt))
                tlen = len(words[o])
                start = off + tlen
            else:
                tlen = len(words[o])
                start += tlen
            alltoks.append(toks[o])

        if start < len(text):
            # get the last
            nwtxt = text[start:]
            alltoks.extend(self.get_toks(nwtxt))
        return alltoks
