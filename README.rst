Cheshire3
=========

25th June 2014 (2014-06-25)

.. image:: https://travis-ci.org/cheshire3/cheshire3.png?branch=master,develop
   :target: https://travis-ci.org/cheshire3/cheshire3?branch=master,develop
   :alt: Build Status


Contents
--------

-  `Description`_
-  `Authors`_
-  `Latest Version`_
-  `Installation`_
-  `Requirements / Dependencies`_

   -  `Additional / Optional Features`_

-  `Documentation`_
-  `Development`_
-  `Bugs, Feature requests etc.`_
-  `Licensing`_
-  `Examples`_

   -  `Command-line UI`_

      -  `Creating a new Database`_
      -  `Loading Data into the Database`_
      -  `Searching the Database`_
      -  `Exposing the Database via SRU`_

   -  `Python API`_

      -  `Initializing Cheshire3 Architecture`_

         - `Using the cheshire3 command`_

      -  `Loading Data`_

         -  `Pre-Processing (PreParsing)`_

      -  `Searching`_
      -  `Retrieving`_
      -  `Transforming Records`_
      -  `Indexes`_

         - `Browsing`_
         - `Facets and Filtering`_
         - `Looking Under The Hood`_


Description
-----------

Cheshire3 is a fast XML search engine, written in Python_ for
extensability and using C libraries for speed. Cheshire3 is feature
rich, including support for XML namespaces, unicode, a distributable
object oriented model and all the features expected of a digital library
system.

Standards are foremost, including SRU_ and CQL_, as well as Z39.50 and
OAI_. It is highly modular and configurable, enabling very specific needs
to be addressed with a minimum of effort. The API_ is stable and fully
documented, allowing easy third party development of components.

Given a set of documents records, Cheshire3 can extract data into one or
more indexes after processing with configurable workflows to add extra
normalization and processing. Once the indexes have been constructed, it
supports such operations as search, retrieve, browse and sort.

The abstract protocolHandler allows integration of Cheshire3 into any
environment that will support Python_. For example using Apache_ handlers
or WSGI_ applications, any interface from standard APIs like SRU_, Z39.50
and OAI_ (all included by default in the cheshire3.web sub-package), to
an online shop front can be provided.


Authors
-------

Cheshire3 Team at the `University of Liverpool`_:

-  Robert Sanderson
-  **John Harrison** john.harrison@liv.ac.uk
-  Catherine Smith
-  Jerome Fuselier

(Current maintainer in **bold**)


Latest Version
--------------

The latest stable version of Cheshire3 is available from `PyPi - the Python
Package Index`:

http://pypi.python.org/pypi/cheshire3/

Bleeding edge source code is under version control and available from the
`Cheshire3 GitHub repository`_:

http://github.com/cheshire3/cheshire3

Previously, source code was available from our own Subversion server. The SVN
repository is being kept alive for the time being as read-only, and best
efforts will be made to keep it up-to-date with the master (i.e.
stable/production) branch from the `Cheshire3 Git repository`. It is available
at:

http://svn.cheshire3.org/repos/cheshire3

Previous versions, including code + dependency bundles, and
auto-installation scripts are available from the `Cheshire3 download site`_:

http://www.cheshire3.org/download/


Installation
------------

The following guidelines assume that you administrative privileges on
the machine you're installing on. If this is not the case, then you
might need to use the option ``--user``. For more details, see:
http://docs.python.org/install/index.html#alternate-installation

**Users** (i.e. those not wanting to actually develop Cheshire3) have
several choices:

- pip_: ``pip install cheshire3``

- `easy_install`_: ``easy_install cheshire3``

- Install from source:

  1. Download a source code archive from one of:

     http://pypi.python.org/pypi/cheshire3

     http://cheshire3.org/download/lastest/src/

     http://github.com/cheshire3/cheshire3

  2. Unpack it:

     ``tar -xzf cheshire3-1.0.8.tar.gz``

  3. Go into the unpacked directory:

     ``cd cheshire3-1.0.8``

  4. Install:

     ``python setup.py install``


