from __future__ import print_function

from schist import db

import arrow
import pytest

try:
  from unittest.mock import MagicMock
except ImportError:
  from mock import MagicMock



def test_db_Row_iter():
  now = arrow.now()
  row = db.Row(now, 'foo')

  ts, cmd = row
  assert ts == now
  assert cmd == 'foo'


@pytest.fixture
def histconfig():
  conn = MagicMock()
  conn_factory = MagicMock()
  conn_factory.side_effect = conn
  output_fn = MagicMock()

  hc = db.HistConfig(
    table_name='xyz_history',
    history_iter_fn=lambda _: [],
    db_conn_factory=conn_factory,
    output_fn=output_fn,
    histfile='bogus',
    db_path=':memory:',
  )

  yield hc


def test_db_HistConfig_open_when_already_open(histconfig):

  with histconfig.open() as hist:
    with pytest.raises(db.AlreadyOpenException):
      with hist.open() as nope:
        assert False, "should not reach here"


def test_db_HistConfig_fails_when_conn_called_and_no_connection(histconfig):
  with pytest.raises(db.NoConnectionError):
    histconfig.conn
