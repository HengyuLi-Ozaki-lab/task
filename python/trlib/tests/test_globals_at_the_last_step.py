"""A run returns the global results of its last step, whatever NTSTEP, NGTSTP and NGRSTP are.

``tr_eval`` computes the global results (``TRGLOB``: WPT, AJT, the betas, TAUE1, TAUE2, ZEFF0, ALI, RQ1) only
on a step that NTSTEP, NGTSTP or NGRSTP divides (``tr/trexec.f90``), and ``tr_get_state`` copies them as
last computed. So a run whose last step none of them divides returned an earlier step's: measured on the
TST-2 fixture with NTMAX 10, all three at 1000 gave WPT 5.39e-7 and TAUE1 2.95e-6 (step 0's) against
2.98e-6 and 8.54e-5, and 4/4/100 gave step 8's, bit for bit. ``tr_eval`` now computes them on the last
step of a run when no output step did. Not on a step it has just computed them on: ``TRGLOB`` keeps the
previous call's WPT and T for WPDOT, which a second call at the same T would set to 0 (TAUE2 would then
equal TAUE1). And that call is no output step, so the previous reference is put back: a run made in
several ``tr_run`` calls (each sets NTMAX to NT plus its count) ends as one run would. One test per case
(``parametrize``, never ``subTest``).
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

from trlib import Trlib  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"
EQDATA = FIXTURES_DIR / "eqdata.TST-2"

pytestmark = [
    pytest.mark.skipif(not DEFAULT_SO.exists(), reason=f"libtrapi.so not built at {DEFAULT_SO}"),
    pytest.mark.skipif(not EQDATA.exists(), reason=f"fixture missing: {EQDATA}"),
]

# The results TRGLOB computes from the state of the step it is called on. TAUE2 is left out: it is
# WPT / (PINT - WPDOT), and WPDOT is taken between this call and the previous one.
INSTANTANEOUS = ("WPT", "TAUE1", "BETA0", "BETAP0", "BETAN", "ALI", "AJT", "ZEFF0")


@contextlib.contextmanager
def _pushd(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _scalars(ntmax: int, ntstep: int, ngtstp: int, ngrstp: int) -> dict:
    from trlib.tests.fixtures import tr_tst2_params as base
    with _pushd(FIXTURES_DIR):
        with Trlib() as tr:
            base.apply(tr)
            for name, value in (("NTMAX", ntmax), ("NTSTEP", ntstep), ("NGTSTP", ngtstp), ("NGRSTP", ngrstp)):
                tr.set_param(name, float(value))
            tr.run(ntmax)
            return dict(tr.get_state().scalars)


@pytest.mark.parametrize("steps", [(1000, 1000, 1000), (4, 4, 100), (3, 7, 9)],
                         ids=["none-within-the-run", "last-at-step-8", "last-at-step-9"])
def test_the_global_results_are_the_last_steps(steps):
    end = _scalars(10, 1, 1, 1)                        # computed on every step, the last one included
    late = _scalars(10, *steps)
    assert late["T"] == end["T"]
    for name in INSTANTANEOUS:
        assert late[name] == pytest.approx(end[name], rel=1e-12, abs=0.0), name


def test_a_last_step_that_is_an_output_step_is_not_computed_twice():
    # Computed twice at the same T, WPDOT would be 0 and TAUE2 would equal TAUE1.
    end = _scalars(10, 1, 1, 1)
    assert math.isfinite(end["TAUE2"]) and end["TAUE2"] != pytest.approx(end["TAUE1"], rel=1e-9)


def _chunked(counts, ntstep: int, ngtstp: int, ngrstp: int) -> dict:
    """The scalars after one handle runs COUNTS steps in turn (one tr_run each)."""
    from trlib.tests.fixtures import tr_tst2_params as base
    with _pushd(FIXTURES_DIR):
        with Trlib() as tr:
            base.apply(tr)
            for name, value in (("NTMAX", sum(counts)), ("NTSTEP", ntstep), ("NGTSTP", ngtstp),
                                ("NGRSTP", ngrstp)):
                tr.set_param(name, float(value))
            states = []
            for count in counts:
                tr.run(count)
                states.append(dict(tr.get_state().scalars))
            return states


def test_a_run_made_in_two_calls_ends_as_one_run_does():
    # The first call ends on step 5, no output step at 10/10/10: its extra TRGLOB must not move the reference of
    # WPDOT, or TAUE2 at step 10 is taken over 5 steps instead of 10 (measured: 1.237e-4 against 2.836e-4).
    # A second tr_run starts with its own TRCALC and bpsd exchange: without this change the two runs already
    # differ by 3.4e-9 in WPT and 1.14e-6 in TAUE2, relative (WPDOT magnifies it), and by the same with it.
    # 1e-4 is far below the factor of 2.3 in TAUE2 this test is for.
    [one] = _chunked([10], 10, 10, 10)
    first, second = _chunked([5, 5], 10, 10, 10)
    for name in INSTANTANEOUS + ("TAUE2",):
        assert second[name] == pytest.approx(one[name], rel=1e-4, abs=0.0), name
    # ... and the first call's own results are step 5's.
    [at_5] = _chunked([5], 1, 1, 1)
    for name in INSTANTANEOUS:
        assert first[name] == pytest.approx(at_5[name], rel=1e-12, abs=0.0), name


def test_a_call_of_no_step_changes_nothing():
    # run(0) leaves tr_loop before tr_eval, so this cannot fail as the change stands: it guards against the extra
    # computation being moved to tr_loop's exit (label 9000), which a call of no step reaches.
    before, after = _chunked([10, 0], 1000, 1000, 1000)
    assert after == before
