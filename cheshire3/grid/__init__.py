"""Cheshire3 support for the data grid.

Data grid (SRB and iRODS) support for Cheshire3 XML Search, Retrieval and
Information Analysis Engine.
"""

__all__ = ['mpiProtocolHandler', 'pvmProtocolHandler', 'documentFactory',
           'irodsStore', 'irods_utils', 'user',
           'srbDocStream', 'srbErrors', 'srbIndex', 'srbStore']

from cheshire3.documentFactory import SimpleDocumentFactory

from cheshire3.grid.documentFactory import streamHash

# Register sub-package streams with base Factories

# DocumentStreams
for format_ in streamHash:
    # register_stream is an @classmethod
    SimpleDocumentFactory.register_stream(format_, streamHash[format_])
