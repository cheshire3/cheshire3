

# --- require print() and make all strings unicodes
#from __future__ import print_function
#from __future__ import unicode_literals

import sys, os

# Tests for Python 3.0 incompatibility
#sys.py3kwarning = True

# Ignore md5 DeprecationWarning from PyZ3950.yacc
from warnings import filterwarnings
filterwarnings('ignore', 'the md5 module is deprecated; use hashlib instead',  DeprecationWarning, 'yacc')

home = os.environ.get("C3HOME")

__name__ = "cheshire3"
__package__ = "cheshire3"

__all__ = ['cqlParser', 'database', 'document', 'documentFactory', 'documentStore',
           'exceptions', 'extractor', 'index', 'indexStore', 'internal', 'logger', 
           'normalizer', 'objectStore', 'parser', 'permissionsHandler', 'preParser', 'protocolMap', 
           'queryFactory', 'queryStore', 'record', 'recordStore', 'resultSet', 'resultSetStore',
           'selector', 'server', 'session', 'tokenizer', 'tokenMerger', 'transformer', 'user',
           'utils', 'workflow', 'xpathProcessor']


# Check for user-specific Cheshire3 server directory
_user_cheshire3_dir = os.path.expanduser('~/.cheshire3-server') 
if not os.path.exists(_user_cheshire3_dir):
    # Create it and sub-dirs for:
    # Database plugins
    os.makedirs(os.path.join(_user_cheshire3_dir, 'configs', 'databases'))
    # Server-level default stores
    os.makedirs(os.path.join(_user_cheshire3_dir, 'stores'))
    # Server-level logs
    os.makedirs(os.path.join(_user_cheshire3_dir, 'logs'))


import cheshire3.internal
# sps = cheshire3.internal.get_subpackages()

sps= ['web', 'formats']

for sp in sps:
    # call import for on init hooks
    try:
        __import__("cheshire3.%s" % sp)
    except:
        pass
           
