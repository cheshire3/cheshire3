"""Initialize a Cheshire 3 database."""

from __future__ import absolute_import

import sys
import os

# Manipulate sys.path to eliminate possibility of local imports
# i.e. local import of cheshire3.py will block import of cheshire3 package
sys.path.pop(0)

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def main(argv=None):
    global argparser, session, server, db
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    session = Session()
    server = SimpleServer(session, args.serverconfig)
    if args.database is None:
        # Find local database name to use as basis of database id
        dbid = "db_{0}".format(os.path.basename(args.directory))
        server.log_debug(session, "database identifier not specified, defaulting to: {0}".format(dbid))
        try:
            db = server.get_object(session, dbid)
        except ObjectDoesNotExistException:
            # Doesn't exists, so OK to init it
            pass
        else:
            msg = """database with id '{0}' has already been init'd. \
Please specify an id using the --database option.""".format(dbid)
            server.log_critical(session, msg)
            raise ValueError(msg)
    else:
        dbid = args.database
        try:
            db = server.get_object(session, dbid)
        except ObjectDoesNotExistException:
            # Doesn't exists, so OK to init it
            pass
        else:
            msg = """database with id '{0}' has already been init'd. \
Please specify a different id.""".format(dbid)
            server.log_critical(session, msg)
            raise ValueError(msg)
    # Create a .cheshire3 directory and populate it
    return 0


argparser = Cheshire3ArgumentParser(conflict_handler='resolve')
argparser.add_argument('directory', type=str,
                       action='store', nargs='?',
                       default=os.getcwd(), metavar='DIRECTORY',
                       help="name of directory in which to init the Cheshire3 database. default: current-working-dir")
argparser.add_argument('-d', '--database', type=str,
                  action='store', dest='database',
                  default=None, metavar='DATABASE',
                  help="identifier of Cheshire3 database to init. default: db_<current-working-dir>")



session = None
server = None
db = None
   
if __name__ == '__main__':
    main(sys.argv)
