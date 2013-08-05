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
   Tutorials <tutorial/index>
   Commands <commands>
   Configuration <config/index>
   Objects <objects/index>
   troubleshooting


Capabilities
------------

What Cheshire3 can do:

* Create a :py:class:`~cheshire3.baseObjects.Database` of your documents, and
  put a search engine on top.

* Index the full text of the documents in your
  :py:class:`~cheshire3.baseObjects.Database`, and allow you to define your own
  :py:class:`~cheshire3.baseObject.Index` of specific fields within each
  structured or semi-structured :py:class:`~cheshire3.baseObjects.Document` .

* Set up each :py:class:`~cheshire3.baseObject.Index` to extract and normalize
  the data exactly the way you need (e.g. make an index of people's names as
  keywords, strip off possessive apostrophes, treat all names as lowercase)

* Search your :py:class:`~cheshire3.baseObjects.Database` to quickly find the
  :py:class:`~cheshire3.baseObjects.Document` you want. When searching the
  :py:class:`~cheshire3.baseObjects.Database` the user's search terms are
  treated the same way as the data, so a user doesn't need to know what
  normalization you've applied, they'll just get the right results!

* Advanced boolean search logic ('AND', 'OR', 'NOT') as well as proximity,
  phrase and range searching (e.g. for date/time periods).

* Return shared 'facets' of your search results to indicate ways in which a
  search could be refined.

* Scan through all terms in an :py:class:`~cheshire3.baseObject.Index`, just
  like reading the index in a book.

* Add international standard webservice APIs to your database

* Use an existing Relation Database Management Systems as a source of
  documents.

[More Coming]


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

