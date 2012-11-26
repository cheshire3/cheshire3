"""Start a demo server to expose Cheshire3 databases via SRU.

Start an HTTP server to expose Cheshire3 databases via the SRU protocol for 
development and demonstration purposes.

For production use it would be advisable to deploy the SRU server application 
via a production ready WSGI server or framework (e.g. CherryPy, mod_wsgi etc.) 
"""

import socket

from wsgiref.simple_server import make_server

from cheshire3.server import SimpleServer
from cheshire3.session import Session
from cheshire3.web.sruWsgi import SRUWsgiHandler
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser


def main(argv=None):
    """Start up a simple app server to serve the SRU application."""
    global argparser, session, server
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    session = Session()
    server = SimpleServer(session, args.serverconfig)
    application = SRUWsgiHandler()
    try:
        httpd = make_server(args.hostname, args.port, application)
    except socket.error:
        print ""
    else:
        print """You will be able to access the application at:
    http://{0}:{1}""".format(args.hostname, args.port)
        httpd.serve_forever()

try:
    hostname = socket.gethostname()
except:
    hostname = 'localhost'

argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0])
argparser.add_argument('--hostname', type=str,
                  action='store', dest='hostname',
                  default=hostname, metavar='HOSTNAME',
                  help=("name of host to listen on. default derived by "
                        "inspection of local system"))
argparser.add_argument('-p', '--port', type=int,
                  action='store', dest='port',
                  default=8000, metavar='PORT',
                  help="number of port to listen on. default: 8000")


session = None
server = None


if __name__ == '__main__':
    main()
