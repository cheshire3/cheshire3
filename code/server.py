
from c3errors import ConfigFileException
from baseObjects import Server, Database
from xml.dom import Node
from configParser import C3Object

class SimpleServer(Server):
    databases = {}

    # here because it's global to the install
    _possiblePaths = {'sortPath' : {"docs" : "Path to the 'sort' utility"}}

    def __init__(self, session, configFile="serverConfig.xml"):
        self.databaseConfigs = {}
        self.databases = {}
        self.id = "DefaultServer"
        session.server = self

        # Bootstrappage
        dom = self._getDomFromFile(session, configFile)
        topNode = dom.childNodes[0]
        C3Object.__init__(self, session, topNode, None)

    def _cacheDatabases(self, session):
        for dbid in self.databaseConfigs.keys():
            db = self.get_object(session, dbid)
            self.databases[dbid] = db
