Cheshire3 Tutorials - Configuring Stores
========================================

.. highlight:: xml
   :linenothreshold: 5


Introduction
------------

There are several trpyes of Store objects, but we're currently primarily
concerned with :py:class:`~cheshire3.baseObjects.RecordStore`\ s.
:py:class:`~cheshire3.baseObjects.DocumentStore`\ s are practically identical
to :py:class:`~cheshire3.baseObjects.RecordStore`\ s in terms of configuration,
so we'll talk about the two together.

:py:class:`~cheshire3.baseObjects.Database` specific stores will be included
in the :ref:`config-subConfigs` section of a database configuration file
[:doc:`Database Config Tutorial <database>`,
:doc:`Database Config Reference </config/index>`].


Example
-------

Example store configuration::

    <subConfig type="recordStore" id="eadRecordStore">
        <objectType>recordStore.BdbRecordStore</objectType>
        <paths>
            <path type="databasePath">recordStore.bdb</path>
            <object type="idNormalizer" ref="StringIntNormalizer"/>
        </paths>
        <options>
            <setting type="digest">sha</setting>
        </options>
    </subConfig>


Explanation
-----------

Line 1 starts a new :py:class:`~cheshire3.baseObjects.RecordStore`
configuration for an object with the identifier ``eadRecordStore``.

Line 2 declares that it should be instantiated with :ref:`config-objectType`
:py:class:`cheshire3.recordStore.BdbRecordStore`. There are several possible
classes distributed with Cheshire3, another is
:py:class:`cheshire3.sql.recordStore.PostgresRecordStore` which will maintain
the data and associated metadata in a PostgreSQL relational database (this
assumes that you installed Cheshire3 with the optional ``sql`` features enabled
- see :ref:`/install` for details). The default is the much faster BerkeleyDB
based store.

Then we have two fields wrapped in the :ref:config-paths section. Line 4 gives
the filename of the database to use, in this case :file:`recordStore.bdb`.
Remember that this will be relative to the current
:ref:`defaultPath <config-common-defaultPath>`.

Line 5 has a reference to a :py:class:`~cheshire3.baseObjects.Normalizer`
object -- this is used to turn the :py:class:`~cheshire3.baseObjects.Record`
identifiers into something appropriate for the underlying storage system. In
this case, it turns integers into strings (as Berkeley DB only has string
keys.) It's safest to leave this alone, unless you know that you're always
going to assign string based identifiers before storing
:py:class:`~cheshire3.baseObjects.Record`\ s. 

Line 8 has a setting called ``digest``. This will configure the
:py:class:`~cheshire3.baseObjects.RecordStore` to maintain a checksum for each
:py:class:`~cheshire3.baseObjects.Record` to ensure that it remains unique
within the store. There are two checksum algorithms available at the moment,
'sha' and 'md5'. If left out, the store will be slightly faster, but allow
(potentially inadvertant) duplicate records.

There are some additional possible objects that can be referenced in the
:ref:`config-paths` section not shown here:

``inTransformer``
    A :py:class:`~cheshire3.baseObjects.Transformer` to run the
    :py:class:`~cheshire3.baseObjects.Record` through in order to transform
    (serialize) it for storing.

    If configured, this takes priority over ``inWorkflow`` which will be
    ignored.
    
    If not configured reverts to ``inWorkflow``.

``outParser``
    A :py:class:`~cheshire3.baseObjects.Parser` to run the stored data through
    in order to parse (deserialize) it back into
    a :py:class:`~cheshire3.baseObjects.Record`.

    If configured, this takes priority over ``outWorkflow`` which will be
    ignored.

    If not configured reverts to ``outWorkflow``.
    
``inWorkflow``
    A :py:class:`~cheshire3.baseObjects.Workflow` to run the
    :py:class:`~cheshire3.baseObjects.Record` through in order to transform
    (serialize) it for storing.
    
    The use of a :py:class:`~cheshire3.baseObjects.Workflow` rather than a
    :py:class:`~cheshire3.baseObjects.Transformer` enables chaining of objects,
    e.g. a :py:class:`~cheshire3.transformer.XmlTransformer` to serialize the
    :py:class:`~cheshire3.baseObjects.Record` to XML, followed by a
    :py:class:`~cheshire3.preParser.GzipPreParser` to compress the XML before
    storing on disk. In this case one would need to configure an
    ``outWorkflow`` to reverse the process.

    If not configured a :py:class:`~cheshire3.baseObjects.Record` will be
    serialized using its method,
    :py:meth:`~cheshire3.baseObjects.Record.get_xml(session)`.

``outWorkflow``
    A :py:class:`~cheshire3.baseObjects.Workflow` to run the stored data
    through in order to turn it back into a
    :py:class:`~cheshire3.baseObjects.Record`.
    
    The use of a :py:class:`~cheshire3.baseObjects.Workflow` rather than a
    :py:class:`~cheshire3.baseObjects.Parser` enables chaining of objects,
    e.g. a :py:class:`~cheshire3.preParser.GunzipPreParser` to decompress the
    data back to XML, followed by a :py:class:`~cheshire3.parser.LxmlParser` to
    parse (deserialize) the XML back into a
    :py:class:`~cheshire3.baseObjects.Record`.
    
    If not configured, the raw XML data will be parsed (deserialized) using a
    :py:class:`~cheshire3.parser.LxmlParser`, if it can be got from the
    :py:class:`~cheshire3.baseObjects.Server`, otherwise a
    :py:class:`~cheshire3.bootstrap.BSLxmlParser`.


:py:class:`~cheshire3.baseObjects.DocumentStore`\ s
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For :py:class:`~cheshire3.baseObjects.DocumentStore`\ s, instead all we would
change would be the identifier, the :ref:`config-objectType`, and probably the
`databasePath`. Everything else can remain pretty much the same.
:py:class:`~cheshire3.baseObjects.DocumentStore`\ s have slightly different
additional objects that can be referenced in the paths section however:

``inPreParser``
    A :py:class:`~cheshire3.baseObjects.PreParser` to run the
    :py:class:`~cheshire3.baseObjects.Document` through before storing its
    content.

    For example a :py:class:`~cheshire3.preParser.GzipPreParser` to compress
    the :py:class:`~cheshire3.baseObjects.Document` content before storing on
    disk. In this case one would need to configure a
    :py:class:`~cheshire3.preParser.GunzipPreParser` as the ``outPreParser``.

    If configured, this takes priority over ``inWorkflow`` which will be
    ignored.

    If not configured reverts to ``inWorkflow``.

``outPreParser``
    A :py:class:`~cheshire3.baseObjects.PreParser` to run the stored data
    through before returning the
    :py:class:`~cheshire3.baseObjects.Document`.

    For example a :py:class:`~cheshire3.preParser.GunzipPreParser` to
    decompress the data from the disk to trun it back into the original
    :py:class:`~cheshire3.baseObjects.Document` content.

    If configured, this takes priority over ``outWorkflow`` which will be
    ignored.

    If not configured reverts to ``outWorkflow``.