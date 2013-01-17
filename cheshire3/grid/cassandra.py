
import pycassa

from cheshire3.configParser import C3Object
from cheshire3.exceptions import ConfigFileException


class CassandraC3Object(C3Object):

    _possiblePaths = {
        'keyspace': {
            'docs': "The Cassandra Keyspace in which to store data."
        }
    }

    _possibleSettings = {
        'host': {
            'docs': "Host on which to connect (via Thrift) to Cassandra."
        },
        'port': {
            'docs': "Port on which to connect (via Thrift) to Cassandra."
        },
        'user': {
            'docs': ("User with which to log in to Cassandra if required by "
                     "the server.")
        },
        'password': {
            'docs': ("Password with which to log in to Cassandra if required "
                     "by the server.")
        }
    }

    def __init__(self, session, config, parent):
        C3Object.__init__(self, session, config, parent)
        self.cxn = None
        self.host = self.get_setting(session, 'host', 'localhost')
        self.port = self.get_setting(session, 'port', 9160)
        self.keyspace = self.get_setting(session,
                                         'keyspace',
                                         '{0}_{1}'.format(parent.id, self.id))
        self.username = self.get_setting(session, 'user', None)
        self.passwd = self.get_setting(session, 'password', None)
        self.servers = ['{0}:{1}'.format(self.host, self.port)] 
        self._verifyDatabase(session)

    def _openContainer(self, session):
        if self.cxn is None:
            self.cxn = pycassa.connect(self.keyspace, servers=self.servers)
            if (self.username is not None) and (self.passwd is not None):
                self.cxn.login(credentials={'username': self.username,
                                            'password': self.passwd})
            else:
                self.cxn.login()

    def _verifyDatabases(self, session):
        """Verify Keyspace and ColumnFamilies.
        
        Verify existence of Keyspace and ColumnFamilies, creating if necessary.
        """
        try:
            self._openContainer(session)
        except pycassa.cassandra.ttypes.InvalidRequestException as e:
            if e.why == "Keyspace does not exist":
                # find a way to create keyspace
                with pycassa.connect('system', servers=self.servers) as cxn:
                    ks_def = pycassa.cassandra.ttypes.KsDef(
                        self.keyspace,
                        strategy_class=('org.apache.cassandra.locator.'
                                        'RackUnawareStrategy'), 
                        replication_factor=1, 
                        cf_defs=[]
                    )
                    cxn.add_keyspace(ks_def)
                self._openContainer(session)
            else:
                raise ConfigFileException("Cannot connect to Cassandra: {0!r}"
                                          "".format(e.args))
        except Exception as e:
            raise ConfigFileException("Cannot connect to Cassandra: {0!r}"
                                      "".format(e.args))
