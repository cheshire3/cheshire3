"""Initialize a Cheshire3 database."""

from __future__ import with_statement

import os

from socket import gethostname
from datetime import datetime
from lxml import etree
from lxml.builder import ElementMaker

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.internal import cheshire3Root, CONFIG_NS
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.utils import getShellResult
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def create_defaultConfig(identifier, args):
    """Create and return a generic database configuration.

    identifier := string
    args := argparse.Namespace
    """
    defaultPath = args.directory
    config = CONF.config(
        {'id': identifier,
         'type': 'database'},
        CONF.objectType("cheshire3.database.SimpleDatabase"),
        # <paths>
        CONF.paths(
            CONF.path({'type': "defaultPath"}, os.path.abspath(defaultPath)),
            # subsequent paths may be relative to defaultPath
            CONF.path({'type': "metadataPath"},
                   os.path.join('.cheshire3', 'stores', 'metadata.bdb')
                   ),
            CONF.object({'type': "recordStore",
                      'ref': "recordStore"}),
            CONF.object({'type': "protocolMap",
                      'ref': "cqlProtocolMap"}),
            CONF.path({'type': "indexStoreList"}, "indexStore"),
        ),
        CONF.subConfigs(
            # recordStore
            CONF.subConfig(
                {'type': "recordStore",
                 'id': "recordStore"},
                CONF.objectType("cheshire3.recordStore.BdbRecordStore"),
                CONF.paths(
                    CONF.path({'type': "defaultPath"},
                           os.path.join('.cheshire3', 'stores')),
                    CONF.path({'type': "databasePath"},
                           'recordStore.bdb'),
                    CONF.object({'type': "idNormalizer",
                              'ref': "StringIntNormalizer"}),
                    CONF.object({'type': "inWorkflow",
                                 'ref': "XmlToLZ4Workflow"}),
                    CONF.object({'type': "outWorkflow",
                                 'ref': "LZ4ToLxmlWorkflow"}),
                ),
                CONF.options(
                    CONF.setting({'type': "digest"}, 'md5'),
                ),
            ),
            # indexStore
            CONF.subConfig(
                {'type': "indexStore",
                 'id': "indexStore"},
                CONF.objectType("cheshire3.indexStore.BdbIndexStore"),
                CONF.paths(
                    CONF.path({'type': "defaultPath"},
                           os.path.join('.cheshire3', 'indexes')),
                    CONF.path({'type': "tempPath"},
                           'temp'),
                    CONF.path({'type': "recordStoreHash"},
                           'recordStore'),
                )
            ),
            # protocolMap
            CONF.subConfig(
                {'type': "protocolMap",
                 'id': "cqlProtocolMap"},
                CONF.objectType("cheshire3.protocolMap.CQLProtocolMap"),
                CONF.paths(
                    CONF.path({'type': "zeerexPath"}, args.zeerexPath)
                ),
            ),
            # MagicRedirectPreParser
            # Over-ride default behavior to preParse generic file types to METS
            # so that it can be parsed and indexed as XML
            CONF.subConfig(
                {'type': "preParser",
                 'id': "MagicRedirectPreParser"},
                CONF.objectType("cheshire3.preParser.MagicRedirectPreParser"),
                CONF.hash(
                    CONF.object({'mimeType': "application/pdf",
                              'ref': "PdfToMetsPreParserWorkflow"}),
                    CONF.object({'mimeType': "text/prs.fallenstein.rst",
                              'ref': "ReSTToMetsPreParserWorkflow"}),
                    CONF.object({'mimeType': "text/plain",
                                 'ref': "TxtToMetsPreParserWorkflow"}),
                    CONF.object({'mimeType': "text/html",
                                 'ref': "HtmlToMetsPreParserWorkflow"}),
                    CONF.object({'mimeType': "*",
                                 'ref': "METSWrappingPreParser"}),
                ),
            ),
        ),
    )
    # Check sortPath and fix up if necessary
    serverSortPath = server.get_path(session, 'sortPath')
    if not os.path.exists(serverSortPath):
        # Attempt to fix locally for default IndexStore
        sortPath = getShellResult('which sort')
        if 'which: no sort in' not in sortPath:
            # Found a sort executable - can add to configuration
            storePathsNode = config.xpath(
                '//c3:subConfig[@id="indexStore"]/c3:paths',
                namespaces={'c3': CONFIG_NS}
            )[0]
            storePathsNode.append(
                CONF.path({'type': "sortPath"}, sortPath)
            )
    # Add database docs if provided
    if args.title and args.description:
        config.insert(0, CONF.docs("{0.title} - {0.description}".format(args)))
    elif args.title:
        config.insert(0, CONF.docs(args.title))
    elif args.description:
        config.insert(0, CONF.docs(args.description))
    return config


