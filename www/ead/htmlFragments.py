#
# Script:     htmlFragments.py
# Version:    0.01
# Description:
#            HTML fragments used by Cheshire for Archives
#
# Language:  Python
# Author:    John Harrison <john.harrison@liv.ac.uk>
# Date:      3 January 2007
#
# Copyright: &copy; University of Liverpool 2005-2007
#
# Version History:
# 0.01 - 03/01/2006 - JH - HTML Fragments migrated from localConfig.py
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
#
#



# img tags for icons used in results
# - N.B. These will only be displayed if the result_graphics switch is set to 1
full_tag = '<img src="/images/v3_full.gif" alt="Full"/>'
email_tag = '<img src="/images/v3_email.gif" alt="e-mail"/>'
similar_tag = '<img src="/images/v3_simlr.gif" alt="Similar"/>'

# Result rows
browse_result_row = '''
    <tr class="%ROWCLASS%">
      <td>
        <a href="SCRIPT?operation=search&amp;fieldidx1=%IDX%&amp;fieldrel1=%REL%&amp;fieldcont1=%CGITERM%" title="Find matching records">%TERM%</a>
      </td>
      <td class="hitcount">%COUNT%</td>
    </tr>'''

subject_resolve_row = '''
    <tr class="%ROWCLASS%">
      <td>
        <a href="SCRIPT?operation=search&amp;fieldidx1=dc.subject&amp;fieldrel1=exact&amp;fieldcont1=%CGISUBJ%" title="Find records with matching subjects">%TITLE%</a>
      </td>
      <td class="relv">%RELV%</td>
      <td class="hitcount">%COUNT%</td>
    </tr>'''

search_result_row = '''
    <tr>
      <td class="hit">
        <table width="100%">
          <tr>
            <td colspan="4">
              <a href="SCRIPT?operation=summary%RSID%&amp;hitposition=%HITPOSITION%" title="Display record summary" %SPLASH%><strong>%TITLE%</strong></a>
            </td>
          </tr>
          <tr>
            <td width="100">
              <a href="SCRIPT?operation=full%RSID%&amp;hitposition=%HITPOSITION%" title="Display Full-text" %SPLASH%>%FULL%</a>
            </td>
            <td width="100">
              <a href="SCRIPT?operation=email%RSID%&amp;hitposition=%HITPOSITION%" title="Send record by e-mail">%EMAIL%</a>
            </td>
            <td width="100">
              <a href="SCRIPT?operation=similar%RSID%&amp;hitposition=%HITPOSITION%" title="Find similar records" %SPLASH%">%SIMILAR%</a>
            </td>
            <td class="relv">%RELV%</td>
          </tr>
        </table>
      </td>
    </tr>'''

search_component_row = '''
    <tr>
      <td class="comphit">
        <table width="100%">
          <tr>
            <td colspan="4">
              In <em>%PARENT%</em>
            </td>
          </tr>
          <tr>
            <td colspan="4">
              <img src="/images/folderClosed.jpg" alt="[+]" title="Component record"/>
              <a href="SCRIPT?operation=summary%RSID%&amp;hitposition=%HITPOSITION%" title="Display record summary" %SPLASH%><strong>%TITLE%</strong></a>
            </td>
          </tr>
          <tr>
            <td width="100">
            <a href="SCRIPT?operation=full%RSID%&amp;hitposition=%HITPOSITION%" title="Display Full-text" %SPLASH%>%FULL%</a>
            </td>
            <td width="100">
            <a href="SCRIPT?operation=email%RSID%&amp;hitposition=%HITPOSITION%" title="Send record by e-mail">%EMAIL%</a>
            </td>
            <td width="100">
            <a href="SCRIPT?operation=similar%RSID%&amp;hitposition=%HITPOSITION%" title="Find similar records" %SPLASH%>%SIMILAR%</a>
            </td>
            <td class="relv">%RELV%</td>
          </tr>
        </table>
      </td>
    </tr>'''

toc_scripts = '''
<script type="text/javascript" src="/javascript/collapsibleLists.js"></script>
<script type="text/javascript" src="/javascript/cookies.js"></script>
<script type="text/javascript">
  <!--
  function loadPage() {
    closeSplash();
    collapseList('someId', getCookie('RECID-tocstate'), true);
  }
  function unloadPage() {
    setCookie('RECID-tocstate', stateToString('someId'));
  }
  -->
</script>
'''

printable_toc_scripts = toc_scripts

user_form = '''

'''

new_user_template = '''
<config type="user" id="%USERNAME%">
  <objectType>user.SimpleUser</objectType>
  <username>%USERNAME%</username>
  <flags>
    <flag>
      <object/>
      <value>c3r:administrator</value>
    </flag>
  </flags>
</config>'''

