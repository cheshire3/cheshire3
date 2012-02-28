
from cheshire3.baseObjects import Server
from cheshire3.configParser import C3Object

class SimpleServer(Server):
    databases = {}
    # here because it's global to the install
    _possiblePaths = {'sortPath' : {"docs" : "Path to the 'sort' utility"}}

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
        for dbid in self.databaseConfigs.keys():
            db = self.get_object(session, dbid)
            self.databases[dbid] = db
