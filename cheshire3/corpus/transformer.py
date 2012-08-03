
import re

from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Transformer
from cheshire3.document import StringDocument

from copy import copy
from lxml import etree


class CorpusPrepTransformer(Transformer):
# Adds all the required elements if they are not already in the input xml:
#    adds eid on requested elements

    _possibleSettings = {'eidXpath' : {'docs' : 'xpath to all nodes which need eid attributes (these should be all nodes which you want to index and retrieve at their own level including span indexes)'},
                         }
    
    def __init__(self, session, config, parent):       
        Transformer.__init__(self, session, config, parent)
        self.session = session
        self.extractor = self.get_path(session, 'extractor')
        self.rfot = self.get_path(session, 'tokenizer')
        self.regexp = re.compile('[\s]+')
        self.eidXpath = self.get_setting(session, 'eidXpath')
    
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
                    el= etree.Element('n')
                    el.text = ''.join(cnw)
                    alltoks.append(el)
                cnw = [c]
                space = csp
        if cnw:
            el= etree.Element('n')
            el.text = ''.join(cnw)
            alltoks.append(el)
        return alltoks
            
            
    def process_record(self, session, rec):
        tree = rec.get_dom(session)
        
        # add option to sentence tokenize?
        if self.eidXpath is not None:
            elems = tree.xpath(self.eidXpath)
            eid = 1       
            for e in elems :
                e.set('eid', str(eid))
                eid += 1
    
        # 
        lookingForW = False
        waiting = None
        totalOffset = 0
        wordOffset = 0
        for s in tree.xpath('//s') :   
            text = re.sub(self.regexp, ' ', self.extractor._flattenTexts(s)).strip()           
            wordCount = 0
            start = 0
            nList = []
            tBase, oBase = self.rfot.process_string(self.session, text)
            txt = etree.Element('txt')
            txt.text = text
            #create toks and delete the children of s
            toks = etree.Element('toks')
            #deal with any .text. content of S
            if s.text:
                t, o = self.rfot.process_string(self.session, s.text)
                for i in range(0, len(t)):
                    w = etree.Element('w')
                    w.text = t[i]
                    w.set('o', str(oBase[wordCount]))
                    if lookingForW:
                        waiting.set('offset', str(oBase[wordCount] + totalOffset))
                        toks.append(waiting)
                        waiting = None
                        lookingForW = False
                        
                    if oBase[wordCount] > start:
                        nwtxt = text[start:oBase[wordCount]]
                        nList = self.get_toks(nwtxt)
                        tlen = len(tBase[wordCount])
                        start = oBase[wordCount] + tlen
                    else:
                        tlen = len(tBase[wordCount])
                        start += tlen             
                    toks.extend(nList)
                    toks.append(w)
                    wordCount += 1
                    wordOffset +=1
                s.text = ''
            #deal with each tag within S
            try:
                walker = s.getiterator()
            except AttributeError:
                # lxml 1.3 or later
                walker = s.iter()           
            for c in walker:      
                if c.tag not in ['s', '{%s}s' % CONFIG_NS]:
                    #deal with any .text content
                    if c.text:
                        t, o = self.rfot.process_string(self.session, c.text)
                        for i in range(0, len(t)):
                            w = etree.Element('w')
                            w.text = t[i]
                            w.set('o', str(oBase[wordCount]))
                            if lookingForW:
                                waiting.set('offset', str(oBase[wordCount] + totalOffset))
                                toks.append(waiting)
                                waiting = None
                                lookingForW = False
                            if not c.get('offset'):
                                c.set('offset', str(oBase[wordCount] + totalOffset))
                                c.set('wordOffset', str(wordOffset))
                            if oBase[wordCount] > start:
                                nwtxt = text[start:oBase[wordCount]]
                                nList = self.get_toks(nwtxt)
                                tlen = len(tBase[wordCount])
                                start = oBase[wordCount] + tlen
                            c.extend(nList)
                            c.append(w) 
                            wordCount += 1
                            wordOffset +=1
                        toks.append(c)
                        c.text = ''
                    #deal with the tag itself
                    else:  
                        if lookingForW:
                            try:
                                waiting.set('offset', str(oBase[wordCount] + totalOffset))
                            except:
                                waiting.set('offset', str(oBase[wordCount-1] + totalOffset))
                            toks.append(waiting)
                            waiting = None
                            lookingForW = False   
                        try:
                            c.set('offset', str(oBase[wordCount] + totalOffset))     
                        except:
                            #this is the last tag of an s so we need to wait to get another w element before setting the offset value
                            c.set('wordOffset', str(wordOffset))
                            lookingForW = True
                            waiting = copy(c)
                            s.remove(c)
                        else:
                            c.set('wordOffset', str(wordOffset))
                            toks.append(c)
                    #deal with any .tail element of the tag
                    if c.tail:
                        t, o = self.rfot.process_string(self.session, c.tail)
                        for i in range(0, len(t)):
                            w = etree.Element('w')
                            w.text = t[i]
                            w.set('o', str(oBase[wordCount]))
                            if lookingForW:
                                waiting.set('offset', str(oBase[wordCount] + totalOffset))
                                toks.append(waiting)
                                waiting = None
                                lookingForW = False
                            if not c.get('offset'):
                                c.set('offset', str(oBase[wordCount] + totalOffset))
                                c.set('wordOffset', str(wordOffset))
                            if oBase[wordCount] >= start:
                                nwtxt = text[start:oBase[wordCount]]
                                nList = self.get_toks(nwtxt)
                                tlen = len(tBase[wordCount])
                                start = oBase[wordCount] + tlen
                            toks.extend(nList)
                            toks.append(w) 
                            wordCount += 1
                            wordOffset +=1
                        c.tail = ''
            if s.tail:
                t, o = self.rfot.process_string(self.session, s.tail)
                for i in range(0, len(t)):
                    w = etree.Element('w')
                    w.text = t[i]
                    w.set('o', str(oBase[wordCount]))
                    if lookingForW:
                        waiting.set('offset', str(oBase[wordCount] + totalOffset))
                        toks.append(waiting)
                        waiting = None
                        lookingForW = False
                    if oBase[wordCount] > start:
                        nwtxt = text[start:oBase[wordCount]]
                        nList = self.get_toks(nwtxt)
                        tlen = len(tBase[wordCount])
                        start = oBase[wordCount] + tlen
                    toks.extend(nList)
                    toks.append(w)
                    wordCount += 1
                    wordOffset +=1
                s.tail = '' 
            if start < len(text):
                    # get the last
                nwtxt = text[start:]
                toks.extend(self.get_toks(nwtxt))
                s.text = ''
            totalOffset += len(text) + 1
            s.append(txt)            
            s.append(toks)       
        return StringDocument(etree.tostring(tree))
          

