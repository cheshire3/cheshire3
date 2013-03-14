
import os.path
import types
import time
import re
import bz2

from lxml import etree

from cheshire3.configParser import C3Object
from cheshire3.baseObjects import Transformer, Record, Database, Server
from cheshire3.document import StringDocument
from cheshire3.utils import nonTextToken
from cheshire3.marc_utils import MARC
from cheshire3.exceptions import ConfigFileException


class FilepathTransformer(Transformer):
    """Returns record.id as an identifier, in raw SAX events.
    
    For use as the inTransformer of a recordStore.
    """
    def process_record(self, session, rec):
        sax = ['1 identifier {}', '3 ' + str(rec.id), '2 identifier']
        data = nonTextToken.join(sax)
        return StringDocument(data)


# Simplest transformation ...
class XmlTransformer(Transformer):
    """ Return a Document containing the raw XML string of the record """
    def process_record(self, session, rec):
        return StringDocument(rec.get_xml(session))


class Bzip2XmlTransformer(Transformer):
    """Return a Document containing bzip2 compressed XML.
    
    Return a Document containing the raw XML string of the record, compressed
    using the bzip2 algorithm.
    """
    
    def process_record(self, session, rec):
        data = rec.get_xml(session)
        bzdata = bz2.compress(data)
        return StringDocument(bzdata, self.id)
    

class SaxTransformer(Transformer):
    def process_record(self, session, rec):
        sax = [x.encode('utf8') for x in rec.get_sax(session)]
        sax.append("9 " + pickle.dumps(rec.elementHash))
        data = nonTextToken.join(sax)       
        return StringDocument(data)


class WorkflowTransformer(Transformer):
    """Transformer to execute a workflow."""
    
    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        self.workflow = self.get_path(session, 'workflow')
        
    def process_record(self, session, record):
        u"""Apply Workflow to the Record, return the resulting Document."""
        output = self.workflow.process(session, record)
        if isinstance(output, basestring):
            output = StringDocument(output)
        elif isinstance(output, Record):
            output = StringDocument(output.get_xml(session))
        
        return output


class ComponentParentFetchingTransformer(Transformer):
    """Given a Cheshire3 component, fetch and return the parent Document.
    
    Given a Cheshire3 component Record, fetch and return the data for its
    parent in a new Document.
    """
    
    def process_record(self, session, record):
        # Get RecordStore and identifier of parent record
        try:
            parentId = record.process_xpath(session, '/c3component/@parent')[0]
        except IndexError:
            parentId = record.process_xpath(
                session,
                '/c3:component/@c3:parent',
                maps={'c3': "http://www.cheshire3.org/schemas/component/"}
            )[0]
        recStoreId, parentId = parentId.split('/', 1)
        # Get RecordStore object
        if isinstance(self.parent, Database):
            db = self.parent
        elif isinstance(self.parent, Server) and session.database:
            db = self.parent.get_object(session, session.database)
        elif (
                session.server and
                isinstance(session.server, Server) and
                session.database
        ):
            db = session.server.get_object(session, session.database)
        elif not session.server:
            raise ValueError("No session.server")
        else:
            raise ValueError("No session.database")
        recStore = db.get_object(session, recStoreId)
        # Fetch parent record
        parentRec = recStore.fetch_record(session, parentId)
        # Return a new Document with parent data and identifier
        data = parentRec.get_xml(session)
        doc = StringDocument(
            data,
            self.id,
            byteCount=len(data),
            byteOffset=0
        )
        doc.id = parentId
        return doc


# --- XSLT Transformers ---


def myTimeFn(dummy):
    # call as <xsl:value-of select="c3fn:now()"/>
    # with c3fn defined as http://www.cheshire3.org/ns/function/xsl/
    return time.strftime("%Y-%m-%dT%H:%M:%SZ")
 

