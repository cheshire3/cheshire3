
import os
import mimetypes
import tempfile
import glob
import re
import time
import subprocess
import shlex
import email

from xml.sax.saxutils import escape
from lxml import etree

# Cheshire3 imports
from cheshire3.record import LxmlRecord
from cheshire3.baseObjects import PreParser
from cheshire3.document import StringDocument
from cheshire3.preParser import CmdLinePreParser, TypedPreParser
from cheshire3.workflow import CachingWorkflow
from cheshire3.xpathProcessor import SimpleXPathProcessor
from cheshire3.utils import getShellResult


class DependentCmdLinePreParser(CmdLinePreParser):
    """Command Line PreParser to start an external service before processing document."""
    
    
    _possiblePaths = {"dependencyExecutable": {'docs' : "Name of the executable to run to start required service."}
                     ,'dependencyExecutablePath' : {'docs' : "Path to the dependency's executable"}
                     }
    
    _possibleSettings = {'dependencyCommandLine' : {'docs' : "Command line to use when starting dependency"}}
    
    dependency = None
    
    def __init__(self, session, config, parent):
        CmdLinePreParser.__init__(self, session, config, parent)
        self._initDependency(session)
        
    def _initDependency(self, session):
        exe = self.get_path(session, 'dependencyExecutable', '')
        if not exe:
            raise ConfigFileException("Missing mandatory 'dependencyExecutable' path in %s" % self.id)
        tp = self.get_path(session, 'dependencyExecutablePath', '')
        if tp:
            exe = os.path.join(tp, exe)

        cl = self.get_setting(session, 'dependencyCommandLine', '')
        self.dependency = subprocess.Popen([exe] + shlex.split(cl))


