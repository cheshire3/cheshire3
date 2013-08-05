"""Abstract Base Classes for Cheshire3 Objects.

Defines the base classes of object in the Cheshire3 Object model, their
API method and documentation.

Functional implementations are contained in the module for each class e.g.
Server in cheshire3.server etc.
"""

from cheshire3.session import Session
from cheshire3.configParser import C3Object


class Server(C3Object):
    """A Server object is a collection point for other objects.
    
    A Server is a collection point for other objects and an initial entry 
    into the system for requests from a ProtocolHandler. A server might know 
    about several Databases, RecordStores and so forth, but its main function 
    is to check whether the request should be accepted or not and create an
    environment in which the request can be processed.
    
    It will likely have access to a UserStore database which maintains 
    authentication and authorization information. The exact nature of this
    information is not defined, allowing many possible backend 
    implementations.
    
    Servers are the top level of configuration for the system and hence their 
    constructor requires the path to a local XML configuration file, however 
    from then on configuration information may be retrieved from other 
    locations such as a remote datastore to enable distributed environments 
    to maintain synchronicity.
    """

    databases = {}
    authStore = None
    resultSetStore = None
    queryStore = None

    def __init__(self, session, configFile="serverConfig.xml"):
        """The constructer takes a Session object and a file path to
        the configuration file to be parsed and processed.
        """
        raise(NotImplementedError)


class Database(C3Object):
    """A Database is a collection of Records and Indexes.
    
    It is responsible for maintaining and allowing access to its components, 
    as well as metadata associated with the collections. It must be able to 
    interpret a request, splitting it amongst its known resources and then 
    recombine the values into a single response.
    """
    indexes = {}
    protocolMaps = {}
    recordStore = None

    def add_record(self, session, rec):
        """Ensure that a Record is registered with the database.
        
        This method does not ensure persistence of the Record, nor index it,
        just perform registration, and accumulate its metadata.
        """
        raise NotImplementedError

    def remove_record(self, session, rec):
        """Unregister the Record.
        
        This method does not delete the Record, nor unindex it, just 
        de-registers the Record and subtracts its metadata from the whole.
        """
        raise NotImplementedError

    def index_record(self, session, rec):
        """Index a Record, return the Record.
        
        Send the Record to all Indexes registered with the Database to be 
        indexed and then return the Record (for the sake of Workflows).
        """
        raise NotImplementedError

    def unindex_record(self, session, rec):
        """Unindex a Record, return the Record.
        
        Sends the Record to all Indexes registered with the Database to be 
        removed/unindexed.
        """
        raise NotImplementedError

    def begin_indexing(self, session):
        """Prepare to index Records.

        Perform tasks before Records are to be indexed."""
        raise NotImplementedError

    def commit_indexing(self, session):
        """Finalize indexing, commit data to persistent storage.

        Perform tasks after Records have been sent to all Indexes. For 
        example, commit any temporary data to IndexStores"""
        raise(NotImplementedError)

    def reindex(self, session):
        """Reindex all Records registered with the database."""
        raise NotImplementedError

    def scan(self, session, clause, nTerms, direction=">="):
        """Scan (browse) through an Index to return a list of terms.

        Given a single clause CQL query, resolve to the appropriate Index and 
        return an ordered term list with document frequencies and total 
        occurrences with a maximum of nTerms items. Direction specifies 
        whether to move backwards or forwards from the term given in clause. 
        """
        raise NotImplementedError

    def search(self, session, query):
        """Search the database, return a ResultSet.
        
        Given a CQL query, execute the query and return a ResultSet object.
        """
        raise NotImplementedError

    def sort(self, session, resultSets, sortKeys):
        """Merge, sort and return one or more ResultSets.
        
        Take one or more resultSets, merge them and sort based on sortKeys.
        """
        raise NotImplementedError

    def commit_metadata(self, session):
        """Ensure persistence of database metadata."""
        raise(NotImplementedError)

    def accumulate_metadata(self, session, obj):
        """Accumulate metadata (e.g. size) from and object.
        """
        raise NotImplementedError


