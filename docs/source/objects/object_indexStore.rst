Cheshire3 Object Model - IndexStore
===================================

.. _objects-indexStore-api:

API
---

.. autoclass:: cheshire3.baseObjects.IndexStore
   :members:


.. _objects-indexStore-implementations:

Implementations
---------------

The following implementations are included in the distribution by default:

.. autoclass:: cheshire3.indexStore.BdbIndexStore


In addition to the default implementation, the :py:mod:`cheshire3.sql`
provides the following implementations:

.. autoclass:: cheshire3.sql.indexStore.PostgresIndexStore
