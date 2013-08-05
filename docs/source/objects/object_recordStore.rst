Cheshire3 Object Model - RecordStore
====================================

.. _objects-recordStore-api:

API
---

.. autoclass:: cheshire3.baseObjects.RecordStore
   :members:


.. _objects-recordStore-implementations:

Implementations
---------------

The following implementations are included in the distribution by default:

.. autoclass:: cheshire3.recordStore.BdbRecordStore

.. autoclass:: cheshire3.recordStore.RedirectRecordStore

.. autoclass:: cheshire3.recordStore.RemoteWriteRecordStore

.. autoclass:: cheshire3.recordStore.RemoteSlaveRecordStore


In addition to the default implementation, the :py:mod:`cheshire3.sql`
provides the following implementations:

.. autoclass:: cheshire3.sql.recordStore.PostgresRecordStore

