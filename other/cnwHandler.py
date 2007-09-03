
from mod_python import apache, Cookie
from mod_python.util import FieldStorage
import sys, traceback, os, cgitb, time, urllib
from server import SimpleServer
from PyZ3950 import CQLParser
import resultSet
from smtplib import SMTP
from baseObjects import Session
# Apache Config:

#<VirtualHost 138.253.81.47:80>
#  DocumentRoot /home/cheshire/c3/cnw/html
#  ServerName www.cardsnotwords.com
#  AddHandler mod_python .html
#  PythonDebug On
#  PythonPath "['/home/cheshire/c3/code']+sys.path"
#  PythonHandler cnwHandler
#</VirtualHost>

#<Directory /home/cheshire/c3/cnw/html/admin>
#  PythonDebug On
#  PythonPath "['/home/cheshire/c3/code']+sys.path"
#  PythonAuthenHandler cnwHandler
#  AuthType Basic
#  AuthName CardsNotWords
#  require valid-user
#</Directory>


class CNWHandler:

    templatePath = "/home/cheshire/cheshire3/www/cnw/html/template.ssi"
    shippingHash = {"UK" : 1.00, "EU" : 2.00, "o" : 3.00}


    def send_html(self, text, req, code=200):
        req.content_type = 'text/html'
        req.content_length = len(text)
        req.send_http_header()
        req.write(text)

        
    def handle_searchList(self, session, cql, start=0, url="", stock=0):
        global l5r, titleIdx, recStore, singleTxr
        stock = 0
        try:
            tree = CQLParser.parse(cql)
        except:
            return ("Search Error", "<p>Could not parse your query. Please try again.")
        try:
            rs = l5r.search(session, tree)
        except Exception, err:
            diag = str(err)
            return ("Search Error", "<p>Could not process your query. Please try again.<br>Error: %s" % diag)  
            
        rs.order(session, titleIdx)
        d = ['<table width="95%" align="center" class="cardListTable" cellspacing=0 cellpadding=1><tr><th>Card Name</th><th width="8%">Stock</th><th width="8%">Price</th><th width="8%">Add</th></tr>']
        end =start +  min(len(rs) - start, 25)
        esccql = urllib.quote(cql)
        newurl = "/list.html?query=%s&start=%d&" % (esccql, start)

        x = start
        while (x < len(rs) and x < end):
            rec = recStore.fetch_record(session, rs[x].docid)
            rec.holdings = 0
            if (not stock or rec.holdings):
                htmldoc = singleTxr.process_record(session, rec)
                html = htmldoc.get_raw()
                html = html.replace("&amp;", "&")
                html = html % (rec.id, rec.holdings)
                #html = html.replace('|ICON|', '<a href="%saddToCart=%d"><img border="0" src="/buy_yellow.gif"/></a>' % (newurl, rec.id))
                if (rec.holdings):
                    html = html.replace('|ICON|', '<a href="%saddToCart=%d"><img border="0" src="/buy_yellow.gif"/></a>' % (newurl, rec.id))
                else:
                    html = html.replace('|ICON|', '<img border="0" src="/buy_grey.gif"/>')
                d.append(html)
            else:
                end += 1
            x += 1
        d.append("</table>")


        d.append('<br><div align="right">')
        s = ['<div align="right">']
        if (start <> 0):
            d.append('<a href="/list.html?query=%s&start=%d"><img src="previous_yellow.gif" border=0></a>   &nbsp; ' % (esccql, start-25))
            s.append('<a href="/list.html?query=%s&start=%d"><img src="previous_yellow.gif" border=0></a>   &nbsp; ' % (esccql, start-25))
        if (end < len(rs)):
            d.append('<a href="/list.html?query=%s&start=%d"><img src="next_yellow.gif" border=0></a><br><br>' % (esccql, end))
            s.append('<a href="/list.html?query=%s&start=%d"><img src="next_yellow.gif" border=0></a><br><br>' % (esccql, end))

        d.append("</div>")
        s.append("</div>")
        
        d = ''.join(s) + ''.join(d)
        t = "Cards %d-%d/%d" % (start+1, min(end, len(rs)), len(rs))
        return (t, d)


    def generateCart(self, rset, session):
        global titleIdx, recStore, singleTxr
        # Actually generate a cart here.
        total = 0.0
        cards = []
        rset.order(session, titleIdx)
        cards = []
        for item in rset:
            rec = recStore.fetch_record(session, item.docid)
            htmldoc = singleTxr.process_record(session, rec)
            html = htmldoc.get_raw()
            html = html.replace('<?xml version="1.0" encoding="UTF-8"?>\n', '')
            stuff = html.split('</td><td align="center">')
            start = stuff[0].replace("<b>", "%dx " % (item.occurences))
            start = start.replace("</b>", "") % (rec.id)
	    p = stuff[2].replace('&amp;pound;', "")
	    price = float(p)
            total += (price * item.occurences)
            cards.append(start + "</td></tr>")
        if (cards):
            cards.append('<tr><td align="right"><a href="viewCart.html">Show Cart --&gt;</a></td></tr>')
        
        cards = ''.join(cards)

        text = """
        <tr>
        <td class="headCell" colspan="2">Cart: &nbsp;  &pound;%.2f</td>
        </tr>
        <tr><td>%s</td></tr>
        """ % (total, cards)
        return text

    def generate_query(self, form):
        # need to return cql query

        if (form.has_key('query')  and form['query'].value):
            return urllib.unquote(form['query'].value)

        if (form.has_key('bool')):
            bool = form['bool'].value
        else:
            bool = 'and'
        n = 1
        cql = []
        while (form.has_key('idx%d' % n)):
            try:
                term = form['term%d' % n].value
            except:
                n += 1
                continue
            if (term):
                idx = form['idx%d' % n].value
                rel = form['rel%d' % n].value
                if (cql):
                    cql.append(bool)
                cql.append(' %s %s "%s" ' % (idx, rel, term))
            n += 1
        return ''.join(cql)
        

    def display_card(self, rec, path, session):
        global cardTxr
        htmldoc = cardTxr.process_record(session, rec)
        html = htmldoc.get_raw()
        (title,html) = html.split('||')
        #href = path + "?c=%d&addToCart=%d" % (rec.id, rec.id)
        html = html.replace("|pound|", "&pound;")
        #html = html.replace("|ADD2CART|", href)
        return (title, "<table>%s</table>" % html)

    def handle(self, req):
        global rsetStore, recStore

        session = Session()
        session.environment = "apache"
        session.db = "db_spy"
        
        path = req.uri[1:]
        form = FieldStorage(req)
        f = file(self.templatePath)
        tmpl = f.read()
        f.close()
        tmpl = tmpl.replace('\n', '')

        cks = Cookie.get_cookies(req)
        if cks.has_key('cnwCart'):
            cart = cks['cnwCart']
            rsid = cart.value
            try:
                cartRSet = rsetStore.fetch_resultSet(session, rsid)
            except:
                cartRSet = None
            if (cartRSet == None):
                # Expired, Create a new one
                cartRSet = resultSet.SimpleResultSet(None)
                rsid = rsetStore.create_resultSet(session, cartRSet)
                cart = Cookie.Cookie('cnwCart', rsid)
        else:
            cartRSet = resultSet.SimpleResultSet(None, [])
            rsid = rsetStore.create_resultSet(session, cartRSet)
            rsetStore.close(session)
            cart = Cookie.Cookie('cnwCart', rsid)
        Cookie.add_cookie(req, cart)
        
        if (form.has_key('addToCart')):
            card = form['addToCart'].value
            item = resultSet.SimpleResultSetItem(None, int(card), recStore.id)
            item.occurences = 1
            add = 1
            for i in cartRSet:
                if (i == item):
                    i.occurences += 1
                    add = 0
                    break
            else:
                cartRSet.append(item)
            rsetStore.store_resultSet(session, cartRSet)
            rsetStore.close(None)
        elif (form.has_key('removeFromCart')):
            card = form['removeFromCart'].value
            item = resultSet.SimpleResultSetItem(None, int(card), recStore.id)
            for i in cartRSet:
                if (i == item):
                    i.occurences -= 1
                    if (i.occurences <= 0):
                        rset2 = resultSet.SimpleResultSet(None, [i])
			q = CQLParser.parse('a not b')
			cartRSet = cartRSet.combine(session, [rset2], q)

            rsetStore.store_resultSet(None, cartRSet)
            rsetStore.close(None)


        if (path == "card.html"):
            if (form.has_key('c')):
                id = form['c'].value               
                rec = recStore.fetch_record(session, id)
                (t, d) = self.display_card(rec, req.uri, session)
            else:
                (t,d) = ("Fuqt!", "<p>The arguments to the page are fuqt</p>")
                
        elif (path == "viewCart.html"):
            # Show full cart, allow remove, go to checkout

            if (form.has_key("country")):
                country = form['country'].value
            else:
                country = "UK"
                
            currentShippingAmnt = self.shippingHash[country]

            t = "Your Shopping Cart"
            cards = ['<BR><table width="95%" align="center" class="cardListTable" cellspacing=0 cellpadding=1><tr><th width="8%">Remove</th><th>Card Name</th><th width="8%" align="center">Number</th><th width="8%">Price</th><th width="8%">Total</th></tr>']
            total = 0.0
            for item in cartRSet:
                rec = recStore.fetch_record(None, item.docid)
                htmldoc = singleTxr.process_record(None, rec)
                html = htmldoc.get_raw()
                html = html.replace('<?xml version="1.0" encoding="UTF-8"?>\n', '')
                stuff = html.split('</td><td align="center">')
		p = stuff[2].replace("&amp;pound;", "")
		price = float(p)
                total += (price * item.occurences)
                html = html % (rec.id, item.occurences)
                html = html.replace("|ICON|", '%.2f' % (price * item.occurences))
                html = html.replace("<tr>", '<tr><td><a href="viewCart.html?removeFromCart=%d"><img src="remove.gif" border="0"></a></td>' % (rec.id))
		html = html.replace("&amp;", "&")
		cards.append(html)

            cards.append('<tr><td colspan="4" align="right">Sub-Total:</td><td align="center">%.2f</td></tr>' % total)
            cards.append('<script language="Javascript">function update() { document.forms[1].submit() }</script>')
            cards.append('<form action="viewCart.html"><tr><td align="right" colspan="2">Select Shipping Country:</td><td colspan="2"><select name="country" onChange="update()">')
            if (country == "UK"):
                cards.append("""
            <option value="UK">United Kingdom</option>
            <option value="EU">Europe</option>
            <option value="o">Other</option>
            """)
            elif (country == "EU"):
                cards.append("""
                        <option value="EU">Europe</option>
                        <option value="UK">United Kingdom</option>
                        <option value="o">Other</option>
                """)
            else:
                cards.append("""            <option value="o">Other</option>
                         <option value="UK">United Kingdom</option>
                         <option value="EU">Europe</option>   
                         """)

            cards.append('</select></td><td align="center">%.2f</td></tr></form>' % currentShippingAmnt)
            cards.append('<tr><td colspan="4" align="right">Total:</td><td align="center">%.2f</td></tr>' % (total + float(currentShippingAmnt)))
            cards.append("""<tr><td colspan="5" align="right" valign="center">Save Cart: <a href="saveCart.html?country=%s"><img src="/checkout_blue.gif" border="0"/></a></td></tr>""" % (country))
            cards.append('</table>')            
            d  = ''.join(cards)

        elif (path == "admin/viewCarts.html"):
            # Fetch list of result sets and link
            carts = permResultStore.fetch_resultSetList(None)
            html = ['<ul>']
            for c in carts:
                html.append('<li><a href="viewCart.html?cartid=%s">%s</a>' % (c, c))
            html.append('</ul>')
            (t, d) = ("Carts", "".join(html))
        elif (path == "admin/viewCart.html"):
            c = form['cartid'].value
            rset = permResultStore.fetch_resultSet(None, c)
            total = 0.0
            cards = ['<table width="90% border="1">']
            for item in rset:
                rec = recStore.fetch_record(None, item.docid)
                htmldoc = singleTxr.process_record(None, rec)
                html = htmldoc.get_raw()
                html = html.replace('<?xml version="1.0" encoding="UTF-8"?>\n', '')
                stuff = html.split('</td><td align="center">')
                html = html.replace("&amp;", "&")
                p = stuff[2].replace("&amp;pound;", "")
                price = float(p)
                total += (price * item.occurences)
                html = html % (rec.id, item.occurences)
                html = html.replace("|ICON|", '%.2f' % (price * item.occurences))
                cards.append(html)
            cards.append("</table>")
            cards.append("<p><b>Total before shipping: %.2f</b>" % (total))
            (t, d) = ("Cart: %s" % (rset.id), "".join(cards))
        
        elif (path == "saveCart.html"):
            # Save cart into permanent DB, delete, email

            if (form.has_key("country")):
                shipping = self.shippingHash[form['country'].value]
            else:
                shipping = 0.0
                (t, d) = ("No Shipping Location", "You did not give a shipping location. Please go back and resave your cart.")
                               
            if (len(cartRSet) == 0):
                (t, d) = ("No Cart To Save", "Either you have already saved your shopping cart, or you do not have any items in it.")
            elif (shipping):
                permResultStore.store_resultSet(None, cartRSet)
                rsetStore.delete_resultSet(None, cartRSet.id)
                txtList = []
                htmlList = []
                formList = []
                total = 0
                i = 0
                allTotal = shipping
                for item in cartRSet:
                    i += 1
                    # First remove stock from db
                    m = parser.update_holdings(None, item.docid, 0 - item.occurences)
                    if (m < 0):
                        item.occurences += m
                        htmlList.append('<tr><td colspan="4"><b>Items were removed from the following entry because another buyer as already bought them.</b></td></tr>')
                    rec = recStore.fetch_record(None, item.docid)
                    htmldoc = singleTxr.process_record(None, rec)
                    html = htmldoc.get_raw()
                    html = html.replace('<?xml version="1.0" encoding="UTF-8"?>\n', '')
                    stuff = html.split('</td><td align="center">')
		    p = stuff[2].replace("&amp;pound;", "")
		    price = float(p)
                    total = (price * item.occurences)
                    allTotal += total
                    title = stuff[0]
                    title = title[37:-8]
                    html = html % (rec.id, item.occurences)
                    html = html.replace("|ICON|", '%.2f' % (price * item.occurences))
		    html = html.replace("&amp;", "&")
		    txt = "%s (%d @ %.2f) %.2f" % (title, item.occurences, price, total)
                    txtList.append(txt)
                    htmlList.append(html)
                    formList.append('<input type="hidden" name="item_name_%d" value="%s (%d)"><input type="hidden" name="amount_%d" value="%.2f">' % (i, title, item.occurences, i, total))
                txtList.append("Total:  %.2f" % (allTotal))
                htmlList.append('<tr><td align="right" colspan="4">Total: %.2f</td></tr>' % (allTotal))

                txt = "\n".join(txtList)
                html = "".join(htmlList)
                items = "".join(formList)
                c = req.connection
                msg = "\n".join(["New CNW Cart Saved", "New cart (%s) saved from user at %s.\n%s" % (cartRSet.id, c.remote_ip, txt)])
                server = SMTP('localhost')
                fromaddr = "cnw@gondolin.hist.liv.ac.uk"
                toaddrs = ["azaroth@liv.ac.uk", "kass@gondolin.hist.liv.ac.uk"]
                server.sendmail(fromaddr, toaddrs, msg)
                server.quit()

                form = """
                <form action="https://www.paypal.com/cgi-bin/webscr" method="post">
                <input type="hidden" name="cmd" value="_cart">
                <input type="hidden" name="business" value="azaroth@liv.ac.uk">
                <input type="hidden" name="item_number_1" value="CardsNotWords Cart: %s">
                <input type="hidden" name="currency_code" value="GBP">
                <input type="hidden" name="upload" value="1">
                <input type="hidden" name="shipping_1" value="%.2f">
                <center><input type="image" src="http://www.paypal.com/en_US/i/btn/x-click-but01.gif" name="submit" alt="Pay with PayPal"></center>
                %s</form>
                """ % (cartRSet.id, shipping, items)

                (t, d) = ("Cart Saved", '<table width="100%%"><tr><th>Card</th><th>Amount</th><th>Price</th><th>Total</th></tr>%s</table><p>Your cart has been saved and an alert sent to the store team.<p>If you are paying by cash or cheque, you <b>MUST</b> send the store team an email at <a href="mailto:cnw@gondolin.hist.liv.ac.uk">cnw@gondolin.hist.liv.ac.uk</a> to say so, or your cart may be deleted and the cards put back into the store.  You MUST include the following reference number: %s<p>You should also include your shipping address.<p>Pay with Paypal: %s</p><p><br></p>' % (html, cartRSet.id, form))                

                
        elif (path =="list.html"):
            if (form.has_key('start')):
                start = int(form['start'].value)
            else:
                start = 0
            if (form.has_key("inStock")):
                inStock = form['inStock'].value
            else:
                inStock = 0
            cql = self.generate_query(form)
            (t, d) = self.handle_searchList(session, cql, start=start, url=path, stock=inStock)
        elif (path == "sets.html"):
            set = form['set'].value
            cql = 'ccg.set any "%s"' % set
            (t, d) = self.handle_searchList(session, cql, url=req.unparsed_uri)
        elif (path == "qsearch.html"):
            stuff = form['fc1'].value
            cql = 'dc.title all "%s"' % stuff
            (t, d) = self.handle_searchList(session, cql, url=req.unparsed_uri)
        else:
            if (os.path.exists(path)):
                f = file(path)
                d = f.read()
                f.close()
                stuff = d.split("\n", 1)
                if (len(stuff) == 1):
                    t = "Cards, Not Words"
                else:
                    t = stuff[0]
                    d= stuff[1]
            else:
                # 404
                t = "Page Not Found"
                d = "<p>Could not find your requested page: '%s'</p><p>Please try again.</p>" % path

        cart = self.generateCart(cartRSet, session)
        tmpl = tmpl.replace("%CONTENT%", d)
        tmpl = tmpl.replace("%CONTENTTITLE%", t)
        tmpl = tmpl.replace("%CARTINCLUDE%", cart)
        self.send_html(tmpl, req)

