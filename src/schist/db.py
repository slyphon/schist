from __future__ import print_function

import logging
import os.path
import re
import sqlite3

from collections import defaultdict
from contextlib import contextmanager
from textwrap import dedent

from .common import _utf8

import arrow
import attr
import six

from attr.validators import instance_of, optional


log = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.expanduser("~/.schist.sq3")


@attr.s(frozen=True, slots=True)
class Row(object):
  timestamp = attr.ib(
      validator=instance_of(arrow.arrow.Arrow),
      convert=lambda s: arrow.get(s)
    )
  command = attr.ib(
      validator=instance_of(six.string_types),
      convert=_utf8
    )
  counter = attr.ib(default=0, validator=instance_of(int))

  def evolve(self, **kw):
    return attr.evolve(self, **kw)

  def as_sql_dict(self):
    d = attr.asdict(self)
    d['timestamp'] = self.timestamp.timestamp
    return d

  @property
  def unix(self):
    return self.timestamp.timestamp

  def __iter__(self):
    return iter(attr.astuple(self))

class AlreadyOpenException(Exception):
  pass

class NoConnectionError(Exception):
  pass


@attr.s(frozen=True, slots=True)
class HistConfig(object):
  table_name = attr.ib(validator=instance_of(six.string_types))

  # A function that takes a file pointer to the appropriate history file
  # and yields Row objects
  history_iter_fn = attr.ib()

  # a function that takes a path to a sqlite3 db file and returns
  # an sqlite3 connection object
  db_conn_factory = attr.ib()

  # a function that takes a Row iterator and a File object and outputs
  # the rows to that file
  output_fn = attr.ib()

  histfile = attr.ib(
    validator=instance_of(six.string_types))

  _conn = attr.ib(default=None)

  db_path = attr.ib(
    default=DEFAULT_DB_PATH,
    validator=instance_of(six.string_types))


  @contextmanager
  def open(self):
    if self._conn is not None:
      raise AlreadyOpenException("connection already open")
    hc = self._open()
    try:
      yield hc
    finally:
      hc._close()

  def _close(self):
    if self._conn is not None:
      self._conn.close()

  def _open(self):
    conn = self.db_conn_factory(self.db_path)
    return self.evolve(conn=conn)

  @property
  def conn(self):
    if self._conn is None:
      raise NoConnectionError()
    else:
      return self._conn

  def init_db(self):
    if not self.table_exists():
      self.create_table()

  def count(self):
    return self.conn.execute(
        "select count(*) as c from {table}".format(table=self.table_name)
      ).fetchone()[0]

  def create_table(self):
    return self.conn.execute("""\
        CREATE TABLE IF NOT EXISTS {table} (
          timestamp BIGINT NOT NULL,
          counter INTEGER NOT NULL DEFAULT 0,
          command text NOT NULL,
          PRIMARY KEY (timestamp, counter)
        )
      """.format(
        table=self.table_name,
        ))

  def insert(self):
    with self.conn:
      cur = self.conn.cursor()

      q = u"""\
        REPLACE INTO {table} ('timestamp', 'counter', 'command')
          VALUES(:timestamp, :counter, :command)
      """.format(table=self.table_name)

      with self.open_histfile() as fp:
        cur.executemany(q, (r.as_sql_dict() for r in self.history_iter_fn(fp)))

  def table_exists(self):
    xs = self.conn.execute(
        "SELECT name from sqlite_master WHERE type='table' and name=:name",
        dict(name=self.table_name)
      ).fetchall()
    return len(xs) > 0

  @contextmanager
  def open_histfile(self):
    with open(self.histfile, 'rb') as fp:
      yield fp

  _ROWS_SQL = "select timestamp, counter, command from {table} order by rowid {limit}"

  def rows(self, limit=None):
    q = self._ROWS_SQL.format(
      table=self.table_name,
      limit=' LIMIT %d' % (limit,) if limit is not None else ''
    )

    for r in self.conn.execute(q):
      yield Row(**r)

  def cmds_since(self, ts):
    q = "select count(*) as c from {table} where timestamp > :ts".format(table=self.table_name)
    return self.conn.execute(q, {'ts': ts.timestamp}).fetchone()[0]

  def last_cmd(self):
    q = "select timestamp as ts from {table} order by rowid DESC limit 1".format(
        table=self.table_name)

    last_ts = self.conn.execute(q).fetchone()['ts']
    return arrow.get(last_ts).to('local')

  def evolve(self, **kw):
    return attr.evolve(self, **kw)

  def restore(self, out_fp):
    """dump the contents of the db to out_fp in the correct format"""
    self.output_fn(self.rows(), out_fp)
