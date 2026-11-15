"""``tr_run`` refuses, before ``tr_prep``, a zero edge density of species 1 or 2; ``validate()`` reports it.

The edge terms of the transport divide by the edge density of the electrons and of the bulk ions (``PNSS(1)``,
``PNSS(2)`` in ``tr/trcalc.f90``). Measured on the TST-2 fixture with PN > 0: PNS[1] = 0 and PNS[2] = 0 each ended
the run with WPT, the betas and TAUE1, TAUE2 non-finite; a zero edge density of species 3 ran finite and stays
allowed. ``species_profile_violations`` (``tr/tr_api.f90``) already refused PN = PNS = 0 and negative values. One
test per case (``parametrize``, never ``subTest``).
"""
from __future__ import annotations

import contextlib
import math
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibParamError  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"
EQDATA = FIXTURES_DIR / "eqdata.TST-2"

pytestmark = [
    pytest.mark.skipif(not DEFAULT_SO.exists(), reason=f"libtrapi.so not built at {DEFAULT_SO}"),
    pytest.mark.skipif(not EQDATA.exists(), reason=f"fixture missing: {EQDATA}"),
]

NTMAX = 2
SP3 = {"NSMAX": 3, "PA[3]": 2.0, "PZ[3]": 1.0, "PN[3]": 0.005, "PNS[3]": 0.0005, "PT[3]": 0.001, "PTS[3]": 0.0001}


@contextlib.contextmanager
def _pushd(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _run(mutations: dict):
    from trlib.tests.fixtures import tr_tst2_params as base
    with _pushd(FIXTURES_DIR):
        with Trlib() as tr:
            base.apply(tr)
            tr.set_param("NTMAX", float(NTMAX))
            for name, value in mutations.items():
                tr.set_param(name, float(value))
            tr.run(NTMAX)
            return tr.get_state()


@pytest.mark.parametrize("ns", [1, 2])
def test_a_zero_edge_density_of_the_electrons_or_the_bulk_ions_is_refused(ns):
    with pytest.raises(TrlibParamError):
        _run({f"PNS[{ns}]": 0.0})


@pytest.mark.parametrize("ns", [1, 2])
def test_validate_reports_a_zero_edge_density_of_species_1_or_2(ns):
    from trlib.tests.fixtures import tr_tst2_params as base
    with _pushd(FIXTURES_DIR):
        with Trlib() as tr:
            base.apply(tr)
            tr.set_param(f"PNS[{ns}]", 0.0)
            assert any(d.param == f"PNS[{ns}]" for d in tr.validate())


def test_a_zero_edge_density_of_species_3_runs_finite():
    state = _run({**SP3, "PNS[3]": 0.0})
    assert all(math.isfinite(v) for v in state.scalars.values())
