
import sys, os, cgitb
from mod_python import apache
from mod_python.util import FieldStorage

# Apache Config:
#<Directory /usr/local/apache2/htdocs/OAI-PMH>
#  SetHandler mod_python
#  PythonDebug On
#  PythonPath "['/home/cheshire/cheshire3/code', ...]+sys.path"
#  PythonHandler oaipmhApacheHandler
#</Directory>
# NB. SetHandler, not AddHandler.

# import Some necessary Cheshire3 bits
from server import SimpleServer
from baseObjects import Session
from resultSet import SimpleResultSet
from document import StringDocument
from PyZ3950 import CQLParser, SRWDiagnostics
from c3errors import ConfigFileException

import datetime
# import bits from oaipmh module
from oaipmh.server import Server as OaiXmlServer
from oaipmh.common import Header, Identify
from oaipmh.metadata import  MetadataRegistry as OaiMetadataRegistry
from oaipmh.error import *

# Cheshire3 architecture
session = Session()
session.environment = "apache"
serv = SimpleServer(session, '/home/cheshire/cheshire3/configs/serverConfig.xml')
lxmlParser = serv.get_object(session, 'LxmlParser')

configs = {}
dbs = {}
serv._cacheDatabases(session)        
for db in serv.databases.values():
    if db.get_setting(session, 'oai-pmh'):
        db._cacheProtocolMaps(session)
        map = db.protocolMaps.get('http://www.openarchives.org/OAI/2.0/OAI-PMH', None)
        if map:
            configs[map.databaseName] = map
            dbs[map.databaseName] = db


class Cheshire3OaiMetadataWriter:
    """ An implementation of a 'MetadataWriter' complying with the oaipmh module's API. 
    """
    def __init__(self, txr):
        self.txr = txr
    
    def __call__(self, element, rec):
        """ Apply any necessary transformation to a record, and appends resulting XML to the elementTree. """
        if self.txr:
            doc = self.txr.process_record(session, rec) # use transformer obejct
        else:
            doc = StringDocument(rec.get_xml()) # make no assumptions about class of record

        lxmlRec = lxmlParser.process_document(session, doc)
        dom = lxmlRec.get_dom()
        return element.append(dom)
      
#= end OaiMetadataWriter ------------------------------------------------------