def create_defaultConfigSelectors():
    """Create and return configuration for generic data selectors."""
    config = CONF.config(
        CONF.subConfigs(
            # Identifier Attribute Selector
            CONF.subConfig(
                {'type': "selector",
                 'id': "idSelector"},
                CONF.docs("Record identifier attribute Selector"),
                CONF.objectType("cheshire3.selector.MetadataSelector"),
                CONF.source(
                    CONF.location({'type': "attribute"}, "id"),
                ),
            ),
            # Current Time Function Selector
            CONF.subConfig(
                {'type': "selector",
                 'id': "nowTimeSelector"},
                CONF.docs("Current time function Selector"),
                CONF.objectType("cheshire3.selector.MetadataSelector"),
                CONF.source(
                    CONF.location({'type': "function"}, "now()"),
                ),
            ),
            # Anywhere XPath Selector
            CONF.subConfig(
                {'type': "selector",
                 'id': "anywhereXPathSelector"},
                CONF.docs("Anywhere XPath Selector. "
                          "Select all mets:xmlData nodes."),
                CONF.objectType("cheshire3.selector.XPathSelector"),
                CONF.source(
                    CONF.location({'type': "xpath"},
                                  "//mets:xmlData"),
                ),
            ),
            CONF.subConfig(
                {'type': "selector",
                 'id': "titleXPathSelector"},
                CONF.docs("Title XPath Selector. Select from a number of "
                          "potential locations."),
                CONF.objectType("cheshire3.selector.XPathSelector"),
                CONF.source(
                    etree.Comment("METS wrapped docutils-native XML (e.g. from"
                                  " reStructured Text)"),
                    CONF.location(
                        {'type': "xpath"},
                        "//mets:FContent/mets:xmlData/document/@title"
                    ),
                    etree.Comment("Generic Dublin-Core terms"),
                    CONF.location(
                        {'type': "xpath"},
                        "//dcterms:title"
                    ),
                    etree.Comment("Generic Dublin-Core elements"),
                    CONF.location(
                        {'type': "xpath"},
                        "//dc:title"
                    ),
                    etree.Comment("METS wrapped file @LABEL"),
                    CONF.location(
                        {'type': "xpath"},
                        "/mets:mets/@LABEL"
                    ),
                ),
            ),
        ),
    )
    return config


