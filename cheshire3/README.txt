
This is some documentation, also used for testing!

=== ABOUT ===

Cheshire3 is a fast XML search engine, written in Python for extensability and using C libraries for speed. Cheshire3 is feature rich, including support for XML namespaces, unicode, a distributable object oriented model and all the features expected of a digital library system.

Standards are foremost, including SRW/U and CQL, as well as Z39.50 and OAI (requires cheshire3.web sub-package). It is highly modular and configurable, enabling very specific needs to be addressed with a minimum of effort. The API is stable and fully documented, allowing easy third party development of components.

Given a set of records, Cheshire3 can extract data into one or more indexes after processing with configurable workflows to add extra normalisation and processing. Once the indexes have been constructed, it supports such operations as search, retrieve, browse and sort.

Cheshire3\'s extensive use of third party C-libraries (e.g. BerkeleyDB, libxml) may involve installing some pre-requisites, and we recommend that you download the necessary Cheshire3 packages from http://www.cheshire3.org/download/ and install them using the scripts provided, rather than just installing this package as a pure python module distribution.

By installing the additional cheshire3.web sub-package, and using Apache handlers, any interface from a shop front, to SRU, Z39.50 to OAI can be provided (all included by default), but the abstract protocolHandler allows integration into any environment that will support Python.

=== INITIALIZATION ===

If you are running from the Subversion repository, you need to do:

   >>> import sys
   >>> sys.path.insert(1, "/home/cheshire/cheshire3/code")

All scripts should start with the following initialization pattern:

   >>> from cheshire3.baseObjects import Session
   >>> from cheshire3.server import SimpleServer
   >>> session = Session()

If you want to include patched files, there is some black magic that will
look for newer versions in a different path.  Useful for development
purposes or distributing patches to working systems without reinstalling the
module.  To start the patch:

   >>> import cheshire3
   >>> cheshire3.patch()

And to turn it off again:

   >>> import cheshire3
   >>> cheshire3.patch(False)

The first thing that we need to do is build a server.  The server looks
after all of our objects, databases, indexes ... everything.

Its constructor takes session and one argument, the filename of the top
level configuration file.  You can find it dynamically as follows:

   >>> import os
   >>> c3home = os.environ.get('C3HOME', '')
   >>> serverConfig = os.path.join(c3home, 'cheshire3', 'configs', 'serverConfig.xml') if c3home else "/home/cheshire/cheshire3/configs/serverConfig.xml"
   >>> serv = SimpleServer(session, serverConfig)
   >>> serv
   <cheshire3.server.SimpleServer object...

The next thing you'll probably want to do is get a database.

   >>> db = serv.get_object(session, 'db_test')
   >>> db
   <cheshire3.database.SimpleDatabase object...

After this you MUST set session.database to the identifier for your
database, in this case 'db_test':

   >>> session.database = 'db_test'
   
This is primarily for efficiency in the workflow processing (objects are
cached by their identifier, which might be duplicated for different objects
in different databases).  More on workflows later.

Another useful path to know is the database's default path:

   >>> dfp = db.get_path(session, 'defaultPath')


=== LOADING DATA ===

In order to load data into your database you'll need a document
factory to find your documents, a parser to parse the XML and a record store
to put the parsed XML into.
The most commonly used are defaultDocumentFactory and LxmlParser.  Each
database needs its own record store.

   >>> df = db.get_object(session, "defaultDocumentFactory")
   >>> parser = db.get_object(session, "LxmlParser")
   >>> recStore = db.get_object(session, "recordStore")

Before we get started, we need to make sure that the stores are all clear.
   >>> recStore.clear(session)
   <cheshire3.recordStore.BdbRecordStore object...
   >>> db.clear_indexes(session)
   
First you should call db.begin_indexing() in order to let the database
initialise anything before indexing starts.  Ditto for the record store.

   >>> idxStore = db.get_object(session, 'indexStore')   
   >>> db.begin_indexing(session)
   >>> recStore.begin_storing(session)   

Then you'll need to tell the document factory where it can find your data:

   >>> df.load(session, 'data', cache=0, format='dir')
   <cheshire3.documentFactory.SimpleDocumentFactory object...

