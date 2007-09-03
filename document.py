
from baseObjects import Document

# Data:  data, creator, history, filename, offset, length, mimeType, parent
# MARC mimetype is application/marc (RFC2220)

class StringDocument(Document):

    def __init__(self, text, creator="", history=[], mimeType="", parent=None, filename=None, schema="", byteCount=0, byteOffset=0, wordCount=0):
	self.id = None
	self.schema = schema
        self.size = 0
        self.text = text
        self.mimeType = mimeType
	self.filename = filename
        self.wordCount = wordCount
        self.byteCount = byteCount
        self.byteOffset = byteOffset
        self.expires = 0
	if (history):
            self.processHistory = history
        else:
            self.processHistory = []
        if creator:
            self.processHistory.append(creator)
        if parent:
            self.parent = parent

    def get_raw(self):
        return self.text

    def find_exception(self, e):
        # Find the cause of a parse exception as reported by expat
        line = e._linenum - 1
        lines = self.text.split('\n')
        l = lines[line]
        chr = e._colnum
        start = min(0, chr - 10)
        end = min(chr+70, len(l))
        return l[start:end]
