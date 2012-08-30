cheshire3.textmining
====================

30th August 2012 (2012-08-30)


Contents
--------

-  `Description`_
-  `Authors`_
-  `Latest Version`_
-  `Installation`_
-  `Requirements / Dependencies`_
-  `Documentation`_
-  `Bugs, Feature requests etc.`_
-  `Licensing`_

Description
-----------

This sub-package contains objects useful when using Cheshire3 for textmining
including part of speech tagging and syntax parsing.


Authors
-------

Cheshire3 Team at the `University of Liverpool`_:

-  Robert Sanderson
-  **John Harrison** john.harrison@liv.ac.uk
-  Catherine Smith
-  Jerome Fuselier

(Current maintainer in **bold**)


Latest Version
--------------

The textmining sub-package is included by default as part of the main cheshire3
Python_ package. The latest stable version of the Cheshire3 Python_ package is
available from `PyPi - the Python Package Index`:

http://pypi.python.org/pypi/cheshire3/

Bleeding edge source code is under version control and available from the
`Cheshire3 GitHub repository`_:

http://github.com/cheshire3/cheshire3


Installation
------------

The textmining sub-package is included by default as part of the main
cheshire3 Python_ package. Details of how to install Cheshire3 can be found
in the main Cheshire3 README file.

Installation / Setup guidelines for any 3rd party dependencies can be found
in the `Requirements / Dependencies`_ section of this README.


Requirements / Dependencies
---------------------------

Certain Cheshire3 object implementations contained within this sub-package
may require additional 3rd party components to be installed (e.g. Enju_
and Genia_ part-of-speech taggers.)


Natural Language Toolkit
~~~~~~~~~~~~~~~~~~~~~~~~

The `Natural Language Toolkit`_ (NLTK_) dependency should have been
automatically resolved by the standard Python package management mechanisms
(e.g. pip_, `easy_install`_, distribute_/setuptools_). If you find that you
need to install it manually, it is available from:

http://pypi.python.org/pypi/nltk

Cheshire3's use of NLTK_ requires you to download some trained models etc. To
download these, you can use the NLTK_ Downloader command-line tool: ::

    $ python -m nltk.downloader all


Documentation
-------------

Documentation is available on our website:

http://cheshire3.org/docs/

If you downloaded the source code, either as a tarball, or by checking
out the repository, you'll find a copy of the HTML Documentation in the
local docs directory.

There is additional documentation for the source code in the form of
comments and docstrings. Documentation for most default object
configurations can be found within the ``<docs>`` tag in the config XML
for each object. We would encourage users to take advantage of this tag
to provide documentation for their own custom object configurations.


Bugs, Feature requests etc.
---------------------------

Bug reports, feature requests etc. should be made using the `GitHub issue
tracker`_:

https://github.com/cheshire3/cheshire3/issues


Licensing
---------

Copyright © 2005-2012, the `University of Liverpool`_. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

-  Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
-  Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
-  Neither the name of the University of Liverpool nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


.. Links
.. _Python: http://www.python.org/
.. _`Python Package Index`: http://pypi.python.org/pypi/cheshire3
.. _`University of Liverpool`: http://www.liv.ac.uk
.. _`Cheshire3 Information Framework`: http://cheshire3.org
.. _`Cheshire3 GitHub repository`: http://github.com/cheshire3/cheshire3
.. _`GitHub issue tracker`: http://github.com/cheshire3/cheshire3/issues
.. _Enju: http://www.nactem.ac.uk/enju/
.. _Genia: http://www.nactem.ac.uk/GENIA/tagger/
.. _`Natural Language Toolkit`: http://nltk.org
.. _NLTK: http://nltk.org


