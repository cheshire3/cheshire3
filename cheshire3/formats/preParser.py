
import os, commands, mimetypes, tempfile

from cheshire3.preParser import CmdLinePreParser

class CmdLineMetadataDiscoveryPreParser(CmdLinePreParser):
    """Command Line PreParser to use external program for metadata discovery."""
    
    def __init__(self, session, config, parent):
        CmdLinePreParser.__init__(self, session, config, parent)
        
    def process_document(self, session, doc):
        """Pass the document to external executable, add results to document metadata."""
        cmd = self.cmd
        stdIn = cmd.find('%INDOC%') == -1
        stdOut = cmd.find('%OUTDOC%') == -1
        if not stdIn:
            if doc.mimeType:
                # guess our extn~n
                suff = mimetypes.guess_extension(doc.mimeType)
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
                    fh = file(outfn)
                else:
                    # command probably added something to the end
                    # annoying
                    matches = glob.glob(outfn + "*")
                    for m in matches:
                        if os.path.getsize(m) > 0:
                            fh = file(m)
                            break
                result = fh.read()
                fh.close()
                os.remove(outfn)
                
        doc.metadata[self.cmd.split()[0]] = result
        return doc
        