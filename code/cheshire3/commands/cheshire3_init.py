"""Initialize a Cheshire 3 database."""

from __future__ import with_statement

import sys
import os

from lxml import etree
from lxml.builder import E

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.internal import cheshire3Root
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
                E.docs("Record identifier attribute Selector"),
                E.objectType("cheshire3.selector.MetadataSelector"),
                E.source(
                    E.location({'type': "attribute"}, "id"),
                ),
            ),
            # Current Time Function Selector
            E.subConfig(
                {'type': "selector",
                 'id': "nowTimeSelector"},
                E.docs("Current time function Selector"),
                E.objectType("cheshire3.selector.MetadataSelector"),
                E.source(
                    E.location({'type': "function"}, "now()"),
                ),
            ),
            # Anywhere XPath Selector
            E.subConfig(
                {'type': "selector",
                 'id': "anywhereXPathSelector"},
                E.docs("Anywhere XPath Selector"),
                E.objectType("cheshire3.selector.XPathSelector"),
                E.source(
                    E.location({'type': "xpath"}, "/*"),
                ),
            ),
        ),
    )
    return config


def create_defaultConfigIndexes():
    """Create and return configuration for generic indexes."""
    config = E.config(
        E.subConfigs(
            # Identifier Index
            E.subConfig(
                {'type': "index",
                 'id': "idx-identifier"},
                E.docs("Identifier Index"),
                E.objectType("cheshire3.index.SimpleIndex"),
                E.paths(
                    E.path({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                E.source(
                    E.selector({'ref': "identifierSelector"}),
                    E.process(
                        E.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                    ),
                ),
            ),
            # Created Time Index
            E.subConfig(
                {'type': "index",
                 'id': "idx-creationDate"},
                E.docs("Created Time Index"),
                E.objectType("cheshire3.index.SimpleIndex"),
                E.paths(
                    E.path({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                E.source(
                    E.selector({'ref': "nowTimeSelector"}),
                    E.process(
                        E.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        E.object({'type': "extractor",
                                  'ref': "DateTokenizer"}),
                        E.object({'type': "extractor",
                                  'ref': "SimpleTokenMerger"}),
                    ),
                ),
                E.options(
                    # Don't index or unindex in db.[un]index_record()
                    E.setting({'type': "noIndexDefault"}, "1"),
                    E.setting({'type': "noUnindexDefault"}, "1"),
                    # Need vectors to unindex these in future
                    E.setting({'type': "vectors"}, "1"),
                ),
            ),
            # Modified Time Index
            E.subConfig(
                {'type': "index",
                 'id': "idx-modificationDate"},
                E.docs("Modified Time Index"),
                E.objectType("cheshire3.index.SimpleIndex"),
                E.paths(
                    E.path({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                E.source(
                    E.selector({'ref': "nowTimeSelector"}),
                    E.process(
                        E.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        E.object({'type': "extractor",
                                  'ref': "DateTokenizer"}),
                        E.object({'type': "extractor",
                                  'ref': "SimpleTokenMerger"}),
                    ),
                ),
                E.options(
                    # Need vectors to unindex these in future
                    E.setting({'type': "vectors"}, "1")
                ),
            ),
            # Anywhere / Full-text Index
            E.subConfig(
                {'type': "index",
                 'id': "idx-anywhere"},
                E.docs("Anywhere / Full-text Index"),
                E.objectType("cheshire3.index.SimpleIndex"),
                E.paths(
                    E.path({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                # Source when processing data
                E.source(
                    {'mode': "data"},
                    E.selector({'ref': "anywhereXPathSelector"}),
                    E.process(
                        E.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        E.object({'type': "tokenizer",
                                  'ref': "RegexpFindTokenizer"}),
                        E.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                    ),
                ),
                # Source when processing all, any, = queries
                E.source(
                    {'mode': "all|any|="},
                    E.process(
                        E.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        E.object({'type': "tokenizer",
                                  'ref': "PreserveMaskingTokenizer"}),
                        E.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                        E.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        E.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
                # Source when processing exact queries
                E.source(
                    {'mode': "exact"},
                    E.process(
                        E.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        E.object({'type': "tokenizer",
                                  'ref': "PreserveMaskingTokenizer"}),
                        E.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                        E.object({'type': "normalizer",
                                  'ref': "SpaceNormalizer"}),
                        E.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        E.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
            ),
        ),
    )
    return config


def include_configByPath(config, path):
    """Modify 'config' to include file found at 'path', return 'config'.
    
    config := lxml.etree.Element
    path := string/unicode
    """
    try:
        subConfigs = config.xpath('/config/subConfigs')[-1]
    except IndexError:
        # Element for subConfigs does not exist - create it
        subConfigs = E.subConfigs()
        config.append(subConfigs)
        
    subConfigs.append(E.path(
                          {'type': "includeConfigs"},
                          path
                      )
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
Please specify a different id using the --database option.""".format(dbid)
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
            server.log_warning(session, 
                             "directory already exists {0}".format(dir_path))
    
    # Generate config file(s)
    xmlFilesToWrite = {}
    # Generate generic database config
    dbConfig = create_defaultConfig(dbid, args.directory)
    dbConfigPath = os.path.join(c3_dir, 'config.xml')
    xmlFilesToWrite[dbConfigPath] = dbConfig 
    
    # Generate Protocol Map(s) (ZeeRex)
                   
    # Generate config for generic selectors
    selectorConfig = create_defaultConfigSelectors()
    path = os.path.join(c3_dir, 'configSelectors.xml')
    dbConfig = include_configByPath(dbConfig, path)
    xmlFilesToWrite[path] = selectorConfig 
    
    # Generate config for generic indexes
    indexConfig = create_defaultConfigIndexes()
    path = os.path.join(c3_dir, 'configIndexes.xml')
    dbConfig = include_configByPath(dbConfig, path)
    xmlFilesToWrite[path] = indexConfig
    
    # Insert database into server configuration
    pathEl = E.path({'type': "database",
                     'id': dbid},
                    dbConfigPath
             )
    # Try to do this by writing config plugin file if possible
    serverDefaultPath = server.get_path(session,
                                        'defaultPath',
                                        cheshire3Root)
    includesPath = os.path.join(serverDefaultPath, 
                              'dbs', 
                              'configs.d')
    if os.path.exists(includesPath) and os.path.isdir(includesPath):
        plugin = E.config(
                     E.subConfigs(
                         pathEl
                     )
                 )
        xmlFilesToWrite[os.path.join(includesPath, '{0}.xml'.format(dbid))] = plugin
    else:
        # No database plugin directory
        server.log_warning(session, "No database plugin directory")
        raise ValueError("No database plugin directory")

    # Write configs to files
    for path, node in xmlFilesToWrite.iteritems():
        with open(path, 'w') as conffh:
            conffh.write(etree.tostring(node, 
                                        pretty_print=True,
                                        encoding="utf-8"))
    
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
