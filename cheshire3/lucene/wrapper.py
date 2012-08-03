
# Wrappers to allow Cheshire3 objects to be used in Lucene processing


# c3:tokenizer <---> lucene:tokenizer
# c3:normalizer <---> lucene:filter
# c3:workflow <---> lucene:analyzer

# c3:selector, c3:xpathObject --> nothing (no XML)
# c3:extractor --> nothing (string is first input)
# c3:tokenMerger --> nothing (might need to *unmerge* :S)


# c3:Record <---> lucene:Document
# c3:IndexStore <---> lucene:IndexWriter + lucene:IndexSearcher
#    (c3:FileSystemStore <---> lucene:FSDirectory)
# c3:Index <---> lucene:Field

# c3:QueryFactory <---> lucene:QueryParser

