#
# Program:   eadSearchHandler.py
# Version:   0.27
# Description:
#            Web interface for searching a cheshire 3 database of EAD finding aids
#            - part of Cheshire for Archives v3
#
# Required externals:
#            Py: localConfig.py, wwwSearch.py
#            HTML: browse.html, email.html, help.html, index.html, subject.html, template.ssi
#            CSS: struc.css, style.css
#            Javascript: ead.js
#            Images: c3_black.gif, v3_full.gif, v3_email.gif, v3_simlr.gif, 
#                    folderClosed.jpg, folderOpen.jpg folderItem.jpg
#                    barPlus.gif, barMinus.gif, barT.gif, barLast.gif
#                    fback.gif, back.gif, forward.gif fforward.gif
#
# Language:  Python
# Author:    JH - John Harrison <john.harrison@liv.ac.uk>
# Date:      18 July 2007
#
# Copyright: &copy; University of Liverpool 2005-2007
#
# Version History:
# 0.01 - 13/04/2005 - JH - Basic search, browse and display functions.
# 0.02 - 09/05/2005 - JH - Loads of additional functionality, subject clustering, email records
# 0.03 - 13/05/2005 - JH - Transformed documents cached in a documentStore
# 0.04 - 19/05/2005 - JH - Multi-page full record display. Reverted to filesystem caching
# 0.05 - 25/05/2005 - JH - Resolves internal links to their correct page in multipage docs
#                        - Ditto for ToC (in nested <ul>s)
# 0.06 - 23/06/2005 - JH - Dual column display for search results, leaves rh column free for summary etc.
#                        - ResultSets stored in ResultSetStore, retrieved whenever needed (subsequent result pages etc.)
#                        - Hits taken from resultSetStore for subsequent operations (e.g. summary, email, similar search etc.)
# 0.07 - 07/11/2005   JH - Components stored and indexed in database, so dealt with simply in search handler.
#                          (required generalisation of XPaths and XSLT transformations)
#                        - search forms served by apache - no need to fire-up handler for something so simple.
#                        - Simple DC records (generated during build) used for faster common XPath extractions (hit display + similar search)
#                        - Search term highlighting in summary display
#                        - Logging object added, log strings kept in mem until request completed, then flushed to logfile
#                        - Logging class and methods moved to wwwSearch module to allow use by other interfaces
# 0.08 - 22/11/2005 - JH - ToC generation and processing shuffled to minimise multiple user complications
#                        - Maximum page size calculations moved to localConfig as they're used multiple times
# 0.09 - 09/12/2005 - JH - Browsing duplicate terms bug fixed
#                          Browse/Subject links to search fixed by improved indexing
#                          Multiple error catching improvements
# 0.10 - 06/01/2006 - JH - Erroneous navigation text removed by adding redirected boolean
#                        - Highlighting wrong word due to 's bug fixed
# 0.11 - 26/01/2006 - JH - localhost global variable added - defined in localConfig.py
#                          More highlight, browse link and character encoding bug fixes
# 0.12 - 31/01/2006 - JH - More minor bug fixes - too trivial to mention
# 0.13 - 08/02/2006 - JH - Browse CQL query generated using wwwSearch.generate_cqlQuery() - fixes 'Next x Terms' bug
# 0.14 - 20/03/2006 - JH - More browse debugging, erroneous error messages removed
#                        - Some resultSet debugging, and query failsafe added
#                        - optional argument 'maxResultSetSize' added to search function
#                        - similar_search made marginally more efficient
#                        - additional function scripted to format resultSet for display - should make things more efficient/reusable
#                        - emailing made more efficient, parent title included in component emails
#                        - CSS tweaks
#                        - Browsing outside of range of index terms caught and more enlightening error message returned
#                        - db refreshed every time - this will slow things down but might help with cached index issue (i.e. when records have been added live using the admin interface)
# 0.15 - 04/08/2006 - JH - Switch for removing relevance accomodated (requires localConfig.py v0.09)
#                        - Accented character stuff fixed
#                        - Number of records displayed in subject resolve results
# 0.16 - 24/08/2006 - JH - Subject resolving on empty database error caught
# 0.17 - 21/09/2006 - JH - Some more tidying up and better error catching and handling
#                        - Exceptions caught and logged to file. Pretty handler-style page returned reporting error
# 0.18 - 13/10/2006 - JH - Slight tweaks to summary display allowing link to full-text
#                        - Some optimisation to reduce memory load
# 0.19 - 20/10/2006 - JH - mods to way full-text display pages are named. 'p' added to distinguish page number from id e.g.: recid-p1.shtml
# 0.20 - 30/11/2006 - JH - Some refactoring to display_record in preparation for a 'preview ead' function in eadAdminHandler
#                        - Mods to similar search for faster results (fingers crossed)
#                          also remove lots of splitting, normalising stuff that will be handled during the search
# 0.21 - ??/02/2007 - JH - Implemented 'search within' function
#                        - nunmerous bug fixes in browsing, and displays
# 0.22 - 21/03/2007 - JH - Catch ObjectDoesNotExistException as well as FileDoesNotExistException (due to Cheshire3 exception change)
# 0.23 - 28/03/2007 - JH - Printable ToC option implemented. XSLT tweaked for full ToC display (list only collapsed in full-text display)
# 0.24 - 11/05/2007 - JH - Highlighting deactivated when full-text index searched (can take a long time to complete)
#                        - Template replacements streamlined
# 0.25 - 18/06/2007 - JH - resultSetItem API change accomodated
# 0.26 - 27/06/2007 - JH - 'cqlquery' --> 'query' - backward compatibility for existing links
#                        - Improved cleverTitleCase conditions
#                        - show/hide python traceback added to error page
# 0.27 - 18/07/2007 - JH - Fixed email, and similar search bugs.
#                        - Accented characters normalised for emailing record.
#
#


# import mod_python stuffs
from mod_python import apache, Cookie
from mod_python.util import FieldStorage
# import generally useful modules
import sys, traceback, os, cgitb, urllib, time, smtplib, re
# import customisable variables
from localConfig import *
# set sys paths 
osp = sys.path
sys.path = [os.path.join(cheshirePath, 'cheshire3', 'code')]
sys.path.extend(osp)
# import Cheshire3/PyZ3950 stuff
from server import SimpleServer
from PyZ3950 import CQLParser, SRWDiagnostics
from baseObjects import Session
from document import StringDocument
import c3errors
# C3 web search utils
from wwwSearch import *
# email modules
from email import Message, MIMEMultipart, MIMEText


