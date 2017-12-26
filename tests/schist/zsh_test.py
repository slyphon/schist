from __future__ import print_function

import tempfile

from io import StringIO

from schist import db, zsh

import pytest
import arrow


ZSH_HISTORY = """\
: 1514240734:0;tox
: 1514240857:0;git rm tests/schist/__init__.py
: 1514240860:0;rm tests/schist/__init__.py
: 1514240862:0;tox
: 1514241010:0;tail -n5 ~/.zshhistory
"""

ROWS = [
  db.Row(arrow.get(1514240734), 'tox'),
  db.Row(arrow.get(1514240857), 'git rm tests/schist/__init__.py'),
  db.Row(arrow.get(1514240860), 'rm tests/schist/__init__.py'),
  db.Row(arrow.get(1514240862), 'tox'),
  db.Row(arrow.get(1514241010), 'tail -n5 ~/.zshhistory'),
]


@pytest.fixture
def zsh_fp(tmpdir):
  with tempfile.NamedTemporaryFile(mode='w+', dir=str(tmpdir)) as tmp:
    print(ZSH_HISTORY, end='', file=tmp)
    tmp.flush()
    tmp.seek(0)
    yield tmp


@pytest.fixture
def row_iter():
  return iter(ROWS)


def test_zsh_history_iter(zsh_fp):
  rows = [r for r in zsh.history_iter(zsh_fp)]
  assert len(rows) == len(ROWS)

  for i in range(0, len(rows)):
    assert rows[i] == ROWS[i]


def test_zsh_history_output(row_iter):
  sio = StringIO()
  zsh.history_output(row_iter, sio)
  assert sio.getvalue() == ZSH_HISTORY


@pytest.fixture
def zsh_config(zsh_fp, memory_db):
  yield zsh.CONFIG.evolve(
      db_path=":memory:",
      histfile=zsh_fp.name,
      db_conn_factory=lambda _: memory_db,
    )


def test_zsh_integration(zsh_fp, zsh_config, memory_db):
  with zsh_config.open() as hist:
    # we don't have a table
    def get_table():
      return memory_db.execute(
        "SELECT name from sqlite_master where type='table' and name='zsh_history'").fetchall()

    assert len(get_table()) == 0

    assert not hist.table_exists()

    hist.init_db()

    assert len(get_table()) == 1

    assert hist.table_exists()

    hist.insert()
    assert [r for r in hist.rows()] == ROWS

    assert hist.count() == len(ROWS)

    # calling insert a second time doesn't insert more rows
    hist.insert()
    assert [r for r in hist.rows()] == ROWS

    sio = StringIO()
    hist.restore(sio)
    assert sio.getvalue() == ZSH_HISTORY

    assert hist.cmds_since(ROWS[2].timestamp) == 2

    assert hist.last_cmd() == ROWS[-1].timestamp
