from mod_python import apache, Cookie
from mod_python.util import FieldStorage
import sys, os, cgitb, time, re

from server import SimpleServer
from PyZ3950 import CQLParser
from baseObjects import Session
from utils import flattenTexts
from www_utils import *
#from wwwSearch import *
from localConfig import *

import urllib

class istcHandler:
    templatePath = "/home/cheshire/cheshire3/cheshire3/www/istc/html/template.ssi"

    def __init__(self, lgr):
        self.logger = lgr



    def send_html(self, text, req, code=200):
        req.content_type = 'text/html; charset=utf-8'
        req.content_length = len(text)
        req.send_http_header()
        req.write(text)



    def generate_query(self, form):
	self.logger.log('generating query')
        phraseRe = re.compile('".+?"')
        qClauses = []
        bools = []
        i = 1
        while (form.has_key('fieldcont%d' % i)):
            bools.append(form.getfirst('fieldbool%d' % (i-1), 'and/relevant/proxinfo'))
            i += 1
        i = 1

        while (form.has_key('fieldcont%d' % i)):
            cont = urllib.unquote(form.getfirst('fieldcont%d' % i)).decode('utf-8')
            idx = urllib.unquote(form.getfirst('fieldidx%d' % i, 'cql.anywhere')).decode('utf-8')
            rel = urllib.unquote(form.getfirst('fieldrel%d'  % i, 'all/relevant/proxinfo')).decode('utf-8')
            #if 'not' in bools:
            #    rel = rel.replace('/relevant', '')

            subClauses = []
            if (rel[:3] == 'all'): subBool = ' and/relevant/proxinfo '
            else: subBool = ' or/relevant/proxinfo '

            # in case they're trying to do phrase searching
            if (rel.find('exact') != -1 or rel.find('=') != -1 or rel.find('/string') != -1):
                # don't allow phrase searching for exact or /string searches
                cont = cont.replace('"', '\\"')
            else:
                phrases = phraseRe.findall(cont)
                for ph in phrases:
                    subClauses.append('(%s =/relevant/proxinfo %s)' % (idx, ph))

                cont = phraseRe.sub('', cont)

            if (idx and rel and cont):
                subClauses.append(u'%s %s "%s"' % (idx, rel, cont.strip()))

            if (len(subClauses)):
                qClauses.append('(%s)' % (subBool.join(subClauses)))

            # if there's another clause and a corresponding boolean
            try: qClauses.append(bools[i])
            except: break

            i += 1
            sys.stderr.write(repr(cont))
            sys.stderr.flush()

        qString = ' '.join(qClauses)
	
        return qString



    def _cleverTitleCase(self, txt):
        global stopwords
        words = txt.split()
        for x in range(len(words)):
            if (x == 0 and not words[x][0].isdigit()) or (words[x][0].isalpha()) and (words[x]):
                words[x] = words[x].title()
        return ' '.join(words)
    


    def handle_istc(self, session, cql):
        self.logger.log('entering handle_istc')
        html = "<strong>Your search was for: " + cql.replace("(c3.idx-", "").replace("/relevant/proxinfo", "").replace(")","").replace("-"," ") + "</strong><br/><br/>"
        
                        
        session.database = db.id

        try:
            tree = CQLParser.parse(cql.encode('utf-8'))
        except:
            return ("Search Error", '<p>Could not parse your query. <a href="http://istc.cheshire3.org">Please try again</a>. %s' % cql)
        self.logger.log('about to search')    
        try:
            rs = db.search(session, tree)     
        except:
            #raise
            return ("Search Error", '<p>Could not complete your query. <a href="http://istc.cheshire3.org">Please try again</a>. %s' % cql)
        self.logger.log('done searching')
        hits = len(rs)
        if hits:
            html = html + "<h1>%d Results</h1><p>Sort by <a href="">Author </a>, <a href="">Title </a> or <a href="">Place of Publication</a><br/><br/>" % (hits)
            idx = "idx-title"
            #try:
            #   sortList = indexStore.fetch_sortValue(session, idx, r)
            #   html = "%s SortList: %s" % (html, sortList)
            #except:
            #    raise
