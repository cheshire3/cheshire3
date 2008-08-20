
import re
import cheshire3.cqlParser as cql
from cheshire3.baseObjects import QueryFactory

class QueryStream(object):
    def parse(self, session, data, codec, db):
        raise NotImplementedError()

class CqlQueryStream(QueryStream):

    def parse(self, session, data, codec, db):
        # XXX check codec, turn into unicode first
        return cql.parse(data)


class FieldStorageQueryStream(QueryStream):
    
    def __init__(self):
        QueryStream.__init__(self)
        self.phraseRe = re.compile('".+?"')
    
    def parse(self, session, data, codec, db):
        qClauses = []
        bools = []
        i = 1
        while (form.has_key('fieldcont%d' % i)):
            bools.append(form.getfirst('fieldbool%d' % (i-1), 'and/relevant/proxinfo'))
            i += 1
            
        i = 1
        while (form.has_key('fieldcont%d' % i)):
            cont = form.getfirst('fieldcont%d' % i)
            idxs = cgi_decode(form.getfirst('fieldidx%d' % i, 'cql.anywhere'))
            rel = cgi_decode(form.getfirst('fieldrel%d'  % i, 'all/relevant/proxinfo'))
            idxClauses = []
            for idx in idxs.split('||'):
                subClauses = []
                if (rel[:3] == 'all'): subBool = ' and/relevant/proxinfo '
                else: subBool = ' or/relevant/proxinfo '
        
                # in case they're trying to do phrase searching
                if (rel.find('exact') != -1 or rel.find('=') != -1 or rel.find('/string') != -1):
                    # don't allow phrase searching for exact or /string searches
                    cont = cont.replace('"', '\\"')
                else:
                    phrases = self.phraseRe.findall(cont)
                    for ph in phrases:
                        subClauses.append('(%s =/relevant/proxinfo %s)' % (idx, ph))
                    
                    cont = self.phraseRe.sub('', cont)
                         
                if (idx and rel and cont):
                    subClauses.append('%s %s "%s"' % (idx, rel, cont.strip()))
                    
                if (len(subClauses)):
                    idxClauses.append('(%s)' % (subBool.join(subClauses)))
                
            qClauses.append('(%s)' % (' or/relevant/proxinfo '.join(idxClauses)))
            # if there's another clause and a corresponcding boolean
            try: qClauses.append(bools[i])
            except: break
            
            i += 1
            
        qString = ' '.join(qClauses)
        formcodec = form.getfirst('_charset_', 'utf-8')
        return cql.parse(qString.decode(formcodec).encode('utf-8'))

    #- end FieldStorageQueryStream() ------------------------------------------
    

class SimpleQueryFactory(QueryFactory):

    def __init__(self, session, config, parent):
        QueryFactory.__init__(self, session, config, parent)
        self.queryHash = {
                          'cql' : CqlQueryStream()
                         ,'www': FieldStorageQueryStream()
                         }

    def get_query(self, session, data, format="cql", codec=None, db=None):
        try:
            strm = self.queryHash[format]
        except KeyError:
            raise ValueError("Unknown format: %s" % format)

        query = strm.parse(session, data, codec, db)
        return query
