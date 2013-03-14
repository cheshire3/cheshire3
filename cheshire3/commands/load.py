"""Load data into a Cheshire3 database."""

import sys
import os

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.exceptions import ObjectDoesNotExistException,\
    MissingDependencyException
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser, \
                                         identify_database


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
            try:
                docFac.load(session, dataArg,
                            args.cache, args.format, args.tagname, args.codec)
            except MissingDependencyException as e:
                server.log_critical(session, e.reason)
                missingDependencies =  e.dependencies
                raise MissingDependencyException('cheshire3-load script',
                                                 missingDependencies)
            wf = db.get_object(session, 'buildIndexWorkflow')
            wf.process(session, docFac)


argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0]
                                    )
argparser.add_argument('-d', '--database', type=str,
                       action='store', dest='database',
                       default=None, metavar='DATABASE',
                       help="identifier of Cheshire3 database")
argparser.add_argument('data', type=str, action='store', nargs='+',
                       help="data to load into the Cheshire3 database.")
argparser.add_argument('-l', '--cache-level', type=int, 
                       action='store', dest='cache',
                       default=0, metavar='CACHE',
                       help=(
                           "level of in memory caching to use when reading "
                           "documents in. For details, see:\n"
                           "http://github.com/cheshire3/cheshire3#loading-data"
                           )
                       )
argparser.add_argument('-f', '--format', type=str,
                       action='store', dest='format',
                       default=None, metavar='FORMAT',
                       help=(
                           "format of the data parameter. For details, see:" 
                           "http://github.com/cheshire3/cheshire3#loading-data"
                           )
                       )
argparser.add_argument('-t', '--tagname', type=str,
                       action='store', dest='tagname',
                       default=None, metavar='TAGNAME',
                       help=("the name of the tag which starts (and ends!) a "
                             "record. This is useful for extracting sections "
                             "of files as Documents and ignoring the rest of "
                             "the XML in the file.")
                       )
argparser.add_argument('-c', '--codec', type=str,
                       action='store', dest='codec',
                       default=None, metavar='CODEC',
                       help=("the name of the codec in which the data is "
                             "encoded. Commonly 'ascii' or 'utf-8'"
                           )
                       )

session = None
server = None
db = None

if __name__ == '__main__':
    sys.exit(main())