#            htmlrows = []
            for x,r in enumerate(rs):
                #self.logger.log('formatting result %d' % x)
                rec = recStore.fetch_record(session, r.id)
                html = "%s %d. " %  (html, x+1)
                try:
                    elms = rec.process_xpath(session, '//fld245/a')
                    title = flattenTexts(elms[0])

                except:
                    try:
                        elms = rec.process_xpath(session, '//fld130/a')
                        title = flattenTexts(elms[0])
                    except:
                        title = ""

                try:
                    elms = rec.process_xpath(session, '//fld001')
                    identifier = flattenTexts(elms[0])
                except:
                    identifier =""
                try:
                    ####need to get author from the other database####
                    elms = rec.process_xpath(session, '//fld100/a')
                    author = flattenTexts(elms[0])
                except:
                    try:
                        elms = rec.process_xpath(session, '//fld100')
                        author = flattenTexts(elms[0])
                    except:
                        author = ""
                # get from other database

                try:
                    elms = rec.process_xpath(session, '//fld260/b')
                    imprint = "- %s" % flattenTexts(elms[0])

                except:
                    imprint = ""
                try:
                    elms = rec.process_xpath(session, '//fld260/c')
                    date = flattenTexts(elms[0])
                except:
                    date= ""


                html= html + '<a href="/istc/record.html?q=%s&r=0">%s</a><br/>&nbsp;&nbsp;&nbsp;%s %s %s <br/><br/>' % ( identifier.strip(), title, author, imprint, date)            #rec.get_xml(session).replace("</","").replace("<","").replace(">","")
               
                    
           # html = html + ('</p>')
            
        else:
            html = html + "No matches  %s." % cql.decode('utf-8')
                
        return ('Search Results', html)



    def handle_record(self, session, form):
        a = re.compile('<(.*?)>(.*?)</.*?>')
        b = re.compile('<(.*?)/>')
        links = re.compile('(http:.*?\s)')
        ilc = ""
        identifier = form['q'].value
        try:
            refValue = int(form['r'].value)
        except:
            refValue = 0
            
        langcodes = { 'eng':'English', 'heb': 'Hebrew', 'bre':'Breton', 'cat':'Catalan','chu':'"Church Slavonic"', 'cze': 'Czech', 'dan':'Danish', 'dut':'Dutch', 'fri':'Frisian', 'frm':'French','ger':'German','grc':'Greek','ita':'Italian', 'lat': 'Latin', 'por':'Portuguese', 'sar': 'Sardinian', 'spa': 'Spanish', 'swe':'Swedish' }

        locationCodeList = ["//fld951", "//fld995", "//fld957", "//fld997" , "//fld954" , "//fld955" , "//fld996" , "//fld952" , "//fld958" , "//fld953" , "//fld994"]
        locationCodeDic = {"//fld951": "British Isles", "//fld952": "U.S.A", "//fld953" : "Other", "//fld954": "Italy", "//fld957": "France", "//fld955": "Spain/Portugal","//fld958": "Other Europe", "//fld994":"Doubtful", "//fld995": "Belgium", "//fld996": "Netherlands", "//fld997": "Germany"}
        
        session.database = 'db_istc'
        q = CQLParser.parse('c3.idx-ISTC-number exact "%s"' % (identifier))
        rs = db.search(session, q)
        html = ""
        if len(rs):

            rec = rs[0].fetch_record(session)
            # Print out of record - get appropriate elements #
            try:
                elms = rec.process_xpath(session, '//fld008')
                field8 = flattenTexts(elms[0])
            except:
                field8 = "" 
            try:
                elms = rec.process_xpath(session, '//fld001')
                istcTitle =("<strong>ISTC Number:</strong>")
                identification ="<tr><td>%s</td><td> %s </td></tr>" %  (istcTitle, flattenTexts(elms[0]))
            except:
                identification =""

            try:
                    elms = rec.process_xpath(session, '//fld100/a')
                    authorBrowse = flattenTexts(elms[0])
                    author = "<tr><td><strong>Author: </strong></td><td> %s </td></tr>" % authorBrowse
                    
            except:
                try:
                    elms = rec.process_xpath(session, '//fld100')
                    authorBrowse = flattenTexts(elms[0])
                    author = "<tr><td><strong>Author:</strong></td><td> %s</td></tr>" % authorBrowse
                except:
                    authorBrowse = ""
                    author = ""

            otherAuthorList = []
            try:
                elms = rec.process_xpath(session, '//fld700')
                otherAuthor = "<tr><td><strong>Other Author:</strong></td><td> %s</td></tr>" % flattenTexts(elms[0])
                for elm in elms[1:len(elms)]:
                    try:
                        ref = "<tr><td></td><td> %s </td></tr>" % flattenTexts(elm)
                        otherAuthorList.append(ref)
                    except:
                        pass
                    
                otherAuthor = "(%s, %s)" % (otherAuthor, "".join(otherAuthorList))
            except:
                otherAuthor = ""
                
            author = "%s %s" % (author, otherAuthor)
                                            
                 
            try:
                elms = rec.process_xpath(session, '//fld245/a')
                titleBrowse = flattenTexts(elms[0])
                title = "<tr><td><strong>Title:</strong></td><td> %s <td></tr>" %  titleBrowse
                    
            except:
                try:
                    elms = rec.process_xpath(session, '//fld130/a')
                    titleBrowse =  flattenTexts(elms[0])
                    title = "<tr><td><strong>Title:</strong></td><td> %s </td></tr>" % titleBrowse
                except:
                    title = ""
            imprintList = []
            try:
                elms = rec.process_xpath(session, '//fld260')
                imprintList.append("<tr><td><strong>Imprint:</strong></td><td> %s <td></tr>" %  flattenTexts(elms[0]))
                for elm in elms[1:len(elms)]:
                    try:
                        ref = "<tr><td></td><td> %s </td></tr>" % flattenTexts(elm)
                        imprintList.append(ref)
                    except:
                        pass
                imprint = "".join(imprintList)
                    
            except:
                imprint = ""
           
            try:
                processedFormat = ""
                elms = rec.process_xpath(session, '//fld300')
                rawFormat =  flattenTexts(elms[0]).strip()
           
                processedFormat = rawFormat.replace("bdsde","Broadside").replace("Bdsde","Broadside").replace("4~~","4<sup>to</sup>").replace("8~~","8<sup>vo</sup>").replace("f~~", "f<sup>o</sup>").replace("~~", "<sup>mo</sup>")
                #.replace("~~", "<sup>vo</sup>")
                
                
                format = "<tr><td><strong>Format:</strong></td><td> %s <td></tr>" %  processedFormat
                #format = "%s %s" % (format, rec.process_xpath(session, '//fld300/text()')[0])
                
            except:
                format = ""
                
            try:
                language = "<tr><td><strong>Language:</strong></td><td> %s <td></tr>" %  langcodes[field8[35:38]]
            except:
                try:
                    language = "<tr><td><strong>Language:</strong></td><td> %s <td></tr>" %  field8[35:38]
                except:
                    language = ""
                    
            referenceList =[]
            ref = ""
            refAction = "expand"
            refNum = 1
            try:
                elms = rec.process_xpath(session, '//fld510')
            
                for elm in elms:
                    try:
                        ref = flattenTexts(elm)
                    except:
                        ref = ""

                    try:
                        if ref.find("ILC") != -1:
                            ilcList = (ref.strip()).split(" ")
                            while len(ilcList[1]) < 4:
                                ilcList[1] = "%s%s" % ("0", ilcList[1])
                            ilc = " ".join(ilcList)
                    except:
                        pass        
            
                    if refValue != 0:
                        try:
                            session.database = db3.id
                            refSearch = ref.strip().split(" ")

                            q3 = CQLParser.parse('c3.idx-refs-code exact "%s"' % (refSearch[0].strip()))
                            rs3 = db3.search(session, q3)
                            if len(rs3):
                                recRefs = rs3[0].fetch_record(session)
                                ref = "%s" % recRefs.process_xpath(session, '//full/text()')[0]
                                ref = "<br/>%s - %s" % (" ".join(refSearch), ref)
                                refAction = "condense"
                                refNum = 0
                        except:
                            pass
                                            
                    referenceList.append(ref.strip())

                references = "<tr><td><strong>References:</strong></td><td>%s <br/><a href=\"/istc/record.html?q=%s&r=%d\">Click here to %s the references</a></td></tr>" % ("; ".join(referenceList), identifier, refNum, refAction) 
            except:
                references = ""
                
            reproductionsList = []
            try:    
                elms = rec.process_xpath(session, '//fld530')
                                
                for elm in elms:
                    try:
                        ref = flattenTexts(elm)
                        matchLinks = links.findall(ref)
                        for item in matchLinks:
                           ref = ref.replace(item, "<br/><a target=\"_new\" href=\"%s\">Click here to link visit the website</a>" % item )
                        reproductionsList.append(ref.strip())
                    except:
                        pass
                if reproductionsList != []:
                    reproductions = "<tr><td><strong>Reproductions:</strong></td><td>%s %s" % (("</td></tr><tr><td></td><td> ".join(reproductionsList)), "</td></tr>")
                else:
                    reproductions = ""
            except:
                reproductions = ""
            
                
            noteList =[]
            try:
                elms = rec.process_xpath(session, '//fld500')
                for elm in elms:
                    try:
                        ref = flattenTexts(elm)
                        if ref.find("Reproductions of the watermarks found in the paper used in this edition are provided by the Koninklijke Bibliotheek, National Library of the Netherlands") != -1 and ilc !="":
                            ref = " %s <br/><a target=\"_new\" href=\"http://watermark.kb.nl/findWM.asp?biblio=%s&max=50&boolean=AND&search2=Search&exact=TRUE\"> Click here to visit the website.</a>" % (ref, ilc)
                            # 
                        noteList.append(ref.strip())
                    except:
                        pass
                elms = rec.process_xpath(session, '//fld505')
                for elm in elms:
                    try:
                        ref = flattenTexts(elm)
                        noteList.append(ref.strip())
                    except:
                        pass
                if noteList != []:
                    notes = "<tr><td><strong>Notes:</strong></td><td>%s %s" % (("</td></tr><tr><td></td><td> ".join(noteList)), "</td></tr>")
                else:
                    notes = ""
            except:
                notes = ""
            shelfmarkList = []
            try:    
                elms = rec.process_xpath(session, '//fld852')
                                
                for elm in elms:
                    try:
                        ref = flattenTexts(elm)

                        shelfmarkList.append(ref.strip())
                    except:
                        pass
                if shelfmarkList != []:
                    shelfmark = "<tr><td><strong>British Library Shelfmark:</strong></td><td>%s %s" % (("</td></tr><tr><td></td><td> ".join(shelfmarkList)), "</td></tr>")
                else:
                    shelfmark = ""
            except:
                shelfmark = ""
            locationList = []

            ### locations ####
            addLocationList = []
            for item in locationCodeList:
               
                try:    
                    elms = rec.process_xpath(session, item)
                   
                    if item.strip() != "//fld952":
                        ref = "<tr><td align=\"right\">%s:</td><td> %s" % (locationCodeDic[item], flattenTexts(elms[0]).strip())
                        
                    else:
                        americanRef = flattenTexts(elms[0])
                        session.database = db2.id
                        q2 = CQLParser.parse('c3.idx-usa-code exact "%s"' % (americanRef.strip()))
                        rs2 = db2.search(session, q2)
                        if len(rs2):
                            recUsa = rs2[0].fetch_record(session)    
                            try:
                                ref = "<tr><td align=\"right\">%s:</td><td> %s" % (locationCodeDic[item], recUsa.process_xpath(session, '//full/text()')[0])
                            except:
                                ref = "<tr><td align=\"right\">%s:</td><td> %s" % (locationCodeDic[item], flattenTexts(elms[0]).strip())
                                
                    addLocationList.append(ref)
                    
                    for elm in elms[1:len(elms)]:
                        try:
                            if item.strip() == "//fld952":    
                                americanRef = flattenTexts(elm)
                                session.database = db2.id
                                q2 = CQLParser.parse('c3.idx-usa-code exact "%s"' % (americanRef.strip()))
                                rs2 = db2.search(session, q2)
                                recUsa = rs2[0].fetch_record(session)
                                ref = "; %s" % recUsa.process_xpath(session, '//full/text()')[0]
                               
                            else:
                                ref = "; %s" % (flattenTexts(elm)).strip()
                            addLocationList.append(ref)
                        except:
                            pass
                   
                except:
                    pass
            locationList.append("".join(addLocationList))

            #### Locations join #####
            
            if locationList != [] and locationList != [''] :
                
                locations = "<tr><td><strong>Locations:</strong></td><td>%s" % ("</td></tr>".join(locationList))
            else:
                locations = ""

            # stuff for the twin display
            
            html = "%s <table cellpadding = \"5\"> %s %s %s %s %s %s %s %s %s %s %s </table><br/><hr/>" % (html, author, title, imprint, format, language, identification, references, reproductions, notes, shelfmark, locations)
            if authorBrowse != "":
                try:
                    authorExtra = "<tr><td align=\"right\" valign=\"middle\" class=\"text\"><strong>Browse Author</strong><img src=\"images/int_link.gif\" alt=\"\" width=\"27\" height=\"21\" border=\"0\" align=\"middle\"/></td></tr><tr class=\"menusubheading\"><td align=\"right\"><a href=\"scan.html?fieldidx1=c3.idx-author&fieldrel1=exact&fieldcont1=%s\">%s</a></td></tr>" % (authorBrowse.strip(), authorBrowse.strip())
                except:
                    authorExtra = ""
            else:
                authorExtra = ""

            if titleBrowse != "":
                try:
                    titleExtra = "<tr><td align=\"right\" valign=\"middle\" class=\"text\"><strong>Browse Title</strong><img src=\"images/int_link.gif\" alt=\"\" width=\"27\" height=\"21\" border=\"0\" align=\"middle\"/></td></tr><tr class=\"menusubheading\"><td align=\"right\"><a href=\"scan.html?fieldidx1=c3.idx-title&fieldrel1=exact&fieldcont1=%s\">%s</a></td></tr>" % (titleBrowse.strip(), titleBrowse.strip())
                except:
                    titleExtra = ""
            else:
                titleExtra = ""
            try:
                elm = flattenTexts(rec.process_xpath(session, '//fld260/b')[0]).strip()
                printerExtra = "<tr><td align=\"right\" valign=\"middle\" class=\"text\"><strong>Browse Printer</strong><img src=\"images/int_link.gif\" alt=\"\" width=\"27\" height=\"21\" border=\"0\" align=\"middle\"/></td></tr><tr class=\"menusubheading\"><td align=\"right\"><a href=\"scan.html?fieldidx1=c3.idx-printer&fieldrel1=exact&fieldcont1=%s\">%s</a></td></tr>" % (elm, elm)
            except:
                printerExtra=""
            try:
                elm = flattenTexts(rec.process_xpath(session, '//fld260/a')[0]).strip()
                printerLocationExtra = "<tr><td align=\"right\" valign=\"middle\" class=\"text\"><strong>Browse Printer Location</strong><img src=\"images/int_link.gif\" alt=\"\" width=\"27\" height=\"21\" border=\"0\" align=\"middle\"/></td></tr><tr class=\"menusubheading\"><td align=\"right\"><a href=\"scan.html?fieldidx1=c3.idx-location&fieldrel1=exact&fieldcont1=%s\">%s</a></td></tr>" % (elm, elm)
            except:
                printerLocationExtra=""

            other = "<tr><td valign=\"middle\" class=\"text\"><strong>&nbsp;&nbsp;For this record</strong></td></tr><tr><td align=\"right\" valign=\"middle\"><a href=\"search.html\">Email<img src=\"images/arrow_next.gif\" alt=\"\" width=\"27\" height=\"19\" border=\"0\" align=\"middle\"></a><br></td></tr><tr><td align=\"right\" valign=\"middle\"><a href=\"print.html\">Print<img src=\"images/link_print.gif\" alt=\"Print\" width=\"27\" height=\"19\" border=\"0\" align=\"middle\"><br></a></td></tr><td align=\"right\" valign=\"middle\"><hr/><tr></tr><tr class=\"menuheading\"><td align=\"right\" valign=\"middle\" ><a href=\"editRecord.html\">Edit This Record<br/>(administrators only)</a></td></tr>"

            extra = "%s %s %s %s <tr><td align=\"right\" valign=\"middle\"><hr align=\"right\" size=\"1\" noshade></td></tr> %s" % (authorExtra, titleExtra, printerExtra, printerLocationExtra, other)
