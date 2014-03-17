"""Cheshire3 wrappers for Lucene vector space model."""

__all__ = ['normalizer', 'tokenizer', 'workflow', 'wrapper', 'indexStore']

# Initialize JVM ___ONCE___
try:
    import lucene
except ImportError:
    pass
else:
    vm = lucene.initVM(lucene.CLASSPATH)

import cheshire3.lucene.normalizer
import cheshire3.lucene.tokenizer
import cheshire3.lucene.workflow
import cheshire3.lucene.wrapper
import cheshire3.lucene.indexStore