class LxmlXsltTransformer(Transformer):
    """XSLT transformer using Lxml implementation. Requires LxmlRecord.
    
    Use Record's resultSetItem's proximity information to highlight query term
    matches.
    """

    _possiblePaths = {
        'xsltPath': {
            'docs': "Path to the XSLT file to use."
        }
    }
    
    _possibleSettings = {
        'parameter': {
            'docs': "Parameters to be passed to the transformer."
        }
    }

    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        xfrPath = self.get_path(session, "xsltPath")
        if xfrPath is None:
            raise ConfigFileException("Missing path 'xsltPath' for "
                                      "{0}.".format(self.id))
        
        if os.path.isabs(xfrPath):
            path = xfrPath
        else:
            dfp = self.get_path(session, "defaultPath")
            path = os.path.join(dfp, xfrPath)
        
        ns = etree.FunctionNamespace(
            'http://www.cheshire3.org/ns/function/xsl/'
        )
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


class LxmlQueryTermHighlightingTransformer(Transformer):
    "Abstract Class for query term highlighting Transformers for LxmlRecords."
    
    HIGHLIGHT_NS = "http://www.cheshire3.org/schemas/highlight/"
    
    _possibleSettings = {
        'highlightTag': {
            'docs': ("Tag to indicate highlighted section (will be inserted "
                     "into output document as: "
                     "<highlightTag>blah blah</highlightTag>)")
        },
        'tagAttrList': {
            'docs': ('Space separated list of attribute name="value" pairs '
                     '(will be inserted into output document as: '
                     '<highlightTag name="value">blah blah</highlightTag>)')
        },
        'breakElementsList': {
            'docs': ('Space separated list of element names to break at when '
                     'tagging Query Terms. This can be useful when a speedy '
                     'response is more important than complete tagging.')
        }
    }
    
    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        htag = self.get_setting(session, 'highlightTag', None)
        if htag is None:
            self.highlightTag = 'c3:highlight'
            self.attrs = {'xmlns:c3': self.HIGHLIGHT_NS}
        else:
            self.highlightTag = htag 
            self.attrs = {}
        
        tagAttrs = self.get_setting(session, 'tagAttrList', None)
        if tagAttrs is not None:
            for attr in tagAttrs.split(' '):
                bits = attr.split('=', 1)
                k = bits[0]
                v = bits[1][1:-1]    # strip off "s
                self.attrs[k] = v
                
        self.breakElements = self.get_setting(session,
                                              'breakElementsList',
                                              '').split(' ')
        
    def _insertHighlightElement(self, element, located, start, end):
        text = getattr(element, located)
        setattr(element, located, text[:start])
        hel = etree.Element(self.highlightTag)
        hel.attrib.update(self.attrs)
        hel.text = text[start:end]
        hel.tail = text[end:]
        return hel


LxmlHighlighTxr = LxmlQueryTermHighlightingTransformer


class LxmlPositionQueryTermHighlightingTransformer(LxmlHighlighTxr):
    """Return Document with search hits higlighted based on word position.
    
    Use word position from Record's resultSetItem's proximity information to
    highlight query term matches.
    
    Note Well: this can be unreliable when used in conjunction with stoplists.
    """

    def __init__(self, session, config, parent):
        raise NotImplementedError