DocumentFactory's load function takes session, plus 
  * data -- this could be a filename, a directory name, the data as a 
            string, a URL to the data and so forth.
            If data ends in [(numA):(numB)], and the preceding string is a
            filename, then the data will be extracted from bytes numA
            through to numB.
  * cache -- Normally 0 (don't cache, yield documents as soon as discovered)
             Also 1:  Cache byte offsets in the file
	     And 2:   Cache full documents.
  * format -- The format of the data parameter. Many options, the most 
 	      common are:	     
              * xml  -- xml file. Can have multiple records in single file.
	      * dir  -- a directory containing files to load
	      * tar  -- a tar file containing files to load
	      * zip  -- a zip file containing files to load
	      * marc -- a file with MARC records (library catalogue data)
	      * http -- a base HTTP URL to retrieve
  * tagName -- the name of the tag which starts (and ends!) a record.
               This is useful for extracting sections of documents and
               ignoring the rest of the XML in the file.
	       Medline, Wikipedia and ModsCollection do this for example.
  * codec -- the name of the codec in which the data is encoded. Normally
             'ascii' or 'utf-8'
	       
You'll note above that the call to load returns itself. This is because the
document factory acts as an iterator.  The easiest way to get to your
documents is to loop through the document factory:

   >>> for doc in df:
   ...    rec = parser.process_document(session, doc)  # [1]
   ...    recStore.create_record(session, rec)         # [2]
   ...    db.add_record(session, rec)                  # [3]
   ...    db.index_record(session, rec)                # [4]
   recordStore/...

In this loop, we first use the Lxml Parser to create a record object in [1].  
Then in [2], we store the record in the recordStore.  This assigns an
identifier to it, by default a sequential integer.
In [3] we add the record to the database. This stores database level
metadata such as how many words in total, how many records, average number
of words per record, average number of bytes per record and so forth.
The last line, [4], indexes the record against all indexes known to the
database -- typically all indexes in the indexStore in the database's
'indexStore' path setting.

Then we need to ensure this data is commited to disk:

   >>> recStore.commit_storing(session)
   >>> db.commit_metadata(session)

And, potentially taking longer, load the temporary index files created:

   >>> db.commit_indexing(session)


=== SEARCHING ===

In order to allow for translation between query languages (if possible) we
have a query factory, which defaults to CQL (SRU's query language, and our
internal language).

   >>> qf = db.get_object(session, 'defaultQueryFactory')
   >>> qf
   <cheshire3.queryFactory.SimpleQueryFactory object ...

We can then use this factory to build queries for us:

   >>> q = qf.get_query(session, 'c3.idx-text-kwd any "compute"')
   >>> q
   <cheshire3.cqlParser.SearchClause ...
   
And then use this parsed query to search the database:

   >>> rs = db.search(session, q)
   >>> rs
   <cheshire3.resultSet.SimpleResultSet ...
   >>> len(rs)
   3
   
The 'rs' object here is a result set which acts much like a list.  Each entry
in the result set is a ResultSetItem, which is a pointer to a record.

   >>> rs[0]
   Ptr:recordStore/1

Each result set item can fetch its record:

   >>> rec = rs[0].fetch_record(session)
   >>> rec.recordStore, rec.id
   ('recordStore', 1)

Records can expose their data as xml:
   >>> rec.get_xml(session)
   '<record>...
   
As SAX events:
   >>> rec.get_sax(session)
   ["4 None, 'record', 'record', {}...
   
Or as DOM nodes, in this case using the Lxml API:
   >>> rec.get_dom(session)
   <Element record at ...

You can also use XPath expressions on them:
   >>> rec.process_xpath(session, '/record/header/identifier')
   [<Element identifier at ...
   >>> rec.process_xpath(session, '/record/header/identifier/text()')
   ['oai:CiteSeerPSU:2']

Records can be processed back into documents, typically in a different form,
using Transformers:

   >>> dctxr = db.get_object(session, 'DublinCoreTxr')
   >>> doc = dctxr.process_record(session, rec)

And you can get the data from the document with get_raw()

   >>> doc.get_raw(session)
   '<?xml version="1.0"?>...
   
This transformer uses XSLT, which is common, but other transformers are
equally possible.

It is also possible to iterate through stores.  This is useful for adding
new indexes or otherwise processing all of the data without reloading it.

First find our index, and the indexStore:
   >>> idx = db.get_object(session, 'idx-creationDate')

Then start indexing for just that index, step through each record, and then
commit the terms extracted.

   >>> idxStore.begin_indexing(session, idx)
   >>> for rec in recStore:
   ...     idx.index_record(session, rec)
   recordStore/...   
   >>> idxStore.commit_indexing(session, idx)


More often than not, documents will require some sort of pre-processing step
in order to ensure that they're valid XML in the schema that you want them in.
To do this, there are PreParser objects which take a document and transform
it into another document.

The simplest preParser takes raw text, escapes the entities and wraps it in
a <data> element:

   >>> from cheshire3.document import StringDocument
   >>> doc = StringDocument("This is some raw text with an & and a < and a >.")
   >>> pp = db.get_object(session, 'TxtToXmlPreParser')
   >>> doc2 = pp.process_document(session, doc)
   >>> doc2.get_raw(session)
   '<data>This is some raw text with an &amp; and a &lt; and a &gt;.</data>'


Configuring the processing for indexes requires the use of some further
object types.

First, there are xpath processor objects, which maintain one or more xpaths
to apply to the record.

   >>> xp1 = db.get_object(session, 'identifierXPath')
   >>> rec = recStore.fetch_record(session, 1)
   >>> elems = xp1.process_record(session, rec)
   >>> elems
   [[<Element identifier at ...

However we need to get the text from the matching elements.  This is done by
an Extractor object:

   >>> extr = db.get_object(session, 'SimpleExtractor')
   >>> h = extr.process_xpathResult(session, elems)
   >>> h
   {'oai:CiteSeerPSU:2 ': {'text': 'oai:CiteSeerPSU:2 ', ...

And then we'll want to normalize the results a bit. For example we can make
everything lowercase:

   >>> n = db.get_object(session, 'CaseNormalizer')
   >>> h2 = n.process_hash(session, h)
   >>> h2
   {'oai:citeseerpsu:2 ': {'text': 'oai:citeseerpsu:2 ', ...

And note the extra space on the end of the identifier...

   >>> s = db.get_object(session, 'SpaceNormalizer')
   >>> h3 = s.process_hash(session, h2)
   >>> h3
   {'oai:citeseerpsu:2': {'text': 'oai:citeseerpsu:2',...

Now it's ready to be stored in the index!

This is fine if you want to just store strings, but most searches should be
at a word level.  Let's get the abstract text from the record:

   >>> xp2 = db.get_object(session, 'textXPath')
   >>> elems = xp2.process_record(session, rec)
   >>> elems
   [[<Element {http://purl.org/dc/elements/1.1/}description ...

Note the {...} bit ... that's lxml's representation of a namespace, and
needs to be put into the configuration for the xpathProcessor.

   >>> e = db.get_object(session, 'ProxExtractor')
   >>> h = e.process_xpathResult(session, elems)
   >>> h
   {'The Graham scan is a fundamental backtracking...
   
ProxExtractor records where in the record the text came from, but otherwise
just extracts the text from the elements.  We now need to split it up into
words, a process called tokenization.

   >>> t = db.get_object(session, 'RegexpFindTokenizer')
   >>> h2 = t.process_hash(session, h)
   >>> h
   {'The Graham scan is a fundamental backtracking...
   
Although the beginning looks the same, the value of the hash key is the list
of tokens from the key, in order.
We then have to merge those tokens together, such that we have 'the' as the
key, and the value has the locations of that type.

   >>> tm = db.get_object(session, 'ProxTokenMerger')
   >>> h2 = t.process_hash(session, h)
   >>> h3 = tm.process_hash(session, h2)
   >>> h3
   {'show': {'text': 'show', 'occurences': 1, 'positions': [12, 41]},...

And after some normalization (as above), the terms will be ready to be put
into the index.

