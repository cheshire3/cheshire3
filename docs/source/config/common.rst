Common Configurations
=====================

.. highlight:: xml
   :linenothreshold: 5

Introduction
------------

Below are the most commonly required or used paths, objects and settings in
Cheshire3 configuration files.


Paths
-----

.. _config-common-defaultPath:

defaultPath
    A default path to be prepended to all other paths in the object and below

metadataPath
    Used to point to a database file or directory for metadata concerning the
    object
                
databasePath
    Used in store objects to point to a database file or directory

tempPath
    For when temporary file(s) are required (e.g. for an
    :py:class:`~cheshire3.baseObjects.IndexStore` .)

schemaPath
    Used in Parsers to point to a validation document (eg xsd, dtd, rng)

xsltPath
    Used in :py:class:`~cheshire3.transformer.LxmlXsltTransformer` to point to
    the :abbr:`XSLT (Extensible Stylesheet Language Transformations)` document
    to use.

sortPath
    Used in an :py:class:`~cheshire3.baseObjects.IndexStore` to refer to the
    local unix :command:`sort` utility.


Settings
--------

log
    This contains a space separated list of function names to log on
    invocation. The `functionLogger` object referenced in
    :ref:`\<paths\> <config-paths>` will be used to do this.

digest
    Used in recordStores to name a digest algorithm to determine if a record
    is already present in the store. Currently supported are 'sha' (which
    results in sha-1) and 'md5'.
