"""Cheshire3 Text Mining DocumentFactory implementations."""

import os
import re

from cheshire3.documentFactory import BaseDocumentStream
from cheshire3.document import StringDocument


class EnjuRecordDocumentStream(BaseDocumentStream):

    def open_stream(self, stream):
        # stream here will be a record in Enju XML schema
        self.streamLocation = stream.id
        return stream

    def find_documents(self, session, cache=0):
        rec = self.stream
        # Find verbs, one verb per document
        vs = rec.process_xpath(session, 'phrase[@cat="VP"]/word')
        docs = []
        processed = []
        sentn = 0
        for v in vs:
            # Find word, and arg1, arg2
            (name, attrs) = rec._convert_elem(v[0])
            prepstr = ""
            iobjstr = ""
            arg1 = attrs[u'arg1']
            vtxt = v[1][2:]
            vid = attrs['id']
            if vid in processed:
                continue
            verb = ['<verb>',
                    '<w pos="%s" base="%s">%s</w>' % (attrs['pos'],
                                                      attrs['base'],
                                                      vtxt)]
            el1 = rec.process_xpath(session,
                                    'phrase[@id="%s"]/descendant::word' % arg1)
            txt = ['<subject>']
            for w in el1:
                (name, nattrs) = rec._convert_elem(w[0])
                txt.append('<w pos="%s">%s</w>' % (nattrs['pos'], w[1][2:]))
            txt.append("</subject>")
            subj = ' '.join(txt)

            try:
                arg2 = attrs[u'arg2']
                # arg2 might be more verb
                # eg 'will -> be -> treating'
                el2 = rec.process_xpath(session, 'phrase[@id="%s"]' % arg2)
                (name, nattrs) = rec._convert_elem(el2[0][0])
                nid = nattrs['id']
                while nattrs[u'cat'] == "VP":
                    allv = rec.process_xpath(
                               session,
                               'phrase[@id="%s"]/descendant::word' % nid)
                    (name, avattrs) = rec._convert_elem(allv[0][0])
                    verb.append('<w pos="%s" base="%s">%s</w>'
                                '' % (avattrs['pos'],
                                      avattrs['base'],
                                      allv[0][1][2:]))
                    processed.append(avattrs['id'])
                    avarg2 = avattrs['arg2']
                    if avarg2 == arg1:
                        avarg2 = avattrs['arg1']
                        if avarg2 == '-1':
                            # no arg2, fall back
                            break
                    el2 = rec.process_xpath(session,
                                            'phrase[@id="%s"]' % avarg2)
                    (name, nattrs) = rec._convert_elem(el2[0][0])
                    nid = nattrs['id']
                el2 = rec.process_xpath(session,
                                        'phrase[@id="%s"]/'
                                        'descendant::word' % nid)
                txt = ['<object>']
                for w in el2:
                    (name, nattrs) = rec._convert_elem(w[0])
                    txt.append('<w pos="%s">%s</w>' % (nattrs['pos'],
                                                       w[1][2:]))
                txt.append("</object>")
                obj = ' '.join(txt)
            except KeyError:
                obj = "<object/>"
            # Try for Prep + Iobjstr
            ppxp = rec.process_xpath(session,
                                     "word[@arg1='%s%s']" % (vid[0],
                                                             int(vid[1:]) - 1))
            if ppxp:
                (name, attrs) = rec._convert_elem(ppxp[0][0])
                ptag = '<w pos="%s">%s</w>' % (attrs['pos'], ppxp[0][1][2:])
                prepstr = "<prep>%s</prep>\n" % ptag
                try:
                    xpth = "phrase[@id='%s']/descendant::word" % attrs['arg2']
                    iobjxp = rec.process_xpath(session, xpth)
                    iobjlist = ['<iobject>']
                    for w in iobjxp:
                        (name, nattrs) = rec._convert_elem(w[0])
                        iobjlist.append('<w pos="%s">%s</w>' % (nattrs['pos'],
                                                                w[1][2:]))
                    iobjlist.append('</iobject>')
                    iobjstr = ' '.join(iobjlist) + "\n"
                except:
                    prepstr = ""
                    iobjstr = ""

            verb.append('</verb>')
            verb = ' '.join(verb)
            docstr = ('<svopi recId="%s" sentenceId="%s">\n'
                      '  %s\n'
                      '  %s\n'
                      '  %s\n'
                      '%s%s</svopi>' % (rec.id, sentn, subj, verb,
                                        obj, prepstr, iobjstr))
            sentn += 1
            doc = StringDocument(docstr)
            if cache == 0:
                yield doc
            elif cache == 1:
                raise NotImplementedError
            else:
                docs.append(doc)
        self.documents = docs
        raise StopIteration
