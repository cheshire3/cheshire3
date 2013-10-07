"""Cheshire3 Textmining Extractor Implementations."""

import nltk

from cheshire3.extractor import SimpleExtractor
from cheshire3.exceptions import ConfigFileException


class NLTKNamedEntityExtractor(SimpleExtractor):
    """Use NLTK to extract Named Entities.
    
    Use NLTK's currently recommended tokenizer, PoS tagger and named entity
    chunker to identify and extract named entities.
    
    Implemented as an Extractor because the process requires full sentences.
    Named entity chunking on generic tokens is likely to give poor results.    
    """

    _possibleSettings = {
        'entityTypes': {
            'docs': ("Space separated list of entity type to keep."
                     "Defaults to all types, i.e. "
                     "'People Places Organizations'")
        },
        'pos': {
            'docs': ("Should the PoS tag be kept (1) or thrown away "
                     "(0)? Default: 0"),
            'type': int,
            'options': "0|1"
        }
    }

    def __init__(self, session, node, parent):
        SimpleExtractor.__init__(self, session, node, parent)
        # Load types from config
        types = self.get_setting(session, 'entityTypes')
        if types:
            self.types = []
            for type_ in types.split():
                type_ = type_.lower()
                if type_.startswith('pe'):
                    self.types.append('PERSON')
                elif type_.startswith(('pl', 'g')):
                    self.types.append('GPE')
                elif type_.startswith(('org', 'co')):
                    self.types.append('ORGANIZATION')
                else:
                    msg = ("Unknown entity type setting {0} on {1} {2}"
                           "".format(type_,
                                     self.__class__.__name__,
                                     self.id)
                           )
                    raise ConfigFileException(msg)
        else:
            # Default to all
            self.types = ['PERSON', 'GPE', 'ORGANIZATION']
        # Should we keep the /POS tag or strip it
        self.keepPos = self.get_setting(session, 'pos', 0)

    def _process_simpleHash(self, simpleHash):
        # Extract entities from keys resulting from SimpleExtractor process_*
        entityHash = {}
        # Setup aliases for NLTK methods
        sent_tokenize = nltk.tokenize.sent_tokenize
        word_tokenize = nltk.tokenize.word_tokenize
        pos_tag = nltk.pos_tag
        ne_chunk = nltk.chunk.ne_chunk
        for data in simpleHash:
            occs = simpleHash[data]['occurences']
            proxLoc = simpleHash[data]['proxLoc']
            # Tokenize sentences
            for sent in sent_tokenize(data):
                # Tokenize words
                tokens = word_tokenize(sent)
                # Tag words with Parts of Speech
                tagged = pos_tag(tokens)
                # Identify named entities
                entities = ne_chunk(tagged)
                for ent in entities:
                    if isinstance(ent, nltk.tree.Tree):
                        # Is it a wanted type?
                        if ent.node in self.types:
                            # Should we keep the PoS tag?
                            if self.keepPos:
                                txts = ['/'.join(token) for token in ent.leaves()]
                            else:
                                txts = [token[0] for token in ent.leaves()]
                            txt = ' '.join(txts)
                            new = {txt: {'text': txt,
                                         'occurences': occs,
                                         'proxLoc': proxLoc[:]}}
                            entityHash = self._mergeHash(entityHash, new)
        return entityHash

    def process_eventList(self, session, data):
        simpleHash = SimpleExtractor.process_eventList(self, session, data)
        return self._process_simpleHash(simpleHash)

    def process_node(self, session, data):
        simpleHash = SimpleExtractor.process_node(self, session, data)
        return self._process_simpleHash(simpleHash)

    def process_string(self, session, data):
        simpleHash = SimpleExtractor.process_string(self, session, data)
        return self._process_simpleHash(simpleHash)
