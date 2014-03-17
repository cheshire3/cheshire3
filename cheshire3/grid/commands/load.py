"""Load iRODS data into a Cheshire3 database."""

import os
import sys

from urlparse import urlsplit, SplitResult, urlunsplit

try:
    import irods
except ImportError:
    irods = None

from cheshire3.exceptions import (
    ObjectDoesNotExistException,
    MissingDependencyException
)
from cheshire3.server import SimpleServer
from cheshire3.session import Session

from cheshire3.commands.load import argparser
from cheshire3.commands.cmd_utils import identify_database


def main(argv=None):
    """Load data into a Cheshire3 database based on parameters in argv."""
    global argparser, session, server, db
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    if irods is None:
        raise MissingDependencyException('icheshire3-load script',
                                         'irods (PyRods)'
                                         )
    session = Session()
    server = SimpleServer(session, args.serverconfig)
    if args.database is None:
        try:
            dbid = identify_database(session, os.getcwd())
        except EnvironmentError as e:
            server.log_critical(session, e.message)
            return 1
        server.log_debug(
            session,
            "database identifier not specified, discovered: {0}".format(dbid))
    else:
        dbid = args.database

    try:
        db = server.get_object(session, dbid)
    except ObjectDoesNotExistException:
        msg = """Cheshire3 database {0} does not exist.
Please provide a different database identifier using the --database option.
""".format(dbid)
        server.log_critical(session, msg)
        return 2
    else:
        # Allow for multiple data arguments
        docFac = db.get_object(session, 'defaultDocumentFactory')
        for dataArg in args.data:
            if dataArg.startswith('irods://'):
                parsed = urlsplit(dataArg)
            else:
                # Examine current environment
                status, myEnv = irods.getRodsEnv()
                try:
                    host = myEnv.getRodsHost()
                except AttributeError:
                    host = myEnv.rodsHost
                # Port
                try:
                    myEnv.getRodsPort()
                except AttributeError:
                    port = myEnv.rodsPort
                # User
                try:
                    username = myEnv.getRodsUserName()
                except AttributeError:
                    username = myEnv.rodsUserName
                netloc = '{0}@{1}:{2}'.format(username, host, port)
                try:
                    cqm = myEnv.getRodsCwd()
                except AttributeError:
                    cwd = myEnv.rodsCwd
                path = '/'.join([cwd, dataArg])
                parsed = SplitResult('irods', netloc, path, None, None)
                dataArg = urlunsplit(parsed)
            server.log_debug(session, dataArg)
            if args.format is None or not args.format.startswith('i'):
                fmt = 'irods'
            else:
                fmt = args.format
            server.log_debug(session, fmt)
            try:
                docFac.load(session, dataArg,
                            args.cache, fmt, args.tagname, args.codec)
            except MissingDependencyException as e:
                server.log_critical(session, e.reason)
                missingDependencies =  e.dependencies
                raise MissingDependencyException('cheshire3-load script',
                                                 missingDependencies)
            wf = db.get_object(session, 'buildIndexWorkflow')
            wf.process(session, docFac)


argparser.add_argument('-f', '--format', type=str,
                       action='store', dest='format',
                       default=None, metavar='FORMAT',
                       help=("format of the data parameter. This should "
                             "almost certainly be one of ifile or idir. For "
                             "details, see:"
                             "http://docs.cheshire3.org/en/latest/"
                             "tutorial/python.html#loading-data")
                       )

session = None
server = None
db = None

if __name__ == '__main__':
    sys.exit(main())
