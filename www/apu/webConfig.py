#
# Script:     webConfig.py
# Version:    0.01
# Description:
#            HTML fragments used by Cheshire3 web-search interface
#
# Language:  Python
# Author(s): JH - John Harrison <john.harrison@liv.ac.uk>
# Date:      09 August 2007
#
# Copyright: &copy; University of Liverpool 2005-2007
#
# Version History:
# 0.01 - 09/08/2007 - JH - File created to support templateHandler.py
#
# NB:
# - If you are not experieced in editing HTML you are advised not to edit any of the HTML fragments
# - Modifying placeholder words (block caps enclosed in '%' e.g. %TITLE%) WILL SERIOUSLY affect the functionality of the system.
#
# Changes to original:
# You should make a note of any changes that you make to the originally distributed file here.
# This will make it easier to remeber which fields need to be modified next time you update the software.
#
#


# TODO: this will require setting specific to your configuration
databaseName = 'apu'

# Interface specific configurables
repository_name = "Cheshire3 %s Search Interface" % (databaseName.title())

# set Cheshire3 base install path
cheshirePath = '/home/cheshire'

# Path where HTML fragments (browse.html, email.html, resolve.html, search.html)
# and template.ssi are located
htmlPath = cheshirePath + '/cheshire3/www/%s/html' % databaseName
templatePath = htmlPath + '/template.ssi'

# TODO: XPath to data to display in search result - may be a string, or a list of strings in descending order of preference
titleXPath = 'head/headline'

# Result rows
browse_result_row = '''
    <tr class="%ROWCLASS%">
      <td>
        <a href="SCRIPT?operation=search&amp;fieldidx1=%IDX%&amp;fieldrel1=%REL%&amp;fieldcont1=%CGITERM%" title="Find matching records">%TERM%</a>
      </td>
      <td class="hitcount">%COUNT%</td>
    </tr>'''

search_result_row = '''
    <tr>
      <td class="hit">
        <table width="100%">
          <tr>
            <td colspan="4">
              <a href="display.html?%RSID%&amp;hitposition=%HITPOSITION%" title="Display record summary"><strong>%TITLE%</strong></a>
            </td>
          </tr>
          <tr>
            <td width="100">
            </td>
            <td width="100">
            </td>
            <td width="100">
            </td>
            <td class="relv">%RELV%</td>
          </tr>
        </table>
      </td>
    </tr>'''
