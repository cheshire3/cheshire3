Troubleshooting
===============


Introduction
------------

This page contains a list of common Python and Cheshire3 specific errors and
exceptions.

It is hoped that it also offers some enlightenment as to what these errors and
exception mean in terms of your configuration/code/data, and suggests how you
might go about correcting them.


Common Run-time Errors
----------------------

``AttributeError: 'NoneType' object has no attribute ...``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The object the system is trying to use is null i.e. of NoneType. There are
several things that can cause this (.. hint:: The reported attribute might give
you a clue to what type the object should be):

* The object does not exist in the architecture. This is often due to
  errors/omissions in the configuration file.
  
  .. admonition:: ACTION
  
     Make sure that the object is configured (either at the database or server
     level).

  .. hint:: Remember that everything is configured hierarchically from the
     server, down to the individual subConfigs of each database.

* There is a discrepancy between the identifier used to configure the object,
  and that used to get the object for use in the script.

  .. admonition:: ACTION
  
     Ensure that the identifier used to get the object in the script is the
     same as that used in the configuration.

  .. hint:: Check the spelling and case used.

* If the object is the result of a get or fetch operation (e.g., from a
  ``DocumentFactory`` or ``ObjectStore``), it looks like it wasn't retrieved
  properly from the store.

  .. admonition:: ACTION
  
     Afraid there's no easy answer to this one. Check that the requested object
     actually exists in the group/store.

* If the object is the result of a process request (e.g., to a ``Parser``,
  ``PreParser`` or ``Tranformer``), it looks like it wasn't returned properly
  by the processor.

  .. admonition:: ACTION
  
     Afraid there's no easy answer here either. Check for any errors/exceptions
     raised during the processing operation.


``AttributeError: x instance has no attribute 'y'``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An instance of object type x, has neither an attribute or method called y.

.. admonition:: ACTION

   Check the API documentation for the object-type, and correct your script.


``Cheshire3 Exception: 'x' referenced from 'y' has no configuration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An object referred to as 'x' in the configuration for object 'y' has no
configuration.

.. admonition:: ACTION

   Make sure that object 'x' is configured in ``subConfigs``, and that all
   references to object 'x' use the correct identifier string.


``Cheshire3 Exception: Failed to build myProtocolMap: not well-formed ...``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``zeerex_srx.xml`` file contains XML which is not well formed.

.. admonition:: ACTION

   Check this file at the suggested line and column and make the necessary
   corrections.


``TypeError: cannot concatenate 'str' and 'int' objects``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the error message looks like the following::

    File "../../code/baseStore.py", line 189, in generate_id
    id = self.currentId +1
    TypeError: cannot concatenate 'str' and 'int' objects
            
Then it's likely that your ``RecordStore`` is trying to create a new integer by
incrementing the previous one, when the previous one is a string!

.. admonition:: ACTION

   This can easily be remedied by adding the following line to the ``<paths>``
   section of the ``<subConfig>`` that defines the ``RecordStore``::

    <object type="idNormalizer" ref="StringIntNormalizer"/>


``TypeError: some_method() takes exactly x arguments (y given)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The method you're trying to use requires x arguments, you only supplied y
arguments.

.. admonition:: ACTION

   Check the API for the required arguments for this method.

.. hint:: All Cheshire3 objects require an instance of type ``Session`` as the
   first argument to their public methods.


``UnicodeEncodeError: 'ascii' codec can't encode character u'\uXXXX' ...``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Oh Dear! Somewhere within one of your ``Documents`` ``Records`` there is a
character which cannot be encoded into ascii unicode.

.. tip:: Use a ``UnicodeDecodePreParser`` or ``PrintableOnlyPreParser`` to
   turn the unprintable unicode character into an XML character entity.


``xml.sax._exceptions.SAXParseException: <unknown>:x:y: not well-formed ...``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Despite the best efforts of the ``PreParsers`` there is badly formed XML within
the document; possibly a malformed tag, or character entity.

.. hint:: Check the document source at line x, column y.


``ConfigFileException: : Sort executable for indexStore does not exist``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This means that the unix sort utility executable was not present at the
configured location, and could not be found. You will need to configure it for
your Cheshire3 server.

.. admonition:: ACTION

   Discover the path to the unix sort executable on your system by running the
   following command and making a note of the result::
   of it::
   
       which sort

   Insert this value into the ``sortPath`` ``<path>`` in the ``<paths>``
   sections of your server configuration file. 


Removing the dependency on the unix sort utility is on the TODO list in our
`issue tracker <https://github.com/cheshire3/cheshire3/issues/6>`.


Apache Errors
-------------

"No space left on device" Apache error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If there is space left on your hard drives, then it is almost certainly that
the linux kernel has run out of semaphores for mod_python or Berkeley DB.

.. admonition:: ACTION

   You need to tweak the kernel performance a little. For more information, see
   `Clarens FAQ <http://clarens.sourceforge.net/index.php?docs+faq>`


.. Links
.. _Python: http://www.python.org/
