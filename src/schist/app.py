#!/usr/bin/env python

from __future__ import print_function

import argparse
import errno
import logging
import logging.config
import os
import os.path
import sys

from textwrap import dedent

import arrow

from . import zsh, bash


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
      dedent(u"""\
        {hr:>7d} rows in the past hour
        {day:>7d} rows in the past day
        {week:>7d} rows in the past week
        {total:>7d} rows total
        last command backed up at: {last}
                        which was: {min}m {s}s ago""".format(
          hr=hist.cmds_since(now.shift(hours=-1)),
          day=hist.cmds_since(now.shift(hours=-24)),
          week=hist.cmds_since(now.shift(days=-7)),
          total=hist.count(),
          last=last_cmd_t.format("YYYY-MM-DD HH:mm:ss"),
          min=int(delta.total_seconds()/60),
          s=int(delta.total_seconds() % 60),
      )))


DATE_FMT = 'YYYY-MM-DD HH:mm:ss\t'
RESULT_FMT = "{date}{command}"


def cmd_search(req, conf):
  with conf.open() as hist:
    hist.init_db()
    results = 0
    for row in hist.search(req.term, req.limit):
      rs = RESULT_FMT.format(
        date=row.timestamp.format(DATE_FMT) if req.include_date else '',
        command=row.command
      )
      print(rs)
      results += 1

    if results == 0:
      print("no results", file=sys.stderr)
      sys.exit(1)


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


def common_args(ap, hist_path=True):
  ap.add_argument(
      'shell',
      choices=['z', 'zsh', 'b', 'bash'],
      help="the shell history to process"
    )

  if hist_path:
    ap.add_argument(
        '-p', '--hist-path', dest='histfile',
        help='path to shell history file (defaults, bash: {bash}, zsh: {zsh})'.format(
          bash=bash._DEFAULT_BASH_HIST, zsh=zsh._DEFAULT_ZSH_HIST
      )
    )


def main(*args):
  ap = argparse.ArgumentParser(prog='schist')

  ap.set_defaults(
    print_help=ap.print_help,
    histfile=None,
  )

  ap.add_argument(
    '--log-level', dest='log_lvl',
    choices="DEBUG INFO WARN ERROR FATAL".split(' '),
    help='set logging level',
    default='INFO'
  )

  ap.add_argument(
    '-d', '--dbpath', dest='db_path',
    help='path to the sqlite db file'
  )


  sub = ap.add_subparsers()
  backup_p = sub.add_parser('backup')
  backup_p.set_defaults(func=cmd_backup)
  common_args(backup_p)

  restore_p = sub.add_parser('restore')
  restore_p.set_defaults(func=cmd_restore)
  restore_p.add_argument("output", type=argparse.FileType('w'), nargs='?', default='-')
  common_args(restore_p)

  stats_p = sub.add_parser('stats')
  stats_p.set_defaults(func=cmd_stats)
  common_args(stats_p)

  def search_args(p):
    p.set_defaults(func=cmd_search)
    common_args(p, hist_path=False)
    p.add_argument('--limit',
        type=int,
        default=25,
        help='max number of rows to return, default: 25'
      )

    p.add_argument(
        '--no-date',
        action='store_false',
        dest='include_date',
        default=True,
        help='suppress timestamp in search results',
      )

    p.add_argument('term',
        help=('search term used in LIKE clause. '
          'Use %% to wildcard multiple characters, _ to wildcard one character')
      )


  search_args(sub.add_parser('search'))
  search_args(sub.add_parser('s'))


  ap.set_defaults(func=cmd_help)

  # I couldn't figure out how to do this w/ argparse
  if len(sys.argv) == 1 or len(sys.argv) == 2 and (
      sys.argv[1] == 'help' or
      sys.argv[1] == '--help' or
      sys.argv[1] == '-h'):
    ap.print_help()
    sys.exit(0)

  req = ap.parse_args(list(args))
  logging_setup(req.log_lvl)

  if req.shell == 'zsh' or req.shell == 'z':
    mod = zsh
  elif req.shell == 'bash' or req.shell == 'b':
    mod = bash
  else:
    req.print_help()
    sys.exit(0)

  d = {'histfile': req.histfile, 'db_path': req.db_path}

  conf = mod.CONFIG.evolve(
    **{k: v for k, v in d.items() if v is not None}
  )

  req.func(req, conf)


if __name__ == '__main__':
  main(*sys.argv[1:])