def create_defaultConfigIndexes():
    """Create and return configuration for generic indexes."""
    config = CONF.config(
        CONF.subConfigs(
            # Identifier Index
            CONF.subConfig(
                {'type': "index",
                 'id': "idx-identifier"},
                CONF.docs("Identifier Index"),
                CONF.objectType("cheshire3.index.SimpleIndex"),
                CONF.paths(
                    CONF.object({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                CONF.source(
                    CONF.selector({'ref': "idSelector"}),
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                    ),
                ),
            ),
            # Created Time Index
            CONF.subConfig(
                {'type': "index",
                 'id': "idx-creationDate"},
                CONF.docs("Created Time Index"),
                CONF.objectType("cheshire3.index.SimpleIndex"),
                CONF.paths(
                    CONF.object({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                CONF.source(
                    CONF.selector({'ref': "nowTimeSelector"}),
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "tokenizer",
                                  'ref': "DateTokenizer"}),
                        CONF.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                    ),
                ),
                CONF.options(
                    # Don't index or unindex in db.[un]index_record()
                    CONF.setting({'type': "noIndexDefault"}, "1"),
                    CONF.setting({'type': "noUnindexDefault"}, "1"),
                    # Need vectors to unindex these in future
                    CONF.setting({'type': "vectors"}, "1"),
                ),
            ),
            # Modified Time Index
            CONF.subConfig(
                {'type': "index",
                 'id': "idx-modificationDate"},
                CONF.docs("Modified Time Index"),
                CONF.objectType("cheshire3.index.SimpleIndex"),
                CONF.paths(
                    CONF.object({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                CONF.source(
                    CONF.selector({'ref': "nowTimeSelector"}),
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "tokenizer",
                                  'ref': "DateTokenizer"}),
                        CONF.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                    ),
                ),
                CONF.options(
                    # Need vectors to unindex these in future
                    CONF.setting({'type': "vectors"}, "1")
                ),
            ),
            # Anywhere / Full-text Index
            CONF.subConfig(
                {'type': "index",
                 'id': "idx-anywhere"},
                CONF.docs("Anywhere / Full-text Index"),
                CONF.objectType("cheshire3.index.SimpleIndex"),
                CONF.paths(
                    CONF.object({'type': "indexStore",
                            'ref': "indexStore"}),
                ),
                # Source when processing data
                CONF.source(
                    {'mode': "data"},
                    CONF.selector({'ref': "anywhereXPathSelector"}),
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "tokenizer",
                                  'ref': "RegexpFindTokenizer"}),
                        CONF.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
                # Source when processing all, any, = queries
                CONF.source(
                    {'mode': "all|any|="},
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "tokenizer",
                                  'ref': "PreserveMaskingTokenizer"}),
                        CONF.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
                # Source when processing exact queries
                CONF.source(
                    {'mode': "exact"},
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "tokenizer",
                                  'ref': "PreserveMaskingTokenizer"}),
                        CONF.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "SpaceNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
            ),
            # Title Index
            CONF.subConfig(
                {'type': "index",
                 'id': "idx-title"},
                CONF.docs("Title Index"),
                CONF.objectType("cheshire3.index.SimpleIndex"),
                CONF.paths(
                    CONF.object({'type': "indexStore",
                                 'ref': "indexStore"}),
                ),
                # Source when processing data and exact queries
                CONF.source(
                    CONF.selector({'ref': "titleXPathSelector"}),
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "SpaceNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
                CONF.options(
                    CONF.setting({'type': "sortStore"}, "1")
                ),
            ),
            # Title Keyword Index
            CONF.subConfig(
                {'type': "index",
                 'id': "idx-title-kwd"},
                CONF.docs("Title Keywords Index"),
                CONF.objectType("cheshire3.index.SimpleIndex"),
                CONF.paths(
                    CONF.object({'type': "indexStore",
                                 'ref': "indexStore"}),
                ),
                # Source when processing data
                CONF.source(
                    {'mode': "data"},
                    CONF.selector({'ref': "titleXPathSelector"}),
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "tokenizer",
                                  'ref': "RegexpFindTokenizer"}),
                        CONF.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
                # Source when processing all, any, = queries
                CONF.source(
                    {'mode': "all|any"},
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "tokenizer",
                                  'ref': "PreserveMaskingTokenizer"}),
                        CONF.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
                # Source when processing exact queries
                CONF.source(
                    {'mode': "exact|="},
                    CONF.process(
                        CONF.object({'type': "extractor",
                                  'ref': "SimpleExtractor"}),
                        CONF.object({'type': "tokenizer",
                                  'ref': "PreserveMaskingTokenizer"}),
                        CONF.object({'type': "tokenMerger",
                                  'ref': "SimpleTokenMerger"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "SpaceNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "DiacriticNormalizer"}),
                        CONF.object({'type': "normalizer",
                                  'ref': "CaseNormalizer"}),
                    ),
                ),
            ),
        ),
    )
    return config


