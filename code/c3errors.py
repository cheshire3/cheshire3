
import exceptions

class C3Exception(Exception):
    text = ""

    def __init__(self, text="None"):
        self.reason = text

    def __str__(self):
        return str(self.__class__) + ": " + self.reason

    def __repr__(self):
        return str(self.__class__) + ": " + self.reason

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


class PermissionException(C3Exception):
    pass

class ExternalSystemException(C3Exception):
    pass

