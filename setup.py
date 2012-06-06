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

# Inspect to find current path
setuppath = inspect.getfile(inspect.currentframe())
setupdir = os.path.dirname(setuppath)

_name = u'cheshire3'
_version = '1.0.0b39'

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
    requires=['lxml(>=2.1)', 'bsddb', 'dateutil'],
    install_requires=['lxml >= 2.1', 'zopyx.txng3.ext == 3.3.1'],
    dependency_links = [
    	"http://labix.org/python-dateutil"
	],
    keywords = u"xml document search information retrieval engine data text",
    description = u'Cheshire3 Search and Retrieval Engine and Information Framework',
    long_description = _long_description,
    author = "Rob Sanderson, et al.",
    author_email = "azaroth@liv.ac.uk",
    maintainer = 'John Harrison',
    maintainer_email = u'john.harrison@liv.ac.uk',
    license = "BSD",
    url = "http://www.cheshire3.org/",
    download_url = 'http://www.cheshire3.org/download/{0}/src/{1}-{2}.tar.gz'.format(
    _version[:5], _name, _version)
    )
    
