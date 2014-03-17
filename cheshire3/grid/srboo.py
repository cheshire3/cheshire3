"""Object Oriented wrapper to Python SRB Interface.

Description: Object Oriented wrapper to Python SRB Interface
Author:      Rob Sanderson (azaroth@liv.ac.uk)
Date:        2005-05-12
Version:     0.8 
Copyright:   (c) University of Liverpool
Licence:     GPL

"""


import srb
import types
import socket
import atexit
from srbErrors import errmsgs


# TODO: Will fail at greater than MAX_GET_RESULT objects per collection

# Ensure polite disconnect behaviour
connections = []


def disconnect_all():
    for c in connections:
        try:
            c.disconnect()
        except:
            pass


class SrbException(Exception):

    def __init__(self, type, info=""):
        self.type = type
        self.message = errmsgs[type]
        self.info = info

    def __repr__(self):
        return "<<SrbException: (%s) %s>>" % (self.message, self.info)

    def __str__(self):
        return "<<SrbException: (%s) %s>>" % (self.message, self.info)


class SrbFile(object):

    conn = None
    fd = -1
    name = ""
    collection = ""
    # Maybe store index in collection?
    # For wrapper to get non-name metadata
    position = 0

    def __init__(self, conn, name):
        self.conn = conn
        self.name = name
        if not conn.collection:
            raise TypeError("Connection does not have a collection set.")
        else:
            self.collection = conn.collection

    def _connect(self, flag):
        fd = srb.obj_open(self.conn.id, self.collection, self.name, flag)        
        if (fd < 0):
            raise SrbException(fd, "Failed to open %s" % self.name)
        else:
            self.fd = fd

    def _create(self, size, resource, type, path):
        fd = srb.obj_create(self.conn.id, 0, self.name, type, resource,
                            self.collection, path, size)
        if fd < 0:
            raise SrbException(fd, "Failed to create %s" % self.name)
        else:
            self.fd = fd

    def fileno(self):
        return self.fd

    def isatty(self):
        return False

    def flush(self):
        # SRB auto flushes
        return None

    def tell(self):
        return self.position

    def read(self, size=-1):
        if self.fd < 0:
            raise TypeError('File is not open.')
        if size > -1:
            data = srb.obj_read(self.conn.id, self.fd, size)
            self.position += size
        else:
            data = ""
            while 1:
                buffer = srb.obj_read(self.conn.id, self.fd, 1024)
                self.position += 1024
                if buffer == "":
                    break
                data += buffer
        return data

    def close(self):
        if self.fd < 0:
            raise TypeError('File is not open.')
        resp = srb.obj_close(self.conn.id, self.fd)
        if resp < 0:
            raise SrbException(resp)
        else:
            self.fd = -1

    def write(self, value):
        if self.fd < 0:
            raise TypeError('File is not open.')
        #if type(value) == types.UnicodeType:
        #    try:
        #        value = value.encode('utf-8')
        #    except:
        #        raise TypeError("Cannot map unicode object to srb-writable "
        #                        "string.")
        #elif type(value) != types.StringType:
        #    raise TypeError("Can only write strings to SRB")

        resp = srb.obj_write(self.conn.id, self.fd, value, len(value))
        if resp < 0:
            raise SrbException(resp)
        else:
            return resp

    def seek(self, offset, whence=0):
        if self.fd < 0:
            raise TypeError('File is not open.')
        resp = srb.obj_seek(self.conn.id, self.fd, offset, whence)
        if resp < 0:
            raise SrbException(resp)
        else:
            self.position = whence + offset
        
    def delete(self, copynum=0):
        resp = srb.obj_delete(self.conn.id, self.name, copynum,
                              self.collection)
        if resp < 0:
            raise SrbException(resp)

    def get_umetadata(self):
        md = srb.get_user_metadata(self.conn.id, self.name, self.connection)
        if isinstance(md, types.IntType):
            if (md == -3005):
                md = {}
            else:
                raise SrbException(md)
        return md

    def set_umetadata(self, f, v):
        try:
            self.delete_umetadata(f)
        except:
            pass
        status = srb.set_user_metadata(self.conn.id, self.name,
                                       self.collection, f, v)
        if status < 0:
            raise SrbException(status)
        else:
            return status

    def delete_umetadata(self, f):
        md = self.get_umetadata()
        if (md.has_key(f)):
            status = srb.rm_user_metadata(self.conn.id, self.name,
                                          self.connection, f, md[f])
        else:
            status = 0
        if status < 0:
            raise SrbException(status)
        else:
            return status
       

