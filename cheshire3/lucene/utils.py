
try:
    import lucene
except ImportError:
    pass
else:
    
    class NullC3Analyzer(lucene.PythonAnalyzer):
    
        def tokenStream(self, fieldName, reader):
            print fieldName
            print reader
            
    
    class SimpleTokenStream(lucene.PythonTokenStream):
        def __init__(self, terms, incrs=[]):
            super(SimpleTokenStream, self).__init__()
            self.tokens = terms
            self.increments = incrs            
            self.i = 0
            
        def next(self):
            if self.i == len(self.tokens):
                return None
            t = lucene.Token(self.tokens[self.i], self.i, self.i)
            # t.setPositionIncrement(n)   -- num words from last token, dflt 1
            self.i += 1
            return t
    
        def reset(self):
            self.i = 0
    
        def close(self):
            pass
    
    
    class C3TokenStream(lucene.PythonTokenStream):
        def __init__(self, terms):
            super(C3TokenStream, self).__init__()
    
            self.termHash = terms
    
            ol = []        
            try:
                for item in terms.values():
                    ol.extend([(item['text'], y)
                               for y
                               in item['positions'][1:2]])
                ol.sort(key=lambda x: x[1])
                self.tokens = [x[0] for x in ol]
                incs = []
                for idx in range(len(ol)):                
                    try:
                        incs.append(ol[idx] - ol[idx-1])
                    except:
                        # first position
                        incs.append(1)                    
                self.increments = incs
    
            except KeyError:
                # no positions
                for item in terms.values():
                    ol.extend([item['text']] * item['occurences'])
                self.tokens = ol
                self.increments = [1 * len(ol)]
    
            self.i = 0
            
        def next(self):
            if self.i == len(self.tokens):
                return None
            t = lucene.Token(self.tokens[self.i], self.i, self.i)
            t.setPositionIncrement(self.increments[self.i])
            self.i += 1
            return t
    
        def reset(self):
            self.i = 0
    
        def close(self):
            pass


def cqlToLucene(session, query, config):
    # parsed CQL query, produce Lucene Query String
    # (date < 2000 and title = fish) or subject any "squirrel bat"
    # --> ( +date:{0000 TO 2000} +title:fish) (title:squirrel title:bat)
    # title = "military intelligence"
    # spanNear([title:military title:intelligence],0,true)

    if hasattr(query, 'boolean'):
        # dealing with AND/OR/NOT/PROX
        lt = cqlToLucene(session, query.leftOperand, config)
        rt = cqlToLucene(session, query.rightOperand, config)
        if query.boolean.value == 'and':
            qstr = "(+%s +%s)" % (lt, rt)
        elif query.boolean.value == 'or':
            qstr = "(%s %s)" % (lt, rt)
        elif query.boolean.value == 'not':
            qstr = "(+%s -%s)" % (lt, rt)
        elif query.boolean.value == "prox":
            raise NotImplementedError()
        return qstr
        
    else:
        # dealing with searchClause

        # resolve to index
        idxo = config.resolveIndex(session, query)
        idx = idxo.id

        # process as per document terms
        res = {}
        for src in idxo.sources.get(query.relation.toCQL(),
                                    idxo.sources.get(query.relation.value,
                                                     idxo.sources[u'data'])):
            res.update(src[1].process(session, [[query.term.value]]))
        wds = res.keys()

        if query.relation.value == 'any':
            s = ['(']
            for w in wds:
                s.append('%s:%s' % (idx, w))
            s.append(')')
            qstr = ' '.join(s)
        elif query.relation.value in ['all', '=']:
            s = ['(']
            for w in wds:
                s.append('+%s:%s' % (idx, w))
            s.append(')')
            qstr = ' '.join(s)
        elif query.relation.value == 'exact':
            qstr = '%s:%s' % (idx, wds[0])
        elif query.relation.value == 'adj':
            s = []
            for w in wds:
                s.append('%s:%s' % (idx, w))
            qstr = "spanNear([%s],0,true)" % ' '.join(s)
        elif query.relation.value in ["<", "<="]:
            qstr = "%s:{0 TO %s}" % (idx, wds[0])
        elif query.relation.value in [">", ">="]:
            qstr = "%s:{%s TO \x7f}" % (idx, wds[0])
        else:
            raise NotImplementedError()
        return qstr
