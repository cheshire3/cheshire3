Cheshire3 Tutorials - Python API
================================

.. highlight:: python
   :linenothreshold: 5


The :doc:`Cheshire3 Object Model </objects/index>` defines public methods for
each object class. These can be used within Python_, for embedding Cheshire3
services within a Python_ enabled web application framework, such as Django,
CherryPy, `mod_wsgi`_ etc. or whenever the command-line interface is
insufficient. This tutorial outlines how to carry out some of the more common
operations using these public methods.


Initializing Cheshire3 Architecture
'''''''''''''''''''''''''''''''''''

Initializing the Cheshire3 Architecture consists primarily of creating
instances of the following types within the
:doc:`Cheshire3 Object Model </objects/index>`:

Session
    An object representing the user session. It will be passed around amongst
    the processing objects to maintain details of the current environment.
    It stores, for example, user and identifier for the database currently in
    use.

Server
    A protocol neutral collection of databases, users and their dependent
    objects. It acts as an inital entry point for all requests and handles
    such things as user authentication, and global object configuration.


The first thing that we need to do is create a Session and build a Server::

    >>> from cheshire3.baseObjects import Session
    >>> session = Session()


The Server looks after all of our objects, databases, indexes ...
everything. Its constructor takes session and one argument, the filename
of the top level configuration file. You could supply your own, or you can
find the filename of the default server configuration dynamically as
follows::

    >>> import os
    >>> from cheshire3.server import SimpleServer
    >>> from cheshire3.internal import cheshire3Root
    >>> serverConfig = os.path.join(cheshire3Root, 'configs', 'serverConfig.xml')
    >>> server = SimpleServer(session, serverConfig)
    >>> server
    <cheshire3.server.SimpleServer object...


Most often you'll also want to work within a Database:

Database
    A virtual collection of Records which may be interacted with. A Database
    includes Indexes, which contain data extracted from the Records as well
    as configuration details. The Database is responsible for handling
    queries which come to it, distributing the query amongst its component
    Indexes and returning a ResultSet. The Database is also responsible for
    maintaining summary metadata (e.g. number of items, total word count etc.)
    that may be need for relevance ranking etc.


To get a database.::

    >>> db = server.get_object(session, 'db_test')
    >>> db
    <cheshire3.database.SimpleDatabase object...


After this you MUST set session.database to the identifier for your
database, in this case 'db\_test'::

    >>> session.database = 'db_test'


This is primarily for efficiency in the workflow processing (objects are
cached by their identifier, which might be duplicated for different
objects in different databases).

Another useful path to know is the database's default path::

    >>> dfp = db.get_path(session, 'defaultPath')


Using the ``cheshire3`` command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One way to ensure that Cheshire3 architecture is initialized is to use the
Cheshire3 interpreter, which wraps the main Python interpreter, to run your
script or just drop you into the interactive console.

``cheshire3 [script]``
   Run the commands in the script inside the current cheshire3
   environment. If script is not provided it will drop you into an interactive
   console (very similar the the native Python interpreter.) You can also tell
   it to drop into interactive mode after executing your script using the
   ``--interactive`` option.

When initializing the architecture in this way, ``session`` and ``server``
variables will be created, as will a ``db`` object if you ran the script from
inside a Cheshire3 database directory, or provided a database identifier
using the ``--database`` option. The variable will correspond to instances of
Session, Server and Database respectively.


.. _tutorial-python-loadingdata:

Loading Data
''''''''''''

In order to load data into your database you'll need a document factory
to find your documents, a parser to parse the XML and a record store to
put the parsed XML into. The most commonly used are
defaultDocumentFactory and LxmlParser. Each database needs its own
record store.::

    >>> df = db.get_object(session, "defaultDocumentFactory")
    >>> parser = db.get_object(session, "LxmlParser")
    >>> recStore = db.get_object(session, "recordStore")


Before we get started, we need to make sure that the stores are all
clear::

    >>> recStore.clear(session)
    <cheshire3.recordStore.BdbRecordStore object...
    >>> db.clear_indexes(session)


First you should call db.begin\_indexing() in order to let the database
initialise anything it needs to before indexing starts. Ditto for the
record store::

    >>> db.begin_indexing(session)
    >>> recStore.begin_storing(session)


Then you'll need to tell the document factory where it can find your
data::

    >>> df.load(session, 'data', cache=0, format='dir')
    <cheshire3.documentFactory.SimpleDocumentFactory object...


DocumentFactory's load function takes session, plus:

data
    this could be a filename, a directory name, the data as a string, a URL to
    the data and so forth.

    If data ends in [(numA):(numB)], and the preceding string is a filename,
    then the data will be extracted from bytes numA through to numB (this is
    pretty advanced though - you'll probably never need it!)

cache
    setting for how to cache documents in memory when reading them in.
    This will depend greatly on use case. e.g. if loading 3Gb of documents on a
    machine with 2Gb memory, full caching will obviously not work very well. On
    the other hand, if loading a reasonably small quantity of data over HTTP,
    full caching would read all of the data in one shot, closing the HTTP
    connection and avoiding potential timeouts. Possible values:

    0
        no document caching. Just locate the data and get ready to discover
        and yield documents when they're requested from the documentFactory.
        This is probably the option you're most likely to want.

    1
        Cache location of documents within the data stream by byte offset.

    2
        Cache full documents.

format
    The format of the data parameter. Many options, the most common are:

    :xml: xml file. Can have multiple records in single file.
    :dir: a directory containing files to load
    :tar: a tar file containing files to load
    :zip: a zip file containing files to load
    :marc: a file with MARC records (library catalogue data)
    :http: a base HTTP URL to retrieve

tagName
    the name of the tag which starts (and ends!) a record. This is useful for
    extracting sections of documents and ignoring the rest of the XML in the
    file.

codec
    the name of the codec in which the data is encoded. Normally 'ascii' or
    'utf-8'


You'll note above that the call to load returns itself. This is because
the document factory acts as an iterator. The easiest way to get to your
documents is to loop through the document factory::

    >>> for doc in df:
    ...    rec = parser.process_document(session, doc)  # [1]
    ...    recStore.create_record(session, rec)         # [2]
    ...    db.add_record(session, rec)                  # [3]
    ...    db.index_record(session, rec)                # [4]
    recordStore/...


In this loop, we:

1. Use the Lxml_ Etree Parser to create a record object.

2. Store the record in the recordStore. This assigns an identifier to it, by
   default a sequential integer.

3. Add the record to the database. This stores database level metadata such
   as how many words in total, how many records, average number of words per
   record, average number of bytes per record and so forth.

4. Index the record against all indexes known to the database - typically all
   indexes in the indexStore in the database's 'indexStore' path setting.


Then we need to ensure this data is committed to disk::

    >>> recStore.commit_storing(session)
    >>> db.commit_metadata(session)


And, potentially taking longer, merge any temporary index files created::

    >>> db.commit_indexing(session)


Pre-Processing (PreParsing)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

As often than not, documents will require some sort of pre-processing
step in order to ensure that they're valid XML in the schema that you
want them in. To do this, there are PreParser objects which take a
document and transform it into another document.

The simplest preParser takes raw text, escapes the entities and wraps it
in a element::

    >>> from cheshire3.document import StringDocument
    >>> doc = StringDocument("This is some raw text with an & and a < and a >.")
    >>> pp = db.get_object(session, 'TxtToXmlPreParser')
    >>> doc2 = pp.process_document(session, doc)
    >>> doc2.get_raw(session)
    '<data>This is some raw text with an &amp; and a &lt; and a &gt;.</data>'


Searching
'''''''''

