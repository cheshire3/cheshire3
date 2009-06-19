
__all__ = ['srwExtensions']

import cheshire3.web.srwExtensions
import sys


# Register our streams with main docFac
# register_stream is an @classmethod
from cheshire3.web.documentFactory import streamHash, accStreamHash
from cheshire3.documentFactory import SimpleDocumentFactory, AccumulatingDocumentFactory
for (k,v) in streamHash.items():
    SimpleDocumentFactory.register_stream(k, v)
    
for (k,v) in accStreamHash.items():
    AccumulatingDocumentFactory.register_stream(k, v)