##             #try:
##             #    identifier = rec.process_xpath(session, '/bibrecord/identifier/text()')[0]
##             #except:
##             #    identifier =""
                
##             try:
##                 ####Need to get from other database
##                 author = rec.process_xpath(session, '//author-used-form[@origin="#48 "]/@subjId')[0]
##                 #author = "%s <br/>" %  flattenTexts(elms[0])
##             except:
##                 try:
##                     author = rec.process_xpath(session, '//author-name-personal/@subjId')[0]
##                 except:
##                     author = ""
##             # get from other database
##             session.database = db2.id
##             q2 = CQLParser.parse('c3.idx-classification-identifier exact "%s"' % (author))
##             try:
##                 rs2 = db2.search(session, q2)
##                 if len(rs2):
##                     recClassification = rs2[0].fetch_record(session)
##                     standardAuthor = recClassification.process_xpath(session, '//term[@type="descriptor"]/text()')[0]
##                     author = "Author: %s <br/>" % standardAuthor
##                     akaList = []
##                     try:
##                         aka = recClassification.process_xpath(session, '//term[@type="use"]/text()')
##                         for item in aka:
##                             akaList.append(item)
##                         akaFinished = " or ".join(akaList)
##                         if akaFinished != "":
##                             author = "%s Author also referred to as %s<br/>" % (author, akaFinished)
##                     except:
##                         pass
##             except:
##                 pass
##             try:
##                 elms = rec.process_xpath(session, '//publisher[@origin="#54 "]')
##                 imprint = "Publisher: %s <br/>" %  flattenTexts(elms[0])
##             except:
##                 imprint = ""

