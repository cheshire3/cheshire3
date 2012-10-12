"""Cheshire3 Textmining Extractor Implementations."""

from __future__ import with_statement

import os

from pkg_resources import Requirement, resource_filename

# NLTK
from nltk import config_megam
from nltk.chunk import ne_chunk
from nltk.chunk.api import ChunkParserI
from nltk.chunk.named_entity import simplify_pos, shape
from nltk.chunk.util import ChunkScore 
from nltk.classify import MaxentClassifier
from nltk.stem.porter import PorterStemmer
from nltk.tag import ClassifierBasedTagger, pos_tag
from nltk.tokenize import (sent_tokenize as tokenize_sentences,
                           word_tokenize as tokenize_words)
from nltk.tree import Tree as NLTKParseTree

# Cheshire
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
        for data in simpleHash:
            occs = simpleHash[data]['occurences']
            proxLoc = simpleHash[data]['proxLoc']
            # Tokenize sentences
            for sent in tokenize_sentences(data):
                # Tokenize words
                tokens = tokenize_words(sent)
                # Tag words with Parts of Speech
                tagged = pos_tag(tokens)
                # Identify named entities
                entities = ne_chunk(tagged)
                for ent in entities:
                    if isinstance(ent, NLTKParseTree):
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


class EventChunkParserTagger(ClassifierBasedTagger):
    """An IOB tagger for events to be used by a chunker.
    
    Tagging is performed using a maximum entropy classifier model.
    """
    
    # The size of window either side of a token to take into consideration 
    window = 3
    
    def __init__(self, train):
        self.stemmer = PorterStemmer()
        ClassifierBasedTagger.__init__(
            self,
            train=train,
            classifier_builder=self._classifier_builder)

    def _classifier_builder(self, train):
        return MaxentClassifier.train(train,
                                      algorithm='megam',
                                      gaussian_prior_sigma=1,
                                      trace=2)

    def _english_wordlist(self):
        try:
            wl = self._en_wordlist
        except AttributeError:
            from nltk.corpus import words
            wl = self._en_wordlist = set(words.words('en-basic'))
        return wl
    
    def _feature_detector(self, tokens, index, history):
        try:
            word, pos = tokens[index]
        except ValueError:
            print tokens[index]
            raise
        simple_pos = simplify_pos(pos)
        # Get English word list
        wl = self._english_wordlist()
        # Set up simple features
        features = {
            'bias': True,
            'word': word,
            'word_lc': word.lower(),
            'word_len': len(word),
            'word_shape': shape(word),
            'word_stem': self.stemmer.stem(word),
            'word_lc_stem': self.stemmer.stem(word.lower()),
            'word_suffix': word[len(self.stemmer.stem(word)):],
            'word_is_basic_eng': (word in wl),
            'pos': pos,
            'simple_pos': simple_pos
        }
        # Assemble features relating to previous words up to maximum of 5
        for x in range(1, min(index, self.window)):
            wordx, posx = tokens[index - x]
            wordx_stem = self.stemmer.stem(wordx)
            wordx_lc_stem = self.stemmer.stem(wordx.lower())
            features.update({
                'word-{0}'.format(x): wordx,
                'word-{0}_lc'.format(x): wordx.lower(),
                'word-{0}_len'.format(x): len(wordx),
                'word-{0}_shape'.format(x): shape(wordx),
                'word-{0}_stem'.format(x): wordx_stem,
                'word-{0}_lc_stem'.format(x): wordx_lc_stem,
                'word-{0}_suffix'.format(x): word[len(wordx_stem):],
                'word-{0}_is_basic_eng'.format(x): (wordx in wl),
                'pos-{0}'.format(x): posx,
                'simple-pos-{0}'.format(x): simplify_pos(posx),
                'tag-{0}'.format(x): history[index - x][0]
            })
        # Assemble features relating to subsequent words up to maximum of 5
        for x in range(index + 1, min(len(tokens), index + self.window)):
            wordx, posx = tokens[x]
            wordx_stem = self.stemmer.stem(wordx)
            wordx_lc_stem = self.stemmer.stem(wordx.lower())
            features.update({
                'word-{0}'.format(x): wordx,
                'word-{0}_lc'.format(x): wordx.lower(),
                'word-{0}_len'.format(x): len(wordx),
                'word-{0}_shape'.format(x): shape(wordx),
                'word-{0}_stem'.format(x): wordx_stem,
                'word-{0}_lc_stem'.format(x): wordx_lc_stem,
                'word-{0}_suffix'.format(x): word[len(wordx_stem):],
                'word-{0}_is_basic_eng'.format(x): (wordx in wl),
            })
        return features