class LxmlOffsetQueryTermHighlightingTransformer(LxmlHighlighTxr):
    """Return Document with search hits higlighted based on character offsets.

    Use character offsets from Record's resultSetItem's proximity information
    to highlight query term matches.
    """

    def __init__(self, session, config, parent):
        LxmlHighlighTxr.__init__(self, session, config, parent)
        try:
            # Try to get database's own version of RegexpFindOffsetTokenizer in
            # case config is non-default
            db = session.server.get_object(session, session.database)
        except:
            self.wordRe = re.compile(u"""
              (?xu)                                            #verbose, unicode
              (?:
                [a-zA-Z0-9!#$%*/?|^{}`~&'+-=_]+@[0-9a-zA-Z.-]+ #email
               |(?:[\w+-]+)?[+-]/[+-]                          #alleles
               |\w+(?:-\w+)+(?:'(?:t|ll've|ll|ve|s|d've|d|re))?  #hypenated word (maybe 'xx on the end)
               |[$\xa3\xa5\u20AC]?[0-9]+(?:[.,:-][0-9]+)+[%]?  #date/num/money/time
               |[$\xa3\xa5\u20AC][0-9]+                        #single money
               |[0-9]+(?=[a-zA-Z]+)                            #split: 8am 1Million
               |[0-9]+%                                        #single percentage 
               |(?:[A-Z]\.)+[A-Z\.]                            #acronym
               |[oOd]'[a-zA-Z]+                                #o'clock, O'brien, d'Artagnan   
               |[a-zA-Z]+://[^\s]+                             #URI
               |\w+'(?:d've|d|t|ll've|ll|ve|s|re)              #don't, we've
               |(?:[hH]allowe'en|[mM]a'am|[Ii]'m|[fF]o'c's'le|[eE]'en|[sS]'pose)
               |[\w+]+                                         #basic words, including +
              )""")
        else:
            self.wordRe = db.get_object(session,
                                        'RegexpFindOffsetTokenizer').regexp

    def process_record(self, session, rec):
        recDom = rec.get_dom(session)
        if (
            (rec.resultSetItem is not None) and
            (rec.resultSetItem.proxInfo is not None) and
            (len(rec.resultSetItem.proxInfo) > 0)
        ):
            # munge proxInfo into more useable form
            proxInfo = rec.resultSetItem.proxInfo
            proxInfo2 = set()
            # for each group of proxInfo (i.e. from each query clause)
            for pig in proxInfo:
                # for each item of proxInfo:
                # [nodeIdx, wordIdx, offset, termId(?)]
                for pi in pig:
                    # values must be strings for sets to work
                    proxInfo2.add('%d %d' % (pi[0], pi[2]))
            proxInfo = [map(int, pis.split(' ')) for pis in proxInfo2]
            nodeIdxs = []
            wordOffsets = []
            # sort proxInfo so that nodeIdxs are sorted descending (so that
            # offsets don't get upset when modifying text)
            for x in sorted(proxInfo, reverse=True):
                nodeIdxs.append(x[0])
                wordOffsets.append(x[1])

            xps = {}
            tree = recDom.getroottree()
            walker = recDom.getiterator()
            for x, n in enumerate(walker):
                if n.tag in self.breakElements:
                    break
                if x in nodeIdxs:
                    xps[x] = tree.getpath(n)
            xpathfn = recDom.xpath
            for ni, offset in zip(nodeIdxs, wordOffsets):
                try:
                    xp = xps[ni]
                except KeyError:
                    # No XPath
                    continue
                el = xpathfn(xp)[0]
                located = None
                for ci, c in enumerate(el.iter()):
                    # Ignore comments processing instructions etc.
                    if c.text:
                        text = c.text
                        if len(c.text) > offset:
                            start = offset
                            try:
                                end = self.wordRe.search(text, start).end()
                            except:
                                # Well I still...
                                # haven't found...
                                # what I'm looking for!
                                pass
                            else:
                                located = 'text'
                                if not (c.tag == self.highlightTag):
                                    hel = self._insertHighlightElement(c,
                                                                       located,
                                                                       start,
                                                                       end)
                                    try:
                                        c.insert(0, hel)
                                    except TypeError:
                                        # Immutable element (?)
                                        break
                                break
                        else:
                            # Adjust offset accordingly
                            offset -= len(text)
                    if c != el and c.tail and located is None:
                        text = c.tail
                        if len(c.tail) > offset:
                            start = offset
                            try:
                                end = self.wordRe.search(text, start).end()
                            except:
                                # Well I still...
                                # haven't found...
                                # what I'm looking for!
                                pass
                            else:
                                if end == -1:
                                    end = len(text)
                                located = 'tail'
                                if not (c.tag == self.highlightTag):
                                    hel = self._insertHighlightElement(c,
                                                                       located,
                                                                       start,
                                                                       end)
                                    p = c.getparent()
                                    try:
                                        p.insert(p.index(c) + 1, hel)
                                    except TypeError:
                                        # Immutable element (?)
                                        break
                                break
                        else:
                            # Adjust offset accordingly
                            offset -= len(text)
        return StringDocument(etree.tostring(recDom))


