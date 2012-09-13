"""Initialize a Cheshire3 database."""

from __future__ import with_statement

import os

from socket import gethostname
from datetime import datetime
from lxml import etree
from lxml.builder import ElementMaker, E

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.internal import cheshire3Root
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def create_defaultConfig(identifier, args):
    """Create and return a generic database configuration.
    
    identifier := string
    args := argparse.Namespace
    """
    defaultPath = args.directory
    config = E.config(
        {'id': identifier,
         'type': 'database'},
        E.objectType("cheshire3.database.SimpleDatabase"),
        # <paths>
        E.paths(
            E.path({'type': "defaultPath"}, os.path.abspath(defaultPath)),
            # subsequent paths may be relative to defaultPath
            E.path({'type': "metadataPath"},
                   os.path.join('.cheshire3', 'stores', 'metadata.bdb')
                   ),
            E.object({'type': "recordStore",
                      'ref': "recordStore"}),
            E.object({'type': "protocolMap",
                      'ref': "cqlProtocolMap"}),
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
            # protocolMap
            E.subConfig(
                {'type': "protocolMap",
                 'id': "cqlProtocolMap"},
                E.objectType("cheshire3.protocolMap.CQLProtocolMap"),
                E.paths(
                    E.path({'type': "zeerexPath"}, args.zeerexPath)
                ),
            ),
        ),
    )
    # Add database docs if provided
    if args.title and args.description:
        config.insert(0, E.docs("{0.title} - {0.description}".format(args)))
    elif args.title:
        config.insert(0, E.docs(args.title))
    elif args.description:
        config.insert(0, E.docs(args.description))
        
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
                    E.object({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                E.source(
                    E.selector({'ref': "idSelector"}),
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
                    E.object({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                E.source(
                    E.selector({'ref': "nowTimeSelector"}),
                    E.process(
                        E.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        E.object({'type': "tokenizer",
                                  'ref': "DateTokenizer"}),
                        E.object({'type': "tokenMerger",
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
                    E.object({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                E.source(
                    E.selector({'ref': "nowTimeSelector"}),
                    E.process(
                        E.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        E.object({'type': "tokenizer",
                                  'ref': "DateTokenizer"}),
                        E.object({'type': "tokenMerger",
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
                    E.object({'type': "indexStore",
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


def create_defaultZeerex(identifier, args):
    """Create and return ZeeRex (to be used for CQL + SRU protocolMap).
    
    For more information on ProtocolMap, see:
    http://cheshire3.org/docs/build/build_protocolMap.html
    
    This is dependent on indexes created by create_defaultConfigIndexes() and
    should be kept up-to-date with it.
    """
    # Derive and create serverInfo
    try:
        host = gethostname()
    except:
        # Fall back to simply localhost
        host = 'localhost'
    if args.port:
        port = str(args.port)
    else:
        port = "80"
    serverInfo = Z.serverInfo(
                     {'protocol': "srw/u",
                      'version': "1.1",
                      'transport': "http"},
                     Z.host(host),
                     Z.port(port),
                     Z.database('api/sru/{0}'.format(identifier)),
                 )
    # Assemble to complete ZeeRex base on created nodes
    zeerex = Z.explain(
                 {'id': identifier,
                  'authoritative': "true"},
                 serverInfo,
                 Z.databaseInfo(
                     Z.title(args.title),
                     Z.description(args.description),
                 ),
                 Z.metaInfo(
                     Z.dateModified(datetime.utcnow().isoformat()),
                 ),
                 # Don't know schemaInfo but should include the node
                 Z.schemaInfo(),
                 Z.indexInfo(
                     Z.set({'identifier':
                            "info:srw/cql-context-set/1/cql-v1.2",
                            'name': "cql"}),
                     Z.set({'identifier': "info:srw/cql-context-set/1/dc-v1.1",
                            'name': "dc"}),
                     Z.set({'identifier': "info:srw/cql-context-set/2/rec-1.1",
                            'name': "rec"}),
                     Z.index(
                         {'{http://www.cheshire3.org/schemas/explain/}index':
                          "idx-identifier"},
                         Z.title("Record Identifier"),
                         Z.map(
                             Z.name({'set': "rec"}, "identifier"),
                         ),
                         Z.configInfo(
                             Z.supports({'type': "relation"}, "exact"),
                             Z.supports({'type': "relation"}, "="),
                             Z.supports({'type': "relation"}, "any"),
                             Z.supports({'type': "relation"}, "all"),
                             Z.supports({'type': "relation"}, "<"),
                             Z.supports({'type': "relation"}, "<="),
                             Z.supports({'type': "relation"}, ">"),
                             Z.supports({'type': "relation"}, ">="),
                             Z.supports({'type': "relation"}, "within"),
                         ),
                     ),
                     Z.index(
                         {'{http://www.cheshire3.org/schemas/explain/}index':
                          "idx-creationDate"},
                         Z.title("Record Creation Date"),
                         Z.map(
                             Z.name({'set': "rec"}, "creationDate"),
                         ),
                         Z.configInfo(
                             Z.supports({'type': "relation"}, "exact"),
                             Z.supports({'type': "relation"}, "="),
                             Z.supports({'type': "relation"}, "<"),
                             Z.supports({'type': "relation"}, "<="),
                             Z.supports({'type': "relation"}, ">"),
                             Z.supports({'type': "relation"}, ">="),
                             Z.supports({'type': "relation"}, "within"),
                         ),
                     ),
                     Z.index(
                         {'{http://www.cheshire3.org/schemas/explain/}index':
                          "idx-modificationDate"},
                         Z.title("Record Modification Date"),
                         Z.map(
                             Z.name({'set': "rec"}, "modificationDate"),
                         ),
                         Z.configInfo(
                             Z.supports({'type': "relation"}, "exact"),
                             Z.supports({'type': "relation"}, "="),
                             Z.supports({'type': "relation"}, "<"),
                             Z.supports({'type': "relation"}, "<="),
                             Z.supports({'type': "relation"}, ">"),
                             Z.supports({'type': "relation"}, ">="),
                             Z.supports({'type': "relation"}, "within"),
                         ),
                     ),
                     Z.index(
                         {'{http://www.cheshire3.org/schemas/explain/}index':
                          "idx-anywhere"},
                         Z.title("Anywhere / Full-text Keywords"),
                         Z.map(
                             Z.name({'set': "cql"}, "anywhere"),
                         ),
                         Z.configInfo(
                             Z.supports({'type': "relation"}, "="),
                             Z.supports({'type': "relation"}, "any"),
                             Z.supports({'type': "relation"}, "all"),
                             Z.supports({'type': "relationModifier"}, "word"),
                         ),
                     ),
                 ),
                 Z.configInfo(
                     Z.default({'type': "numberOfRecords"}, "1"),
                     Z.default({'type': "contextSet"}, "cql"),
                     Z.default({'type': "index"}, "cql.anywhere"),
                     Z.default({'type': "relation"}, "all"),
                     Z.default({'type': "sortCaseSensitive"}, "false"),
                     Z.default({'type': "sortAscending"}, "true"),
                     Z.default({'type': "sortMissingValue"}, "HighValue"),
                     Z.setting({'type': "maximumRecords"}, "50"),
                     Z.supports({'type': "resultSets"}),
                     Z.supports({'type': "sort"}),
                     Z.supports({'type': "relationModifier"}, "relevant"),
                     Z.supports({'type': "relationModifier"}, "word"),
                 ),
             )
    return zeerex


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
        if args.directory.endswith(os.path.sep):
            args.directory = args.directory[:-1]
        # Find local database name to use as basis of database id
        dbid = "db_{0}".format(os.path.basename(args.directory))
        server.log_debug(session,
                         ("database identifier not specified, defaulting to: "
                          "{0}".format(dbid)))
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
    c3_dir = os.path.join(os.path.abspath(args.directory), '.cheshire3')
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
    
    # Generate Protocol Map(s) (ZeeRex)
    zrx = create_defaultZeerex(dbid, args)
    zrxPath = os.path.join(c3_dir, 'zeerex_sru.xml')
    args.zeerexPath = zrxPath
    xmlFilesToWrite[zrxPath] = zrx
    
    # Generate generic database config
    dbConfig = create_defaultConfig(dbid, args)
    dbConfigPath = os.path.join(c3_dir, 'config.xml')
    xmlFilesToWrite[dbConfigPath] = dbConfig 
    
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
    # Write configs to files
    for path, node in xmlFilesToWrite.iteritems():
        with open(path, 'w') as conffh:
            conffh.write(etree.tostring(node, 
                                        pretty_print=True,
                                        encoding="utf-8"))
    
    # Tell the server to register the config file
    server.register_databaseConfigFile(session, dbConfigPath)
    return 0


argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0])
argparser.add_argument('directory', type=str,
                       action='store', nargs='?',
                       default=os.getcwd(),
                       metavar='DIRECTORY',
                       help=("name of directory in which to init the Cheshire3"
                             " database. default: current-working-dir"))
argparser.add_argument('-d', '--database', type=str,
                  action='store', dest='database',
                  default=None, metavar='DATABASE',
                  help=("identifier of Cheshire3 database to init. default: "
                        "db_<database-directory-name>"))
argparser.add_argument('-t', '--title', type=str,
                  action='store', dest='title',
                  default="", metavar='TITLE',
                  help="Title for the Cheshire3 database to init.")
argparser.add_argument('-c', '--description', type=str,
                  action='store', dest='description',
                  default="", metavar='DESCRIPTION',
                  help="Description of the Cheshire3 database to init.")
argparser.add_argument('-p', '--port', type=int,
                  action='store', dest='port',
                  default=0, metavar='PORT',
                  help=("Port on which Cheshire3 database will be served via "
                        "SRU."))


# Set up ElementMaker for ZeeRex and Cheshire3 Explain namespaces
Z = ElementMaker(namespace="http://explain.z3950.org/dtd/2.0/",
                  nsmap={None: "http://explain.z3950.org/dtd/2.0/",
                         'c3': "http://www.cheshire3.org/schemas/explain/"})

session = None
server = None
db = None

if __name__ == '__main__':
    main()
