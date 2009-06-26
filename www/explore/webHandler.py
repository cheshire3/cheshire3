# import mod_python stuffs
from mod_python import apache, Cookie
from mod_python.util import FieldStorage

import sys
import os
import cgitb
import libxml2

cheshirePath = "/Users/cheshire3"

# set sys paths 
sys.path.insert(1, os.path.join(cheshirePath, 'cheshire3', 'code'))

# import Cheshire3 stuff
from cheshire3.baseObjects import Session
from cheshire3.server import SimpleServer
from cheshire3.utils import flattenTexts
import cheshire3.cqlParser as cql
import cheshire3.exceptions as c3errors
# C3 web search utils
from cheshire3.web.www_utils import *
from types import *

from lxml import etree


def xml_encode(text):
    return re.sub("'", '&apos;',
           re.sub('"', '&quot;',
           re.sub('>', '&gt;',
           re.sub('<', '&lt;',
           re.sub('&', '&amp;', text)))))

class SearchHandler:
    
    baseUrl = '';
    varTypes = [NoneType, TypeType, BooleanType, IntType, LongType, FloatType, ComplexType, StringType, UnicodeType]

    def log(self, msg):
        self.logMessages.append(msg);

    def __init__(self, lgr=None):
        global db
        self.logMessages = []
        self.logger = lgr
        self.globalReplacements = {'SCRIPT': script
                                  }
        self.redirected = False
        self.opStartTime = None
        #- end __init__() -----------------------------------------------------

    def _logVars(self, obj):
        vars = str(obj) + ': ' + str(type(obj)) + '\n'
        for field in dir(obj):
            if not field.startswith('_'):
                val = getattr(obj, field)
                t = type(val)
                if (t in self.varTypes):
                    vars += '  ' + field + ': ' + str(val) + '\n'
                else:
                    vars += '  ' + field + ': ' + str(t) + '\n'
        self.log(vars)
            
    def _send_html(self, data, req, code=200):
        req.content_type = 'text/html'
        req.content_length = len(data)
        req.send_http_header()
        if (type(data) == unicode):
            data = data.encode('utf-8')
        req.write(data)
        req.flush()
        #- end _send_html() ----------------------------------------------------
        
    def _send_xml(self, data, req, code=200):
        req.content_type = 'text/xml'
        req.content_length = len(data)
        req.send_http_header()
        if (type(data) == unicode):
            data = data.encode('utf-8')
        req.write(data)
        req.flush()
        #- end _send_xml() -----------------------------------------------------
        
    def browse(self, req, form):
        u"""Scan through the requested index to the requested point, return HTML representing a list of links to search for each index term."""
        global queryFactory
        idx = form.get('fieldidx1', 'cql.anywhere')
        rel = form.get('fieldrel1', '=')
        scanTerm = form.get('fieldcont1', '*')
        nTerms = int(form.get('maximumTerms', 25))
        rp = int(form.get('responsePosition', nTerms/2))
        qString = '%s %s %s' % (idx, rel, scanTerm)
        if form.has_key('ajax'):
            linkClass = 'ajax'
        else:
            linkClass = 'simple'
        try:
            scanClause = queryFactory.get_query(session, qString)
        except:
            try:
                scanClause = queryFactory.get_query(session, form, format='www')
            except:
                self.log('Unparsable query: %s' % qString)
                self.htmlTitle.append('Error')
                return '<p class="error">An invalid query was submitted.</p>'
            else:
                qString = scanClause.toCQL()
            
        self.htmlTitle.append('browse')
        self.log('Browsing for "%s"' % (qString))
        hitstart = False
        hitend = False
        if (scanTerm == ''):
            hitstart = True
            rp = 0
            
        scanTermNorm = scanTerm
        if (rp == 0):
            scanData = db.scan(session, scanClause, nTerms, direction=">")
            if (len(scanData) < nTerms): hitend = True
        elif (rp == 1):
            scanData = db.scan(session, scanClause, nTerms, direction=">=")
            if (len(scanData) < nTerms): hitend = True
        elif (rp == nTerms):
            scanData = db.scan(session, scanClause, nTerms, direction="<=")
            scanData.reverse()
            if (len(scanData) < nTerms): hitstart = True
        elif (rp == nTerms+1):
            scanData = db.scan(session, scanClause, nTerms, direction="<")
            scanData.reverse()
            if (len(scanData) < nTerms): hitstart = True
        else:
            # Need to go down...
            try:
                scanData = db.scan(session, scanClause, rp, direction="<=")
            except:
                scanData = []
            # ... then up
            try:
                scanData1 = db.scan(session, scanClause, nTerms-rp+1, direction=">=")
            except:
                scanData1 = []
            
            if (len(scanData1) < nTerms-rp+1):
                hitend = True
            if (len(scanData) < rp):
                hitstart = True
            # try to stick them together
            try:
                if scanData1[0][0] == scanData[0][0]:
                    scanTermNorm = scanData.pop(0)[0]
                else:
                    scanTermNorm = scanTerm
                    scanData.insert(0, None)
                    scanData1[:-1]
            except:
                scanTermNorm = scanTerm

            scanData.reverse()
            scanData.extend(scanData1)
            del scanData1
            
        totalTerms = len(scanData)
        if (totalTerms > 0):
            self.htmlTitle.append('Results')
            rows = ['<div id="browseresults">']

            if (hitstart):
                #rows.append('<tr class="odd"><td colspan="3">-- start of index --</td></tr>')
                prevlink = ''
            else:
                rows.append('''<a href="%s/browse.html?fieldidx1=%s&amp;fieldrel1=%s&amp;fieldcont1=%s&amp;responsePosition=%d&amp;maximumTerms=%d" title="view previous %d terms" class="%s">%s&#160;PREVIOUS</a>''' % (script, idx, rel, cgi_encode(scanData[0][0]), nTerms+1, nTerms, nTerms, linkClass, prev_page_tag))

            rows.append('<table class="browseresults" summary="list of terms in this index"><tbody>')
            rows.append('<tr><td>Term</td><td>No. of records</td></tr>')
            dodgyTerms = []
            for i, item in enumerate(scanData):
                if not item:
                    rows.append('<tr class="notfound"><td colspan="3">Your term would have been here</td></tr>')
                    continue
                term = item[0]
                if not term:
                    continue

                # TODO: ideally get original, un-normalised version from index
                # until then do a clever version of term.title()
                if (idx not in ['dc.identifier']):
                    displayTerm = self._cleverTitleCase(term)
                else:
                    displayTerm = term
              
                if (term.lower() == scanTermNorm.lower()):
                    displayTerm = '<b>%s</b>' % displayTerm
                    
                rows.extend(['<tr class="%s">' % (['odd','even'][i % 2])
                            ,'<td class="term"><a href="%s/search.html?fieldidx1=%s&amp;fieldrel1=%s&amp;fieldcont1=%s" title="Find matching records">%s</a></td>' % (script, cgi_encode(idx), cgi_encode(rel), cgi_encode(term), displayTerm)
                            ,'<td class="count" title="Number of records containing this term">%d</td>' % (item[1][1])
                            ,'</tr>'])

            #- end for each item in scanData
            if (hitend):
                rowclass = ['odd','even'][(i+1) % 2]
                rows.append('<tr class="%s"><td colspan="3">-- end of index --</td></tr>' % (rowclass))
                nextlink = ''
            else:
                nextlink = '''<a href="%s/browse.html?fieldidx1=%s&amp;fieldrel1=%s&amp;fieldcont1=%s&amp;responsePosition=%d&amp;maximumTerms=%d" title="view next %d terms" class="%s">NEXT&#160;%s</a>''' % (script, idx, rel, cgi_encode(scanData[-1][0]), 0, nTerms, nTerms, linkClass, next_page_tag)

            del scanData
            rows.append('</tbody></table>')
            rows.append(nextlink)           
            rows.extend('</div>')
            #- end hit navigation
            return '\n'.join(rows)

        else:
            self.htmlTitle.append('Error')
            return '<p class="error">No terms retrieved from index. You may be browsing outside the range of terms within the index.</p>'
        #- end browse() -------------------------------------------------------
        
    def _searchReplace(self, html, subst = {}):

        collections = ['<option value="cql.anywhere" selected="selected">All Collections</option>']
        for d in serv.databaseConfigs.items():
            mydb = serv.get_object(session, d[0])
            collections.append('<option value="%s">%s (%s)</option>' % (mydb.id, d[1].get('name'), mydb.id))

        known = {};
        indexMenu = ['<option value="cql.anywhere||dc.description||dc.title" selected="selected">Keywords</option>']
        indexArray = ['new Array("cql.anywhere||dc.description||dc.title|||Keywords"']
        for d in serv.databaseConfigs.items():
            mydb = serv.get_object(session, d[0])
            for i in mydb.indexConfigs:
                idx = db.get_object(session, i)
                idxName = db.get_config(session, i).get('name')
                fullID = 'c3' + '.' + idx.id;
                if (idxName not in known):
                    known[idxName] = len(indexMenu)
                    indexMenu.append('<option value="%s">%s %s (%s)</option>' % (fullID, mydb.name, idxName, fullID))
                    indexArray.append('"%s|||%s"' % (fullID,  idxName))
                else:
                    pos = known[idxName];
                    if (indexMenu[pos].find(idxName) < 0):
                        indexMenu[pos] = re.sub('">', ',%s">'  % (fullID), indexMenu[pos]);
                        indexMenu[pos] = re.sub('\\)',  ', %s)' % (fullID), indexMenu[pos]);
                        indexArray[pos] = re.sub('\\|\\|\\|', '||%s|||' % (fullID), indexArray[pos]);

        replHash = self.globalReplacements.copy()
        self.log('subst = ' + str(subst))
        replHash.update(subst)
        self.log('replHash = ' + str(replHash))
        replHash.update({'%COLLECTIONS%': ', '.join(collections) + ')'
                        ,'%INDEX_MENU%': '\n'.join(indexMenu)
                        ,'%INDEX_ARRAY%': ', '.join(indexArray) + ')'
                        })
        self.log('replHash = ' + str(replHash))
        
        html = multiReplace(html, replHash)
        return html

    def search(self, req, form):
        u"""Get query from form, do search and return formatted results."""
        # search.html
        global session, queryFactory
	self.log(str(dir(req)))
        self.baseUrl = req.construct_url(req.unparsed_uri + '/../..');
        self.log("baseUrl = " + self.baseUrl);
        self.htmlTitle.append('search')
        if not form:
            self.globalReplacements['%ERROR%'] = ''
            return self._searchReplace(read_file('search.html'))
        
        self.log('submit: ' + form.get('submit', '<>'))
        qString = form.get('query', '')
        self.log('qString = ' + qString);
        if not qString:
            qString = generate_cqlQuery(form)
            self.log('generated qString = ' + qString)
            if not (len(qString)):
                self.globalReplacements['%ERROR%'] = '<p class="error">No search terms provided.</p>'
                return self._searchReplace(read_file('search.html'))
        
        try:
            query = queryFactory.get_query(session, qString)
        except:
            self.log('*** Unparsable query: %s' % qString)
            raise

        self.log('Searching CQL query: %s' % (qString))
        try:
            rs = db.search(session, query)
        except cql.Diagnostic:
            if not self.redirected:
                self.htmlTitle.append('Error')
            return '<div id="searchresults">%s</div>' % (search_result_unsupported)
        
        # no need to store rs - database does this for us
        self.log('%d Hits' % (len(rs)))
        if len(rs) < 1:
            self.htmlTitle.append('No Matches')
            return '<div id="searchresults">Sorry, we couldn&#0039;t find matching records.</div>'

        nRecs = int(form.get('maximumRecords', 20))
        startRec = int(form.get('startRecord', 0))
        if not startRec:
            page = int(form.get('hitsPage', 1))
            startRec = 1+(nRecs*page)-nRecs
            
        self.log('startRec = ' + str(startRec) + ', nRecs = ' + str(nRecs))
        searchResults = self._format_resultSet(rs, nRecs, startRec, qString = qString)
        self.log('resultSet formatted')
        del rs, startRec, nRecs
        self.globalReplacements['%QUERY%'] = xml_encode(qString)
        return self._searchReplace(searchResults)
        #- end search() -------------------------------------------------------
        
    def _titleFromRecord(self, session, rec):
        u"""Extract title from the record and return."""
        dom = rec.get_dom(session)
        title = ''
        kids = dom.getchildren()
        for child in kids:
            if child.tag.endswith('}title'):
                title += child.text
        if title == '':
            title = 'I don&apos;t know where to find titles for these records...'
        return title
        
    def _format_resultSet(self, rs, nRecs=20, startRec=1, qString=''):
        u"""Format resultSet for HTML display."""
        global session, script, namespaceUriHash
        if not self.redirected:
            self.htmlTitle.append('Results')

        hits = len(rs)
        if (startRec-1 >= hits):
            return '<div class="hitreport">Your search resulted in <strong>%d</strong> hits, however you requested to begin displaying at result <strong>%d</strong>.</div>' % (hits, startRec)

        rows = []
        rows.append('<div id="hitreport">Your search resulted in <strong>%d</strong> hits. Results <strong>%d</strong> - <strong>%d</strong> displayed. <a href="%s/help.html#results" class="helplink">[display explained]</a></div>' % (hits, startRec, min(startRec + nRecs-1, hits), self.baseUrl))
        rows.append('<table id="searchresults" class="searchresults" summary="Search results table"><tbody>')
        rsid = rs.id
        #rsidCgiString = 'rsid=%s' % cgi_encode(str(rsid))
        rsidCgiString = 'query=%s' % cgi_encode(qString)
        topWeight = rs[0].weight # get relevance of best record
        #recs = rs.retrieve(session, startRec-1, nRecs, schema="dc")
        self.log('records batch fetched from remote servers')
        rowClass = ''
        for i in range(min(hits, nRecs)):
            e = None
            #rowClass = ['even','odd'][i % 2]
            rowNum = i + startRec;
            try:
                rsi = rs[(startRec-1)+i]
                rec = rsi.fetch_record(session)
            except AttributeError:
                rsi = rs[(startRec-1)+i]
                try:
                    rec = rsi.fetch_record(session)
                except e:
                    rows.append(''.join((
                            '<tr class="%s">' % (rowClass),
                            '<td class="relv"> %RELV%',
                            '<td class="hit"><div id="spoke-broke-img-mini">%s</div>Record currently unavailable from: <a href="%s">%s</a>' % (spoke_broke_mini, rsi.toURL(), rsi.baseUrl),
                            '</tr>'
                        )))
                    continue

            recid = rec.id
            row = ''.join((
                    '<tr class="%s">' % (rowClass),
                    '<td class="relv"> %RELV%' ,
                    '''<td class="hit"><a href="SCRIPT/record.html?%RECID%" onclick="updateElementByUrl('docArea', 'SCRIPT/record.html?%RECID%'); return false;" title="Display record summary"><strong>%TITLE%</strong></a>''',
                    '</tr>'
                ))
            title = self._titleFromRecord(session, rec).strip()
            # Relevance