def create_defaultConfigWorkflows():
    """Create and return configuration for Workflows."""
    config = CONF.config(
        CONF.subConfigs(
            CONF.subConfig(
                {'type': "workflow",
                 'id': "XmlToLZ4Workflow"},
                CONF.docs("Workflow to take a Record and compress the XML data"
                          " with the lz4 algorithm"),
                CONF.objectType("cheshire3.workflow.CachingWorkflow"),
                CONF.workflow(
                    CONF.object({'type': "transformer",
                                 'ref': "XmlTransformer"}),
                    CONF.object({'type': "preParser",
                                 'ref': "LZ4CompressPreParser"}),
                ),
            ),
            CONF.subConfig(
                {'type': "workflow",
                 'id': "LZ4ToLxmlWorkflow"},
                CONF.docs("Workflow to take a Document containing data "
                          "compressed with the lz4 algorithm, decompress and "
                          "parse into an LxmlRecord"),
                CONF.objectType("cheshire3.workflow.CachingWorkflow"),
                CONF.workflow(
                    CONF.object({'type': "preParser",
                                 'ref': "LZ4DecompressPreParser"}),
                    CONF.object({'type': "parser",
                                 'ref': "LxmlParser"}),
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
                     Z.index(
                         {'{http://www.cheshire3.org/schemas/explain/}index':
                          "idx-title"},
                         Z.title("Title"),
                         Z.map(
                             Z.name({'set': "dc"}, "title"),
                         ),
                         Z.configInfo(
                             Z.supports({'type': "relation"}, "exact"),
                             Z.supports({'type': "relation"}, "="),
                             Z.supports(
                                 {'type': "relation",
                                  '{{{0}}}index'.format(Z._nsmap['c3']):
                                  "idx-title-kwd"},
                                 "any"),
                             Z.supports(
                                 {'type': "relation",
                                  '{{{0}}}index'.format(Z._nsmap['c3']):
                                  "idx-title-kwd"},
                                 "all"),
                             Z.supports({'type': "relationModifier"},
                                        "string"),
                             Z.supports(
                                 {'type': "relationModifier",
                                  '{{{0}}}index'.format(Z._nsmap['c3']):
                                  "idx-title-kwd"},
                                 "word"),
                             Z.supports(
                                 {'type': "relationModifier",
                                  '{{{0}}}index'.format(Z._nsmap['c3']):
                                  "idx-title-kwd"},
                                 "stem"),
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
    global CONFIG_NS
    try:
        subConfigs = config.xpath(
            '/config/subConfigs|/c3:config/c3:subConfigs',
            namespaces={'c3': CONFIG_NS}
            )[-1]
    except IndexError:
        # Element for subConfigs does not exist - create it
        subConfigs = CONF.subConfigs()
        config.append(subConfigs)
    subConfigs.append(CONF.path(
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

    # Generate config for default Workflows
    workflowConfig = create_defaultConfigWorkflows()
    path = os.path.join(c3_dir, 'configWorkflows.xml')
    dbConfig = include_configByPath(dbConfig, path)
    xmlFilesToWrite[path] = workflowConfig

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


# Set up ElementMaker for Cheshire3 config and METS namespaces
CONF = ElementMaker(namespace=CONFIG_NS,
                    nsmap={'c3': CONFIG_NS,
                           'mets': "http://www.loc.gov/METS/",
                           'xlink': "http://www.w3.org/1999/xlink",
                           'dcterms': "http://purl.org/dc/terms/",
                           'dc': "http://purl.org/dc/elements/1.1/"})

# Set up ElementMaker for ZeeRex and Cheshire3 Explain namespaces
Z = ElementMaker(namespace="http://explain.z3950.org/dtd/2.0/",
                  nsmap={'zrx': "http://explain.z3950.org/dtd/2.0/",
                         'c3': "http://www.cheshire3.org/schemas/explain/"})

session = None
server = None
db = None

if __name__ == '__main__':
    main()
