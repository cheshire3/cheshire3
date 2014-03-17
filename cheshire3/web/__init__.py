"""Cheshire3 web sub-package

Using Apache handlers, any interface from a shop front, to Z39.50 to
OAI can be provided (all included by default), but the abstract
protocolHandler allows integration into any environment that will
support Python.

This sub-package requires the base cheshire3 module.
"""


__all__ = ['srwExtensions']

import cheshire3.web.srwExtensions

from cheshire3.documentFactory import SimpleDocumentFactory, AccumulatingDocumentFactory
from cheshire3.queryFactory import SimpleQueryFactory

from cheshire3.web.documentFactory import streamHash, accStreamHash
from cheshire3.web.queryFactory import streamHash as qStreams

# Register web sub-package streams base Factories

# DocumentStreams
for (k,v) in streamHash.items():
    # register_stream is an @classmethod
    SimpleDocumentFactory.register_stream(k, v)

# AccumulatingDocumentStreams 
for (k,v) in accStreamHash.items():
    # register_stream is an @classmethod
    AccumulatingDocumentFactory.register_stream(k, v)

# QueryStreams
for format, cls in qStreams.iteritems():
    # register_stream is an @classmethod
    SimpleQueryFactory.register_stream(format, cls)