**Developers**:

We recommend that you use virtualenv_ to isolate your development environment
from system Python and any packages that may be installed there.

1. In GitHub_, fork the `Cheshire3 GitHub repository`_

2. Clone your fork of Cheshire3:

	``git clone git@github.com:<username>/cheshire3.git``

3. Install dependencies [#]_:

	``pip install -r requirements.txt``

4. Install Cheshire3 in develop / editable mode:

    ``pip install -e .``

5. Read the Development section of this README

.. [#] While step 4 should theoretically resolve dependencies, we've found it 
   more reliable to run this explicitly.


Requirements / Dependencies
---------------------------

Cheshire3 requires Python_ 2.6.0 or later. It has not yet been verified
as Python 3 compliant.

As of the version 1.0 release Cheshire3's python dependencies *should* be
resolved automatically by the standard Python package management
mechanisms (e.g. pip_, `easy_install`_, distribute_/setuptools_).

However on some systems, for example if installing on a machine without
network access, it may be necessary to manually install some 3rd party
dependencies. In such cases we would encourage you to download the
necessary Cheshire3 bundles from the `Cheshire3 download site`_ and install
them using the automated build scripts included. If the automated scripts
fail on your system, they should at least provide hints on how to resolve
the situation.

If you experience problems with dependencies, please get in touch via
the `GitHub issue tracker`_ or wiki_, and we'll do our best to help.


Additional / Optional Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Certain features within the `Cheshire3 Information Framework`_ will have
additional dependencies (e.g. web APIs will require a web application
server). We'll try to maintain an accurate list of these in the module
docstring of the ``__init__.py`` file in each sub-package.

The bundles available from the `Cheshire3 download site`_ should
continue to be a useful place to get hold of the source code for these
pre-requisites.


Documentation
-------------

Documentation is available hosted by `Read the Docs`_:
http://docs.cheshire3.org

Some additional, but possibly redundant and outdated documentation is
available on our website:
http://cheshire3.org/docs/

If you downloaded the source code, either as a tarball, or by checking
out the repository, you'll find a copy of the Sphinx based Documentation in
the local docs directory.

There is additional documentation for the source code in the form of
comments and docstrings. Documentation for most default object
configurations can be found within the ``<docs>`` tag in the config XML
for each object. We would encourage users to take advantage of this tag
to provide documentation for their own custom object configurations.


Development
-----------

This section is intended for those who are intending to develop code to
contribute back to Cheshire3.

The Cheshire3 code base, configurations and documentation are maintained
in the `Cheshire3 GitHub repository`_.

Development in the `Cheshire3 GitHub repository`_ will follow `Vincent
Driessen's branching model
<http://nvie.com/posts/a-successful-git-branching-model/>`_, and use
`git-flow <https://github.com/nvie/gitflow>`_ to facilitate this.

So your workflow should be something like:

1. Fork the GitHub repository

2. Clone your forked repository onto you local development machine

3. Fix bugs in the ``develop`` branch, or develop new features in your own
   ``feature`` branch and merge back into the ``develop`` branch.)

4. Push your changes back to you github fork

5. Issue a pull request

Developed code intended to be contributed back to Cheshire3 should
follow the recommendations made by the standard `Style Guide for Python
Code`_ (which includes the provision that guidelines may be ignored in
situations where following them would make the code less readable.)

Particular attention should be paid to documentation and source code
annotation (comments). All developed modules, functions, classes, and
methods should be documented in the source code. Newly configured
objects at the server level should be documented using the ``<docs>``
tag. Comments and Documentation should be accurate and up-to-date, and
should *never* contradict the code itself.


Bugs, Feature requests etc.
---------------------------

Bug reports, feature requests etc. should be made using the GitHub issue
tracker: https://github.com/cheshire3/cheshire3/issues


Licensing
---------

Copyright © 2005-2014, the `University of Liverpool`_. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

-  Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
-  Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
-  Neither the name of the `University of Liverpool`_ nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


MARC Utilities
~~~~~~~~~~~~~~

The following licensing conditions apply to the marc\_utils module
included in the Cheshire3 package. In the following statements, "This
file" and "the Software" should be understood to mean marc\_utils.py.

    This file should be available from
    http://www.pobox.com/~asl2/software/PyZ3950/ and is licensed under
    the X Consortium license: Copyright (c) 2001, Aaron S. Lav,
    asl2@pobox.com All rights reserved.

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation files
    (the "Software"), to deal in the Software without restriction,
    including without limitation the rights to use, copy, modify, merge,
    publish, distribute, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, provided
    that the above copyright notice(s) and this permission notice appear
    in all copies of the Software and that both the above copyright
    notice(s) and this permission notice appear in supporting
    documentation.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT OF THIRD PARTY RIGHTS. IN NO EVENT SHALL THE
    COPYRIGHT HOLDER OR HOLDERS INCLUDED IN THIS NOTICE BE LIABLE FOR
    ANY CLAIM, OR ANY SPECIAL INDIRECT OR CONSEQUENTIAL DAMAGES, OR ANY
    DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
    WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
    ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
    OF THIS SOFTWARE.

    Except as contained in this notice, the name of a copyright holder
    shall not be used in advertising or otherwise to promote the sale,
    use or other dealings in this Software without prior written
    authorization of the copyright holder.


Examples
--------

Command-line UI
~~~~~~~~~~~~~~~

Cheshire3 provides a number of command-line utilities to enable you to
get started creating databases, indexing and searching your data quickly.
All of these commands have full help available, including lists
of available options which can be accessed using the ``--help`` option.
e.g.::

    ``cheshire3 --help``


Creating a new Database
'''''''''''''''''''''''

``cheshire3-init [database-directory]``
   Initialize a database with some generic configurations in the given
   directory, or current directory if absent

Example 1: create database in a new sub-directory::

    $ cheshire3-init mydb

Example 2: create database in an existing directory::

    $ mkdir -p ~/dbs/mydb
    $ cheshire3-init ~/dbs/mydb
    
Example 3: create database in current working directory::

    $ mkdir -p ~/dbs/mydb
    $ cd ~/dbs/mydb
    $ cheshire3-init

Example 4: create database with descriptive information in a new
sub-directory::
    
    $ cheshire3-init --database=mydb --title="My Database" \
    --description="A Database of Documents" mydb


Loading Data into the Database
''''''''''''''''''''''''''''''

``cheshire3-load data``
   Load data into the current Cheshire3 database

Example 1: load data from a file::

    $ cheshire3-load path/to/file.xml

Example 2: load data from a directory::

    $ cheshire3-load path/to/directory

Example 3: load data from a URL::

    $ cheshire3-load http://www.example.com/index.html


Searching the Database
''''''''''''''''''''''

``cheshire3-search query``
   Search the current Cheshire3 database based on the parameters given
   in query

Example 1: search with a single keyword::

    $ cheshire3-search food

Example 2: search with a complex CQL_ query::

    $ cheshire3-search "cql.anywhere all/relevant food and \
    rec.creationDate > 2012-01-01"


Exposing the Database via SRU
'''''''''''''''''''''''''''''

``cheshire3-serve``
   Start a demo HTTP WSGI application server to serve configured databases
   via SRU

*Please Note* the HTTP server started is probably not sufficiently robust
for production use. You should consider using something like `mod_wsgi`_.

Example 1: start a demo HTTP WSGI server with default options::

    $ cheshire3-serve

Example 2: start a demo HTTP WSGI server, specifying host name and port
number::

    $ cheshire3-serve --host myhost.example.com --port 8080


Python API
~~~~~~~~~~

This section contains examples of using the Cheshire3 API_ from within
Python, for embedding Cheshire3 services within a Python enabled web
application framework, such as Django, CherryPy, `mod_wsgi`_ etc. or when
the command-line interface is simply insufficient.


Initializing Cheshire3 Architecture
'''''''''''''''''''''''''''''''''''

Initializing the Cheshire3 Architecture consists primarily of creating
instances of the following types within the `Cheshire3 Object Model`_:

Session
    An object representing the user session. It will be passed around amongst
    the processing objects to maintain details of the current environment.
    It stores, for example, user and identifier for the database currently in
    use.

Server
    A protocol neutral collection of databases, users and their dependent
    objects. It acts as an inital entry point for all requests and handles
    such things as user authentication, and global object configuration.


The first thing that we need to do is create a Session and build a Server.::

    >>> from cheshire3.baseObjects import Session
    >>> session = Session()

The Server looks after all of our objects, databases, indexes ...
everything. Its constructor takes session and one argument, the filename
of the top level configuration file. You could supply your own, or you can
find the filename of the default server configuration dynamically as
follows:::

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
database, in this case 'db\_test':::

    >>> session.database = 'db_test'


This is primarily for efficiency in the workflow processing (objects are
cached by their identifier, which might be duplicated for different
objects in different databases).

Another useful path to know is the database's default path:::

    >>> dfp = db.get_path(session, 'defaultPath')


**Note:** You can often avoid having to type all of the above boiler-plate code,
by `Using the cheshire3 command`_


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
variables will be created corresponding to instances of Session and Server
respectively.

Additionally, if you ran the script from inside a Cheshire3 Database
directory, or provided the Database identifier using the ``--database`` option,
the Database will be available as ``db``. The default RecordStore will also be
available as ``recordStore`` if it was possible to discover from the Database.


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
clear.::

    >>> recStore.clear(session)
    <cheshire3.recordStore.BdbRecordStore object...
    >>> db.clear_indexes(session)


First you should call db.begin\_indexing() in order to let the database
initialise anything it needs to before indexing starts. Ditto for the
record store.::

    >>> db.begin_indexing(session)
    >>> recStore.begin_storing(session)


Then you'll need to tell the document factory where it can find your
data:::

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
documents is to loop through the document factory:::

    >>> for doc in df:
    ...    rec = parser.process_document(session, doc)  # [1]
    ...    recStore.create_record(session, rec)         # [2]
    ...    db.add_record(session, rec)                  # [3]
    ...    db.index_record(session, rec)                # [4]
    recordStore/...


In this loop, we:

1. Use the Lxml Parser to create a record object.

2. Store the record in the recordStore. This assigns an identifier to it, by
   default a sequential integer.

3. Add the record to the database. This stores database level metadata such
   as how many words in total, how many records, average number of words per
   record, average number of bytes per record and so forth.

4. Index the record against all indexes known to the database - typically all
   indexes in the indexStore in the database's 'indexStore' path setting.

Then we need to ensure this data is commited to disk:::

    >>> recStore.commit_storing(session)
    >>> db.commit_metadata(session)


And, potentially taking longer, merge any temporary index files created:::

    >>> db.commit_indexing(session)


Pre-Processing (PreParsing)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

As often than not, documents will require some sort of pre-processing
step in order to ensure that they're valid XML in the schema that you
want them in. To do this, there are PreParser objects which take a
document and transform it into another document.

The simplest preParser takes raw text, escapes the entities and wraps it
in a element:::

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
and our internal language).::

    >>> qf = db.get_object(session, 'defaultQueryFactory')
    >>> qf
    <cheshire3.queryFactory.SimpleQueryFactory object ...


