from __future__ import print_function

import tempfile

from io import StringIO

from schist import bash, db

import pytest
import arrow


BASH_HISTORY = """\
ls /tmp/xyz
#1447184318
echo "foo"
#1447185494
echo "bar"
#1447185522
cat file
#1447185931
ls x
ls y
ls z
"""

# we expect everything but the first line
EXPECTED_OUTPUT = '\n'.join(BASH_HISTORY.split("\n")[1:])

ROWS = [
  db.Row(arrow.get(1447184318), 'echo "foo"'),
  db.Row(arrow.get(1447185494), 'echo "bar"'),
  db.Row(arrow.get(1447185522), 'cat file'),
  db.Row(arrow.get(1447185931), '\n'.join(['ls x', 'ls y', 'ls z']))
]

@pytest.fixture
def bash_fp(tmpdir):
  with tempfile.NamedTemporaryFile(mode='w+', dir=str(tmpdir)) as tmp:
    print(BASH_HISTORY, end='', file=tmp)
    tmp.flush()
    tmp.seek(0)
    yield tmp


@pytest.fixture
def row_iter():
  return iter(ROWS)


def test_bash_history_iter(bash_fp):
  rows = [r for r in bash.history_iter(bash_fp)]
  assert len(rows) == len(ROWS)

  assert rows[0] == ROWS[0]
  assert rows[1] == ROWS[1]
  assert rows[2] == ROWS[2]
  assert rows[3] == ROWS[3]


def test_bash_history_output(row_iter):
  sio = StringIO()
  bash.history_output(row_iter, sio)

  assert sio.getvalue() == EXPECTED_OUTPUT


@pytest.fixture
def bash_config(bash_fp, memory_db):
  def db_factory(s):
    return memory_db

  yield bash.CONFIG.evolve(
      db_path=":memory:",
      histfile=bash_fp.name,
      db_conn_factory=db_factory,
    )


def test_bash_integration(bash_fp, bash_config, memory_db):
  with bash_config.open() as hist:
    # we don't have a table
    def get_table():
      return memory_db.execute(
        "SELECT name from sqlite_master where type='table' and name='bash_history'").fetchall()

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
    assert sio.getvalue() == EXPECTED_OUTPUT

    assert hist.cmds_since(ROWS[1].timestamp) == 2

    assert hist.last_cmd() == ROWS[-1].timestamp