class EventChunkParser(ChunkParserI):
    """NLTK Chunk Parser implementation to chunk Events."""

    def __init__(self, train):
        self._train(train)

    def _train(self, corpus):
        corpus = [self._parse_to_tagged(s) for s in corpus]
        self._tagger = EventChunkParserTagger(train=corpus)

    @staticmethod
    def _tagged_to_parse(tagged_tokens):
        """Convert a list of tagged tokens to a chunk-parse Tree."""
        tree = NLTKParseTree('TEXT', [])
        sent = NLTKParseTree('S', [])
        for ((token, pos), tag) in tagged_tokens:
            if tag == 'O':
                sent.append((token, pos))
                if pos == '.':
                    # End of sentence, add to main tree
                    tree.append(sent)
                    # Start a new subtree
                    sent = NLTKParseTree('S', [])
            elif tag.startswith('B-'):
                sent.append(NLTKParseTree(tag[2:], [(token, pos)]))
            elif tag.startswith('I-'):
                if (sent and isinstance(sent[-1], NLTKParseTree) and
                    sent[-1].node == tag[2:]):
                    sent[-1].append((token, pos))
                else:
                    sent.append(NLTKParseTree(tag[2:], [(token, pos)]))
        if sent:
            tree.append(sent)
        return tree

    @staticmethod
    def _parse_to_tagged(sentence):
        """Convert a chunk-parse Tree to a list of tagged tokens."""
        toks = []
        for child in sentence:
            if isinstance(child, NLTKParseTree):
                if len(child) == 0:
                    print "Warning -- empty chunk in sentence"
                    continue
                toks.append((child[0], 'B-%s' % child.node))
                for tok in child[1:]:
                    if isinstance(tok, basestring):
                        tok = tuple(tok.split('/', 1))
                    toks.append((tok, 'I-%s' % child.node))
            else:
                if isinstance(child, basestring):
                    child = tuple(child.split('/', 1))
                toks.append((child, 'O'))
        return toks
    
    def parse(self, tokens):
        """Parse tokens and return a chunk-parse Tree.
        
        Expected input: list of PoS-tagged tokens.
        """
        tagged = self._tagger.tag(tokens)
        tree = self._tagged_to_parse(tagged)
        return tree


def load_data(root, format_="raw"):
    for root, dirs, files in os.walk(os.path.join(root, format_)):
        for f in files:
            yield load_file(os.path.join(root, f), format_)


def load_file(filepath, format_):
    with open(filepath, 'r') as fh:
        if format_ == "raw":
            return fh.read()
        elif format_ == "tagged":
            tagged_tokens = []
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        tok, pos, tag = line.split()
                    except ValueError:
                        print line
                        raise
                    tagged_tokens.append(((tok, pos), tag))
            return tagged_tokens
        elif format_ == "parsed":
            data = fh.read()
            return NLTKParseTree(data)
        else:
            return "unsupported format {0}".format(format_)


def load_training_data(format_="raw"):
    return load_data(_EVENT_TRAIN_DATA_PATH, format_)


def load_evaluation_data(format_="raw"):
    return load_data(_EVENT_EVAL_DATA_PATH, format_)


def _raw_data_to_tagged(overwrite=False):
    # Take raw data and put it into a suitable format for manual tagging
    for root, dirs, files in os.walk(os.path.join(_EVENT_EVAL_DATA_PATH,
                                                  "raw")):
        for f in files:
            data = load_file(os.path.join(root, f), "raw")
            tagged_fn = os.path.splitext(f)[0] + '.tagged'
            tagged_filepath = os.path.join(_EVENT_EVAL_DATA_PATH,
                                           "tagged",
                                           tagged_fn) 
            if os.path.exists(tagged_filepath) and not overwrite:
                print ("file {0} already exists, skipping..."
                       "".format(tagged_filepath))
                continue
            with open(tagged_filepath, 'w') as tagged_fh:
                for sent in tokenize_sentences(data):
                    for token, tag in pos_tag(tokenize_words(sent)):
                        tagged_fh.write(token.ljust(24))
                        tagged_fh.write(tag.ljust(8))
                        tagged_fh.write('O\n')
                    tagged_fh.write('\n')


