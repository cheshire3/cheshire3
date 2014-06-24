
import re

from urllib import unquote

import cheshire3.cqlParser as cql
from cheshire3.queryFactory import QueryStream
from cheshire3.web.www_utils import generate_cqlQuery


class FieldStorageQueryStream(QueryStream):
    u"""A QueryStream to process queries in web forms.

    Takes data from forms initialized as FieldStorage instances.
    """

    def __init__(self):
        QueryStream.__init__(self)

    def parse(self, session, data, codec, db):
        form = data
        qString = generate_cqlQuery(form)
        return cql.parse(qString)


streamHash = {
              'www': FieldStorageQueryStream
              }
