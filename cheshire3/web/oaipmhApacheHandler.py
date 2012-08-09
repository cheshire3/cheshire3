"""OAI-PMH server implementation to be run under mod_python.

 Apache Config:
<Directory /usr/local/apache2/htdocs/OAI/2.0>
  SetHandler mod_python
  PythonDebug On
  PythonPath "['/home/cheshire/cheshire3/code', ...]+sys.path"
  PythonHandler cheshire3.web.oaipmhApacheHandler
</Directory>
NB. SetHandler, not AddHandler.

"""

import sys
import os
import datetime
import cgitb

# import Some necessary Cheshire3 bits
from cheshire3.server import SimpleServer
from cheshire3.baseObjects import Session
from cheshire3.resultSet import SimpleResultSet
from cheshire3.document import StringDocument
from cheshire3.exceptions import *
from cheshire3.cqlParser import parse as cqlparse
from cheshire3.internal import cheshire3Root
from cheshire3.web.oai_utils import *

from PyZ3950 import SRWDiagnostics

# import bits from oaipmh module
import oaipmh.server
from oaipmh.server import Server as OaiServer, XMLTreeServer, Resumption as ResumptionServer, decodeResumptionToken, encodeResumptionToken
from oaipmh.common import Header, Identify, getMethodForVerb
from oaipmh.metadata import  MetadataRegistry as OaiMetadataRegistry, global_metadata_registry
from oaipmh.error import *

# Cheshire3 architecture
session = Session()

try:
    from mod_python import apache
    from mod_python.util import FieldStorage
except ImportError:
    pass
else:
    session.environment = "apache"
    
serv = SimpleServer(session, os.path.join(cheshire3Root, 'configs', 'serverConfig.xml'))
lxmlParser = serv.get_object(session, 'LxmlParser')

configs = {}
dbs = {}

serv._cacheDatabases(session)        
for db in serv.databases.values():
    if db.get_setting(session, 'oai-pmh'):
        db._cacheProtocolMaps(session)
        map = db.protocolMaps.get('http://www.openarchives.org/OAI/2.0/OAI-PMH', None)
        # check that there's a path and that it can actually be requested from this handler
        if (map is not None):
            configs[map.databaseName] = map
            dbs[map.databaseName] = db


class Cheshire3OaiMetadataWriter:
    """An implementation of a 'MetadataWriter' complying with the oaipmh module's API."""
    
    def __init__(self, txr):
        self.txr = txr
    
    def __call__(self, element, rec):
        """Apply any necessary transformation to a record, and appends resulting XML to the elementTree. """
        if self.txr:
            # use transformer object
            doc = self.txr.process_record(session, rec)
        else:
            # make no assumptions about class of record
            doc = StringDocument(rec.get_xml(session))
        lxmlRec = lxmlParser.process_document(session, doc)
        dom = lxmlRec.get_dom(session)
        return element.append(dom)
    #= end OaiMetadataWriter ------------------------------------------------------


class MinimalOaiServer(OaiServer):
    """A server that responds to messages by returning OAI-PMH compliant XML.

    Takes a server object complying with the OAIPMH interface.
    Sub-classed only so that correct class of MinimalXMLTreeServer instantiated
    """
    
    def __init__(self, server, metadata_registry=None, resumption_batch_size=10):
        self._tree_server = MinimalXMLTreeServer(server, metadata_registry, resumption_batch_size)


class MinimalXMLTreeServer(XMLTreeServer):
    """A server that responds to messages by returning XML trees.

    Takes an object conforming to the OAIPMH API.
    Sub-classed only so that correct class of MinimalResumptionServer instantiated
    """
    def __init__(self, server, metadata_registry, resumption_batch_size=10):
        self._server = MinimalResumptionServer(server, resumption_batch_size)
        self._metadata_registry = (metadata_registry or global_metadata_registry)
        self._nsmap = nsmap