class EadSearchHandler:
    global repository_name, repository_link, repository_logo, htmlPath
    templatePath = os.path.join(htmlPath, 'template.ssi')
    htmlTitle = None
    htmlNav = None
    logger = None
    globalReplacements = None
    redirected = False

    def __init__(self, lgr):
        global repository_name, repository_link, repository_logo, script
        self.htmlTitle = []
        self.htmlNav = []
        self.logger = lgr
        self.globalReplacements = {'%REP_NAME%': repository_name,
                              '%REP_LINK%': repository_link,
                              '%REP_LOGO%': repository_logo,
                              'SCRIPT': script,
                              '%SCRIPT%': script
                              }

    #- end __init__() ----------------------------------------------------------
    
    def send_html(self, data, req, code=200):
        req.content_type = 'text/html'
        req.content_length = len(data)
        req.send_http_header()
        if (type(data) == unicode):
          data = data.encode('utf-8')
        req.write(data)
        req.flush()
        
    #- end send_html() ---------------------------------------------------------

    def _parentTitle(self, id):
        try:
            rec = dcRecordStore.fetch_record(session, id)
        except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
            try:
                rec = recordStore.fetch_record(session, id)
            except:
                return None
                
        try:
            parentTitle = rec.process_xpath('/sru_dc:dc/dc:title/text()', namespaceUriHash)[0]
        except IndexError:
            try:
                parentTitle = rec.process_xpath('did[1]/unittitle/text()')[0]
            except IndexError:
                try:
                    parentTitle = rec.process_xpath('/ead/eadheader/filedesc/titlestmt/titleproper/text()')[0]
                except IndexError:
                    parentTitle = '(untitled)'
                
        parentTitle = nonAsciiRe.sub(_asciiFriendly, parentTitle)
        if (type(parentTitle) == unicode):
            try:
                parentTitle = parentTitle.encode('utf-8')
            except:
                parentTitle = '(unable to render parent title)'

        return parentTitle

    
    #- end _parentTitle() ---------------------------------------------------------


    def format_resultSet(self, rs, firstrec=1, numreq=20, highlight=1):
        global search_result_row, search_component_row, display_relevance, graphical_relevance
        hits = len(rs)
        rsid = rs.id
        if not self.redirected:
            self.htmlTitle.append('Results')
            
        # check scaledWeights not horked (i.e. check they're not all 0.5)
        try:
            assert (rs[0].scaledWeight <> 0.5 and rs[-1].scaledWeight <> 0.5)
        except: 
            useScaledWeights = False
             # get relevance of best record
            topWeight = rs[0].weight
        else: 
            useScaledWeights = True
        
        if (firstrec-1 >= len(rs)):
            return '<div class="hitreport">Your search resulted in <strong>%d</strong> hits, however you requested to begin displaying at result <strong>%d</strong>.</div>' % (hits, firstrec)
        
        rows = ['''<script type="text/javascript"> <!-- 
                function loadPage() {
                    closeSplash(); 
                }
                --> </script>''',
                '<div id="hitreport">Your search resulted in <strong>%d</strong> hits. Results <strong>%d</strong> - <strong>%d</strong> displayed. <a href="/ead/help.html#results">[Result display explained]</a></div>' % (hits, firstrec, min(firstrec + numreq-1, len(rs))),
                '\n<table id="results" class="results">']

        parentTitles = {}
        rsidCgiString = '&amp;rsid=%s' % cgi_encode(rsid)

        for x in range(firstrec-1, min(len(rs), firstrec -1 + numreq)):
            r = rs[x]
            try:
                try:
                    rec = dcRecordStore.fetch_record(session, r.docid);
                except AttributeError:
                    # API change
                    rec = dcRecordStore.fetch_record(session, r.id);
                    
            except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                # no DC record, probably component
                try:
                    rec = r.fetch_record(session)
                except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                    try:
                        self.logger.log('Unable to retrieve record: %s' % (r.docid))
                    except:
                        # API change
                        self.logger.log('Unable to retrieve record: %s' % (r.id))
                    continue
                else:
                    try:
                        title = rec.process_xpath('did[1]/unittitle/text()')[0]
                    except IndexError:
                        try:
                            title = rec.process_xpath('/ead/eadheader/filedesc/titlestmt/titleproper/text()')[0]
                        except IndexError:
                            title = '(untitled)'
            else:
                try:
                    title = rec.process_xpath('/sru_dc:dc/dc:title/text()', namespaceUriHash)[0]
                except IndexError:
                    title = '(untitled)'
            
            title = nonAsciiRe.sub(_asciiFriendly, title)

            if ( display_relevance ) and (rs[0].weight > rs[-1].weight):
                # format relevance measure for display
                if (useScaledWeights):
                    relv = float(r.scaledWeight)
                else:
                    relv = r.weight / topWeight
                    
                relv = int(relv * 100)
                if ( graphical_relevance ):
                    relv = '''
                    <table width="100" style="border:0;" cellpadding="0" cellspacing="0">
                      <tr>
                        <td background="%s" width="%d"></td>
                        <td><img src="/images/spacer1x20.gif" alt=""/></td>
                      </tr>
                    </table>''' % (relevance_graphic, relv)
                else:
                    if relv == 0: relv = '&lt; 1%'
                    else: relv = str(relv) + '%'
            else:
                relv = ''
            
            try:
                parentId = rec.process_xpath('/c3component/@parent')[0]
            except IndexError:
                # full record
                row = search_result_row
                parentLink = ''
            else:
                # OK, must be a component record
                row = search_component_row
                parentId = parentId.split('/')[-1]
                try:
                    parentTitle = parentTitles[parentId];
                except KeyError:
                    parentTitle = self._parentTitle(parentId)
                    parentTitles[parentId] = parentTitle
                
                if parentTitle:
                    parentLink = '<a href="%s?operation=full&amp;recid=%s" title="Link to Complete Collection Description" onclick="SPLASH">%s</a>' % (script, parentId , parentTitle)
                else:
                    parentLink = '(unable to locate parent document)'
            
            if (display_splash_screen_popup ):
                splash = 'splashScreen();'
            else:
                splash = ''

            replHash = {'%RECID%': rec.id
                       ,'%PARENT%': parentLink
                       ,'%TITLE%': title
                       ,'%RELV%': relv
                       ,'%RSID%': '%s&amp;firstrec=%d&amp;numreq=%d&amp;highlight=%d' % (rsidCgiString, firstrec, numreq, highlight)
                       ,'%HITPOSITION%': str(x)
                       ,'SCRIPT': script
                       ,'SPLASH': splash
                       }
            row = multiReplace(row, replHash)
            rows.append(row)

        #- end for each hit
        del rs
            
        rows.append('</table>')

        # some hit navigation
            
        if (hits > numreq):
            if (firstrec > 1):
                hitlinks = ['<div class="backlinks"><a href="%s?operation=search%s&amp;firstrec=%d&amp;numreq=%d&amp;highlight=%d">Previous</a></div>'
                                % (script, rsidCgiString, max(firstrec-numreq, 1), numreq, highlight)]
            else:
                hitlinks = []

            if (hits > firstrec+numreq-1):
                hitlinks.append('<div class="forwardlinks"><a href="%s?operation=search%s&amp;firstrec=%d&amp;numreq=%d&amp;highlight=%d">Next</a></div>'
                                 % (script, rsidCgiString, firstrec+numreq, numreq, highlight))

            numlinks = ['<div class="numnav">']
            for x in range(1, hits+1, numreq):
                if (x == firstrec):
                    numlinks.append('<strong>%d-%d</strong>' % (x, min(x+numreq-1, hits)))
                elif (x == hits):
                    numlinks.append('<a href="%s?operation=search%s&amp;firstrec=%d&amp;numreq=%d&amp;highlight=%d">%d</a>'
                                    % (script, rsidCgiString, x, numreq, highlight, x))
                else:
                    numlinks.append('<a href="%s?operation=search%s&amp;firstrec=%d&amp;numreq=%d&amp;highlight=%d">%d-%d</a>'
                                    % (script, rsidCgiString, x, numreq, highlight, x, min(x+numreq-1, hits)))

            numlinks.append('</div>')
            hitlinks.append(' | '.join(numlinks))
            rows.append('<div class="hitnav">%s</div>' % (' '.join(hitlinks)))
            del numlinks, hitlinks
        #- end hit navigation
       
        return '\n'.join(rows)
        
    #- end format_resultSet() ---------------------------------------------------------


    def search(self, form, maxResultSetSize=None):
        global recordStore, resultSetStore
        firstrec = int(form.get('firstrec', 1))
        numreq = int(form.get('numreq', 20))
        highlight = int(form.get('highlight', 1))
        rsid = form.get('rsid', None)
        qString = form.get('query', form.get('cqlquery', None))
        withinCollection = form.get('withinCollection', None)

        if (rsid):
            try:
                rs = resultSetStore.fetch_resultSet(session, rsid)
            except:
                rsid = cgi_decode(rsid)
                try:
                    query = CQLParser.parse(cgi_decode(rsid))
                except:
                    self.logger.log('Unretrievable resultSet %s' % (rsid))
                    if not self.redirected:
                        self.htmlTitle.append('Error')
                    return '<p class="error">Could not retrieve resultSet from resultSetStore. Please re-submit your search</p>'
                else:
                    self.logger.log('Searching CQL query: %s' % (rsid))
                    rs = db.search(session, query)
                        
            else:
                self.logger.log('Retrieved resultSet "%s"' % (rsid))
            
            rs.id = rsid
        else:
            if not qString:
                qString = generate_cqlQuery(form)
                if not (len(qString)):
                    if not self.redirected:
                        self.htmlTitle.append('Error')
                    self.logger.log('*** Unable to generate CQL query')
                    return '<p class="error">Could not generate CQL query.</p>'
                
            if (withinCollection and withinCollection != 'allcollections'):
                qString = '(c3.ead-idx-docid exact "%s" or ead.parentid exact "%s/%s") and/relevant %s' % (withinCollection, recordStore.id, withinCollection, qString)
            elif (form.has_key('noComponents')):
                qString = 'ead.istoplevel=1 and/relevant ' + qString
            
            try:
                query = CQLParser.parse(qString)
            except:
                self.logger.log('*** Unparsable query: %s' % qString)
                raise

            self.logger.log('Searching CQL query: %s' % (qString))
            try:
                rs = db.search(session, query)
            except SRWDiagnostics.Diagnostic24:
                if not self.redirected:
                    self.htmlTitle.append('Error')
                return '''<p class="error">Search Failed. Unsupported combination of relation and term.</p>
                    <p><strong>HINT</strong>: Did you provide too many, or too few search terms?<br/>
                    \'Between\' requires 2 terms expressing a range.<br/>
                    \'Before\' and \'After\' require 1 and only 1 term.
                    </p>'''
            
            if maxResultSetSize:
                rs.fromList(rs[:maxResultSetSize])

            self.logger.log('%d Hits' % (len(rs)))
            if (len(rs) > 5000):
                # probably quicker to resubmit search than store/retrieve resultSet
                self.logger.log('very large resultSet - passing CQL for repeat search')
                rsid = rs.id = qString
            elif (len(rs)):
                # store this resultSet and remember identifier
                try:
                    resultSetStore.begin_storing(session)
                    rsid = rs.id = str(resultSetStore.create_resultSet(session, rs))
                    resultSetStore.commit_storing(session)
                except c3errors.ObjectDoesNotExistException:
                    self.logger.log('could not store resultSet - passing CQL for repeat search')
                    rsid = rs.id = qString
            else:
                self.htmlTitle.append('No Matches')
                return '<p>No records matched your search.</p>'
        
        # disable highlighting if full-text search has been used - highlighting takes forever!
        if qString and (qString.find('cql.anywhere') > -1):
            highlight = 0
            
        return self.format_resultSet(rs, firstrec, numreq, highlight)

    #- end search() ------------------------------------------------------------
    
    def _cleverTitleCase(self, txt):
        global stopwords
        words = txt.split()
        for x in range(len(words)):
            if (x == 0 and not words[x][0].isdigit()) or (words[x][0].isalpha()) and (words[x] not in stopwords):
                words[x] = words[x].title()
        return ' '.join(words)
    
    #- end _cleverTitleCase() --------------------------------------------------
    

    def browse(self, form):
        idx = form.get('fieldidx1', None)
        rel = form.get('fieldrel1', 'exact')
        scanTerm = form.get('fieldcont1', '')
        firstrec = int(form.get('firstrec', 1))
        numreq = int(form.get('numreq', 25))
        rp = int(form.get('responsePosition', numreq/2))
        qString = '%s %s "%s"' % (idx, rel, scanTerm)
        try:
            scanClause = CQLParser.parse(qString)
        except:
            qString = generate_cqlQuery(form)
            try:
                scanClause = CQLParser.parse(qString)
            except:
                self.logger.log('Unparsable query: %s' % qString)
                self.htmlTitle.append('Error')
                return '<p class="error">An invalid query was submitted.</p>'
            
        self.htmlTitle.append('Browse Indexes')
        self.logger.log('Browsing for "%s"' % (qString))

        hitstart = False
        hitend = False
        
        if (scanTerm == ''):
            hitstart = True
            rp = 0
        if (rp == 0):
            scanData = db.scan(session, scanClause, numreq, direction=">")
            if (len(scanData) < numreq): hitend = True
        elif (rp == 1):
            scanData = db.scan(session, scanClause, numreq, direction=">=")
            if (len(scanData) < numreq): hitend = True
        elif (rp == numreq):
            scanData = db.scan(session, scanClause, numreq, direction="<=")
            scanData.reverse()
            if (len(scanData) < numreq): hitstart = True
        elif (rp == numreq+1):
            scanData = db.scan(session, scanClause, numreq, direction="<")
            scanData.reverse()
            if (len(scanData) < numreq): hitstart = True
        else:
            # Need to go down...
            try:
                scanData = db.scan(session, scanClause, rp, direction="<=")
            except:
                scanData = []
            # ... then up
            try:
                scanData1 = db.scan(session, scanClause, numreq-rp+1, direction=">=")
            except:
                scanData1 = []
            
            
            if (len(scanData1) < numreq-rp+1):
                hitend = True
            if (len(scanData) < rp):
                hitstart = True
            # try to stick them together
            try:
                if scanData1[0][0] == scanData[0][0]:
                    scanData = scanData[1:]
            except:
                pass

            scanData.reverse()
            scanData.extend(scanData1)
            del scanData1
            
        totalTerms = len(scanData)

        if (totalTerms > 0):
            self.htmlTitle.append('Results')
            rows = ['<div id="wrapper"><div id="single"><br/>',
                    '<table cellspacing="0" summary="list of terms in this index">',
                    '<tr class="headrow"><td>Term</td><td>Records</td></tr>']

            rowCount = 0
            if (hitstart):
                rows.append('<tr class="odd"><td colspan="2">-- start of index --</td></tr>')
                rowCount += 1
                prevlink = ''
            else:
                prevlink = '<a href="%s?operation=browse&amp;fieldidx1=%s&amp;fieldrel1=%s&amp;fieldcont1=%s&amp;responsePosition=%d&amp;numreq=%d"><!-- img -->Previous %d terms</a>' % (script, idx, rel, cgi_encode(scanData[0][0]), numreq+1, numreq, numreq)
            
            dodgyTerms = []
            for i in range(len(scanData)):
                item = scanData[i]
                term = item[0]
                if not term:
                    continue

                # TODO: ideally get original, un-normalised version from index
                # until then do a clever version of term.title()
                if (idx not in ['dc.identifier']):
                    displayTerm = self._cleverTitleCase(term)
                else:
                    displayTerm = term

