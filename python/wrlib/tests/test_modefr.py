"""WR's MODEFR takes 0 only (task-web-client #202).

MODEFR is FROPEN's MODEP for the EQ load of WR's MODELG 3, 5 and 8 (``wr/wrparm.f90``): with 1, FROPEN
reads the file name from standard input (unit 5), the stdio MCP servers' channel, and other values are
no mode. ``set_param`` refuses both and takes 0.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from wrlib import Wrlib, WrlibParamError

_DEFAULT_SO = Path(__file__).resolve().parents[3] / "wr" / "libwrapi.so"

pytestmark = pytest.mark.skipif(
    not Path(os.environ.get("WRLIB_PATH") or _DEFAULT_SO).exists(),
    reason="libwrapi.so not built",
)


@pytest.mark.parametrize("value", [1.0, 2.0, -1.0, 1.5])
def test_modefr_other_than_0_is_refused(value):
    with Wrlib() as w:
        with pytest.raises(WrlibParamError):
            w.set_param("MODEFR", value)


def test_modefr_0_is_taken():
    with Wrlib() as w:
        w.set_param("MODEFR", 0.0)