class MinimalResumptionServer(ResumptionServer):
    """A server object that handles resumption tokens etc.
    
    More efficient than default implementations, as only contructs minimal resultSet needed for response.
    """
    
    def handleVerb(self, verb, kw):
        # fetch the method for the verb
        method = getMethodForVerb(self._server, verb)
        if verb in ['ListSets', 'ListIdentifiers', 'ListRecords']:
            batch_size = self._batch_size
            # check for resumption token
            if 'resumptionToken' in kw:
                kw, cursor = decodeResumptionToken(kw['resumptionToken'])
            else:
                cursor = 0
            kw['cursor'] = cursor
            end_batch = cursor + batch_size        
            # fetch only self._batch_size results
            kw['batch_size'] = batch_size + 1 # request 1 more so that we know whether resumptionToken is needed we'll trim this off later
            result = method(**kw)
            del kw['cursor'], kw['batch_size']
            # XXX defeat the laziness effect of any generators..
            result = list(result)
            if len(result) > batch_size:
                # we need a resumption token
                resumptionToken = encodeResumptionToken(kw, end_batch)
                result.pop(-1)
            else:
                resumptionToken = None
                
            return result, resumptionToken
        else:
            result = method(**kw)
        return result


class Cheshire3OaiServer:
    """A server object complying with the oaipmh module's API."""
    
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
        q = cqlparse('rec.lastModificationDate > "%s"' % (str(datetime.datetime.utcfromtimestamp(0)))) # get UTC of the epoch as query term
        try:
            tl = self.db.scan(session, q, 1)
        except SRWDiagnostics.Diagnostic16:
            raise ConfigFileException('Index map for rec.lastModificationDate required in protocolMap: %s' % self.db.get_path(session, 'protocolMap').id)
        else:
            try:
                datestamp = tl[0][0]
            except IndexError:
                #something went wrong :( - use the epoch
                self.earliestDatestamp = datetime.datetime.utcfromtimestamp(0)
            else:
                try:
                    self.earliestDatestamp = datetime.datetime.strptime(datestamp, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    self.earliestDatestamp = datetime.datetime.strptime(datestamp, '%Y-%m-%d %H:%M:%S')
        
        self.repositoryName = self.protocolMap.title
        self.protocolVersion = self.protocolMap.version
        self.adminEmails = self.protocolMap.contacts
        self.deletedRecord = "no"    # Cheshire3 does not support deletions at this time
        self.granularity = "YYYY-MM-DDThh:mm:ssZ" # finest level of granularity
        self.compression = []        # Cheshire3 does not support compressions at this time
        self.metadataRegistry = OaiMetadataRegistry()
    
    def getRecord(self, metadataPrefix, identifier):
        """Return a (header, metadata, about) tuple for the the record.
         
            metadataPrefix - identifies metadata set to retrieve the record in
            identifier - repository-unique identifier of record
            Should raise error.CannotDisseminateFormatError if metadataPrefix is unknown or not supported by identifier.
            Should raise error.IdDoesNotExistError if identifier is unknown or illegal.
        """
        if metadataPrefix and not (metadataPrefix in self.protocolMap.recordNamespaces):
            raise CannotDisseminateFormatError()
        
        if not self.metadataRegistry.hasWriter(metadataPrefix):
            # need to create a 'MetadataWriter' for this schema for oaipmh to use, and put in self.metadataRegister
            schemaId = self.protocolMap.recordNamespaces[metadataPrefix]
            txr = self.protocolMap.transformerHash.get(schemaId, None)
            mdw = Cheshire3OaiMetadataWriter(txr)
            self.metadataRegistry.registerWriter(metadataPrefix, mdw)
            
        q = cqlparse('rec.identifier exact "%s"' % (identifier))
        try:
            rs = self.db.search(session, q)
        except SRWDiagnostics.Diagnostic16:
            raise ConfigFileException('Index map for rec.identifier required in protocolMap: %s' % self.db.get_path(session, 'protocolMap').id)
            
        if not len(rs) or len(rs) > 1:
            raise IdDoesNotExistError('%s records exist for this identifier' % (len(rs)))
        
        r = rs[0]        
        rec = r.fetch_record(session)
        # now reverse lookup lastModificationDate
        q = cqlparse('rec.lastModificationDate < "%s"' % (datetime.datetime.utcnow()))
        pm = self.db.get_path(session, 'protocolMap') # get CQL ProtocolMap
        idx = pm.resolveIndex(session, q)
        vector = idx.fetch_vector(session, rec)
        term = idx.fetch_termById(session, vector[2][0][0])
        try:
            datestamp = datetime.datetime.strptime(term, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            datestamp = datetime.datetime.strptime(term, '%Y-%m-%d %H:%M:%S')
        return (Header(str(r.id), datestamp, [], None), rec, None)    
    
    def identify(self):
        """Return an Identify object describing the repository."""
        return Identify(self.repositoryName, self.baseURL, self.protocolVersion, self.adminEmails,
                        self.earliestDatestamp, self.deletedRecord, self.granularity, self.compression)

    def _listResults(self, metadataPrefix, set=None, from_=None, until=None):
        """Return a list of (datestamp, resultSet) tuples.
        
        Suitable for use by:
            - listIdentifiers
            - listRecords
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
        q = cqlparse('rec.lastModificationDate > "%s" and rec.lastModificationDate < "%s"' % (from_, until))
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
        tuples = []
        for t in termList:
            try:
                tuples.append((datetime.datetime.strptime(t[0], u'%Y-%m-%dT%H:%M:%S'), idx.construct_resultSet(session, t[1])))
            except ValueError:
                tuples.append((datetime.datetime.strptime(t[0], u'%Y-%m-%d %H:%M:%S'), idx.construct_resultSet(session, t[1])))
        return tuples

    def listIdentifiers(self, metadataPrefix, set=None, from_=None, until=None, cursor=0, batch_size=10):
        """Return a list of Header objects for records which match the given parameters.
        
            metadataPrefix - identifies metadata set to retrieve
            set - set identifier; only return headers in set (optional)
            from_ - only retrieve headers from from_ date forward (optional)
            until - only retrieve headers with dates up to and including until date (optional)
            Should raise error.CannotDisseminateFormatError if metadataPrefix is not supported by the repository.
            Should raise error.NoSetHierarchyError if the repository does not support sets.
        """
        if metadataPrefix and not (metadataPrefix in self.protocolMap.recordNamespaces):
            raise CannotDisseminateFormatError()
        # Cheshire3 does not support sets
        if set:
            raise NoSetHierarchyError()
        # get list of datestamp, resultSet tuples
        tuples = self._listResults(metadataPrefix, set, from_, until)
        # need to return iterable of header objects
        # Header(identifier, datestamp, setspec, deleted) - identifier: string, datestamp: dtaetime.datetime instance, setspec: list, deleted: boolean?
        headers = []
        i = 0
        for (datestamp, rs) in tuples:
            for r in rs:
                if i < cursor:
                    i+=1
                    continue
                headers.append(Header(str(r.id), datestamp, [], None))
                i+=1
                if (len(headers) >= batch_size):
                    return headers
        return headers
        
    def listMetadataFormats(self, identifier=None):
        """Return a list of (metadataPrefix, schema, metadataNamespace) tuples (tuple items are strings).
        
            identifier - identify record for which we want to know all 
                         supported metadata formats. if absent, list all metadata
                         formats supported by repository. (optional)
            Should raise error.IdDoesNotExistError if record with identifier does not exist.
            Should raise error.NoMetadataFormatsError if no formats are available for the indicated record.
            
            N.B.: Cheshire3 should supply same formats to all records in a database
        """
        if identifier is not None:
            q = cqlparse('rec.identifier exact "%s"' % (identifier))
            try:
                rs = self.db.search(session, q)
            except SRWDiagnostics.Diagnostic16:
                raise ConfigFileException('Index map for rec.identifier required in protocolMap: %s' % self.db.get_path(session, 'protocolMap').id)
                
            if not len(rs) or len(rs) > 1:
                raise IdDoesNotExistError('%s records exist for identifier: %s' % (len(rs), identifier))
        # all records should be available in the same formats in a Cheshire3 database
        mfs = []
        for prefix, ns in self.protocolMap.recordNamespaces.iteritems():
            mfs.append((prefix, self.protocolMap.schemaLocations[ns], ns))
            
        if not len(mfs):
            raise NoMetadataFormatsError()
        return mfs
        
    def listRecords(self, metadataPrefix, set=None, from_=None, until=None, cursor=0, batch_size=10):
        """Return a list of (header, metadata, about) tuples for records which match the given parameters.
        
            metadataPrefix - identifies metadata set to retrieve
            set - set identifier; only return records in set (optional)
            from_ - only retrieve records from from_ date forward (optional)
            until - only retrieve records with dates up to and including
                    until date (optional)
            Should raise error.CannotDisseminateFormatError if metadataPrefix is not supported by the repository.
            Should raise error.NoSetHierarchyError if the repository does not support sets.
        """
        if metadataPrefix and not (metadataPrefix in self.protocolMap.recordNamespaces):
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
        i = 0
        for (datestamp, rs) in tuples:
            for r in rs:
                if i < cursor:
                    i+=1
                    continue
                rec = r.fetch_record(session)
                records.append((Header(str(r.id), datestamp, [], None), rec, None))
                i+=1
                if (len(records) == batch_size):
                    return records
        return records

    def listSets(self, cursor=0, batch_size=10):
        """Return an iterable of (setSpec, setName) tuples (tuple items are strings).
        
            Should raise error.NoSetHierarchyError if the repository does not support sets.
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
        global configs, oaiDcReader, c3OaiServers
        path = req.uri[1:]
        if (path[-1] == "/"):
            path = path[:-1]
                    
        if configs.has_key(path):
            args = {}
            # parse options out of req
            store = FieldStorage(req)            
            for qp in store.list:
                args[qp.name] = qp.value
            try:
                oaixml = MinimalOaiServer(c3OaiServers[path], c3OaiServers[path].metadataRegistry)
            except KeyError:
                oai = Cheshire3OaiServer(path)
                c3OaiServers[path] = oai
                oaixml = MinimalOaiServer(oai, oai.metadataRegistry)
            try:
                xmlresp = oaixml.handleRequest(args)
            except DatestampError:
                try:
                    raise BadArgumentError('Invalid date format supplied.')
                except:
                    xmlresp = oaixml.handleException(args, sys.exc_info())
            except C3Exception, e:
                xmlresp = '<c3:error xmlns:c3="http://www.cheshire3.org/schemas/error" code="%s">%s</c3:error>' % (str(e.__class__).split('.')[-1], e.reason)
            self.send_xml(xmlresp, req)
        else:
            fullPath = os.path.join(apache.server_root(), 'htdocs', path)
            if os.path.exists(fullPath) and not os.path.isdir(fullPath):
                req.sendfile(os.path.join(apache.server_root(), 'htdocs', path))
            else:
                # TODO: send proper OAI error?
                dbps = ['<c3:database>{0}</c3:database>'.format(dbp) for dbp in configs]
                self.send_xml('''
<c3:error xmlns:c3="http://www.cheshire3.org/schemas/error">
    <c3:details>{0}</c3:details>
    <c3:message>Incomplete or incorrect baseURL, requires a database path from:
        <c3:databases>{1}</c3:databases>
    </c3:message>
</c3:error>'''.format(path, '\n\t'.join(dbps)), req)
                    
#- end reqHandler -------------------------------------------------------------
    
#from dateutil.tz import *
# OAI-PMH friendly ISO8601 UTCdatetime obtained with the following
# datetime.datetime.now(datetime.tzutc()).strftime('%Y-%m-%dT%H:%M:%S%Z').replace('UTC', 'Z')

c3OaiServers = {}

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