class Index(C3Object):
    """An Index defines an access point into the Records.

    An Index is an object which defines an access point into Records and is 
    responsible for extracting that information from them. It can then store 
    the information extracted in an IndexStore.
    
    The entry point can be defined using one or more Selectors (e.g. an XPath 
    expression), and the extraction process can be defined using a Workflow 
    chain of standard objects. These chains must start with an Extractor, but 
    from there might then include Tokenizers, PreParsers, Parsers, 
    Transformers, Normalizers, even other Indexes. A processing chain usually 
    finishes with a TokenMerger to merge identical tokens into the appropriate 
    data structure (a dictionary/hash/associative array)
    
    An Index can also be the last object in a regular Workflow, so long as a 
    Selector object is used to find the data in the Record immediately before 
    an Extractor.
    """
    indexStore = None

    def begin_indexing(self, session):
        """Prepare to index Records.

        Perform tasks before indexing any Records.
        """
        raise NotImplementedError

    def commit_indexing(self, session):
        """Finalize indexing.
        
        Perform tasks after Records have been indexed.
        """
        raise NotImplementedError

    def index_record(self, session, rec):
        """Index and return a Record.
        
        Accept a Record to index. If begin indexing has been called, the index 
        might not commit any data until commit_indexing is called.  If it is 
        not in batch mode, then index_record will also commit the terms to the 
        indexStore.
        """
        raise NotImplementedError

    def delete_record(self, session, rec):
        """Delete a Record from the Index.
        
        Identify terms from the Record and delete them from IndexStore. 
        Depending on the configuration of the Index, it may be necessary to do 
        this by repeating the extracting the terms from the Record, finding 
        and removing them. Hence the Record must be the same as the one that 
        was indexed.
        """
        raise NotImplementedError

    def store_terms(self, session, data, rec):
        """Store the indexed Terms in the configured IndexStore."""
        raise NotImplementedError

    def extract_data(self, session, rec):
        """Extract data from the Record.
        
        Deprecated?
        """
        raise NotImplementedError

    def fetch_term(self, session, term, summary, prox):
        """Fetch and return the data for the given term."""
        raise NotImplementedError

    def fetch_termById(self, session, termId):
        """Fetch and return the data for the given term id."""
        raise NotImplementedError

    def fetch_termList(self, session, term, nTerms, relation, end, summary):
        """Fetch and return a list of terms from the index."""
        raise NotImplementedError 

    def fetch_vector(self, session, rec, summary):
        """Fetch and return a vector for the given Record."""
        raise NotImplementedError

    def fetch_proxVector(self, session, rec, elemId=-1):
        """Fetch and return a proximity vector for the given Record."""
        raise NotImplementedError

    def fetch_summary(self, session):
        """Fetch and return summary data for all terms in the Index.
        
        e.g. for sorting, then iterating.
        USE WITH CAUTION! Everything done here for speed.
        """
        raise NotImplementedError

    def fetch_termFrequencies(self, session, mType, start, nTerms, direction):
        """Fetch and return a list of term frequency tuples."""
        raise NotImplementedError

    def clear(self, session):
        """Clear all data from Index."""
        raise NotImplementedError
    
    def scan(self, session, clause, nTerms, direction=">="):
        """Scan (browse) through an Index to return a list of terms.
        
        Given a single clause CQL query, return an ordered term list with 
        document frequencies and total occurrences with a maximum of nTerms 
        items. Direction specifies whether to move backwards or forwards from 
        the term given in clause.
        """
        raise NotImplementedError

    def search(self, session, clause, db):
        """Search this Index, return a ResultSet.
        
        Given a CQL query, execute the query and return a ResultSet object.
        """
        raise NotImplementedError

    def sort(self, session, rset):
        """Sort and return a ResultSet object.
        
        Sort and return a ResultSet object based on the values extracted 
        according to this index.
        """
        raise NotImplementedError

    def serialize_term(self, session, termId, data, nRecs=0, nOccs=0):
        """Return a string serialization representing the term.
               
        Return a string serialization representing the term for storage 
        purposes. Used as a callback from IndexStore to serialize a list of 
        terms and document references to be stored.

        termId  := numeric ID of term being serialized
        data    := list of longs
        nRecs   := number of Records containing the term, if known
        nOccs   := total occurrences of the term, if known
        """
        raise NotImplementedError

    def deserialize_term(self, session, data, nRecs=-1, prox=1):
        """Deserialize and return the internal representation of a term.
        
        Return the internal representation of a term as recreated from a 
        string serialization from storage. Used as a callback from IndexStore 
        to take serialized data and produce list of terms and document 
        references.
        
        data  := string (usually retrieved from indexStore)
        nRecs := number of Records to deserialize (all by default)
        prox  := boolean flag to include proximity information
        """
        raise NotImplementedError

    def merge_term(self, session, currentData, newData,
                   op="replace", nRecs=0, nOccs=0):
        """Merge newData into currentData and return the result.
        
        Merging takes the currentData and can add, replace or delete the data 
        found in newData, and then returns the result. Used as a callback from 
        IndexStore to take two sets of terms and merge them together.
        
        currentData := output of deserialize_terms
        newData     := flat list
        op          := replace | add | delete
        nRecs       := total records in newData
        nOccs       := total occurrences in newdata
        """
        raise NotImplementedError

    def construct_resultSetItem(self, session, term, rsiType=""):
        """Create and return a ResultSetItem.
        
        Take the internal representation of a term, as stored in this Index, 
        create and return a ResultSetItem from it.
        """
        raise NotImplementedError

    def construct_resultSet(self, session, terms, queryHash={}):
        """Create and return a ResultSet.
        
        Take a list of the internal representation of terms, as stored in this
        Index, create and return an appropriate ResultSet object.
        """
        raise NotImplementedError

    def calc_sectionOffsets(self, session, start, nRecs, dataLen=0):
        raise NotImplementedError


