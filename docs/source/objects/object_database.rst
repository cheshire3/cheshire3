Cheshire3 Object Model - Database
=================================

API
---

.. autoclass:: cheshire3.baseObjects.Database
   :members:
   

Implementations
---------------

.. autoclass:: cheshire3.database.SimpleDatabase

.. autoclass:: cheshire3.database.OptimisingDatabase


Configurations
--------------

There are no pre-configured databases as this is totally application specific.
Configuring a database it your primary task when beginning to use Cheshire3 for
your data. There are some example databases including configuration available
in the `Cheshire3 Download Site`_.

You can also obtain a default :py:class:`~cheshire3.baseObjects.Database`
configuration using :command:`cheshire3-init` (see :doc:`/commands` for
details.)


.. Links
.. _`Cheshire3 Download Site`: http://download.cheshire3.org
