"""Interact with Cheshire3."""

import sys
import os
try:
    import readline
except ImportError:
    # Gracefully degrade command line UX
    pass

from code import InteractiveConsole

from cheshire3.internal import cheshire3Version
from cheshire3.commands.cmd_utils import Cheshire3ArgumentParser, \
                                         identify_database
from cheshire3.licensing import cheshire3_license, cheshire3_license_text,\
                                marc_utils_license


class Cheshire3Console(InteractiveConsole):
    """Cheshire3 Interactive Console."""

    def __init__(self, args, locals_=None, filename="<console>"):
        InteractiveConsole.__init__(self, locals_, filename)
        # Standard Cheshire3 initialization code
        init_code_lines = [
           'from cheshire3.session import Session',
           'from cheshire3.server import SimpleServer',
           'from cheshire3.exceptions import *',
           'session = Session()',
           'server = SimpleServer(session, "{0}")'.format(args.serverconfig),
        ]
        # Seed console with standard initialization code
        for line in init_code_lines:
            self.push(line)

    def push(self, line):
        if line.strip() == 'help':
            # Write some Cheshire3 help
            self.write("Cheshire3 Documentation can be found in the `docs` "
                       "folder of the distribution\n"
                       "or online at:\n"
                       "http://cheshire3.org/docs/\n")
            self.write("Type help() for Python's interactive help, or "
                       "help(object) for help about object.\n")
            return
        elif line.strip() == 'copyright':
            # Write Cheshire3 copyright info, before that of Python
            self.write('Cheshire3 is Copyright (c) 2005-2012, the University '
                       'of Liverpool.\n')
            self.write('All rights reserved.\n\n')
        elif line.strip() == "license":
            self.write(cheshire3_license() + '\n\n')
            self.write("Type marc_utils_license() for marc_utils license\n")
            self.write("Type python_license() for Python license\n")
        elif line.strip() == "license()":
            self.write(cheshire3_license_text() + '\n')
            return
        elif line.strip() == "marc_utils_license()":
            self.write(marc_utils_license() + '\n')
            return
        elif line.strip() == "python_license()":
            return InteractiveConsole.push(self, "license()")
        return InteractiveConsole.push(self, line)

    def interact(self, banner=None):
        """Emulate the standard interactive Python console.

        The optional banner argument specify the banner to print
        before the first interaction; by default it prints a banner
        similar to the one printed by the real Python interpreter.
        """
        if banner is None:
            c3_version = '.'.join([str(p) for p in cheshire3Version])
            banner = ("\n".join(["Python {0} on {1}"
                                 "".format(sys.version, sys.platform),
                                 "Cheshire3 {0} Interactive Console"
                                 "".format(c3_version),
                                 'Type "help", "copyright", "credits" or '
                                 '"license" for more information.']))
        return InteractiveConsole.interact(self, banner)


def main(argv=None):
    """Main method for cheshire3 command."""
    global argparser, session, server, db
    if argv is None:
        args = argparser.parse_args()
    else:
        args = argparser.parse_args(argv)
    console = Cheshire3Console(args)
    if args.database is not None:
        dbid = args.database
    else:
        # Inspect context
        try:
            dbid = identify_database(session, os.getcwd())
        except EnvironmentError as e:
            dbid = None

    if dbid is not None:
        dbline = 'db = server.get_object(session, "{0}")'.format(dbid)
        console.push(dbline)
        # Try to get main recordStore
        recordStoreLines = [
            "try:",
            "    recordStore = db.get_object(session, 'recordStore')",
            "except ObjectDoesNotExistException:",
            "    recordStore = db.get_path(session, 'recordStore')",
            "",
        ]
        for line in recordStoreLines:
            console.push(line)

    if args.script is not None:
        with open(args.script, 'r') as fh:
            retval = console.runsource(fh.read(), args.script)
            if not args.interactive:
                return retval
            console.resetbuffer()
            banner = ''
    else:
        banner = None
    console.interact(banner)
    return 0


argparser = Cheshire3ArgumentParser(conflict_handler='resolve',
                                    description=__doc__.splitlines()[0])
argparser.add_argument('-d', '--database', type=str,
                       action='store', dest='database',
                       default=None, metavar='DATABASE',
                       help="identifier of Cheshire3 database")
argparser.add_argument('script', type=str,
                       action='store', nargs='?',
                       default=None,
                       help="read and execute commands from script file")
argparser.add_argument('-i', '--interactive',
                       action="store_true", dest="interactive", default=False,
                       help=("drop into interactive console after running "
                             "script; if no script is provided, interactive "
                             "mode is the default"))

session = None
server = None
db = None

if __name__ == '__main__':
    main(sys.argv)