#            if ( display_relevance ):# and (rs[0].weight > rs[-1].weight):
            if True:
                # format relevance measure for display
                try:
                    relv = rsi.weight / topWeight
                except ZeroDivisionError:
                    relv = 0
                relv = round(relv * 100)
#                if ( graphical_relevance ):
                if False:
                    n = min((relv/20)+1, 5)
                    graphrel = [u'<table class="graph-rel" summary="Graphical representation for relevance score of %d out of 5" title="%d%% relevant"><tbody><tr>' % (n,relv)]
                    for i in range(5):
                        if i < n:
                            graphrel.append(u'<td class="item%d">*</td>' % (n))
                        else:
                            graphrel.append(u'<td class="item0"> </td>')
                    graphrel.append(u'</tr></tbody></table>')
                    relv = u''.join(graphrel)
                else:
                    if relv == 0: relv = '&lt; 1%'
                    else: relv = str(relv) + '%'
            else:
                relv = ''
                
            replHash = self.globalReplacements.copy()
            replHash.update({'%RECID%': recid
                       ,'%TITLE%': title
                       ,'%RELV%': relv
                       ,'%RECID%': 'recid=%d&amp;store=%s' % (rec.id, rec.recordStore)
                       #,'%RSID%': '%s&amp;startRecord=%d&amp;maximumRecords=%d' % (rsidCgiString, startRec, nRecs)
                       ,'%HITPOSITION%': str(i)
                       ,'SCRIPT': script
                       })
            
            row = multiReplace(row, replHash)
            rows.append(row)
            
        del rs
        rows.append('</tbody></table>')
        # some hit navigation
        if (hits > nRecs):
            totalPages = (hits/nRecs) + int(bool(hits % nRecs)) 
            if (startRec > 1):
                hitlinks = ['<div class="hitnav">'
                           ,'<div class="backlinks">'
                           ,'''<a href="%s/search?%s&amp;hitsPage=1&amp;maximumRecords=%d" title="view first %d results">%s</a>''' % (script, rsidCgiString, nRecs, nRecs, first_page_tag) 
                           ,'''<a href="%s/search?%s&amp;startRecord=%d&amp;maximumRecords=%d" title="view previous %d results">%s</a>''' % (script, rsidCgiString, max(startRec-nRecs, 1), nRecs, nRecs, prev_page_tag)
                           ,'</div>']
            else:
                hitlinks = ['<div class="hitnav">']

            rsidConfig = 'query=' + cgi_encode(qString)
            if (hits > startRec+nRecs-1):
                hitlinks.extend(['<div class="forwardlinks">'
                                ,'''<a href="%s/search?%s&amp;startRecord=%d&amp;maximumRecords=%d" title="view next %d results">%s</a>''' % (script, rsidCgiString, startRec+nRecs, nRecs, min(nRecs, hits-nRecs), next_page_tag)
                                ,'''<a href="%s/search?%s&amp;hitsPage=%d&amp;maximumRecords=%d" title="view final %d results">%s</a>''' % (script, rsidCgiString, totalPages, nRecs, hits%nRecs, final_page_tag)
                                ,'</div>'])
                
            # TODO: find condition where this is necessary? - more than 3 pages?
            numlinks = ['<div class="pagenumnav">'
                       ,'<form action="%s/search">' % (script)
                       ,'<input type="hidden" name="rsid" value="%s"/>' % cgi_encode(rsid)
                       ]
            # text input
            #numlinks.append('Page: <input type="text" name="hitsPage" size="3" value="%d"/> of %d' % ((startRec / nRecs)+1, totalPages))
            # dropdown
            numlinks.append('<input type="hidden" id="query" name="query" value="%s"/>' % xml_encode(qString))
            numlinks.append('Page: <select name="hitsPage">')
            for x in range(1,totalPages+1): # totalPages +1 for range to not exclude upper limit
                if x == (startRec / nRecs)+1:
                    numlinks.append('<option value="%d" selected="selected">%d</option>' % (x,x))
                else:
                    numlinks.append('<option value="%d">%d</option>' % (x,x))
                    
            numlinks.extend(['</select>'
                            ,'of %d' % (totalPages)
                             ])
            
            numlinks.extend(['<input type="submit" value="Go!"/>'
                            ,'</form>'
                            ,'</div><!-- end pagenumnav div -->'
                            ])
            
            hitlinks.append('\n'.join(numlinks))
                
            hitlinks.append('</div> <!-- end hitnav div -->')
            rows.append('<div class="hitnav">%s</div>' % (' '.join(hitlinks)))
            del numlinks, hitlinks
        #- end hit navigation
        
        # XXX: response timing - remove before launch
        if self.opStartTime:
            rows.append('<i>Time taken: %f secs</i>' % (time.time() - self.opStartTime))

        rows[0:0] = ['<div id="leftcol">'
                    ,'<div id="searchresults">'
                    ]
        rows     += ['</div><!-- /searchresults -->'
                    ,'</div><!-- /leftcol -->'
                    ,'<div id="rightcol">'
                    ,'<div id="docArea">'
                    ,'</div><!-- /docArea -->'
                    ,'</div><!-- /rightcol -->'
                    ]
        return '\n'.join(rows)
        #- end _format_resultSet() --------------------------------------------

    # Decodes either of two types of from the form:
    #   recid=<record id>&store=<store name>
    #   rsid=<result set id>&hitposition=<hit position>
    def record(self, req, form):
        self.htmlTitle.append('Record')
        rsid = form.get('rsid', None)
        recid = form.get('recid', None)
        query = form.get('query', None)
        hitpos = int(form.get('hitposition', 0))
        startRec = int(form.get('startRecord', 1))
        nRecs = int(form.get('maximumRecords', 20))
        rs = None
        self.log('recid = ' + str(recid) + ', rsid = ' + str(rsid));
        if bool(recid):
            storeName = form.get('store', None)
            recStore = db.get_object(session, storeName)
            rec = recStore.fetch_record(session, recid)
        else:
            try:
                rs = self._fetch_resultSet(rsid)
            except (c3errors.ObjectDoesNotExistException):
                if query is not None:
                    query = queryFactory.get_query(session, query)
                    rs = db.search(session, query)
                else:
                    return 'Sorry, we have no record of that search.'
            
            rec = rs[hitpos].fetch_record(session)
            recid = rec.id
        
        xslt = etree.XSLT(etree.parse('docRecord.xsl'))
        data = str(xslt.apply(rec.get_dom(session)))

        if debug:
            recTxr = db.get_object(session, 'XmlTransformer') # this just returns the XML source of the document
            doc = recTxr.process_record(session, rec)
            rawXml = html_encode(unicode(doc.get_raw(session), 'utf-8'))
	    #self.log('XML: ' + rawXml)
            #data += '<br><hr><h1>XML</h1>' + rawXml
            del recTxr, doc, rawXml
        startRec = int(form.get('startRecord', 1))
        nRecs = int(form.get('maximumRecords', 20))
        replHash = self.globalReplacements.copy()
        replHash.update({'SCRIPT': script
                        #,'RSID': 'rsid=%s&amp;hitposition=%d&amp;startRecord=%d&amp;maximumRecords=%d' % (cgi_encode(rsid), hitpos, startRec, nRecs)
                        ,'RECID': recid
                        })
        
        data = multiReplace(data, replHash)
        if False:
            data += html_encode(data)
        del rec, rs, startRec, nRecs
        return data
    
    #- end record() -------------------------------------------------------------------

    def _handle_error(self, info):
        return str(info)
    
    def _dispatch(self, req, content, ajax=False):
        if ajax:
            self._send_xml(content, req)
        else:
            if content.startswith('<?xml'):
                self._send_html(content, req)
                return

            if (debug):
                # Append the log messages to the content, but if column CSS is used
                # add it inside a column so it will be placed somewhere visible
                logStr = '\n'.join([
                    '<div id="debugLog">',
                    '<hr>',
                    '<h3>Log Messages</h3><ul>',
                    '<li>',
                    '<li>\n'.join(self.logMessages),
                    '</ul>',
                    '</div> <!-- /debugLog -->'
                ])
                logMatch = re.search('</div>[\\s<!-/]+(single|leftcol)\\b', content)
                self.log('logMatch = ' + str(logMatch))
                if (logMatch == None):
                    content += logStr
                else:
                    pos = logMatch.start(0)
                    content = content[0:pos] + logStr + content[pos:]

            # read the template in
            templatePath = 'tmpl.html'
            tmpl = read_file(templatePath)
            page = tmpl.replace('%CONTENT%', content)
            reps = self.globalReplacements.copy()
            reps.update({'%TITLE%': ' :: '.join(self.htmlTitle)
                        ,'%NAVBAR%': ' | '.join(self.htmlNav)
                       })
            page = multiReplace(page, reps)
            # send the display
            self._send_html(page, req)
            
            
    def handle(self, req):
        global script
        self.htmlTitle = []
        self.htmlNav = []
        self.opStartTime = time.time()
        path = req.uri[1:].rsplit('/', 1)[1]
        # get contents of submitted form
        content = None
        try:
            op = path.rsplit('.')[0]
        except IndexError:
            # 404
            self.htmlTitle.append('Page Not Found')
            content = '<p>1: Could not find your requested page: "%s"</p>' % req.uri

        form = FieldStorage(req)

        # establish if user signed in
        #uh = self._handle_user(req)
        uh = None
        if uh is not None:
            return self._dispatch(req, uh, form.has_key('ajax'))
            
        try:
            fn = getattr(self, op)
        except AttributeError:
            try:
                self.log('req: ' + req.filename)
                contentPath = os.path.join(os.path.dirname(req.filename), path)
                content = read_file(contentPath)
            except:
                # 404
                self.htmlTitle.append('Page Not Found')
                content = '<p>2: Could not find your requested page: "%s"</p>' % contentPath
        else:
