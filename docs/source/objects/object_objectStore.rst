Cheshire3 Object Model - ObjectStore
====================================

.. _objects-objectStore-api:

API
---

.. autoclass:: cheshire3.baseObjects.ObjectStore
   :members:


.. _objects-objectStore-implementations:

Implementations
---------------

The following implementations are included in the distribution by default:

.. autoclass:: cheshire3.objectStore.BdbObjectStore


In addition to the default implementation, the :py:mod:`cheshire3.sql`
provides the following implementations:

.. autoclass:: cheshire3.sql.objectStore.PostgresObjectStore

