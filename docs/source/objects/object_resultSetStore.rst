Cheshire3 Object Model - ResultSetStore
=======================================

.. _objects-resultSetStore-api:

API
---

.. autoclass:: cheshire3.baseObjects.ResultSetStore
   :members:


.. _objects-resultSetStore-implementations:

Implementations
---------------

The following implementations are included in the distribution by default:

.. autoclass:: cheshire3.resultSetStore.BdbResultSetStore


In addition to the default implementation, the :py:mod:`cheshire3.sql`
provides the following implementations:

.. autoclass:: cheshire3.sql.resultSetStore.PostgresResultSetStore