##             try:
##                 date = "Date: %s <br/>" %  rec.process_xpath(session, '//dc:date/text()', {'dc' : 'http://purl.org/dc/elements/1.1/'})[0]          
##             except:
##                 date= ""

##             try:
##                 wbbb = rec.process_xpath(session, '//wbbb/text()')[0]
##             except:
##                 wbbb= ""
##             try:
##                 leif = rec.process_xpath(session, '//leif/text()')[0]
##             except:
##                 leif= ""
##             try:
##                 bbb = rec.process_xpath(session, '//bbb/text()')[0]
##             except:
##                 bbb= ""
##             try:
##                 pulsiano = rec.process_xpath(session, '//pulsiano/text()')[0]
##             except:
##                 pulsiano= ""
##             try:
##                 isbn = rec.process_xpath(session, '//isbn/text()')[0]
##             except:
##                 isbn = ""
##             try:
##                 issn = rec.process_xpath(session, '//issn/text()')[0]
##             except:
##                 issn = ""

##             identification = "Identification: %s %s %s %s %s %s<br/>" % (wbbb, leif, bbb, pulsiano, isbn, issn)
                
##             try:
##                 format = "Format %s <br/>" %  flattenTexts(rec.process_xpath(session, '//format'))[0]
##                 #format = flatteTexts(elms[0])
##             except:
##                 format = ""

