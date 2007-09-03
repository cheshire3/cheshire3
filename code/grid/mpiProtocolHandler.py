
import sys, time, commands, os
import traceback
from baseObjects import Session, Record

try:
    import mpi
except ImportError:
    # Don't need it to import, just to use (???)
    pass


class Message:
    source = None
    manager = None
    data = None

    def __repr__(self):
        return '<<Message data="%r">>' % self.data

    def __init__(self, data, source, manager):
        self.data = data
        self.manager = manager  # TaskManager
        self.source = source    # Task
        if (isinstance(data, list) and isinstance(data[0], Exception) and len(data) == 2):
            data[0].tb = data[1]
            raise data[0]
        
    def reply(self, data):
        self.source.send(data)

class TaskManager:
    tid = -1
    tasks = {}
    idle = []
    ntasks = 0
    status = None
    debug = 0
    messagesSent = {}
    currentReceive = None
    server = None

    def __init__(self, session):
	self.currentReceive = None
        self.ntasks = mpi.WORLD.size
        self.tid = mpi.rank
        self.session = session
        self.server = session.server

	if self.debug:
	    self.hostname = commands.getoutput('hostname')
	    self.logh = file('debug_%s_%s' % (self.tid, self.hostname), 'w')

        if self.ntasks > 1:
            for t in range(self.ntasks):
                task = Task(t, manager=self)
                self.tasks[t] = task
	        self.messagesSent[t] = 0
                self.idle.append(task)
            if self.tid == 0:
                # Strip self
                del self.tasks[0]
                self.idle.pop(0)


    def shutdown(self):
        for t in self.tasks.values():
            t.send("SHUTDOWN")

    def log(self, type, msg, to=None):
	if self.debug:
	    if type== "recv":
                self.logh.write("[%s] %s @ %s got %r from %s\n" % (time.time(), self.tid, self.hostname, msg, msg.source))
	    else:
	        self.logh.write("[%s] %s @ %s sending %s to %s\n" % (time.time(), self.tid, self.hostname, msg, to))
	    self.logh.flush()

    def start(self):
        if self.ntasks == 1:
            raise ValueError("Not running in parallel.")

        if self.tid != 0:
            # Start listening
            cont = 1
            asynchronous = 0
            master = self.tasks[0]
            while (cont):
                msg = None
                if asynchronous:
                    # Listen for reqs from anywhere
                    # round robin through tasks
                    msg = self.recv()
                else:
                    # Listen for reqs from master
                    msg = master.recv()

		self.log("recv", msg)  
                try:
                    val = -1
                    if msg.data == "SHUTDOWN":
                        cont = 0
                        break
                    elif msg.data == "PING":
                        msg.reply(-100)
                        continue
                    elif msg.data == "ASYNC":
                        asynchronous = 1
                        msg.reply(None)
                        continue

                    try:
                        (objid, fn, args, kw) = msg.data
                        if isinstance(args[0], Session):
                            db = self.server.get_object(self.session, args[0].database)
                            session = args[0]
                        else:
                            session = self.session
                        target = self.server.get_object(session, objid)

                        if (not target):
                            target = db.get_object(session, objid)
                        if (hasattr(target, fn)):
                            code = getattr(target, fn)
                            val = code(*args, **kw)
                        else:
                            val = (target, objid, fn)
                        if isinstance(val, Record) and val.recordStore and val.id:
                            val = "%s/%s" % (val.recordStore, val.id)
                        
                    except Exception, e:
                        val = [e, traceback.format_tb(sys.exc_info()[2])]

                    try:
                        msg.reply(val)
                    except Exception, e:
                        # We have an exception object
                        val = [e, traceback.format_tb(sys.exc_info()[2])]
                        msg.reply(val)
                    except:
                        # Something was raised, but it ain't an exception
                        val = traceback.format_tb(sys.exc_info()[2])
                        msg.reply(val)
                except Exception, e:
                    # Something seriously wrong, need to reply SOMETHING
                    val = [e, traceback.format_tb(sys.exc_info()[2])]
                    msg.reply(val)
	        except:
		    msg.reply('-2')

    def recv(self):

        # blocking receive from anywhere
        (data, status) = mpi.recv()
        src = self.tasks[status.source]
        # Put back into idle list
        if not src in self.idle:
            self.idle.append(src)
        msg = Message(data, src, self)
        msg.status = status
        return msg

    # Wait for irecv
    # msg = None
    # while not msg:
    #    msg = self.irecv()
    #    time.sleep(0.01)
    # return msg

    def arecv(self):
	if self.currentReceive == None:
	    return 1
	else:
	    while not self.currentReceive:
		time.sleep(0.1)
            sourcet = self.currentReceive.status.source
            t = self.tasks[sourcet]
            data = self.currentReceive.message
            self.currentReceive = None
            msg = Message(data, t, self)
            self.idle.append(t)
            self.log("recv", msg)
            return msg

    def irecv(self):
        # Receive a message from anywhere, create Message 
        # round robin irecvs

        if self.currentReceive == None:
            self.currentReceive = mpi.irecv()
        if self.currentReceive:
            # Find source task
            sourcet = self.currentReceive.status.source
            t = self.tasks[sourcet]
            data = self.currentReceive.message
            self.currentReceive = None
            msg = Message(data, t, self)
            self.idle.append(t)
            self.log("recv", msg)
            return msg
        else:
            return None

	#start = self.rrIdx
        #idxs = range(start, len(self.tasks)) + range(min(start, len(self.tasks)))
        #for x in idxs:
        #    m = tasks[x].irecv()
        #    if m:
        #        self.rrIdx = x+1
        #        if not m.source in self.idle:
        #            self.idle.append(m.source)
        #        return m
        #return None

    def send(self, data):
        # Forward to task to send to
        if not self.idle:
            return 0
        else:
            task = self.idle.pop(0)
            task.send(data)
            return 1

    def call(self, o, fn, *args, **kw):
        # Forward to task to send to
        if not self.idle:
            return 0
        else:
            task = self.idle.pop(0)
            task.call(o, fn, *args, **kw)
            return 1

    # Remove tasks from pool
    def request_task(self):
        if not self.idle:
            return 0
        else:
            t = self.idle.pop(0)
            del self.tasks[t.tid]
            return t

    def relinquish_task(self, task):
        self.idle.append(task)
	self.tasks[task.tid] = task
        return 1

    def bcall(self, o, fn, *args, **kw):
        # Broadcast message to non removed tasks
	tasks = self.tasks.values()
        for t in tasks:
            t.call(o, fn, *args, **kw)
	self.idle = []
	return len(tasks)
        
    def waitall(self):
        start = time.time()
        waiting = self.tasks.copy()
	for t in self.idle:
	    del waiting[t.tid]	
        msgs = []
        while waiting:
            for t in waiting.values():
                msg = t.irecv()
                if msg != 0:
                    msgs.append(msg)
                    del waiting[t.tid]
	            self.idle.append(t)
            if time.time() > start + 600:
                raise ValueError("Tasks in deadlock")
            time.sleep(0.5)
        return msgs
            
