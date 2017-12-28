from __future__ import print_function

import logging
import os.path
import re
import sqlite3

from collections import defaultdict
from contextlib import contextmanager
from textwrap import dedent

from .common import filter_none_v, _utf8

import arrow
import attr
import six

from attr.validators import instance_of, optional, in_ as is_in


log = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.expanduser("~/.schist.sq3")

BASH = 'b'
ZSH = 'z'

VALID_SHELLS = frozenset([BASH, ZSH])


class AlreadyOpenException(Exception):
  pass

class NoConnectionError(Exception):
  pass


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

  shell = attr.ib(
      validator=[instance_of(six.string_types), is_in(VALID_SHELLS)]
    )

  def as_sql_dict(self):
    d = attr.asdict(self)
    d['timestamp'] = self.timestamp.timestamp
    return d

  @property
  def unix(self):
    return self.timestamp.timestamp

  def __iter__(self):
    return iter(attr.astuple(self))


@attr.s(frozen=True, slots=True)
class DB(object):
  # a function that takes a path to a sqlite3 db file and returns
  # an sqlite3 connection object
  db_conn_factory = attr.ib()

  db_path = attr.ib(
    default=DEFAULT_DB_PATH,
    validator=instance_of(six.string_types))

  _conn = attr.ib(default=None)


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
      # from the sqlite3 docs:
      #
      #   The PRAGMA optimize command will automatically run ANALYZE on individual tables on an
      #   as-needed basis. The recommended practice is for applications to invoke the PRAGMA optimize
      #   statement just before closing each database connection.
      #
      self._conn.execute("PRAGMA optimize")
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


  _CREATE_SQL = """\
      CREATE TABLE IF NOT EXISTS history (
        timestamp BIGINT NOT NULL,
        shell text NOT NULL,
        command text NOT NULL,
        PRIMARY KEY (timestamp, command)
      );

      CREATE INDEX IF NOT EXISTS history_shell ON history(shell);
    """

  def create_table(self):
    return self.conn.executescript(self._CREATE_SQL)


  _TABLE_EXISTS_SQL = "SELECT name from sqlite_master WHERE type='table' and name='history'"


  def table_exists(self):
    xs = self.conn.execute(self._TABLE_EXISTS_SQL).fetchall()
    return len(xs) > 0


  _COUNT_SQL = "select count(*) as c from history {where}"


  def count(self, shell=None):
    q = self._COUNT_SQL.format(
      where='WHERE shell = :shell' if shell is not None else ''
    )

    return self.conn.execute(q, filter_none_v(shell=shell)).fetchone()[0]


  def evolve(self, **kw):
    return attr.evolve(self, **kw)


class _HasDB(object):
  """a mixin for common db-related things"""

  @contextmanager
  def open(self):
    with self.db.open() as db:
      yield self.evolve(db=db)

  @property
  def conn(self):
    return self.db.conn

  def init_db(self):
    return self.db.init_db()

  def evolve(self, **kw):
    return attr.evolve(self, **kw)



@attr.s(frozen=True, slots=True)
class Backup(_HasDB):
  shell = attr.ib(validator=[instance_of(six.string_types), is_in(VALID_SHELLS)])

  db = attr.ib(validator=instance_of(DB))

  # A function that takes a file pointer to the appropriate history file
  # and yields Row objects
  history_iter_fn = attr.ib()

  histfile = attr.ib(
    validator=instance_of(six.string_types))

  _INSERT_SQL = (
    u"REPLACE INTO history ('timestamp', 'command', 'shell') "
    "VALUES(:timestamp, :command, :shell)"
  )

  @contextmanager
  def open_histfile(self):
    with open(self.histfile, 'rb') as fp:
      yield fp

  def insert(self):
    with self.conn:
      cur = self.conn.cursor()

      with self.open_histfile() as fp:
        cur.executemany(self._INSERT_SQL, (r.as_sql_dict() for r in self.history_iter_fn(fp)))

  def count(self):
    return self.db.count(shell=self.shell)



@attr.s(frozen=True, slots=True)
class Query(_HasDB):
  db = attr.ib(validator=instance_of(DB))

  # a function that takes a Row iterator and a File object and outputs
  # the rows to that file
  output_fn = attr.ib()

  def restore(self, out_fp, limit=None, shell=None):
    """dump the contents of the db to out_fp in the correct format"""
    self.output_fn(self.rows(limit=limit, shell=shell), out_fp)


  _SEARCH_SQL = (
      u"SELECT * from history where command LIKE :term {where} "
      "ORDER BY timestamp DESC LIMIT :limit"
    )


  def search(self, term, limit=25, shell=None):
    """do a text search for a command"""
    with self.conn:
      q = self._SEARCH_SQL.format(
        where='AND shell = :shell' if shell is not None else ''
      )

      d = filter_none_v(term=term, limit=int(limit), shell=shell)

      for r in self.conn.execute(q, d):
        yield Row(**r)


  _ROWS_SQL = "select timestamp, command, shell from history {where} order by rowid {limit}"


  def rows(self, limit=None, shell=None):
    q = self._ROWS_SQL.format(
      where='WHERE shell = :shell' if shell is not None else '',
      limit=' LIMIT :limit' if limit is not None else ''
    )

    for r in self.conn.execute(q, filter_none_v(shell=shell, limit=limit)):
      yield Row(**r)


  _CMDS_SINCE_SQL = "select count(*) as c from history where timestamp > :ts {shell}"


  def cmds_since(self, ts, shell=None):
    q = self._CMDS_SINCE_SQL.format(
        shell='AND shell = :shell' if shell is not None else ''
      )

    return self.conn.execute(q, filter_none_v(ts=ts.timestamp, shell=shell)).fetchone()[0]


  _LAST_CMD_SQL = "select timestamp as ts from history {shell} order by rowid DESC limit 1"


  def last_cmd(self, shell=None):
    q = self._LAST_CMD_SQL.format(shell='WHERE shell = :shell' if shell is not None else '')

    last_ts = self.conn.execute(q, filter_none_v(shell=shell)).fetchone()['ts']
    return arrow.get(last_ts).to('local')
