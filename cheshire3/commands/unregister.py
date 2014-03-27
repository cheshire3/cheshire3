"""Unregister a Cheshire3 Database.

Unregister a Cheshire3 :py:class:`~cheshire3.baseObjects.Database` from
the :py:class:`~cheshire3.baseObjects.Server`.

This process tells the :py:class:`~cheshire3.baseObjects.Server` that it
should drop the configuration(s) for the specified
`~cheshire3.baseObjects.Database`.
"""

from __future__ import with_statement

import sys
import os

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def main(argv=None):
    """Unregister a Database from the Cheshire3 Server."""
    global argparser, session, server
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    session = Session()
    server = SimpleServer(session, args.serverconfig)
    # Tell the server to unregister the Database
    server.unregister_databaseConfig(session, args.identifier)
    return 0


argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0])

argparser.add_argument('identifier', type=str,
                       action='store', nargs='?',
                       metavar='IDENTIFIER',
                       help="identifier for the database to unregister"
                       )

session = None
server = None

if __name__ == '__main__':
    sys.exit(main())
