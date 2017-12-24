import sqlite3

import six


def _utf8(x):
  if isinstance(x, six.binary_type):
    return x.decode('utf-8', 'replace')
  elif isinstance(x, six.string_types):
    return x
  else:
    raise TypeError("unknown type of {0!r}: {1!r}".format(x, type(x)))

def _mk_conn(path, *a):
  conn = sqlite3.connect(path, *a)
  conn.text_factory = sqlite3.OptimizedUnicode
  conn.row_factory = sqlite3.Row
  return conn
