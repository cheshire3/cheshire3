Cheshire3 Tutorials - Configuring Databases
===========================================

.. highlight:: xml
   :linenothreshold: 5


Introduction
------------

:py:class:`~cheshire3.baseObjects.Database`\ s are primarily collections of
:py:class:`~cheshire3.baseObjects.Record`\ s and
:py:class:`~cheshire3.baseObjects.Index`\ es along with the associated metadata
and objects required for processing the data.

Configuration is typically done in a single file, with all of the dependent
components included within it and stored in a directory devoted to just that
database. The file is normally called, simply, :file:`config.xml`.


.. _tutorials-database-example:

Example
-------

An example :py:class:`~cheshire3.baseObjects.Database` configuration::

    <config type="database" id="db_ead">
        <objectType>cheshire3.database.SimpleDatabase</objectType>
        <paths>
            <path type="defaultPath">dbs/ead</path>
            <path type="metadataPath">metadata.bdb</path>
            <path type="indexStoreList">eadIndexStore</path>
            <object type="recordStore" ref="eadRecordStore"/>
        </paths>
        <subConfigs>
        ...
        </subConfigs>
        <objects>
        ...
        </objects>
    </config>


.. _tutorials-database-explanation:

Explanation
-----------

In line 1 we open a new object, of type
:py:class:`~cheshire3.baseObjects.Database` with an identifier of ``db_ead``.
You should replace ``db_ead`` with the identifier you want for your
:py:class:`~cheshire3.baseObjects.Database`.

Line 2 defines the :ref:`config-objectType` of the
:py:class:`~cheshire3.baseObjects.Database` (which will normally be a class from
the :py:mod:`cheshire3.database` module). There is currently only one
recommended implementation, :py:class:`cheshire3.database.SimpleDatabase`, so
this line should be copied in verbatim, unless you have defined your own
sub-class of :py:class:`cheshire3.baseObjects.Database` (in which case you're
probably more advanced than the target audience for this tutorial!)

Lines 4 and 7 define three :ref:`config-path`\ s and one
:ref:`config-object`. To explain each in turn:

defaultPath
    the path to the directory where the database is being stored. It will be
    prepended to any further paths in the database or in any subsidiary object.

metadataPath
    the path to a datastore in which the database will keep its metadata. This
    includes things like the number of records, the average size or the records
    and so forth. As it's a file path, it would end up being
    :file:`dbs/ead/metdata.bdb` -- in other words, in the same directory as the
    rest of the database files.

indexStoreList
    a space separated list of references to all
    :py:class:`~cheshire3.baseObjects.IndexStore`\ s the
    :py:class:`~cheshire3.baseObjects.Database` will use. This is needed if we
    intend to index any :py:class:`~cheshire3.baseObjects.Record`\ s later, as
    it tells the :py:class:`~cheshire3.baseObjects.Database` which
    :py:class:`~cheshire3.baseObjects.IndexStore`\ s to register the
    :py:class:`~cheshire3.baseObjects.Record` in.

The :ref:`config-object` element refers to an object called ``eadRecordStore``
which is an instance of a :py:class:`~cheshire3.baseObjects.RecordStore`. This
is important for future :py:class:`~cheshire3.baseObjects.Workflow`\ s, so that
the :py:class:`~cheshire3.baseObjects.Database` knows which
:py:class:`~cheshire3.baseObjects.RecordStore` it should put
:py:class:`~cheshire3.baseObjects.Record`\ s into by default.

Line 10 would be expanded to contain a series of :ref:`config-subConfig`
elements, each of which is the configuration for a subsidiary object such as
the :py:class:`~cheshire3.baseObjects.RecordStore` and the
:py:class:`~cheshire3.baseObjects.Index`\ es to store in the
:py:class:`~cheshire3.baseObjects.IndexStore`, ``eadIndexStore``.

Line 13 could be expanded to contain a series of :ref:`config-path` elements,
each of which has a reference to a Cheshire3 object that has been previously
configured. This lines instruct the server to actually instantiate the object
in memory. while this is not strictly necessary it may occasionally be
desirable, see :ref:`config-objects` for more information.
