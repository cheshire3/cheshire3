Cheshire3 Configuration - Workflows
===================================

.. highlight:: xml
   :linenothreshold: 5

Introduction
------------

:py:class:`~cheshire3.baseObjects.Workflow` can be configured to define a
series of processing steps that are common to several Cheshire3
:py:class:`~cheshire3.baseObjects.Database` or
:py:class:`~cheshire3.baseObjects.Server`, as an alternative to writing
customized code for each.

.. :doc:`Workflow Configuration Tutorial </build/workflow>` including examples and explanation.


Workflow Configuration Elements
-------------------------------

.. _config-workflows-workflow:

``<workflow>``
~~~~~~~~~~~~~~

Base wrapping tags for workflows; analagous to
:ref:`\<process\> and \<preprocess\>` in :doc:`Index configurations <indexes>`.

Contains an ordered list of :ref:`\<object\>s <config-workflows-object>`. The
results of the first object is given to the second and so on down the chain.
It should be apparent that subsequent objects must be able to accept as input,
the result of the previous.


.. _config-workflows-object:

``<object>``
~~~~~~~~~~~~

A call to an object within the system. ``<object>`` s define the following
attributes:
           
type [ mandatory ]
    Specifies the type of the object within the Cheshire3 framework. Broadly
    speaking this may be a:
    
    - preParser
    - parser
    - database
    - recordStore
    - index
    - logger
    - transformer
    - workflow
              
ref
    A reference to a configured object within the system. If unspecified, the
    current :py:class:`~cheshire3.baseObjects.Session` is used to determine
    which :py:class:`~cheshire3.baseObjects.Server`,
    :py:class:`~cheshire3.baseObjects.Database`,
    :py:class:`~cheshire3.baseObjects.RecordStore` and so forth should be used.

function
    The name of the method to call on the object. If unspecified, the default
    function for the particular type of object is called.


For existing processing objects that can be used in these fields, see the
:doc:`object documentation <../objects/index>`.

.. _config-workflows-log:

``<log>``
~~~~~~~~~
 
Log text to a :py:class:`~cheshire3.baseObjects.Logger` object.
A reference to a configured :py:class:`~cheshire3.baseObjects.Logger` may be
provided using the ``ref`` attribute.  If no ``ref`` attribute is present,
the :py:class:`~cheshire3.baseObjects.Database` 's default logger is used.


.. _config-workflows-assign:

``<assign>``
~~~~~~~~~~~~

Assign a specified value to a variable with a given name. Requires both of the
following attributes:

from [ *mandatory* ]
    the value to assign

to [ *mandatory* ]
    a name to refer to the variable


.. _config-workflows-fork:

``<fork>``
~~~~~~~~~~

Feed the current input into each processing fork.
[ more details to follow in v1.1]


.. _config-workflows-foreach:

``<for-each>``
~~~~~~~~~~~~~~

Iterate/loop through the items in the input object. Like
:ref:`\<workflow\> <config-workflows-workflow>` contains an ordered list of
:ref:`\<object\>s <config-workflows-object>` . Each of the items in the input is
run through the chain of processing objects.


.. _config-workflows-try:

``<try>``
~~~~~~~~~

Allows for error catching. Any errors that occur within this element will not
cause the :py:class:`~cheshire3.baseObjects.Workflow` to exit with a failure.
Must be followed by one :ref:`\<except\> <config-workflows-except>` elements,
which may in turn also be followed by one
:ref:`\<else\> <config-workflows-else>` element.


.. _config-workflows-except:

``<except>``
~~~~~~~~~~~~

Enables error handling. This element may only follow a
:ref:`\<try\> <config-workflows-try>` element. Specifies action to take in the
event of an error occurring during the work executed within the preceding
:ref:`<\try\> <config-workflows-try>`.


.. _config-workflows-else:

``<else>``
~~~~~~~~~~

Success handling. This element may follow a
:ref:`\<try\> <config-workflows-try>` /
:ref:`\<except\> <config-workflows-except>` pair.

Specifies the action to take in the event that no errors occur within the
preceding :ref:`\<try\> <config-workflows-try>`.


.. _config-workflows-continue:

``<continue/>``
~~~~~~~~~~~~~~~

Skip remaining processing steps, and move on to next iteration while inside a
:ref:`\<for-each\> <config-workflows-foreach>` loop element. May not contain
any further elements or attributes. This can be useful in the error handling
:ref:`\<except\> <config-workflows-except>` element, e.g. if a document cannot
be parsed, it cannot be indexed, so skip to next
:py:class:`~cheshire3.baseObjects.Document` in the
:py:class:`~cheshire3.baseObjects.DocumentFactory`.


.. _config-workflows-break:

``<break/>``
~~~~~~~~~~~~

Break out of a :ref:`\<for-each\> <config-workflows-foreach>` loop element,
skipping all subsequent processing steps, and all remaining iterations. May not
contain any further elements or attributes.


.. _config-workflows-raise:

``<raise/>``
~~~~~~~~~~~~

Raise an error occurring within the preceding
:ref:`\<try\> <config-workflows-try>` to the calling script or
:py:class:`~cheshire3.baseObjects.Workflow`. May only be used within an
:ref:`\<except\> <config-workflows-except>` element. May not contain any
further elements or attributes.


.. _config-workflows-return:

``<return/>``
~~~~~~~~~~~~~

Return the result of the previous step to the calling script or
:py:class:`~cheshire3.baseObjects.Workflow`. May not contain any further
elements or attributes.