##             try:
##                 publisher = rec.process_xpath(session, '//publisher/text()')
##                 publish = "<br/>".join(publisher)
##             except:
##                 publish = ""
##                 ##add in printer
##             try:
##                 description = "Description: %s <br/>" % rec.process_xpath(session, '//work-included/text()')[0]
##                 #desc = "<br/>".join(description)
##             except:
##                 description = ""

##             try:
##                 edition = "Edition %s <br/>" % rec.process_xpath(session, '//edition-statement/text()')[0]
               
##             except:
##                 edition = ""
##             try:
##                 note = "Note: %s <br/>" % rec.process_xpath(session, '//note/text()')[0]
                
##             except:
##                 note = ""
##             try:
##                 notevolumes = "Note Volumes: %s <br/>" % rec.process_xpath(session, '//note-volumes/text()')[0]
                
##             except:
##                 notevolumes= ""
##             try:
##                 titleseries = "Title Series: %s <br/>" % rec.process_xpath(session, '//title-series/text()')[0]
                
##             except:
##                 titleseries = ""

##             try:
##                 issuedin = "Issued in:%s <br/>" % rec.process_xpath(session, '//issued-in/text()')[0]
                
##             except:
##                 issuedin = ""
##             try:
##                 issuedinauthor = "Issued in Author: %s <br/>" % rec.process_xpath(session, '//issued-in-author/text()')[0]
                
