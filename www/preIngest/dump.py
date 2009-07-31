#!/Users/cheshire3/install/bin/python -i

import sys, os, time, re
import pprint

import lxml
from lxml import etree

import string

from types import *

class dump:

    out = None
    varTypes = [NoneType, TypeType, BooleanType, IntType, LongType, FloatType,
		ComplexType, StringType, UnicodeType, DictType, TupleType, ListType]

    def __init__(self, out = sys.stdout):
	self.out = out

    def list(self, name, obj, indent = 0, dir = False, basic = False):
	lead = ' ' * indent
	self.out.write('%s%s (%d):\n' % (lead, name, len(obj)))
	i = 1;
	for o in obj:
	    print '%s    %3d: %s' % (lead, i, o)
	    if (dir):
		var(i, o, indent + 4, basic)
	    i += 1

    def iter(slef, obj):
	prefix = '<<'
	for x in obj:
	    self.out.write(prefix + ' ' + str(obj))
	    prefix = ','
	self.out.write('>>\n')

    def xmlToString(self, xml, indent = 0):
	xmlStr = etree.tostring(xml, pretty_print=True).strip()
	lines = xmlStr.split('\n')
	if (len(lines) > 1):
	    closing = lines[len(lines) - 1]
	    lt = closing.find('<')
	    spaces = closing[0:lt]
	    xmlStr = re.sub(re.compile('^' + spaces, re.MULTILINE), '', xmlStr)
	if (indent > 0):
	    xmlStr = re.sub(re.compile('^', re.MULTILINE), ' ' * indent, xmlStr)
	return xmlStr

    def _dumpList(self, name, list, prefix):
	    outStr = ''
	    pre = ':'
	    for m in list:
		outStr += pre + ' ' + m
		pre = ','
	    self.out.write(prefix)
	    self.out.write(name)
	    self.out.write(outStr)
	    self.out.write('\n')

    def var(self, name, obj, indent = 0, basic = False):
	prefix = ''
	if (indent > 0):
	    prefix = ' ' * indent

	try:
	    self.out.write('\n')
	    self.out.write('%s{ %s: %s: %s [%s]\n' % (prefix, name, obj, type(obj), id(obj)))

	    if (not basic):
		t = type(obj)
		if (t == lxml.etree._Element):
		    self.out.write(self.xmlToString(obj, indent=indent + 4))
		    self.out.write('\n')
		    return
		elif (t in self.varTypes):
		    pp = pprint.PrettyPrinter(indent=indent + 4)
		    self.out.write(' ' * (indent + 4))
		    self.out.write(pp.pformat(obj))
		    self.out.write('\n')
		    return

	    subPrefix = prefix + ' ' * 4
	    methods = ()
	    functions = ()
	    pp = pprint.PrettyPrinter(indent=indent + 8)
	    for field in dir(obj):
		if not field.startswith('_'):
		    val = getattr(obj, field)
		    t = type(val)
		    if (t == MethodType):
			methods += field,
		    elif (t in [FunctionType, LambdaType]):
			functions += field,
		    else:
			self.out.write('%s%s = ' % (subPrefix, field))
			if (not basic and type(obj) == lxml.etree._Element):
			    self.out.write('\n')
			    self.out.write(self.xmlToString(val))
			else:
			    self.out.write(pp.pformat(val))
			    self.out.write('\n')
	    self._dumpList('<methods>', methods, subPrefix)
	    self._dumpList('<functions>', functions, subPrefix)
	finally:
	    self.out.write('%s} // %s\n' % (prefix, name))
