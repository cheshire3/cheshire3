Cheshire3 Tutorials - Command-line UI
=====================================

Cheshire3 provides a number of command-line utilities to enable you to
get started creating databases, indexing and searching your data quickly.
All of these commands have full help available, including lists
of available options which can be accessed using the ``--help`` option.
e.g. ::

    ``cheshire3 --help``


Creating a new Database
'''''''''''''''''''''''

``cheshire3-init [database-directory]``
   Initialize a database with some generic configurations in the given
   directory, or current directory if absent

Example 1: create database in a new sub-directory ::

    $ cheshire3-init mydb


Example 2: create database in an existing directory ::

    $ mkdir -p ~/dbs/mydb
    $ cheshire3-init ~/dbs/mydb


Example 3: create database in current working directory ::

    $ mkdir -p ~/dbs/mydb
    $ cd ~/dbs/mydb
    $ cheshire3-init


Example 4: create database with descriptive information in a new
sub-directory ::
    
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

Example 1: search with a single keyword ::

    $ cheshire3-search food


Example 2: search with a complex CQL_ query ::

    $ cheshire3-search "cql.anywhere all/relevant food and \
    rec.creationDate > 2012-01-01"


Exposing the Database via SRU
'''''''''''''''''''''''''''''

``cheshire3-serve``
   Start a demo HTTP WSGI application server to serve configured databases
   via SRU_

*Please Note* the HTTP server started is probably not sufficiently robust
for production use. You should consider using something like `mod_wsgi`_.

Example 1: start a demo HTTP WSGI server with default options ::

    $ cheshire3-serve


Example 2: start a demo HTTP WSGI server, specifying host name and port
number ::

    $ cheshire3-serve --host myhost.example.com --port 8080


.. Links
.. _`mod_wsgi`: http://code.google.com/p/modwsgi/
.. _SRU: http://www.loc.gov/standards/sru/
.. _CQL: http://www.loc.gov/standards/sru/specs/cql.html