class Selector(C3Object):
    """A Selector is a simple wrapper around a means of selecting data.
    
    This could be an XPath or some other means of selecting data from the 
    parsed structure in a Record.
    """
    
    def process_record(self, session, record):
        """Process the given Record and return the results."""
        raise NotImplementedError


class Extractor(C3Object):
    """An Extractor takes selected data and returns extracted values.
    
    An Extractor is a processing object called by an Index with the value 
    returned by a Selector, and extracts the values into an appropriate data 
    structure (a dictionary/hash/associative array).
    
    Example Extractors might extract all text from within a DOM node / etree 
    Element, or select all text that occurs between a pair of selected DOM 
    nodes / etree Elements.
    
    Extractors must also be used on the query terms to apply the same keyword 
    processing rules, for example.
    """
    
    def process_string(self, session, data):
        """Process and return the value of a raw string.
        
        e.g. from an attribute value or the query.
        """
        raise NotImplementedError

    def process_node(self, session, data):
        """Process a DOM node."""
        raise NotImplementedError
              
    def process_eventList(self, session, data):
        """Process a list of SAX events serialized in C3 internal format."""
        raise NotImplementedError

    def process_xpathResult(self, session, data):
        """Process the result of an XPath expression.
        
        Convenience function to wrap the other process_* functions and do type
        checking.
        """
        raise NotImplementedError


class Tokenizer(C3Object):
    u"""A Tokenizer takes a string and returns an ordered list of tokens.
    
    A Tokenizer takes a string of language and processes it to produce an 
    ordered list of tokens.
    
    Example Tokenizers might extract keywords by splitting on whitespace, or 
    by identifying common word forms using a regular expression. 
    
    The incoming string is often in a data structure (dictionary / hash / 
    associative array), as per output from Extractor.
    """

    def process_string(self, session, data):
        """Process and return tokens found in a raw string."""
        raise NotImplementedError

    def process_hash(self, session, data):
        """Process and return tokens found in the keys of a hash."""
        raise NotImplementedError


