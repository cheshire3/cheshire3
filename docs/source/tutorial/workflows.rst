Cheshire3 Tutorials - Configuring Workflows
===========================================

.. highlight:: xml
   :linenothreshold: 5


Introduction
------------

:py:class:`~cheshire3.baseObjects.Workflow`\ s are first class objects in the
Cheshire3 system - they're configured at the same time and in the same way as
other objects. Their function is to provide an easy way to define a series of
common steps that can be reused by different Cheshire3 databases/systems, as
opposed to writing customised code to achieve the same end result for each.

Build :py:class:`~cheshire3.baseObjects.Workflow`\ s are the most common type
as the data must generally pass through a lot of different functions on
different objects, however as explained previously the differences between
:py:class:`~cheshire3.baseObjects.Database`\ s are often only in one section.
By using :py:class:`~cheshire3.baseObjects.Workflow`\ s, we can simply define
the changed section rather than writing code to do the same task over and over
again.

The disadvantage, currently, of :py:class:`~cheshire3.baseObjects.Workflow`\ s
is that it is very complicated to find out what is going wrong if something
fails. If your data is very clean, then a
:py:class:`~cheshire3.baseObjects.Workflow` is probably the right solution,
however if the data is likely to have XML parse errors or has to go through
many different :py:class:`~cheshire3.baseObjects.PreParser`\ s and you want to
verify each step, then hand written code may be a better solution for you.

The distribution comes with a generic build workflow object called
``buildIndexWorkflow``. It then calls ``buildIndexSingleWorkflow`` to handle
each individual :py:class:`~cheshire3.baseObjects.Document`, also supplied.
This second :py:class:`~cheshire3.baseObjects.Workflow`\ s then calls
``PreParserWorkflow``, of which a trivial one is supplied, but this is very
unlikely to suit your particular needs, and should be customised as required.
An example would be if you were trying to build a
:py:class:`~cheshire3.baseObjects.Database` of legacy SGML documents, your
``PreParserWorkflow`` would probably need to call an:
:py:class:`~cheshire3.preParser.SgmlPreParser`, configured to deal with the
non-XML conformant parts of that particular SGML DTD.

For a full explanation of the different tags used in
:py:class:`~cheshire3.baseObjects.Workflow` configuration, and what they do,
see the :doc:`Configuration section dealing with workflows </config/workflows>`.


Example 1
---------

Simple workflow configuration::

    <subConfig type="workflow" id="PreParserWorkflow">
        <objectType>workflow.SimpleWorkflow</objectType>
        <workflow>
            <!-- input type:  document -->
            <object type="preParser" ref="SgmlPreParser"/>
            <object type="preParser" ref="CharacterEntityPreParser"/>
        </workflow>
    </subConfig>


Example 2
---------

Slightly more complex workflow configurations::

    <subConfig type="workflow" id="buildIndexWorkflow">
        <objectType>workflow.SimpleWorkflow</objectType>
        <workflow>
            <!-- input type:  documentFactory -->
            <log>Loading records</log>
            <object type="recordStore" function="begin_storing"/>
            <object type="database" function="begin_indexing"/>
            <for-each>
                <object type="workflow" ref="buildIndexSingleWorkflow"/>
            </for-each>
            <object type="recordStore" function="commit_storing"/>
            <object type="database" function="commit_metadata"/>
            <object type="database" function="commit_indexing"/>
        </workflow>
    </subConfig>

    <subConfig type="workflow" id="buildIndexSingleWorkflow">
        <objectType>workflow.SimpleWorkflow</objectType>
        <workflow>
            <!-- input type:  document -->
            <object type="workflow" ref="PreParserWorkflow"/>
            <try>
                <object type="parser" ref="LxmlParser"/>
            </try>
            <except>
                 <log>Unparsable Record</log>
            </except>
            <object type="recordStore" function="create_record"/>
            <object type="database" function="add_record"/>
            <object type="database" function="index_record"/>
            <log>Loaded Record</log>
        </workflow>
    </subConfig>


Explanation
-----------

The first two lines of each configuration example are exactly the same as all
previous objects. Then there is one new section -
:ref:`config-workflows-workflow`. This contains a series of instructions for
what to do, primarily by listing objects to handle the data.

The workflow in `Example 1`_ is an example of how to override the
``PreParserWorkflow`` for a specific database. In this case we start by giving
the document input object to the :py:class:`~cheshire3.preParser.SgmlPreParser`
in line 5, and the result of that is given to the
:py:class:`~cheshire3.preParser.CharacterEntityPreParser` in line 6. Note that
lines 4 and 20 are just comments and are not required.

The workflows in `Example 2`_ are slightly more complex with some additional
constructions. Lines 5, 26, 31 use the log instruction to get the
:py:class:`~cheshire3.baseObjects.Workflow` to log the fact that it is starting
to load :py:class:`~cheshire3.baseObjects.Record`\ s.

In lines 6 and 7 the object tags have a second attribute called ``function``.
This contains the name of the function to call when it's not derivable from the
input object. For example, a :py:class:`~cheshire3.baseObjects.PreParser` will
always call :py:meth:`~cheshire3.baseObjects.PreParser.process_document()`,
however you need to specify the function to call on a
:py:class:`~cheshire3.baseObjects.Database` as there are many available. Note
also that there isn't a 'ref' attribute to reference a specific object
identifier. In this case it uses the current session to determine which
:py:class:`~cheshire3.baseObjects.Server`,
:py:class:`~cheshire3.baseObjects.Database`,
:py:class:`~cheshire3.baseObjects.RecordStore` and so forth should be used.
This allows the :py:class:`~cheshire3.baseObjects.Workflow` to be used in
multiple contexts (i.e. if configured at the server level it can be used by
several :py:class:`~cheshire3.baseObjects.Database`\ s).

The for-each block (lines 8-10) then iterates through the
:py:class:`~cheshire3.baseObjects.Document`\ s in the supplied
:py:class:`~cheshire3.baseObjects.DocumentFactory`, calling another
:py:class:`~cheshire3.baseObjects.Workflow`,
``buildIndexSingleWorkflow`` (configured in lines 17-33), on each of them. Like
the :py:class:`~cheshire3.baseObjects.PreParser` objects mentioned earlier,
:py:class:`~cheshire3.baseObjects.Workflow` objects called don't need to be
told which function to call - the system will always call their
:py:meth:`~cheshire3.baseObjects.Workflow.process()` function. Finally the
:py:class:`~cheshire3.baseObjects.Database` and
:py:class:`~cheshire3.baseObjects.RecordStore` have their commit functions
called to ensure that everything is written out to disk.

The second workflow in `Example 2`_ is called by the first, and in turn calls
the ``PreParserWorkflow`` configured in `Example 1`_. It then calls a
:py:class:`~cheshire3.baseObjects.Parser`, carrying out some error handling as
it does so (lines 22-27), and then makes further calls to the
:py:class:`~cheshire3.baseObjects.RecordStore` (line 28) and
:py:class:`~cheshire3.baseObjects.Database` (lines 29-30) objects to store and
:py:class:`~cheshire3.baseObjects.Index` the record produced.

