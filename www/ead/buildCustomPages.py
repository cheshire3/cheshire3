#!/home/cheshire/cheshire3/install/bin/python

import time, sys, os, re
from crypt import crypt

osp = sys.path
sys.path = ["/home/cheshire/cheshire3/cheshire3/code", "."]
sys.path.extend(osp)

from wwwSearch import *
# import customisable variables
from localConfig import *

pageMaps = {
    'index.html': 'Search', 
    'browse.html': 'Browse Indexes',
    'subject.html':'Subject Finder',
#    'preview.html':'Preview EAD',
#,    'adminhelp.html': 'Administration Help'
    'help.html':'Help',
    'about.html':'About Cheshire for Archives'
    }
    
tmplPage = read_file(templatePath)

paramDict = {
    'SCRIPT':script, 
    '%REP_NAME%': repository_name, 
    '%REP_LINK%': repository_link,
    '%REP_LOGO%': repository_logo, 
    '%NAVBAR%': ''
    }

print "Building customised pages:"        

for pn, title in pageMaps.iteritems():
    paramDict['%TITLE%'] = title

    p = read_file('%s/%s' % (htmlPath, pn))
    np = tmplPage.replace('%CONTENT%', p)
    
    for k,v in paramDict.iteritems():
        np = np.replace(k,v)
    
    write_file('%s/%s' % (baseHtmlPath, pn), np)
    print pn

sys.exit()
