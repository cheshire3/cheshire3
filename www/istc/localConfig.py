#
# Script:   localConfig.py
# Version:   0.12
# Description:
#            Customisable elements for Cheshire for Archives v3.x
#
# Language:  Python
# Author:    John Harrison <john.harrison@liv.ac.uk>
# Date:      18 June 2007
#
# Copyright: &copy; University of Liverpool 2005-2007
#
# Version History:
# 0.01 - 13/04/2005 - JH - Basic configurable elements coded by John
# 0.02 - 23/05/2005 - JH - Additions for email host/port, cache filepaths/URLs
# 0.03 - 10/06/2005 - JH - Result row reconfigured TITLE links to Summary, FULL links to Full-text
#                        - Preference switches from 0/1 to False/True
# 0.04 - 23/06/2005 - JH - Release synchronised with eadSearchHandler v0.06
# 0.05 - 22/11/2005 - JH - Additional elements added for eadAdminHandler
#                        - File size measurement adjusted to give a 10% buffer when generating multiple page display
#                        - Synchronised for release with eadSearchHandler v0.08
# 0.06 - 17/01/2006 - JH - extra global variables added for configuring email - sync'ed with release of v0.11
# 0.07 - 29/01/2006 - JH - oops, typo bug fixes
# 0.08 - 16/02/2006 - JH - Modifications to result row display
# 0.09 - 25/07/2006 - JH - Mods to subject resolve result rows
#                        - Switch to completely remove measure of relevance
# 0.10 - 03/01/2006 - JH - HTML Fragments moved out to separate file, htmlFragments.py and imported
#                        - script URL now defined here (overwritten in adminHandler)
# 0.11 - 16/05/2007 - JH - Change to default settings for switches
# 0.12 - 18/06/2007 - JH - sourceDir setting removed - now derived from documentFactory setting
#
#
# Changes to original:
# You should make a note of any changes that you make to the originally distributed file here.
# This will make it easier to remeber which fields need to be modified next time you update the software.
#
#
#

# Preference switches - True => ON, False => OFF
result_graphics = True
display_relevance = True
graphical_relevance = False
display_splash_screen_popup = False

# Path to Cheshire Root - i.e. where Cheshire3 was installed
cheshirePath = "/home/cheshire"

# Institutionally specific configurables
repository_name = "DNB Bibliographic Database"
repository_link = ""                        # must begin http://
repository_logo = ""             # should begin http:// unless on this server

# URL of relevance graphic
relevance_graphic = '/images/star.gif'

# server and email settings - you should check these with your computing services people.
localhost = '138.253.81.47'
outgoing_email_username = 'cheshire'
outgoing_email_host = "mail1.liv.ac.uk"
outgoing_email_port = 25                           # 25 is the default for most mail servers

# Logfile paths
logpath = cheshirePath + '/cheshire3/www/dnb/logs'
searchlogfilepath = logpath + '/searchHandler.log'
adminlogfilepath = logpath + '/adminHandler.log'

# Path where HTML fragments (browse.html, email.html, resolve.html, search.html)
# and template.ssi are located
htmlPath = cheshirePath + '/cheshire3/www/dnb/html'
templatePath = htmlPath + '/template.ssi'

# The approximate maximum desired page size when displaying full records (in kB)
maximum_page_size = 50

# The filepath where the HTML for finding aids and contents should be cached 
# N.B. This must be accessible by apache, so should be a sub-directory of htdocs
baseHtmlPath = cheshirePath + '/install/htdocs/dnb'
cache_path = baseHtmlPath + '/html'
toc_cache_path = baseHtmlPath + '/tocs'
# URLs
script = '/scan.html'
cache_url = '/dnb/html'
toc_cache_url = '/dnb/tocs'

# useful URIs
namespaceUriHash = {
    'dc': 'http://purl.org/dc/elements/1.0',
    'srw_dc': "info:srw/schema/1/dc-v1.1"
    }

# List of words which should not be used when conducting similar searches
# New words should be added inside the inverted commas, and separated by whitespace
stopwords = 'a and by for in is of on s th the to'

# HTML Fragments
from htmlFragments import *

# reflect switch preferences in HTML fragments
if ( result_graphics ):
    search_result_row = search_result_row.replace( '%FULL%', full_tag ).replace( '%EMAIL%', email_tag ).replace( '%SIMILAR%', similar_tag )
    search_component_row = search_component_row.replace( '%FULL%', full_tag ).replace( '%EMAIL%', email_tag ).replace( '%SIMILAR%', similar_tag )
else:
    search_result_row = search_result_row.replace( '%FULL%', 'Full text' ).replace( '%EMAIL%', 'e-mail' ).replace( '%SIMILAR%', 'Similar' )
    search_component_row = search_component_row.replace( '%FULL%', 'Full text' ).replace( '%EMAIL%', 'e-mail' ).replace( '%SIMILAR%', 'Similar' )

if ( display_splash_screen_popup ):
    search_result_row = search_result_row.replace('%SPLASH%', 'onclick="splashScreen()"')
    search_component_row = search_component_row.replace('%SPLASH%', 'onclick="splashScreen()"')
else:
    search_result_row = search_result_row.replace('%SPLASH%', '')
    search_component_row = search_component_row.replace('%SPLASH%', '')


# Some bits to ensure that objects are of the correct python object type - DO NOT EDIT THESE
# split similar search stoplist at whitespace
try:
    similar_search_stoplist = similar_search_stopwords.split()
except:
    similar_search_stoplist = []

# calculation for approx max page size in bytes - DO NOT edit
# maximum size in kb * bytes in a kb - size of template in bytes
max_page_size_bytes = (maximum_page_size * 1024) - 4943

