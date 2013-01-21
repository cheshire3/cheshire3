"""Setup file for cheshire3 package."""
from __future__ import with_statement

import sys
import os
import inspect

from warnings import warn

# Import Distribute / Setuptools
import distribute_setup
distribute_setup.use_setuptools()
from setuptools import setup, find_packages
from pkg_resources import DistributionNotFound

# Check Python version
py_version = getattr(sys, 'version_info', (0, 0, 0))

if py_version < (2, 6):
    warn("Cheshire3 requires Python 2.6 or later; some code may be "
         "incompatible with earlier versions.")

# Inspect to find current path
setuppath = inspect.getfile(inspect.currentframe())
setupdir = os.path.dirname(setuppath)

# Basic information
_name = 'cheshire3'
_description = ('Cheshire3 Search and Retrieval Engine and Information '
                'Framework')
# Discover version number
vfn = 'VERSION.txt'
try:
    # Try to import version number from cheshire3.internal
    from cheshire3.internal import cheshire3Version
except (ImportError, DistributionNotFound):
    # Missing dependencies, e.g. source distribution
    # Read from version file instead    
    with open(os.path.join(setupdir, vfn), 'r') as vfh:
        _version = vfh.read()
else:
    # Turn version tuple into a string
    _version = '.'.join(map(str, cheshire3Version))
    # Write version number to file for source distributions
    with open(os.path.join(setupdir, vfn), 'w') as vfh:
        vfh.write(_version)

_download_url = ('http://download.cheshire3.org/{0}/src/{1}-{2}.tar.gz'
                 ''.format(_version[:3], _name, _version))

# More detailed description from README

try:
    fh = open(os.path.join(setupdir, 'README.rst'), 'r')
except IOError:
    _long_description = ''
else:
    _long_description = fh.read()
    fh.close()

# Requirements
_install_requires = ['lxml >= 2.1', 'zopyx.txng3.ext >= 3.3.1']
# Determine python-dateutil version
if py_version < (3, 0):
    dateutilstr = 'python-dateutil == 1.5'
else:
    'python-dateutil >= 2.0'
_install_requires.append(dateutilstr)
if py_version < (2, 7):
    _install_requires.append('argparse')
    _install_requires.append('unittest2')


setup(
    name=_name,
    version=_version,
    packages=[_name],
    include_package_data=True,
    package_data={'cheshire3': ['configs/*.xml', 'configs/extra/*.xml']},
    exclude_package_data={'': ['README.*', '.gitignore']},
    requires=['lxml(>=2.1)', 'bsddb', 'dateutil', 'argparse'],
    install_requires=_install_requires,
    setup_requires=['setuptools-git'],
    dependency_links=[
        "http://labix.org/python-dateutil"
    ],
    extras_require={
        'graph': ['rdflib'],
        'lucene': ['lucene'],
        'sql': ['PyGreSQL >= 3.8.1'],
        'web': ['PyZ3950 >= 2.04']
    },
    test_suite="cheshire3.test.testAll",
    scripts=['scripts/DocumentConverter.py'],
    entry_points={
        'console_scripts': [
            'cheshire3 = cheshire3.commands.cheshire3_console:main',
            'cheshire3-init = cheshire3.commands.cheshire3_init:main',
            'cheshire3-load = cheshire3.commands.cheshire3_load:main',
            'cheshire3-register = cheshire3.commands.cheshire3_register:main',
            'cheshire3-search = cheshire3.commands.cheshire3_search:main',
            'cheshire3-serve = cheshire3.commands.cheshire3_serve:main'
        ],
    },
    keywords="xml document search information retrieval engine data text",
    description=_description,
    long_description=_long_description,
    author="Rob Sanderson, et al.",
    author_email="azaroth@liv.ac.uk",
    maintainer='John Harrison',
    maintainer_email='john.harrison@liv.ac.uk',
    license="BSD",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: Z39.50",
        "Topic :: Text Processing :: Indexing",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Text Processing :: Markup"
    ],
    url="http://www.cheshire3.org/",
    download_url=_download_url
)
