"""Cheshire3 Workflow Implementations."""

import sys
import traceback

from types import MethodType
from lxml import etree

from cheshire3.baseObjects import Workflow, Server
from cheshire3.configParser import C3Object
from cheshire3.utils import elementType, flattenTexts
from cheshire3.exceptions import C3Exception, ConfigFileException,\
                                 ObjectDoesNotExistException
from cheshire3.internal import CONFIG_NS


class WorkflowException(C3Exception):
    pass


class SimpleWorkflow(Workflow):
    """Default workflow implementation.

    Translates XML to python and compiles it on object instantiation.
    """

    code = None
    splitN = 0
    splitCode = {}

    def __init__(self, session, config, parent):
        self.splitN = 0
        self.splitCode = {}
        self.fnHash = {
            u'preParser': 'process_document',
            u'parser': 'process_document',
            u'transformer': 'process_record',
            u'extractor': 'process_xpathResult',
            u'normalizer': 'process_hash',
            u'xpathProcessor': 'process_record',
            u'selector': 'process_record',
            u'documentFactory': 'load',
            u'logger': 'log',
            u'documentStore': 'create_document',
            u'recordStore': 'create_record',
            u'authStore': 'create_record',
            u'configStore': 'create_record',
            u'queryStore': 'create_query',
            u'resultSetStore': 'create_resultSet',
            u'indexStore': 'store_terms',
            u'queryStore': 'create_query',
            u'workflow': 'process',
            u'index': 'store_terms',
            u'database': 'search',
            u'tokenMerger': 'process_hash',
            u'tokenizer': 'process_hash'
        }

        self.singleFunctions = [
            u'begin_indexing', u'commit_indexing',
            u'begin_storing', u'commit_storing',
            u'begin_logging', u'commit_logging',
            u'commit_metadata', u'shutdown'
        ]

        self.singleInputFunctions = [
            u'get_indexes',
            u'commit_parallelIndexing',
            u'get_idChunkGenerator',
            u'get_dom', u'get_sax', u'get_xml',  # Records
            u'get_raw'  # Documents
        ]

        Workflow.__init__(self, session, config, parent)
        # Somewhere at the top there must be a server
        self.server = parent

    def _handleLxmlConfigNode(self, session, node):
        if node.tag in ['workflow', '{%s}workflow' % CONFIG_NS]:
            code = ['def handler(self, session, input=None):']
            sub = self._handleLxmlGlobals(node)
            for s in sub:
                code.append("    " + s)
            sub = self._handleLxmlFlow(node)
            for s in sub:
                code.append("    " + s)
            code.append('    return input')
            self.code = "\n".join(code)
            filename = self.__class__.__name__ + ': ' + self.id
            compiled = compile(self.code, filename=filename, mode='exec')
            exec(compiled)
            setattr(self,
                    'process',
                    MethodType(locals()['handler'], self, self.__class__))

    def _handleConfigNode(self, session, node):
        # <workflow>
        if node.localName == "workflow":
            # Nummy.
            code = ['def handler(self, session, input=None):']
            sub = self._handleGlobals(node)
            for s in sub:
                code.append("    " + s)
            sub = self._handleFlow(node)
            for s in sub:
                code.append("    " + s)
            code.append('    return input')
            self.code = "\n".join(code)
            filename = self.__class__.__name__ + ': ' + self.id
            compiled = compile(self.code, filename=filename, mode='exec')
            exec(compiled)
            setattr(self,
                    'process',
                    MethodType(locals()['handler'], self, self.__class__))

    def _handleLxmlGlobals(self, node):
        return self._handleGlobals(node)

    def _handleGlobals(self, node):
        code = []
        code.append('if session.database:')
        code.append('    db = self.server.get_object(session, '
                    'session.database)')
        code.append('    self.database = db')
        code.append('else:')
        code.append('    raise WorkflowException("No database")')
        return code

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
                    type_ = node.getAttributeNS(None, 'type')
                    if type_:
                        code.append("except {0} as err:".format(type_))
                    else:
                        code.append("except Exception as err:")
                    sub = self._handleFlow(c)
                    if sub:
                        for s in sub:
                            code.append("    " + s)
                    else:
                        code.append("    pass")
                elif n == "else":
                    code.append("else:")
                    sub = self._handleFlow(c)
                    for s in sub:
                        code.append("    " + s)
                elif n == "break":
                    code.append("break")
                elif n == "continue":
                    code.append("continue")
                elif n == "return":
                    code.append("return input")
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
                        code.append("    pass")
                elif n == "object":
                    code.extend(self._handleObject(c))
                elif n == "log":
                    code.extend(self._handleLog(c))
                elif n == "fork":
                    code.extend(self._handleFork(c))
                else:
                    try:
                        name = n.title()
                        fn = getattr(self, "_handle%s" % name)
                        code.extend(fn(c))
                    except:
                        raise ConfigFileException("Unknown workflow element: "
                                                  "%s" % n)
        return code

    def _handleLxmlFlow(self, node):
        code = []
        for c in node.iterchildren(tag=etree.Element):
            n = c.tag[c.tag.find('}') + 1:]
            if n == "object":
                code.extend(self._handleLxmlObject(c))
            elif n == "assign":
                try:
                    fro = c.attrib['from']
                    to = c.attrib['to']
                except:
                    raise ConfigFileException("Workflow element assign "
                                              "requires 'to' and 'from' "
                                              "attributes in %s" % self.id)
                code.append("%s = %s" % (to, fro))
            elif n == "for-each":
                fcode = self._handleForEach(c)
                code.extend(fcode)
                sub = self._handleLxmlFlow(c)
                if sub:
                    for s in sub:
                        code.append("    " + s)
                else:
                    code.append("    pass")
            elif n == "log":
                code.extend(self._handleLxmlLog(c))
            elif n == "try":
                code.append("try:")
                sub = self._handleLxmlFlow(c)
                for s in sub:
                    code.append("    " + s)
            elif n == "except":
                type_ = node.attrib.get('type', '')
                if type_:
                    code.append("except {0} as err:".format(type_))
                else:
                    code.append("except Exception as err:")
                sub = self._handleLxmlFlow(c)
                if sub:
                    for s in sub:
                        code.append("    " + s)
                else:
                    code.append("    pass")
            elif n == "else":
                code.append("else:")
                sub = self._handleLxmlFlow(c)
                for s in sub:
                    code.append("    " + s)
            elif n == "break":
                code.append("break")
            elif n == "continue":
                code.append("continue")
            elif n == "return":
                code.append("return input")
            elif n == "raise":
                code.append("raise")
            elif n == "fork":
                code.extend(self._handleLxmlFork(c))
            else:
                try:
                    name = n.title()
                    fn = getattr(self, "_handleLxml%s" % name)
                    code.extend(fn(c))
                except:
                    raise ConfigFileException("Unknown workflow element: "
                                              "%s" % n)
        return code

    def _handleLog(self, node):
        code = []
        ref = node.getAttributeNS(None, 'ref')
        if (ref):
            code.append("object = db.get_object(session, '%s')" % ref)
        else:
            code.append("object = db.get_path(session, 'defaultLogger')")
        text = flattenTexts(node)
        if not text.startswith('"'):
            text = repr(text)

        lvl = node.getAttributeNS(None, 'level')
        if (lvl):
            if lvl.isdigit():
                code.append("object.log_lvl(session, %s, "
                            "str(%s).strip())" % (int(lvl), text))
            else:
                code.append("object.log_%s(session, "
                            "str(%s).strip())" % (lvl, text))
        else:
            code.append("object.log(session, str(%s).strip())" % text)
        return code

    def _handleLxmlLog(self, node):
        code = []
        ref = node.attrib.get('ref', '')
        if ref:
            code.append("object = db.get_object(session, '%s')" % ref)
        else:
            code.append("object = db.get_path(session, 'defaultLogger')")
        text = flattenTexts(node)
        if not text.startswith('"'):
            text = repr(text)
        lvl = node.attrib.get('level', '')
        if (lvl):
            if lvl.isdigit():
                code.append("object.log_lvl(session, %s, "
                            "str(%s).strip())" % (int(lvl), text))
            else:
                code.append("object.log_%s(session, "
                            "str(%s).strip())" % (lvl, text))
        else:
            code.append("object.log(session, str(%s).strip())" % text)
        return code

    def _handleForEach(self, node):
        return ['looped = input', 'for input in looped:']

    def _handleAnonObject(self, ref, typ, function):
        code = []
        if (ref):
            code.append("object = db.get_object(session, '%s')" % ref)
        elif typ == 'database':
            code.append("object = db")
        elif typ == 'input':
            code.append("object = input")
        elif typ:
            code.append("object = db.get_path(session, '%s')" % typ)
        else:
            raise ConfigFileException("Could not determine object")
        if not function:
            # Assume most common for object type
            function = self.fnHash[typ]

        if (function in self.singleFunctions):
            code.append('object.%s(session)' % function)
        elif function in self.singleInputFunctions:
            code.append('input = object.%s(session)' % function)
        elif (typ == 'index' and function == 'store_terms'):
            code.append('object.store_terms(session, input, inRecord)')
        elif typ == 'documentFactory' and function == 'load' and input is None:
            code.append('input = object.load(session)')
        elif typ == 'documentStore':
            # Check for normalizer output  (deprecated, use documentFactory)
            code.append('if type(input) == {}.__class__:')
            code.append('    for k in input.keys():')
            code.append('        object.%s(session, k)' % function)
            code.append('else:')
            code.append('    object.%s(session, input)' % function)
        elif typ == 'xpathProcessor':
            code.append('global inRecord')
            code.append('inRecord = input')
            code.append('input = object.process_record(session, input)')
        else:
            code.append('result = object.%s(session, input)' % function)
            code.append('if result is not None:')
            code.append('    input = result')
        #code.append('else:')
        #code.append('    raise WorkflowException("No function: "
        #"%s on %%s" %% object)' % function)
        return code

    def _handleLxmlObject(self, node):
        ref = node.attrib.get('ref', '')
        try:
            typ = node.attrib['type']
        except KeyError:
            raise ConfigFileException("Workflow element 'object' requires "
                                      "'type' attribute in %s" % self.id)
        function = node.attrib.get('function', '')
        return self._handleAnonObject(ref, typ, function)

    def _handleObject(self, node):
        ref = node.getAttributeNS(None, 'ref')
        typ = node.getAttributeNS(None, 'type')
        function = node.getAttributeNS(None, 'function')
        return self._handleAnonObject(ref, typ, function)

    def _handleLxmlSplit(self, node):
        fn = node.attrib.get('id', '')
        if fn:
            fname = "split_%s" % fn
        else:
            fname = "split%s" % self.splitN
            self.splitN += 1
        code = ['def %s(self, session, input):' % fname]
        sub = self._handleLxmlGlobals(node)
        for s in sub:
            code.append('    ' + s)

        sub = self._handleLxmlFlow(node)
        for s in sub:
            code.append("    " + s)
        code.append('    return input')
        codestr = "\n".join(code)
        self.splitCode[fname] = codestr
        exec(codestr)
        setattr(self, fname, MethodType(locals()[fname], self,
                                        self.__class__))
        return fname

    def _handleSplit(self, node):
        # <workflow>
        fn = node.getAttributeNS(None, 'id')
        if fn:
            fname = "split_%s" % fn
        else:
            fname = "split%s" % self.splitN
            self.splitN += 1
        code = ['def %s(self, session, input):' % fname]
        sub = self._handleGlobals(node)
        for s in sub:
            code.append('    ' + s)

        sub = self._handleFlow(node)
        for s in sub:
            code.append("    " + s)
        code.append('    return input')
        codestr = "\n".join(code)
        self.splitCode[fname] = codestr
        exec(codestr)
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

    def _handleLxmlFork(self, node):
        code = []
        for c in node.iterchildren(tag=etree.Element):
            if c.tag in ["split", '{%s}split' % CONFIG_NS]:
                fname = self._handleLxmlSplit(c)
                code.append("self.%s(session, input)" % fname)
        return code


