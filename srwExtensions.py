
# All extension functions for SRW should be imported into this space
# even if they're defined elsewhere.

# Functions should modify extra*Data in place.
# Add DOM node for serialization by ZSI. 
# Fr'ex:
# object.extraFooData.append(r.fromString('<a:b c="d">e</a:b>'))

# Configuration in SRW ZeeRex file should look like:
#
#  <zeerex:supports type="extension"
#                   c3:type="record"
#                   c3:function="docidRecordHandler"
#                   c3:sruName="x-info2-docid"
#                   c3:sruFunction="docidRequestXform">
#     info:srw/extensions/2/docid-v1.0 docid
#  </zeerex:/supports>
# 
# Where c3:type is one of: record, term, search, scan, explain, response

# Useful tools:
from xml.sax.saxutils import escape
from utils import reader
r = reader()

# Simple SRU->SRW transformation

def simpleRequestXform(item, config):
    data = config.sruExtensionMap.get(item[0], None)
    if data:
        xml = '<ns1:%s xmlns:ns1="%s">%s</ns1:%s>' % (data[1], data[0], item[1], data[1])
        val = r.fromString(xml)
        return val
    return None

# Extension Handler Functions:

import internal
def implementationResponseHandler(req, resp, other=None):
    # Put our implementation id into the response
    # Stored in ZeeRex, so on config object
    txt = """
    <ident:serverInfo xmlns:ident="info:srw/extensions/1/ident-v1.0">
      <ident:institution>University of Liverpool</ident:institution>
      <ident:vendor>Cheshire3 Project</ident:vendor>
      <ident:application>Cheshire3 SRW Server</ident:application>
      <ident:version>%s</ident:version>
    </ident:serverInfo>
    """ % ('.'.join(map(str, internal.cheshireVersion)))
    resp.extraResponseData.append(r.fromString(txt))

def docidRecordHandler(req, ro, other):
    # Put the record identifier into extraRecordData
    txt = '<docid:recordIdentifier xmlns:docid="info:srw/extensions/2/docid-v1.0">%s</docid:recordIdentifier>' % escape(str(other))
    ro.extraRecordData.append(r.fromString(txt))
