
import exceptions


class C3Exception(Exception):

    text = ""

    def __init__(self, text="None"):
        self.reason = text

    def __str__(self):
        return str(self.__class__) + ": " + self.reason

    def __repr__(self):
        return str(self.__class__) + ": " + self.reason


class C3ObjectTypeError(C3Exception):
    pass


class ConfigFileException(C3Exception):
    pass


class FileDoesNotExistException(C3Exception):
    pass


class FileAlreadyExistsException(C3Exception):
    pass


class ObjectDoesNotExistException(C3Exception):
    pass


class ObjectAlreadyExistsException(C3Exception):
    pass


class ObjectDeletedException(C3Exception):

    def __init__(self, deleted):
        self.store = deleted.store.id
        self.id = deleted.id
        self.time = deleted.time
        self.reason = "%s/%s deleted at %s" % (self.store, self.id, self.time)


class QueryException(C3Exception):

    diagnostic = 0

    def __init__(self, text="", diag=0):
        self.reason = text
        self.diagnostic = diag


class PermissionException(C3Exception):
    pass


class IntegrityException(C3Exception):
    pass


class ExternalSystemException(C3Exception):
    pass


class FileSystemException(C3Exception):
    pass


class XMLSyntaxError(C3Exception):
    pass
