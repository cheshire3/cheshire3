"""DocumentFactory and DocumentStream Implementations."""

from cheshire3.documentFactory import BaseDocumentStream, SimpleDocumentFactory


# Idea is to take the results of an SQL search and XMLify them into documents.
# FIXME:  Implement PostgresDocumentStream
class PostgresDocumentStream(BaseDocumentStream):
    def __init__(self, stream=None, format='', tag='', codec=''):
        raise NotImplementedError

    def find_documents(self, cache=0):
        pass


class PostgresDocumentFactory(SimpleDocumentFactory):
    database = ''
    host = ''
    port = 0

    _possibleSettings = {
        'databaseName': {
            'docs': 'Name of the database in which to find the data'
        },
        'host': {
            'docs': 'Host for where the SQL database is'
        },
        'port': {
            'docs': 'Port for where the SQL database is'
        }
    }

    def __init__(self, session, config, parent):
        SimpleDocumentFactory.__init__(self, session, config, parent)
        self.database = self.get_setting(session, 'databaseName', '')
        self.host = self.get_setting(session, 'host', 'localhost')
        self.port = int(self.get_setting(session, 'port', '5432'))
        # Query info to come in .load()
