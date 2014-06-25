CHANGES
=======

1.1.6 - Wednesday 25th June 2014
--------------------------------

ENHANCEMENTS
~~~~~~~~~~~~

* Unittests added for `web.queryFactory`

BUG FIXES
~~~~~~~~~

* Fix bug when generating CQL from HTML forms introduced in 1.1.5.


1.1.5 - Tuesday 24th June 2014
------------------------------

BUG FIXES
~~~~~~~~~

* Fix bug in phrase extraction when generating CQL from HTML forms.


1.1.4 - Friday 6th June 2014
----------------------------

BUG FIXES
~~~~~~~~~

* Update package, download and dependency links to avoid DNS problem causing
  builds to fail for Cheshire3 and packages dependent on it.


1.1.3 - Thursday 1st May 2014
-----------------------------

BUG FIXES
~~~~~~~~~

* Improved handling of deleted records:

  * Relevance score calculations no longer raise TypeError.

  * SRU supplies a surrogate diagnostic for deleted results.

  * OAI-PMH:

    * Checks RecordStore for deletion support, and reports this in the
      Identify response.

    * Includes an appropriate status in the header for deleted records.


1.1.2 - Monday 28th April 2014
------------------------------

BUG FIXES
~~~~~~~~~

* Don't mask errors due to a Logger being unavailable.

* Warn instead of error when a subconfig file is missing.

* Init additional tables used for linking in PostgreSQL base Stores.

* Avoid non-namespaced Records from inheriting the OAI-PMH namespace be
  prefixing the OAI-PMH namespace in responses.


1.1.1 - Monday 27th March 2014
------------------------------

ENHANCEMENTS
~~~~~~~~~~~~

* ``cheshire3-unregister`` command to unregister existing databases.


1.1.0 - Monday 17th March 2014
------------------------------

ENHANCEMENTS
~~~~~~~~~~~~

* Improved out-of-the-box indexing capabilities.

  * Support for a number of common file formats. This is achieved by
    preParsing to XML where possible, and wrapping all formats in METS.

    * PDF
    * HTML
    * plain-text
    * OpenDocument Format (LibreOffice, OpenOffice 3+)
    * Office Open XML (Microsoft Office 2007+ - docx, pptx, xlsx etc.)

  * Easily load and index data from an iRODS data grid.

  * Attempts to create title index entries by default.

  * Faster retrieval[*]_ by compressing stored records using the lz4
    algorithm to reduce read time from disk.

* Store low and high values for each Record when ``sortStore`` setting is
  given for an Index. This provides more intuitive results when ordering
  ResultSets.

* NLTK Integration enabling configuration of indexes for automatically
  extracted named entities. This feature can be enabled by installing
  cheshire3 with 'nlp' or 'textmining' extras, e.g.::

      pip install cheshire3[nlp] >= 1.1.0

* Improved speed, readability and security of ``sql`` sub-package through use
  of ``psycopg2``.

* Better support for custom OAI-PMH servers (available as part of 'web'
  extras).

.. [*] Faster retrieval assuming reasonable processing power (>=2.5GHz) and
       non solid-state storage.


BUG FIXES
~~~~~~~~~

* Fixed major bug with indexing on 64-bit platforms.

* Many more minor bug fixes.


TESTS
~~~~~

New regression unittests:

* Workflows
* ResultSets
* ResultSetStores
* Loggers
* Indexes

For fuller details see the `GitHub Issue Tracker
<https://github.com/cheshire3/cheshire3/issues?milestone=8&state=closed>`


1.0.16 - Thursday 10 October 2013
---------------------------------

ENHANCEMENTS
~~~~~~~~~~~~

* Usability improvements in the ``cheshire3`` interactive console.


BUG FIXES
~~~~~~~~~

* Fixed assumed end datetime for ranges in ``DateRangeTokenizer``


1.0.15 - Thursday 26 September 2013
-----------------------------------

BUG FIXES
~~~~~~~~~

* Fixed ``UnicodeDecodeError`` when logging errors in ``BdbIndexStore``