class TokenMerger(C3Object):
    u"""A TokenMerger merges identical tokens and returns a hash.
    
    A TokenMerger takes an ordered list of tokens (i.e. as produced by a 
    Tokenizer) and merges them into a hash. This might involve merging 
    multiple tokens per key, while maintaining frequency, proximity 
    information etc.
    
    One or more Normalizers may occur in the processing chain between a 
    Tokenizer and TokenMerger in order to reduce dimensionality of terms.
    """

    def process_string(self, session, data):
        """Merge and return tokens found in a raw string."""
        raise NotImplementedError
    
    def process_hash(self, session, data):
        """Merge and return tokens found in a hash."""
        raise NotImplementedError


# Takes a string, returns a list of normalised values
class Normalizer(C3Object):
    """A Normalizer modifies terms to allow effective comparison.
    
    Normalizer objects are chained after Extractors in order to transform the 
    data from the Record or query.
    
    Example Normalizers might standardize the case, perform stemming or 
    transform a date into ISO8601 format.
    
    Normalizers are also needed to transform the terms in a request into the 
    same format as the term stored in the Index. For example a date index might 
    be searched using a free text date and that would need to be parsed into 
    the normalized form in order to compare it with the stored data.
    """
    
    def process_string(self, session, data):
        """Process a string into an alternative form."""
        raise NotImplementedError

    def process_hash(self, session, data):
        """Process a hash of values into alternative forms."""
        raise NotImplementedError


class DocumentFactory(C3Object):
    """A DocumentFactory takes raw data, returns one or more Documents.
    
    A DocumentFacory can be used to return Documents from e.g. a file, a 
    directory containing many files, archive files, a URL, or a web-based API.
    """
    
    def load(self, session, data,
             cache=None, format=None, tagName=None, codec=""):
        """Load documents into the document factory from data.

        Returns the DocumentFactory itself which acts as an iterator
        DocumentFactory's load function takes session, plus:

        data     := the data to load. Could be a filename, a directory name, 
                    the data as a string, a URL to the data etc.

        cache    := setting for how to cache documents in memory when reading 
                    them in.

        format   := format of the data parameter. Many options, most common:
                    * xml  -- XML file. May contain multiple records
                    * dir  -- a directory containing files to load
                    * tar  -- a tar file containing files to load
                    * zip  -- a zip file containing files to load
                    * marc -- a file with MARC records (library catalogue data)
                    * http -- a base HTTP URL to retrieve
                    
        tagName  := name of the tag which starts (and ends!) a Record.

        codec    := name of the codec in which the data is encoded.
        """
        raise NotImplementedError

    def get_document(self, session, n=-1):
        """Return the Document at index n."""
        raise NotImplementedError

    @classmethod
    def register_stream(self, session, format, cls):
        """Register a new format, handled by given DocumentStream (cls).
         
        Class method to register an implementation of a DocumentStream (cls) 
        against a name for the format parameter (format) in future calls to 
        load().
        """
        raise NotImplementedError


class QueryFactory(C3Object):
    """A QueryFactory takes data and returns a CQL Query."""
    pass

    
class Parser(C3Object):
    """A Parser takes a Document and parses it to a Record.
    
    Parsers could be viewed as Record Factories. They take a Document 
    containing some data and produce the equivalent Record.
    
    Often a simple wrapper around an XML parser, however implementations also
    exist for various types of RDF data.
    """
    
    def process_document(self, session, doc):
        """Take a Document, parse it and return a Record object."""
        raise NotImplementedError


