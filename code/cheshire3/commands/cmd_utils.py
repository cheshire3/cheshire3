"""Command line utilities for Cheshire3 Command-line UI."""

from __future__ import absolute_import

import sys
import os

# Manipulate sys.path to eliminate possibility of local imports
# i.e. local import of cheshire3.py will block import of cheshire3 package
sys.path.pop(0)

from argparse import ArgumentParser

from cheshire3.internal import cheshire3Root

class Cheshire3ArgumentParser(ArgumentParser):
    
    def __init__(self, *args, **kwargs):
        ArgumentParser.__init__(self, *args, **kwargs)
        defaultConfig = os.path.join(cheshire3Root,
                                     'configs',
                                     'serverConfig.xml')
        self.add_argument('-s', '--server-config', type=str, 
                          action='store', dest='serverconfig',
                          default=defaultConfig, metavar='PATH', 
                          help="path to Cheshire3 server configuration file. default: {0}".format(defaultConfig))
        self.add_argument('-d', '--database', type=str,
                          action='store', dest='database',
                          default=None, metavar='DATABASE',
                          help="identifier of Cheshire3 database")
        
        
    def parse_args(self, args=None, namespace=None):
        args = ArgumentParser.parse_args(self, args, namespace)
        # Expand server config file path
        args.serverconfig = os.path.abspath(os.path.expanduser(args.serverconfig))
        return args
    
