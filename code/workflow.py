
from baseObjects import Workflow, Server
from configParser import C3Object
from utils import elementType, flattenTexts
from types import MethodType
import traceback, sys

from c3errors import C3Exception, ConfigFileException, ObjectDoesNotExistException

class WorkflowException(C3Exception):
    pass


class SimpleWorkflow(Workflow):
    """ Default workflow implementation. Translates XML to python and compiles it on object instantiation """

    code = None
    splitN = 0
    splitCode = {}

    def __init__(self, session, node, parent):
        self.splitN = 0
        self.splitCode = {}
        self.fnHash = {u'preParser' : 'process_document',
                       u'parser' : 'process_document',
                       u'transformer' : 'process_record',
                       u'extracter' : 'process_xpathResult',
                       u'normaliser' : 'process_hash',
                       u'xpathObject' : 'process_record',
                       u'documentFactory' : 'load',
                       u'logger' : 'log',
                       u'documentStore' : 'create_document',
                       u'recordStore' : 'create_record',
                       u'authStore' : 'create_record',
                       u'configStore' : 'create_record',
                       u'queryStore' : 'create_query',
                       u'resultSetStore' : 'create_resultSet',
                       u'indexStore' : 'store_terms',
                       u'queryStore' : 'create_query',                       
                       u'workflow' : 'process',
                       u'index' : 'store_terms',
                       u'database' : 'search'}
        self.singleFunctions = [u'begin_indexing', u'commit_indexing',
                                u'commit_metadata', u'begin_storing',
                                u'commit_storing']

        Workflow.__init__(self, session, node, parent)
        # Somewhere at the top there must be a server
        self.server = parent

    def _handleConfigNode(self, session, node):
        # <workflow>
        if node.localName == "workflow":
            # Nummy. 
            code = ['def handler(self, session, input=None):']
            code.append('    if session.database:')
            code.append('        db = self.server.get_object(session, session.database)')
            code.append('        self.database = db')
            code.append('    else:')
            code.append('        raise WorkflowException("No database")')
            sub = self._handleFlow(node)
            for s in sub:
                code.append("    " + s)
            code.append('    return input')
            self.code =  "\n".join(code)
            exec self.code
            setattr(self, 'process', MethodType(locals()['handler'], self,
                                              self.__class__))
            
    def _handleFlow(self, node):
        code = []
        for c in node.childNodes:
            if c.nodeType == elementType:
                n = c.localName
                if n == "try":
                    code.append("try:")
                    sub = self._handleFlow(c)
                    for s in sub:
                        code.append("    " + s)
                elif n == "except":
                    code.append("except Exception, err:")
                    sub = self._handleFlow(c)
                    for s in sub:
                        code.append("    " + s)
                elif n == "break":
                    code.append("break")
                elif n == "continue":
                    code.append("continue")
                elif n == "return":
                    code.append("return")
                elif n == "raise":
                    code.append("raise")
                elif n == "assign":
                    fro = c.getAttributeNS(None, 'from')
                    to = c.getAttributeNS(None, 'to')
                    code.append("%s = %s" % (to, fro))
                elif n == "for-each":
                    fcode = self._handleForEach(c)
                    code.extend(fcode)
                    sub = self._handleFlow(c)
                    if sub:
                        for s in sub:
                            code.append("    " + s)
                    else:
                        code.append("    pass");
                elif n == "object":                    
                    code.extend(self._handleObject(c))
                elif n == "log":
                    code.extend(self._handleLog(c))
                elif n == "fork":
                    code.extend(self._handleFork(c))
                else:
                    raise ConfigFileException("Unknown workflow element: %s" % n)
        return code
                               
    def _handleLog(self, node):
        code = []
        ref = node.getAttributeNS(None, 'ref')
        if (ref):
            code.append("object = db.get_object(session, '%s')" % ref)
        else:
            code.append("object = db.get_path(session, 'defaultLogger')")
        text = flattenTexts(node)
        if text[0] != '"':
            text = repr(text)
        code.append("object.log(session, str(%s))" % text)
        return code
            
    def _handleForEach(self, node):
        return ['looped = input', 'for input in looped:']

    def _handleObject(self, node):
        ref = node.getAttributeNS(None, 'ref')
        type = node.getAttributeNS(None, 'type')
        function = node.getAttributeNS(None, 'function')
        code = []
        if (ref):
            code.append("object = db.get_object(session, '%s')" % ref)
        elif type == 'database':
            code.append("object = db")
        elif type == 'input':
            code.append("object = input")
        elif type:
            code.append("object = db.get_path(session, '%s')" % type)
        else:
            raise ConfigFileException("Could not determine object")
        if not function:
            # Assume most common for object type
            function = self.fnHash[type]

        if (function in self.singleFunctions):
            code.append('object.%s(session)' % function)
        elif (type == 'index' and function == 'store_terms'):
            code.append('object.store_terms(session, input, inRecord)')
        elif type == 'documentFactory' and function == 'load' and input == None:
            code.append('input = object.load(session)')
        elif type == 'documentStore':
            # Check for normaliser output  (deprecated, use documentFactory)
            code.append('if type(input) == {}.__class__:')
            code.append('    for k in input.keys():')
            code.append('        object.%s(session, k)' % function)
            code.append('else:')
            code.append('    object.%s(session, input)' % function)
        elif type == 'xpathObject':
            code.append('global inRecord')
            code.append('inRecord = input')
            code.append('input = object.process_record(session, input)')
        else:
            code.append('result = object.%s(session, input)' % function)
            code.append('if result != None:')
            code.append('    input = result')           
        #code.append('else:')
        #code.append('    raise WorkflowException("No function: %s on %%s" %% object)' % function)
        return code


    def _handleSplit(self, node):
        # <workflow>
        fn = node.getAttributeNS(None, 'id')
        if fn:
            fname = "split_%s" % fn
        else:
            fname = "split%s" % self.splitN
            self.splitN += 1
        code = ['def %s(self, session, input):' % fname] 
        code.append('    db = self.database')

        sub = self._handleFlow(node)
        for s in sub:
            code.append("    " + s)
        code.append('    return input')
        codestr = "\n".join(code)
        self.splitCode[fname] = codestr
        exec codestr
        setattr(self, fname, MethodType(locals()[fname], self,
                                        self.__class__))
        return fname

    def _handleFork(self, node):
        code = []
        for c in node.childNodes:
            if c.nodeType == elementType:
                if c.localName == "split":
                    fname = self._handleSplit(c)
                    code.append("self.%s(session, input)" % fname)
        return code


