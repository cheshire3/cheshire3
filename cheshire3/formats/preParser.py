
import os, commands, mimetypes, tempfile, glob, re
from lxml import etree

from cheshire3.record import LxmlRecord
from cheshire3.preParser import CmdLinePreParser
from cheshire3.workflow import CachingWorkflow
from cheshire3.xpathProcessor import SimpleXPathProcessor


class DependentCmdLinePreParser(CmdLinePreParser):
    """Command Line PreParser to start an external service before processing document."""
    
    
    _possiblePaths = {"dependencyExecutable": {'docs' : "Name of the executable to run to start required service."}
                     ,'dependencyExecutablePath' : {'docs' : "Path to the dependency's executable"}
                     }
    
    _possibleSettings = {'dependencyCommandLine' : {'docs' : "Command line to use when starting dependency"}}
    
    dependency = None
    
    def __init__(self, session, config, parent):
        CmdLinePreParser.__init__(self, session, config, parent)
        exe = self.get_path(session, 'dependencyExecutable', '')
        if not exe:
            raise ConfigFileException("Missing mandatory 'dependencyExecutable' path in %s" % self.id)
        tp = self.get_path(session, 'dependencyExecutablePath', '')
        if tp:
            exe = os.path.join(tp, exe)

        cl = self.get_setting(session, 'dependencyCommandLine', '')
        self.dependency = os.popen(exe + ' ' + cl)


class CmdLineMetadataDiscoveryPreParser(CmdLinePreParser):
    """Command Line PreParser to use external program for metadata discovery."""
    
    def __init__(self, session, config, parent):
        self._possibleSettings["metadataType"] = {'docs' : "Key to use in document.metadata dictionary (often the name of the external program)"}
        CmdLinePreParser.__init__(self, session, config, parent)
        mdt = self.get_setting(session, 'metadataType', None)
        if mdt is not None:
            self.metadataType = mdt
        else:
            self.metadataType = self.get_path(session, 'executable', self.cmd.split()[0])
        
    def _processResult(self, session, data):
        """Process result from external program."""
        return data
        
    def process_document(self, session, doc):
        """Pass the document to external executable, add results to document metadata."""
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
            pipe = Popen(cmd, bufsize=0, shell=True,
                         stdin=PIPE, stdout=PIPE, stderr=PIPE)
            pipe.stdin.write(doc.get_raw(session))
            pipe.stdin.close()
            result = pipe.stdout.read()
            pipe.stdout.close()
            pipe.stderr.close()
        else:
            # result will read stdout+err regardless
            result = commands.getoutput(cmd)
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
                
        doc.metadata[self.metadataType] = self._processResult(session, result)
        return doc
        
        
class XmlParsingCmdLineMetadataDiscoveryPreParser(CmdLineMetadataDiscoveryPreParser):
    """Command Line PreParser to take the results of an external program given in XML, parse it, and extract metadata into a hash."""
    
    def __init__(self, session, config, parent):
        self.sources = {}
        CmdLineMetadataDiscoveryPreParser.__init__(self, session, config, parent)
        
    
    def _handleLxmlConfigNode(self, session, node):
        # Source
        if (node.tag == "source"):
            key = node.attrib.get('id', None)
            default = node.attrib.get('default', None)
            process = None
            preprocess = None
            xp = None
            for child in node.iterchildren(tag=etree.Element):
                if child.tag == "xpath":
                    if xp == None:
                        ref = child.attrib.get('ref', '')
                        if ref:
                            xp = self.get_object(session, ref)
                        else:
                            node.set('id', self.id + '-xpath')
                            xp = SimpleXPathProcessor(session, node, self)
                            xp._handleLxmlConfigNode(session, node)
                elif child.tag == "preprocess":
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
                elif child.tag == "process":
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
        """Process XML output from external program, process self.sources to create dictionary of metadata items."""
        try:
            et = etree.fromstring(data)
        except AssertionError:
            data = data.decode('utf8')
            et = etree.XML(data)
            
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
            
            if processed:
                mddict[key] = ' '.join(processed.keys())
            elif src['default'] is not None:
                mddict[key] = src['default']
            
        return mddict
        