class Task:
    tid = -1
    currentSend = None
    currentReceive = None

    def __init__(self, tid=-1, name="", debug=0, manager=None):
	self.debug = 0
        self.currentSend = None
        self.currentReceive = None
	self.manager=manager
        if tid > -1:
            self.tid = tid
        else:
            self.tid = mpi.rank
        if name:
            self.name = name
        else:
            self.name = "Task%s" % self.tid

    def __repr__(self):
        return "MpiTask%s" % self.tid

    def async(self):
        self.send("ASYNC", 1)
        # don't want to ever try calling it until it has gone async
        return self.recv()

    def call(self, what, fn, *args, **kw):
        if (args and isinstance(args[0], Session)):
            args[0].task = self.name
        if (what == 'self' or what == self):
            message = ['self', fn, args, kw]
        else:
            message = [what.id, fn, args, kw]
        self.send(message, 1)

    def log(self, type, msg, to=None):
	if self.manager:
	    self.manager.log(type, msg, to)
	elif self.debug:
	    # Task object created outside normal scope
	    fileh = file("debug_%s" % self.tid, 'a')
	    fileh.write("%r %r %r\n" % (type, msg, to))
	    fileh.flush()
	    fileh.close()

    def send(self, data, listen=0):
	if self.manager:
            self.manager.messagesSent[self.tid] += 1
	#self.log("send", data, self.tid)
        mpi.send(data, self.tid)

    def recv(self):
        # Read data from this specific task
        (data, status) = mpi.recv(self.tid)
        return Message(data, self, self.manager)
     
    def irecv(self):
        # Read data from this specific task, nonblocking
        if self.currentReceive == None:
            self.currentReceive = mpi.irecv(self.tid)
        if mpi.testany(self.currentReceive)[0] != None:
            msg = self.currentReceive.message
            self.currentReceive = None
            msg = Message(msg, self, self.manager)
	    self.log("recv", msg)
	    return msg
        else:
            return 0




