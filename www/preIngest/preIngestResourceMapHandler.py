
from mod_python import apache
from mod_python.util import FieldStorage
import urlparse, httplib
import cgitb

import os, re, sys

import simplejson as json
from rdflib import ConjunctiveGraph, URIRef, StringInputSource
import uuid
from foresite import *

remMimeTypes = ['application/atom+xml', 'application/rdf+xml', 'text/rdf+n3', 'application/x-turtle', 'text/plain']

parser = RdfLibParser()
atomp = AtomParser()
rdfap = RdfAParser()

url_Resource_Map_XML_File = 'cur_Resource_Map_XML_File.xml';


def gen_uuid():
    return str(uuid.uuid4())

class Handler(object):

    def __init__(self):
        # load up our ORE/RDF graph
        self.graph_ORE_RDF = ConjunctiveGraph()
        os.chdir('/home/cheshire/cheshire3/www/preIngest')
        f1 = file(url_Resource_Map_XML_File)
        data1 = f1.read()
        f1.close()
        self.graph_ORE_RDF.parse(StringInputSource(data1))       
      
        self.linkre = re.compile("<(.+?)>;?")
        self.relre = re.compile('rel\s?=\s?"?(resourcemap|aggregation)(["; ]|$)?')

    def send(self, data, req, code=200, ct="text/xml"):
        req.content_type = ct
        req.content_length = len(data)
        req.send_http_header()
        if type(data) == unicode:
            req.write(data.encode('utf-8'))
        else:
            req.write(data)
            
    def process(self, req):
        if req.uri.find('/Write/') != -1:
            data = self.write_DOM_ORE_ResourceMap(req)
        elif req.uri.find('/Read/') != -1:
            data = self.read_DOM_ORE_ResourceMap()
        else:
            data = 'error: uri not recognised 2'

        self.send(data, req, ct='text/plain')

    

    def read_DOM_ORE_ResourceMap(self):
        f1 = open(url_Resource_Map_XML_File, 'r')
        xmlData = f1.read()
        f1.close()

        return xmlData

    def write_DOM_ORE_ResourceMap(self, req):
        f1 = open(url_Resource_Map_XML_File, 'w')
        f2 = req.getfile()
        os.write(f1, f2.read())
        f1.close()
        f2.close()
        return 1
        

hdlr = Handler()

def handler(req):
    try:
        sys.stderr.write('called python\n')
        sys.stderr.flush()
        hdlr.process(req)
    except:
        req.content_type = "text/html"
        cgitb.Hook(file=req).handle()
    return apache.OK
    
