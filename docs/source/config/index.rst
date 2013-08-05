Cheshire3 Configuration
=======================

.. highlight:: xml
   :linenothreshold: 5

Contents:

.. toctree::
   :maxdepth: 2

   common
   Index Configuration <indexes>
   ProtocolMap Configuration <protocolMap>
   Workflow Configuration <workflows>


Introduction
------------

As Cheshire3 is so flexible and modular in the way that it can be implemented
and then the pieces fitted together, it requires configuration files to set up
which pieces to use and in which order. The configuration files are also very
modular, allowing as many objects to be defined in one file as desired and then
imported as required. They are put together from a small number of elements,
with some additional constructions for specialized objects.

A very basic default configuration for a
:py:class:`~cheshire3.baseObjects.Database` can be obtained using the
:command:`cheshire3-init` command described in :doc:`/commands`. The generated
default configuration can then be used as a base on which to build.

Every object in the system that is not instantiated from a request or as the
result of processing requires a configuration section. Many of these
configurations will just contain the object class to instantiate and an
identifier with which to refer to the object. Object constructor functions are
called with the top DOM node of their configuration and another object to be
used as a parent. This allows a tree hierarchy of objects, with a Server at
the top level. It also means that objects can handle their own specialized
configuration elements, while leaving the common elements to the base
configuration handler.

The main elements will be described here, the specialized elements and values
will be described in object specific pages.


Configuration Elements
----------------------

XML namespace is optional, but if used it must be::

    http://www.cheshire3.org/schemas/config/

If you wish to generate configurations in Python_ and have Cheshire3 installed,
then you can import the configuration namespace from
:py:const:`cheshire3.internal.CONFIG_NS`


``<config>``
~~~~~~~~~~~~

The top level element of any configuration file is the config element, and
contains at least one object to construct. It should have an ``id`` attribute
containing an identifier for the object in the system, and a ``type``
attribute specifying what sort of object is being created.

If the configuration file is not for the top level
:py:class:`~cheshire3.baseObjects.Server`, this element must contain an
`\<objectType\>`_ element. It may also contain one of each of `\<docs\>`_,
`\<paths\>`_, `\<subConfigs\>`_,  `\<objects\>`_  and `\<options\>`_ .


.. _config-objectType:

``<objectType>``
~~~~~~~~~~~~~~~~

This element contains the module and class to use when instantiating the
object, using the standard :py:class:`package.module.class` Python_ syntax.

When using classes defined by external packages/modules it is expected that
they will inherit from a base class in the `Cheshire3 Object Model`_
(specifically from a class in :py:mod:`cheshire3.baseObjects`), and conform to
the public API defined therein.


.. _config-docs:

``<docs>``
~~~~~~~~~~

This element may be used to provide configured object level documentation.

e.g. to explain that a particular :py:class:`~cheshire3.baseObjects.Tokenizer`
splits data into sentences based on some pre-defined pattern.


.. _config-paths:

``<paths>``
~~~~~~~~~~~

This element may contain `\<path\>`_ and/or `\<object\>`_ elements to be stored
when building the object in the system.


.. _config-path:

``<path>``
~~~~~~~~~~

This element is used to refer to a path to a resource (usually a filepath)
required by the object and has several attributes to govern this:

- It **must** have a 'type' attribute, saying what sort of thing the resource
  is. This is somewhat context dependent, but is either an object type (e.g.
  'database', 'index') or a description of a file path (e.g. 'defaultPath',
  'metadataPath').

- For configurations which are being included as an external file, the path
  element should have the same ``id`` attribute as the included configuration.

- For references to other configurations, a ``ref`` attribute is used to
  contain the identifier of the referenced object.

- Finally, for configuration files which are held in a
  :py:class:`~cheshire3.baseObjects.ObjectStore` object, the document's
  identifier within the store (rather than the identifier of the object it
  contains) should be put in a ``docid`` attribute.

