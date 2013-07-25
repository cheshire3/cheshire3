Cheshire3 Configuration - Protocol Map
======================================

.. highlight:: xml
   :linenothreshold: 5

Introduction
------------

ZeeRex is a schema for service description and is required for
:abbr:`SRU (Search and Retrieve via URL)` but it can also be used to describe
Z39.50,
:abbr:`OAI-PMH (Open Archives Initiative Protcol for Metadata Harvesting)`
and other information retrieval protocols.

As such, a ZeeRex description is required for each database. The full ZeeRex
documentation is available at http://explain.z3950.org/ along with samples,
schemas and so forth. It is also being considered as the standard service
description schema in the NISO Metasearch Initiative, so knowing about it
won't hurt you any.

In order to map from a :abbr:`CQL (Contextual Query Language)` (the primary
query language for Cheshire3 and :abbr:`SRU (Search and Retrieve via URL)`)
query, we need to know the correlation between
:abbr:`CQL (Contextual Query Language)` index name and Cheshire3's
:py:class:`~cheshire3.baseObjects.Index` object. Defaults for the
:abbr:`SRU (Search and Retrieve via URL)` handler for the database are also
drawn from this file, such as the default number of records to return and the
default record schema in which to return results. Mappings between requested
schema and a :py:class:`~cheshire3.baseObjects.Transformer` object are also
possible. These mappings are all handled by a ProtocolMap.


ZeeRex Elements/Attributes of Particular Significance for Cheshire3
-------------------------------------------------------------------

``<database>``
~~~~~~~~~~~~~~

If you plan to make your database available over
:abbr:`SRU (Search and Retrieve via URL)`, then the contents of the field MUST
correspond with that which has been configured as the mount point for the
:abbr:`SRU (Search and Retrieve via URL)` web application in Apache (or an
alternative Python_ web framework), i.e. if you configured with mapping
/api/sru/ to the :py:mod:`~cheshire3.web.sruApacheHandler` code, then the
first part of the database MUST be api/sru/.

Obviously the rest of the information in serverInfo should be correct as well,
but without the database field being correct, it won't be available over
:abbr:`SRU (Search and Retrieve via URL)`.


``c3:index``
~~~~~~~~~~~~

This attribute may be present on an index element, or a supports element within
``<configInfo>`` within an ``<index>``. It maps that particular index, or the
use of the index with a ``<relation>`` or ``<relationModifier>``, to the
:py:class:`~cheshire3.baseObjects.Index` object with the given id.
``<relationModifiers>`` and ``<relations>`` will override the index as
appropriate.


``c3:transformer``
~~~~~~~~~~~~~~~~~~

Similar to c3:index, this can be present on a ``<schema>`` element and maps
that schema to the :py:class:`~cheshire3.baseObjects.Transformer` used to
process the internal schema into the requested one. If the schema is the one
used internally, then the attribute should not be present.


Paths
-----

zeerexPath
    In the configuration for the ProtocolMap object, this contains the path to
    the ZeeRex file to read.


.. _config-indexes-examples:

Examples
--------

``<subConfig>`` within the main :py:class:`~cheshire3.baseObjects.Database`
configuration (see :doc:`index` for details.)::

    <subConfig type="protocolMap" id="l5rProtocolMap">
        <objectType>protocolMap.CQLProtocolMap</objectType>
        <paths>
            <object type="zeerexPath">sru_zeerex.xml</path>
        </paths>
    </subConfig>


Contents of the :file:`sru_zeerex.xml` file::

    <explain id="org.o-r-g.srw-card" authoritative="true"
        xmlns="http://explain.z3950.org/dtd/2.0/"
        xmlns:c3="http://www.cheshire3.org/schemas/explain/">
        <serverInfo protocol="srw/u" version="1.1" transport="http">
            <host>srw.cheshire3.org</host>
            <port>8080</port>
            <database numRecs="3492" lastUpdate="2002-11-26 23:30:00">srw/l5r</database>
        </serverInfo>
        [...]
        <indexInfo>
            <set identifier="http://srw.cheshire3.org/contextSets/ccg/1.0/" name="ccg"/>
            <set identifier="http://srw.cheshire3.org/contextSets/ccg/l5r/1.0/" name="ccg_l5r"/>
            <set identifier="info:srw/cql-context-set/1/dc-v1.1" name="dc"/>
    
            <index c3:index="l5r-idx-1">
                <title>Card Name</title>
                <map>
                    <name set="dc">title</name>
                </map>
                <configInfo>
                    <supports type="relation" c3:index="l5r-idx-1">exact</supports>
                    <supports type="relation" c3:index="l5r-idx-15">any</supports>
                    <supports type="relationModifier" c3:index="l5r-idx-15">word</supports>
                    <supports type="relationModifier" c3:index="l5r-idx-1">string</supports>
                    <supports type="relationModifier" c3:index="l5r-idx-16">stem</supports>
                </configInfo>
            </index>
        </indexInfo>
        <schemaInfo>
            <schema identifier="info:srw/schema/1/dc-v1.1"
                location="http://www.loc.gov/zing/srw/dc.xsd"
                sort="false" retrieve="true" name="dc"
                c3:transformer="l5rDublinCoreTxr">
                <title>Dublin Core</title>
            </schema>
        </schemaInfo>
    </explain>


.. Links
.. _Python: http://www.python.org/