class PreParser(C3Object):
    """A PreParser takes a Document and returns a modified Document.
    
    For example, the input document might consist of SGML data. The
    output would be a Document containing XML data.
    
    This functionality allows for Workflow chains to be strung together in 
    many ways, and perhaps in ways which the original implemention had not 
    foreseen.
    """
    
    def process_document(self, session, doc):
        """Take a Document, transform it and return a new Document object."""
        raise NotImplementedError


# Takes a Record, returns a Document
class Transformer(C3Object):
    """A Transformer transforms a Record into a Document.
    
    A Transformer may be seen as the opposite of a Parser. It takes a Record
    and produces a Document. In many cases this can be handled by an XSLT 
    stylesheet, but other instances might include one that returns a binary 
    file based on the information in the Record.
    
    Transformers may be used in the processing chain of an Index, but are more 
    likely to be used to render a Record in a format or schema for delivery to
    the end user.
    """

    def process_record(self, session, rec):
        """Take a Record, transform it and return a new Document object."""
        raise NotImplementedError


class User(C3Object):
    """A User represents a user of the system.
    
    An object representing a user of the system to allow for convenient access 
    to properties such as username, password, rights and permissions metadata.

    Users may be stores and retrieved from an ObjectStore like any other 
    configured or created C3Object.
    """

    username = ''
    password = ''
    rights = []
    email = ''
    realName = ''
    flags = []

    def has_flag(self, session, flag, object=None):
        """Does the User have the specified flag?
                
        Check whether or not the User has the specified flag.  This flag may 
        be set regarding a particular object, for example write access to a 
        particular ObjectStore.
        """
        raise NotImplementedError


class ProtocolMap(C3Object):
    """A ProtocolMap maps incoming queries to internal capabilities.
    
    A ProtocolMaps maps from an incoming query type to internal Indexes based 
    on some specification.
    """

    protocol = ""

    def resolve_index(self, session, data):
        """Given a query, resolve it and return the index object to be used."""
        raise NotImplementedError

# --- Store APIs ---


class IndexStore(C3Object):
    """A persistent storage mechanism for terms organized by Indexes.
    
    Not an ObjectStore, just looks after Indexes and their terms.
    """

    def begin_indexing(self, session, index):
        """Prepare to index Records.

        Perform tasks as required before indexing begins, for example creating 
        batch files.
        """
        raise NotImplementedError

    def commit_indexing(self, session, index):
        """Finalize indexing for the given Index.
        
        Perform tasks after all Records have been sent to given Index. For 
        example, commit any temporary data to disk."""
        raise NotImplementedError

    def commit_centralIndexing(self, session, index, filePath):
        """Finalize indexing for given index in single process context.
        
        Commit data from the indexing process to persistent storage. Called 
        automatically unless indexing is being carried out in distributed 
        context. In this case, must be called in only one of the processes.
        """
        raise NotImplementedError

    def contains_index(self, session, index):
        """Does the IndexStore currently store the given Index."""
        raise NotImplementedError

    def create_index(self, session, index):
        """Create an index in the store."""
        raise NotImplementedError

    def clean_index(self, session, index):
        """Remove all the terms from an Index, but keep the specification."""
        raise NotImplementedError

    def delete_index(self, session, index):
        """Completely delete an index from the store."""
        raise NotImplementedError

    def delete_terms(self, session, index, terms, rec=None):
        """Delete the given terms from Index.
        
        Optionally only delete terms for a particular Record.
        """
        raise NotImplementedError
    
    def store_terms(self, session, index, terms, rec):
        """Store terms in the index for a given Record."""
        raise NotImplementedError

    def create_term(self, session, index, termId, resultSet):
        """Take resultset and munge to Index format, serialise, store."""
        raise NotImplementedError

    def fetch_term(self, session, index, term, summary=0, prox=0):
        """Fetch and return data for a single term."""
        raise NotImplementedError

    def fetch_termById(self, session, index, termId):
        """Fetch and return data for a single term based on term identifier."""
        raise NotImplementedError

    def fetch_termList(self, session, index, term,
                       nTerms=0, relation="", end="", summary=0, reverse=0):
        """Fetch and return a list of terms for an Index.
        
        :param numReq: how many terms are wanted.
        :type numReq: integer
        :param relation: which order to scan through the index.
        :param end: a point to end at (e.g. between A and B)
        :param summary: only return frequency info, not the pointers to
        matching records.
        :type summary: boolean (or something that can be evaluated as True or
        False)
        :param reverse: use the reversed index if available (eg 'xedni' not
        'index').
        :rtype: list
        """
        raise NotImplementedError

    def fetch_sortValue(self, session, index, item):
        """Fetch a stored value for the given Record to use for sorting."""
        raise NotImplementedError

    def fetch_vector(self, session, index, rec, summary=0):
        """Fetch and return a vector for the given Record."""
        raise NotImplementedError

    def fetch_proxVector(self, session, index, rec, elemId=-1):
        """Fetch and return a proximity vector for the given Record."""
        raise NotImplementedError

    def fetch_summary(self, session, index):
        """Fetch and return summary data for all terms in the Index.
        
        e.g. for sorting, then iterating.
        USE WITH CAUTION! Everything done here for speed.
        """
        raise NotImplementedError

    def fetch_termFrequencies(self, session, index, mType,
                              start, nTerms, direction):
        """Fetch and return a list of term frequency tuples."""
        raise NotImplementedError

    def construct_resultSetItem(self, session, recId,
                                recStoreId, nOccs, rsiType=None):
        """Create and return a ResultSetItem.
        
        Take the internal representation of a term, as stored in this Index, 
        create and return a ResultSetItem from it.
        """
        raise NotImplementedError