class CmdLineMetadataDiscoveryPreParser(CmdLinePreParser):
    """Command Line PreParser to use external program for metadata discovery."""
    
    _possibleSettings = {"metadataType": {'docs' : "Key to use in document.metadata dictionary (often the name of the external program)"}
                        ,"metadataSubType": {'docs' : "Key to use in document.metadata[metadataKey] dictionary (allows output from running command multiple times with different arguments to be merged into single dictionary)"}
                         }
    
    def __init__(self, session, config, parent):
        CmdLinePreParser.__init__(self, session, config, parent)
        mdt = self.get_setting(session, 'metadataType', None)
        if mdt is not None:
            self.metadataType = mdt
        else:
            self.metadataType = self.get_path(session, 'executable', self.cmd.split()[0])
            
        self.metadataSubType = self.get_setting(session, 'metadataSubType', 'result')
        
    def _processResult(self, session, data):
        """Process result from external program."""
        res = {}
        # look for a version number (most common use of this base class is *nix file utility)
        vRe = re.compile('''(?:[,:;]\s)?    # possibly a leading comma followed by whitespace
                            v(?:ersion)?\s? # 'v' 'version' 'v ' or 'version '
                            (\d+(\.\d+)*)   # this is the actual version number, possibly with major, minor revision parts 
                        ''', re.VERBOSE)
        vMatch = vRe.search(data) 
        if vMatch is not None:
            res['version'] = vMatch.group(1)
            data = vRe.sub('', data)
            
        res[self.metadataSubType] = data
        return res
        
    def process_document(self, session, doc):
        """Pass Document to executable, add results to document metadata."""
        cmd = self.cmd
        stdIn = cmd.find('%INDOC%') == -1
        stdOut = cmd.find('%OUTDOC%') == -1
        if not stdIn:
            if doc.mimeType or doc.filename:
                # guess our extn~n                
                try: suff = mimetypes.guess_extension(doc.mimeType)
                except: suff = ''
                if not suff:
                    suff = mimetypes.guess_extension(doc.filename)
                if suff:
                    (qq, infn) = tempfile.mkstemp(suff)
                else:
                    (qq, infn) = tempfile.mkstemp()                    
            else:
                (qq, infn) = tempfile.mkstemp()
            os.close(qq)
            fh = file(infn, 'w')
            fh.write(doc.get_raw(session))
            fh.close()
            cmd = cmd.replace("%INDOC%", infn)
            
        if not stdOut:
            if self.outMimeType:
                # guess our extn~n
                suff = mimetypes.guess_extension(self.outMimeType)
                (qq, outfn) = tempfile.mkstemp(suff)
            else:
                (qq, outfn) = tempfile.mkstemp()
            cmd = cmd.replace("%OUTDOC%", outfn)               
            os.close(qq)
        
        if self.working:
            old = os.getcwd()
            os.chdir(self.working)            
        else:
            old = ''
            
        if stdIn:
            pipe = subprocess.Popen(cmd, bufsize=0, shell=True,
                         stdin=subprocess.PIPE, 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
            pipe.stdin.write(doc.get_raw(session))
            pipe.stdin.close()
            result = pipe.stdout.read()
            pipe.stdout.close()
            pipe.stderr.close()
            del pipe
        else:
            # result will read stdout+err regardless
            result = getShellResult(cmd)
            os.remove(infn)
            if not stdOut:
                if os.path.exists(outfn) and os.path.getsize(outfn) > 0:
                    ofh = open(outfn)
                else:
                    # command probably added something to the end
                    # annoying
                    matches = glob.glob(outfn + "*")
                    for m in matches:
                        if os.path.getsize(m) > 0:
                            ofh = open(m)
                            break
                result = ofh.read()
                ofh.close()
                os.remove(outfn)
            # strip input filename from result if present (this is a tempfile so the name is useless)
            if result.startswith(infn):
                result = re.sub('^%s\s*[:-]?\s*' % (infn), '', result)
        if old:
            os.chdir(old)
        try:
            doc.metadata[self.metadataType].update(self._processResult(session, result))
        except:
            doc.metadata[self.metadataType] = self._processResult(session, result)
            
        if 'analysisDateTime' not in doc.metadata[self.metadataType]:
            doc.metadata[self.metadataType]['analysisDateTime'] = time.strftime('%Y-%m-%dT%H:%M:%S%Z')
        return doc
    

class TxtParsingCmdLineMetadataDiscoveryPreParser(CmdLineMetadataDiscoveryPreParser):
    """For external programs that return multi-line text output.
    
    Command Line PreParser to use an external program for metadata 
    discovery, when output of the external program is colon separated 
    key:value pairs in plain-text. Takes the output, parses it using a 
    regular expression, and extracts metadata based on configured 
    sources and populates Document metadata dictionary/hash.
    """
    
    def __init__(self, session, config, parent):
        CmdLineMetadataDiscoveryPreParser.__init__(self, session, config, parent)
        self.lineRe = re.compile('^(.*?):\s+(.*)$', re.MULTILINE)
    
    def _processResult(self, session, data):
        """Process result from external program."""
        res = {}
        for k,v in self.lineRe.findall(data):
            res[k] = unicode(v, 'utf-8')
        return res
        
        
class XmlParsingCmdLineMetadataDiscoveryPreParser(CmdLineMetadataDiscoveryPreParser):
    """For external programs that return XML.
    
    Command Line PreParser to use an external program for metadata 
    discovery, when output of the external program is XML. Takes the 
    XML output, parses it, and extracts metadata based on configured 
    sources and populates Document metadata dictionary/hash.
    """
    
    def __init__(self, session, config, parent):
        self.sources = {}
        CmdLineMetadataDiscoveryPreParser.__init__(self, session, config, parent)
        
    
    def _handleLxmlConfigNode(self, session, node):
        # Source
        if (node.tag in ['source', '{%s}source' % CONFIG_NS]):
            key = node.attrib.get('id', None)
            default = node.attrib.get('default', None)
            process = None
            preprocess = None
            xp = None
            for child in node.iterchildren(tag=etree.Element):
                if child.tag in ['xpath', '{%s}xpath' % CONFIG_NS]:
                    if xp is None:
                        ref = child.attrib.get('ref', '')
                        if ref:
                            xp = self.get_object(session, ref)
                        else:
                            node.set('id', self.id + '-xpath')
                            xp = SimpleXPathProcessor(session, node, self)
                            xp._handleLxmlConfigNode(session, node)
                elif child.tag in ['preprocess', '{%s}preprocess' % CONFIG_NS]:
                    # turn preprocess chain to workflow
                    ref = child.attrib.get('ref', '')
                    if ref:
                        preprocess = self.get_object(session, ref)
                    else:
                        # create new element
                        e = etree.XML(etree.tostring(child))
                        e.tag = 'workflow'
                        e.set('id', self.id + "-preworkflow")
                        preprocess = CachingWorkflow(session, child, self)
                        preprocess._handleLxmlConfigNode(session, child)
                elif child.tag in ["process", '{%s}process' % CONFIG_NS]:
                    # turn xpath chain to workflow
                    ref = child.attrib.get('ref', '')
                    if ref:
                        process = self.get_object(session, ref)
                    else:
                        # create new element
                        e = etree.XML(etree.tostring(child))
                        e.tag = 'workflow'
                        e.set('id', self.id + "-workflow")
                        process = CachingWorkflow(session, e, self)
                        process._handleLxmlConfigNode(session, e)
                        
            self.sources[key] = {'source': (xp, process, preprocess), 'default': default}
            
    def _processResult(self, session, data):
        """Parse XML to create and return dict of metadata items.
        
        Parse XML output from external program.
        Process parsed XML using self.sources.
        Populate and return a dictionary of metadata items.
        
        """
        try:
            et = etree.fromstring(data)
        except AssertionError:
            data = data.decode('utf8')
            et = etree.fromstring(data)
        except etree.XMLSyntaxError:
            if session.logger is not None:
                # log debug level
                session.logger.log_lvl(session, 10, data)
            raise
        record = LxmlRecord(et)
        record.byteCount = len(data)
        mddict = {}
        for key, src in self.sources.iteritems():
            (xpath, process, preprocess) = src['source']
            if preprocess is not None:
                record = preprocess.process(session, record)
            if xpath is not None:
                rawlist = xpath.process_record(session, record)
                processed = process.process(session, rawlist)
            else:
                processed = process.process(session, record)
            
            if len(processed) > 1:
                mddict[key] = []
                for pl, k in sorted([(val['proxLoc'], k) for k, val in processed.iteritems()]):
                    for x in pl:
                        mddict[key].append(k)
                    
            elif len(processed) == 1:
                mddict[key] = processed.keys()[0]
            elif src['default'] is not None:
                mddict[key] = src['default']
            
        return mddict
    
    
class DependentXmlParsingCmdLineMetadataDiscoveryPreParser(DependentCmdLinePreParser, XmlParsingCmdLineMetadataDiscoveryPreParser):
    """XmlParsingCmdLineMetadataDiscoveryPreParser with a dependency."""
    
    def __init__(self, session, config, parent):
        XmlParsingCmdLineMetadataDiscoveryPreParser.__init__(self, session, config, parent)
        self._initDependency(session)
    

class EmailToXmlPreParser(TypedPreParser):
    """PreParser to process email data and output it as XML."""
    
    def _processHeaders(self, msg):
        out = ['<headers>']
        for k,v in msg.items():
            out.append('<%s>%s</%s>' % (k,escape(v),k))
        out.append('</headers>')
        return out
    
    def _processPayload(self, msg):
        out = []
        if msg.is_multipart():
            out.append('<multipart-mixed>')
            for part in msg.walk():
                if part == msg:
                    continue
                out.append('<part>')
                out.extend(self._processHeaders(part))
                out.extend(self._processPayload(part))
                out.append('</part>')
            out.append('</multipart-mixed>')
        else:
            out.extend(['<body mime-type="%s">' % (msg.get_content_type()), escape(msg.get_payload()), '</body>'])
        return out
    
    def process_document(self, session, doc):
        data = doc.get_raw(session)
        msg = email.message_from_string(data)
        out = ['<email>', ]
        out.extend(self._processHeaders(msg))
        out.extend(self._processPayload(msg))
        out.append('</email>')
        mt = self.outMimeType
        if not mt:
            mt = doc.mimeType
        return StringDocument(''.join(out), self.id, doc.processHistory, mimeType=mt, parent=doc.parent, filename=doc.filename)
