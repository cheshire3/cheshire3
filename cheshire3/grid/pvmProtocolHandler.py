
import sys
import time

from cheshire3.baseObjects import Session

try:
    import pypvm
except ImportError:
    # Don't need it to import, just to use (???)
    pass


def shutdown():
    # Handle any other pypvm cleanup
    pypvm.exit()


class Message:
    source = None
    manager = None
    data = None

    def __init__(self, data, source, manager):
        self.data = data
        self.manager = manager
        self.source = source
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
    slave = ""
    ntasks = 0

    def __init__(self, slaveFile, ntasks):
        self.tid = pypvm.mytid()
        self.slaveFile = slaveFile
        self.ntasks = ntasks
        self.tasks = {}
        self.idle = []
        self.hosts = []
        self.splitTasksEvenly = 1
        # pypvm.catchout(sys.stdout)

    def addHosts(self, hostnames):
        if (not isinstance(hostnames, list)):
            hostnames = [hostnames]
        resp = pypvm.addhosts(hostnames)
        self.hosts.extend(hostnames)
        #for s in range(len(resp)):
        #    if not resp[s]:
        #        self.hosts.append(hostnames[s])

    def start(self):
        if self.hosts and self.splitTasksEvenly:
            tph = self.ntasks / len(self.hosts)
            rem = self.ntasks - (tph * len(self.hosts))
            tids = []
            for h in self.hosts:
                htids = pypvm.spawn(self.slaveFile, [], pypvm.PvmTaskHost,
                                    h, tph)
                tids.extend(htids)
            if rem:
                rtids = pypvm.spawn(self.slaveFile, [], pypvm.PymTaskDefault,
                                    "", rem)
                tids.extend(rtids)
        else:
            tids = pypvm.spawn(self.slaveFile, [], pypvm.PvmTaskDefault, "",
                               self.ntasks)
        for n in range(len(tids)):
            name = 'Task%s' % n
            self.tasks[tids[n]] = Task(tids[n], name)
            self.idle.append(tids[n])

    def setname(self):
        # Spam out requests
        v = self.tasks.values()
        for t in v:
            t.setname()
        # and pull back the acks
        for t in v:
            self.recv()

    def waitall(self):
        start = time.time()
        d = []
        while len(self.tasks.keys()) != len(self.idle):
            d2 = self.maybeRecv()
            if (d2):
                d.extend(d2)
            time.sleep(0.1)
            if (time.time() - start > 600):
                raise ValueError('Deadlocked tasks')
        return d

    def request_task(self):
        # get a task and take it out of commision
        if not self.idle:
            return 0
        else:
            t = self.idle.pop(0)
            return self.tasks[t]

    def relinquish_task(self, t):
        self.idle.append(t.tid)

    def call(self, what, fn, *args, **kw):
        # call to one idle task
        if not self.idle:
            #Everyone's busy
            return 0
        else:
            t = self.idle.pop(0)
            self.tasks[t].call(what, fn, *args, **kw)
            return 1

    def kill(self):
        # Kill all tasks
        for t in self.tasks:
            self.tasks[t].kill()

    def send(self, data):
        # send message to one idle task
        if not self.idle:
            return 0
        else:
            t = self.idle.pop(0)
            self.tasks[t].send(data)
            return 1

    def maybeRecv(self):
        d = []
        while (pypvm.probe() > 0):
            try:
                m = self.recv()
            except Exception, e:
                m = e
            d.append(m)
        return d

    def recv(self):
        # Get response data from any task, put back into idle.
        bufid = pypvm.recv()
        (bytes, msgtag, src) = pypvm.bufinfo(bufid)
        if src not in self.tasks:
            self.tasks[src] = Task(src)
        source = self.tasks[src]
        if (not src in self.idle):
            self.idle.append(src)
        data = pypvm.upk()
        return Message(data, source, self)


class Task:
    tid = -1

    def __init__(self, tid=-1, name="", debug=0):
        if (tid > -1):
            self.tid = tid
        else:
            self.tid = pypvm.mytid()
        if name:
            self.name = name
        else:
            self.name = "Task%s" % self.tid
        self.debug = debug
        if debug:
            self.fileh = file("fuxored_%s" % self.name, 'w')

    def setname(self, name=None):
        if (name):
            self.name = name
        else:
            name = self.name
        self.call(self, 'name', name)

    def call(self, what, fn, *args, **kw):
        if (args and isinstance(args[0], Session)):
            args[0].task = self.name
        if (what == 'self' or what == self):
            message = ['self', fn, args, kw]
        else:
            message = [what.id, fn, args, kw]
        self.send(message)

    def send(self, data):
        if (self.debug):
            self.fileh.write("%r " % data)
            self.fileh.flush()
        pypvm.initsend(pypvm.PvmDataDefault)
        pypvm.pk(data)
        pypvm.send(self.tid, 1)

    def kill(self):
        pypvm.kill(self.tid)

    def recv(self):
        # Read data from this specific task
        bufid = pypvm.recv(self.tid)
        (bytes, msgtag, src) = pypvm.bufinfo(bufid)
        data = pypvm.upk()
        if self.debug:
            self.fileh.write("--> %r\n" % data)
            self.fileh.flush()
        return Message(data, src, None)
