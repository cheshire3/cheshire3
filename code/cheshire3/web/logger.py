
import time
from cheshire3.logger import SimpleLogger

class SingleTransactionLogger(object):
    u"""A mini logging object to handle logs for a single transaction. Not API!"""
    
    def __init__(self, remoteHost):
        self.startTime = time.time()
        self.lastLogTime = time.time()
        self.logLines = [remoteHost]
        
    def log(self, msg):
        now = time.time()
        diff = now - self.lastLogTime
        try:
            self.logLines.append('[+{0:.3f} s] {1}'.format(diff, msg))
        except AttributeError:
            raise ValueError("log method called on closed {0}".format(self.__class__.__name__))
        self.lastLogTime = now
        
    def flush(self, sepChar):
        now = time.time()
        total = now - self.startTime
        self.logLines.append('Total time: {0:.3f} secs'.format(total))
        msg = sepChar.join(self.logLines)
        return msg
    
    def close(self):
        del self.logLines
        

class TransactionLogger(SimpleLogger):
    
    _possibleSettings = {'separatorString': {'docs': 'String to use to delimit individual log lines which are part of the same transaction.', 'type': str}}

    def __init__(self, session, config, parent):
        SimpleLogger.__init__(self, session, config, parent)
        self.sepString = self.get_setting(session, 'separatorString', '\n')
        self.transactionLoggers = {}
        
    def _logPart(self, msg, remoteHost):
        try:
            self.transactionLoggers[remoteHost].log(msg)
        except KeyError:
            stl = SingleTransactionLogger(remoteHost)
            stl.log(msg)
            self.transactionLoggers[remoteHost] = stl 
       
    def log(self, session, msg, remoteHost):
        self.log_lvl(session, self.defaultLevel, msg, remoteHost)

    def log_lvl(self, session, lvl, msg, remoteHost, *args, **kw):
        if not lvl:
            lvl = self.defaultLevel
        if lvl >= self.minLevel:
            self._logPart(msg, remoteHost)
            
    def flush(self, session, lvl, remoteHost):
        try:
            msg = self.transactionLoggers[remoteHost].flush(self.sepString)
        except KeyError:
            raise ValueError("flush method called for unrecognized host {0}".format(remoteHost))
        else:
            self.transactionLoggers[remoteHost].close()
            del self.transactionLoggers[remoteHost]
            self._logLine(lvl, msg)

    #- end class TransactionLogger ---------------------------------------------------
    