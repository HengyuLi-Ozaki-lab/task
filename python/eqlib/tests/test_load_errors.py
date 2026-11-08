"""run(1), the load of an equilibrium file, reports a load that failed.

eq_save writes only after a run that succeeded, so the load's return code has
to be true: EQ_READ used to go on into EQCALQ after EQDSKR had failed
(MODELG=5, a missing file) and hand back EQCALQ's code, and left its code
unassigned for a MODELG that is no file format.

Against the library as it was: the MODELG=5 case does not fail, it ends its
process at a STOP inside EQCALQ (under --forked the session then stops with an
INTERNALERROR); the MODELG=2 case depends on what the unassigned variable
happened to hold, and so pins the behaviour more than it shows the change.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import eqlib

_HERE = Path(__file__).resolve()
_DEFAULT_SO = _HERE.parents[3] / "eq" / "libeqapi.so"

pytestmark = pytest.mark.skipif(
    not Path(os.environ.get("EQLIB_PATH") or _DEFAULT_SO).exists(),
    reason="libeqapi.so not built",
)


@pytest.fixture(autouse=True)
def _in_tmp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("modelg", [3, 5])
def test_load_of_a_missing_file_is_an_error(modelg):
    with eqlib.Eq() as e:
        e.set_param("MODELG", modelg)
        e.set_param_str("KNAMEQ", "no_such_file")
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(1)


def test_load_with_a_modelg_that_is_no_file_format_is_an_error():
    with eqlib.Eq() as e:
        e.set_param("MODELG", 2)
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(1)
