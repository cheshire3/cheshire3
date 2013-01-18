
import exceptions


class C3Exception(Exception):

    text = ""

    def __init__(self, text="None"):
        self.reason = text

    def __str__(self):
        return "{0.__class__.__name__}: {0.reason}".format(self)

    def __repr__(self):
        return "{0.__class__.__name__}: {0.reason}".format(self)


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


class MissingDependencyException(C3Exception):
    
    def __init__(self, objectType="Unknown", dependencies=None):
        if isinstance(dependencies, list):
            self.dependencies = dependencies
        elif isinstance(dependencies, basestring):
            self.dependencies = [dependencies]
        else:
            self.dependencies = ['Unknown']
        depStr = ", ".join(["'{0}'".format(d) for d in self.dependencies])
        self.reason = ("Missing dependency/dependencies {0} for object of "
                       "type '{1}'".format(depStr, objectType)
                       )
