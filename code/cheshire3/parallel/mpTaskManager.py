
import sys
import time
import traceback

import multiprocessing as mp

from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Session


# Remote Process
class RemoteTask(mp.Process):

    def __init__(self, session, name=None, manager=None, debug=0):

        # This sets self.name
        mp.Process.__init__(self, name=name)
        self.inPipe = None
        self.debug = debug
        self.manager = manager
        
        # Reconstruct our own session, so as to not overwrite task
        self.session = Session(user=session.user, logger=session.logger, 
                               task=self.name, database=session.database, 
                               environment=session.environment)
        self.session.server = session.server        
        self.server = session.server
        self.database = self.server.get_object(self.session, session.database)
        
    try:
        name = property(mp.Process.get_name, mp.Process.set_name)
    except AttributeError:
        pass
        
    def log(self, inout, data):
        try:
            lgr = self.session.logger
        except AttributeError:
            pass
        if self.debug and lgr:
            if inout == 'in':    
                logtmpl = "[{0!s}:0-->]: {1!r}\n"
            else:
                logtmpl = "[{0!s}:-->0]: {1!r}\n" 
            lgr.log(self.session, logtmpl.format(self.name, data))    
        
    def run(self):          
        # Listen to pipe and evaluate
        while True:
            # The recv will block, so no need to sleep()
            try:
                msg = self.inPipe.recv()
            except:
                continue
            self.log('in', msg)  
            try:
                if msg == "SHUTDOWN":
                    self.inPipe.send(-1)
                    break
                elif msg == "PING":
                    self.inPipe.send(-100)
                    continue
                try:
                    (objid, fn, args, kw) = msg
                    args = list(args)
                    target = self.database.get_object(self.session, objid)    
                    if (hasattr(target, fn)):
                        code = getattr(target, fn)
                        val = code(self.session, *args, **kw)
                    else:
                        val = (target, objid, fn)
                    if isinstance(val, Record):
                        val = "%s/%s" % (val.recordStore, val.id)

                except Exception, e:
                    val = traceback.format_tb(sys.exc_info()[2])

                try:
                    self.inPipe.send(val)
                    self.log('out', val)
                except Exception, e:
                    # We have an exception object
                    val2 = traceback.format_tb(sys.exc_info()[2])
                    self.inPipe.send(val2)
                except:
                    # Something was raised, but it ain't an exception
                    val = traceback.format_tb(sys.exc_info()[2])
                    self.inPipe.send(val)
            except Exception, e:
                # Something seriously wrong, need to reply SOMETHING
                val = traceback.format_tb(sys.exc_info()[2])
                self.inPipe.send(val)

# Handle communication to remote process
class Task(object):
    
    name = ""
    session = None
    debug = 0
    process = None
    outPipe = None
    
    def __init__(self, session, name, manager=None, debug=0):
        self.name = name
        self.session = session
        self.debug = debug
        self.manager= manager
        
        self.process = RemoteTask(session=session, name=name, manager=manager, debug=debug)
        par, chld = mp.Pipe(duplex=True)
        self.process.inPipe = chld
        self.outPipe = par
        self.process.start()        

    def log(self, inout, data):
        if self.debug and self.session.logger:
            if inout == 'out':
                self.session.logger.log(self.session, '[0:-->%s]: %r\n' % (self.name, data))
            else:
                self.session.logger.log(self.session, '[0:%s-->]: %r\n' % (self.name, data))
        
    def send(self, data):
        self.outPipe.send(data)
        self.log('out', data)
    
    def recv(self):
        data = self.outPipe.recv()
        self.log('in', data)
        return data
        
    def poll(self):
        return self.outPipe.poll()

    def call(self, o, fn, *args, **kw):
        self.send([o.id, fn, args, kw])



class ProcessTaskManager(C3Object):    
    nTasks = 0
    session = None
    debug = 0
    
    tasks = {}
    claimed_tasks = {}
    idle_tasks = []

    _possibleSettings = {'nTasks': {'docs': "Number of tasks to create and distribute work between.", 'type': int},
                         'maxChunkSize': {'docs': "Maximum chunk size when splitting iterative tasks.", 'type': int},
                         'chunkBy': {'docs': "Criteria to chunk by (e.g. byteCount, wordCount, or number of times to use each task.)"},
                         'maxChunkByteCount': {'docs': "Maximum number of bytes that each chunk should represent.", 'type': int},
                         'maxChunkWordCount': {'docs': "Maximum number of words that each chunk should represent.", 'type': int}
                         }

    def __init__(self, session, config, parent):
        C3Object.__init__(self, session, config, parent)

        self.session = session
        self.debug = 0
        self.nTasks = self.get_setting(session, 'nTasks')
        if not self.nTasks:
            self.nTasks = mp.cpu_count() 
                
        self.tasks = {}
        self.claimed_tasks = {}
        self.idle_tasks = []
        
        for t in range(1, self.nTasks+1):    
            wt = Task(session, name=t, manager=self, debug=self.debug)
            self.tasks[t] = wt
            self.idle_tasks.append(wt)

    # Send and Receive functions 

    def recv(self, task):
        data = task.recv()
        self.idle_tasks.append(task)
        return data  

    def recv_any(self):
        while True:
            time.sleep(0.1)
            for task in self.tasks.values():
                if not task.name in self.idle_tasks and task.poll():
                    data = self.recv(task)
                    return (task, data)

    def recv_all(self):
        info = {}
        while len(self.idle_tasks) != len(self.tasks):
            data = self.recv_any()
            info[data[0]] = data[1]
        return info
        
    def send(self, task, data):
        try:
            self.idle_tasks.remove(task)
        except:
            pass
        task.send(data)

    def send_all(self, data):
        # This should probably respect idle_tasks?
        # But what about shutdown?
        for t in self.tasks.values():            
            self.send(t, data)           

    def send_any(self, data):
        if not self.idle_tasks:
            self.recv_any()
        task = self.idle_tasks.pop(0)
        self.send(task, data)
        

    # End User API
    
    def shutdown(self, session):
        self.send_all('SHUTDOWN')
        return self.recv_all()

    def ping(self, session):
        self.send_all('PING')
        return self.recv_all()
        
    def call_all(self, session, o, fn, *args, **kw):
        val = [o.id, fn, args, kw]
        self.send_all(val)            
            
    def call_all_wait(self, session, o, fn, *args, **kw):
        self.call_all(o, fn, *args, **kw)
        return self.recv_all()
         
    def call(self, session, o, fn, *args, **kw):
        self.send_any([o.id, fn, args, kw])
                
    def claim(self, session):
        # give up an idle task and let user handle it
        if not self.idle_tasks:
            self.recv_any()
        task = self.idle_tasks.pop(0)
        del self.tasks[task.name]
        self.claimed_tasks[task.name] = task
        return task
        
    def relinquish(self, session, task):
        del self.claimed_tasks[task.name]
        self.tasks[task.name] = task
        self.idle_tasks.append(task)





    
    
    
    