
import cheshire3.cqlParser as cql
from cheshire3.baseObjects import QueryFactory


class QueryStream(object):
    def parse(self, session, data, codec, db):
        raise NotImplementedError()


class CqlQueryStream(QueryStream):

    def parse(self, session, data, codec, db):
        # XXX check codec, turn into unicode first
        return cql.parse(data)


class Cheshire2QueryStream(QueryStream):
    u"""A QueryStream to process queries in the Cheshire 2 Query Syntax.
    
http://cheshire.berkeley.edu/cheshire2.html#zfind

top        ::= query ['resultsetid' name]
query      ::= query boolean clause | clause 
clause     ::=  '(' query ')'
               | attributes [relation] term
               | resultset
attributes ::= '[' { [set] type '=' value } ']' | name
boolean    ::= 'and' | 'or' | 'not' | (synonyms)
prox       ::= ('!PROX' | (synonyms)) {'/' name}
relation   ::= '>' | '<' | ...

[bib1 1=5, bib1 3=6] > term and title @ fish
    """

    booleans = {
                'AND': 'and',
                '.AND.': 'and',
                '&&': 'and',
                'OR': 'or',
                '.OR.': 'or',
                '||': 'or',
                'NOT': 'not',
                '.NOT.': 'not',
                'ANDNOT': 'not',
                '.ANDNOT.': 'not',
                '!!': 'not'
                }
    
    relations = {
                 '<': '<',
                 'LT': '<',
                 '.LT.': '<',
                 '<=': '<=',
                 'LE': '<=',
                 '.LE.': '<=',
                 '=': '=',
                 '>=': '>=',
                 'GE': '>=',
                 '.GE.': '>=',
                 '>': '>',
                 'GT': '>',
                 '.GT.': '>',
                 #'<>': 6,    currently unsupported in Cheshire3
                 #'!=': 6,
                 #'NE': 6,
                 #'.NE.': 6,
                 '<=>': 'within',
                 'WITHIN': 'within',
                 '.WITHIN.': 'within',
                 # linguistic modifiers
                 '%': 'all/stem',
                 'STEM': 'all/stem',
                 '.STEM.': 'all/stem',
                 '?': 'all/phonetic',
                 '??': 'all/phonetic',
                 'PHON': 'all/phonetic',
                 '.PHON.': 'all/phonetic',
                 # relevance modifiers
                 # Cheshire3's generic relevance algorithm for result ranking
                 '@': 'all/relevant',
                 'REL': 'all/relevant',
                 '.REL.': 'all/relevant',
                 # Berkeley TREC2 algorithm for result ranking
                 '@@': 'all/rel.algorithm=trec2',
                 '.TREC2.': 'all/rel.algorithm=trec2',
                 # Berkeley TREC3 Algorithm for result ranking
                 '.TREC3.': 'all/rel.algorithm=trec3',
                 # Berkeley TREC2 Algorithm for result ranking with blind
                 # relevance feedback
                 '@*': 'all/rel.algorithm=trec2/rel.feedback',
                 '.TREC2FBK.': 'all/rel.algorithm=trec2/rel.feedback',
                 # Okapi BM-25 for result ranking  
                 '@+': 'all/rel.algorithm=okapi',
                 '.OKAPI.': 'all/rel.algorithm=okapi',
                 # TF-IDF for result ranking
                 '@/': 'all/rel.algorithm=tfidf',
                 '.TFIDF.': 'all/rel.algorithm=tfidf',
                 # Lucene Vector Space TFIDF for result ranking
                 '@&': 'all/rel.algorithm=lucene',
                 '.LUCENE.': 'all/rel.algorithm=lucene',
                 # CORI algorithm for result ranking
                 # -- N.B. primarily intended for collection summary data 
                 # (e.g. distributed search)
                 '@#': 'all/rel.algorithm=cori',
                 '.CORI.': 'all/rel.algorithm=cori'
                 }
    
    geoRelations = {'>#<': 'within',
                    '.FULLY_ENCLOSED_WITHIN.': 'within',
                    '<#>': 'encloses',
                    '.ENCLOSES.': 'encloses',
#                    '>=<': 7,
#                    '.OVERLAPS.': 7,
#                    '<>#': 10,
#                    '.OUTSIDE_OF.': 10,
#                    '+-+': 11
#                    '.NEAR.': 11,
#                    '.#.': 12,
#                    '.MEMBERS_CONTAIN.': 12,
#                    '!.#.': 13,
#                    '.MEMBERS_NOT_CONTAIN.': 13,
#                    ':<:': 14,
#                    '.BEFORE.': 14,
#                    ':<=:': 15,
#                    '.BEFORE_OR_DURING.': 15,
#                    ':=:': 16,
#                    '.DURING.': 16,
#                    ':>=:': 17,
#                    '.DURING_OR_AFTER.': 17,
#                    ':>:': 18,
#                    '.AFTER.': 18
                    }
    
    proxBooleans = {
                    '!PROX': (2, 0, 2),  # prox
                    '!ADJ': (2, 0, 2),   # prox/unit=word/distance=1
                    '!NEAR': (20, 0, 2),  # err, what counts as near
                    '!FAR': (20, 0, 4),  # err, what counts as far
                    '!OPROX': (2, 1, 2),  # prox/ordered=1
                    '!OADJ': (2, 1, 2),  # prox/unit=word/distance=1/ordered=1
                    '!ONEAR': (20, 1, 2),  # err, what counts as near
                    '!OFAR': (20, 1, 4)  # err, what counts as far
                    }
    
    def parse(self, session, data, codec, db):
        pass
    
    #- end Cheshire2QueryStream() ---------------------------------------------


class SimpleQueryFactory(QueryFactory):
    
    streamHash = {}

    def __init__(self, session, config, parent):
        QueryFactory.__init__(self, session, config, parent)

    @classmethod
    def register_stream(qf, format, cls):
        qf.streamHash[format] = cls()

    def get_query(self, session, data, format="cql", codec=None, db=None):
        try:
            strm = self.streamHash[format]
        except KeyError:
            raise ValueError("Unknown format: %s" % format)

        query = strm.parse(session, data, codec, db)
        return query


streamHash = {
              'cql': CqlQueryStream
              }

for format, cls in streamHash.iteritems():
    SimpleQueryFactory.register_stream(format, cls)
