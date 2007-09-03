

# This doesn't work any more

class GoogleDocumentStream(HttpDocumentStream):
    portType = None
    total = 0
    current = 0

    def __init__(self, session, stream, format, schema=None, codec=None, factory=None ):
        BaseDocumentStream.__init__(self, session, stream, format, schema, codec, factory)

    def open_stream(self, stream):
        self.key = self.factory.get_setting(None, 'googleKey')
        loc = GoogleSearchServiceLocator()
        kw = {'readerclass' : reader}
        self.portType = loc.getGoogleSearchPort(**kw)
        req = doGoogleSearchWrapper()
        req._key = self.key
        req._q = self.streamLocation
        req._filter = 0
        req._start = 1
        # Need one result or totalResultsCount == 0
        req._maxResults = 10
        req._safeSearch = 0
        req._oe = "latin1"
        req._ie = "latin1"
        req._lr = "lang_en"
        req._restrict = ""
        return req


    def find_documents(self, session, cache=0):
        if cache != 0:
            raise NotImplementedError
        # Ask for 10 and then step through those, then ask for next        
        cont = 1
        current = 0
        while cont:
            self.stream._start = current
            current += 10
            self.response = self.portType.doGoogleSearch(self.stream)

            for i in self.response._return._resultElements:
                try:
                    s = self._fetchStream(i._URL)
                    d = s.read()
                except socket.timeout:
                    data = ""
                yield StringDocument(data)
            if not self.response._return._resultElements:
                cont = 0
        raise StopIteration