#                seq = range(len(term))
#                seq.reverse()
#                try: term.encode('utf-8', 'latin-1')
#                except: raise
#                for x in seq:
#                    #term = term[:x]
#                    try:
#                        term = term[:x].encode('utf-8')
#                    except UnicodeDecodeError: continue
#                    break
#                
#                if len(term) <= 1:
#                    continue
                
                if (term.lower() == scanTerm.lower()):
                    displayTerm = '<strong>%s</strong>' % displayTerm
                    
                rowCount += 1                   
                if (rowCount % 2 == 1): rowclass = 'odd';
                else: rowclass = 'even';
                
                row = browse_result_row
                paramDict =  {
                    '%ROWCLASS%': rowclass,
                    '%IDX%': idx, 
                    '%REL%': rel, 
                    '%CGITERM%': cgi_encode(term), 
                    '%TERM%': displayTerm, 
                    '%COUNT%': str(item[1][1]),
                    'SCRIPT': script
                }
                for key, val in paramDict.iteritems():
                    row = row.replace(key, val)

                rows.append(row)

            #- end for each item in scanData
                
            if (hitend):
                rowCount += 1
                if (rowCount % 2 == 1): rowclass = 'odd';
                else: rowclass = 'even';
                rows.append('<tr class="%s"><td colspan="2">-- end of index --</td></tr>' % (rowclass))
                nextlink = ''
            else:
                nextlink = '<a href="%s?operation=browse&amp;fieldidx1=%s&amp;fieldrel1=%s&amp;fieldcont1=%s&amp;responsePosition=%d&amp;numreq=%d"><!-- img -->Next %d terms</a>' % (script, idx, rel, cgi_encode(scanData[-1][0]), 0, numreq, numreq)

            del scanData
            rows.append('</table>')           
            rows.extend(['<div class="scannav"><p>%s</p></div>' % (' | '.join([prevlink, nextlink])),
                         '</div><!-- end of single div -->',
                         '</div> <!-- end of wrapper div -->'
                         ])
            #- end hit navigation
            
            return '\n'.join(rows)

        else:
            self.htmlTitle.append('Error')
            return '<p class="error">No terms retrieved from index. You may be browsing outside the range of terms within the index.</p>'

    #- end browse() ------------------------------------------------------------


    def subject_resolve(self, form):
        global display_relevance, graphical_relevance
        cont = form.get('fieldcont1', None)
        firstrec = int(form.get('firstrec', 1))
        numreq = int(form.get('numreq', 25))
        self.htmlTitle.append('Find Subjects')
        if not cont:
            content = read_file('subject.html').replace('SCRIPT', script)
            return content

        session.database = 'db_ead_cluster'
        qString = 'cql.anywhere all/stem/relevant "%s"' % (cont)
        self.logger.log('Resolving subject "%s"' % (cont))
        query = CQLParser.parse(qString)
        rs = clusDb.search(session, query)
        if (rs):
            # FIXME: remove once Cheshire3 code is fixed
