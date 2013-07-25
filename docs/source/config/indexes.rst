Cheshire3 Configuration - Indexes
=================================

.. highlight:: xml
   :linenothreshold: 5

Introduction
------------

Indexes need to be configured to know where to find the data that they should
extract, how to process it once it's extracted and where to store it once
processed.

.. _config-indexes-paths:

Paths
-----

indexStore
    An object reference to the default indexStore to use for extracted terms.

termIdIndex
    Alternative index object to use for termId for terms in this index.

tempPath
    Path to a directory where temporary files will be stored during batch mode
    indexing.


.. _config-indexes-settings:

Settings
--------

The value for any true/false type settings must be 0 or 1.

sortStore
    If the value is true , then the indexStore is instructed to also create
    an inverted list of record Id to value (as opposed to value to list of
    records) which should be used for sorting by that index.

cori_constant[0-2]
    Constants to be used during CORI relevance ranking, if different from the
    defaults.

lr_constant[0-6]
    Constants to be used during logistic regression relevance ranking, if
    different from the defaults.

okapi_constant_[b|k1|k3]'
    Constants to be used for the OKAPI BM-25 algorithm, if different from the
    defaults. These can be used to fine tune the behavior of relevance ranking
    using this algorithm.

noIndexDefault
    If the value is true, the :py:class:`~cheshire3.baseObjects.Index`
    should not be called from
    :py:meth:`~cheshire3.baseObjects.Database.index_record()` method of
    :py:class:`~cheshire3.baseObjects.Database`.

noUnindexDefault
    If the value is true, the :py:class:`~cheshire3.baseObjects.Index`
    should not be called from
    :py:meth:`~cheshire3.baseObjects.Database.unindex_record()` method of
    :py:class:`~cheshire3.baseObjects.Database`.

vectors
    Should the index store vectors (doc -> list of termIds)

proxVectors
    Should the index store vectors that also maintain proximity for their terms

minimumSupport
    TBC

vectorMinGlobalFreq
    TBC

vectorMaxGlobalFreq
    TBC

vectorMinGlobalOccs
    TBC

vectorMaxGlobalOccs
    TBC

vectorMinLocalFreq
    TBC

vectorMaxLocalFreq
    TBC

longSize
    Size of a long integer in this index's underlying data structure (e.g. to
    migrate between 32 and 64 bit platforms)

recordStoreSizes
    Use average record sizes from recordStores when calculating relevances.
    This is useful when a database includes records from multiple recordStores,
    particularly when recordStores contain records of varying sizes.

maxVectorCacheSize
    Number of terms to cache when building vectors.


.. _config-indexes-elements:

Index Configuration Elements
----------------------------

.. _config-indexes-elements-source:

``<source>``
~~~~~~~~~~~~

An index configuration must contain at least one source element. Each source
block configures a way of treating the data that the index is asked to process.

It's worth mentioning here that the index object will be asked to process
incoming search terms as well as data from records being indexed. A
``<source>`` element may have a ``mode`` attribute to specify when the
processing configured within this ``source`` block should be applied. To
clarify, the ``mode`` attribute may have the value of any of the relations
defined by :abbr:`CQL (Contextual Query Language)` (any, all, =, exact, etc.),
indicating that the processing in this source should be applied when the index
is searched using that particular relation.

The ``mode`` attribute may also have the value 'data', indicating that the
processing in the source block should be applied to the records at the time
they are indexed. Multiple modes can be specified for a single source block by
separating the with a vertical pipe ``|`` character within the value of the
``mode`` attribute. If no ``mode`` attribute is specified, the source will
default to being a ``data`` source. `Example 2'_ demonstrates the use of the
``mode`` attribute to apply a different
:py:class:`~cheshire3.baseObjects.Extractor` object when carrying out searches
using the 'any', 'all' or '=' CQL relation, in this case to preserve
masking/wildcard characters.

Each data mode source block configures one or more XPaths to use to extract
data from the record, a workflow of objects to process the results of the XPath
evaluation and optionally a workflow of objects to pre-process the record to
transform it into a state suitable for XPathing. Each data mode source block
will be processed in turn by the system for each record during indexing.

For source blocks with modes other than data, only the element configuring the
workflow of objects to process the incoming term with is required.
:ref:`config-indexes-elements-xpath` and
:ref:config-indexes-elements-preprocess` elements will be ignored.


.. _config-indexes-elements-xpath:
.. _config-indexes-elements-selector:

