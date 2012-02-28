
import re

from urllib import unquote

import cheshire3.cqlParser as cql
from cheshire3.queryFactory import QueryStream


class FieldStorageQueryStream(QueryStream):
    u"""A QueryStream to process queries in web forms.
    
    Takes data from forms initialized as FieldStorage instances.
    """
    
    def __init__(self):
        QueryStream.__init__(self)
        self.phraseRe = re.compile('".*?"')
    
    def parse(self, session, data, codec, db):
        form = data
        qClauses = []
        bools = []
        i = 1
        while 'fieldcont{0}'.format(i) in form:
            boolean = form.getfirst('fieldbool{0}'.format(i-1), 'and/relevant/proxinfo')
            bools.append(boolean)
            i += 1
            
        i = 1
        while 'fieldcont{0}'.format(i) in form:
            cont = form.getfirst('fieldcont{0}'.format(i))
            idxs = unquote(form.getfirst('fieldidx{0}'.format(i), 'cql.anywhere'))
            rel = unquote(form.getfirst('fieldrel{0}'.format(i), 'all/relevant/proxinfo'))
            idxClauses = []
            # in case they're trying to do phrase searching
            if (rel.startswith('exact') or rel.startswith('=') or rel.find('/string') != -1):
                # don't allow phrase searching for exact or /string searches
                cont = cont.replace('"', '\\"')
                
            for idx in idxs.split('||'):
                subClauses = []
                if (rel.startswith('all')):
                    subBool = ' and/relevant/proxinfo '
                else:
                    subBool = ' or/relevant/proxinfo '
                
                # in case they're trying to do phrase searching
                if (rel.find('exact') != -1 or rel.find('=') != -1 or rel.find('/string') != -1):
                    # don't allow phrase searching for exact or /string searches
                    # we already did quote escaping
                    pass 
                else:
                    phrases = self.phraseRe.findall(cont)
                    for ph in phrases:
                        subClauses.append('({0} =/relevant/proxinfo {1})'.format(idx, ph))
                    
                    cont = self.phraseRe.sub('', cont)
                    
                if (idx and rel and cont):
                    subClauses.append('{0} {1} {2}'.format(idx, rel, cont.strip()))
                    
                if (len(subClauses)):
                    idxClauses.append('({0})'.format(subBool.join(subClauses)))
                
            qClauses.append('({0})'.format(' or/rel.combine=sum/proxinfo '.join(idxClauses)))
            # if there's another clause and a corresponding boolean
            try:
                qClauses.append(bools[i])
            except:
                break
            
            i += 1
            
        qString = ' '.join(qClauses)
        formcodec = form.getfirst('_charset_', 'utf-8')
        return cql.parse(qString.decode(formcodec).encode('utf-8'))


streamHash = {
              'www': FieldStorageQueryStream
              }
