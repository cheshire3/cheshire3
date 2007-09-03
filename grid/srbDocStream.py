

from documentFactory import RemoteDocumentStream, MultipleDocumentStream

# XXX Should go to grid package
class SrbDocumentStream(RemoteDocumentStream, MultipleDocumentStream):
    # SRB://user.domain:pass@host:port/path/to/object?DEFAULTRESOURCE=res
    pass

