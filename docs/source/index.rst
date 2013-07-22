.. Cheshire3 documentation master file, created by
   sphinx-quickstart on Mon Jul 22 12:08:43 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Cheshire3's documentation!
=====================================

Contents:

.. toctree::
   :maxdepth: 1

   Installation <install>
   Command-line UI <commands>
   Tutorial <tutorial>
   Configuration <config/index>
   troubleshooting


Capabilities
------------

What Cheshire3 can do:

* Create a database of your documents, and put a search engine on top.

* Index the full text of those documents, and allow you to set up your own
  indexes of specific fields within structured documents.
  
* Set up these indexes to extract and normalize the data exactly the way you
  need (e.g. make an index of people's names as keywords, strip off possessive
  apostrophes, treat all names as lowercase)

* Search the indexes you've set up to quickly find the document you want. When
  searching indexes the search terms are treated the same way as the data, so a
  user doesn't need to know what normalization you've applied, they'll just get
  the correct results!

* Advanced boolean search logic ('AND', 'OR', 'NOT') as well as proximity,
  phrase and range searching (e.g. for date/time periods).

* Return shared 'facets' of your search results to indicate ways in which a
  search could be refined.

* Scan through all terms in an index, just like reading the index in a book.

* Add international standard webservice APIs to your database

* Use an existing Relation Database Management Systems as a source of
  documents.

[More Coming]




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

