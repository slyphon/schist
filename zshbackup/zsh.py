from __future__ import print_function

import logging
import os
import re

from collections import defaultdict

from .common import _utf8, _mk_conn
from .db import HistConfig, Row

import arrow

log = logging.getLogger(__name__)

_ZSH_REGEX = re.compile(r"""^: (?P<ts>\d+):\d+;(?P<cmd>.*)$""")


def history_iter(fp):
  countdict = defaultdict(int)

  for line in fp:
    m = _ZSH_REGEX.match(_utf8(line))
    if m:

      ts = arrow.get(int(m.group('ts')))

      unix_ts = ts.timestamp

      row = Row(
        timestamp=ts,
        counter=countdict[unix_ts],
        command=_utf8(m.group('cmd'))
      )

      countdict[unix_ts] += 1

      yield row.as_sql_dict()
    else:
      log.debug("BAD LINE: %r", line)


def history_output(row_iter, fp):
  for row in row_iter:
    print(": {ts}:0;{cmd}".format(ts=str(row.timestamp.timestamp), cmd=row.command), file=fp)


_DEFAULT_ZSH_HIST = os.path.expanduser("~/.zsh_history")

CONFIG = HistConfig(
  table_name="zsh_history",
  histfile=_DEFAULT_ZSH_HIST,
  db_conn_factory=_mk_conn,
  history_iter_fn=history_iter,
  output_fn=history_output,
)