##             except:
##                 issuedinauthor = ""
##             try:
##                 issuedinedition = "Issued in Edition: %s <br/>" % rec.process_xpath(session, '//issued-in-edition/text()')[0]
                
##             except:
##                 issuedinedition = ""
##             try:
##                 issuedineditionstatement = "Issues in Edition Statement: %s <br/>" % rec.process_xpath(session, '//issued-in-edition-statement/text()')[0]
                
##             except:
##                 issuedineditionstatement = ""
##             try:
##                 issuedinpublisher = "Issued in Publisher: %s <br/>" % rec.process_xpath(session, '//issued-in-publisher/text()')[0]
                
##             except:
##                 issuedinpublisher = ""

            
##             try:
##                 subjects = rec.process_xpath(session, '//dc:subject//@subjId', {'dc' : 'http://purl.org/dc/elements/1.1/'})
##                 session.database = db2.id
##                 subjectList = []
##                 for item in subjects:
##                     #subjectList.append(item)
##                     #search other database
##                     q2 = CQLParser.parse('c3.idx-classification-identifier exact "%s"' % (item))
                    
##                     try:
##                         rs3 = db2.search(session, q2)
##                         if len(rs3):
##                             recClassification = rs3[0].fetch_record(session)
##                             manySubjectList = []
##                             manySubject = recClassification.process_xpath(session, '//term[@type="descriptor"]')
##                             for el in manySubject:
##                                 if el.text:
##                                     try:
##                                         lang = el.xpath('@xml:lang', {'xml':'{http://www.w3.org/XML/1998/namespace'})[0]
##                                     except IndexError:
##                                         manySubjectList.append(flattenTexts(el))
##                                     else:
##                                         manySubjectList.append(flattenTexts(el) + ' (' + lang + ")")
                                                                                        
##                             manySubject2 = recClassification.process_xpath(session, '//term[@type="use"]')
##                             for el in manySubject2:
##                                 if el.text:
##                                     try:
##                                         lang = el.xpath('@xml:lang', {'xml':'{http://www.w3.org/XML/1998/namespace'})[0]
##                                     except IndexError:
##                                         manySubjectList.append(flattenTexts(el))
##                                     else:
##                                         manySubjectList.append(flattenTexts(el) + ' (' + lang + ")")          

                                                       
##                             subjectFinished = " or ".join(manySubjectList)
##                             subject = "Subject: %s" % (subjectFinished)
##                             subjectList.append(subject)
                        
##                     except:
##                         subjectList.append(item)
                            
##                 printSubjects = "<br/>".join(subjectList)
##             except:
##                 printSubjects = ""
##             ## try:
## ##                 subjectpersonal = "Subject Personal: %s <br/>" % rec.process_xpath(session, '//subject-personal/subjId')[0]
                