class ObjectStore(C3Object):
    """A persistent storage mechanism for configured Cheshire3 objects."""

    def create_object(self, session, obj=None):
        """Create a slot for and store a serialized Cheshire3 Object.
        
        Given a Cheshire3 object, create a serialized form of it in the 
        database.
        Note: You should use create_record() as per RecordStore to create an 
        object from a configuration.
        """
        raise NotImplementedError

    def delete_object(self, session, id):
        """Delete an object."""
        raise NotImplementedError

    def fetch_object(self, session, id):
        """Fetch and return an object."""
        raise NotImplementedError

    def store_object(self, session, obj):
        """Store an object, potentially overwriting an existing copy."""
        raise NotImplementedError


class QueryStore(ObjectStore):
    """An interface to persistent storage for CQL Queries."""

    def create_query(self, session, query=None):
        """Create a new query in the store."""
        raise NotImplementedError

    def delete_query(self, session, id):
        """Delete a query from the store."""
        raise NotImplementedError

    def fetch_query(self, session, id):
        """Fetch a query from the store."""
        raise NotImplementedError

    def store_query(self, session, query):
        """Store a query, potentially overwriting an existing copy."""
        raise NotImplementedError


class RecordStore(ObjectStore):
    """A persistent storage mechanism for Records.
    
    A RecordStore allows such operations as create, update, fetch and delete. 
    It also allows fast retrieval of important Record metadata, for use in
    computing relevance rankings for example.
    """

    def create_record(self, session, rec=None):
        """Create an identifier, store and return a Record.
        
        Generate a new identifier. If a Record is given, assign the identifier 
        to the Record and store it using store_record. If Record not given 
        create a placeholder Record. Return the Record.
        """
        raise NotImplementedError

    def replace_record(self, session, rec):
        """Check for permission, replace stored copy of an existing Record.

        Carry out permission checking before calling store_record.
        """
        raise NotImplementedError
    
    def store_record(self, session, rec, transformer=None):
        """Store a Record that already has an identifier assigned.
        
        If a Transformer is given, use it to serialize the Record data.
        """
        raise NotImplementedError

    def fetch_record(self, session, id, parser=None):
        """Fetch and return the Record with the given identifier."""
        raise NotImplementedError

    def delete_record(self, session, id):
        """Delete the Record with the given identifier from storage."""
        raise NotImplementedError

    def fetch_recordMetadata(self, session, id, mType):
        """Return the size of the Record, according to its metadata."""
        raise NotImplementedError