class Cheshire3OaiServer:
    """ A server object complying with the oaipmh module's API. """
    protocolMap = None
    db = None
    
    def __init__(self, dbName):
        global configs, dbs, session
        self.protocolMap = configs[dbName]
        self.db = dbs[dbName]
        session.database = self.db.id
        # get some generally useful stuff now
        self.baseURL = self.protocolMap.baseURL
        # get earliest datestamp in database
        q = CQLParser.parse('rec.lastModificationDate > "%s"' % (str(datetime.datetime.utcfromtimestamp(0)))) # get UTC of the epoch as query term
        try:
            tl = self.db.scan(session, q, 1)
        except SRWDiagnostics.Diagnostic16:
            raise ConfigFileException('Index map for rec.lastModificationDate required in protocolMap: %s' % self.db.get_path(session, 'protocolMap').id)
        else:
            try:
                datestamp = tl[0][0]
            except IndexError:
                #something went wrong :( - use the epoch
                self.earliestDatestamp = datetime.datetime.utcfromdatestamp(0)
            else:
                self.earliestDatestamp = datetime.datetime.strptime(datestamp, '%Y-%m-%d %H:%M:%S')
        
        self.repositoryName = self.protocolMap.title
        self.protocolVersion = self.protocolMap.version
        self.adminEmails = self.protocolMap.contacts
        self.deletedRecord = "no"    # Cheshire3 does not support deletions at this time
        self.granularity = "YYYY-MM-DDThh:mm:ssZ" # finest level of granularity
        self.compression = []        # Cheshire3 does not support compressions at this time
        self.metadataRegistry = OaiMetadataRegistry()
    
    def getRecord(self, metadataPrefix, identifier):
        """ Get a record for a metadataPrefix and identifier.
            metadataPrefix - identifies metadata set to retrieve
            identifier - repository-unique identifier of record
            Should raise error.CannotDisseminateFormatError if metadataPrefix is unknown or not supported by identifier.
            Should raise error.IdDoesNotExistError if identifier is unknown or illegal.
            Returns a header, metadata, about tuple describing the record.
        """
        if metadataPrefix and not self.protocolMap.recordNamespaces.has_key(metadataPrefix):
            raise CannotDisseminateFormatError()
        
        if not self.metadataRegistry.hasWriter(metadataPrefix):
            # need to create a 'MetadataWriter' for this schema for oaipmh to use, and put in self.metadataRegister
            schemaId = self.protocolMap.recordNamespaces[metadataPrefix]
            txr = self.protocolMap.transformerHash.get(schemaId, None)
            mdw = Cheshire3OaiMetadataWriter(txr)
            self.metadataRegistry.registerWriter(metadataPrefix, mdw)
            
        q = CQLParser.parse('rec.identifier exact "%s"' % (identifier))
        rs = self.db.search(session, q)
        if not len(rs) or len(rs) > 1:
            raise IdDoesNotExistError('%s records exist for this identifier' % (len(rs)))
        
        r = rs[0]        
        rec = r.fetch_record(session)
        # now reverse lookup lastModificationDate
        q = CQLParser.parse('rec.lastModificationDate < "%s"' % (datetime.datetime.utcnow()))
        pm = self.db.get_path(session, 'protocolMap') # get CQL ProtocolMap
        idx = pm.resolveIndex(session, q)
        vector = idx.fetch_vector(session, rec)
        term = idx.fetch_termById(session, vector[2][0][0])
        datestamp = datetime.datetime.strptime(term, '%Y-%m-%d %H:%M:%S')
        return (Header(str(r.id), datestamp, [], None), rec, None)    
    
    def identify(self):
        """ Retrieve information about the repository.
            Returns an Identify object describing the repository.
        """
        return Identify(self.repositoryName, self.baseURL, self.protocolVersion, self.adminEmails,
                        self.earliestDatestamp, self.deletedRecord, self.granularity, self.compression)

    def _listResults(self, metadataPrefix, set=None, from_=None, until=None):
        """ Internal functions to get a list of datestamp, resultSet tuples, suitable for use by: listIdentifiers, listRecords
            Returns a list of datestamp, resultSet tuples, suitable for use by: listIdentifiers, listRecords
        """
        if until and until < self.earliestDatestamp:
            raise BadArgumentError('until argument value is earlier than earliestDatestamp.')
        if not from_:
            from_ = self.earliestDatestamp
        if not until:
            until = datetime.datetime.now()
            #(from_ < self.earliestDatestamp)
        if (until < from_):
            raise BadArgumentError('until argument value is earlier than from argument value.')
        
        q = CQLParser.parse('rec.lastModificationDate > "%s" and rec.lastModificationDate < "%s"' % (from_, until))
        # actually need datestamp values as well as results - interact with indexes directly for efficiency
        pm = self.db.get_path(session, 'protocolMap') # get CQL ProtocolMap
        idx = pm.resolveIndex(session, q.leftOperand)
        q.config = pm
        res = {}
        for src in idx.sources[u'data']:
            res.update(src[1].process(session, [[str(from_)]]))
            res.update(src[1].process(session, [[str(until)]]))
            
        from_ = min(res.keys())
        until = max(res.keys())
        # tweak until value to make it inclusive
        until = until[:-1] + chr(ord(until[-1])+1)
        termList = idx.fetch_termList(session, from_, 0, '>=', end=until)
        # create list of datestamp, resultSet tuples
        tuples = [(datetime.datetime.strptime(t[0], '%Y-%m-%d %H:%M:%S'), idx.construct_resultSet(session, t[1])) for t in termList]
        return tuples

    def listIdentifiers(self, metadataPrefix, set=None, from_=None, until=None):
        """ Get a list of header information on records.
            metadataPrefix - identifies metadata set to retrieve
            set - set identifier; only return headers in set (optional)
            from_ - only retrieve headers from from_ date forward (optional)
            until - only retrieve headers with dates up to and including until date (optional)
            Should raise error.CannotDisseminateFormatError if metadataPrefix is not supported by the repository.
            Should raise error.NoSetHierarchyError if the repository does not support sets.
            Returns an iterable of headers.
        """
        if metadataPrefix and not self.protocolMap.recordNamespaces.has_key(metadataPrefix):
            raise CannotDisseminateFormatError()
        # Cheshire3 does not support sets
        if set:
            raise NoSetHierarchyError()
        
        # get list of datestamp, resultSet tuples
        tuples = self._listResults(metadataPrefix, set, from_, until)
        # need to return iterable of header objects
        # Header(identifier, datestamp, setspec, deleted) - identifier: string, datestamp: dtaetime.datetime instance, setspec: list, deleted: boolean?
        headers = []
        for (datestamp, rs) in tuples:
            for r in rs:
                headers.append(Header(str(r.id), datestamp, [], None))
        
        return headers
        
    def listMetadataFormats(self, identifier=None):
        """List metadata formats supported by repository or record.
            identifier - identify record for which we want to know all
                         supported metadata formats. if absent, list all metadata
                         formats supported by repository. (optional)
            Should raise error.IdDoesNotExistError if record with identifier does not exist.
            Should raise error.NoMetadataFormatsError if no formats are available for the indicated record.
            Returns an iterable of metadataPrefix, schema, metadataNamespace tuples (each entry in the tuple is a string).
        """
        mfs = []
        for prefix, ns in self.protocolMap.recordNamespaces.iteritems():
            mfs.append((prefix, self.protocolMap.schemaLocations[ns], ns))
        return mfs
        
    def listRecords(self, metadataPrefix, set=None, from_=None, until=None):
        """Get a list of header, metadata and about information on records.
            metadataPrefix - identifies metadata set to retrieve
            set - set identifier; only return records in set (optional)
            from_ - only retrieve records from from_ date forward (optional)
            until - only retrieve records with dates up to and including
                    until date (optional)
            Should raise error.CannotDisseminateFormatError if metadataPrefix is not supported by the repository.
            Should raise error.NoSetHierarchyError if the repository does not support sets.
            Returns an iterable of header, metadata, about tuples.
        """
        if metadataPrefix and not self.protocolMap.recordNamespaces.has_key(metadataPrefix):
            raise CannotDisseminateFormatError()
        # Cheshire3 does not support sets
        if set:
            raise NoSetHierarchyError()

        if not self.metadataRegistry.hasWriter(metadataPrefix):
            # need to create a 'MetadataWriter' for this schema for oaipmh to use, and put in self.metadataRegister
            schemaId = self.protocolMap.recordNamespaces[metadataPrefix]
            txr = self.protocolMap.transformerHash.get(schemaId, None)
            mdw = Cheshire3OaiMetadataWriter(txr)
            self.metadataRegistry.registerWriter(metadataPrefix, mdw)
        
        # get list of datestamp, resultSet tuples
        tuples = self._listResults(metadataPrefix, set, from_, until)
        # need to return iterable of (header, metadata, about) tuples
        # Header(identifier, datestamp, setspec, deleted) - identifier: string, datestamp: dtaetime.datetime instance, setspec: list, deleted: boolean?
        records = []
        if len(tuples):
            for (datestamp, rs) in tuples:
                for r in rs:
                    rec = r.fetch_record(session)
                    records.append((Header(str(r.id), datestamp, [], None), rec, None))
        
        return records

    def listSets(self):
        """Get a list of sets in the repository.
            Should raise error.NoSetHierarchyError if the repository does not support sets.
            Returns an iterable of setSpec, setName tuples (strings).
        """
        raise NoSetHierarchyError()
        
