"""Start a demo server to expose Cheshire3 databases via SRU etc.

Start an HTTP server to expose Cheshire3 databases via SRU, OAI-PMH (and maybe
more in future) protocols for development and demonstration purposes.

The current implementation uses Paste.
"""
import sys
import socket
import signal
import webbrowser

import paste.httpserver
from paste.urlmap import URLMap
from paste.urlparser import make_pkg_resources

from cheshire3.server import SimpleServer
from cheshire3.session import Session

from cheshire3.web.sruWsgi import SRUWsgiHandler, get_configsFromServer
from cheshire3.web.oaipmhWsgi import OAIPMHWsgiApplication
from cheshire3.web.oaipmhWsgi import get_databasesAndConfigs
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def main(argv=None):
    """Start up a CherryPy server to serve the SRU, OAI-PMH applications."""
    global argparser, c3_session, c3_server
    global sru_app, oaipmh_app  # WSGI Apps
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    c3_session = Session()
    c3_server = SimpleServer(c3_session, args.serverconfig)
    # Init SRU App
    sru_configs = get_configsFromServer(c3_session, c3_server)
    sru_app = SRUWsgiHandler(c3_session, sru_configs)
    # Init OAI-PMH App
    dbs, oaipmh_configs = get_databasesAndConfigs(c3_session, c3_server)
    oaipmh_app = OAIPMHWsgiApplication(c3_session, oaipmh_configs, dbs)
    # Mount various Apps and static directories
    urlmap = URLMap()
    urlmap['/docs'] = make_pkg_resources(None, 'cheshire3', 'docs/build/html')
    urlmap['/api/sru'] = sru_app
    urlmap['/api/oaipmh/2.0'] = oaipmh_app
    url = "http://{0}:{1}/".format(args.hostname, args.port)
    if args.browser:
        webbrowser.open(url)
        print ("Hopefully a new browser window/tab should have opened "
               "displaying the application.")
    paste.httpserver.serve(urlmap,
                           host=args.hostname,
                           port=args.port,
                           )


argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0])
argparser.add_argument('--hostname', type=str,
                       action='store', dest='hostname',
                       default='127.0.0.1', metavar='HOSTNAME',
                       help=("name of host to listen on. default derived by "
                             "inspection of local system")
                       )
argparser.add_argument('-p', '--port', type=int,
                       action='store', dest='port',
                       default=8000, metavar='PORT',
                       help="number of port to listen on. default: 8000"
                       )
argparser.add_argument('--browser',
                       action='store_true', dest='browser',
                       help=("open a browser window/tab containing the app.")
                       )

c3_session = None
c3_server = None


if __name__ == '__main__':
    main()
