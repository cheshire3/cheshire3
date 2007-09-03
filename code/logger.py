
from configParser import C3Object
from PyZ3950.CQLParser import PrefixableObject
import os, time, sys
from baseObjects import Session, Logger

class SimpleLogger(Logger):

    fileh = None
    lineCache = []
    cacheLen = 0

    _possiblePaths = {'filePath' : {'docs' : "Path to the where the logger will store its logs"}}
    _possibleSettings = {'cacheLength' : {'docs' : "The number of log entries to cache in memory before writing to disk"}}

    def __init__(self, session, config, parent):
        Logger.__init__(self, session, config, parent)
        fp = self.get_path(session, 'filePath')
        if (fp == "stdout"):
            self.fileh = sys.stdout
        elif (fp == "stderr"):
            self.fileh = sys.stderr
        else:
            if (not os.path.isabs(fp)):
                dfp = self.get_path(session, 'defaultPath')
                fp = os.path.join(dfp, fp)
            self.fileh = file(fp, 'a')
	clen = self.get_setting(session, 'cacheLength')
	if clen:
	    self.cacheLen = int(clen)
	else:
	    self.cacheLen = 0
	    
    def log(self, session, txt):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        line = "[%s]: %s" % (now, txt)
        self._logLine(line)

    def _logLine(self, line):
        if (self.lineCache and self.lineCache[-1].startswith(line)):
            self.lineCache[-1] += "."
        else:
            self.lineCache.append(line)
        if (len(self.lineCache) > self.cacheLen):
            for l in self.lineCache:
                self.fileh.write(l + "\n")
            self.fileh.flush()
            self.lineCache = []


class FunctionLogger(SimpleLogger):

    def __init__(self, session, config, parent):
        self.cacheLen = 1000
        SimpleLogger.__init__(self, session, config, parent)

    def _myRepr(self, a):
        if (isinstance(a, C3Object)):
            return a.id
        elif (isinstance(a, Session)):
            return "Session(%s)" % (a.user)
        elif (isinstance(a, PrefixableObject)):
            return repr(a.toCQL())
        else:
            return repr(a)

    def log(self, object, fn, *args, **kw):

        frame = sys._getframe(2)
        caller = frame.f_code.co_name
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        line = ["[%s]: from %s() : %s.%s(" % (now, caller, object.id, fn)]
        ln = []
        for a in args:
            ln.append(self._myRepr(a))
        for k in kw:
            ln.append("%s=%s" % (k, self._myRepr(kw[k])))
        atxt = ','.join(ln)
        line.append(atxt)
        line.append(")")
        line = ''.join(line)

        self._logLine(line)

        
