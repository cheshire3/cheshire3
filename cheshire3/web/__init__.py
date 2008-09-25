
__all__ = ['srwExtensions']

import cheshire3.web.srwExtensions
import sys


# Register our streams with main docFac
# register_stream is an @classmethod
from cheshire3.web.documentFactory import streamHash
from cheshire3.documentFactory import SimpleDocumentFactory
for (k,v) in streamHash.items():
    SimpleDocumentFactory.register_stream(k, v)
