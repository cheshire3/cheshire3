Cheshire3 Commands Reference
============================

Introduction
------------

This page describes the Cheshire3 command line utilities, their intended
purpose, and options.

Examples of their use can be found in the
:doc:`Command-line UI Tutorial </tutorial/commands>`.


``cheshire3``
-------------

.. program:: cheshire3

Cheshire3 interactive interpreter.

This wraps the main Python interpreter to ensure that Cheshire3 architecture
is initialized. It can be used to execute a custom :option:`script` or just
drop you into the interactive console.

:py:data:`session` and :py:data:`server` variable will be created
automatically, as will a :py:data:`db` object if you ran the script from
inside a Cheshire3 database directory, or provided a database identifier
using the :option:`cheshire3 --database` option. These variables will
correspond to instances of :py:class:`~cheshire3.baseObjects.Session`,
:py:class:`~cheshire3.baseObjects.Server` and
:py:class:`~cheshire3.baseObjects.Database` respectively.

.. option:: script

   Run the commands in the script inside the current cheshire3
   environment. If script is not provided it will drop you into an interactive
   console (very similar the the native Python interpreter.) You can also tell
   it to drop into interactive mode after executing your script using the
   :option:`--interactive` option.

.. option:: -h, --help

   show help message and exit

.. option:: -s <PATH>, --server-config <PATH>

   Path to :py:class:`~cheshire3.baseObjects.Server` configuration file.
   Defaults to the default :py:class:`~cheshire.baseObjects.Server`
   configuration included in the distribution.

.. option:: -d <DATABASE>, --database <DATABASE>

   Identifier of the :py:class:`~cheshire3.baseObjects.Database`

.. option:: --interactive

   Drop into interactive console after running :option:`script`. If no
   :option:`script` is provided, interactive mode is the default.


``cheshire3-init``
------------------

.. program:: cheshire3-init

Initialize a Cheshire3 :py:class:`~cheshire3.baseObjects.Database` with some
generic configurations.

.. option:: DIRECTORY

   name of directory in which to init the
   :py:class:`~cheshire3.baseObjects.Database`. Defaults to the current
   working directory.

.. option:: -h, --help

   show help message and exit

.. option:: -s <PATH>, --server-config <PATH>

   Path to :py:class:`~cheshire3.baseObjects.Server` configuration file.
   Defaults to the default :py:class:`~cheshire.baseObjects.Server`
   configuration included in the distribution.

.. option:: -d <DATABASE>, --database <DATABASE>

   Identifier of the :py:class:`~cheshire3.baseObjects.Database` to init.
   Default to db_<database-directory-name>.

.. option:: -t <TITLE>, --title <TITLE>

   Title for the Cheshire3 :py:class:`~cheshire3.baseObjects.Database` to init.
   This wil be inserted into the :ref:`config-docs` section of the generated
   configuration, and the
   :doc:`CQL Protocol Map configuration <config/protocolMap>`.

.. option:: -c <DESCRIPTION>, --description <DESCRIPTION>

   Description of the :py:class:`~cheshire3.baseObjects.Database` to init.
   This wil be inserted into the :ref:`config-docs` section of the generated
   configuration, and the
   :doc:`CQL Protocol Map configuration <config/protocolMap>`.

.. option:: -p <PORT>, --port <PORT>

   Port on which :py:class:`~cheshire3.baseObjects.Database` will be served via
   :abbr:`SRU (Search and Retrieve via URL)`.


``cheshire3-register``
----------------------

.. program:: cheshire3-register

Register a Cheshire3 :py:class:`~cheshire3.baseObjects.Database` config file
with the Cheshire3 :py:class:`~cheshire3.baseObjects.Server`.

.. option:: CONFIGFILE

   Path to configuration file for a :py:class:`~cheshire3.baseObjects.Database`
   to register with the Cheshire3 :py:class:`~cheshire3.baseObjects.Server`.
   Default: :file:`config.xml` in the current working directory.

.. option:: --help

   show help message and exit

.. option:: --server-config <PATH>

   Path to :py:class:`~cheshire3.baseObjects.Server` configuration file.
   Defaults to the default :py:class:`~cheshire.baseObjects.Server`
   configuration included in the distribution.


``cheshire3-load``
------------------

.. program:: cheshire3-load

Load data into a Cheshire3 :py:class:`~cheshire3.baseObjects.Database`.

.. option:: data

   Data to load into the :py:class:`~cheshire3.baseObjects.Database`.

.. option:: -h, --help

   show help message and exit

.. option:: -s <PATH>, --server-config <PATH>

   Path to :py:class:`~cheshire3.baseObjects.Server` configuration file.
   Defaults to the default :py:class:`~cheshire.baseObjects.Server`
   configuration included in the distribution.

.. option:: -d <DATABASE>, --database <DATABASE>

   Identifier of the :py:class:`~cheshire3.baseObjects.Database`

.. option:: -l <CACHE>, --cache-level <CACHE>

   Level of in memory caching to use when reading documents in. For details,
   see :ref:`tutorial-python-loadingdata`

.. option:: -f <FORMAT>, --format <FORMAT>

   Format of the data parameter. For details,
   see :ref:`tutorial-python-loadingdata`

.. option:: -t <TAGNAME>, --tagname <TAGNAME>

   The name of the tag which starts (and ends!) a record.
   This is useful for extracting sections of documents and ignoring the rest of
   the XML in the file.

.. option:: -c <CODEC>, --codec <CODEC>

   The name of the codec in which the data is encoded. Commonly ``ascii`` or
   ``utf-8``.


``cheshire3-search``
--------------------

.. program:: cheshire3-search

Search a Cheshire3 :py:class:`~cheshire3.baseObjects.Database`.

.. option:: query

   Query to execute on the :py:class:`~cheshire3.baseObjects.Database`.

.. option:: -h, --help

   show help message and exit

.. option:: --server-config <PATH>

   Path to :py:class:`~cheshire3.baseObjects.Server` configuration file.
   Defaults to the default :py:class:`~cheshire.baseObjects.Server`
   configuration included in the distribution.

.. option:: -d <DATABASE>, --database <DATABASE>

   Identifier of the :py:class:`~cheshire3.baseObjects.Database`

.. option:: -f <FORMAT>, --format <FORMAT>

   Format/language of query. default: :abbr:`CQL (Contextual Query Language)`

.. option:: -m <MAXIMUM>, --maximum-records <MAXIMUM>

   Maximum number of hits to display

.. option:: -s <START>, --start-record <START>

   Point in the resultSet to start from (enables result paging) first record in
   results = 1 (not 0)


``cheshire3-serve``
-------------------

.. program:: cheshire3-serve

Start a demo server to expose Cheshire3
:py:class:`~cheshire3.baseObjects.Database`\ s. via
:abbr:`SRU (Search and Retrieve via URL)`.

.. option:: -h, --help

   show help message and exit

.. option:: -s <PATH>, --server-config <PATH>

   Path to :py:class:`~cheshire3.baseObjects.Server` configuration file.
   Defaults to the default :py:class:`~cheshire.baseObjects.Server`
   configuration included in the distribution.

.. option:: --hostname <HOSTNAME>

   Name of host to listen on. Default is derived by inspection of local system

.. option:: -p <PORT>, --port <PORT>

   Number of port to listen on. Default: 8000

