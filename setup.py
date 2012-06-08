# Setup file for cheshire3 package
import sys
import os
import inspect

from warnings import warn

# Import Distribute / Setuptools
import distribute_setup
distribute_setup.use_setuptools()
from setuptools import setup, find_packages

# Check version
if sys.version_info < (2,6):
    warn("Python 2.6 or later required, some code may be incompatible with earlier versions.")

# Determine python-dateutil version
dateutilstr = 'python-dateutil == 1.5' if sys.version_info < (3,0) else 'python-dateutil >= 2.0'

# Inspect to find current path
setuppath = inspect.getfile(inspect.currentframe())
setupdir = os.path.dirname(setuppath)

_name = u'cheshire3'
_version = '1.0.0b41'

# Read any necessary bits from README.mdown
try:
    fh = open(os.path.join(setupdir, 'README.mdown'), 'r')
except IOError:
    _long_description = u''
else:
    fstr = fh.read()
    fh.close()
    # Long Description
    desc_st_str = u'''\
Description
-----------'''
    desc_end_str = u'''\
Authors
-------'''
    desc_st = fstr.find(desc_st_str)+len(desc_st_str)+1
    desc_end = fstr.find(desc_end_str)-1
    _long_description = fstr[desc_st:desc_end]
    # Process any further sections here
    # Delete file contents from memory
    del fstr


setup(
    name = _name,
    version = _version,
    packages = find_packages('code'),
    package_dir = {'': 'code'},
    include_package_data = True,
    exclude_package_data = {'': ['README.mdown']},
    requires=['lxml(>=2.1)', 'bsddb', 'dateutil', 'unittest2'],
    install_requires=['lxml >= 2.1', 
                      dateutilstr, 
                      'zopyx.txng3.ext == 3.3.1',
                      'unittest2'],
    dependency_links = [
    	"http://labix.org/python-dateutil"
	],
    extras_require = {
        'graph': ['rdflib'],
        'lucene': ['lucene'],
        'sql': ['PyGreSQL >= 3.8.1'],
        'web': ['PyZ3950 >= 2.04']
    },
    test_suite = "cheshire3.test.testAll",
    keywords = u"xml document search information retrieval engine data text",
    description = u'Cheshire3 Search and Retrieval Engine and Information Framework',
    long_description = _long_description,
    author = "Rob Sanderson, et al.",
    author_email = "azaroth@liv.ac.uk",
    maintainer = 'John Harrison',
    maintainer_email = u'john.harrison@liv.ac.uk',
    license = "BSD",
    classifiers = [
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
    url = "http://www.cheshire3.org/",
    download_url = 'http://www.cheshire3.org/download/{0}/src/{1}-{2}.tar.gz'.format(
    _version[:5], _name, _version)
)

