"""Generic Base Class for OAI-PMH server implementation."""

import os
import datetime

# Import bits from oaipmh module
from oaipmh.server import Server as OaiServer
from oaipmh.server import XMLTreeServer
from oaipmh.server import Resumption as ResumptionServer
from oaipmh.server import decodeResumptionToken, encodeResumptionToken
from oaipmh.common import Header, Identify, getMethodForVerb
from oaipmh.metadata import  MetadataRegistry as OaiMetadataRegistry
from oaipmh.metadata import global_metadata_registry
from oaipmh.error import *

from PyZ3950 import SRWDiagnostics

# Import Some necessary Cheshire3 bits
from cheshire3.server import SimpleServer
from cheshire3.baseObjects import Session
from cheshire3.resultSet import SimpleResultSet
from cheshire3.document import StringDocument
from cheshire3.exceptions import *
from cheshire3.cqlParser import parse as cqlparse
from cheshire3.internal import cheshire3Root
from cheshire3.web.oai_utils import *


class Cheshire3OaiMetadataWriter(object):
    """Cheshire3 Transforming MetadataWriter.
    
    An implementation of a 'MetadataWriter' complying with the oaipmh module's
    API.
    """
    
    def __init__(self, txr):
        self.txr = txr
    
    def __call__(self, element, rec):
        """Add a record to the element.
        
        Apply any necessary transformation to a record, and appends resulting
        XML to the elementTree.
        """
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
        self._tree_server = MinimalXMLTreeServer(server, metadata_registry,
                                                 resumption_batch_size)


class MinimalXMLTreeServer(XMLTreeServer):
    """A server that responds to messages by returning XML trees.

    Takes an object conforming to the OAIPMH API.
    
    Sub-classed only so that correct class of MinimalResumptionServer
    instantiated.
    """
    def __init__(self, server, metadata_registry, resumption_batch_size=10):
        self._server = MinimalResumptionServer(server, resumption_batch_size)
        self._metadata_registry = (metadata_registry or
                                   global_metadata_registry)
        self._nsmap = nsmap


