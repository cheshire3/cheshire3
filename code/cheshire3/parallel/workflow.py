
from cheshire3.workflow import CachingWorkflow
from cheshire3.exceptions import ConfigFileException

class ParallelWorkflow(CachingWorkflow):
    """ Parallel workflow that uses a TaskManager to distribute processing """

    _possiblePaths = {'taskManager' : {'docs': "TaskManager to use to distribute processing"}}

    def __init__(self, session, config, parent):
        CachingWorkflow.__init__(self, session, config, parent)
        # Now get taskManager
        self.taskManager = self.get_path(session, 'taskManager')
        if not self.taskManager:
            raise ConfigFileException("Parallel Workflow needs a taskManager")

    def _handleGlobals(self, node):
        code = CachingWorkflow._handleGlobals(self, node)
        code.append('tm = self.taskManager')
        return code

    def _handleLxmlObject(self, node):
        ref = node.attrib.get('ref', '')
        try:
            typ = node.attrib['type']
        except KeyError:
            raise ConfigFileException("Workflow element 'object' requires 'type' attribute in %s" % self.id)
        function = node.attrib.get('function', '')
        proc = node.attrib.get('process', '')
        return self._handleAnonObject(ref, typ, function, proc)

    def _handleObject(self, node):
        ref = node.getAttributeNS(None, 'ref')
        typ = node.getAttributeNS(None, 'type')
        function = node.getAttributeNS(None, 'function')
        proc = node.getAttributeNS(None, 'process')
        return self._handleAnonObject(ref, typ, function, proc)
    
    def _handleAnonObject(self, ref, typ, function, proc):
        code = []
        if (ref):
            self.objrefs.add(ref)
            o = "self.objcache['%s']" % ref
        elif typ == 'database':
            o = "self.database"
        elif typ == 'input':
            o = "input"
        elif typ == "taskManager":
            o = "tm"
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
                raise ConfigFileException("No default function for objectType: %s" % typ)

        if not proc or proc == 'local':
            # Do the call locally
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
        else:
            if proc == 'all':
                # Broadcast to all processes
                if function in self.singleFunctions or function in self.singleInputFunctions:
                    code.append("result = tm.call_all(session, %s, '%s')" % (o, function))
                else:
                    code.append('result = tm.call_all(session, %s, "%s", input)' % (o, function))                         
            elif proc == 'any':
                # Send the call to any available process
                if function in self.singleFunctions or function in self.singleInputFunctions:
                    code.append('result = tm.call(session, %s, "%s")' % (o, function))
                else:
                    code.append('result = tm.call(session, %s, "%s", input)' % (o, function))
            else:
                raise ConfigFileException("Unknown process type on workflow: %s" % proc)
            code.append('if result is not None:')
            code.append('    input = result')
                          
        return code

    def _handleWait(self, node):
        return ['tm.recv_all()']

    def _handleLxmlWait(self, node):
        return ['tm.recv_all()']    
    
    
    
