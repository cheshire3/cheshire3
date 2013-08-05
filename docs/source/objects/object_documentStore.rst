Cheshire3 Object Model - DocumentStore
======================================

.. _objects-documentStore-api:

API
---

.. autoclass:: cheshire3.baseObjects.DocumentStore
   :members:


.. _objects-documentStore-implementations:

Implementations
---------------

The following implementations are included in the distribution by default:

.. autoclass:: cheshire3.documentStore.BdbDocumentStore

.. autoclass:: cheshire3.documentStore.FileSystemDocumentStore


In addition to the default implementation, the :py:mod:`cheshire3.sql`
provides the following implementations:

.. autoclass:: cheshire3.sql.documentStore.PostgresDocumentStore
