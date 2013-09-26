"""Cheshire3

Cheshire3 is a fast XML search engine, written in Python_ for
extensability and using C libraries for speed. Cheshire3 is feature
rich, including support for XML namespaces, unicode, a distributable
object oriented model and all the features expected of a digital library
system.

Standards are foremost, including SRU_ and CQL_, as well as Z39.50 and
OAI_. It is highly modular and configurable, enabling very specific needs
to be addressed with a minimum of effort. The API_ is stable and fully
documented, allowing easy third party development of components.

Given a set of documents records, Cheshire3 can extract data into one or
more indexes after processing with configurable workflows to add extra
normalization and processing. Once the indexes have been constructed, it
supports such operations as search, retrieve, browse and sort.

The abstract protocolHandler allows integration of Cheshire3 into any
environment that will support Python_. For example using Apache_ handlers
or WSGI_ applications, any interface from standard APIs like SRU_, Z39.50
and OAI_ (all included by default in the cheshire3.web sub-package), to
an online shop front can be provided.


Requirements / Dependencies
---------------------------

Cheshire3 requires Python_ 2.6.0 or later. It has not yet been verified
as Python 3 compliant.

As of the version 1.0 release Cheshire3's python dependencies *should* be
resolved automatically by the standard Python package management
mechanisms (e.g. pip_, `easy_install`_, distribute_/setuptools_).

However on some systems, for example if installing on a machine without
network access, it may be necessary to manually install some 3rd party
dependencies. In such cases we would encourage you to download the
necessary Cheshire3 bundles from the `Cheshire3 download site`_ and install
them using the automated build scripts included. If the automated scripts
fail on your system, they should at least provide hints on how to resolve
the situation.

If you experience problems with dependencies, please get in touch via
the `GitHub issue tracker`_ or wiki_, and we'll do our best to help.


Additional / Optional Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Certain features within the `Cheshire3 Information Framework`_ will have
additional dependencies (e.g. web APIs will require a web application
server). We'll try to maintain an accurate list of these in the module
docstring of the ``__init__.py`` file in each sub-package.

The bundles available from the `Cheshire3 download site`_ should
continue to be a useful place to get hold of the source code for these
pre-requisites.


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

"""


# --- require print() and make all strings unicodes
#from __future__ import print_function
#from __future__ import unicode_literals

import sys, os

# Tests for Python 3.0 incompatibility
#sys.py3kwarning = True

# Ignore md5 DeprecationWarning from PyZ3950.yacc
from warnings import filterwarnings
filterwarnings('ignore',
               'the md5 module is deprecated; use hashlib instead',
               DeprecationWarning,
               'yacc'
               )

import cheshire3.internal

home = os.environ.get("C3HOME")

__name__ = "cheshire3"
__package__ = "cheshire3"
__version__ = "{0}.{1}.{2}".format(*cheshire3.internal.cheshire3Version)
__all__ = ['cqlParser', 'database', 'document', 'documentFactory',
           'documentStore', 'exceptions', 'extractor', 'index', 'indexStore',
           'internal', 'logger', 'normalizer', 'objectStore', 'parser',
           'permissionsHandler', 'preParser', 'protocolMap', 'queryFactory',
           'queryStore', 'record', 'recordStore', 'resultSet',
           'resultSetStore', 'selector', 'server', 'session', 'tokenizer',
           'tokenMerger', 'transformer', 'user', 'utils', 'workflow',
           'xpathProcessor'
           ]

# Check for user-specific Cheshire3 server directory
_user_cheshire3_dir = os.path.expanduser('~/.cheshire3-server') 
if not os.path.exists(_user_cheshire3_dir):
    # Create it and sub-dirs for:
    # Database plugins
    os.makedirs(os.path.join(_user_cheshire3_dir, 'configs', 'databases'))
    # Server-level default stores
    os.makedirs(os.path.join(_user_cheshire3_dir, 'stores'))
    # Server-level logs
    os.makedirs(os.path.join(_user_cheshire3_dir, 'logs'))

# Import sub-packages to initiate on-init hooks
# e.g. to add DocumentStreams, QueryStreams to base factories
for sp in cheshire3.internal.get_subpackages():
    # Don't catch errors here. Each sub-package is responsible for degrading
    # gracefully in absence of dependencies (i.e. don't fail until missing
    # functionality is explicitly called).
    __import__("cheshire3.%s" % sp)
