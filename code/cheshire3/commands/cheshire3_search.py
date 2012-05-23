"""Search a Cheshire3 database."""

import sys
import os

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser, identify_database


def main(argv=None):
    """Search a Cheshire3 database based on query in argv."""
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
        qFac = db.get_object(session, 'defaultQueryFactory')
        query = qFac.get_query(session, args.query, format=args.format)
        resultSet = db.search(session, query)
        return 0


argparser = Cheshire3ArgumentParser(conflict_handler='resolve')
argparser.add_argument('query', type=str, action='store',
                       help="query to execute on the Cheshire3 database.")
argparser.add_argument('-f', '--format', type=str,
                  action='store', dest='format',
                  default="cql", metavar='FORMAT',
                  help="format/language of query. default: cql (Contextual Query Language)")


session = None
server = None
db = None


if __name__ == '__main__':
    main(sys.argv)