We can then use this factory to build queries for us:::

    >>> q = qf.get_query(session, 'c3.idx-text-kwd any "compute"')
    >>> q
    <cheshire3.cqlParser.SearchClause ...


And then use this parsed query to search the database:::

    >>> rs = db.search(session, q)
    >>> rs
    <cheshire3.resultSet.SimpleResultSet ...
    >>> len(rs)
    3


The 'rs' object here is a result set which acts much like a list. Each
entry in the result set is a ResultSetItem, which is a pointer to a
record.::

    >>> rs[0]
    Ptr:recordStore/1


Retrieving
''''''''''

Each result set item can fetch its record:::

    >>> rec = rs[0].fetch_record(session)
    >>> rec.recordStore, rec.id
    ('recordStore', 1)


Records can expose their data as xml:::

    >>> rec.get_xml(session)
    '<record>...


As SAX events:::

    >>> rec.get_sax(session)
    ["4 None, 'record', 'record', {}...


Or as DOM nodes, in this case using the Lxml Etree API:::

    >>> rec.get_dom(session)
    <Element record at ...


You can also use XPath expressions on them:::

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


And you can get the data from the document with get\_raw():::

    >>> doc.get_raw(session)
    '<?xml version="1.0"?>...


This transformer uses XSLT, which is common, but other transformers are
equally possible.


Indexes
'''''''

While `Searching`_ is the primary use of an Index, there are other API methods
that can be used to get information from an Index in slightly different forms
that can be useful when developing a user interface. This section describes
those API methods and then shows how to *really* get your hands dirty by
`Looking Under the Hood`_ and getting direct access to some of the object types
that are used to process data within an Index.


Browsing
^^^^^^^^

It is possible to browse through all terms in an index, just like reading the
index in a book. This is usualy done through ``scan`` method of a Database
object, so as to make use of the normal Index resolution machinery::

    >>> qf = db.get_object(session, 'defaultQueryFactory')
    >>> query = qf.get_query(session, 'dc.title = ""')
    >>> terms = db.scan(session, query, nTerms=25, direction=">=")


``terms`` will be a list of no more than 25 items representing the terms
from the start of the Index that was resolved from the context `dc.title`
(by convention the Dublin-Core definition of "title"; the title of a piece of
work.) Each item in ``terms`` is a 2-item list:

0. The unicode representation of the term
1. A 3-item list:
   0. internal numeric term id
   1. number of records the term appears in
   2. total number of occurrences of the term across the database

e.g.::

    [u"zen and the art of motorcycle maintenance", [12345, 2, 3]]


It is also possible to use the `scan` method of an Index object directly::

    >>> idx = db.get_object(session, 'idx-title')
    >>> terms = idx.scan(session, query, nTerms=25, direction=">=")


The resulting ``terms`` will be the same as when obtained through the ``scan``
method of the Database object.


Facets and Filtering
^^^^^^^^^^^^^^^^^^^^

Assuming that you have configured your Index with the setting `vectors` set to
`1`, it is possible to obtain search facets for the Index. That is to say that
given a ResultSet obtained from a `Searching`_, one can obtain a list of the terms
that occur within the Records in that ResultSet. This list can be used to
present a search user with options for refining their search.::

    >>> qf = db.get_object(session, 'defaultQueryFactory')
    >>> query = qf.get_query(session, 'c3.idx-text-kwd any "compute"')
    >>> rs = db.search(session, query)
    >>> idx = db.get_object(session, 'idx-author')
    >>> facets = idx.facets(session, rs, nTerms=5)


The resulting ``facets`` will be a list representing the 5 terms that occur in
the highest number of Records within the ResultSet. Setting ``nTerms`` to ``0``
(or omitting it) will return all terms within the Index for the Records within
the ResultSet. Each item in ``terms`` is a 2-item list:

0. The unicode representation of the term
1. A 3-item list:
   0. internal numeric term id
   1. number of records the term appears in
   2. total number of occurrences of the term across the database

e.g.::

    [u"Crichton, Michael", [54321, 3, 24]]


Looking Under the Hood
^^^^^^^^^^^^^^^^^^^^^^

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
for each configured location.::

    >>> xp1 = db.get_object(session, 'identifierXPathSelector')
    >>> rec = recStore.fetch_record(session, 1)
    >>> elems = xp1.process_record(session, rec)
    >>> elems
    [[<Element identifier at ...

However we need the text from the matching elements rather than the XML
elements themselves. This is achieved using an Extractor, which
processes the list of lists returned by a Selector and returns a
doctionary a.k.a an associative array or hash:::

    >>> extr = db.get_object(session, 'SimpleExtractor')
    >>> hash = extr.process_xpathResult(session, elems)
    >>> hash
    {'oai:CiteSeerPSU:2 ': {'text': 'oai:CiteSeerPSU:2 ', ...


And then we'll want to normalize the results a bit. For example we can
make everything lowercase:::

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
record:::

    >>> xp2 = db.get_object(session, 'textXPathSelector')
    >>> elems = xp2.process_record(session, rec)
    >>> elems
    [[<Element {http://purl.org/dc/elements/1.1/}description ...


Note the {...} bit ... that's lxml's representation of a namespace, and
needs to be included in the configuration for the xpath in the Selector.::

    >>> extractor = db.get_object(session, 'ProxExtractor')
    >>> hash = extractor.process_xpathResult(session, elems)
    >>> hash
    {'The Graham scan is a fundamental backtracking...


ProxExtractor records where in the record the text came from, but
otherwise just extracts the text from the elements. We now need to split
it up into words, a process called tokenization.::

    >>> tokenizer = db.get_object(session, 'RegexpFindTokenizer')
    >>> hash2 = tokenizer.process_hash(session, hash)
    >>> h
    {'The Graham scan is a fundamental backtracking...


Although the key at the beginning looks the same, the value is now a
list of tokens from the key, in order. We then have to merge those
tokens together, such that we have 'the' as the key, and the value has
the locations of that type.::

    >>> tokenMerger = db.get_object(session, 'ProxTokenMerger')
    >>> hash3 = tokenMerger.process_hash(session, hash2)
    >>> hash3
    {'show': {'text': 'show', 'occurences': 1, 'positions': [12, 41]},...


After token merging, the multiple terms are ready to be stored in the
index!


It is also possible to iterate through stores. This is useful for adding
new indexes or otherwise processing all of the data without reloading
it.

First find our index, and the indexStore:::

    >>> idx = db.get_object(session, 'idx-modificationDate')
    >>> idxStore = idx.get_path(session, 'indexStore')


Then start indexing for just that index, step through each record, and
then commit the terms extracted.::

    >>> idxStore.begin_indexing(session, idx)
    >>> for rec in recStore:
    ...     idx.index_record(session, rec)
    recordStore/...   
    >>> idxStore.commit_indexing(session, idx)


This example will have the effect of 'touching' each Record, as if it had
been updated. This might be useful if for example, you knew that your Database
was being harvested periodically using OAI-PMH, and you wanted to indicate that
all Records should be reharvested next time.


.. Links
.. _Python: http://www.python.org/
.. _`Python Package Index`: http://pypi.python.org/pypi/cheshire3
.. _Apache: http://httpd.apache.org 
.. _`University of Liverpool`: http://www.liv.ac.uk
.. _`Cheshire3 Information Framework`: http://cheshire3.org
.. _`Cheshire3 Object Model`: http://cheshire3.org/docs/objects/
.. _`Cheshire3 download site`: http://download.cheshire3.org/
.. _API: http://cheshire3.org/docs/objects/api/
.. _`Cheshire3 GitHub repository`: http://github.com/cheshire3/cheshire3
.. _`GitHub issue tracker`: http://github.com/cheshire3/cheshire3/issues
.. _wiki: http://github.com/cheshire3/cheshire3/wiki
.. _GitHub: http://github.com
.. _pip: http://www.pip-installer.org/en/latest/index.html
.. _distribute: http://packages.python.org/distribute/
.. _`easy_install`: http://packages.python.org/distribute/easy_install.html
.. _setuptools: http://pypi.python.org/pypi/setuptools/
.. _`Style Guide for Python Code`: http://www.python.org/dev/peps/pep-0008/
.. _WSGI: http://wsgi.org
.. _`mod_wsgi`: http://code.google.com/p/modwsgi/
.. _SRU: http://www.loc.gov/standards/sru/
.. _CQL: http://www.loc.gov/standards/sru/specs/cql.html
.. _OAI: http://www.openarchives.org/pmh/
.. _virtualenv: http://www.virtualenv.org/en/latest/
.. _`Read the Docs`: https://readthedocs.org/
