
import os, commands, mimetypes, tempfile, glob

from cheshire3.document import StringDocument
from cheshire3.bootstrap import BSLxmlParser
from cheshire3.preParser import CmdLinePreParser

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
        
    def _processResult(self, data):
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

        if old:
            os.chdir(old)
                
        doc.metadata[self.metadataType] = self._processResult(session, result)
        return doc
        
        
class DroidCmdLineMetadataDiscoveryPreParser(CmdLineMetadataDiscoveryPreParser):
    """Command Line PreParser to use the National Archives' DROID software for format identification."""
    
    def _processResult(self, session, data):
        """Process output from DROID."""
        bsdoc = StringDocument(data)
        bsrec = BSLxmlParser.process_document(session,bsdoc)
        dom = bsrec.get_dom(session)
        nsdict = {'tna': "http://www.nationalarchives.gov.uk/pronom/FileCollection"}
        mddict = {}
        try: mddict['Certainty'] = dom.xpath('/tna:FileCollection/tna:IdentificationFile/@IdentQuality', namespaces=nsdict)[0]
        except IndexError: mddict['certainty'] = 'Unknown'
        mddict['mimeType'] = dom.xpath('string(//tna:IdentificationFile/tna:FileFormatHit/tna:MimeType)', namespaces=nsdict)
        if not len(mddict['mimeType']): mddict['mimeType'] = 'Unknown'
            
        for mdbit in ['Name', 'Version', 'PUID']:
            mddict['Format ' + mdbit] = dom.xpath('string(//tna:IdentificationFile/tna:FileFormatHit/tna:%s)' % (mdbit), namespaces=nsdict)
            
        warn = dom.xpath('string(//tna:IdentificationFile/tna:FileFormatHit/tna:IdentificationWarning)', namespaces=nsdict)
        if warn: mddict['Warning'] = warn 

        return mddict
    
    