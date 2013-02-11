"""Search a Cheshire3 database."""

import sys
import os

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser, \
identify_database


def _formatResultSetItem(resultSetItem):
    rec = resultSetItem.fetch_record(session)
    # Try to get a title using a selector
    ext = db.get_object(session, 'SimpleExtractor')
    title = None
    sel = None
    try:
        # Database caches object, so this is not as inefficient as it seems
        sel = db.get_object(session, 'titleXPathSelector')
    except ObjectDoesNotExistException:
        try:
            # Database caches object, so this is not as inefficient as it seems
            sel = db.get_object(session, 'titleSelector')
        except ObjectDoesNotExistException:
            pass
    if sel is not None:
        titleData = sel.process_record(session, rec)
        # Process result in order, to respect any preference in the config
        for selRes in titleData:
            if selRes:
                for title in ext.process_xpathResult(session, [selRes]).keys():
                    if title:
                        break
                if title:
                    # Strip leading/trailing whitespace
                    title = title.strip()
                    break
    # If still no title, revert to string representation of resultSetItem
    if not title:
        title = str(resultSetItem)
    return "{0} {1}\n".format(resultSetItem.resultSetPosition + 1, title)


def _format_resultSet(resultSet, outStream=sys.stdout, 
                      maximumRecords=10, startRecord=1):
    """Format and write resultSet to outstream.
    
    resultSet := instance of (sub-class of) cheshire3.baseObjects.ResultSet
    outStream := file-like object for writing to. defaults to sys.stdout
    maxRecords := maximum number of hits to display (int)
    startRecord := where in the recordStore to start from (enables result 
                   paging) first record in resultSet = 1 (not 0) 
    """
    hits = len(resultSet)
    outStream.write("searched: {0}\n".format(resultSet.query.toCQL()))
    outStream.write("{0} hits\n".format(hits))
    # Fencepost.  startRecord starts at 1, C3 ResultSetstarts at 0
    startRecord = startRecord - 1
    end = min(startRecord + maximumRecords, hits)
    for rIdx in range(startRecord, end):
        resultSetItem = resultSet[rIdx]
        resultSetItem.resultSetPosition = rIdx
        outStream.write(_formatResultSetItem(resultSetItem))
    outStream.flush()
    return 0


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
        return _format_resultSet(resultSet,
                                 maximumRecords=args.maxRecs,
                                 startRecord=args.startRec)


argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0])
argparser.add_argument('-d', '--database', type=str,
                       action='store', dest='database',
                       default=None, metavar='DATABASE',
                       help="identifier of Cheshire3 database")
argparser.add_argument('query', type=str, action='store',
                       help="query to execute on the Cheshire3 database.")
argparser.add_argument('-f', '--format', type=str,
                       action='store', dest='format',
                       default="cql", metavar='FORMAT',
                       help=("format/language of query. "
                             "default: cql (Contextual Query Language)")
                       )
argparser.add_argument('-m', '--maximum-records', type=int,
                       action='store', dest='maxRecs',
                       default=10, metavar='MAXIMUM',
                       help="maximum number of hits to display")
argparser.add_argument('-s', '--start-record', type=int,
                       action='store', dest='startRec',
                       default=1, metavar='START',
                       help=("point in the resultSet to start from (enables "
                             "result paging) first record in resultSet = 1 "
                             "(not 0)")
                       )


session = None
server = None
db = None


if __name__ == '__main__':
    main(sys.argv)