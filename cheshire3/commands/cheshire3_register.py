"""Register a Cheshire3 configuration.

Register a configuration for a Cheshire3 object (most common use case
will be a Database) with the server.

This process simply tells the server that it should include the
configuration(s) in your file - it doesn't ingest your file - so you
don't need to re-register any time you make changes.
"""

from __future__ import with_statement

import sys
import os

from lxml import etree
from lxml.builder import ElementMaker

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.internal import cheshire3Root, CONFIG_NS
from cheshire3.bootstrap import BSLxmlParser, BootstrapDocument
from cheshire3.exceptions import ObjectDoesNotExistException
from cheshire3.exceptions import ConfigFileException
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def main(argv=None):
    """Register an object with the Cheshire3 Server."""
    global argparser, session, server
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    session = Session()
    server = SimpleServer(session, args.serverconfig)
    # Make path to configfile absolute
    args.configfile = os.path.abspath(os.path.expanduser(args.configfile))
    # Read in proposed config file
    with open(args.configfile, 'r') as fh:
        confdoc = BootstrapDocument(fh)
        # Check it's parsable
        try:
            confrec = BSLxmlParser.process_document(session, confdoc)
        except etree.XMLSyntaxError as e:
            msg = ("Config file {0} is not well-formed and valid XML: "
                   "{1}".format(args.configfile, e.message))
            server.log_critical(session, msg)
            raise ConfigFileException(msg)
    # Extract the database identifier
    confdom = confrec.get_dom(session)
    dbid = confdom.attrib.get('id', None)
    if dbid is None:
        msg = ("Config file {0} must have an 'id' attribute at the top-level"
               "".format(args.configfile))
        server.log_critical(session, msg)
        raise ConfigFileException(msg)
    # Check that the identifier is not already in use by an existing database
    try:
        server.get_object(session, dbid)
    except ObjectDoesNotExistException:
        # Doesn't exists, so OK to init it
        pass
    else:
        # TODO: check for --force ?
        msg = ("Database with id '{0}' is already registered. "
               "Please specify a different id in your configurations "
               "file.".format(dbid))
        server.log_critical(session, msg)
        raise ConfigFileException(msg)
    
    # Insert database into server configuration
    pathEl = E.path({'type': "database",
                     'id': dbid},
                    args.configfile
             )
    # Try to do this by writing config plugin file if possible
    serverDefaultPath = server.get_path(session,
                                        'defaultPath',
                                        cheshire3Root)
    includesPath = os.path.join(serverDefaultPath,
                                'configs',
                                'databases')
    if os.path.exists(includesPath) and os.path.isdir(includesPath):
        plugin = E.config(
                     E.subConfigs(
                         pathEl
                     )
                 )
        pluginpath = os.path.join(includesPath, '{0}.xml'.format(dbid))
        with open(pluginpath, 'w') as pluginfh:
            pluginfh.write(etree.tostring(plugin,
                                          pretty_print=True,
                                          encoding="utf-8"))
    else:
        # No database plugin directory
        server.log_warning(session, "No database plugin directory")
        raise ValueError("No database plugin directory")
    server.log_info(session,
                    "Database configured in {0} registerd with Cheshire3 "
                    "Server configured in {1}".format(args.configfile,
                                                      args.serverconfig))
    return 0
        

argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0])

argparser.add_argument('configfile', type=str,
                       action='store', nargs='?',
                       default=os.path.join(os.getcwd(), 'config.xml'),
                       metavar='CONFIGFILE',
                       help=("path to configuration file for the database to "
                             "register with the Cheshire3 server. Default: "
                             "config.xml"))

# Set up ElementMaker for Cheshire3 config namespace
E = ElementMaker(namespace=CONFIG_NS, nsmap={None: CONFIG_NS})

session = None
server = None

if __name__ == '__main__':
    sys.exit(main())