``<xpath>`` or ``<selector>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These elements specify a way to select data from a
:py:class:`~cheshire3.baseObject.Record`. They can contain either a simple
XPath expression as CDATA (as in `Example 1`_) or have a ``ref`` attribute
containing a reference to a configured
:py:class:`~cheshire3.baseObject.Selector` object within the configuration
hierarchy (as in `Example 2`_).

While it is possible to use either element in either way, it is considered best
practice to use the convention of ``<xpath>`` for explicit CDATA XPaths and
``<selector>`` when referencing a configured
:py:class:`~cheshire3.baseObject.Selector`.

These elements may not appear more than once within a given
:ref:`config-indexes-elements-source` , however a
:py:class:`~cheshire3.baseObjects.Selector` may itself specify multiple
``<xpath>`` or ``<location>`` elements. When the a configured
:py:class:`~cheshire3.baseObjects.Selector` contains multiple ``<xpath>`` or
``<location>`` elements, the results of each expression will be processed by
the :ref:`process chain <config-indexes-elements-process>` (as described below).

If an XPath makes use of XML namespaces, then the mappings for the namespace
prefixes must be present on the XPath element. This can be seen in
`Example 1`_.


.. _config-indexes-elements-process:
.. _config-indexes-elements-preprocess:
.. _`\<process\> and \<preprocess\>`:

``<process>`` and ``<preprocess>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These elements contain an ordered list of objects. The results of the first
object is given to the second and so on down the chain.

The first object in a process chain must be an Extractor, as the input data is
either a string, a :abbr:`DOM (Document Object Model)` node or a
:abbr:`SAX (Simple API for XML)` event list as appropriate to the XPath
evaluation. The result of a process chain must be a hash, typically from an
:py:class:`~cheshire3.baseObjects.Extractor` or a
:py:class:`~cheshire3.baseObjects.Normalizer` . However if the last object is
an :py:class:`~cheshire3.baseObjects.IndexStore` , it will be used to store
the terms rather than the default.

The input to a preprocess chain is a :py:class:`~cheshire3.baseObjects.Record`
, so the first object is most likely to be a Transformer. The result must also
be a :py:class:`~cheshire3.baseObjects.Record` , so the last object is most
likely to be a :py:class:`~cheshire3.baseObjects.Parser` .

For existing processing objects that can be used in these fields, see the
object documentation.


.. _config-indexes-example1:

Example 1
---------

::

    <subConfig type="index" id="zrx-idx-9">
        <objectType>index.ProximityIndex</objectType>
        <paths>
            <object type="indexStore" ref="zrxIndexStore"/>
        </paths>
        <source>
            <preprocess>
                <object type="transformer" ref="zeerexTxr"/>
                <object type="parser" ref="SaxParser"/>
            </preprocess>
            <xpath>name/value</xpath>
            <xpath xmlns:zrx="http://explain.z3950.org/dtd/2.0">zrx:name/zrx:value</xpath>
            <process>
                <object type="extractor" ref="ExactParentProximityExtractor"/>
                <object type="normalizer" ref="CaseNormalizer"/>
            </process>
        </source>
        <options>
            <setting type="sortStore">true</setting>
            <setting type="lr_constant0">-3.7</setting>
        </options>
    </subConfig>


.. _config-indexes-example2:

Example 2
---------

::

    <subConfig type="selector" id="indexXPath">
        <objectType>cheshire3.selector.XPathSelector</objectType>
        <source>
            <xpath>/explain/indexInfo/index/title</xpath>
            <xpath>/explain/indexInfo/index/description</xpath>
        </source>
    </subConfig>

    <subConfig type="index" id="zrx-idx-10">
        <objectType>index.ProximityIndex</objectType>
        <paths>
            <object type="indexStore" ref="zrxIndexStore"/>
        </paths> 
        <source mode="data">
            <selector ref="indexXPath"/>
            <process>
                <object type="extractor" ref="ProximityExtractor"/>
                <object type="normalizer" ref="CaseNormalizer"/>
                <object type="normalizer" ref="PossessiveNormalizer"/>
            </process>
        </source>
        <source mode="any|all|=">
            <process>
                <object type="extractor" ref="PreserveMaskingProximityExtractor"/>
                <object type="normalizer" ref="CaseNormalizer"/>
                <object type="normalizer" ref="PossessiveNormalizer"/>
            </process>
        </source> 
    </subConfig>

