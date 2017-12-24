from __future__ import print_function

import logging
import os
import re

from collections import defaultdict

from .common import _utf8, _mk_conn
from .db import HistConfig, Row

import arrow

log = logging.getLogger(__name__)

_TS_RE = re.compile(r"""^#\d+$""")

def history_iter(fp):
  countdict = defaultdict(int)

  def count(k):
    v = countdict[k]
    countdict[k] += 1
    return v

  def mkrow(ts, ary):
    return Row(
      timestamp=ts,
      counter=count(ts.timestamp),
      command='\n'.join(ary)
    )

  # this solution kinda sucks because it requires reading the whole file into
  # a list.

  def parse(lines, ts=None, cmds=None, rows=None):
    if len(lines) == 0:
      if ts and cmds:
        rows.append(mkrow(ts, cmds))
      return rows

    if _TS_RE.match(lines[0]):
      if ts is None:
        # we don't have a timestamp, so this is a new record
        return parse(lines[1:], arrow.get(lines[0][1:]), cmds=None, rows=rows)
      else:
        # we have a timestamp, so this is the start of a new record, so we
        # create a Row, capture the new ts, and reset cmds for the next iteration
        assert cmds is not None
        rows = rows or []
        rows.append(mkrow(ts, cmds))

        return parse(lines[1:], ts=arrow.get(lines[0][1:]), cmds=None, rows=rows)
    else:
      cmds = cmds or []
      cmds.append(lines[0])
      return parse(lines[1:], ts=ts, cmds=cmds, rows=rows)

  for row in parse([_utf8(line).rstrip("\n") for line in fp]):
    yield row


def history_output(row_iter, fp):
  for row in row_iter:
    print(_utf8("#{0}".format(row.unix)), file=fp)
    print(row.command, file=fp)


_DEFAULT_BASH_HIST = os.path.expanduser("~/.bash_history")

CONFIG = HistConfig(
  table_name='bash_history',
  histfile=_DEFAULT_BASH_HIST,
  history_iter_fn=history_iter,
  output_fn=history_output,
  db_conn_factory=_mk_conn,
)
