
from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Transformer
from cheshire3.document import StringDocument
from cheshire3.utils import nonTextToken
from cheshire3.marc_utils import MARC

import os.path, time


class FilepathTransformer(Transformer):
    """ Returns record.id as an identifier, in raw SAX events. For use as the inTransformer of a recordStore """
    def process_record(self, session, rec):
        sax = ['1 identifier {}', '3 ' + str(rec.id), '2 identifier']
        data = nonTextToken.join(sax)
        return StringDocument(data)

# Simplest transformation ...
class XmlTransformer(Transformer):
    """ Return the raw XML string of the record """
    def process_record(self,session, rec):
        return StringDocument(rec.get_xml(session))


class SaxTransformer(Transformer):
    def process_record(self, session, rec):
        sax = [x.encode('utf8') for x in rec.get_sax(session)]
        sax.append("9 " + pickle.dumps(rec.elementHash))
        data = nonTextToken.join(sax)       
        return StringDocument(data)

# --- XSLT Transformers ---

from lxml import etree

def myTimeFn(dummy):
    # call as <xsl:value-of select="c3fn:now()"/>
    # with c3fn defined as http://www.cheshire3.org/ns/xsl/
    return time.strftime("%Y-%m-%dT%H:%M:%SZ")

class LxmlXsltTransformer(Transformer):
    """ XSLT transformer using Lxml implementation. Requires LxmlRecord """

    _possiblePaths = {'xsltPath' : {'docs' : "Path to the XSLT file to use."}}
    
    _possibleSettings = {'parameter' : {'docs' : "Parameters to be passed to the transformer."}}

    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        xfrPath = self.get_path(session, "xsltPath")
        dfp = self.get_path(session, "defaultPath")
        path = os.path.join(dfp, xfrPath)
        
        ns = etree.FunctionNamespace('http://www.cheshire3.org/ns/xsl/')
        ns['now'] = myTimeFn
        self.functionNamespace = ns
        self.parsedXslt = etree.parse(path)
        self.txr = etree.XSLT(self.parsedXslt)
        self.params = None
        parameter = self.get_setting(session, 'parameter', None)
        if (parameter):
            self.params = {}
            kv = parameter.split(' ')
            for pair in kv:
                (k, v) = pair.split(':')
                self.params[k] = '"%s"' % v
                

    def process_record(self, session, rec):
        # return StringDocument
        dom = rec.get_dom(session)
        if (session.environment == 'apache'):
            self.txr = etree.XSLT(self.parsedXslt)
            
        if self.params:
            result = self.txr(dom, **self.params)
        else:
            result = self.txr(dom)
        return StringDocument(str(result))


#converts records in marc21xml to marc records 
class MarcTransformer(Transformer):
    
    def __init__(self, session, config, parent):       
        Transformer.__init__(self, session, config, parent)
        self.session = session
    
    def _process_tagName(self, tagname):
        for i, c in enumerate(tagname):
            if c != '0':
                return int(tagname[i:])

    def process_record(self, session, rec):
        fields = {}
        tree = rec.get_dom(session)
        try:
            walker = tree.getiterator("controlfield")
        except AttributeError:
            # lxml 1.3 or later
            walker = tree.iter("controlfield")  
        for element in walker:
            tag = self._process_tagName(element.get('tag'))
            contents = element.text
            if tag in fields:
                fields[tag].append(contents)
            else:
                fields[tag] = [contents]
                
        try:
            walker = tree.getiterator("datafield")
        except AttributeError:
            # lxml 1.3 or later
            walker = tree.iter("datafield")  
        for element in walker:
            tag = self._process_tagName(element.get('tag'))
            try:
                children = element.getiterator('subfield')
            except AttributeError:
                # lxml 1.3 or later
                walker = element.iter('subfield') 
            subelements = [(c.get('code'), c.text) for c in children]
            contents = (element.get('ind1'), element.get('ind2'), subelements)         
            if tag in fields:
                fields[tag].append(contents)
            else:
                fields[tag] = [contents] 

        leader = tree.xpath('//leader')[0]
        l = leader.text
        fields[0] = [''.join([l[5:9], l[17:20]])]
        marcObject = MARC()
        marcObject.fields = fields
        return StringDocument(marcObject.get_MARC())

          

