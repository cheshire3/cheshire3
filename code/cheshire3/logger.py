
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
    _possibleDefaults = {'level' : {'docs' : 'The default level to assign to logged messages if one isn\'t provided', 'type' : int}
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
            self.fileh = open(fp, 'a')
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
        lvlstr = ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'][min(int(lvl/10), 5)]
        line = "[%s] %s: %s" % (now, lvlstr, line)

        if (self.lineCache and self.lineCache[-1].startswith(line)):
            self.lineCache[-1] += "."
        else:
            self.lineCache.append(line)
        if (len(self.lineCache) > self.cacheLen):
            for l in self.lineCache:
                if type(l) == unicode:
                    l = l.encode('utf8')
                self.fileh.write(l + "\n")
            if hasattr(self.fileh, 'flush'):
                self.fileh.flush()
            self.lineCache = []

    def log_fn(self, session, object, fn, *args, **kw):
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
        try:
            line.append(") by user : {0}".format(session.user.username))
        except AttributeError:
            # no user
            line.append(")")
        line = ''.join(line)
        self.log_lvl(session, self.defaultLevel, line)

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
        SimpleLogger.__init__(self, session, config, parent)
        self.cacheLen = self.get_setting(session, 'cacheLength', 1000) # still give config ability to over-ride but increase default


class LoggingLogger(SimpleLogger):
    """Logger to use Python built-in logging module."""

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


class DateTimeFileLogger(SimpleLogger):
    """Logger to write date time rotating log files. """
    
    _possibleSettings = {'createSubDirs' : {'docs' :'Should a sub-directory be used for this log', 'type' : int, 'options' : "0|1"}
                        ,'dateTimeLevel' : {'docs' : 'What level of separation should be used when logging. If createSubDir is set, sub-directories will be created to this level, otherwise separation will be by filename. e.g. separate sub-directory / file for year, month, day etc. ', 'type' : str, 'options' : "year|month|day|hour|minute"}
                        }
    
    dateTimeFormats = ["%Y", "%m", "%d","%H", "%M"]
    
    def __init__(self, session, config, parent):
        Logger.__init__(self, session, config, parent)
        # generic Logger settings
        self.cacheLen = self.get_setting(session, 'cacheLength', 100) # default to caching 100 lines per log file when writing in iRODS
        self.minLevel = self.get_setting(session, 'minLevel', 0)
        self.defaultLevel = self.get_default(session, 'level', 0)
        # rotating bits
        self.createSubDirs = self.get_setting(session, 'createSubDirs', 1)
        dtlvl = self.get_setting(session, 'dateTimeLevel', '').lower()
        dtlvls = self._possibleSettings['dateTimeLevel']['options'].split('|')
        if not dtlvl in dtlvls:
            raise ConfigFileException("Unrecognized value for 'dateTimeLevel' setting")        
        self.dateTimeLevel = dtlvls.index(dtlvl)+1
        self.lastLogTime = time.gmtime()
        self._open(session)
        
    def __del__(self):
        self._close()
        
    def __exit__(self):
        self._close()

    def _open(self, session):
        # we don't actually want to open a file until there's something to log - just find log base path
        fp = self.get_path(session, 'filePath', self.id)
        if (not os.path.isabs(fp)):
            dfp = self.get_path(session, 'defaultPath')
            fp = os.path.join(dfp, fp)
        self.logBasePath = fp

    def _close(self):
        # flush any remaining log lines
        self._flush()
        
    def _getLogFile(self):
        fnbits = [self.logBasePath]
        for dtlvl in range(self.dateTimeLevel):
            dtb = time.strftime(self.dateTimeFormats[dtlvl], self.lastLogTime)
            fnbits.append(dtb)
        if self.createSubDirs:
            try: os.makedirs(os.path.join(*fnbits[:-1])) # create necessary directory structure
            except OSError: pass
            fn = os.path.join(*fnbits) 
        else:
            fn = '-'.join(fnbits)
        return open(fn + '.log', 'a')
    
    def _flush(self):
        """ Flush log lines to file. """
        if not len(self.lineCache):
            return
        
        fileh = self._getLogFile()
        try:
            for l in self.lineCache:
                if type(l) == unicode:
                    l = l.encode('utf8')
                fileh.write(l + "\n")
        finally:
            fileh.close()
        self.lineCache = []
        
    def _logLine(self, lvl, line, *args, **kw):
        # templating here etc
        now = time.gmtime()
        if (now[:self.dateTimeLevel]) > self.lastLogTime[:self.dateTimeLevel]:
            self._flush()
        # set last log time to correct level
        self.lastLogTime = now
        lvlstr = ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'][min(int(lvl/10), 5)]
        line = "[%s] %s: %s" % (time.strftime("%Y-%m-%d %H:%M:%S", now), lvlstr, line)
        self.lineCache.append(line)
        if (len(self.lineCache) >= self.cacheLen):
            self._flush()


class MultipleLogger(SimpleLogger):
    """Logger to write messages across multiple loggers."""
    
    _possiblePaths = {'loggerList' : {'docs' : "Space separated list of Logger identifiers to log to."}}
    
    def __init__(self, session, config, parent):
        Logger.__init__(self, session, config, parent)
        loggerList = self.get_path(session, 'loggerList')
        getObj = self.parent.get_object
        self.loggers = [getObj(session, id) for id in loggerList.split(' ')]

    def log_lvl(self, session, lvl, msg, *args, **kw):
        for lgr in self.loggers:
            lgr.log_lvl(session, lvl, msg, *args, **kw)
