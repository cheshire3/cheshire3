
from __future__ import with_statement

import os

from urlparse import urlsplit

from lxml import etree
from lxml.builder import ElementMaker

from cheshire3.baseObjects import Server
from cheshire3.bootstrap import BSLxmlParser, BootstrapDocument
from cheshire3.configParser import C3Object
from cheshire3.exceptions import (ConfigFileException,
                                  ObjectDoesNotExistException,
                                  XMLSyntaxError,
                                  FileSystemException,
                                  FileDoesNotExistException)
from cheshire3.internal import cheshire3Root, CONFIG_NS


class SimpleServer(Server):
    databases = {}
    # here because it's global to the install
    _possiblePaths = {'sortPath': {"docs": "Path to the 'sort' utility"}}

    def __init__(self, session, configFile="serverConfig.xml"):
        # self.defaultFunctionLog = "__api__"
        self.defaultFunctionLog = ""
        self.databaseConfigs = {}
        self.databases = {}
        self.id = "DefaultServer"
        session.server = self

        # Bootstrappage
        dom = self._getDomFromFile(session, configFile)
        try:
            topNode = dom.childNodes[0]
        except:
            topNode = dom
        C3Object.__init__(self, session, topNode, None)

        # Add default logger to session
        log = self.get_path(session, 'defaultLogger', None)
        if log:
            session.logger = log

    def _cacheDatabases(self, session):
        # Read in all Database configurations, build and cache Database objects
        for dbid in self.databaseConfigs.keys():
            db = self.get_object(session, dbid)
            self.databases[dbid] = db

    def _get_newDatabaseId(self, session, dbConfig):
        dbid = dbConfig.attrib.get('id', None)
        # Check that the identifier is not already in use by existing database
        try:
            self.get_object(session, dbid)
        except ObjectDoesNotExistException:
            # Doesn't exists, so OK to register it
            pass
        else:
            msg = ("Database with id '{0}' is already registered. "
                   "Please specify a different id in your configurations "
                   "file.".format(dbid))
            self.log_critical(session, msg)
            raise ConfigFileException(msg)
        return dbid

    def register_databaseConfigFile(self, session, file_path):
        """Register a Cheshire3 Database config file.

        Register a configuration file for a Cheshire3 Database with
        the server.

        This process simply tells the server that it should include the
        configuration(s) in your file (it does not ingest your file) so
        you don't need to re-register when you make changes to the file.
        """
        # Read in proposed config file
        docFac = self.get_object(session, 'defaultDocumentFactory')
        docFac.load(session, file_path)
        confdoc = docFac.get_document(session)
        try:
            confrec = BSLxmlParser.process_document(session, confdoc)
        except XMLSyntaxError as e:
            msg = ("Config file {0} is not well-formed and valid XML: "
                   "{1}".format(file_path, e.message))
            self.log_critical(session, msg)
            raise ConfigFileException(msg)
        # Extract the database identifier
        confdom = confrec.get_dom(session)
        dbid = self._get_newDatabaseId(session, confdom)
        if dbid is None:
            msg = ("Config file {0} must have an 'id' attribute at the "
                   "top-level".format(file_path))
            self.log_critical(session, msg)
            raise ConfigFileException(msg)
        # Generate plugin XML
        plugin = E.config(
                         E.subConfigs(
                             E.path({'type': "database", 'id': dbid},
                                    file_path
                             )
                         )
                     )
        # Try to do this by writing config plugin file if possible
        serverDefaultPath = self.get_path(session,
                                          'defaultPath',
                                          cheshire3Root)
        userSpecificPath = os.path.join(os.path.expanduser('~'),
                                        '.cheshire3-server')
        pluginPath = os.path.join('configs',
                                  'databases',
                                  '{0}.xml'.format(dbid))
        try:
            pluginfh = open(os.path.join(serverDefaultPath, pluginPath), 'w')
        except IOError:
            try:
                pluginfh = open(os.path.join(userSpecificPath, pluginPath),
                                'w')
            except IOError:
                msg = ("Database plugin directory {0} unavailable for writing"
                       "".format(os.path.join(userSpecificPath, pluginPath)))
                self.log_critical(session, msg)
                raise FileSystemException(msg)
        pluginfh.write(etree.tostring(plugin,
                                      pretty_print=True,
                                      encoding="utf-8"
                                      )
                      )
        pluginfh.close()
        self.log_info(session,
                      "Database configured in {0} registered with Cheshire3 "
                      "Server {1}".format(file_path, self.id))


# Set up ElementMaker for Cheshire3 config namespace
E = ElementMaker(namespace=CONFIG_NS, nsmap={None: CONFIG_NS})
