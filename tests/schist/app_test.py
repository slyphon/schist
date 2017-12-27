from __future__ import print_function

import os
import os.path
import sys

from io import StringIO
from textwrap import dedent

from schist import app, common, db

import arrow
import pytest

NOW = arrow.now()

ROWS = [
  db.Row(NOW.shift(days=-99), 'sudo reboot -n'),
  db.Row(NOW.shift(days=-3), 'cd /var/tmp'),
  db.Row(NOW.shift(days=-2), 'cd /tmp'),
  db.Row(NOW.shift(hours=-6), 'umount /blah'),
  db.Row(NOW.shift(minutes=-20), 'ls tests'),
  db.Row(NOW.shift(minutes=-5, seconds=-22), 'tox'),
]

ZSH_HISTORY = u'\n'.join(
    u": {r.timestamp.timestamp:d}:0;{r.command}".format(r=r) for r in ROWS
  )


@pytest.fixture
def zsh_history_file():
  with open(os.path.expanduser('~/.zsh_history'), 'w') as fp:
    print(ZSH_HISTORY, file=fp)


DB_PATH = os.path.expanduser('~/.schist.sq3')

@pytest.fixture
def zsh_history_db():
  conn = common._mk_conn(DB_PATH)
  try:
    with conn:
      conn.execute("""\
        CREATE TABLE IF NOT EXISTS zsh_history (
          timestamp BIGINT NOT NULL,
          command text NOT NULL,
          PRIMARY KEY (timestamp, command)
        )
        """)

      conn.executemany(
        "INSERT INTO zsh_history(timestamp,command) VALUES (:timestamp,:command)",
        (row.as_sql_dict() for row in ROWS)
      )

    yield conn
  finally:
    conn.close()
    os.unlink(DB_PATH)


def test_app_stats_cmd(monkeypatch, zsh_history_db):
  sio = StringIO()
  monkeypatch.setattr('sys.stdout', sio)
  monkeypatch.setattr('schist.app.arrow.now', lambda: NOW)
  app.main('stats', 'zsh')

  value = sio.getvalue()

  expected = dedent(u"""\
    {hr:>7d} rows in the past hour
    {day:>7d} rows in the past day
    {week:>7d} rows in the past week
    {total:>7d} rows total
    last command backed up at: {last}
                    which was: {min}m {s}s ago
    """.format(
      hr=2, day=3, week=5, total=6,
      last=ROWS[-1].timestamp.format('YYYY-MM-DD HH:mm:ss'),
      min=5, s=22
    ))

  assert value == expected

