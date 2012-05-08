"""Cheshire3 command."""

from __future__ import absolute_import

import sys
import os

# Manipulate sys.path to eliminate possibility of local imports
# i.e. local import of cheshire3.py will block import of cheshire3 package
sys.path.pop(0)

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def main(argv=None):
    global argparser, session, server, db
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    session = Session()
    server = SimpleServer(session, args.serverconfig)
    if args.database is not None:
        db = server.get_object(session, args.database)
    return 0


argparser = Cheshire3ArgumentParser()
#subparsers = argparser.add_subparsers(title='subcommands',
#                                   description='valid subcommands')
session = None
server = None
db = None
   
if __name__ == '__main__':
    main(sys.argv)
