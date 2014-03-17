"""iRODS Utilities for Cheshire3."""

from urlparse import urlsplit
from collections import namedtuple

try:
    import irods
except ImportError:
    irods = None

from cheshire3.exceptions import MissingDependencyException


def icatValToPy(val, un):
    if un in ['int', 'long']:
        return long(val)
    elif un == 'unicode':
        return val.decode('utf-8')
    elif un == 'float':
        return float(val)
    else:
        return val


def pyValToIcat(val):
    x = type(val)
    if x in [int, long]:
        return ("%020d" % val, 'long')
    elif x == unicode:
        return (val.encode('utf-8'), 'unicode')
    elif x == float:
        return ('%020f' % val, 'float')
    else:
        return (val, 'str')


def parse_irodsUrl(url):
    """Parse and iRODS URL, return a named tuple.

    Return value will have attributes:

    rodsHost
        Name of the iRODS host

    rodsPort
        Number of the port on which iRODS is served

    rodsZone
        Name of iRODS Zone

    path
        Absolute path of the file/collection

    rodsUserName
        iRODS username

    rodsHome
        iRODS home collection of given rodsUserName

    relpath
        Path relative to rodsHome

    """
    if irods is None:
        raise MissingDependencyException("parse_irodsUrl()", 'irods (PyRods)')
    IrodsUrl = namedtuple("IrodsUrl",
                          ["rodsHost",
                           "rodsPort",
                           "rodsZone",
                           "path",
                           "rodsUserName",
                           "rodsHome",
                           "relpath"],
                          verbose=False
                          )
    parsed = urlsplit(url)
    pathParts = parsed.path.split('/')
    return IrodsUrl(parsed.hostname,
                    parsed.port,
                    pathParts[0],             # Zone
                    parsed.path,              # Absolute path
                    parsed.username,
                    '/'.join(pathParts[:4]),  # Home
                    '/'.join(pathParts[4:])   # Path relative to home
                    )


def open_irodsUrl(url, mode='r'):
    """Open and return the file specified by an iRODS URL.

    Returns a file-like object - ``irods.IrodsFile``
    """
    if irods is None:
        raise MissingDependencyException("open_irodsUrl()", 'irods (PyRods)')
    parsed = parse_irodsUrl(url)
    conn, errMsg = irods.rcConnect(parsed.rodsHost,
                                   parsed.rodsPort,
                                   parsed.rodsUserName,
                                   parsed.rodsZone
                                   )
    status = irods.clientLogin(conn)
    return irods.irodsOpen(conn, parsed.path, mode)
