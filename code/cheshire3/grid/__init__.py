
__all__ = ['mpiProtocolHandler', 'pvmProtocolHandler', 'documentFactory', 'irodsStore', 'irods_utils', 'user', 'srbDocStream', 'srbErrors', 'srbIndex', 'srbStore']

# Register our streams with main docFac
# register_stream is an @classmethod
from cheshire3.grid.documentFactory import streamHash
from cheshire3.documentFactory import SimpleDocumentFactory
for (k,v) in streamHash.items():
    SimpleDocumentFactory.register_stream(k, v)
