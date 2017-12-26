from __future__ import print_function

import tempfile

from schist.common import _mk_conn

import pytest

@pytest.fixture
def memory_db():
  conn = _mk_conn(":memory:")
  try:
    yield conn
  finally:
    conn.close

@pytest.fixture(autouse=True)
def bogus_HOME(tmpdir, monkeypatch):
  monkeypatch.setenv('HOME', str(tmpdir))
