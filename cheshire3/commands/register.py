"""Register a Cheshire3 Database config file.

Register a configuration file for a Cheshire3 Database with the server.

This process simply tells the server that it should include the
configuration(s) in your file (it does not ingest your file) so you
don't need to re-register when you make changes to the file.
"""

from __future__ import with_statement

import sys
import os

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def main(argv=None):
    """Register a Database configuration file with the Cheshire3 Server."""
    global argparser, session, server
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    session = Session()
    server = SimpleServer(session, args.serverconfig)
    # Make path to configfile absolute
    args.configfile = os.path.abspath(os.path.expanduser(args.configfile))
    # Tell the server to register the config file
    server.register_databaseConfigFile(session, args.configfile)
    return 0
        

argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0])

argparser.add_argument('configfile', type=str,
                       action='store', nargs='?',
                       default=os.path.join(os.getcwd(), 'config.xml'),
                       metavar='CONFIGFILE',
                       help=("path to configuration file for the database to "
                             "register with the Cheshire3 server. Default: "
                             "config.xml"))

session = None
server = None

if __name__ == '__main__':
    sys.exit(main())