#            rs.order(session, 'weight')
#            rs.reverse(session)
            rs.scale_weights()
            # end remove
            self.htmlTitle.append('Results')        
            rs = rs[:min(len(rs), firstrec + numreq - 1)]
            rows = ['<div id="wrapper"><div id="single">',
                    '<table cellspacing="0" summary="suggested relevant subject headings">',
                    '<tr class="headrow"><td>Subject</td><td class="relv">Relevance</td><td class="hitcount">Predicted Hits</td></tr>']
            rowCount = 0
            for r in rs:
                rowCount += 1                   
                if (rowCount % 2 == 1):
                    rowclass = 'odd';
                else:
                    rowclass = 'even';
                    
                subject = r.fetch_record(session).process_xpath('cluster/key/text()')[0]
                self.logger.log('starting subject find hit estimate')
                try:
                    sc = CQLParser.parse('dc.subject exact "%s"' % (subject))
                    session.database = 'db_ead'
                    scanData = db.scan(session, sc, 1, direction=">=")
                    session.database = 'db_ead_cluster'
                    hits = scanData[0][1][1]
                    del sc, scanData
                except:
                    hits = 'N/A'

                if ( display_relevance ):
                    #relv = r.weight
                    relv = int(r.scaledWeight * 100)
                    if ( graphical_relevance ):
                        relv = '''
                        <table width="100" style="border:0;" cellpadding="0" cellspacing="0">
                          <tr>
                            <td background="%s" width="%d"></td>
                            <td><img src="/images/spacer1x20.gif" alt=""/></td>
                          </tr>
                        </table>''' % (relevance_graphic, relv)
                    else:
                        if relv < 1: relv = '&lt; 1%'
                        else: relv = str(relv) + '%'
                else:
                    relv = ''

                row = subject_resolve_row
                subject = self._cleverTitleCase(subject)
                paramDict = {
                    '%ROWCLASS%': rowclass, 
                    '%CGISUBJ%':cgi_encode(subject), 
                    '%TITLE%': subject,
                    '%RELV%': relv,
                    '%COUNT%': str(hits),
                    'SCRIPT':script
                }
                for k, v in paramDict.iteritems():
                    row = row.replace(k, v)

                rows.append(row)

            rows.append('</table></div></div>')                
            content = '\n'.join(rows)
            
        else:
            self.htmlTitle.append('No Matches')        
            content = '<p>No relevant terms were found.</p>'
            
        session.database = 'db_ead'
        return content
        
    #- end subject_resolve() ---------------------------------------------------

    def display_summary(self, rec, paramDict, proxInfo=None, highlight=1):
        recid = rec.id
        self.logger.log('Summary requested for record: %s' % (recid))
        # highlight search terms in rec.sax
        if (proxInfo) and highlight:
            try:
                # to save repeated calls to get_sax
                saxEvnts = rec.get_sax()
                # for each pair of terms in result.proxInfo
                for x in range(0, len(proxInfo), 2):
                    located = False
                    wordCount = 0
                    # for each subsequent sax event
                    for y in range(proxInfo[x] + 1, len(saxEvnts)):
                        if (saxEvnts[y][0] == '3') and not located:
                            # keep leading space to find first word
                            spaceline = punctuationRe.sub(' ', saxEvnts[y][2:])
                            # Words ending in 's are treated as 2 words in proximityInfo - make it so!
                            spaceline = spaceline.replace('\'s', ' s') 
                            words = wordRe.findall(spaceline)
                            try:
                                start = sum(map(len, words[:proxInfo[x+1] - wordCount]))
                                end = start + len(words[proxInfo[x+1] - wordCount])
                                wp = 0
                                while words[proxInfo[x+1] - wordCount][wp] == ' ':
                                    wp += 1

                                start += wp

                                newSax = saxEvnts[y][:2+start] + 'HGHLGHT' + saxEvnts[y][2+start:2+end] + 'THGLHGH' + saxEvnts[y][2+end:]
                                rec.sax[y] = newSax
                                located = True
                                break
                            
                            except IndexError:
                                # haven't got to the occurence yet, but current text node has ended - go to next one
                                wordCount += len(words)
                                continue
                            except:
                                continue

            except:
                # hmm proxInfo busted - oh well
                self.logger.log('unable to highlight')
                
            self.logger.log('Search terms highlighted')

        # NEVER cache summaries - always generate on the fly - as we highlight search terms         
        # send record to transformer
        #self.logger.log(rec.get_xml())
        doc = summaryTxr.process_record(session, rec)
        del rec
        summ = doc.get_raw()
        summ = nonAsciiRe.sub(_asciiFriendly, summ)
        summ = overescapedAmpRe.sub(_unescapeCharent, summ)
        self.logger.log('Record transformed to HTML')
        try:
            summ = summ.encode('utf-8', 'latin-1')
        except:
            #pass # hope for the best! 
            return (False, '<div id="padder"><div id="rightcol"><p class="error">Record contains non-ascii characters and cannot be transformed to HTML.</p></div></div><div id="leftcol" class="results">%s</div>' % (searchResults))
            
        summ = '<div id="padder"><div id="rightcol">%s</div></div>' % (summ)
        # get template, insert info and return
        tmpl = read_file(self.templatePath)
        page = tmpl.replace('%CONTENT%', '<div id="leftcol">LEFTSIDE</div>%s' % (summ))
        for k, v in paramDict.iteritems():
            page = page.replace(k, v)
            
        return page


    def display_full(self, rec, paramDict, isComponent):
        global toc_cache_path, max_page_size_bytes, cache_url, overescapedAmpRe, toc_scripts, anchorRe
        recid = rec.id
        if (len(rec.get_xml()) < max_page_size_bytes) or isComponent:
            doc = fullTxr.process_record(session, rec)
        else:
            doc = fullSplitTxr.process_record(session, rec)

        # open, read, and delete tocfile NOW to avoid overwriting screwups
        try:
            tocfile = read_file(os.path.join(toc_cache_path, 'foo.bar'))
        except IOError:
            tocfile = None
        else:
            os.remove(os.path.join(toc_cache_path, 'foo.bar'))
            tocfile = nonAsciiRe.sub(_asciiFriendly, tocfile)
            try: 
                tocfile = tocfile.encode('utf-8', 'latin-1')
            except:
                try:
                    tocfile = tocfile.encode('utf-16')
                except:
                    pass # hope for the best
            
            tocfile = tocfile.replace('RECID', recid)
            tocfile = overescapedAmpRe.sub(_unescapeCharent, tocfile)
        
        doc = doc.get_raw()
        if type(doc) == unicode:
            try: doc = doc.encode('utf-8', 'latin-1')
            except:
                try: doc = doc.encode('utf-16')
                except: pass # hope for the best!
                
        doc = overescapedAmpRe.sub(_unescapeCharent, doc)
        tmpl = read_file(self.templatePath)
        if (len(rec.get_xml()) < max_page_size_bytes) or isComponent:
            # Nice and short record/component - do it the easy way
            self.logger.log('HTML generated by non-splitting XSLT')
            # resolve anchors to only page
            doc = doc.replace('PAGE#', '%s/RECID-p1.shtml#' % cache_url)
            doc = nonAsciiRe.sub(_asciiFriendly, doc)
            page = tmpl.replace('%CONTENT%', toc_scripts + doc)
            for k, v in paramDict.iteritems():
                page = page.replace(k, v)

            write_file(os.path.join(cache_path, recid + '-p1.shtml'), page)
            
        else:
            # Long record - have to do splitting, link resolving etc.
            self.logger.log('HTML generated by splitting XSLT')
            # before we split need to find all internal anchors
            anchors = anchorRe.findall(doc)
            pseudopages = doc.split('<p style="page-break-before: always"></p>')
            pages = []
            while pseudopages:
                page = '<div id="padder"><div id="rightcol" class="ead">%PAGENAV%'
                while (len(page) < max_page_size_bytes):
                    page = page + pseudopages.pop(0)
                    if not pseudopages:
                        break
                
                # append: pagenav, end rightcol div, padder div, left div (containing toc)
                page = page + '%PAGENAV%<br/>\n<br/>\n</div>\n</div>\n<div id="leftcol" class="toc"><!--#include virtual="/ead/tocs/RECID.inc"--></div>'
                pages.append(page)

            start = 0
            anchorPageHash = {}
            for a in anchors:
                if len(a.strip()) > 0:
                    for x in range(start, len(pages), 1):
                        if (pages[x].find('name="%s"' % a) > -1):
                            anchorPageHash[a] = x + 1
                            start = x                                  # next anchor must be on this page or later

            self.logger.log('Links resolved over multiple pages (%d pages)' % (len(pages)))

            for x in range(len(pages)):
                doc = pages[x]
                # now we know how many real pages there are, generate some page navigation links
                if len(pages) > 1:
                    pagenav = ['<div class="pagenav">', '<div class="backlinks">']
                    if (x > 0):
                        pagenav.extend(['<a href="%s/%s-p1.shtml" title="First page" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))"><img src="/images/fback.gif" alt="First"/></a>' % (cache_url, recid, recid), 
                                        '<a href="%s/%s-p%d.shtml" title="Previous page" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))"><img src="/images/back.gif" alt="Previous"/></a>' % (cache_url, recid, x, recid)
                                      ])
                    pagenav.extend(['</div>', '<div class="forwardlinks">'])
                    if (x < len(pages)-1):
                        pagenav.extend(['<a href="%s/%s-p%d.shtml" title="Next page" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))"><img src="/images/forward.gif" alt="Next"/></a>' % (cache_url, recid, x+2, recid),
                                        '<a href="%s/%s-p%d.shtml" title="Final page" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))"><img src="/images/fforward.gif" alt="Final"/></a>' % (cache_url, recid, len(pages), recid)
                                      ])
                    pagenav.extend(['</div>', '<div class="numnav">'])
                    for y in range(len(pages)):
                        if (y == x):
                            pagenav.append('<strong>%d</strong>' % (y+1))
                        else:
                            pagenav.append('<a href="%s/%s-p%d.shtml" title="Page %d" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))">%d</a>' % (cache_url, recid, y+1, y+1, recid, y+1))
                    pagenav.extend(['</div> <!--end numnav div -->', '</div> <!-- end pagenav div -->'])
                else:
                    pagenav = []
                
                doc = nonAsciiRe.sub(_asciiFriendly, doc)
                pagex = tmpl.replace('%CONTENT%', toc_scripts + doc)
                pagex = pagex.replace('%PAGENAV%', '\n'.join(pagenav))

                #resolve internal ref links
                for k, v in anchorPageHash.iteritems():
                    pagex = pagex.replace('PAGE#%s"' % k, '%s/RECID-p%d.shtml#%s"' % (cache_url, v, k))

                # any remaining links were not anchored - encoders fault :( - hope they're on page 1
                pagex = pagex.replace('PAGE#', '%s/RECID-p1.shtml#' % (cache_url))
                
                for k, v in paramDict.iteritems():
                    pagex = pagex.replace(k, v)
                    
                write_file(os.path.join(cache_path, recid + '-p%d.shtml' % (x+1)), pagex)
                if (x == 0):
                    page = pagex

            self.logger.log('Multi-page navigation generated')
 
        del rec
        if tocfile:
            try:
                for k, v in anchorPageHash.iteritems():
                    tocfile = tocfile.replace('PAGE#%s"' % k, '%s/%s-p%d.shtml#%s"' % (cache_url, recid, v, k))
            except UnboundLocalError:
                pass
            
            # any remaining links were not anchored - encoders fault :( - hope they're on page 1
            tocfile = multiReplace(tocfile, {'SCRIPT': script, 'PAGE#': '%s/%s-p1.shtml#' % (cache_url, recid)})
            write_file(os.path.join(toc_cache_path, recid +'.inc'), tocfile)
            os.chmod(os.path.join(toc_cache_path, recid + '.inc'), 0755)
 
        return page
    
    def display_toc(self, form):
        global toc_cache_path, printable_toc_scripts
        recid = form.getfirst('recid', None)
        self.htmlTitle.append('Display Contents for %s' % recid)
        try:
            path = os.path.join(toc_cache_path, recid.replace('/', '-') + '.inc')
        except:
            return ('<p class="error">You didn\'t specify a record.</p>')
        else:
            try:
                page = read_file(path)
            except:
                # oh dear, not generated yet...
                try: 
                    rec = recordStore.fetch_record(session, recid)
                except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                    try:
                        rec = compStore.fetch_record(session, recid)
                    except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                        self.htmlTitle.append('Error')
                        return ('<p class="error">The record you requested is not available.</p>')
                    
                # TODO: finish this!
            
            return printable_toc_scripts + page

    def display_record(self, form):
        global max_page_size_bytes, cache_path, cache_url, toc_cache_path, toc_cache_url, repository_name, repository_link, repository_logo, display_splash_screen_popup, punctuationRe, wordRe, anchorRe, highlightInLinkRe, overescapedAmpRe
        isComponent = None
        operation = form.get('operation', 'full')
        recid = form.getfirst('recid', None)
        rsid = form.getfirst('rsid', None)
        firstrec = int(form.get('firstrec', 1))
        numreq = int(form.get('numreq', 20))
        highlight = int(form.get('highlight', 1))
        hitposition = int(form.getfirst('hitposition', 0))

        if (recid):
            try: 
                rec = recordStore.fetch_record(session, recid)
            except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                try:
                    rec = compStore.fetch_record(session, recid)
                except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                    self.htmlTitle.append('Error')
                    return (False, '<div id="wrapper"><p class="error">The record you requested is not available.</p></div>')
        else:
            if (rsid):
                if (rsid):
                    try:
                        rs = resultSetStore.fetch_resultSet(session, rsid)
                    except:
                        rsid = cgi_decode(rsid)
                        try:
                            query = CQLParser.parse(cgi_decode(rsid))
                        except:
                            self.logger.log('Unretrievable resultSet %s' % (rsid))
                            if not self.redirected:
                                self.htmlTitle.append('Error')
                            return (False, '<p class="error">Could not retrieve resultSet from resultSetStore. Please re-submit your search</p>')
                        else:
                            self.logger.log('Re-submitting CQL query: %s' % (rsid))
                            rs = db.search(session, query)
                    else:
                        self.logger.log('Retrieved resultSet "%s"' % (rsid))
                        
                    rs.id = rsid
                    
                if not rs:
                    try: 
                        query = CQLParser.parse(rsid)
                        rs = db.search(session, query)
                    except:
                        self.logger.log('Unretrievable resultSet %s' % (rsid))
                        return (False, '<div id="wrapper"><p class="error">Could not retrieve resultSet from resultSetStore. Please re-submit your search</p></div>')
                self.logger.log('Retrieved resultSet "%s"' % (rsid))
                rs.id = rsid
            else:
                qString = form.get('query', form.get('cqlquery', None))
                if not qString:
                    qString = generate_cqlQuery(form)
                    
                try:
                    query = CQLParser.parse(qString);
                except:
                    return (False, '<div id="wrapper"><p class="error">Could not generate CQL query.</p></div>')
                        
                rs = db.search(session, query)
                rs.id = qString
            
            try:
                r = rs[hitposition]
            except IndexError:
                self.logger.log('Index %d not in range %d' % (hitposition, len(rs)))
                self.htmlTitle.append('Error')
                return (False, '<div id="wrapper"><p class="error">Could not retrieve requested record.</p></div>')
            else:
                try:
                    rec = r.fetch_record(session)
                except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                    self.logger.log('*** Unable to retrieve record: %s' % (r))
                    self.htmlTitle.append('Error')
                    return (False, '<div id="wrapper"><p class="error">Could not retrieve requested record.</p></div>')
                else:
                    recid = str(rec.id)

        # Resolve link to parent if a component
        try:
            parentId = rec.process_xpath('/c3component/@parent')[0]
        except IndexError:
            parentLink = ''
        else:
            # OK, must be a component record
            parentId = parentId.split('/')[-1]
            isComponent = True
            parentTitle = self._parentTitle(parentId)
            if parentTitle:
                parentTitle = nonAsciiRe.sub(_asciiFriendly, parentTitle)
                try:
                    parentTitle = parentTitle.encode('utf-8');
                except:
                    parentTitle = '[Could not encode parent title into Unicode]';
            
                parentLink = '<a href="%s?operation=full&amp;recid=%s" title="Link to Complete Collection Description" onclick="SPLASH">%s</a>' % (script, parentId , parentTitle)
            else:
                parentLink = '(unable to locate parent document)'
                
            if (display_splash_screen_popup ):
                parentLink = parentLink.replace('SPLASH', ' onclick="splashScreen()"')
            else:
                parentLink = parentLink.replace('SPLASH', '')
            
        self.htmlTitle.append('Display in %s' % operation.title())

        # get results of most recent search
        self.redirected = True
        try:
            searchResults = self.format_resultSet(rs, firstrec, numreq, highlight)
        except:
            searchResults = ''
        
        paramDict = self.globalReplacements
        paramDict.update({'RECID': recid
                         ,'LINKTOPARENT': parentLink
                         #,'QSTRING': qString
                         ,'%TITLE%': ' :: '.join(self.htmlTitle)
                         ,'%NAVBAR%':' | '.join(self.htmlNav)
                         })
        
        if (operation == 'summary'):
            if (rsid): paramDict['RSID'] = 'rsid=%s&amp;firstrec=%d&amp;numreq=%d&amp;hitposition=%s&amp;highlight=%d' % (cgi_encode(rsid), firstrec, numreq, hitposition, highlight)
            else: paramDict['RSID'] = 'recid=%s' % (recid)
            paramDict['HGHLGHT'] = '<span class="highlight">'
            paramDict['THGLHGH'] = '</span>'
            paramDict['LEFTSIDE'] = searchResults
            try:
                page = self.display_summary(rec, paramDict, r.proxInfo, highlight)
            except:
                page = self.display_summary(rec, paramDict)
        else:
            # full record
            path = os.path.join(cache_path, recid.replace('/', '-') + '-p1.shtml')
            if (isComponent):
                self.logger.log('Full-text requested for component: ' + recid)
            else:
                self.logger.log('Full-text requested for record: ' + recid)
            
            try:
                page = read_file(path)
                self.logger.log('Retrieved from cache')
            except:
                paramDict['TOC_CACHE_URL'] = toc_cache_url
                page = self.display_full(rec, paramDict, isComponent)
            
            if (isComponent) or not (os.path.exists('%s/%s.inc' % (toc_cache_path, recid))):
                page = page.replace('<!--#include virtual="%s/%s.inc"-->' % (toc_cache_url, recid), searchResults)
            else:
                # cannot use Server-Side Includes in script generated pages - insert ToC manually
                try:
                    page = page.replace('<!--#include virtual="%s/%s.inc"-->' % (toc_cache_url, recid), read_file('%s/%s.inc' % (toc_cache_path, recid)))
                except:
                    page = page.replace('<!--#include virtual="%s/%s.inc"-->' % (toc_cache_url, recid), '<span class="error">There was a problem whilst generating the Table of Contents</span>')
        
            
        return (True, page)

    #- end display_record() ----------------------------------------------------


    def email_record(self, form):
        global outgoing_email_username, localhost, outgoing_email_host, outgoing_email_port, cache_path, emailRe
        self.htmlTitle.append('e-mail Record')
        rsid = form.getfirst('rsid', None)
        hitposition = int(form.getfirst('hitposition', 0))
        firstrec = int(form.getfirst('firstrec', 1))
        numreq = int(form.getfirst('numreq', 20))
        address = form.get('address', None)

        if (rsid):
            rsInputs = ['<input type="hidden" name="rsid" value="%s"/>' % (rsid)]
            backToResultsLink = '<a href="%s?operation=search&amp;rsid=%s&amp;firstrec=%d&amp;numreq=%d" title="Back to search results">Back to results</a>' % (script, rsid, firstrec, numreq)
        else:
            qString = form.get('query', form.get('cqlquery', None))
            try:
                qString = qString.replace('"', "'")
            except AttributeError:
                self.htmlTitle.append('Error')
                return '<div id="single">Unable to determine which record to email.</div>'
            
            rsInputs = ['<input type="hidden" name="query" value="%s"/>' % (qString)]
            backToResultsLink = '<a href="%s?operation=search&amp;query=%s&amp;firstrec=%d&amp;numreq=%d" title="Back to search results">Back to results</a>' % (script, cgi_encode(qString), firstrec, numreq)

        rsInputs.extend(['<input type="hidden" name="firstrec" value="%d"/>' % (firstrec)
                         ,'<input type="hidden" name="numreq" value="%d"/>' % (numreq)
                       ])

        self.htmlNav.append(backToResultsLink)
        self.globalReplacements.update({
             '%RSID%': '\n    '.join(rsInputs)
            ,'%HITPOSITION%': str(hitposition)
            })
        if not address:
            self.globalReplacements['%ERROR%'] = '<!-- no errors -->'
            self.htmlTitle.append('Enter Address')
            f = read_file('email.html')
            return f
        
        # should be handled by JavaScript, but just in case...
        elif not emailRe.match(address):
            self.htmlTitle.append('Re-enter Address')
            f = read_file('email.html')
            self.globalReplacements['%ERROR%'] = '<p><span class="error">Your address did not match the expected form: name@company.domain</span></p>'
            return f
        else:
            if (rsid):            
                self.logger.log('Retrieving resultSet "%s"' % (rsid))
                rs = resultSetStore.fetch_resultSet(session, rsid)
                if not rs:
                    self.logger.log('Unretrievable resultSet %s' % (rsid))
                    return 'Could not retrieve resultSet from resultSetStore. Please re-submit your search'
                rs.id = rsid
            else:
                qString = form.get('query', form.get('cqlquery', None))
                try:
                    query = CQLParser.parse(qString);
                except:
                    qString = generate_cqlQuery(form)
                    query = CQLParser.parse(qString);
                self.logger.log('Searching CQL query: %s' % (qString))
                rs = db.search(session, query)
                rsid = rs.id = qString
            
            try:
                r = rs[hitposition]
            except IndexError:
                self.htmlTitle.append('Error')
                return '<p class="error">Could not retrieve requested record</p>'
            
            rec = r.fetch_record(session)
            recid = rec.id
            try:
                parentId = rec.process_xpath('/c3component/@parent')[0]
                # only when integers are used
                parentId = parentId.split('/')[-1]
                # OK, must be a component record
                isComponent = True
                try:
                    parentRec = dcRecordStore.fetch_record(session, parentId.split('/')[-1])
                except:
                    parentRec = recordStore.fetch_record(session, parentId.split('/')[-1])                   
                    try:
                        parentTitle = parentRec.process_xpath('/ead/archdesc/did/unittitle/text()')[0]
                    except IndexError:
                        try:
                            parentTitle = parentRec.process_xpath('/ead/eadheader/filedesc/titlestmt/titleproper/text()')[0]
                        except IndexError:
                            parentTitle = '(untitled)'
                else:
                    parentTitle = parentRec.process_xpath('dc:title/text()', namespaceUriHash)[0]

                parentTitle = nonAsciiRe.sub(_asciiFriendly, parentTitle)
                try:
                    parentTitle = parentTitle.encode('utf-8');
                except:
                    parentTitle = '[Could not encode parent title into Unicode]';
                
            except:
                parentTitle = '';
                isComponent = False
            
            doc = textTxr.process_record(session, rec)
            # cache copy
