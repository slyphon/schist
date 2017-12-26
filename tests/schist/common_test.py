from __future__ import print_function

from schist.common import _utf8

import pytest

def test_utf8_with_bad_input():
  with pytest.raises(TypeError):
    _utf8(object())