In order to allow for translation between query languages (if possible)
we have a query factory, which defaults to CQL (SRU's query language,
and our internal language)::

    >>> qf = db.get_object(session, 'defaultQueryFactory')
    >>> qf
    <cheshire3.queryFactory.SimpleQueryFactory object ...


We can then use this factory to build queries for us::

    >>> q = qf.get_query(session, 'c3.idx-text-kwd any "compute"')
    >>> q
    <cheshire3.cqlParser.SearchClause ...


And then use this parsed query to search the database::

    >>> rs = db.search(session, q)
    >>> rs
    <cheshire3.resultSet.SimpleResultSet ...
    >>> len(rs)
    3


The 'rs' object here is a result set which acts much like a list. Each
entry in the result set is a ResultSetItem, which is a pointer to a
record::

    >>> rs[0]
    Ptr:recordStore/1


Retrieving
''''''''''

Each result set item can fetch its record::

    >>> rec = rs[0].fetch_record(session)
    >>> rec.recordStore, rec.id
    ('recordStore', 1)


Records can expose their data as xml::

    >>> rec.get_xml(session)
    '<record>...


As :abbr:`SAX (Simple API for XML)` events::

    >>> rec.get_sax(session)
    ["4 None, 'record', 'record', {}...


Or as DOM nodes, in this case using the Lxml_ Etree API::

    >>> rec.get_dom(session)
    <Element record at ...


You can also use XPath expressions on them::

    >>> rec.process_xpath(session, '/record/header/identifier')
    [<Element identifier at ...
    >>> rec.process_xpath(session, '/record/header/identifier/text()')
    ['oai:CiteSeerPSU:2']


Transforming Records
''''''''''''''''''''

Records can be processed back into documents, typically in a different
form, using Transformers::

    >>> dctxr = db.get_object(session, 'DublinCoreTxr')
    >>> doc = dctxr.process_record(session, rec)


And you can get the data from the document with get\_raw()::

    >>> doc.get_raw(session)
    '<?xml version="1.0"?>...


This transformer uses XSLT, which is common, but other transformers are
equally possible.

It is also possible to iterate through stores. This is useful for adding
new indexes or otherwise processing all of the data without reloading
it.

First find our index, and the indexStore::

    >>> idx = db.get_object(session, 'idx-creationDate')


Then start indexing for just that index, step through each record, and
then commit the terms extracted::

    >>> idxStore.begin_indexing(session, idx)
    >>> for rec in recStore:
    ...     idx.index_record(session, rec)
    recordStore/...
    >>> idxStore.commit_indexing(session, idx)


Indexes (Looking Under the Hood)
''''''''''''''''''''''''''''''''

Configuring Indexes, and the processing required to populate them
requires some further object types, such as Selectors, Extractors,
Tokenizers and TokenMergers. Of course, one would normally configure
these for each index in the database and the code in the examples below
would normally be executed automatically. However it can sometimes be
useful to get at the objects and play around with them manually,
particularly when starting out to find out what they do, or figure out
why things didn't work as expected, and Cheshire3 makes this possible.

Selector objects are configured with one or more locations from which
data should be selected from the Record. Most commonly (for XML data at
least) these will use XPaths. A selector returns a list of lists, one
for each configured location::

    >>> xp1 = db.get_object(session, 'identifierXPathSelector')
    >>> rec = recStore.fetch_record(session, 1)
    >>> elems = xp1.process_record(session, rec)
    >>> elems
    [[<Element identifier at ...


However we need the text from the matching elements rather than the XML
elements themselves. This is achieved using an Extractor, which
processes the list of lists returned by a Selector and returns a
dictionary a.k.a an associative array or hash::

    >>> extr = db.get_object(session, 'SimpleExtractor')
    >>> hash = extr.process_xpathResult(session, elems)
    >>> hash
    {'oai:CiteSeerPSU:2 ': {'text': 'oai:CiteSeerPSU:2 ', ...


And then we'll want to normalize the results a bit. For example we can
make everything lowercase::

    >>> n = db.get_object(session, 'CaseNormalizer')
    >>> h2 = n.process_hash(session, h)
    >>> h2
    {'oai:citeseerpsu:2 ': {'text': 'oai:citeseerpsu:2 ', ...


And note the extra space on the end of the identifier...::

    >>> s = db.get_object(session, 'SpaceNormalizer')
    >>> h3 = s.process_hash(session, h2)
    >>> h3
    {'oai:citeseerpsu:2': {'text': 'oai:citeseerpsu:2',...


Now the extracted and normalized data is ready to be stored in the
index!

This is fine if you want to just store strings, but most searches will
probably be at word or token level. Let's get the abstract text from the
record::

    >>> xp2 = db.get_object(session, 'textXPathSelector')
    >>> elems = xp2.process_record(session, rec)
    >>> elems
    [[<Element {http://purl.org/dc/elements/1.1/}description ...


Note the {...} bit ... that's lxml's representation of a namespace, and
needs to be included in the configuration for the xpath in the
:py:class:`~cheshire3.baseObjects.Selector`.::

    >>> extractor = db.get_object(session, 'ProxExtractor')
    >>> hash = extractor.process_xpathResult(session, elems)
    >>> hash
    {'The Graham scan is a fundamental backtracking...


:py:class:`~cheshire3.extractor.ProxExtractor` records where in the record the
text came from, but otherwise just extracts the text from the elements. We now
need to split it up into words, a process called tokenization::

    >>> tokenizer = db.get_object(session, 'RegexpFindTokenizer')
    >>> hash2 = tokenizer.process_hash(session, hash)
    >>> h
    {'The Graham scan is a fundamental backtracking...


Although the key at the beginning looks the same, the value is now a
list of tokens from the key, in order. We then have to merge those
tokens together, such that we have 'the' as the key, and the value has
the locations of that type::

    >>> tokenMerger = db.get_object(session, 'ProxTokenMerger')
    >>> hash3 = tokenMerger.process_hash(session, hash2)
    >>> hash3
    {'show': {'text': 'show', 'occurences': 1, 'positions': [12, 41]},...


After token merging, the multiple terms are ready to be stored in the
index!


.. Links
.. _Python: http://www.python.org/
.. _Lxml: http://lxml.de/
.. _CQL: http://www.loc.gov/standards/sru/specs/cql.html
.. _`mod_wsgi`: http://code.google.com/p/modwsgi/
.. _SRU: http://www.loc.gov/standards/sru/