#            doc.id = recid
#            try: textStore.store_document(session, doc)
#            except: pass;         # cannot cache, oh well...

            docString = unicode(doc.get_raw(), 'utf-8')
            docString = diacriticNormaliser.process_string(session, docString)
            try: docString = docString.encode('utf-8', 'latin-1')
            except:
                try: docString = docString.encode('utf-16')
                except: pass # hope for the best!

            if isComponent:
                msgtxt = '''\
******************************************************************************
In: %s
******************************************************************************

%s
''' % (parentTitle, docString)
            else:
                msgtxt = docString
            try:
                mimemsg = MIMEMultipart.MIMEMultipart()
                mimemsg['Subject'] = 'Requested Finding Aid'
                mimemsg['From'] = '%s@%s' % (outgoing_email_username, localhost)
                mimemsg['To'] = address
            
                # Guarantees the message ends in a newline
                mimemsg.epilogue = '\n'        
                msg = MIMEText.MIMEText(msgtxt)
                mimemsg.attach(msg)
                
                # send message
                s = smtplib.SMTP()
                s.connect(host=outgoing_email_host, port=outgoing_email_port)
                s.sendmail('%s@%s' % (outgoing_email_username, localhost), address, mimemsg.as_string())
                s.quit()
                
                self.logger.log('Record %s emailed to %s' % (recid, address))
                # send success message
                self.htmlTitle.append('Record Sent')
                return '<div id="padder"><div id="rightcol"><p><span class="ok">[OK]</span> - The record with id %s was sent to %s and should arrive shortly. If it does not, please feel free to try again later.</p></div></div><div id="leftcol" class="results">%s</div>' % (recid, address, self.format_resultSet(rs, firstrec, numreq)) 
            except:
                self.logger.log('Failed to send mail')
                self.htmlTitle.append('Error')
                return '<div id="padder"><div id="rightcol"><p class="error">The record with id %s could not be sent to %s. We apologise for the inconvenience and ask that you try again later.</p></div></div><div id="leftcol" class="results">%s</div>' % (recid, address, self.format_resultSet(rs, firstrec, numreq))
                
    #- end email_record() ------------------------------------------------------
    
    
    def similar_search(self, form):
        global exactExtracter
        if not (exactExtracter): exactExtracter = db.get_object(session, 'ExactExtracter') #ensure it's available
        rsid = form.getfirst('rsid', None)
        hitposition = int(form.getfirst('hitposition', 0))
        highlight = form.getfirst('highlight', 0)
        self.htmlTitle.append('Similar Search')
        self.logger.log('Similar Search')
        if (rsid):
            try:
                rs = resultSetStore.fetch_resultSet(session, rsid)
                rs.id = rsid
            except:
                try: query = CQLParser.parse(rsid)
                except:
                    self.logger.log('Unretrievable resultSet %s' % (rsid))
                    return 'Could not retrieve resultSet from resultSetStore. Please re-submit your search'
            
                try: rs = db.search(session, query)
                except: 
                    raise
                rs.id = rsid
        else:
            try:
                qString = generate_cqlQuery(form)
            except: 
                self.htmlTitle.append('Error')
                return '<p class="error">No rsid provided, could not generate CQL query from form.</p>'

            try: 
                query = CQLParser.parse(qString)
            except: 
                self.htmlTitle.append('Error')
                return '<p class="error">No rsid provided, unparsable CQL query submitted</p>'

            rs = db.search(session, query)
            if not (rs):
                self.htmlTitle.append('Error')
                return '<p class="error">Could not retrieve requested record, query returns no hits</p>'
        
        r = rs[hitposition]
        try:
            recid = str(r.docid)
        except AttributeError:
            # API change
            recid = str(r.id)
            
        paramDict = {
            'RECID': recid, 
            '%REP_NAME%': repository_name, 
            '%REP_LINK%': repository_link,
            '%REP_LOGO%': repository_logo, 
            '%TITLE%': ' :: '.join(self.htmlTitle), 
            '%NAVBAR%': ' | '.join(self.htmlNav),
            'SCRIPT':script
        }

        rec = r.fetch_record(session)
        controlaccess = {}
        for cah in ['subject', 'persname', 'famname', 'geogname']:
            controlaccess[cah] = rec.process_xpath('controlaccess[1]/%s' % (cah)) # we only want top level stuff to feed into similar search
        
        cqlClauses = []
        for cah, cal in controlaccess.iteritems():
            for casax in cal:
                key = exactExtracter.process_eventList(session, casax).keys()[0]
                cqlClauses.append('c3.ead-idx-%s exact "%s"' % (cah, key))
        
        if len(cqlClauses):
            if highlight: cql = ' or/proxinfo '.join(cqlClauses)
            else: cql = ' or '.join(cqlClauses)
        else:
            # hrm there's no control access - try something a bit more vague...
            # take words from important fields and feed back into quick search
            # TODO: this is too slow - optimise similar search query
            #cql = 'dc.description any/rel.algorithm=tfidf/rel.combine=sum "%s"' % (' '.join(allWords))
            #cql = 'dc.description any/relevant "%s"' % (' '.join(allWords))
            fields = [('dc.title', 'did[1]/unittitle'),
                      #('dc.description', 'scopecontent[1]'),
                      ('dc.creator', 'did[1]/origination')]

            for (idx, xp) in fields:
                terms = []
                data = rec.process_xpath(xp) # we only want top level stuff to feed into similar search
                for d in data:
                    key = exactExtracter.process_eventList(session, d).keys()[0]
                    if (type(key) == unicode):
                        key = key.encode('utf-8')
                    terms.append(key)
                
                if len(terms):
                    cqlClauses.append('%s any/relevant/proxinfo "%s"' % (idx, ' '.join(terms)))
            
            if highlight: cql = ' or/relevant/proxinfo '.join(cqlClauses)
            else: cql = ' or/relevant '.join(cqlClauses)
        
        form = {'query': cql, 'firstrec': 1, 'numreq': 20, 'highlight': highlight}
        try:
            #return self.search(form, 100)            # limit similar search results to 100 - noone will look through more than that anyway!
            return self.search(form)
        except ZeroDivisionError:
            self.htmlTitle.append('Error')
            self.logger.log('*** unable to locate similar records')
            return '<p>Unable to locate similar records.</p>'

    #- end similar_search() ----------------------------------------------------
        
        
    def handle(self, req):
        # get contents of submitted form
        form = FieldStorage(req)
        content = None
        operation = form.get('operation', None)
        try:
            if (form.has_key('operation')):
                operation = form.get('operation', None)
                if (operation == 'search'):
                    self.htmlTitle.append('Search')
                    content = '<div id="wrapper">%s</div>' % (self.search(form))
                elif (operation == 'browse'):
                    content = '<div id="wrapper">%s</div>' % (self.browse(form))
                elif (operation == 'summary') or (operation == 'full'):
                    # this function sometimes returns complete HTML pages, check and if so just send it back to request
                    send_direct, content = self.display_record(form)
                    if send_direct:
                        self.send_html(content, req)
                        return 1
                elif (operation == 'resolve'):
                    content = '<div id="wrapper">%s</div>' % (self.subject_resolve(form))
                elif (operation == 'email'):
                    self.redirected = True
                    content = self.email_record(form)
                elif (operation == 'similar'):
                    content = '<div id="wrapper"><div id="leftcol" class="results">%s</div></div>' % (self.similar_search(form))
                elif (operation == 'toc'):
                    content = '<div id="wrapper"><div id="single">%s</div></div>' % (self.display_toc(form))
                else:
                    #invalid operation selected
                    self.htmlTitle.append('Error')
                    content = '<div id="wrapper"><p class="error">An invalid operation was attempted. Valid operations are:<br/>search, browse, resolve, summary, full, toc, email</p></div>'
        except Exception:
            self.htmlTitle.append('Error')
            cla, exc, trbk = sys.exc_info()
            excName = cla.__name__
            try:
                excArgs = exc.__dict__["args"]
            except KeyError:
                excArgs = str(exc)
                
            self.logger.log('*** %s: %s' % (excName, excArgs))
            excTb = traceback.format_tb(trbk, 100)
            content = '''\
            <div id="wrapper"><p class="error">An error occured while processing your request.<br/>
            The message returned was as follows:</p>
            <code>%s: %s</code>
            <p><strong>Please try again, or contact the system administrator if this problem persists.</strong></p>
            <p>Debugging Traceback: <a class="jscall" onclick="toggleShow(this, 'traceback');">[ show ]</a></p>
            <div id="traceback">%s</div>
            </div>
            ''' % (excName, excArgs, '<br/>\n'.join(excTb))
            
        
        if not content:
            # return the home/quick search page
            self.htmlTitle.append('Search')
            content = read_file('index.html')

        tmpl = read_file(templatePath)                                        # read the template in
        page = tmpl.replace("%CONTENT%", content)
        self.globalReplacements.update({
            "%TITLE%": ' :: '.join(self.htmlTitle)
           ,"%NAVBAR%": ' | '.join(self.htmlNav),
           })

        page = multiReplace(page, self.globalReplacements)
        self.send_html(page, req)                                            # send the page

    #- end handle() ------------------------------------------------------------

