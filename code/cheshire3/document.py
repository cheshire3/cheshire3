
from cheshire3.baseObjects import Document

# MARC mimetype is application/marc (RFC2220)


class StringDocument(Document):

    def __init__(self, data, creator="", history=[], mimeType="",
                 parent=None, filename=None, tagName="",
                 byteCount=0, byteOffset=0, wordCount=0):
        self.id = None
        self.tagName = tagName
        self.size = 0
        self.text = data
        self.mimeType = mimeType
        self.filename = filename
        self.wordCount = wordCount
        self.byteCount = byteCount
        self.byteOffset = byteOffset
        self.expires = 0
        self.metadata = {}

        if (history):
            self.processHistory = history
        else:
            self.processHistory = []
        if creator:
            self.processHistory.append(creator)
        if parent:
            self.parent = parent

    def get_raw(self, session):
        return self.text

    def find_exception(self, e):
        # Find the cause of a parse exception as reported by expat
        line = e._linenum - 1
        lines = self.text.split('\n')
        l = lines[line]
        chr = e._colnum
        start = min(0, chr - 10)
        end = min(chr + 70, len(l))
        return l[start:end]