class DocumentStore(ObjectStore):
    """A persistent storage mechanism for Documents and their metadata."""
    
    def create_document(self, session, doc=None):
        """Create an identifier, store and return a Document
        
        Generate a new identifier. If a Document is given, assign the 
        identifier to the Document and store it using store_document. If 
        Document not given create a placeholder Document. Return the Document.
        """
        raise NotImplementedError

    def delete_document(self, session, id):
        """Delete the Document with the given identifier from storage."""
        raise NotImplementedError

    def fetch_document(self, session, id):
        """Fetch and return Document with the given identifier."""
        raise NotImplementedError

    def store_document(self, session, doc):
        """Store a Document that already has an identifier assigned."""
        raise NotImplementedError


# And store result sets
class ResultSetStore(ObjectStore):
    """A persistent storage mechanism for ResultSet objects."""

    def create_resultSet(self, session, rset=None):
        """Create an identifier, store and return a ResultSet
        
        Generate a new identifier. If a ResultSet is given, assign the 
        identifier and store it using store_resultSet. If ResultSet is not 
        given create a placeholder ResultSet. Return the ResultSet.
        """
        raise NotImplementedError 

    def delete_resultSet(self, session, id):
        """Delete a ResultSet with the given identifier from storage."""
        raise NotImplementedError

    def fetch_resultSet(self, session, id):
        """Fetch and return Resultset with the given identifier."""
        raise NotImplementedError

    def store_resultSet(self, session, rset):
        """Store a ResultSet that already has an identifier assigned."""
        raise NotImplementedError

# --- Code Instantiated Objects ---


class Document(object):
    """A Document is a wrapper for raw data and its metadata.
    
    A Document is the raw data which will become a Record. It may be processed 
    into a Record by a Parser, or into another Document type by a PreParser. 
    Documents might be stored in a DocumentStore, if necessary, but can 
    generally be discarded. Documents may be anything from a JPG file, to an 
    unparsed XML file, to a string containing a URL. This allows for future 
    compatability with new formats, as they may be incorporated into the 
    system by implementing a Document type and a PreParser.
    """
    
    id = -1
    documentStore = ""
    text = ""
    mimeType = ""
    processHistory = []
    parent = ('', '', -1)

    def __init__(self, data, creator="", history=[], mimeType="",
                 parent=None, filename="", tagName="",
                 byteCount=0, byteOffset=0, wordCount=0):
        """Construct a Document from data, with given metadata attributes.
        
        The constructer takes the data which should be used to construct the 
        document. This is implementation dependant. It also optionally may 
        take a creator object, process history information and a mimetype. 
        The parent option is for documents which have been extracted from 
        another document, for example pages from a book.
        """
        raise NotImplementedError

    def get_raw(self, session):
        """Return the raw data associated with this document."""
        raise NotImplementedError


class ResultSet(object):
    """A collection of results, commonly pointers to Records.
    
    Typically created in response to a search on a Database. ResultSets are 
    also the return value when searching an IndexStore or Index and are merged 
    internally to combine results when searching multiple Indexes combined 
    with boolean operators.
    """

    termid = -1
    totalOccs = 0
    totalRecs = 0
    id = ""
    expires = ""
    index = None
    queryTerm = ""
    queryFreq = 0
    queryPositions = []
    relevancy = 0
    maxWeight = 0
    minWeight = 0

    def combine(self, session, others, clause):
        """Combine the ResultSets in 'others' into this ResultSet."""
        raise NotImplementedError

    def retrieve(self, session, nRecs, start=0):
        """Return an iterable of ``nRecs`` Records starting at ``start``."""
        raise NotImplementedError
    
    def order(self, session, spec, 
              ascending=None, missing=None, case=None, accents=None):
        """Re-order in-place based on the given spec and arguments."""
        raise NotImplementedError

    def serialize(self, session):
        """Return a string serialization of the ResultSet."""
        raise NotImplementedError

    def deserialize(self, session, data):
        """Deserialize string in ``data`` to return the populated ResultSet."""
        raise NotImplementedError