#- end class EadSearchHandler --------------------------------------------------

#- Some stuff to do on initialisation
rebuild = True
serv = None
session = None
db = None
recordStore = None
dcStore = None
compStore = None
clusDb = None
clusStore = None
textStore = None
resultSetStore = None
summaryTxr = None
fullTxr = None
fullSplitTxr = None
textTxr = None
exactExtracter = None
diacriticNormaliser = None

# regexs
#punctuationRe = re.compile('([@+=;!?:*"{}()\[\]\~/\\|\#\&\^]|[-.,\'][^\w]|[^\w][-.,\'])')
# modified slightly from re used to extract keywords
# spaces need to be maintained (not consumed) to maintain accuracy of offsets
#punctuationRe = re.compile('([~`@+=;!?:*"{}()\[\]\~/\\|\#\&\^]|[-.,]([^\w]|$)|[^\w][-.\',])')
#punctuationRe = re.compile('([@+=;!?:*"{}()\[\]\~/\\|\#\&\^]|[-.,\'](?=\s)|(?<=\s)[-.,\'])')
#punctuationRe = re.compile('([@+=;!?:*"{}()\[\]\~/\\|\#\&\^](?!\.)|[-.,\'](?=\s)|(?<=\s)[-.,\'])')
punctuationRe = re.compile('([@+=;!?:*"{}()\[\]\~/\\|\#\&\^]|[-.,\'](?=\s+)|(?<=\s)[-.,\'])')   # this busts when there are accented chars
wordRe = re.compile('\s*\S+')
#emailRe = re.compile('^[^@ ]+(\.[^@ ])*@[^@ ]+\.[^@ ]+(\.[^@ ])*$')                    # e.g. foo@bar.com
emailRe = re.compile('^[a-zA-Z][^@ .]*(\.[^@ .]+)*@[^@ .]+\.[^@ .]+(\.[^@ .]+)*$')    # e.g. foo@bar.com
anchorRe = re.compile('<a .*?name="(.*?)".*?>')
overescapedAmpRe = re.compile('&amp;([^\s]*?);')
def _unescapeCharent(mo): return '&%s;' % mo.group(1)
nonAsciiRe = re.compile('([\x7b-\xff])')
def _asciiFriendly(mo): return "&#%s;" % ord(mo.group(1))

