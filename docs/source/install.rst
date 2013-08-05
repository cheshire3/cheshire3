Cheshire3 Installation
======================

Requirements / Dependencies
---------------------------

Cheshire3 requires Python_ 2.6.0 or later. It has not yet been verified
as Python 3 compliant.

As of the version 1.0 release Cheshire3's core dependencies *should* be
resolved automatically by the standard Python_ package management
mechanisms (e.g. pip_, `easy_install`_, distribute_/setuptools_).

However on some systems, for example if installing on a machine without
network access, it may be necessary to manually install some 3rd party
dependencies. In such cases we would encourage you to download the
necessary Cheshire3 bundles from the `Cheshire3 download site`_ and install
them using the automated build scripts included. If the automated scripts
fail on your system, they should at least provide hints on how to resolve
the situation.

If you experience problems with dependencies, please get in touch via
the `GitHub issue tracker`_ or wiki_, and we'll do our best to help.


Additional / Optional Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Certain features within the `Cheshire3 Information Framework`_ will have
additional dependencies (e.g. web APIs will require a web application
server). We'll try to maintain an accurate list of these in the README
file for each sub-package.

The bundles available from the `Cheshire3 download site`_ should
continue to be a useful place to get hold of the source code for these
pre-requisites.


Installation
------------

The following guidelines assume that you have administrative privileges
on the machine you're installing on, or that you're installing in a local
Python_ install or a virtual environment created using ``virtualenv``. If
this is not the case, then you might need to use the ``--local`` or
``--user`` option . For more details, see:
http://docs.python.org/install/index.html#alternate-installation


Users
~~~~~

Users (i.e. those not wanting to actually develop Cheshire3) have several
choices:

- pip_: ``pip install cheshire3``

- `easy_install`_: ``easy_install cheshire3``

- Install from source:

  1. Download a source code archive from one of:

     http://pypi.python.org/pypi/cheshire3

     http://cheshire3.org/download/lastest/src/

     http://github.com/cheshire3/cheshire3

  2. Unpack it:

     ``tar -xzf cheshire3-1.0.8.tar.gz``

  3. Go into the unpacked directory:

     ``cd cheshire3-1.0.8``

  4. Install:

     ``python setup.py install``


Developers
~~~~~~~~~~

1. In GitHub_, fork the `Cheshire3 GitHub repository`_

2. Locally clone your Cheshire3 GitHub fork

3. Run ``python setup.py develop``


.. Links
.. _Python: http://www.python.org/
.. _pip: http://www.pip-installer.org/en/latest/index.html
.. _distribute: http://packages.python.org/distribute/
.. _`easy_install`: http://packages.python.org/distribute/easy_install.html
.. _setuptools: http://pypi.python.org/pypi/setuptools/
.. _GitHub: http://github.com
.. _`Cheshire3 GitHub repository`: http://github.com/cheshire3/cheshire3
.. _`GitHub issue tracker`: http://github.com/cheshire3/cheshire3/issues
.. _wiki: http://github.com/cheshire3/cheshire3/wiki
.. _`Cheshire3 Information Framework`: http://cheshire3.org
.. _`Cheshire3 download site`: http://www.cheshire3.org/download/
