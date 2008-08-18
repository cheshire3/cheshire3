
from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Session, Logger
from cheshire3.cqlParser import PrefixableObject

import os, time, sys
import logging

class SimpleLogger(Logger):

    fileh = None
    lineCache = []
    cacheLen = 0

    _possiblePaths = {'filePath' : {'docs' : "Path to the where the logger will store its logs"}}
    _possibleSettings = {'cacheLength' : {'docs' : "The number of log entries to cache in memory before writing to disk", 'type': int},
                         'minLevel' : {'docs' : 'The minimum level that this logger will record, if a level is given.', 'type' : int}}
    _possibleDefaults = {'defaultLevel' : {'docs' : 'The default level to assign to logged messages if one isn\'t provided', 'type' : int}
                         }

    def __init__(self, session, config, parent):
        Logger.__init__(self, session, config, parent)
        fp = self.get_path(session, 'filePath')
        if (fp in ["stdout", 'sys.stdout']):
            self.fileh = sys.stdout
        elif (fp in ["stderr", 'sys.stderr']):
            self.fileh = sys.stderr
        else:
            if (not os.path.isabs(fp)):
                dfp = self.get_path(session, 'defaultPath')
                fp = os.path.join(dfp, fp)
            self.fileh = file(fp, 'a')
        self.cacheLen = self.get_setting(session, 'cacheLength', 0)
        self.minLevel = self.get_setting(session, 'minLevel', 0)
        self.defaultLevel = self.get_default(session, 'level', 0)

    def _myRepr(self, a):
        if (isinstance(a, C3Object)):
            return a.id
        elif (isinstance(a, Session)):
            return "Session(%s)" % (a.user)
        elif (isinstance(a, PrefixableObject)):
            return repr(a.toCQL())
        else:
            return repr(a)

    def _logLine(self, lvl, line, *args, **kw):

        # templating here etc
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        lvlstr = ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'][max(int(lvl/10), 6)]        
        line = "[%s] %s: %s" % (now, lvlstr, line)

        if (self.lineCache and self.lineCache[-1].startswith(line)):
            self.lineCache[-1] += "."
        else:
            self.lineCache.append(line)
        if (len(self.lineCache) > self.cacheLen):
            for l in self.lineCache:
                self.fileh.write(l + "\n")
            self.fileh.flush()
            self.lineCache = []

    def log_fn(self, object, fn, *args, **kw):
        # just construct message

        frame = sys._getframe(2)
        caller = frame.f_code.co_name
        line = ["from %s() : %s.%s(" % (caller, object.id, fn)]
        ln = []
        for a in args:
            ln.append(self._myRepr(a))
        for k in kw:
            ln.append("%s=%s" % (k, self._myRepr(kw[k])))
        atxt = ','.join(ln)
        line.append(atxt)
        line.append(")")
        line = ''.join(line)
        self.log_lvl(None, 0, line)

    def log(self, session, msg):
        self.log_lvl(session, self.defaultLevel, msg)

    def log_lvl(self, session, lvl, msg, *args, **kw):
        if not lvl:
            lvl = self.defaultLevel
        if lvl >= self.minLevel:
            self._logLine(lvl, msg, *args, **kw)


class FunctionLogger(SimpleLogger):

    def __init__(self, session, config, parent):
        # default to caching or ...will... BE... REALLY... SLOW...
        self.cacheLen = 1000
        SimpleLogger.__init__(self, session, config, parent)


class LoggingLogger(SimpleLogger):

    _possibleSettings = {'name' : {'docs' : "The name to call the logger in logging module. Defaults to root logger if not supplied."}}

    def __init__(self, session, config, parent):
        # default to caching or ...will... BE... REALLY... SLOW...
        SimpleLogger.__init__(self, session, config, parent)
        name = self.get_path(session, 'name', '')
        if name:
            # use specific Logger obj
            self.logger = logging.getLogger(name)
        else:
            # default to module level log fn
            self.logger = logging

    def _logLine(self, lvl, msg, *args, **kw):
        # pass through
        self.logger.log(lvl, msg, *args, **kw)