## ##             except:
## ##                 subjectpersonal = ""
## ##             try:
## ##                 subjectcorporate = "Subject Corporate: %s <br/>" % rec.process_xpath(session, '//subject-corporate/subjId')[0]
                
## ##             except:
## ##                 subjectcorporate = ""
## ##             try:
## ##                 subjectplace = "Subject Place: %s <br/>" % rec.process_xpath(session, '//subject-place/@subjId')[0]
                
## ##             except:
## ##                 subjectplace = ""
## ##             try:
## ##                 subjectmatter = "Subject Matter: %s <br/>" % rec.process_xpath(session, '//subject-matter/@subjId')[0]
                
## ##             except:
## ##                 subjectmatter = ""
       
             
            #html = html + "%s  %s  %s  %s %s %s %s  %s  %s  %s  %s  %s  %s  %s  %s  %s    " % (classification, author, title, identification, date, publish, description, edition, note, notevolumes, titleseries, issuedin, issuedinauthor, issuedineditionstatement, issuedinpublisher, printSubjects)
        #html = html + "</table>"

        return ('Record details', html, extra)
        #return (references.encode('utf8'), html)
       

    def browse(self, form):
        idx = form.get('fieldidx1', None)
        rel = form.get('fieldrel1', 'exact')
        scanTerm = form.get('fieldcont1', '')
        firstrec = int(form.get('firstrec', 1))
        numreq = int(form.get('numreq', 25))
        rp = int(form.get('responsePosition', numreq/2))
        qString = '%s %s "%s"' % (idx, rel, scanTerm)
        t = []
##       if (idx == 'c3.idx-classification-personal'):
##             db = serv.get_object(session, 'db_leipzig_classification')
##         else:
        db = serv.get_object(session, 'db_istc')
        #db2 = serv.get_object(session, 'db_leipzig_classification')
        try:
            scanClause = CQLParser.parse(qString)
           
        except:
           
            qString = self.generate_query(form)
            try:
                scanClause = CQLParser.parse(qString)
                
            except:
                t.append('Unparsable query: %s' % qString)
                return (" ".join(t), '<p>An invalid query was submitted.</p>')
            
        t.append('Browse Indexes')

        hitstart = False
        hitend = False
        #scanData = db.scan(session, scanClause, 5, direction="<=")
        if (scanTerm == ''):
            hitstart = True
            rp = 0
        if (rp == 0):
            scanData = db.scan(session, scanClause, numreq, direction=">")
            #if (len(scanData) < numreq): hitend = True
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
                scanData = db.scan(session, scanClause, numreq, direction="<=")
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
           #### FOR ENCODED Classification ###########
##         if (idx == 'c3.idx-author' or idx == 'c3.idx-subject' or idx == 'c3.idx-subject-object' or idx == 'c3.idx-subject-motive' or idx== 'c3.idx-subject-location' or idx =='c3.idx-subject-person' or idx == 'c3.idx-subject-corporation' or idx == 'c3.idx-corporal-editor' ):
##             session.database = db2.id   
##             scanData2 = []
##             authorDict = {}
##             for each in scanData:
##                 q2 = CQLParser.parse('c3.idx-classification-identifier exact "%s"' % (each[0]))
##                 #try:
##                 rs2 = db2.search(session, q2)
##                 if len(rs2):
##                     recClassification = rs2[0].fetch_record(session)
##                     displayTerm = [recClassification.process_xpath(session, '//term[@type="descriptor"]/text()')[0], each[1]]
##                 else:
##                     displayTerm = each 
##                 #except:
##                 #    displayTerm = each
##                 scanData2.append(displayTerm)
##                 authorDict[displayTerm[0]] = each[0]
##             scanData2.sort()
##             scanData = scanData2
               ######################################    
        totalTerms = len(scanData)

        if (totalTerms > 0):
            t.append('Results')
            rows = ['<table width = "90%" cellspacing="5" summary="list of terms in this index">',
                    '<tr class="headrow"><td>Term</td><td>Records</td></tr>']

            rowCount = 0
            
            
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
                #if (idx == 'c3.idx-author' or idx == 'c3.idx-subject' or idx == 'c3.idx-subject-object' or idx == 'c3.idx-subject-motive' or idx== 'c3.idx-subject-location' or idx =='c3.idx-subject-person' or idx == 'c3.idx-subject-corporation' or idx == 'c3.idx-corporal-editor'):
                   # term = authorDict[term]
                    
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
                    'SCRIPT': "search.html"
                }
                for key, val in paramDict.iteritems():
                    row = row.replace(key, val)

                rows.append(row)

            #- end for each item in scanData
            if (hitstart):
                rows.append('<tr class="odd"><td colspan="2">-- start of index --</td></tr>')
                rowCount += 1
                prevlink = ''
            else:
                prevlink=""
                prevlink = '<a href="/istc%s?fieldidx1=%s&amp;fieldrel1=%s&amp;fieldcont1=%s&amp;responsePosition=%d&amp;numreq=%d"><!-- img -->Previous %d terms</a>' % (script, idx, rel, cgi_encode(scanData[0][0]), numreq, numreq, numreq)
                
            if (hitend):
                rowCount += 1
                if (rowCount % 2 == 1): rowclass = 'odd';
                else: rowclass = 'even';
                rows.append('<tr class="%s"><td colspan="2">-- end of index --</td></tr>' % (rowclass))
                nextlink = ''
            else:
                nextlink = '<a href="/istc%s?operation=browse&amp;fieldidx1=%s&amp;fieldrel1=%s&amp;fieldcont1=%s&amp;responsePosition=%d&amp;numreq=%d"><!-- img -->Next %d terms</a>' % (script, idx, rel, cgi_encode(scanData[-1][0]), 0, numreq, numreq)

            del scanData
            rows.append('</table>')           
            rows.extend(['<div class="scannav"><p>%s</p></div>' % (' | '.join([prevlink, nextlink])),
                         '</div><!-- end of single div -->',
                         '</div> <!-- end of wrapper div -->'
                         ])
            #- end hit navigation
            
            return (" ".join(t),'\n'.join(rows))

        else:
            t.append('Error')
            return (" ".join(t), '<p class="error">No terms retrieved from index. You may be browsing outside the range of terms within the index.</p>')

