#!/usr/bin/env python

from __future__ import print_function

import argparse
import logging
import logging.config
import os
import os.path
import re
import sqlite3
import sys

from collections import defaultdict
from contextlib import contextmanager
from logging import DEBUG, INFO
from textwrap import dedent

import arrow

log = logging.getLogger(__name__)

HOME = os.environ['HOME']
DEFAULT_DB_LOCATION = os.path.join(HOME, '.zsh_hist_backup.db')
ZSHHIST_PATH = os.path.join(HOME, '.zshhistory')
TABLE_NAME = 'history'

def utf8(x):
  return unicode(x, 'UTF-8', 'replace')


def mk_conn(path, *a):
  conn = sqlite3.connect(path, *a)
  conn.text_factory = sqlite3.OptimizedUnicode
  conn.row_factory = sqlite3.Row
  return conn


@contextmanager
def open_conn(path, *a):
  conn = mk_conn(path, *a)
  try:
    yield conn
  finally:
    conn.close()


def table_exists(conn):
  cursor = conn.cursor()
  cursor.execute(
    "SELECT name from sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,)
  )

  return len(cursor.fetchall()) > 0


def create_table(conn):
  cursor = conn.cursor()
  cursor.execute("""
    CREATE TABLE {0} (
      timestamp BIGINT,
      counter INTEGER NOT NULL DEFAULT 0,
      command text NOT NULL,
      PRIMARY KEY (timestamp, counter)
    )
  """.format(TABLE_NAME))
  conn.commit()
  log.info("table created successfully")


def init_db(conn):
  with conn:
    if not table_exists(conn):
      create_table(conn)


def count_rows(conn):
  return conn.execute("select count(*) as c from history").fetchone()['c']


_REGEX = re.compile(r"""^: (?P<ts>\d+):\d+;(?P<cmd>.*)$""")


def history_iter(fp):
  countdict = defaultdict(int)

  for line in fp:
    m = _REGEX.match(line)
    if m:
      ts = int(m.group('ts'))
      cmd = utf8(m.group('cmd'))

      d = dict(timestamp=ts, command=cmd, counter=0)

      d['counter'] = countdict[ts]
      countdict[ts] += 1

      yield d
    else:
      log.debug("BAD LINE: %r", line)


def backup(conn, zshhist_fp):

  initial_count = count_rows(conn)

  with conn:
    cur = conn.cursor()

    q = u"""\
      REPLACE INTO {table} ('timestamp', 'counter', 'command')
        VALUES(:timestamp, :counter, :command)
    """.format(table=TABLE_NAME)

    cur.executemany(q, history_iter(zshhist_fp))

  log.info("inserted {0} rows".format(count_rows(conn)- initial_count))


def cmd_backup(req):
  with open_conn(req.dbpath) as conn:
    init_db(conn)
    with open(req.histfile) as fp:
      backup(conn, fp)
  log.info("complete!")


BOGO_TS = 1478541623


def cmd_munge(req):
  """fixes historical data where my timestamp was the same for 3 years :P"""
  with open_conn(req.dbpath) as conn:
    init_db(conn)
    nrows = conn.execute("select count(*) from history where timestamp = ?",
        (BOGO_TS,)).fetchone()[0]

    ts = BOGO_TS - nrows

    for row in conn.execute("select command from history where timestamp = ?", (BOGO_TS,)):
      print(": {ts}:0;{cmd}".format(ts=ts, cmd=row[0].encode('utf-8')), file=req.output)
      ts += 1


def cmd_restore(req):
  with open_conn(req.dbpath) as conn:
    init_db(conn)
    for row in conn.execute("select timestamp, command from history"):
      print(": {ts}:0;{cmd}".format(ts=ts, cmd=row[0].encode('utf-8')), file=req.output)


def cmds_since(conn, ts):
  return conn.execute(
    "select count(*) as c from history where timestamp > ?", (ts,)).fetchone()[0]

def last_cmd(conn):
  last_ts = conn.execute(
    "select timestamp as ts from history order by rowid DESC limit 1").fetchone()['ts']

  return arrow.get(last_ts).to('local')


def cmd_stats(req):
  with open_conn(req.dbpath) as conn:
    init_db(conn)
    now = arrow.now()

    last_cmd_t = last_cmd(conn)

    delta = (now - last_cmd_t)

    print(dedent("""\
      {hr:>5d} rows in the past hour
      {day:>5d} rows in the past day
      {week:>5d} rows in the past week
      last command backed up at: {last}
                      which was: {min}m {s}s ago""".format(
      hr=cmds_since(conn, now.shift(hours=-1).timestamp),
      day=cmds_since(conn, now.shift(hours=-24).timestamp),
      week=cmds_since(conn, now.shift(days=-7).timestamp),
      last=last_cmd_t.format("YYYY-MM-DD HH:mm:ss"),
      min=int(delta.total_seconds()/60),
      s=int(delta.total_seconds() % 60),
    )))


def logging_setup(level):
  logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,  # this fixes the problem
    'formatters': {
      'standard': {
        'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
      },
    },
    'handlers': {
      'default': {
        'level': level,
        'class': 'logging.StreamHandler',
      },
    },
    'loggers': {
      '': {
        'handlers': ['default'],
        'level': level,
        'propagate': True
      },
      'twitter.git': {'level': 'CRITICAL'},
      'requests_kerberos': {'level': 'CRITICAL'}
    }
  })


def cmd_help(req):
  req.print_help()


def main():
  parser = argparse.ArgumentParser(prog='zsh-backup')

  parser.set_defaults(print_help=parser.print_help)

  parser.add_argument(
      '-p', '--zsh-hist-path', dest='histfile',
      help='path to .zshhist file',
      default=ZSHHIST_PATH)

  parser.add_argument(
      '-d', '--dbpath', dest='dbpath',
      help='path to the sqlite db file',
      default=DEFAULT_DB_LOCATION)

  parser.add_argument(
    '--log-level', dest='log_lvl',
    choices="DEBUG INFO WARN ERROR FATAL".split(' '),
    help='set logging level',
    default='INFO'
  )

  parser.set_defaults(func=cmd_help)

  sub = parser.add_subparsers()
  backup_p = sub.add_parser('backup')
  backup_p.set_defaults(func=cmd_backup)

  munge_p = sub.add_parser('munge')
  munge_p.set_defaults(func=cmd_munge)
  munge_p.add_argument("output", type=argparse.FileType('wb'), default='-')

  restore_p = sub.add_parser('restore')
  restore_p.set_defaults(func=cmd_restore)
  restore_p.add_argument("output", type=argparse.FileType('wb'), default='-')

  stats_p = sub.add_parser('stats')
  stats_p.set_defaults(func=cmd_stats)

  help_p = sub.add_parser('help')
  help_p.set_defaults(func=cmd_help)

  parsed = parser.parse_args()
  logging_setup(parsed.log_lvl)

  parsed.func(parsed)


if __name__ == '__main__':
  main()
