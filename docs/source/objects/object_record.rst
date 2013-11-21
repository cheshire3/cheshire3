Cheshire3 Object Model - Record
===============================

.. _objects-record-api:

API
---

.. autoclass:: cheshire3.baseObjects.Record
   :members:

.. _objects-record-implementations:

Implementations
---------------

The following implementations are included in the distribution by default:

.. autoclass:: cheshire3.record.LxmlRecord

.. autoclass:: cheshire3.record.MinidomRecord

.. autoclass:: cheshire3.record.SaxRecord

.. autoclass:: cheshire3.record.MarcRecord


The class that you interact with will almost certainly depend on which
:py:class:`~cheshire3.baseObjects.Parser` you used.

In addition to the default implementation, the :py:mod:`cheshire3.graph`
provides the following implementations:

.. autoclass:: cheshire3.graph.record.GraphRecord

.. autoclass:: cheshire3.graph.record.OreGraphRecord

