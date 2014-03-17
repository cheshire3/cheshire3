"""Cheshire3 file format support.

File format conversion and metadata discovery for Cheshire3.

All classes defined in this sub-package conform to the Cheshire3 object model 
and API. Noteworthy classes defined by this sub-package:

 * DependentCmdLinePreParser:    
   Command Line PreParser to start an external service before processing
   document.
    
 * CmdLineMetadataDiscoveryPreParser:
   Command Line PreParser to use external program for metadata discovery.
        
 * XmlParsingCmdLineMetadataDiscoveryPreParser:
   Command Line PreParser to take the results of an external program given
   in XML, parse it, and extract metadata into a hash.

"""

__name__ = "Cheshire3 File Formats Package"
__package__ = "formats"

__all__ = ['preParser', 'documentFactory']

