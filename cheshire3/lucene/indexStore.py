
from cheshire3.baseObjects import IndexStore
from cheshire3.resultSet import SimpleResultSet, SimpleResultSetItem
from cheshire3.exceptions import MissingDependencyException

try:
    import lucene
except ImportError:

    class LuceneIndexStore(IndexStore):
    
        def __init__(self, session, config, parent):
            IndexStore.__init__(self, session, config, parent)
            raise MissingDependencyException(self.objectType, "lucene")

else:

    from cheshire3.lucene.utils import NullC3Analyzer, C3TokenStream
    from cheshire3.lucene.utils import cqlToLucene

    class LuceneIndexStore(IndexStore):
    
        def __init__(self, session, config, parent):
            IndexStore.__init__(self, session, config, parent)
            path = self.get_path(session, 'defaultPath')
            self.analyzer = NullC3Analyzer()
            self.dir = lucene.FSDirectory.getDirectory(path, False)
            self.parser = lucene.QueryParser("", lucene.StandardAnalyzer())
            self.searcher = lucene.IndexSearcher(self.dir)
    
            self.writer = None
            self.currDoc = None
            self.currRec = None
    
        def create_index(self, session, index):
            # created in begin_indexing()
            pass
            
        def begin_indexing(self, session, index):
            # will append if exists, or create if not
            if not self.writer:
                self.writer = lucene.IndexWriter(self.dir, self.analyzer, lucene.IndexWriter.MaxFieldLength.UNLIMITED)
    
        def commit_indexing(self, session, index):
            if self.currDoc:
                self.writer.addDocument(self.currDoc)
                self.currDoc = None
            elif self.writer:
                self.writer.optimize()
                self.writer.close()
                self.writer = None
            print "called commit"
    
        def store_terms(self, session, index, terms, rec):
            strm = C3TokenStream(terms)
            if rec != self.currRec:
                if self.currDoc:
                    # write it
                    self.writer.addDocument(self.currDoc)
                doc = lucene.Document()
                self.currDoc = doc
                doc.add(lucene.Field(index.id, strm))
                doc.add(lucene.Field('id', str(rec),
                                     lucene.Field.Store.YES,
                                     lucene.Field.Index.UN_TOKENIZED))
            else:
                doc.add(lucene.Field(index.id, strm))
    
        def search(self, session, query, db):
            # take CQL query and translate to Lucene
            pm = db.get_path(session, 'protocolMap')
            if not pm:
                db._cacheProtocolMaps(session)
                pm = db.protocolMaps.get('http://www.loc.gov/zing/srw/')
            query.config = pm
            lq = cqlToLucene(session, query, pm)
            q = self.parser.parse(lq)
            results = self.searcher.search(q, lucene.Sort.RELEVANCE)
    
            # now map to a ResultSet
            items = []
            for x in range(len(results)):
                hit = results[x]
                w = results.score(x)
                rsid = hit.getField('id').stringValue()
                (recStore, id) = rsid.split('/')
                if id.isdigit():
                    id = int(id)
                rsi = SimpleResultSetItem(session, id, recStore, weight=w)
                items.append(rsi)
                
            rs = SimpleResultSet(session, items)        
            return rs
    
        def index_record(self, session, rec):
            pass
    
        def delete_record(self, session, rec):
            pass
    
        def fetch_term(self, session, term, summary, prox):
            pass
    
        def fetch_summary(self, session, index):
            raise NotImplementedError()