##     #- end browse() ------------------------------------------------------------
    
    def handle(self, req):
        session = Session()
        session.environment = "apache"
        session.server = serv
                
        form = FieldStorage(req)
        
        f = file(self.templatePath)
        tmpl = f.read()
        f.close()
        tmpl = tmpl.replace('\n', '')
        
        path = req.uri[1:] 
        path = path[5:]

        e = ""
        if (path =="list.html"):
	        (t, d) = self.handle_list(session, form)           
        elif (path == "search.html"):
            cql = self.generate_query(form)
            (t, d) = self.handle_istc(session, cql)
        elif (path == "record.html"):
            (t, d, e) = self.handle_record(session, form)
        elif (path  == 'scan.html'):
            (t, d) = self.browse(form)   
        else:            
            if (os.path.exists(path)):
                f = file(path)
                d = f.read()
                f.close()
                stuff = d.split("\n", 1)
                if (len(stuff) == 1):
                    t = "Cheshire/ISTC"
                else:
                    t = stuff[0]
                    d = stuff[1]
            else:
                                
                f= file("index.html")
                d = f.read()
                f.close()
                t = "Search"
  
            
        extra = ''

        d = d.encode('utf8')
        d = d.replace('iso-8859-1', 'utf-8')
        e = e.encode('utf8')
        tmpl = tmpl.replace("%CONTENT%", d)
        tmpl = tmpl.replace("%CONTENTTITLE%", t)
        tmpl = tmpl.replace("%EXTRA%", extra)
        tmpl = tmpl.replace("%EXTRATABLESTUFF%", e)
	self.send_html(tmpl, req)


    
os.chdir("/home/cheshire/cheshire3/cheshire3/code")

from baseObjects import Session
session = Session()
serv = SimpleServer(session, '/home/cheshire/cheshire3/cheshire3/configs/serverConfig.xml')

db = serv.get_object(session, 'db_istc')
db2 = serv.get_object(session, 'db_usa')
db3 = serv.get_object(session, 'db_refs')

session.database = db.id
dfp = db.get_path(session, "defaultPath")
recStore = db.get_object(session, 'recordStore')
indexStore = db.get_object(session, 'indexStore')
usaRecStore = db2.get_object(session, 'usaRecordStore')
usaIndexStore = db2.get_object(session, 'usaIndexStore')
refsRecStore = db3.get_object(session, 'refsRecordStore')
refsIndexStore = db3.get_object(session, 'refsIndexStore')

logfilepath = '/home/cheshire/cheshire3/cheshire3/www/istc/logs/searchhandler.log'
from www_utils import FileLogger

def handler(req):
    # do stuff
    os.chdir("/home/cheshire/cheshire3/cheshire3/www/istc/html/")
    remote_host = req.get_remote_host(apache.REMOTE_NOLOOKUP)                   # get the remote host's IP for logging
    lgr = FileLogger(logfilepath, remote_host)                                  # initialise logger object
    istchandler = istcHandler(lgr)        
    try:
        istchandler.handle(req)
        try: lgr.flush()                                                        # flush all logged strings to disk
        except: pass
    except:
        req.content_type = "text/html; charset=utf-8"
        cgitb.Hook(file = req).handle()
    return apache.OK