class TemplatedTransformer(Transformer):
    """Trasnform a Record using a Selector and a Python string.Template.
    
    Transformer to insert the output of a Selector into a template string
    containing place-holders.
    
    Template can be specified directly in the configuration using the 
    template setting (whitespace is respected), or in a file using the 
    templatePath path. If the template is specified in the configuration, 
    XML reserved characters (<, >, & etc.) must be escaped.
    
    This can be useful for Record types that are not easily transformed using
    more standard mechanism (e.g. XSLT), a prime example being GraphRecords
    
    Example
    
    config:
    
    <subConfig type="transformer" id="myTemplatedTransformer">
        <objectType>cheshire3.transformer.TemplatedTransformer</objectType>
        <paths>
            <object type="selector" ref="mySelector"/>
            <object type="extractor" ref="SimpleExtractor"/>
        </paths>
        <options>
            <setting type="template">
                This is my document. The title is {0}. The author is {1}
            </setting>
        </options>
    </subConfig>
    
    selector config:
    
    <subConfig type="selector" id="mySelector">
        <objectType>cheshire3.selector.XpathSelector</objectType>
        <source>
            <location type="xpath">//title</location>
            <location type="xpath">//author</location>
        </source>
    </subConfig>
    
    """
    
    _possiblePaths = {
        'selector': {
            'docs': "Selector to use to get data from the record."
        },
        'extractor': {
            'docs': ("An Extractor to use on each data item returned by the "
                     "Selector. The Extractor used must be able to handle the "
                     "output from the Selector (e.g. A SPARQL Selector would "
                     "require an RDF Extractor). Default is SimpleExtractor")
        },
        'templatePath': {
            'docs': ("Path to the file containing the template for the output "
                     "Document with place-holders for the selected data items."
                     )
        }
    }
    
    _possibleSettings = {
        'template': {
            'docs': ("A string representing the template for the output "
                     "Document with place-holders for selected data items.")
        }
    }
    
    def __init__(self, session, config, parent):
        Transformer.__init__(self, session, config, parent)
        self.selector = self.get_path(session, 'selector')
        self.extractor = self.get_path(session, 'extractor')
        tmplPath = self.get_path(session, "templatePath")
        if tmplPath is not None:
            dfp = self.get_path(session, "defaultPath")
            path = os.path.join(dfp, tmplPath)
            with open(path, 'r') as fh:
                self.template = unicode(fh.read()) 
        else:
            tmpl = self.get_setting(session, 'template', '')
            if not tmpl:
                raise ConfigFileException("{0} requires either a "
                                          "'templatePath' path or a "
                                          "'template' setting."
                                          "".format(self.id))
            self.template = unicode(tmpl)
            
    def process_record(self, session, rec):
        process_eventList = self.extractor.process_eventList
        process_string = self.extractor.process_string
        process_node = self.extractor.process_node
        data = self.selector.process_record(session, rec)
        vals = []
        for location in data:
            vals2 = []
            for match in location:
                if isinstance(match, types.ListType):
                    # SAX event
                    vals2.append(process_eventList(session, match).keys()[0])
                elif (
                    type(match) in types.StringTypes or
                    type(match) in [int, long, float, bool]
                ):
                    # Attribute content or function result (e.g. count())
                    vals2.append(process_string(session, match).keys()[0])
                elif isinstance(match, types.TupleType):
                    # RDF graph results (?)
                    vals3 = [] 
                    for item in match:
                        if item is not None:
                            vals3.append(process_node(session, item).keys()[0])
                        else:
                            vals3.append(None)
                    vals2.append(vals3)
                else:
                    # DOM nodes
                    vals2.append(process_node(session, match).keys()[0])
            vals.append(vals2)
        tmpl = self.template
        try:
            return StringDocument(tmpl.format(*vals))
        except IndexError as e:
            try:
                session.logger.log_error(session, repr(vals))
                session.logger.log_error(session, tmpl)
            except AttributeError:
                pass
            raise ConfigFileException('Template contained a place-holder for '
                                      'which data was not selected by the '
                                      'selector.')


class MarcTransformer(Transformer):
    """Transformer to converts records in marc21xml to marc records."""
    
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
        fields[0] = [''.join([l[5:10], l[17:20]])]
        marcObject = MARC()
        marcObject.fields = fields
        return StringDocument(marcObject.get_MARC())
