Cheshire3 Tutorials - Configuring Indexes
=========================================

.. highlight:: xml
   :linenothreshold: 5


Introduction
------------

:py:class:`~cheshire3.baseObjects.Index`\ es are the primary means of locating
:py:class:`~cheshire3.baseObjects.Record`\ s in the system, and hence need to
be well thought out and specified in advance. They consist of one or more
:ref:`config-paths` to tags in the :py:class:`~cheshire3.baseObjects.Record`,
and how to process the data once it has been located.


Example
-------

Example index configurations::

    <subConfig id = "xtitle-idx">
        <objectType>index.SimpleIndex</objectType>
        <paths>
            <object type="indexStore" ref="indexStore"/>
        </paths>
        <source>
            <xpath>/ead/eadheader/filedesc/titlestmt/titleproper</xpath>
            <process>
                <object type="extractor" ref="SimpleExtractor"/>
                <object type="normalizer" ref="SpaceNormalizer"/>
                <object type="normalizer" ref="CaseNormalizer"/>
            </process>
        </source>
        <options>
            <setting type="sortStore">true</setting>
        </options>
    </subConfig>

    <subConfig id = "stemtitleword-idx">
        <objectType>index.ProximityIndex</objectType>
        <paths>
            <object type="indexStore" ref="indexStore"/>
        </paths>
        <source>
            <xpath>titleproper</xpath>
            <process>
                <object type="extractor" ref="ProxExtractor" />
                <object type="tokenizer" ref="RegexpFindOffsetTokenizer"/>
                <object type="tokenMerger" ref="OffsetProxTokenMerger"/>
                <object type="normalizer" ref="CaseNormalizer"/>
                <object type="normalizer" ref="PossessiveNormalizer"/>
                <object type="normalizer" ref="EnglishStemNormalizer"/>
            </process>
        </source>
    </subConfig>


Explanation
-----------

Lines 1 and 2, 19 and 20 should be second nature by now. Line 4 and the same in
line 22 are a reference to the :py:class:`~cheshire3.baseObjects.IndexStore` in
which the :py:class:`~cheshire3.baseObjects.Index` will be maintained.

This brings us to the :ref:`config-indexes-elements-source` section starting in
line 6. It must contain one or more xpath elements. These XPaths will be
evaluated against the record to find a node, nodeSet or attribute value. This
is the base data that will be indexed after some processing. In the first case,
we give the full path, but in the second only the final element.

If the records contain XML Namespaces, then there are two approaches available.
If the element names are unique between all the namespaces in the document, you
can simply omit them. For example /srw:record/dc:title could be written as just
/record/title. The alternative is to define the meanings of 'srw' and 'dc' on
the xpath element in the normal xmlns fashion.

After the XPath(s), we need to tell the system how to process the data that
gets pulled out. This happens in the process section, and is a list of objects
to sequentially feed the data through. The first object must be an extractor.
This may be followed by a :py:class:`~cheshire3.baseObjects.Tokenizer` and a
:py:class:`~cheshire3.baseObjects.TokenMerger`. These are used to split
the extracted data into tokens of a particular type, and then merge it into
discreet index entries. If a :py:class:`~cheshire3.baseObjects.Tokenizer` is
used, a :py:class:`~cheshire3.baseObjects.TokenMerger` must also be used.
Generally any further processing objects in the chain are
:py:class:`~cheshire3.baseObjects.Normalizer`\ s.

The first :py:class:`~cheshire3.baseObjects.Index` uses the
:py:class:`~cheshire.extractor.SimpleExtractor` to pull out the text as it
appears exactly as a single term. This is followed by a
:py:class:`~cheshire3.normalizer.SpaceNormalizer` on line 10, to
remove leading and trailing whitespace and normalize multiple adjacent
whitespace characters (e.g. newlines followed by tabs, spaces etc.) into single
whitespaces The second :py:class:`~cheshire3.baseObjects.Index` uses the
``ProxExtractor``; this is a special instance of
:py:class:`~cheshire3.extractor.SimpleExtractor`, that has been configured to
also extract the position of the XML elements from which is extracting. Then
it uses a :py:class:`~cheshire3.tokenizer.RegexpFindOffsetTokenizer` to
identify word tokens, their positions and character offsets. It then uses the
necessary :py:class:`~cheshire3.tokenMerger.OffsetProxTokenMerger` to merge
identical tokens into discreet index entries, maintaining the word positions
and character offsets identified by the Tokenizer. Both indexes then send the
extracted terms to a :py:class:`~cheshire3.normalizer.CaseNormalizer`, which
will reduce all characters to lowercase. The second
:py:class:`~cheshire3.baseObjects.Index` then gives the lowercase terms to a
:py:class:`~cheshire3.normalizer.PossessiveNormalizer` to strip off 's and s'
from the end, and then to
:py:class:`~cheshire3.normalizer.EnglishStemNormalizer` to apply
linguistic stemming.

After these processes have happened, the system will store the transformed
terms in the :py:class:`~cheshire3.baseObjects.IndexStore` referenced in the
:ref:`config-paths` section.

Finally, in the first example, we have a setting called ``sortStore``. When
this is provided and set to a true value, it instructs the system to create a
map of :py:class:`~cheshire3.baseObjects.Record` identifier to terms
enabling the :py:class:`~cheshire3.baseObjects.Index` to be used to quickly
re-order :py:class:`~cheshire3.baseObjects.ResultSet`\ s based on the values
extracted.

For detailed information about
available settings for :py:class:`~cheshire3.baseObjects.Index`\ es see
the :ref:`Index Configuration, Settings section<config-indexes-settings>`.
