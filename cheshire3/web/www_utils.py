#
# Program:   www_utils.py
# Version:   0.10
# Description:
#            Generic search functions for Cheshire 3
#
# Language:  Python
# Author:    John Harrison <john.harrison@liv.ac.uk>
# Date:      19 December 2007
#
# Copyright: &copy; University of Liverpool 2005-2007
#
# Version History:
# 0.01 - 13/04/2005 - JH - Ported from Cheshire II compatible scripts
# 0.02 - 14/06/2005 - JH - Improved CGI encoding/decoding
#                       - Mixed phrase and plain term searching handled
#                         (e.g. wyndham "science fiction" triffids)
# 0.03 - 17/10/2005 - JH - File logger class added
#                           keeps all logs for a single request in mem until complete, then flushes to file
#                        - html_encode() added to allow display of raw SGML in the browser
# 0.04 - 26/01/2006 - JH - Modifications to cgiReplacements
# 0.05 - 31/01/2006 - JH - More tweaks to cgiReplacement characters
#                        - Speech marks handled sensibly in exact or /string searches
# 0.06 - 27/02/2006 - JH - Booleans extracted first in generate_cqlQuery() - debugs 'NOT' searches
# 0.07 - 04/01/2007 - JH - Check for noComponents moved out of generic generate_cqlQuery function
#                        - Allow limit to collection
# 0.08 - 25/01/2007 - JH - Mods to allow date searching - decode < > etc from form
# 0.09 - 07/09/2007 - JH - renamed: wwwSearch.py --> www_utils.py
# 0.10 - 19/12/2007 - JH - handling of form character set implemented
#                        - can handle multiple indexes to be specified in fieldidx
#                            multiple indexes combine with or/relevant/proxinfo
#


import re
import time

from urllib import unquote


class FieldStorageDict(dict):
    """A sub-class of dict to behave like FieldStorage for testing.

    Note, does not support multiple values for the same key.
    """

    def getfirst(self, key, default=None):
        return self.get(key, default)

    def getlist(self, key):
        val = self.get(key)
        if val:
            return [val]
        return []


def generate_cqlQuery(form):
    global phraseRe
    qClauses = []
    bools = []
    i = 1
    while 'fieldcont{0}'.format(i) in form:
        boolean = form.getfirst('fieldbool{0}'.format(i - 1),
                                'and/relevant/proxinfo'
                                )
        bools.append(boolean)
        i += 1

    i = 1
    while 'fieldcont{0}'.format(i) in form:
        cont = form.getfirst('fieldcont{0}'.format(i))
        idxs = unquote(
            form.getfirst('fieldidx{0}'.format(i),
                          'cql.anywhere'
                          )
        )
        rel = unquote(
            form.getfirst('fieldrel{0}'.format(i),
                          'all/relevant/proxinfo'
                          )
        )
        idxClauses = []
        # In case they're trying to do phrase searching
        if (
            rel.startswith('exact') or
            rel.startswith('=') or
            '/string' in rel
        ):
            # Don't allow phrase searching for exact or /string searches
            cont = cont.replace('"', '\\"')

        for idx in idxs.split('||'):
            subClauses = []
            if (rel.startswith('all')):
                subBool = ' and/relevant/proxinfo '
            else:
                subBool = ' or/relevant/proxinfo '

            # In case they're trying to do phrase searching
            if (
                'exact' in rel or
                '=' in rel or
                '/string' in rel
            ):
                # Don't allow phrase searching for exact or /string searches
                # we already did quote escaping
                pass
            else:
                phrases = phraseRe.findall(cont)
                for ph in phrases:
                    subClauses.append(
                        '({0} =/relevant/proxinfo {1})'.format(idx, ph)
                    )

                subcont = phraseRe.sub('', cont)

            if (idx and rel and subcont):
                subClauses.append(
                    '{0} {1} "{2}"'.format(idx, rel, subcont.strip())
                )

            if (len(subClauses)):
                idxClauses.append('({0})'.format(subBool.join(subClauses)))

        qClauses.append(
            '({0})'.format(' or/rel.combine=sum/proxinfo '.join(idxClauses))
        )
        # If there's another clause and a corresponding boolean
        try:
            qClauses.append(bools[i])
        except:
            break

        i += 1

    qString = ' '.join(qClauses)
    formcodec = form.getfirst('_charset_', 'utf-8')
    return qString.decode(formcodec).encode('utf8')


