"""Initialize a Cheshire 3 database."""

from __future__ import with_statement

import sys
import os

from lxml import etree
from lxml.builder import E

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def create_defaultConfig(identifier, defaultPath):
    """Create and return a generic database configuration."""
    config = E.config(
        {'id': identifier,
         'type': 'database'},
        E.objectType("cheshire3.database.SimpleDatabase"),
        # <paths>
        E.paths(
            E.path({'type': "defaultPath"}, defaultPath),
            # subsequent paths may be relative to defaultPath
            E.path({'type': "metadataPath"},
                   os.path.join('.cheshire3', 'stores', 'metadata.bdb')
                   ),
            E.object({'type': "recordStore",
                      'ref': "recordStore"}),
            E.path({'type': "indexStoreList"}, "indexStore"),
        ),
        E.subConfigs(
            # recordStore
            E.subConfig(
                {'type': "recordStore",
                 'id': "recordStore"},
                E.objectType("cheshire3.recordStore.BdbRecordStore"),
                E.paths(
                    E.path({'type': "defaultPath"},
                           os.path.join('.cheshire3', 'stores')),
                    E.path({'type': "databasePath"},
                           'recordStore.bdb'),
                    E.object({'type': "idNormalizer",
                              'ref': "StringIntNormalizer"}),
                ),
                E.options(
                    E.setting({'type': "digest"}, 'md5'),
                ),
            ),
            # indexStore
            E.subConfig(
                {'type': "indexStore",
                 'id': "indexStore"},
                E.objectType("cheshire3.indexStore.BdbIndexStore"),
                E.paths(
                    E.path({'type': "defaultPath"},
                           os.path.join('.cheshire3', 'indexes')),
                    E.path({'type': "tempPath"},
                           'temp'),
                    E.path({'type': "recordStoreHash"},
                           'recordStore'),
                )
            ),
            E.path({'type': "includeConfigs"}, 
                   os.path.join(".cheshire3", "configSelectors.xml")
            ),
        ),
    )
    return config


def create_defaultConfigSelectors():
    """Create and return configuration for generic data selectors."""
    config = E.config(
        E.subConfigs(
            # Identifier Attribute Selector
            E.subConfig(
                {'type': "selector",
                 'id': "idSelector"},
                E.objectType("cheshire3.selector.MetadataSelector"),
                E.source(
                    E.location({'type': "attribute"}, "id"),
                ),
            ),
            # Load Time Function Selector
            E.subConfig(
                {'type': "selector",
                 'id': "nowTimeSelector"},
                E.objectType("cheshire3.selector.MetadataSelector"),
                E.source(
                    E.location({'type': "function"}, "now()"),
                ),
            ),
            # Anywhere XPath Selector
            E.subConfig(
                {'type': "selector",
                 'id': "anywhereXpathSelector"},
                E.objectType("cheshire3.selector.XPathSelector"),
                E.source(
                    E.location({'type': "xpath"}, "/*"),
                ),
            ),
        ),
    )
    return config


def main(argv=None):
    """Initialize a Cheshire 3 database based on parameters in argv."""
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
            # TODO: check for --force ?
            msg = """database with id '{0}' has already been init'd. \
Please specify a different id.""".format(dbid)
            server.log_critical(session, msg)
            raise ValueError(msg)
    # Create a .cheshire3 directory and populate it
    c3_dir = os.path.join(args.directory, '.cheshire3')
    for dir_path in [c3_dir, 
                     os.path.join(c3_dir, 'stores'),
                     os.path.join(c3_dir, 'indexes'),
                     os.path.join(c3_dir, 'logs')]:
        try:
            os.makedirs(dir_path)
        except OSError:
            # Directory already exists
            server.log_error(session, 
                             "directory already exists {0}".format(dir_path))
    # Generate Protocol Map(s) (ZeeRex)
    # Generate config file(s)
    # Generate config for generic selectors
    with open(os.path.join(c3_dir, 'configSelectors.xml'), 'w') as conffh:
        config = create_defaultConfigSelectors()
        conffh.write(etree.tostring(config, 
                                    pretty_print=True,
                                    encoding="utf-8"))
    # Generate generic database config
    with open(os.path.join(c3_dir, 'config.xml'), 'w') as conffh:
        config = create_defaultConfig(dbid, args.directory)
        conffh.write(etree.tostring(config, 
                                    pretty_print=True,
                                    encoding="utf-8"))
        
    # Insert database into server configuration
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
