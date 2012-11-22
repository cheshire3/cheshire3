1.0.8 - Thursday 22 November 2012

  DOCUMENTATION
  
  * Updated installations instructions in README.
  
  * Added CHANGES file.


1.0.7 - Friday 16 November 2012

  BUG FIXES
  
  * Fixed bug in serialization of ResultSet class for storage in
    cheshire3.sql.resultSetStore.


1.0.6 - Thursday 15 November 2012

  DOCUMENTATION
  
  * Updated download URL in package info.


1.0.5 - Thursday 15 November 2012
  
  BUG FIXES
  
  * cheshireVersion reinstated for backward compatibility.


1.0.4 - Friday 9 November 2012

  BUG FIXES
  
  * Fixed missing import of cheshire3.exceptions in
    cheshire3.sql.resultSetStore.


1.0.3 - Tuesday 6 November 2012

  BUG FIXES
  
  * Fixed incorrect version number in package info which could break dependency
    version resolution.


1.0.2 - Tuesday 6 November 2012

  BUG FIXES
  
  * Fixed missing import of CONFIG_NS in cheshire3.web.transformer.


1.0.1 - Thursday 6 September 2012

  ENHANCEMENTS
  
  * Allowed all configured paths to be specified relative to user's home 
    directory (i.e. by use of ~/).
    
  * Added an implementation agnostic XMLSyntaxError to cheshire3.exceptions.

  BUG FIXES
  
  * Fixed permission error bug in ``cheshire3-init`` and ``cheshire3-register``
    when Cheshire3 was installed as root. Solution creates a
    ``.cheshire3-server`` directory in the users home directory in which to
    create server-level config plugins, log files and persistent data stores.


1.0.0 - Thursday 9 August 2012

  ENHANCEMENTS
  
  * Standardized installation process. Installable from PyPI_.
  
  * Unittest suite for the majority of processing objects.
  
  * Command-line UI
  
    * ``cheshire3-init``
    * ``cheshire3-load``
    * ``cheshire3-load``
    * ``cheshire3-search``
    * ``cheshire3-serve``

    
.. _`PyPI`: http://pypi.python.org/pypi/cheshire3