def parse_url(url):
    u"""Parse a URL to split it into its component parts."""
    bits = urlparse.urlsplit(url)
    transport = bits[0]
    uphp = bits[1].split('@')
    user = ''
    passwd = ''
    if len(uphp) == 2:
        (user, passwd) = uphp[0].split(':')
        uphp.pop(0)
    hp = uphp[0].split(':')
    host = hp[0]
    if len(hp) == 2:
        port = int(hp[1])
    else:
        # require subclass to default
        port = 0
    # now cwd to the directory, check if last chunk is dir or file
    (dirname,filename) = os.path.split(bits[2])
    # params = map(lambda x: x.split('='), bits[3].split('&'))
    params = [x.split('=') for x in bits[3].split('&')]
    params = dict(params)
    anchor = bits[4]
    return (transport, user, passwd, host, port, dirname, filename, params, anchor)


phraseRe = re.compile('".*?"')

cgiReplacements = {
#'%': '%25',
'+': '%2B',
' ': '%20',
'<': '%3C',
'>': '%3E',
'#': '%23',
'{': '%7B',
'}': '%7D',
'|': '%7C',
'"': '%22',
"'": '%27',
'^': '%5E',
'~': '%7E',
'[': '%5B',
']': '%5D',
'`': '%60',
';': '%3B',
'/': '%2F',
'?': '%3F',
':': '%3A',
'@': '%40',
'=': '%3D',
'&': '%26',
'$': '%24'
#'=': "%3D", 
#'\n\t': "%0A", 
#',': "%2C", 
#'\'': "%27",
#'/': "%2F",
#'"': "%22",
#'@': "%40",
#'#': "%23",
#'{': "%7B",
#'}': "%7D",
#'[': "%5B",
#']': "%5D",
#'\\': "%5C",
#';': "%3B"
}

def cgi_encode(txt):
    global cgiReplacements
    txt = txt.replace('%', '%25')
    #txt = txt.strip()
    for key, val in cgiReplacements.iteritems():
        txt =  txt.replace(key, val)

    return txt

#- end cgi_encode

def cgi_decode(txt):
    global cgiReplacements
    #txt = txt.strip()
    for key, val in cgiReplacements.iteritems():
        txt =  txt.replace(val, key)

    txt = txt.replace('%25', '%')
    return txt

#- end cgi_decode

rawSgmlReplacements = {'<': '&lt;'
                      ,'>': '&gt;'
                      ,"'": '&apos;'
                      ,'"': '&quot;'
                      }

def html_encode(txt):
    global rawSgmlReplacements
    txt = txt.replace('&', '&amp;')
    for key, val in rawSgmlReplacements.iteritems():
        txt =  txt.replace(key, val)

    return txt


#- end html_encode

def multiReplace(txt, params):
    for k,v in params.iteritems():
        try:
            txt = txt.replace(k,unicode(v).encode('ascii', 'xmlcharrefreplace'))
        except UnicodeDecodeError:
            txt = txt.replace(k,unicode(v, 'utf8').encode('ascii', 'xmlcharrefreplace'))
    return txt

#- end multiReplace

def read_file(fileName):
    fileH = open(fileName, 'r')
    cont = fileH.read()
    fileH.close()
    return cont

#- end read_file()

def write_file(fileName, txt):
    fileH = open(fileName, 'w')
    cont = fileH.write(txt)
    fileH.close()

#- end write_file()


class FileLogger:
    u"""DEPRECATED: A quick and dirty transaction logger that isn't actually a Cheshire3 object and doesn't match the API.
    
    Please use cheshire3.web.logger.TransactionLogger instead.
    """
    st = None
    llt = None
    fp = None
    rh = None
    lsl = None

    def __init__(self, path, rh):
        self.st = time.time()
        self.llt = self.st
        self.fp = path
        self.rh = rh
        self.lsl = ['\n[%s]: Request received from %s' % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.st)), self.rh)]
        
    def log(self,txt):
        now = time.time()
        diff = now - self.llt
        self.lsl.append('...[+%f s]: %s' % (diff, txt))
        self.llt = now

    def flush(self):
        now = time.time()
        total = now - self.st
        self.lsl.append('...Total time: %f secs' % (total))
        fileh = file(self.fp, 'a')
        fileh.write('\n'.join(self.lsl))
        fileh.close()


#- end class FileLogger ---------------------------------------------------