#            try:
                content = fn(req, form)
#            except TypeError:
#                # internal function (e.g. log(), rather than a page - raise 404
#                self.htmlTitle.append('Page Not Found')
#                content = '<p>3: Could not find your requested page: "%s"</p>' % path
#                self.log('not found');
#            except:
#                content = self._handle_error(sys.exc_info())

        return self._dispatch(req, content, form.has_key('ajax'))
        #- end handle()


#- Some stuff to do on initialisation
session = None
serv = None
db = None
queryFactory = None
rebuild = True
script = None
prev_page_tag =  '<img class="navButton" src="../images/ShamanPrev.png">Prev'
first_page_tag = '<img class="navButton" src="../images/ShamanFirst.png">First'
next_page_tag =  'Next<img class="navButton" src="../images/ShamanNext.png">'
final_page_tag = 'Last<img class="navButton" src="../images/ShamanLast.png">'
debug = True

def build_architecture(data=None):
    # data argument provided for when function run as clean-up - always None
    global session, serv, db, queryFactory, rebuild 
    session = Session()
    session.environment = 'apache'
    serv = SimpleServer(session, os.path.join(cheshirePath, 'cheshire3', 'configs', 'serverConfig.xml'))
    db = serv.get_object(session, 'db_mets')
    session.database = db.id
    queryFactory = db.get_object(session, 'defaultQueryFactory')
    rebuild = False

build_architecture()
searchHandler = SearchHandler()                                          # initialise handler

def handler(req):
    global script, rebuild, searchHandler, userStore
    script = req.subprocess_env['SCRIPT_NAME']
    req.register_cleanup(build_architecture)
    try:
        remote_host = req.get_remote_host(apache.REMOTE_NOLOOKUP)                   # get the remote host's IP for logging
        os.chdir(os.path.join(cheshirePath, 'cheshire3','www','hub','html'))        # cd to where html fragments are
        searchHandler.handle(req)                                               # handle request
        return apache.OK
        
    except Exception, e:
        req.content_type = "text/html"
        cgitb.Hook(file=req).handle()                                            # give error info
        return apache.HTTP_INTERNAL_SERVER_ERROR
    
#- end handler()
