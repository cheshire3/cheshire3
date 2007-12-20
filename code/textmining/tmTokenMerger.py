from tokenMerger import SimpleTokenMerger

class PosPhraseTokenMerger(SimpleTokenMerger):

    _possibleSettings = {'regexp' : {'docs' : 'Regular expression to match phrases'},
                         'pattern' : {'docs' : 'Pattern to match phrases. Possible components: JJ NN * + ?'},
                         'minimumWords' : {'docs' : "Minimum number of words that constitute a phrase.", 'type' : int, 'options' : "0|1|2|3|4|5"},
                         'subPhrases' : {'docs' : "Extract all sub-phrases (1) or not (0, default)", 'type' : int, 'options' : "0|1"}
                         }

    def __init__(self, session, config, parent):
        SimpleNormalizer.__init__(self, session, config, parent)
        match = self.get_setting(session, 'regexp', '')
        if not match:
            match = self.get_setting(session, 'pattern')
            if not match:
                match = "((?:[ ][^\\s]+/JJ[SR]?)*)((?:[ ][^\\s]+/NN[SP]?)+)"
            else:
                match = match.replace('*', '*)')
                match = match.replace('+', '+)')
                match = match.replace('?', '?)')        
                match = match.replace('JJ', '((?:[ ][^\\s]+/JJ[SR]?)')
                match = match.replace('NN', '((?:[ ][^\\s]+/NN[SP]*)')
        self.pattern = re.compile(match)
        self.strip = re.compile('/(JJ[SR]?|NN[SP]*)')
        self.minimum = self.get_setting(session, 'minimumWords', 0)
        self.subPhrases = self.get_setting(session, 'subPhrases', 0)


    def process_string(self, session, data):
        # input is tagged string, pre keywording
        # output: hash of phrases
        kw = {}
        has = kw.has_key
        strp = self.strip.sub
        minm = self.minimum
        matches = self.pattern.findall(data)
        for phrase in matches:
            phrases = []
            if type(phrase) == tuple:
                phrase = ' '.join(phrase)
            phrase = phrase.strip()
            # Strip tags
            if self.subPhrases:
                # find all minimum+ length sub phrases that include a noun
                words = phrase.split()
                idx = 0
                while idx < len(words)+1:
                    idx2 = idx+1
                    while idx2 < len(words)+1:
                        curr = words[idx:idx2]                        
                        phrase = ' '.join(curr)
                        noun = (phrase.find('/NN') > -1)
                        if len(curr) >= minm and noun:
                            phrases.append(phrase)
                        idx2 += 1
                    idx += 1
            else:
                phrases = [phrase]

            for phrase in phrases:
                phrase = strp('', phrase)
                phrase = phrase.strip()
                if not minm or phrase.count(' ') >= minm -1:
                    if has(phrase):
                        kw[phrase]['occurences'] += 1
                    else:
                        kw[phrase] = {'text' : phrase, 'occurences' : 1, 'positions' : []}
                    

        return kw
        
    