class CachingWorkflow(SimpleWorkflow):
    """Slightly faster Workflow implementation that caches the objects.

    Object must not be used in one database and then another database without
    first calling workflow.load_cache(session, newDatabaseObject).
    """
    code = None
    splitN = 0
    splitCode = {}
    objcache = {}
    objrefs = None
    database = None
    defaultLogger = None

    def __init__(self, session, config, parent):
        self.objcache = {}
        self.objrefs = set()
        self.database = None
        self.defaultLogger = None
        SimpleWorkflow.__init__(self, session, config, parent)

    def load_cache(self, session, db):
        if not db:
            raise ValueError("ERROR: db parameter empty when loading cache "
                             "for workflow %s" % self.id)
        self.objcache = {}
        self.database = db
        self.defaultLogger = db.get_path(session, 'defaultLogger')
        for o in self.objrefs:
            obj = db.get_object(session, o)
            if not obj:
                raise ObjectDoesNotExistException(o)
            self.objcache[o] = obj

    def _handleGlobals(self, node):
        code = SimpleWorkflow._handleGlobals(self, node)
        code.extend(
                    ["if not self.objcache:",
                     "    self.load_cache(session, db)"])
        return code

    def _handleLog(self, node):
        text = flattenTexts(node)
        if not text.startswith('"'):
            text = repr(text)
        ref = node.getAttributeNS(None, 'ref')
        lvl = node.getAttributeNS(None, 'level')
        if (ref):
            self.objrefs.add(ref)
            obj = "self.objcache[%s]" % ref
        else:
            obj = "self.defaultLogger"
        if lvl:
            if lvl.isdigit():
                return ["%s.log_lvl(session, %s, "
                        "str(%s).strip())" % (obj, lvl, text)]
            else:
                return ["%s.log_%s(session, "
                        "str(%s).strip())" % (obj, lvl, text)]
        else:
            return ["%s.log(session, str(%s).strip())" % (obj, text)]

    def _handleLxmlLog(self, node):
        text = flattenTexts(node)
        if not text.startswith('"'):
            text = repr(text)
        ref = node.attrib.get('ref', '')
        lvl = node.attrib.get('level', '')
        if (ref):
            self.objrefs.add(ref)
            obj = "self.objcache[%s]" % ref
        else:
            obj = "self.defaultLogger"
        if lvl:
            if lvl.isdigit():
                return ["%s.log_lvl(session, %s, "
                        "str(%s).strip())" % (obj, lvl, text)]
            else:
                return ["%s.log_%s(session, "
                        "str(%s).strip())" % (obj, lvl, text)]
        else:
            return ["%s.log(session, str(%s).strip())" % (obj, text)]

    def _handleObject(self, node):
        ref = node.getAttributeNS(None, 'ref')
        typ = node.getAttributeNS(None, 'type')
        function = node.getAttributeNS(None, 'function')
        return self._handleAnonObject(ref, typ, function)

    def _handleLxmlObject(self, node):
        ref = node.attrib.get('ref', '')
        try:
            typ = node.attrib['type']
        except KeyError:
            raise ConfigFileException("Workflow element 'object' requires "
                                      "attribute 'type' in %s" % self.id)
        function = node.get('function', '')
        return self._handleAnonObject(ref, typ, function)

    def _handleAnonObject(self, ref, typ, function):
        code = []
        if (ref):
            self.objrefs.add(ref)
            o = "self.objcache['%s']" % ref
        elif typ == 'database':
            o = "self.database"
        elif typ == 'input':
            o = "input"
        elif typ:
            code.append("obj = self.database.get_path(session, '%s')" % typ)
            o = "obj"
        else:
            raise ConfigFileException("Could not determine object")
        if not function:
            # Assume most common for object type
            try:
                function = self.fnHash[typ]
            except KeyError:
                raise ConfigFileException("No default function for "
                                          "objectType: %s" % typ)
        if (function in self.singleFunctions):
            code.append('%s.%s(session)' % (o, function))
        elif (function in self.singleInputFunctions):
            code.append('input = %s.%s(session)' % (o, function))
        elif (typ == 'index' and function == 'store_terms'):
            code.append('%s.store_terms(session, input, inRecord)' % o)
        elif typ == 'documentFactory' and function == 'load' and input is None:
            code.append('input = %s.load(session)' % o)
        elif typ == 'documentStore':
            # Check for normalizer output
            code.append('if type(input) == {}.__class__:')
            code.append('    for k in input.keys():')
            code.append('        %s.%s(session, k)' % (o, function))
            code.append('else:')
            code.append('    %s.%s(session, input)' % (o, function))
        elif typ == 'xpathProcessor':
            code.append('global inRecord')
            code.append('inRecord = input')
            code.append('input = %s.process_record(session, input)' % o)
        else:
            code.append('result = %s.%s(session, input)' % (o, function))
            code.append('if result is not None:')
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
        exec(codestr)
        setattr(self, fname, MethodType(locals()[fname], self,
                                        self.__class__))
        return fname

    def _handleLxmlSplit(self, node):
        # <workflow>
        fn = node.attrib.get('id', '')
        if fn:
            fname = "split_%s" % fn
        else:
            fname = "split%s" % self.splitN
            self.splitN += 1
        code = ['def %s(self, session, input):' % fname]
        sub = self._handleLxmlFlow(node)
        for s in sub:
            code.append("    " + s)
        code.append('    return input')
        codestr = "\n".join(code)
        self.splitCode[fname] = codestr
        exec(codestr)
        setattr(self, fname, MethodType(locals()[fname], self,
                                        self.__class__))
        return fname