logfilepath = searchlogfilepath

# data argument provided for when request does clean-up - always None
def build_architecture(data=None):
    global session, serv, db, clusDb, recordStore, dcRecordStore, compStore, textStore, resultSetStore, summaryTxr, fullTxr, fullSplitTxr, textTxr, rebuild, exactExtracter, diacriticNormaliser
    # Discover objects...
    session = Session()
    session.database = 'db_ead'
    session.environment = 'apache'
    session.user = None
    serv = SimpleServer(session, '/home/cheshire/cheshire3/cheshire3/configs/serverConfig.xml')
    db = serv.get_object(session, 'db_ead')
    clusDb = serv.get_object(session, 'db_ead_cluster')
    recordStore = db.get_object(session, 'recordStore')
    dcRecordStore = db.get_object(session, 'eadDcStore')
    compStore = db.get_object(session, 'componentStore')
    #textStore = db.get_object(session, 'textDocStore')
    resultSetStore = db.get_object(session, 'eadResultSetStore')
    # transformers
    summaryTxr = db.get_object(session, 'htmlSummaryTxr')
    fullTxr = db.get_object(session, 'htmlFullTxr')
    fullSplitTxr = db.get_object(session, 'htmlFullSplitTxr')
    textTxr = db.get_object(session, 'textTxr')
    if not (exactExtracter): exactExtracter = db.get_object(session, 'ExactExtracter')
    if not (diacriticNormaliser): diacriticNormaliser = db.get_object(session, 'DiacriticNormaliser')
    rebuild = False


def handler(req):
    global rebuild, logfilepath, resultSetStore, db, cheshirePath
    req.register_cleanup(build_architecture)
    try:
        try:
            fp = recordStore.get_path(session, 'databasePath')    # attempt to find filepath for recordStore
            assert (rebuild)
            assert (os.path.exists(fp) and time.time() - os.stat(fp).st_mtime > 60*60)
        except:
            # architecture not built
            build_architecture()
        
        remote_host = req.get_remote_host(apache.REMOTE_NOLOOKUP)                   # get the remote host's IP for logging
        os.chdir(os.path.join(cheshirePath, 'cheshire3','www','ead','html'))        # cd to where html fragments are
        lgr = FileLogger(logfilepath, remote_host)                                  # initialise logger object
        eadSearchHandler = EadSearchHandler(lgr)                                    # initialise handler - with logger for this request
        try:
            eadSearchHandler.handle(req)                                            # handle request
        finally:
            # clean-up
            try: lgr.flush()                                                        # flush all logged strings to disk
            except: pass
            del lgr, eadSearchHandler                                               # delete handler to ensure no state info is retained
            
    except:
        req.content_type = "text/html"
        cgitb.Hook(file = req).handle()                                            # give error info
    else:
        return apache.OK
    
#- end handler()