DOCUMENTATION
~~~~~~~~~~~~~

* Improved "Configuring Indexes" tutorial:

  * Fixed incorrect information regarding ``ProximityIndex``es.

  * Completed truncated section on ``sortStore`` setting.


1.0.14 - Monday 5 August 2013
-----------------------------

DOCUMENTATION
~~~~~~~~~~~~~

* Replaced documentation in docs/ folder with Sphinx-based documentation.


1.0.13 - Friday 7 June 2013
---------------------------

BUG FIXES
~~~~~~~~~

* Fixed typo in ``index.SimpleIndex.construct_resultSetItem``

  rsitype -> rsiType


1.0.12 - Monday 4 March 2013
----------------------------

BUG FIXES
~~~~~~~~~

* Fixed ResultSet ordering by XPath

* Fixed IndexError when Workflows log a zero-length message


1.0.11 - Tuesday 22 January 2013
--------------------------------

* Eventually fixed build bugs when discovering version number in setup.py
  Read in version from VERSION.txt instead of trying to import from package

* ``python setup.py test`` now works with Python 2.6


1.0.9, 1.0.10 - Monday 21 January 2013
--------------------------------------

BUG FIXES
~~~~~~~~~

* Attempts to fix build bugs when discovering version number in setup.py


1.0.9 - Tuesday 18 December 2012
--------------------------------

BUG FIXES
~~~~~~~~~

* Fixed typo in cheshire3.resultSet:

  ValueErorr -> ValueError

* Fixed mutable type default data argument to SimpleResultSet constructor


1.0.8 - Thursday 22 November 2012
---------------------------------

DOCUMENTATION
~~~~~~~~~~~~~

* Updated installations instructions in README.

* Added CHANGES file.


1.0.7 - Friday 16 November 2012
-------------------------------

BUG FIXES
~~~~~~~~~

* Fixed bug in serialization of ResultSet class for storage in
  cheshire3.sql.resultSetStore.


1.0.6 - Thursday 15 November 2012
---------------------------------

DOCUMENTATION
~~~~~~~~~~~~~

* Updated download URL in package info.


1.0.5 - Thursday 15 November 2012
---------------------------------

BUG FIXES
~~~~~~~~~

* cheshireVersion reinstated for backward compatibility.


1.0.4 - Friday 9 November 2012
------------------------------

BUG FIXES
~~~~~~~~~

* Fixed missing import of cheshire3.exceptions in
  cheshire3.sql.resultSetStore.


1.0.3 - Tuesday 6 November 2012
-------------------------------

BUG FIXES
~~~~~~~~~

* Fixed incorrect version number in package info which could break dependency
  version resolution.


1.0.2 - Tuesday 6 November 2012
-------------------------------

BUG FIXES
~~~~~~~~~

* Fixed missing import of CONFIG_NS in cheshire3.web.transformer.


1.0.1 - Thursday 6 September 2012
---------------------------------

ENHANCEMENTS
~~~~~~~~~~~~

* Allowed all configured paths to be specified relative to user's home
  directory (i.e. by use of ~/).

* Added an implementation agnostic XMLSyntaxError to cheshire3.exceptions.

BUG FIXES
~~~~~~~~~

* Fixed permission error bug in ``cheshire3-init`` and ``cheshire3-register``
  when Cheshire3 was installed as root. Solution creates a
  ``.cheshire3-server`` directory in the users home directory in which to
  create server-level config plugins, log files and persistent data stores.


1.0.0 - Thursday 9 August 2012
------------------------------

ENHANCEMENTS
~~~~~~~~~~~~

* Standardized installation process. Installable from PyPI_.

* Unittest suite for the majority of processing objects.

* Command-line UI

  * ``cheshire3-init``
  * ``cheshire3-load``
  * ``cheshire3-load``
  * ``cheshire3-search``
  * ``cheshire3-serve``


.. Links
.. _`PyPI`: http://pypi.python.org/pypi/cheshire3
.. _`psycopg2`: https://pypi.python.org/pypi/psycopg2