class ResultSetItem(object):
    """Object representing a result, typically a pointer to a Record.
    
    Object representing a pointer to a Record, with ResultSet specific 
    metadata.
    """

    id = 0
    recordStore = ""
    occurences = 0

    def fetch_record(self, session):
        """Fetch and return the Record represented by the ResultSetItem."""
        raise NotImplementedError

    def serialize(self, session):
        """Return a string serialization of the ResultSetItem."""
        raise NotImplementedError


class Record(object):
    """A Record is a wrapper for parsed data and its metadata.
    
    Records in the system are commonly stored in an XML form. Attached to the 
    record is various configurable metadata, such as the time it was inserted 
    into the database and by which user. Records are stored in a RecordStore 
    and retrieved via a persistent and unique identifier. The record data may 
    be retrieved as a list of SAX events, as regularised XML, as a DOM tree or 
    ElementTree.
    """
    
    tagName = ''
    status = ''
    baseUri = ''
    history = []
    rights = []
    recordStore = None    # RecordStore in which the Record is stored
    elementHash = {}
    resultSetItem = None  # ResultSetItem from which the Record was fetched

    wordCount = -1
    byteCount = -1
    metadata = {}        # Arbitrary metadata

    parent = ('', None, 0)
    processHistory = []

    dom = None
    xml = ""
    sax = []

    def __init__(self, data, xml="", docId=None, wordCount=0, byteCount=0):
        raise NotImplementedError
    
    def __repr__(self):
        if self.recordStore is not None:
            return "%s/%s" % (self.recordStore, self.id)            
        else:
            return "%s-%s" % (self.__class__.__name__, self.id)

    def get_dom(self, session):
        """Return the DOM document node for the record."""
        raise NotImplementedError

    def get_sax(self, session):
        """Return the list of SAX events for the record
        
        SAX events are serialized according to the internal Cheshire3 format.
        """
        raise NotImplementedError

    def get_xml(self, session):
        """Return the XML for the record as a serialized string."""
        raise NotImplementedError

    def process_xpath(self, session, xpath, maps={}):
        """Process and return the result of the given XPath
        
         XPath may be either a string or a configured XPath, perhaps with some 
         supplied namespace mappings.
         """
        raise NotImplementedError

    def fetch_vector(self, session, index, summary=False):
        """Fetch and return a vector for the Record from the given Index."""
        raise NotImplementedError


class Workflow(C3Object):
    """A Workflow defines a series of processing steps. 

    A Workflow is similar to the process chain concept of an index, but acts 
    at a more global level. It will allow the configuration of a Workflow 
    using Cheshire3 objects and simple code to be defined and executed for 
    input objects.
    
    For example, one might define a common Workflow pattern of PreParsers, 
    a Parser and then indexing routines in the XML configuration, and then 
    run each Document in a DocumentFactory through it. This allows users who 
    are not familiar with Python, but who are familiar with XML and available 
    Cheshire3 processing objects to implement tasks as required, by changing 
    only configuration files. It thus also allows a user to configure personal 
    workflows in a Cheshire3 system the code for which they don't have 
    permission to modify.
    """

    code = ""

    def process(self, session, *args, **kw):
        """Executes the code as constructed from the XML configuration.
        
        Executes the generate code on the given input arguments. The return 
        value is the last object to be produced by the execution. 
        This function is automatically written and compiled when the object 
        is instantiated.
        """
        raise NotImplementedError


class Logger(C3Object):
    """A Logger logs messages for system events."""

    def log(self, session, *args, **kw):
        """Log a message based in the given args."""
        raise(NotImplementedError)
    
