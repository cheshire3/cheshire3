"""Load data into a Cheshire3 database."""

import sys
import os

from lxml import etree

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.internal import cheshire3Root
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser

def main(argv=None):
    """Load data into a Cheshire3 database based on parameters in argv."""
    global argparser, session, server, db
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    session = Session()
    server = SimpleServer(session, args.serverconfig)
    if args.database is None:
        # Walk up directories looking for a .cheshire3 directory
        cpath = os.getcwd()
        boundary = os.path.abspath(os.path.expanduser('~'))
        while True:
            server.log_debug(session, cpath)
            if (cpath == os.path.split(boundary)[0] or
                len(cpath) < len(boundary)):
                msg = """Not in a Cheshire3 database.
Refusing to look any further up the directory hierarchy than: {0}
Please provide a database identifier using the --database option.
""".format(boundary)
                server.log_critical(session, msg)
                return 1
            c3_dir = os.path.join(cpath, '.cheshire3')
            if os.path.exists(c3_dir) and os.path.isdir(c3_dir):
                with open(os.path.join(c3_dir, 'config.xml')) as cfh:
                    conf = etree.parse(cfh)
                    dbid = conf.getroot().attrib['id']
                    del conf
                break
            cpath, foo = os.path.split(cpath)
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
        docFac = db.get_object(session, 'defaultDocumentFactory')
        docFac.load(session, args.data)
        wf = db.get_object(session, 'buildIndexWorkflow')
        wf.process(session, docFac)


argparser = Cheshire3ArgumentParser(conflict_handler='resolve')
argparser.add_argument('data', type=str, action='store',
                       help="data to load into the Cheshire3 database.")

session = None
server = None
db = None

if __name__ == '__main__':
    main(sys.argv)