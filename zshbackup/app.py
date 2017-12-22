#!/usr/bin/env python

from __future__ import print_function

import argparse
import errno
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

from . import db, zsh, bash

log = logging.getLogger(__name__)

def cmd_backup(req, conf):
  # change this to pass the HistConfig object instead of the parsed cmdline opts

  with conf.open() as hist:
    if not hist.table_exists():
      hist.create_table()

    initial_count = hist.count()
    hist.insert()
    log.info("inserted {0} rows".format(hist.count() - initial_count))


def cmd_restore(req, conf):
  with conf.open() as hist:
    hist.init_db()
    try:
      hist.restore(req.output)
    except IOError as e:
      if e.errno == errno.EPIPE:
        return
      else:
        raise


def cmd_stats(req, conf):
  with conf.open() as hist:
    hist.init_db()

    now = arrow.now()

    last_cmd_t = hist.last_cmd()

    delta = (now - last_cmd_t)

    print(
      dedent("""\
        {hr:>5d} rows in the past hour
        {day:>5d} rows in the past day
        {week:>5d} rows in the past week
        last command backed up at: {last}
                        which was: {min}m {s}s ago""".format(
          hr=hist.cmds_since(now.shift(hours=-1)),
          day=hist.cmds_since(now.shift(hours=-24)),
          week=hist.cmds_since(now.shift(days=-7)),
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


def cmd_help(req, conf):
  req.print_help()

HOME = os.environ['HOME']
DEFAULT_DB_LOCATION = os.path.expanduser('~/.zsh_hist_backup.db')
ZSHHIST_PATH = os.path.expanduser('~/.zshhistory')

def main():
  parser = argparse.ArgumentParser(prog='shell-history-backup')

  parser.set_defaults(print_help=parser.print_help)

  parser.add_argument(
      'shell', choices=['zsh', 'bash'], help="the shell history to process")

  parser.add_argument(
      '-p', '--hist-path', dest='histfile',
      help='path to shell history file'
    )

  parser.add_argument(
      '-d', '--dbpath', dest='db_path',
      help='path to the sqlite db file'
    )

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

  restore_p = sub.add_parser('restore')
  restore_p.set_defaults(func=cmd_restore)
  restore_p.add_argument("output", type=argparse.FileType('w'), nargs='?', default='-')

  stats_p = sub.add_parser('stats')
  stats_p.set_defaults(func=cmd_stats)

  help_p = sub.add_parser('help')
  help_p.set_defaults(func=cmd_help)

  req = parser.parse_args()
  logging_setup(req.log_lvl)

  if req.shell == 'zsh':
    mod = zsh
  else:
    mod = bash

  d = {'histfile': req.histfile, 'db_path': req.db_path}

  conf = mod.CONFIG.evolve(
    **{k: v for k, v in d.items() if v is not None}
  )

  req.func(req, conf)


if __name__ == '__main__':
  main()
