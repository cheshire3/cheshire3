"""Cheshire3 support for the data grid.

Data grid (SRB and iRODS) support for Cheshire3 XML Search, Retrieval and
Information Analysis Engine.
"""

__all__ = ['mpiProtocolHandler', 'pvmProtocolHandler', 'documentFactory', 'irodsStore', 'irods_utils', 'user', 'srbDocStream', 'srbErrors', 'srbIndex', 'srbStore']

# Register our streams with main docFac
# register_stream is an @classmethod
from cheshire3.grid.documentFactory import streamHash
from cheshire3.documentFactory import SimpleDocumentFactory
for (k,v) in streamHash.items():
    SimpleDocumentFactory.register_stream(k, v)