class CachingWorkflow(SimpleWorkflow):
    """ Slightly faster workflow implementation that caches the objects.  Object not to be used in one database and then another database without first calling workflow.load_cache(session, newDatabaseObject) """
    code = None
    splitN = 0
    splitCode = {}
    objcache = {}
    objrefs = None
    database = None
    defaultLogger = None

    def __init__(self, session, node, parent):
        self.objcache = {}
        self.objrefs = set()
        self.database = None
        self.defaultLogger = None
        SimpleWorkflow.__init__(self, session, node, parent)


    def load_cache(self, session, db):
        self.objcache = {}
        self.database = db        
        self.defaultLogger = db.get_path(session, 'defaultLogger')
        for o in self.objrefs:
	    obj = db.get_object(session, o)
	    if not obj:
	        raise ObjectDoesNotExistException(o)
            self.objcache[o] = obj


    def _handleConfigNode(self, session, node):
        # <workflow>
        if node.localName == "workflow":
            # Nummy. 
            code = ['def handler(self, session, input=None):']
            code.extend(
["    if not self.objcache:",
 "        db = session.server.get_object(session, session.database)",
 "        self.load_cache(session, db)"])
            sub = self._handleFlow(node)
            for s in sub:
                code.append("    " + s)
            code.append('    return input')
            self.code =  "\n".join(code)
            exec self.code
            setattr(self, 'process', MethodType(locals()['handler'], self,
                                              self.__class__))
            
    def _handleLog(self, node):
        text = flattenTexts(node)
        if text[0] != '"':
            text = repr(text)
        ref = node.getAttributeNS(None, 'ref')
        if (ref):
            self.objrefs.add(ref)
            return ["self.objcache[%s].log(session, str(%s))" % (ref, text)]
        else:
            return ["self.defaultLogger.log(session, str(%s))" % (text)]

            
    def _handleObject(self, node):
        ref = node.getAttributeNS(None, 'ref')
        type = node.getAttributeNS(None, 'type')
        function = node.getAttributeNS(None, 'function')
        code = []
        if (ref):
            self.objrefs.add(ref)
            o = "self.objcache['%s']" % ref
        elif type == 'database':
            o = "self.database"
        elif type == 'input':
            o = "input"
        elif type:
            code.append("obj = self.database.get_path(session, '%s')" % type)
	    o = "obj"
        else:
            raise ConfigFileException("Could not determine object")
        if not function:
            # Assume most common for object type
            function = self.fnHash[type]

        if (function in self.singleFunctions):
            code.append('%s.%s(session)' % (o, function))
        elif (type == 'index' and function == 'store_terms'):
            code.append('%s.store_terms(session, input, inRecord)' % o)
        elif type == 'documentFactory' and function == 'load' and input == None:
            code.append('input = %s.load(session)' % o)
        elif type == 'documentStore':
            # Check for normaliser output
            code.append('if type(input) == {}.__class__:')
            code.append('    for k in input.keys():')
            code.append('        %s.%s(session, k)' % (o, function))
            code.append('else:')
            code.append('    %s.%s(session, input)' % (o, function))
        elif type == 'xpathObject':
            code.append('global inRecord')
            code.append('inRecord = input')
            code.append('input = %s.process_record(session, input)' % o)
        else:
            code.append('result = %s.%s(session, input)' % (o, function))
            code.append('if result != None:')
            code.append('    input = result')            
        return code


    def _handleSplit(self, node):
        # <workflow>
        fn = node.getAttributeNS(None, 'id')
        if fn:
            fname = "split_%s" % fn
        else:
            fname = "split%s" % self.splitN
            self.splitN += 1
        code = ['def %s(self, session, input):' % fname] 
        sub = self._handleFlow(node)
        for s in sub:
            code.append("    " + s)
        code.append('    return input')
        codestr = "\n".join(code)
        self.splitCode[fname] = codestr
        exec codestr
        setattr(self, fname, MethodType(locals()[fname], self,
                                        self.__class__))
        return fname