#= end Cheshire3OaiServer -----------------------------------------------------


class reqHandler:
    def send_xml(self, text, req, code=200):
        req.content_type = 'text/xml'
        req.content_length = len(text)
        req.send_http_header()
        req.write(text)
        
        
    def dispatch(self, req):
        global configs, oaiMetadataRegistry, oaiDcReader
        path = req.uri[1:]
        if (path[-1] == "/"):
            path = path[:-1]
                    
        if configs.has_key(path):
            args = {}
            # parse options out of req
            store = FieldStorage(req)            
            for qp in store.list:
                args[qp.name] = qp.value
                            
            oai = Cheshire3OaiServer(path)
            oaixml = OaiXmlServer(oai, oai.metadataRegistry)
            try:
                xmlresp = oaixml.handleRequest(args)
            except DatestampError:
                try:
                    raise BadArgumentError('Invalid date format supplied.')
                except:
                    xmlresp = oaixml.handleException(args, sys.exc_info())

            self.send_xml(xmlresp, req)
        else:
            fullPath = os.path.join(apache.server_root(), 'htdocs', path)
            if os.path.exists(fullPath) and not os.path.isdir(fullPath):
                req.sendfile(os.path.join(apache.server_root(), 'htdocs', path))
            else:
                # TODO: send proper OAI error
                self.send_xml('<error>Incomplete baseURL, requires a database path from: %s</error>' % (repr(configs.keys())), req)
                    
#- end reqHandler -------------------------------------------------------------
    
#from dateutil.tz import *
# OAI-PMH friendly ISO8601 UTCdatetime obtained with the following
# datetime.datetime.now(datetime.tzutc()).strftime('%Y-%m-%dT%H:%M:%S%Z').replace('UTC', 'Z')

h = reqHandler()        

def handler(req):
    # do stuff
    try:
        h.dispatch(req)
    except:
        req.content_type = "text/html"
        cgitb.Hook(file = req).handle()                                            # give error info
    else:
        return apache.OK

# Add AuthHandler here when necesary ------------------------------------------