.. note:: A ``<path>`` element may only occur within a `\<paths\>`_ ,
   `\<subConfigs\>`_ or `\<objects\>`_ element.


.. _config-object:

``<object>``
~~~~~~~~~~~~

Object elements are used to create references to other objects in the system by
their identifier, for example the default
:py:class:`~cheshire3.baseObjects.RecordStore` used by the
:py:class:`~cheshire3.baseObjects.Database`.

There are two mandatory attributes, the ``type`` of object and ``ref`` for the
object's identifier.


``<options>``
~~~~~~~~~~~~~

This section may include one or more `\<setting\>`_ (a value that can't be
changed) and/or `\<default\>`_ (a value that can be overridden in a request)
elements.


.. _`\<setting\>`:
.. _`\<default\>`:

``<setting>`` and ``<default>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``<setting>`` and ``<default>`` have a ``type`` attribute to specify which
setting/default the value is for and the contents of the element is the value
for it.

Each class within the `Cheshire3 Object Model`_ will have different setting and
default types.

.. note:: ``<setting>`` and ``<default>`` may only occur within an
   `\<options\>`_ element.


.. _config-subConfigs:

``<subConfigs>``
~~~~~~~~~~~~~~~~

This wrapper element contains one or more `\<subConfig\>`_ elements. Each
`\<subConfig\>`_ has the same model as the `\<config\>`_, and hence a nested
tree of configurations and subConfigurations can be constructed. It may also
contain `\<path\>`_ elements with a file path to another file to read in and
treat as further subConfigurations.

Cheshire3 employs 'Just In Time' instantiation of objects. That is to say they
will be instantiated when required by the system, or when requested from their
parent object in a script.


.. _config-subConfig:

``<subConfig>``
~~~~~~~~~~~~~~~

This element has the same model as the `\<config\>`_ element to allow for
nested configurations. ``id`` and ``type`` attributes are mandatory for this
element.


.. _config-objects:

``<objects>``
~~~~~~~~~~~~~

The objects element contains one or more path elements, each with a reference
to an identifier for a `\<subConfig\>`_ ). This reference acts as an instruction
to the system to actually instantiate the object from the configuration.

.. note:: while this is no longer required (due to the implementation of 'Just
   In Time' object instantiation) it remains in the configuration schema as
   there are still situation in which this may be desirable, e.g. to
   instantiate objects with long spin-up times at the server level.


.. _config-example:

Example
-------

::

    <config type="database" id="db_l5r">
        <objectType>database.SimpleDatabase</objectType>
        <paths>
            <path type="defaultPath">/home/cheshire/c3/cheshire3/l5r</path>
            <path type="metadataPath">metadata.bdb</path>
            <object type="recordStore" ref="l5rRecordStore"/>
        </paths>
        <options>
            <setting type="log">handle_search</setting>
        </options>
        <subConfigs>
            <subConfig type="parser" id="l5rAttrParser">
                <objectType>parser.SaxParser</objectType>
                <options>
                    <setting type="attrHash">text@type</setting>
                </options>
            </subConfig>
            <subConfig id = "l5r-idx-1">
                <objectType>index.SimpleIndex</objectType>
                <paths>
                    <object type="indexStore" ref="l5rIndexStore"/>
                </paths>
                <source>
                    <xpath>/card/name</xpath>
                    <process>
                        <object type="extractor" ref="ExactExtractor"/>
                        <object type="normalizer" ref="CaseNormalizer"/>
                    </process>
                </source>
            </subConfig>
            <path type="index" id="l5r-idx-2">configs/idx2-cfg.xml<path>
        </subConfigs>
        <objects>
            <path ref="l5RAttrParser"/>
            <path ref="l5r-idx-1"/>
        </objects>
    </config>


.. Links
.. _Python: http://www.python.org/
.. _`Cheshire3 Object Model`: http://cheshire3.org/docs/objects/