

# --- require print() and make all strings unicodes
#from __future__ import print_function
#from __future__ import unicode_literals

import sys, os

# Tests for Python 3.0 incompatibility
#sys.py3kwarning = True

# Ignore md5 DeprecationWarning from PyZ3950.yacc
from warnings import filterwarnings
filterwarnings('ignore', 'the md5 module is deprecated; use hashlib instead',  DeprecationWarning, 'yacc')

# Hack to allow us to patch a module in a different directory
import __builtin__

home = os.environ.get("C3HOME")
if home:
    C3MODULEPATH=os.path.join(home, "cheshire3", "code")
else:
    C3MODULEPATH = '/home/cheshire/cheshire3/code'
builtin_importer = __builtin__.__import__

def patch(enable=True):

    if enable:
        def import_module(name, globals = None, locals = None, fromlist = None, *args, **kw):

            if name[:10] == "cheshire3.":
                # try to import from code first
                sys.path.insert(1, C3MODULEPATH)
                try:
                    oname = "c3patch.%s" % name[10:]            
                    m =  builtin_importer(oname, globals,locals, fromlist)
                    return m
                except ImportError:
                    sys.path.pop(1)
                    m = builtin_importer(name, globals, locals, fromlist)
                    return m
                sys.path.pop(1)
                return m            
            else:
                return builtin_importer(name, globals, locals, fromlist)

        __builtin__.__import__ = import_module
    else:
        __builtin__.__import__ = builtin_importer




__name__ = "cheshire3"
__package__ = "cheshire3"

__all__ = ['database', 'documentFactory', 'document', 'exceptions',
           'documentStore', 'extractor', 'index', 'indexStore', 'logger',
           'normalizer', 'objectStore', 'parser', 'preParser',
           'protocolMap', 'record', 'recordStore', 'resultSet', 'resultSetStore',
           'server', 'sqlite', 'tokenizer', 'tokenMerger', 'transformer', 'user',
           'workflow', 'xpathProcessor']


import cheshire3.internal
sps = cheshire3.internal.get_subpackages()

sps= ['web']
for sp in sps:
    # call import for on init hooks
    try:
        __import__("cheshire3.%s" % sp)
    except:
        raise
           
