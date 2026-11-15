"""``run(0)``, the analytic solve, refuses a negative plasma current; ``validate()`` reports it.

With RIP < 0 the solve converged and EQCALQ filled every output, but several were wrong, with no message. Measured
on the ITER geometry (RR 6.2, RA 2.0, RB 2.4, RKAP 1.7, RDLT 0.33, BB 5.3), RIP -15 against +15: QAXIS = QSURF =
4.611 (the wall's q) against 0.618 and 3.201, BETAT and BETAP 0, PVOL -1915 against 798 m^3, RAAVE NaN, PSITA
-117.70 against 120.02, and the q profile's first point 0.556 against 0.618; the default case at -3 alike. The
clamp of FNPSIP (eqsplf.f90) is one cause (it assumes PSIT grows outward); clamping it both ways put QSURF right
but left QAXIS 0.556, PVOL -798, BETAT and BETAP -0 and RAAVE NaN, so the solve itself does not treat the sign of
the current. ``eq_run(0)`` refuses it (EQ_ERR_INVALID, the reason in ``last_error()``) before any work; EQCALC and
the coupled path are left as they are (TR's MODELG 9 refuses a negative current itself:
python/trlib/tests/test_negative_current_for_eq.py). A file load (run(1)) reads its current from the file. One
test per case (``parametrize``, never ``subTest``).
"""
from __future__ import annotations

import math
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

ITER = {"MODELG": 2, "RR": 6.2, "RA": 2.0, "RB": 2.4, "RKAP": 1.7, "RDLT": 0.33, "BB": 5.3}


@pytest.fixture(autouse=True)
def _in_tmp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("params,rip", [(ITER, -15.0), ({"MODELG": 2}, -3.0)], ids=["iter", "default"])
def test_a_negative_current_is_refused_with_its_reason_and_the_handle_lives(params, rip):
    with eqlib.Eq() as e:
        e.set_params({**params, "RIP": rip})
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.run(0)
        assert "RIP" in e.last_error() and "negative" in e.last_error()
        e.set_param("RIP", abs(rip))                                    # the same handle solves a positive one
        e.run(0)
        assert 0.0 < e.get_state().scalars["qaxis"] < e.get_state().scalars["qsurf"]


@pytest.mark.parametrize("params,rip", [(ITER, -15.0), ({"MODELG": 2}, -3.0)], ids=["iter", "default"])
def test_validate_reports_a_negative_current_on_an_analytic_run(params, rip):
    with eqlib.Eq() as e:
        e.set_params({**params, "RIP": rip})
        assert [d.param for d in e.validate() if d.param == "RIP"] == ["RIP"]


@pytest.mark.parametrize("rip", [15.0, 3.0])
def test_a_positive_current_solves_as_before_and_is_not_reported(rip):
    with eqlib.Eq() as e:
        e.set_params({**ITER, "RIP": rip})
        assert not any(d.param == "RIP" for d in e.validate())
        e.run(0)
        scalars = e.get_state().scalars
        assert scalars["pvol"] > 0 and math.isfinite(scalars["raave"]) and scalars["qsurf"] > scalars["qaxis"]


def test_a_file_load_is_not_reported():
    # The file brings its own current: validate() says nothing of RIP for MODELG 3.
    with eqlib.Eq() as e:
        e.set_params({"MODELG": 3, "RIP": -1.0})
        assert not any(d.param == "RIP" for d in e.validate())
