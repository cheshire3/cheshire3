"""Command line utilities for Cheshire3 Command-line UI."""

from __future__ import absolute_import

import sys
import os

# Manipulate sys.path to eliminate possibility of local imports
# i.e. local import of cheshire3.py will block import of cheshire3 package
sys.path.pop(0)

from argparse import ArgumentParser
from lxml import etree

from cheshire3.internal import cheshire3Root
from cheshire3.bootstrap import BootstrapDocument, BSLxmlParser


class Cheshire3ArgumentParser(ArgumentParser):
    
    def __init__(self, *args, **kwargs):
        ArgumentParser.__init__(self, *args, **kwargs)
        defaultConfig = os.path.join(cheshire3Root,
                                     'configs',
                                     'serverConfig.xml')
        self.add_argument('-s', '--server-config', type=str, 
                          action='store', dest='serverconfig',
                          default=defaultConfig, metavar='PATH', 
                          help=("path to Cheshire3 server configuration "
                                "file. default: {0}".format(defaultConfig))
                          )
        
    def parse_args(self, args=None, namespace=None):
        args = ArgumentParser.parse_args(self, args, namespace)
        # Expand server config file path
        args.serverconfig = os.path.abspath(
                                os.path.expanduser(args.serverconfig)
                            )
        return args


def identify_database(session, cwd):
    """Identify and return identifier of current database.
    
    Walk up directories looking for a .cheshire3 directory or config.xml file.
    Raise an error if current working directory is not part of a Cheshire3 
    database.
    """
    # Establish upper boundary directory beyond which we shouldn't look 
    boundary = os.path.abspath(os.path.expanduser('~'))
    out_of_bounds_msg = """\
Current working directory is not part of a Cheshire3 database.
Refusing to look any further up the directory tree than: {0}
Please provide a database identifier using the --database option.
""".format(boundary)
    while True:
        if (cwd == os.path.split(boundary)[0] or
            len(cwd) < len(boundary)):
            raise EnvironmentError(out_of_bounds_msg)
        c3_dir = os.path.join(cwd, '.cheshire3')
        if os.path.exists(c3_dir) and os.path.isdir(c3_dir):
            conf_file_path = os.path.join(c3_dir, 'config.xml')
        else:
            # No .cheshire3 directory - maybe old-style database
            conf_file_path = os.path.join(cwd, 'config.xml')
        try:
            with open(conf_file_path, 'r') as cfh:
                doc = BootstrapDocument(cfh)
                record = BSLxmlParser.process_document(session, doc)
        except IOError:
            try:
                cwd, foo = os.path.split(cwd)
            except:
                raise EnvironmentError(out_of_bounds_msg)
            else:
                del foo
        else:
            dom = record.get_dom(session)
            dbid = dom.attrib['id']
            return dbid
