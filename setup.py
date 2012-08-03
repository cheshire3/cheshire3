# Setup file for cheshire3 package

import sys
import os
import inspect

from warnings import warn

# Import Distribute / Setuptools
import distribute_setup
distribute_setup.use_setuptools()
from setuptools import setup, find_packages

# Check Python version
py_version = getattr(sys, 'version_info', (0, 0, 0))

if py_version < (2, 6):
    warn("Cheshire3 requires Python 2.6 or later; some code may be "
         "incompatible with earlier versions.")

# Basic information
_name = 'cheshire3'
_version = '1.0.0c3'
_description = ('Cheshire3 Search and Retrieval Engine and Information '
                'Framework')
_download_url = ('http://www.cheshire3.org/download/{0}/src/{1}-{2}.tar.gz'
                 ''.format(_version[:5], _name, _version))

# More detailed description from README.mdown
# Inspect to find current path
setuppath = inspect.getfile(inspect.currentframe())
setupdir = os.path.dirname(setuppath)
# Read any necessary bits from README.mdown
try:
    fh = open(os.path.join(setupdir, 'README.mdown'), 'r')
except IOError:
    _long_description = ''
else:
    fstr = fh.read()
    fh.close()
    # Long Description
    desc_st_str = '''\
Description
-----------'''
    desc_end_str = '''\
Authors
-------'''
    desc_st = fstr.find(desc_st_str) + len(desc_st_str) + 1
    desc_end = fstr.find(desc_end_str) - 1
    _long_description = fstr[desc_st:desc_end]
    # Process any further sections here
    # Delete file contents from memory
    del fstr

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
    packages=find_packages('code'),
    package_dir={'': 'code'},
    include_package_data=True,
    exclude_package_data={'': ['README.mdown']},
    data_files=[('configs',
                 ['configs/authStore.xml', 'configs/basicConfigs.xml',
                  'configs/configStore.xml', 'configs/serverConfig.xml',
                  'configs/workflow.xml', 'configs/zserver.xml',
                  'configs/extra/datamining.xml', 'configs/extra/formats.xml',
                  'configs/extra/graph.xml', 'configs/extra/textmining.xml',
                  'configs/extra/web.xml']
                ),
                ('dbs', ['dbs/configs.d']),
                ('www', ['www']),
                ],
    requires=['lxml(>=2.1)', 'bsddb', 'dateutil', 'argparse'],
    install_requires=_install_requires,
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
    entry_points={
        'console_scripts': [
            'cheshire3 = cheshire3.commands.cheshire3_console:main',
            'cheshire3-init = cheshire3.commands.cheshire3_init:main',
            'cheshire3-load = cheshire3.commands.cheshire3_load:main',
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
