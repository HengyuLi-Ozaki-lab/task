"""An EQ contour step that cannot be completed fails the run; the process lives.

``EQCALQP`` and ``EQCALQV`` (eq/eqcalq.f90) refine the top and bottom of each
flux surface with ``zminmax``, which reads the contour points on both sides
of the extremum. When the extremum is the first or the last point of the
contour, or when the surface could not be traced at all, that read is outside
``YA`` (index 0) and a build with run-time checks ends the process; a build
without them reads whatever lies there.

Measured on the healthy runs (the EQ baselines eq_iter01 and eq_tst2, the
analytic default, and tr2 on the ITER heating inputs): the extremum is never
at the edge, so the guard changes no healthy result.

The failing runs here are ``MODELG=9`` with ``RA`` larger than the default
(1.8 and 2.0), the rest at the ``tr_init`` defaults: the wall ``RB`` (1.2) is
smaller than ``RA``, so a surface near the wall cannot be traced within
NTVMAX (400) points; EQMAGS reports its status 1 and the old code went on to
read ``YA(:,0)``. EQCALQP now returns 111 (surface loop; 112 for the edge
surface; 110 for an extremum at the edge of the contour) with a reason in
``eq_last_error``; the code is read from unit 6 of the child
(``eq_calc: eqcalq: ierr=``), the text through eqlib. No input was found that
reaches 110 or 112. Each TR case runs in a child process so that a process end
is a failed test, not a dead pytest. One test per case, no ``subTest``.
Skipped when ``libtrapi.so`` has not been built.
"""
from __future__ import annotations

import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
REPO = HERE.parents[3]

pytestmark = pytest.mark.skipif(
    not (REPO / "tr" / "libtrapi.so").exists(), reason="libtrapi.so not built"
)

CHILD = textwrap.dedent('''
    import sys
    sys.path.insert(0, {root!r})
    from trlib import Trlib, TrlibRunError
    t = Trlib()
    t.set_param("MODELG", 9)
    {sets}
    try:
        t.run(0)
        print("RC 0")
    except TrlibRunError:
        print("RC CALC_FAILED")
''')


def _child(sets: str):
    code = CHILD.format(root=str(PYTHON_ROOT), sets=sets)
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )


def _assert_failed_cleanly(p) -> None:
    assert p.returncode == 0, p.stderr[-2000:]
    assert "RC CALC_FAILED" in p.stdout, p.stdout[-2000:]


def test_unsolvable_modelg9_fails_without_ending_the_process():
    """RIPS = RIPE = 100: the first equilibrium solve fails (regression: passes before and after)."""
    _assert_failed_cleanly(_child('t.set_param("RIPS", 100.0); t.set_param("RIPE", 100.0)'))


def test_untraceable_surface_reports_code_111_on_unit_6():
    p = _child('t.set_param("RA", 1.8)')
    _assert_failed_cleanly(p)
    m = re.search(r"eq_calc: eqcalq: ierr=\s*(\d+)", p.stdout)
    assert m and int(m.group(1)) == 111, p.stdout[-2000:]


def test_eq_run_untraceable_surface_last_error_names_the_cause():
    """RR 6.2, RA 2.0, RB at its default (1.2), analytic solve: eq_run fails with a reason."""
    code = textwrap.dedent(f'''
        import sys
        sys.path.insert(0, {str(PYTHON_ROOT)!r})
        from eqlib import Eq
        from eqlib.errors import EqlibCalculationFailedError
        with Eq() as eq:
            eq.set_param("RR", 6.2); eq.set_param("RA", 2.0)
            try:
                eq.run(mode=0)
                print("RC 0")
            except EqlibCalculationFailedError:
                print("RC FAILED")
                print("MSG " + eq.last_error())
    ''')
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    assert "RC FAILED" in p.stdout, p.stdout[-2000:]
    msg = [l for l in p.stdout.splitlines() if l.startswith("MSG ")][0]
    assert "EQCALQP: EQMAGS could not trace the flux surface" in msg
    assert "RB smaller than the plasma radius RA" in msg


def test_untraceable_surface_ra_1p8_fails_without_ending_the_process():
    _assert_failed_cleanly(_child('t.set_param("RA", 1.8)'))


def test_untraceable_surface_ra_2p0_fails_without_ending_the_process():
    _assert_failed_cleanly(_child('t.set_param("RA", 2.0)'))
