from __future__ import absolute_import

import os
import re

from subprocess import Popen, PIPE

from cheshire3.baseObjects import DocumentFactory
from cheshire3.document import StringDocument
from cheshire3.utils import getFirstData, elementType, getShellResult
from cheshire3.exceptions import ConfigFileException


class TsujiiObject:
    pipe = None
    tokenizer = None

    _possiblePaths = {
        'executablePath': {
            'docs': ("Path to the tagger executable's directory, as must"
                     "be run from there.")},
        'executable': {
            'docs': 'Name of executable'
        }
    }

    def __init__(self, session, node, parent):
        o = os.getcwd()
        tp = self.get_path(session, 'executablePath')
        if tp:
            os.chdir(tp)
        exe = self.get_path(session, 'executable', './tagger')

        self.pipe = Popen(exe, shell=True, bufsize=1,
                          stdin=PIPE, stdout=PIPE, stderr=PIPE)
        os.chdir(o)

    def tag(self, session, data, xml=0):
        all = []
        paras = myTokenizer.split_paragraphs(data)
        for p in paras:
            sents = myTokenizer.split_sentences(p)
            for s in sents:
                try:
                    self.pipe.stdin.write(s)
                except UnicodeEncodeError:
                    self.pipe.stdin.write(s.encode('utf-8'))
                self.pipe.stdin.write("\n")
                self.pipe.stdin.flush()
                tagd = self.pipe.stdout.readline()
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
    pipe = None
    tokenizer = None

    _possiblePaths = {
        'executablePath': {
            'docs': "Path to enju executable."
        },
        'executable': {
            'docs': 'Name of executable'
        }
    }

    _possibleSettings = {
        'xml': {
            'docs': 'Should return XML form (1, default) or text (0)',
            'type': int,
            'options': '0|1'
        }
    }

    def __init__(self, session, node, parent):
        tp = self.get_path(session, 'executablePath', '')
        exe = self.get_path(session, 'executable', 'enju')
        if not tp:
            tp = getShellResult('which %s' % exe)
            tp = tp if not tp.startswith('which:') else exe
        else:
            tp = os.path.join(tp, exe)
        xml = self.get_setting(session, 'xml', 1)
        if xml:
            cmd = "%s -xml" % tp
        else:
            cmd = tp
        self.pipe = Popen(cmd, shell=True, bufsize=1,
                          stdin=PIPE, stdout=PIPE, stderr=PIPE)
        l = ""
        while l != 'Ready\n':
            # Check for errors with command
            if "command not found" in l:
                self.log_error(session,
                               "Error while initializing EnjuObject: "
                               "{0}".format(l.strip()))
                break
            l = self.pipe.stderr.readline()

    def tag(self, session, data, xml=0):
        s = data.strip()
        if not s:
            return ""
        try:
            self.pipe.stdin.write(s)
        except UnicodeEncodeError:
            self.pipe.stdin.write(s.encode('utf-8'))
        self.pipe.stdin.write("\n")
        self.pipe.stdin.flush()
        tagd = self.pipe.stdout.readline()
        return tagd


class GeniaObject:
    pipe = None
    tokenizer = None

    _possiblePaths = {
        'executablePath': {
            'docs': "Path to geniatagger executable."},
        'executable': {
            'docs': 'Name of executable'
        }
    }

    _possibleSettings = {
        'parseOutput': {
            'docs': ("If 0 (default), then the output from the object will "
                     "be the lines from genia, otherwise it will interpret "
                     "back to word/POS"),
            'type': int,
            'options': "0|1"
        },
        'tokenize': {
            'docs': '',
            'type': int,
            'options': '0|1'
        }
    }

    def __init__(self, session, node, parent):
        self.unparsedOutput = self.get_setting(session, 'parseOutput', 0)
        tp = self.get_path(session, 'executablePath', '')
        exe = self.get_path(session, 'executable', 'geniatagger')
        if not tp:
            tp = getShellResult('which %s' % exe)
            tp = os.path.dirname(tp)
        tpe = os.path.join(tp, exe)
        if not tp:
            raise ConfigFileException("%s requires the path: "
                                      "executablePath" % self.id)
        o = os.getcwd()
        os.chdir(tp)
        if self.get_setting(session, 'tokenize', 0):
            cmd = exe
        else:
            cmd = "%s -nt" % exe
        self.pipe = Popen(cmd, shell=True, bufsize=1,
                          stdin=PIPE, stdout=PIPE, stderr=PIPE)

        l = ""
        while l != 'loading named_entity_models..done.\n':
            l = self.pipe.stderr.readline()
        os.chdir(o)

    def tag(self, session, data, xml=0):
        words = []
        s = data.strip()
        if not s:
            return []
        try:
            self.pipe.stdin.write(s)
        except UnicodeEncodeError:
            self.pipe.stdin.write(s.encode('utf-8'))
        self.pipe.stdin.write("\n")
        self.pipe.stdin.flush()
        tagline = ""
        while 1:
            tagline = self.pipe.stdout.readline()
            tagline = tagline.decode('utf-8')
            if tagline == "\n":
                break
            elif tagline.isspace():
                continue
            else:
                if self.unparsedOutput:
                    words.append(tagline)
                else:
                    (word, stem, type, type2, ner) = tagline[:-1].split('\t')
                    words.append({'text': word,
                                  'stem': stem,
                                  'pos': type,
                                  'phr': type2})
        return words