os.chdir("/home/cheshire/cheshire3/code")
serv = SimpleServer('/home/cheshire/cheshire3/configs/serverConfig.xml')
l5r = serv.get_object(None, 'db_spy')
titleIdx = l5r.get_object(None, 'spy-idx-1')
recStore = l5r.get_object(None, 'spyRecordStore')
cardTxr = l5r.get_object(None, 'spyHtmlTxr')
singleTxr = l5r.get_object(None, 'spySingleTxr')
rsetStore = l5r.get_object(None, 'defaultResultSetStore')
permResultStore = l5r.get_object(None, 'PermanentResultSetStore')
authStore = serv.get_object(None, 'defaultAuthStore')
parser = l5r.get_object(None, 'spyOutParser')

def handler(req):
    # do stuff
    os.chdir("/home/cheshire/cheshire3/www/cnw/html")
    cnwhandler = CNWHandler()        
    try:
        cnwhandler.handle(req)
    except:
        req.content_type = "text/html"
        cgitb.Hook(file = req).handle()
    return apache.OK

def authenhandler(req):
    pw = req.get_basic_auth_pw()
    user = req.user
    u = authStore.fetch_object(None, user)
    if (u and u.password == pw):
        return apache.OK
    else:
        return apache.HTTP_UNAUTHORIZED
