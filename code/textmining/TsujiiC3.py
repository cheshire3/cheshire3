
from baseObjects import DocumentFactory
from document import StringDocument

import os, re
from utils import getFirstData, elementType, verifyXPaths
import commands

class TsujiiObject:
    inh = None
    outh = None
    tokenizer = None

    _possiblePaths = {'taggerPath' : {'docs' : "Path to the tagger executable's directory, as must be run from there."}}

    def __init__(self, session, node, parent):
        o = os.getcwd()
        tp = self.get_path(session, 'taggerPath')
	if tp:
            os.chdir(tp)
        (a,b) = os.popen2('./tagger')
        self.inh = a
        self.outh = b
        os.chdir(o)
        
    def tag(self, session, data, xml=0):
	all = []
        paras = myTokenizer.split_paragraphs(data)
        for p in paras:
            sents = myTokenizer.split_sentences(p)
	    for s in sents:
		try:
		    self.inh.write(s)
		except UnicodeEncodeError:
		    self.inh.write(s.encode('utf-8'))
		self.inh.write("\n")
                self.inh.flush()
                tagd = self.outh.readline()                
                if xml:
                    tagd = self.toxml(tagd)
                all.append(tagd)
        return all

    def toxml(self, data):
        wds = data.split()
        xml = []
        for w in wds:
            t = w.split('/')
            xml.append('<t p="%s">%s</t>' % (t[1], t[0]))
            
        return " ".join(xml)


class EnjuObject:
    inh = None
    outh = None
    tokenizer = None

    _possiblePaths = {'enjuPath'  : {'docs' : "Path to enju executable."}}
    _possibleSettings = {'xml' : {'docs' : 'Should return XML form (1, default) or text (0)',
                                  'type' : int,
                                  'options' : '0|1'}}

    def __init__(self, session, node, parent):
        tp = self.get_path(session, 'enjuPath')
        if not tp:
            tp = commands.getoutput('which enju')
        if not tp:
            raise ConfigFileException("%s requires the path: enjuPath" % self.id)
        xml = self.get_setting(session, 'xml', 1)
        if xml:            
            (a,b,c) = os.popen3("%s -xml" % tp)
        else:
            (a,b,c) = os.popen3(tp)
        self.inh = a
        self.outh = b
        self.errh = c
        l = ""
        while l != 'Ready\n':
            l = c.readline()
        
    def tag(self, session, data, xml=0):
        s = data.strip()
        if not s:
            return ""
        try:
            self.inh.write(s)
        except UnicodeEncodeError:
            self.inh.write(s.encode('utf-8'))
        self.inh.write("\n")
        self.inh.flush()
        tagd = self.outh.readline()                
        return tagd


class GeniaObject:
    inh = None
    outh = None
    tokenizer = None

    _possiblePaths = {'filePath' : {'docs' : "Path to geniatagger executable."}}
    _possibleSettings = {'parseOutput' : {'docs' : "If 0 (default), then the output from the object will be the lines from genia, otherwise it will interpret back to word/POS", 'type' : int, 'options' : "0|1"}}

    def __init__(self, session, node, parent):
        self.unparsedOutput = self.get_setting(session, 'parseOutput', 0)
        tp = self.get_path(session, 'filePath')
        if not tp:
            tp = commands.getoutput('which geniatagger')
	    tp = os.path.dirname(tp)
	if not tp:
            raise ConfigFileException("%s requires the path: filePath" % self.id)
        # must be run in right directory :(
        o = os.getcwd()
	os.chdir(tp)
        (a,b,c) = os.popen3("./geniatagger")
        self.inh = a
        self.outh = b
        self.errh = c
        l = ""
        # Updated for Genia 3.0
        while l != 'loading named_entity_models..done.\n':
            l = c.readline()
        os.chdir(o)

        
    def tag(self, session, data, xml=0):
        words = []
        s = data.strip()
        if not s:
            return []
        try:
            self.inh.write(s)
        except UnicodeEncodeError:
            self.inh.write(s.encode('utf-8'))
        self.inh.write("\n")
        self.inh.flush()
        tagline = ""
        while 1:
            tagline = self.outh.readline()
            tagline = tagline.decode('utf-8')
            if tagline == "\n":
                if self.unparsedOutput:
                    words.append(tagline)
                break
            else:
                if self.unparsedOutput:
                    words.append(tagline)
                else:
                    (word, stem, type, type2, ner) = tagline[:-1].split('\t')
                    words.append({'text' : word, 'stem' : stem, 'pos' : type, 'phr' : type2})
        return words