class SrbConnection(object):
    id = -1
    collection = ""
    resource = ""

    host = ""
    port = ""
    domain = ""
    auth = ""
    user = ""
    passwd = ""
    dn = ""

    def __init__(self, host, port, domain,
                 auth="ENCRYPT1", user="", passwd="", dn=""):

        # Lookup host to ensure safe
        try:
            info = socket.gethostbyname(host)
            self.host = host
        except socket.gaierror, e:
            raise TypeError("Unknown host: %s" % host)

        if isinstance(port, types.IntType):
            self.port = str(port)
        elif isinstance(port, types.StringType):
            if port.isdigit():
                self.port = port
            else:
                raise TypeError("Port must be numeric")
        else:
            raise TypeError("Port must be integer or numeric string")

        self.domain = domain

        if auth == "PASSWD_AUTH":
            # deprecated
            self.auth = "ENCRYPT1"
        elif auth in ["ENCRYPT1", "GSI_AUTH"]:            
            self.auth = auth
        elif not auth and user and passwd:
            self.auth = "ENCRYPT1"
        elif not auth and dn:
            self.auth = "GSI_AUTH"
        else:
            print user, passwd
            raise TypeError("Unknown authentication type: %s" % auth)

        assert self.host
        assert self.port
        assert self.domain
        if self.auth == "ENCRYPT1":
            assert user
            assert passwd
        elif self.auth == "GSI_AUTH":
            assert dn

        sid = srb.connect(self.host, self.port, self.domain, self.auth,
                          user, passwd, dn)
        if sid < 0:
            raise SrbException(sid)
        else:
            self.id = sid
            connections.append(self)
            self.open_collection("/home/%s.%s" % (user, domain))

    def disconnect(self):
        srb.disconnect(self.id)

    def open(self, name, flag='w'):
        # Map from 'r', 'a', 'w' to unixFlag int
        # XXX How to open at end for 'a' ?
        if flag == 'r':
            iflag = 0
        else:
            iflag = 2
        f = SrbFile(self, name)
        f._connect(iflag)
        return f

    def create(self, name, size=-1, type="generic", resource="", path=""):
        f = SrbFile(self, name)
        if not resource and not self.resource:
            raise TypeError("Must either give resource or set on connection")
        elif not resource:
            resource = self.resource
        f._create(size, resource, type, path)
        return f

    def create_collection(self, name):
        # Create collection in current
        resp = srb.mk_collection(self.id, 0, self.collection, name)
        if resp < 0:
            raise SrbException(resp)

    def up_collection(self):
        new = self.collection[:self.collection.rindex('/')]
        self.open_collection(new)

    def open_collection(self, name):
        if (name[0] != '/'):
            name = self.collection + '/' + name
        self.collection = name
        self.n_objects()
        self.n_subcollections()

    def delete_collection(self, recursive=0):
        resp = srb.rm_collection(self.id, 0, recursive, self.collection)
        if resp < 0:
            raise SrbException(resp)
        else:
            self.up_collection()
        
    def n_subcollections(self):
        n = srb.get_subcolls(self.id, 0, self.collection)
        if n < 0:
            raise SrbException(n)
        else:
            self.subcolls = n
            return n

    def n_objects(self):
        # Order of objects by name
        n = srb.get_objs_in_coll(self.id, 0, 2, self.collection)
        if n < 0:
            raise SrbException(n)
        else:
            self.objects = n
            return n

    def object_metadata(self, idx, type='name'):
        # Will raise if not valid
        if not self.collection:
            raise TypeError("Must open a collection first")
        elif idx >= self.objects:
            raise IndexError("Object index out of range")
        t = ['name', 'collection', 'size', 'type', 'owner', 'timestamp',
             'replica', 'resource'].index(type)
        return srb.get_obj_metadata(self.id, t, idx)

    def collection_name(self, idx):
        if not self.collection:
            raise TypeError("Must open a collection first")
        elif idx >= self.subcolls:
            raise IndexError("Subcollection index out of range")
        return srb.get_subcoll_name(self.id, idx)
        
    def walk_names(self):
        # Return tuple of colls, files
        self.n_subcollections()
        self.n_objects()
        colls = []
        files = []
        for s in range(self.subcolls):
            colls.append(self.collection_name(s))
        for f in range(self.objects):
            files.append(self.object_metadata(f))
        return (colls, files)

    def walk(self):
        # Following os.walk
        # (Leaves you in lowest leaf)
        (colls, files) = self.walk_names()
        yield self.collection, colls, files
        for name in colls:
            self.open_collection(name)
            for x in self.walk():
                yield x

    def rmrf(self):
        for path, dirs, files in self.walk():
            for file in files:
                f = self.open(file)
                f.close()
                f.delete()


atexit.register(disconnect_all)