class MinimalResumptionServer(ResumptionServer):
    """A server object that handles resumption tokens etc.
    
    More efficient than default implementations, as only contructs minimal
    resultSet needed for response.
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
            # Fetch only self._batch_size results
            # Request 1 more so that we know whether resumptionToken is needed
            # we'll trim this off later
            kw['batch_size'] = batch_size + 1
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


class Cheshire3OaiServer(object):
    """A server object complying with the oaipmh module's API."""
    
    protocolMap = None
    db = None
    
    def __init__(self, session, configs, dbs, dbName):
        self.session = session
        self.protocolMap = configs[dbName]
        self.db = dbs[dbName]
        session.database = self.db.id
        # Get some generally useful stuff now
        self.baseURL = self.protocolMap.baseURL
        # Get earliest datestamp in database - UTC of the epoch as query term
        q = cqlparse('rec.lastModificationDate > "%s"'
                     '' % (str(datetime.datetime.utcfromtimestamp(0))))
        try:
            tl = self.db.scan(session, q, 1)
        except SRWDiagnostics.Diagnostic16:
            raise ConfigFileException('Index map for rec.lastModificationDate '
                                      'required in protocolMap: %s'
                                      '' % self.db.get_path(session,
                                                            'protocolMap').id
                                      )
        else:
            try:
                datestamp = tl[0][0]
            except IndexError:
                # Something went wrong :( - use the epoch
                self.earliestDatestamp = datetime.datetime.utcfromtimestamp(0)
            else:
                try:
                    self.earliestDatestamp = datetime.datetime.strptime(
                        datestamp,
                        '%Y-%m-%dT%H:%M:%S'
                    )
                except ValueError:
                    self.earliestDatestamp = datetime.datetime.strptime(
                        datestamp,
                        '%Y-%m-%d %H:%M:%S'
                    )
        
        self.repositoryName = self.protocolMap.title
        self.protocolVersion = self.protocolMap.version
        self.adminEmails = self.protocolMap.contacts
        # Cheshire3 does not support deletions at this time
        self.deletedRecord = "no"
        # Finest level of granularity
        self.granularity = "YYYY-MM-DDThh:mm:ssZ"
        # Cheshire3 does not support compressions at this time
        self.compression = []
        self.metadataRegistry = OaiMetadataRegistry()
    
    def getRecord(self, metadataPrefix, identifier):
        """Return a (header, metadata, about) tuple for the the record.
         
            metadataPrefix - identifies metadata set to retrieve the record in
            identifier - repository-unique identifier of record
            
            Should raise error.CannotDisseminateFormatError if metadataPrefix
            is unknown or not supported by identifier.
            
            Should raise error.IdDoesNotExistError if identifier is unknown or
            illegal.
        """
        session = self.session
        if (
            metadataPrefix and not
            (metadataPrefix in self.protocolMap.recordNamespaces)
        ):
            raise CannotDisseminateFormatError()
        
        if not self.metadataRegistry.hasWriter(metadataPrefix):
            # Need to create a 'MetadataWriter' for this schema for oaipmh to
            # use, and put in self.metadataRegister
            schemaId = self.protocolMap.recordNamespaces[metadataPrefix]
            txr = self.protocolMap.transformerHash.get(schemaId, None)
            mdw = Cheshire3OaiMetadataWriter(txr)
            self.metadataRegistry.registerWriter(metadataPrefix, mdw)
            
        q = cqlparse('rec.identifier exact "%s"' % (identifier))
        try:
            rs = self.db.search(session, q)
        except SRWDiagnostics.Diagnostic16:
            raise ConfigFileException('Index map for rec.identifier required '
                                      'in protocolMap: %s'
                                      '' % self.db.get_path(session,
                                                            'protocolMap').id
                                      )
            
        if not len(rs) or len(rs) > 1:
            raise IdDoesNotExistError('%s records exist for this identifier'
                                      '' % (len(rs)))
        
        r = rs[0]        
        rec = r.fetch_record(session)
        # Now reverse lookup lastModificationDate
        q = cqlparse('rec.lastModificationDate < "%s"'
                     '' % (datetime.datetime.utcnow())
                     )
        pm = self.db.get_path(session, 'protocolMap')  # Get CQL ProtocolMap
        idx = pm.resolveIndex(session, q)
        vector = idx.fetch_vector(session, rec)
        term = idx.fetch_termById(session, vector[2][0][0])
        try:
            datestamp = datetime.datetime.strptime(term, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            datestamp = datetime.datetime.strptime(term, '%Y-%m-%d %H:%M:%S')
        # Handle non-ascii characters in identifier
        identifier = unicode(r.id, 'utf-8')
        identifier = identifier.encode('ascii', 'xmlcharrefreplace')
        return (Header(identifier, datestamp, [], None), rec, None)    
    
    def identify(self):
        """Return an Identify object describing the repository."""
        return Identify(self.repositoryName, self.baseURL,
                        self.protocolVersion, self.adminEmails,
                        self.earliestDatestamp, self.deletedRecord,
                        self.granularity, self.compression)

    def _listResults(self, metadataPrefix, set=None, from_=None, until=None):
        """Return a list of (datestamp, resultSet) tuples.
        
        Suitable for use by:
            - listIdentifiers
            - listRecords
        """
        session = self.session
        if until and until < self.earliestDatestamp:
            raise BadArgumentError('until argument value is earlier than '
                                   'earliestDatestamp.')
        if not from_:
            from_ = self.earliestDatestamp
        if not until:
            until = datetime.datetime.now()
            #(from_ < self.earliestDatestamp)
        if (until < from_):
            raise BadArgumentError('until argument value is earlier than from '
                                   'argument value.')
        q = cqlparse('rec.lastModificationDate > "%s" and '
                     'rec.lastModificationDate < "%s"' % (from_, until))
        # Actually need datestamp values as well as results - interact with
        # indexes directly for efficiency
        # Get CQL ProtocolMap
        pm = self.db.get_path(session, 'protocolMap')
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
                tuples.append((datetime.datetime.strptime(t[0], u'%Y-%m-%dT%H:%M:%S'),
                               idx.construct_resultSet(session, t[1]))
                              )
            except ValueError:
                tuples.append((datetime.datetime.strptime(t[0], u'%Y-%m-%d %H:%M:%S'),
                               idx.construct_resultSet(session, t[1]))
                              )
        return tuples

    def listIdentifiers(self, metadataPrefix, set=None, from_=None, until=None,
                        cursor=0, batch_size=10):
        """Return a list of Header objects for matching records.
        
        Return a list of Header objects for records which match the given
        parameters.
        
        metadataPrefix
            identifies metadata set to retrieve
            
        set
            set identifier; only return headers in set (optional)
        
        from_
            only retrieve headers from from_ date forward (optional)
            
        until
            only retrieve headers with dates up to and including until date
            (optional)
        
        Should raise error.CannotDisseminateFormatError if metadataPrefix is
        not supported by the repository.
        
        Should raise error.NoSetHierarchyError if the repository does not
        support sets.
        """
        if (metadataPrefix and not
            (metadataPrefix in self.protocolMap.recordNamespaces)):
            raise CannotDisseminateFormatError()
        # Cheshire3 does not support sets
        if set:
            raise NoSetHierarchyError()
        # Get list of datestamp, resultSet tuples
        tuples = self._listResults(metadataPrefix, set, from_, until)
        # Need to return iterable of header objects
        # Header(identifier, datestamp, setspec, deleted)
        # identifier: string, datestamp:
        # datetime.datetime instance
        # setspec: list
        # deleted: boolean?
        headers = []
        i = 0
        for (datestamp, rs) in tuples:
            for r in rs:
                if i < cursor:
                    i+=1
                    continue
                # Handle non-ascii characters in identifier
                identifier = unicode(r.id, 'utf-8')
                identifier = identifier.encode('ascii', 'xmlcharrefreplace')
                headers.append(Header(identifier, datestamp, [], None))
                i+=1
                if (len(headers) >= batch_size):
                    return headers
        return headers
        
    def listMetadataFormats(self, identifier=None):
        """Return a list of metadata formats. 
        
        Return a list of (metadataPrefix, schema, metadataNamespace) tuples
        (tuple items are strings).
        
        identifier
            identify record for which we want to know all supported metadata
            formats. if absent, list all metadata formats supported by
            repository. (optional)
            
        Should raise error.IdDoesNotExistError if record with identifier does
        not exist.
        
        Should raise error.NoMetadataFormatsError if no formats are available
        for the indicated record.
        
        N.B.: Cheshire3 should supply same formats to all records in a database
        """
        session = self.session
        if identifier is not None:
            q = cqlparse('rec.identifier exact "%s"' % (identifier))
            try:
                rs = self.db.search(session, q)
            except SRWDiagnostics.Diagnostic16:
                msg = ('Index map for rec.identifier required in protocolMap: '
                       '%s' % self.db.get_path(session, 'protocolMap').id
                       )
                raise ConfigFileException(msg)
                
            if not len(rs) or len(rs) > 1:
                raise IdDoesNotExistError('%s records exist for identifier: %s'
                                          '' % (len(rs), identifier)
                                          )
        # all records should be available in the same formats in a Cheshire3 database
        mfs = []
        for prefix, ns in self.protocolMap.recordNamespaces.iteritems():
            mfs.append((prefix, self.protocolMap.schemaLocations[ns], ns))
            
        if not len(mfs):
            raise NoMetadataFormatsError()
        return mfs
        
    def listRecords(self, metadataPrefix, set=None, from_=None, until=None,
                    cursor=0, batch_size=10):
        """Return a list of records.
        
        Return a list of (header, metadata, about) tuples for records which
        match the given parameters.
        
        metadataPrefix
            identifies metadata set to retrieve
            
        set
            set identifier; only return records in set (optional)
        
        from_
            only retrieve records from from_ date forward (optional)
            
        until
            only retrieve records with dates up to and including until date
            (optional)
            
        Should raise error.CannotDisseminateFormatError if metadataPrefix is
        not supported by the repository.
        
        Should raise error.NoSetHierarchyError if the repository does not
        support sets.
        """
        session = self.session
        if (
            metadataPrefix and not
            (metadataPrefix in self.protocolMap.recordNamespaces)
        ):
            raise CannotDisseminateFormatError()
        # Cheshire3 does not support sets
        if set:
            raise NoSetHierarchyError()

        if not self.metadataRegistry.hasWriter(metadataPrefix):
            # Need to create a 'MetadataWriter' for this schema for oaipmh to
            # use, and put in self.metadataRegister
            schemaId = self.protocolMap.recordNamespaces[metadataPrefix]
            txr = self.protocolMap.transformerHash.get(schemaId, None)
            mdw = Cheshire3OaiMetadataWriter(txr)
            self.metadataRegistry.registerWriter(metadataPrefix, mdw)
        # Get list of datestamp, resultSet tuples
        tuples = self._listResults(metadataPrefix, set, from_, until)
        # Need to return iterable of (header, metadata, about) tuples
        # Header(identifier, datestamp, setspec, deleted)
        # identifier: string, datestamp: datetime.datetime instance
        # setspec: list
        # deleted: boolean?
        records = []
        i = 0
        for (datestamp, rs) in tuples:
            for r in rs:
                if i < cursor:
                    i+=1
                    continue
                rec = r.fetch_record(session)
                # Handle non-ascii characters in identifier
                identifier = unicode(r.id, 'utf-8')
                identifier = identifier.encode('ascii', 'xmlcharrefreplace')
                records.append((Header(identifier, datestamp, [], None),
                                rec,
                                None))
                i+=1
                if (len(records) == batch_size):
                    return records
        return records

    def listSets(self, cursor=0, batch_size=10):
        """Return an iterable of sets.
        
        Return an iterable of (setSpec, setName) tuples (tuple items are
        strings).
        
        Should raise error.NoSetHierarchyError if the repository does not
        support sets.
        """
        raise NoSetHierarchyError()
    #= end Cheshire3OaiServer -----------------------------------------------------


def get_databasesAndConfigs(session, serv):
    """Get and return database and config mappings from Server."""
    dbs = {}
    configs = {}
    serv._cacheDatabases(session)        
    for db in serv.databases.values():
        if db.get_setting(session, 'oai-pmh'):
            db._cacheProtocolMaps(session)
            pmap = db.protocolMaps.get('http://www.openarchives.org/OAI/2.0/OAI-PMH',
                                      None)
            # check that there's a path and that it can actually be requested from this handler
            if (pmap is not None):
                configs[pmap.databaseName] = pmap
                dbs[pmap.databaseName] = db
    return dbs, configs


# Cheshire3 architecture
session = Session()
serv = SimpleServer(session, os.path.join(cheshire3Root, 'configs', 'serverConfig.xml'))
lxmlParser = serv.get_object(session, 'LxmlParser')
dbs, configs = get_databasesAndConfigs(session, serv)
c3OaiServers = {}
