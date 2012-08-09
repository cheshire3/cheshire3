
from mod_python import apache
from mod_python.util import FieldStorage
import sys, traceback, os, time
from Ft.Xml.Domlette import Print
from StringIO import StringIO

from cheshire3.server import SimpleServer
from cheshire3.baseObjects import Session
from cheshire3.document import StringDocument
from cheshire3.internal import storeTypes, collTypes, processTypes, Architecture, cheshire3Root

session = Session()
session.environment = "apache"
serv = SimpleServer(session, os.path.join(cheshire3Root , 'configs', 'serverConfig.xml'))

lastRefresh = time.time()
arch = Architecture()

class reqHandler:
    def send_xml(self, text, req, code=200):
        req.content_type = 'text/xml'
        req.content_length = len(text)
        req.send_http_header()
        req.write(text)


    def dispatch(self, req):
        # switch on path
        path = req.uri[1:]
        if (path[-1] == "/"):
            path = path[:-1]
        path = path[5:]

        if hasattr(self, "handle_%s" % path):
            fn = getattr(self, "handle_%s" % path)
            fn(req)
        else:
            self.send_xml("<fault>Unknown Request Type: %s</fault>" % path, req)


    def handle_create(self, req):
        # Create a new object  (workflow or otherwise)
        store = FieldStorage(req)
        try:
            objid = store['contextId']
            storeid = store['storeId']
            targetid = store['targetId']
            workflow = store['config']
            replace = int(store['replace'])
            context = serv.get_object(session, objid)
            confStore = context.get_object(session, storeid)
        except:
            context = None
            contStore = None
        if not context or not confStore:
            self.send_xml("<fault>Unknown object</fault>", req);
            return

        try:
            contStore.fetch_record(session, targetid)
            if not replace:
                self.send_xml("<fault>Object exists</fault>", req)
                return
        except:
            # does not exist
            pass

        try:
            p = context.get_object(session, 'SaxParser')
            d = StringDocument(workflow)
            rec = p.process_document(session, d)
            rec.id = targetid
            rec.recordStore = storeid
            confStore.begin_storing(session)
            confStore.store_record(session, rec)
            confStore.commit_storing(session)
        except Exception, e:
            self.send_xml("<fault>Storing failed %s</fault>" % e , req)
            return

        # Now destroy object and config from architecture
        try:
            del context.subConfigs[targetid]
            del context.objects[targetid]
        except KeyError, e:
            pass

        # now retrieve from confStore
        cfg = confStore.fetch_record(session, targetid)            
        dom = rec.get_dom(session)
        node = dom.childNodes[0]
        node.setAttributeNS(None, 'configStore', confStore.id)
        context.subConfigs[targetid] = node

        self.send_xml("<success/>", req)
        return
            

    def handle_docs(self, req):
        # retrieve documentation for object
        store = FieldStorage(req)
        try:
            objid = store['contextId']
            context = serv.get_object(session, objid)
            target = store['targetId']
            obj = context.get_object(session, target)
        except:
            obj = None
        if not obj:
            self.send_xml("<fault>Unknown object</fault>", req);
            return

        docs = []
        # look on object for manual docs
        if obj.docstring:
            docs.append('<doc from="%s">' % obj.id)
            docs.append(obj.docstring)
            docs.append("</doc>")
        classList = [obj.__class__]
        done = [];
        while classList:
            cl = classList.pop(0)
            if cl.__module__ != '__builtin__' and cl.__doc__ and not (cl in done):
                docs.append('<doc from="%s.%s">' % (cl.__module__, cl.__name__))
                docs.append(cl.__doc__)
                docs.append("</doc>")
                done.append(cl)
            classList.extend(list(cl.__bases__))
        
        self.send_xml("<docs>" + '\n'.join(docs) + "</docs>", req)

    def handle_listFunctions(self, req):
        # retrieve list of function on object

        store = FieldStorage(req)
        try:
            objid = store['contextId']
            context = serv.get_object(session, objid)
        except:
            self.send_xml("<fault>Unknown object: %s</fault>" % (objid), req);
            return
        try:
            target = store['targetId']
            if target[:8] == "default ":
                # use random object of this type?
                otype = target[8:]
                obj = context.get_path(session, otype)
            else:
                obj = context.get_object(session, target)
            select = store['select']            
        except:
            self.send_xml("<fault>Unknown object: %s</fault>" % (target), req);
            return

        properties = dir(obj)
        imt = type(self.handle_listObjects)
        funcs = []
        for p in properties:
            if p[0] != "_" and type(getattr(obj, p)) == imt:
                funcs.append(p)
        xml = ['<select xmlns="http://www.w3.org/1999/xhtml" id="functionNameSelect" onchange="set_function()">']
        xml.append('<option value="">(No Function)</option>');

        boringFns = ['add_logging', 'add_auth', 'get_setting', 'get_path', 'get_default', 'get_object', 'get_config', 'remove_logging', 'remove_auth']
        for f in funcs:
            if f in boringFns:
                # emphasize fns not everywhere
                name = '<span style="color:#888888;">%s</span>' % f
            else:
                name = f
            if f == select:
                xml.append('<option value="%s" selected="true">%s</option>' % (f, name));
            else:
                xml.append('<option value="%s">%s</option>' % (f, name));
        xml.append("</select>")
        self.send_xml(''.join(xml), req)


    def handle_getConfig(self, req):
        # fetch configuration (eg for editing existing workflow)

        store = FieldStorage(req)
        try:
            objid = store['contextId']
            context = serv.get_object(session, objid)
        except:
            self.send_xml("<fault>Unknown object: %s</fault>" % objid, req);
            return
        try:
            target = store['targetId']
            obj = context.get_object(session, target)
        except:
            raise
            self.send_xml("<fault>Unknown object: %s</fault>" % target, req);
            return

        config = obj.parent.get_config(session, target)
        cfgStr = config.getAttributeNS(None, 'configStore')
        if cfgStr:
            confStore = context.get_object(session, cfgStr)
            try:
                del context.subConfigs[target]
                del context.objects[target]
            except KeyError, e:
                pass

            # now re-retrieve from confStore
            rec = confStore.fetch_record(session, target)            
            dom = rec.get_dom(session)
            config = dom.childNodes[0]
            config.setAttributeNS(None, 'configStore', cfgStr)
            context.subConfigs[target] = config
            
        try:
            xml = config.toxml()
        except AttributeError, e:
            stream = StringIO()
            Print(config, stream)
            stream.seek(0)
            xml = stream.read()

        self.send_xml(xml, req)

    def handle_listObjects(self, req):
        # List existing objects in context

        storeHash = {}
        collHash = {}
        processHash = {}

        # get start obj from request
        store = FieldStorage(req)
        try:
            objid = store['contextId']
        except:
            self.send_xml("<fault>Missing contextId</fault>", req);
            return
        try:
            obj = serv.get_object(session, objid)
            origObj = obj
        except:
            raise
            self.send_xml("<fault>Unknown object: '%s'</fault>" % objid, req);
            return;

        while obj:
            # first, recheck any configStores
            for csid in obj._includeConfigStores:
                confStore = obj.get_object(session, csid)
                if confStore is not None:
                    for rec in confStore:
                        # do something with config
                        if (not (rec.id in obj.subConfigs.keys())):
                            node = rec.get_dom(session)
                            node= node.childNodes[0]
                            nid = node.getAttributeNS(None, 'id')
                            node.setAttributeNS(None, 'configStore', confStore.id)
                            obj.subConfigs[nid] = node
                            ntype = node.getAttributeNS(None, 'type')
                            if ntype == 'index':
                                obj.indexConfigs[nid] = node
                            elif ntype == 'protocolMap':
                                obj.protocolMapConfigs[nid] = node
                            elif ntype == 'database':
                                obj.databaseConfigs[nid] = node
                            elif ntype == '':
                                raise ConfigFileException("Object must have a type attribute: %s  -- in configStore %s" % (nid, csid))
            sys.stderr.flush()
            for oid in obj.subConfigs.keys():
                dom = obj.subConfigs[oid]
                t = dom.getAttributeNS(None, 'type')
                if t in storeTypes:
                    try:
                        storeHash[t].append(oid)
                    except:
                        storeHash[t] = [oid]
                elif t in collTypes:
                    try:
                        collHash[t].append(oid)
                    except:
                        collHash[t] = [oid]
                elif t in processTypes:
                    try:
                        processHash[t].append(oid)
                    except:
                        processHash[t] = [oid]
            obj = obj.parent

        html = ["""<div xmlns="http://www.w3.org/1999/xhtml"><ul id="ObjectList" style="padding-left: 5px; border-left: none;">"""]

        html.append("<li>Process Objects")
        html.append("<ul>")
        keys = processHash.keys()
        keys.sort()
        for ot in keys:
            html.append("<li>" + ot + "<ul>")
            oids = processHash[ot]
            oids.sort()
            if (origObj.get_path(session, ot)):
                html.append('<li> <a class="item" href="javascript:none()" onclick="create_ellipse(\'default %s\', \'%s\')"><i>default %s</i></a></li>' % (ot, ot, ot))
            for oid in oids:
                html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_ellipse('%s', '%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="help(event, '%s')" onmouseout="unhelp()">?</a>
</li>""" % (oid, ot, oid, oid))
            html.append("</ul></li>")
        html.append("</ul></li>")


        html.append("<li>Store Objects")
        html.append("<ul>")
        keys = storeHash.keys()
        keys.sort()
        for ot in keys:
            html.append("<li>" + ot + "<ul>")
            oids = storeHash[ot]
            oids.sort()
            if (origObj.get_path(session, ot)):
                html.append('<li> <a class="item" href="javascript:none()" onclick="create_store(\'default %s\', \'%s\')"><i>default %s</i></a></li>' % (ot, ot, ot))
            if ot == 'configStore':
                for oid in oids:
                    html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_store('%s', '%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="help(event, '%s')" onmouseout="unhelp()">?</a>
<a class="item" href="javascript:none()" onclick="setConfigStore('%s')">(set)</a>
</li>""" % (oid, ot, oid, oid, oid))
            else:
                for oid in oids:
                    html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_store('%s', '%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="help(event, '%s')" onmouseout="unhelp()">?</a>
</li>""" % (oid, ot, oid, oid))
            html.append("</ul></li>")
        html.append("</ul></li>")

        html.append("<li>Collection Objects")
        html.append("<ul>")
        keys = collHash.keys()
        keys.sort()
        for ot in keys:
            html.append("<li>" + ot + "<ul>")
            oids  = collHash[ot]
            oids.sort()
            if (origObj.get_path(session, ot)):
                html.append('<li> <a class="item" href="javascript:none()" onclick="create_rect(\'default %s\', \'%s\')"><i>default %s</i></a></li>' % (ot, ot, ot))
            if ot == 'database':
                for oid in oids:
                    html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_rect('%s', '%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="help(event, '%s')" onmouseout="unhelp()">?</a>
<a class="item" href="javascript:none()" onclick="setContext('%s')">(set)</a>
</li>""" % (oid, ot, oid, oid, oid))
            elif ot == 'workflow':
                for oid in oids:
                    html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_rect('%s', '%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="help(event, '%s')" onmouseout="unhelp()">?</a>
<a class="item" href="javascript:none()" onclick="loadWorkflow('%s')">(edit)</a>
</li>""" % (oid, ot, oid, oid, oid))

            else:
                for oid in oids:
                    html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_rect('%s', '%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="help(event, '%s')" onmouseout="unhelp()">?</a>
</li>""" % (oid, ot, oid, oid))

            html.append("</ul></li>")

        html.append("</ul></li>")
        html.append('<li><a class="item" href="javascript:none()" onclick="create_line();">Create Line</a></li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="create_log();">Create Log Entry</a></li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="create_assign();">Create Assignment</a></li>')

        html.append('<li>Create: <a class="item" href="javascript:none()" onclick="create_fork();">Fork</a>, ')
        html.append('<a class="item" href="javascript:none()" onclick="create_foreach();">ForEach</a>, ')
        html.append('<a class="item" href="javascript:none()" onclick="create_try();">TryExcept</a></li>')

        html.append('<li>Create: <a class="item" href="javascript:none()" onclick="create_return();">Return</a>, ')
        html.append('<a class="item" href="javascript:none()" onclick="create_raise();">Raise</a>, ')
        html.append('<a class="item" href="javascript:none()" onclick="create_continue();">Continue</a>, ')
        html.append('<a class="item" href="javascript:none()" onclick="create_break();">Break</a></li>')

        html.append("</ul>")

        html.append('<ul style="padding-left: 5px; border-left: none;">')

        html.append('<li><a class="item" href="javascript:none()" onclick="zoom(1);">Zoom Out</a>  (Current: <span id="zoomLevel">1</span>:1)</li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="zoom(-1);">Zoom In</a></li>')

        html.append('<li><a class="item" href="javascript:none()" onclick="panX(1);">Move Left</a> (Current: <span id="panLevel">0 0</span>)</li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="panX(-1);">Move Right</a></li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="panY(1);">Move Up</a></li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="panY(-1);">Move Down</a></li>')


        html.append('<li><br/><a class="item" href="index2.xml">Create New Object</a></li>')


        html.append('<li><br/><a class="item" href="javascript:none()" onclick="clear_flow();">Clear Workflow</a></li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="show_flow();">Preview Workflow</a></li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="send_flow();">Save Workflow</a></li>')

        html.append('<li><br/><table cellpadding="0" cellspacing="0" border="0"><tr><td>Context:</td><td><span id="contextId">%s</span></td></tr><tr><td>Workflow:</td><td><input type="text" value="test-flow" id="workflowId"/></td></tr><tr><td>ConfigStore:</td><td><input type="text" value="defaultConfigStore" id="configStoreId"/></td></tr><tr><td>Replace:</td><td><select id="replace"><option value="0">No</option><option value="1">Yes</option></select></td></tr></table></li>' % objid);

        html.append("</ul></div>")

        xml = '\n'.join(html)
        self.send_xml(xml, req)


    def handle_listTypedObjects(self, req):
        # get list of typed objects, eg loggers

        storeHash = {}
        collHash = {}
        processHash = {}

        # get start obj from request
        store = FieldStorage(req)
        try:
            objid = store['contextId']
        except:
            self.send_xml("<fault>Missing contextId</fault>", req);
            return
        try:
            obj = serv.get_object(session, objid)
        except:
            self.send_xml("<fault>Unknown object: '%s'</fault>" % objid, req);
            return;
        try:
            objType = store['objectType']
        except:
            self.send_xml("<fault>Missing parameter: objectType</fault>")
            return
        try:
            dflt = store['default']
        except:
            dflt = None
        
        oids = []
        while obj:
            for oid in obj.subConfigs.keys():
                dom = obj.subConfigs[oid]
                t = dom.getAttributeNS(None, 'type')
                if t == objType and oid != dflt:
                    oids.append(oid)
            obj = obj.parent

        oids.sort()
        html = ['<select id="loggerObjectSelect" xmlns="http://www.w3.org/1999/xhtml">']
        if dflt:
            html.append('<option value="%s">%s</option>' % (dflt, dflt))
        html.append('<option value="">Default Logger</option>')
            
        for o in oids:
            html.append('<option value="%s">%s</option>' % (o, o))
        html.append('</select>')

        xml = '\n'.join(html)
        self.send_xml(xml, req)

    def handle_listClasses(self, req):
        # List classes to pick one to create new object

        # [(type, classObj),...]  sorted by type
        classList = arch.discover_classes()

        storeHash = {}
        collHash = {}
        processHash = {}
        others = []

        for (t, cls) in classList:
            clsName = "%s.%s" % (cls.__module__, cls.__name__)
            # lowercase first two characters
            t = "%s%s" % (t[:2].lower(), t[2:])

            
            if t in storeTypes:
                try:
                    storeHash[t].append(clsName)
                except:
                    storeHash[t] = [clsName]
            elif t in collTypes:
                try:
                    collHash[t].append(clsName)
                except:
                    collHash[t] = [clsName]
            elif t in processTypes:
                try:
                    processHash[t].append(clsName)
                except:
                    processHash[t] = [clsName]
            else:
                others.append(clsName)


        html = ["""<div xmlns="http://www.w3.org/1999/xhtml"><ul id="ObjectList" style="padding-left: 5px; border-left: none;">"""]

        html.append("<li>Process Objects")
        html.append("<ul>")
        keys = processHash.keys()
        keys.sort()
        for ot in keys:
            html.append("<li>" + ot + "<ul>")
            oids = processHash[ot]
            oids.sort()
            for oid in oids:
                if oid.count('.') > 1:
                    name = oid[oid.index('.')+1:]
                else:
                    name = oid
                html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_config('%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="class_help(event, '%s')" onmouseout="unhelp()">?</a>
</li>""" % (oid, name, oid))
            html.append("</ul></li>")
        html.append("</ul></li>")


        html.append("<li>Store Objects")
        html.append("<ul>")
        keys = storeHash.keys()
        keys.sort()
        for ot in keys:
            html.append("<li>" + ot + "<ul>")
            oids = storeHash[ot]
            oids.sort()
            for oid in oids:
                if oid.count('.') > 1:
                    name = oid[oid.index('.')+1:]
                else:
                    name = oid

                html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_config('%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="class_help(event, '%s')" onmouseout="unhelp()">?</a>
</li>""" % (oid, name, oid))
            html.append("</ul></li>")
        html.append("</ul></li>")

        html.append("<li>Collection Objects")
        html.append("<ul>")
        keys = collHash.keys()
        keys.sort()
        for ot in keys:
            html.append("<li>" + ot + "<ul>")
            oids  = collHash[ot]
            oids.sort()
            for oid in oids:
                if oid.count('.') > 1:
                    name = oid[oid.index('.')+1:]
                else:
                    name = oid
                html.append("""
<li>
<a class="item" href="javascript:none()" onclick="create_config('%s')">%s</a> 
<a class="item" href="javascript:none()" onclick="class_help(event, '%s')" onmouseout="unhelp()">?</a>
</li>""" % (oid, name, oid))

            html.append("</ul></li>")

        html.append('</ul></li>')

        html.append('<li><a class="item" href="javascript:none()" onclick="show_config()">Preview Configuration</a></li>')
        html.append('<li><a class="item" href="javascript:none()" onclick="save_config()">Save Configuration</a></li>')

        html.append('</ul></div>')

        xml = '\n'.join(html)
        self.send_xml(xml, req)
        
    def handle_getConfigParams(self, req):
        store = FieldStorage(req)
        try:
            cls = store['className']
        except:
            self.send_xml("<fault>Missing className</fault>", req);
            return
        try:
            classObj = arch.find_class(cls)
        except:
            self.send_xml("<fault>No such class: %s</fault>" % cls, req)

        try:
            (paths, setts, defs) = arch.find_params(classObj)
        except:
            self.send_xml("<fault>Not a configurable object?</fault>", req)


        # This is stupid...
        classes = arch.discover_classes()
        otype = "unknown"
        for c in classes:
            if c[1] == classObj:
                otype = c[0]
                otype = otype[:2].lower() + otype[2:]
        

        html = ["""<div xmlns="http://www.w3.org/1999/xhtml">""",
                """<center><i>Basic Information</i></center>""",
                """<table width="100%%">
                <tr><td width="20%%"><b>Identifier</b></td><td><input id="identifierInput" type="text" name="identifier" size="30"/></td><td width="5%%"></td></tr>
                <tr><td><b>Class</b></td><td>%s</td><td></td></tr>
                <tr><td><b>Object Type</b></td><td>%s</td><td></td></tr>
                </table>
                <input type="hidden" name="className" id="classNameInput" value="%s"/>
                <input type="hidden" name="objectType" id="objectTypeInput" value="%s"/>
                <br/>
                <center><i>Paths</i></center>""" % (cls, otype, cls, otype)]

        html.append('<table width="100%">')
        items = paths.items()
        items.sort()
        for (p, info) in items:
            html.append("<tr><td width=\"20%%\"><b>%s</b></td><td>" % p)
            if info.has_key('options'):
                opts = info['options'].split('|')
                html.append("""<select name="path_%s">""" % p)
                html.append("""<option value="">(default)</option>""")
                for o in opts:
                    html.append("""<option value="%s">%s</option>""" % (o,o))
                html.append("""</select>""")
            else:
                html.append("""<input type="text" name="path_%s" size="30"/>""" % (p))
            html.append("""</td><td width=\"5%%\"><a href="javascript:none()" onclick="config_help('%s')"><img src="http://sca.lib.liv.ac.uk/images/whatisthis.gif"/></a></td></tr>""" % info['docs'].replace("'", "\\'"))
        html.append('</table>')

        if setts:
            html.append("<br/><center><i>Settings</i></center>")
            html.append('<table width="100%">')
            items = setts.items()
            items.sort()
            for (p, info) in items:
                html.append("<tr><td width=\"20%%\"><b>%s</b></td><td>" % p)
                if info.has_key('options'):
                    opts = info['options'].split('|')
                    html.append("""<select name="setting_%s">""" % p)
                    html.append("""<option value="">(default)</option>""")
                    for o in opts:
                        html.append("""<option value="%s">%s</option>""" % (o,o))
                    html.append("""</select>""")
                else:
                    html.append("""<input type="text" name="setting_%s" size="30"/>""" % (p))
                html.append("""</td><td width=\"5%%\"><a href="javascript:none()" onclick="config_help('%s')"><img src="http://sca.lib.liv.ac.uk/images/whatisthis.gif"/></a></td></tr>""" % info['docs'].replace("'", "\\'"))
            html.append('</table>')


        if defs:
            html.append("<br/><center><i>Defaults</i></center>")
            html.append('<table width="100%">')
            items = defs.items()
            items.sort()
            for (p, info) in items:
                html.append("<tr><td width=\"20%%\"><b>%s</b></td><td>" % p)
                if info.has_key('options'):
                    opts = info['options'].split('|')
                    html.append("""<select name="default_%s">""" % p)
                    html.append("""<option value="">(default)</option>""")
                    for o in opts:
                        html.append("""<option value="%s">%s</option>""" % (o,o))
                    html.append("""</select>""")
                else:
                    html.append("""<input type="text" name="default_%s" size="30"/>""" % (p))
                html.append("""</td><td width=\"5%%\"><a href="javascript:none()" onclick="config_help('%s')"><img src="http://sca.lib.liv.ac.uk/images/whatisthis.gif"/></a></td></tr>""" % info['docs'].replace("'", "\\'"))
            html.append('</table>')

        html.append("</div>")

        xml = "\n".join(html)
        self.send_xml(xml, req)

    def handle_classDocs(self, req):
        # retrieve documentation for object
        store = FieldStorage(req)
        try:
            cls = store['className']
        except:
            self.send_xml("<fault>Missing className</fault>", req);
            return
        try:
            obj = arch.find_class(cls)
        except:
            self.send_xml("<fault>No such class: %s</fault>" % cls, req)

        docs = []
        classList = [obj]
        done = [];
        while classList:
            cl = classList.pop(0)
            if cl.__module__ != '__builtin__' and cl.__doc__ and not (cl in done):
                docs.append('<doc from="%s.%s">' % (cl.__module__, cl.__name__))
                docs.append(cl.__doc__)
                docs.append("</doc>")
                done.append(cl)
            classList.extend(list(cl.__bases__))
        
        self.send_xml("<docs>" + '\n'.join(docs) + "</docs>", req)


srwh = reqHandler()        


def handler(req):
    # do stuff
    srwh.dispatch(req)
    return apache.OK