def _tagged_data_to_parsed(overwrite=False):
    # Take tagged data and covert it to parsed Trees in files
    for root, dirs, files in os.walk(os.path.join(_EVENT_EVAL_DATA_PATH,
                                                  "tagged")):
        for f in files:
            parsed_fn = os.path.splitext(f)[0] + '.parsed'
            parsed_filepath = os.path.join(_EVENT_EVAL_DATA_PATH,
                                           "parsed",
                                           parsed_fn)
            if os.path.exists(parsed_filepath) and not overwrite:
                print ("file {0} already exists, skipping..."
                       "".format(parsed_filepath))
                continue
            tree = NLTKParseTree("TEXT", [])
            tagged_tokens = load_file(os.path.join(root, f), "tagged")
            tree = EventChunkParser._tagged_to_parse(tagged_tokens)
            with open(parsed_filepath, 'w') as parsed_fh:
                parsed_fh.write(tree.pprint())


def split_tree_tokens(tree):
    """Process a chunk-parse Tree, splitting nodes in the form "token/POS".
    
    Returns a similar tree in which the leaves are PoS tagged tokens in the
    form:
    ("token", "TAG")
    """
    token_iter = (tuple(token.split('/')) for token in tree.leaves())
    newtree = NLTKParseTree(tree.node, [])
    for child in tree:
        if isinstance(child, NLTKParseTree):
            newtree.append(NLTKParseTree(child.node, []))
            for subchild in child:
                newtree[-1].append(token_iter.next())
        else:
            newtree.append(token_iter.next())
    return newtree


def cmp_chunks(correct, guessed):
    correct = EventChunkParser._parse_to_tagged(correct)
    guessed = EventChunkParser._parse_to_tagged(guessed)
    ellipsis = False
    for (w, ct), (w, gt) in zip(correct, guessed):
        if ct == gt == 'O':
            if not ellipsis:
                print "  %-15s %-15s %s" % (ct, gt, w)
                print '  %-15s %-15s %s' % ('...', '...', '...')
                ellipsis = True
        else:
            ellipsis = False
            print "  %-15s %-15s %s" % (ct, gt, w)


def build_event_chunking_model():
    # Assemble training data, splitting token/PoS pairs
    train_corpus = []
    for tree in load_training_data('parsed'):
        for sentence_tree in tree:
            newtree = split_tree_tokens(sentence_tree)
            train_corpus.append(newtree)
    # Train chunker
    chunker = EventChunkParser(train_corpus)
    del train_corpus
    # Load evaluation data, splitting token/PoS pairs
    eval_corpus = []
    for tree in load_evaluation_data('parsed'):
        for sentence_tree in tree:
            eval_corpus.append(split_tree_tokens(sentence_tree))
    # Evaluate model
    print 'Evaluating...'
    chunkscore = ChunkScore()
    for i, correct in enumerate(eval_corpus):
        guessed = chunker.parse(correct.leaves())
        guessed = chunker._parse_to_tagged(guessed)
        chunkscore.score(correct, guessed)
        if i < 3:
            cmp_chunks(correct, guessed)
    print chunkscore
    return chunker


_EVENT_TRAIN_DATA_PATH = resource_filename(
    Requirement.parse('cheshire3'),
    'cheshire3/data/textmining/events/train')
                                              
_EVENT_EVAL_DATA_PATH = resource_filename(
    Requirement.parse('cheshire3'),
    'cheshire3/data/textmining/events/eval')

config_megam(resource_filename(
    Requirement.parse('cheshire3'),
    'cheshire3/data/textmining/megam_i686.opt'))


if __name__ == "__main__":
    chunker = build_event_chunking_model()
