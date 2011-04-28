
import sys
import urllib
import datetime

from lxml import etree

from cheshire3.record import LxmlRecord
# cheshire3.web package
from cheshire3.web.www_utils import cgi_encode
from cheshire3.web.sru_utils import fetch_data
# oaipmh package
from oaipmh.common import Header

NS_OAIPMH = 'http://www.openarchives.org/OAI/2.0/'
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
NS_OAIDC = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
NS_DC = "http://purl.org/dc/elements/1.1/"

nsmap = {
    None: NS_OAIPMH,
    'xsi': NS_XSI,
    'oai_dc': NS_OAIDC,
    'dc': NS_DC
    }


def headerFromLxmlElement(et):
    identifier = et.xpath('string(//oai:identifier)', namespaces={'oai': NS_OAIPMH})
    datestamp = et.xpath('string(//oai:datestamp)', namespaces={'oai': NS_OAIPMH})
    datestamp = datetime.datetime.strptime(datestamp, '%Y-%m-%dT%H:%M:%SZ')
    return Header(identifier, datestamp, [], None)


def getRecord(baseUrl, metadataPrefix, identifier):
    """Return (Header, metadata, about) tuple of record with specified identifier from the specified OAI-PMH server."""
    args = {'verb': "GetRecord",
            'metadataPrefix': metadataPrefix,
            'identifier': identifier}
    params = urllib.urlencode(args)
    url = "{0}?{1}".format(baseUrl, params)
    data = fetch_data(url)
    try:
        tree = etree.fromstring(data)
    except:
        sys.stderr.write(url + '\n')
        sys.stderr.write(data + '\n')
        sys.stderr.flush()
        raise
    hEl = tree.xpath('//oai:record[1]/oai:header', namespaces={'oai': NS_OAIPMH})[0]
    header = headerFromLxmlElement(hEl)
    recEl = tree.xpath('//oai:record[1]/oai:metadata/*', namespaces={'oai': NS_OAIPMH})[0]
    recString = etree.tostring(recEl)
    rec = LxmlRecord(recEl, xml=recString, docId=identifier, byteCount=len(recString))
    return (header, rec, None)


def listIdentifiers(baseUrl, metadataPrefix, set=None, from_=None, until=None, cursor=0, batch_size=10):
    """Return a list of Headers with the given parameters from the specified OAI-PMH server."""
    args = {'verb': "ListIdentifiers",
            'metadataPrefix': metadataPrefix
            }
    if set is not None:
        args['set'] = set
    if from_ is not None:
        args['from'] = str(from_)
    if until is not None:
        args['until'] = str(until)
    params = urllib.urlencode(args)
    url = "{0}?{1}".format(baseUrl, params)
    data = fetch_data(url)
    headers = []
    while data is not None:
        try:
            tree = etree.fromstring(data)
        except:
            sys.stderr.write(url + '\n')
            sys.stderr.write(data + '\n')
            sys.stderr.flush()
            raise
        for h in tree.xpath('//oai:header', namespaces={'oai': NS_OAIPMH}):
            headers.append(headerFromLxmlElement(h))
            
        resTok = tree.xpath('string(//oai:resumptionToken)', namespaces={'oai': NS_OAIPMH})
        if resTok:
            params = urllib.urlencode({'verb': "ListIdentifiers",
                                       'resumptionToken': resTok})
            url = "{0}?{1}".format(baseUrl, params)
            data = fetch_data(url)
        else:
            break
    return headers


def listRecords(baseUrl, metadataPrefix, set=None, from_=None, until=None, cursor=0, batch_size=10):
    """Return a list of (Header, metadata, about) tuples for records which match the given parameters from the specified OAI-PMH server."""
    args = {'verb': "ListRecords",
            'metadataPrefix': metadataPrefix
            }
    if set is not None:
        args['set'] = set
    if from_ is not None:
        args['from'] = str(from_)
    if until is not None:
        args['until'] = str(until)
    params = urllib.urlencode(args)
    url = "{0}?{1}".format(baseUrl, params)
    data = fetch_data(url)
    records = []
    i = 0
    while (data is not None):
        try:
            tree = etree.fromstring(data)
        except:
            print url
            print data
            raise
        for recEl in tree.xpath('//oai:record', namespaces={'oai': NS_OAIPMH}):
            if i < cursor:
                i+=1
                continue
            hEl = recEl.xpath('//oai:header', namespaces={'oai': NS_OAIPMH})[0]
            header = headerFromLxmlElement(hEl)
            mdEl = recEl.xpath('//oai:metadata/*', namespaces={'oai': NS_OAIPMH})[0]
            recString = etree.tostring(mdEl)
            rec = LxmlRecord(mdEl, xml=recString, docId=header.identifier(), byteCount=len(recString))
            records.append((header, rec, None))
            i+=1
            if (len(headers) >= batch_size):
                return headers
            
        resTok = tree.xpath('string(//oai:resumptionToken)', namespaces={'oai': NS_OAIPMH})
        if resTok:
            data = fetch_data(url + '&resumptionToken=' + cgi_encode(resTok))
        else:
            break

    return records