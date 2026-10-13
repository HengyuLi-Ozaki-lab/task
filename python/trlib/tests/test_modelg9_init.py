"""``MODELG=9`` (TR with the EQ q-solver): every initial state adopts EQ (#228).

With ``MODELG=9`` ``tr_set_metric`` builds the initial state by solving the
equilibrium and scaling q until the equilibrium current matches ``RIPS``;
during that, ``tr_bpsd_get`` adopts EQ's psi_p while the saved flag
``tr_eq_init`` is set, and the transport owns psi_p afterwards.

The flag was cleared by the first run and never set again, so every later
initial state in the same process (a second ``tr_init`` .. ``tr_finalize``
lifecycle, or a second ``tr_prep`` after a parameter change) skipped the
adoption: ``tr_run`` returned 0 with q = NaN in a new lifecycle, and with
the previous run's psi_p inside one lifecycle.

The case is ``RIPS=RIPE=3`` (the ``tr_init`` default, set here by name) on
the other defaults: the q-scaling agrees there after three clean
equilibrium solves. One test per case, no ``subTest``. Skipped when
``libtrapi.so`` has not been built.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

pytestmark = pytest.mark.skipif(not DEFAULT_SO.exists(), reason="libtrapi.so not built")

RIPS_GOOD = 3.0


def _configure(tr: Trlib, rips: float) -> None:
    tr.set_param("MODELG", 9)
    tr.set_param("RIPS", rips)
    tr.set_param("RIPE", rips)


def _profiles(state) -> dict:
    """The radial profiles of a state: what ``tr_prep`` builds."""
    n = state.nrmax
    return {
        "QP": list(state.QP[:n]),
        "AJ": list(state.AJ[:n]),
        "RN": [list(row) for row in state.RN[:n]],
        "RT": [list(row) for row in state.RT[:n]],
    }


def _everything(state) -> dict:
    return {"nt": state.nt, "scalars": dict(state.scalars), **_profiles(state)}


def _one_step(rips: float = RIPS_GOOD) -> dict:
    """One lifecycle: configure, one transport step, the whole state."""
    with Trlib() as tr:
        _configure(tr, rips)
        tr.run(1)
        return _everything(tr.get_state())


def _assert_finite(state: dict) -> None:
    flat = list(state["scalars"].values()) + state["QP"] + state["AJ"]
    flat += [x for row in state["RN"] + state["RT"] for x in row]
    bad = [x for x in flat if not math.isfinite(x)]
    assert not bad, f"{len(bad)} of {len(flat)} values are not finite"


def test_first_lifecycle_is_finite_and_near_the_commanded_current():
    state = _one_step()
    _assert_finite(state)
    assert state["nt"] == 1
    assert state["scalars"]["AJT"] == pytest.approx(RIPS_GOOD, rel=0.05)
    assert all(q > 0.0 for q in state["QP"])


def test_second_lifecycle_equals_the_first():
    first = _one_step()
    second = _one_step()
    _assert_finite(second)
    assert second == first


def test_third_lifecycle_equals_the_first():
    first = _one_step()
    _one_step()
    assert _one_step() == first


def test_second_preparation_in_one_lifecycle_equals_the_first():
    """``run(0)`` prepares without a step; the profiles are what was prepared.

    The scalars are left out: no step evaluates them after ``run(0)``.
    """
    with Trlib() as tr:
        _configure(tr, RIPS_GOOD)
        tr.run(0)
        first = _profiles(tr.get_state())
        tr.run(1)                         # the transport now owns psi_p
        tr.set_param("RIPS", RIPS_GOOD)   # same value: asks for tr_prep again
        tr.run(0)
        second = _profiles(tr.get_state())
    assert all(math.isfinite(q) for q in second["QP"])
    assert second == first
