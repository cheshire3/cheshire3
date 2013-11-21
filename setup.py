"""Setup file for cheshire3 package."""
from __future__ import with_statement

import sys
import os
import inspect

from warnings import warn

# Import Distribute / Setuptools
from ez_setup import use_setuptools
use_setuptools()

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
# Discover version number from file    
with open(os.path.join(setupdir, 'VERSION.txt'), 'r') as vfh:
    _version = vfh.read().strip()

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
with open(os.path.join(setupdir, 'requirements.txt'), 'r') as fh:
    _install_requires = fh.readlines()
_tests_require = []
# Determine python-dateutil version
if py_version < (3, 0):
    dateutilstr = 'python-dateutil == 1.5'
    if py_version < (2, 7):
        _install_requires.append('argparse')
        _tests_require.append('unittest2')
else:
    dateutilstr = 'python-dateutil >= 2.0'

_install_requires.append(dateutilstr)


setup(
    name=_name,
    version=_version,
    packages=[_name],
    include_package_data=True,
    package_data={'cheshire3': ['configs/*.xml', 'configs/extra/*.xml']},
    exclude_package_data={'': ['README.*', '.gitignore']},
    requires=['lxml(>=2.1)', 'bsddb', 'dateutil', 'argparse'],
    tests_require=_tests_require,
    install_requires=_install_requires,
    setup_requires=['setuptools-git'],
    dependency_links=[
        "http://labix.org/python-dateutil",
        "http://www.panix.com/~asl2/software/PyZ3950/",
        "http://download.cheshire3.org/latest/reqs/"
    ],
    extras_require={
        'graph': ['rdflib'],
        'grid': ['PyRods'],
        'datamining': ['svm'],
        'lucene': ['lucene'],
        'sql': ['psycopg2 >= 2.5'],
        'textmining': ['numpy', 'nltk >= 2.0'],
        'web': ['pyoai', 'PyZ3950 >= 2.04', 'ZSI < 2.0']
    },
    test_suite="cheshire3.test.testAll.suite",
    scripts=['scripts/DocumentConverter.py'],
    entry_points={
        'console_scripts': [
            'cheshire3 = cheshire3.commands.console:main',
            'cheshire3-init = cheshire3.commands.init:main',
            'cheshire3-load = cheshire3.commands.load:main',
            'cheshire3-register = cheshire3.commands.register:main',
            'cheshire3-search = cheshire3.commands.search:main',
            'cheshire3-serve = cheshire3.commands.serve:main',
            'icheshire3-load = cheshire3.grid.commands.load:main [grid]'
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
