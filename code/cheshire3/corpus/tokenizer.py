
from cheshire3.baseObjects import Tokenizer
from cheshire3.tokenizer import OffsetTokenizer



class SuppliedOffsetTokenizer(OffsetTokenizer):

    def process_string(self, session, data):
        tokens = []
        positions = []
        for t in data.split():
            tokens.append(t[:t.rfind('/')])
            positions.append(int(t[t.rfind('/')+1:]))
        return (tokens, positions)
