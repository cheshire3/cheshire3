from __future__ import absolute_import


import sys
import os
import time
import commands
import traceback
try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import mpi
except ImportError:
    # Don't need it to import, just to use (???)
    pass

from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.baseObjects import Session, Record


class Message:
    source = None
    manager = None
    data = None

    def __repr__(self):
        return '<<Message data="%r">>' % self.data

    def __init__(self, data, source, manager, status):
        self.data = data
        self.manager = manager  # TaskManager
        self.source = source    # Task
        self.status = status
        if (
            isinstance(data, list) and
            isinstance(data[0], Exception) and
            len(data) == 2
        ):
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
    namedTasks = {}

    def __init__(self, session):
        self.currentReceive = None
        self.ntasks = mpi.WORLD.size
        self.tid = mpi.rank
        self.session = session
        self.server = session.server
        self.namedTasks = {}

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
            if type == "recv":
                self.logh.write("[%s] %s @ %s got %r from %s\n"
                                "" % (time.time(), self.tid, self.hostname,
                                      msg, msg.source))
            else:
                self.logh.write("[%s] %s @ %s sending %s to %s\n"
                                "" % (time.time(), self.tid, self.hostname,
                                      msg, to))
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
                    elif type(msg.data) == list and msg.data[0] == "NAMETASK":
                        (rtid, name) = msg.data[1:]
                        self.namedTasks[name] = self.tasks[rtid]
                        msg.reply(None)
                        continue

                    try:
                        (objid, fn, args, kw) = msg.data
                        if isinstance(args[0], Session):
                            db = self.server.get_object(self.session,
                                                        args[0].database)
                            session = args[0]
                        else:
                            session = self.session
                        session.server = self.server
                        session.processManager = self

                        try:
                            target = self.server.get_object(session, objid)
                        except ObjectDoesNotExistException:
                            target = db.get_object(session, objid)

                        if (hasattr(target, fn)):
                            code = getattr(target, fn)
                            val = code(*args, **kw)
                        else:
                            val = (target, objid, fn)
                        if isinstance(val, Record):
                            val = "%s/%s" % (val.recordStore, val.id)

                    except Exception, e:
                        val = [e, traceback.format_tb(sys.exc_info()[2])]

                    try:
                        msg.reply(val)
                    except Exception, e:
                        # We have an exception object
                        val2 = [e, traceback.format_tb(sys.exc_info()[2])]
                        msg.reply(val2)
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
        msg = Message(data, src, self, status)
        self.log("recv", msg)
        return msg

    def irecv(self):
        # Receive a message from anywhere, create Message
        # round robin irecvs

        if self.currentReceive is None:
            self.currentReceive = mpi.irecv()
        if self.currentReceive:
            # Find source task
            sourcet = self.currentReceive.status.source
            t = self.tasks[sourcet]
            data = self.currentReceive.message
            msg = Message(data, t, self, self.currentReceive.status)
            self.log("recv", msg)
            self.currentReceive = None
            self.idle.append(t)
            return msg
        else:
            return None

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

    # Put task back in pool
    def relinquish_task(self, task):
        self.idle.append(task)
        self.tasks[task.tid] = task
        return 1

    def name_task(self, task, name):
        self.namedTasks[name] = task
        task.name = name
        for t in self.tasks.values():
            t.send(["NAMETASK", task.tid, name])

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
            #if time.time() > start + 600:
            # raise ValueError("Tasks in deadlock")
            time.sleep(0.5)
        return msgs

    def callOnEach(self, stack, function, *args, **kw):
        # Fill tasks
        tasks = self.tasks.values()
        for t in tasks:
            try:
                what = stack.pop()
            except IndexError:
                break
            if args:
                t.call(what, function, *args, **kw)
            else:
                t.call(what, function, *args, **kw)
        self.idle = []

        while stack:
            try:
                okay = self.recv()
            except Exception, e:
                print e
                if (hasattr(e, 'tb')):
                    for l in e.tb:
                        print l[:-1]
                raise
            what = stack.pop()
            self.call(what, function, *args, **kw)
        self.waitall()

    def callForEach(self, stack, object, function, *args, **kw):
        # Put first *arg first (== session)
        tasks = self.tasks.values()
        for t in tasks:
            try:
                what = stack.pop()
            except IndexError:
                break
            if args:
                t.call(object, function, args[0], what, *args[1:], **kw)
            else:
                t.call(object, function, what, **kw)
        self.idle = []
        while stack:
            try:
                okay = self.recv()
            except Exception, e:
                print e
                if (hasattr(e, 'tb')):
                    for l in e.tb:
                        print l[:-1]
                raise
            what = stack.pop()
            if args:
                self.call(object, function, args[0], what, *args[1:], **kw)
            else:
                self.call(object, function, what, **kw)
        self.waitall()


class Task:
    tid = -1
    name = ""
    currentSend = None
    currentReceive = None

    def __init__(self, tid=-1, name="", debug=0, manager=None):
        self.debug = 0
        self.currentSend = None
        self.currentReceive = None
        self.manager = manager
        self.name = ""
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
            session = args[0]
            session.task = self.name
            svr = session.server
            session.server = None
            session.processManager = None
        else:
            session = None
        if (what == 'self' or what == self):
            message = ['self', fn, args, kw]
        else:
            message = [what.id, fn, args, kw]
        self.send(message, 1)
        if session:
            session.server = svr

    def log(self, type, msg, to=None):
        if self.manager:
            self.manager.log(type, msg, to)
        elif self.debug:
            # Task object created outside normal scope
            fileh = file("debug_%s" % self.tid, 'a')
            fileh.write("type:%r msg:%r to:%r\n" % (type, msg, to))
            fileh.flush()
            fileh.close()

    def send(self, data, listen=0):
        if self.manager:
            self.manager.messagesSent[self.tid] += 1
        self.log("send", data, self.tid)
        try:
            mpi.send(data, self.tid)
        except:
            if (
                type(data) == list and
                isinstance(data[0], pickle.UnpickleableError)
            ):
                data[0] = ValueError("Unpickleable!")
                try:
                    mpi.send(data, self.tid)
                except:
                    print "Fail in send:"
                    print data
                    raise
            else:
                print "Fail in send:"
                print data
                raise

    def recv(self):
        # Read data from this specific task
        (data, status) = mpi.recv(self.tid)
        return Message(data, self, self.manager, status)

    def irecv(self):
        # Read data from this specific task, nonblocking
        if self.currentReceive is None:
            self.currentReceive = mpi.irecv(self.tid)
        if mpi.testany(self.currentReceive)[0] is not None:
            msg = self.currentReceive.message
            msg = Message(msg, self, self.manager, self.currentReceive.status)
            self.currentReceive = None
            self.log("recv", msg)
            return msg
        else:
            return 0
