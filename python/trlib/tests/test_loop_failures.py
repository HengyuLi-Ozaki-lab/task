"""Library mode: a failure inside the time loop returns an error with a record; the process lives.

``tr_run`` used to return ``TR_ERR_CALC_FAILED`` with nothing to say what failed, and a
failure in the periodic equilibrium re-solve (``NTEQIT``) was not tested at all: the run went on
with an equilibrium that had not converged. In library mode (``tr_init`` sets it; ``tr2`` never
does) ``tr_loop`` now stops at the first failed ``eq_calc`` or at a non-finite state, and
``tr_last_error`` gives the kind, the Fortran code, the step and the time.

Every case that can reach a Fortran ``STOP`` or a long run is a child process. One test per case,
no ``subTest``. Skipped when ``libtrapi.so`` has not been built.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

pytestmark = pytest.mark.skipif(not DEFAULT_SO.exists(), reason="libtrapi.so not built")

sys.path.insert(0, str(PYTHON_ROOT))
from trlib import TrFailure, TrlibRunError  # noqa: E402
from trlib.errors import TrlibError  # noqa: E402


def _child(body: str) -> subprocess.CompletedProcess:
    code = (
        "import sys\nsys.path.insert(0, %r)\n" % str(PYTHON_ROOT)
        + "from trlib import Trlib, TrlibRunError\n"
        + textwrap.dedent(body)
    )
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=900)


# The flat 9 MA ITER case of the spec's section 4, with the heating of the staged scenario.
ITER_M9 = '''
t = Trlib()
for k, v in dict(MODELG=9, RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33, BB=5.3, NSMAX=4, DT=0.02).items():
    t.set_param(k, v)
t.set_param("eq:RB", 2.1); t.set_param("eq:NSGMAX", 128)
for nm, vals in dict(PN=[0.7, 0.315, 0.315, 0.035], PNS=[0.1, 0.045, 0.045, 0.005],
                     PT=[1.0] * 4, PTS=[0.1] * 4).items():
    for i, v in enumerate(vals):
        t.set_param("%s[%d]" % (nm, i + 1), v)
t.set_param("PROFN2", 0.15); t.set_param("MDLNF", 1)
for k, v in dict(PNBR0=0.0, PNBRW=1.0, PNBENG=1000.0, PNBRTG=6.2, PICCD=0.1, PICR0=0.0, PICRW=0.2,
                 PICNPR=5.0, PECCD=0.5, PECR0=1.1, PECRW=0.05, PECNPR=5.0, PLHCD=1.0, PLHR0=0.8,
                 PLHRW=0.2, PLHNPR=2.0, PNBTOT=25.0, PICTOT=5.0, PECTOT=20.0).items():
    t.set_param(k, v)
t.set_param("RIPS", 9.0); t.set_param("RIPE", 9.0)
'''


def test_the_failure_record_is_a_frozen_dataclass():
    f = TrFailure(kind="EQ_FAILED", code=110, nt=3, time=0.06, detail="x")
    assert (f.kind, f.code, f.nt, f.time) == ("EQ_FAILED", 110, 3, 0.06)
    with pytest.raises(Exception):
        f.kind = "OTHER"  # type: ignore[misc]


def test_a_run_error_carries_the_failure_and_defaults_to_none():
    assert TrlibRunError("x").failure is None
    f = TrFailure("OTHER", 1, 0, 0.0, "")
    assert TrlibRunError("x", failure=f).failure == f


def test_a_failed_q_scaling_is_recorded_as_eq_failed():
    # RIPS=100: the first equilibrium solve of the initial q-scaling fails (test_modelg9_init.py)
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9); t.set_param("RIPS", 100.0); t.set_param("RIPE", 100.0)
        try:
            t.run(0); print("RC 0")
        except TrlibRunError as e:
            print("RC", e.failure.kind, e.failure.code, e.failure.nt)
            print("MSG", e.failure.detail)
        print("LAST", t.last_error().kind)
    ''')
    assert p.returncode == 0, p.stderr[-2000:]
    assert "RC EQ_FAILED" in p.stdout, p.stdout[-1500:]
    assert "LAST EQ_FAILED" in p.stdout
    assert "q-scaling" in p.stdout


def test_a_q_scaling_failure_carries_eq_s_message():
    # RA 1.8 under MODELG 9 (RB stays 2.0 outside it): EQCALQP fails the first solve with code 111, and the record's
    # detail ends with EQ's own EQ_ERRMSG text, not only TR's "where".
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9); t.set_param("RA", 1.8)
        try:
            t.run(0); print("RC 0")
        except TrlibRunError as e:
            print("RC", e.failure.kind, e.failure.code)
            print("MSG", e.failure.detail)
            print("FULL", e)
    ''')
    assert p.returncode == 0, p.stderr[-2000:]
    assert "RC EQ_FAILED 111" in p.stdout, p.stdout[-1500:]
    msg = [l for l in p.stdout.splitlines() if l.startswith("MSG ")][0]
    assert "q-scaling" in msg and "EQCALQ" in msg, msg


def test_flat_9ma_with_nteqit_50_stops_before_25_s():
    # tr2 goes on after "XX EQAXIS: AXIS NOT FOUND" at 1 s and ends with a state that means nothing.
    # Slow (about 37 s): the failure is at nt 600, t 12 s, and no shorter case fails the same way.
    p = _child(ITER_M9 + '''
t.set_param("NTEQIT", 50)
try:
    t.run(1250); print("RC 0")       # 25 s at DT 0.02
except TrlibRunError as e:
    print("RC", e.failure.kind, e.failure.time, e.failure.nt)
    # the handle stays usable after the failure
    t.set_param("NTEQIT", 0)
    print("STATE", type(t.get_state()).__name__)
''')
    assert p.returncode == 0, p.stderr[-2000:]
    assert "RC 0" not in p.stdout, "the run was expected to fail"
    assert "STATE TrState" in p.stdout
    kind, time, nt = p.stdout.split("RC ")[1].split()[:3]
    assert kind in ("EQ_FAILED", "NONFINITE") and float(time) < 25.0
    assert int(nt) % 50 == 0 or kind == "NONFINITE"


def test_a_non_finite_state_ends_the_run_with_nonfinite():
    # DT = 1e6 s: the state is NaN after the second step; without library mode the run returns 0
    p = _child('''
        t = Trlib()
        t.set_param("DT", 1.0e6)
        try:
            t.run(30); print("RC 0")
        except TrlibRunError as e:
            f = e.failure
            print("RC", f.kind, f.nt, f.time, f.code)
    ''')
    assert p.returncode == 0, p.stderr[-2000:]
    rc = [l.split() for l in p.stdout.splitlines() if l.startswith("RC ")]
    assert len(rc) == 1, p.stdout[-800:]
    kind, nt, time, code = rc[0][1:]
    assert (kind, nt, code) == ("NONFINITE", "2", "-3") and time.startswith("2000000"), p.stdout[-800:]


def test_a_negative_temperature_is_recorded_as_tr_check():
    # DT = 100 s: TRCHCK finds a negative temperature at step 8
    p = _child('''
        t = Trlib()
        t.set_param("DT", 100.0)
        try:
            t.run(30); print("RC 0")
        except TrlibRunError as e:
            f = e.failure
            print("RC", f.kind, f.code, f.nt)
    ''')
    assert p.returncode == 0, p.stderr[-2000:]
    assert "RC TR_CHECK 1 8" in p.stdout, p.stdout[-800:]


def test_last_error_is_none_on_a_fresh_handle():
    p = _child('''
        t = Trlib()
        print("KIND", t.last_error().kind)
    ''')
    assert "KIND NONE" in p.stdout, p.stderr[-1500:]


def test_last_error_is_cleared_by_a_good_run():
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9); t.set_param("RIPS", 100.0); t.set_param("RIPE", 100.0)
        try: t.run(0)
        except TrlibRunError: pass
        print("AFTER_FAIL", t.last_error().kind)
        t.set_param("MODELG", 2); t.set_param("RIPS", 3.0); t.set_param("RIPE", 3.0); t.run(2)
        print("KIND", t.last_error().kind)
    ''')
    assert "AFTER_FAIL EQ_FAILED" in p.stdout, p.stdout[-1500:] + p.stderr[-1500:]
    assert "KIND NONE" in p.stdout


def test_a_new_handle_starts_with_no_failure():
    # a failure, close, a new handle: the record of the first lifecycle is gone
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9); t.set_param("RIPS", 100.0); t.set_param("RIPE", 100.0)
        try: t.run(0)
        except TrlibRunError: pass
        print("FIRST", t.last_error().kind)
        t.close()
        t2 = Trlib()
        print("SECOND", t2.last_error().kind)
    ''')
    assert "FIRST EQ_FAILED" in p.stdout, p.stdout[-800:] + p.stderr[-800:]
    assert "SECOND NONE" in p.stdout


def test_an_old_library_without_tr_last_error_still_raises_run_error():
    class OldLib:  # a libtrapi.so built before tr_last_error: the symbol is absent
        def tr_run(self, n):
            return 3

    from trlib import Trlib
    t = Trlib()
    real = t._lib
    t._lib = OldLib()
    try:
        with pytest.raises(TrlibRunError) as ei:
            t.run(1)
        assert ei.value.failure is None
    finally:
        t._lib = real
        t.close()
