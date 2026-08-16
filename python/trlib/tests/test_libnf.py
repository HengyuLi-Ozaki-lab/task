"""libnf's D-T reactivity spline, pinned against tr's legacy SIGMAM.

P1 Task 5 ports trx's multi-reaction fusion module into `tr` as an ADDITIVE
path: `model_pnf` defaults to 0, nothing dispatches to libnf yet (Task 6), and
the legacy MDLNF/SIGMAM D-T path is untouched. So the two things worth
asserting now are (a) the port is inert at the default, and (b) the ported
spline reproduces the reactivity the existing code already computes.

Every tolerance below comes from a sweep run against this repo's own
libtrapi.so, not from a specification. The measured ratio
`sigmav_nf(DT,T) * 1e-6 / SIGMAM(T,T)` is:

      T[keV]     ratio          T[keV]     ratio
           1    1.0021              30    0.9823
           2    0.9997              50    1.0068
           3    0.4012  <--         70    1.0086
           5    1.0054             100    0.9958
           7    0.9900             200    0.9622
          10    1.0118             300    0.9716
          15    1.0126             500    1.0579
          20    0.9895            1000    1.4573  <--

Two things that measurement settled, both contrary to what the project report
says:

* **Units.** `svnf_*` is tabulated in cm^3/s and `SIGMAM` returns m^3/s, so the
  comparison needs a 1e-6 factor. Confirmed by the ratio landing on 1.0 at
  every table point rather than by reading a comment.
* **Where they disagree.** The report describes a low-temperature overshoot
  below ~3 keV with good behaviour above. That is not what the sweep shows.
  T=1 and T=2 agree to 0.2%; the two large deviations are T=3 keV (-60%) and
  T=1000 keV (+46%), and they have different causes:

  - **3 keV** sits in the sparse 2->5 keV gap, where a spline through raw
    sigma-v against log10(T) undershoots. That one is the interpolant.
  - **1000 keV is a table point**, so the interpolant is not implicated. The
    table says 2.7e-22 m^3/s and SIGMAM says 1.85e-22; published D-T
    reactivity at 1000 keV is nearer the former, so this is SIGMAM's analytic
    fit degrading far outside the range it was built for -- not a port defect
    and not something a tolerance should paper over.

  That is one reaction and one curve; enough to set tolerances, not enough to
  generalise about either function, so nothing here claims more.

A 1e-10 gate would be meaningless against a two-significant-figure table.
`test_matches_sigmam_at_table_points` uses 6% against a measured worst of
5.79%, and `test_matches_sigmam_in_fusion_band` uses 2% against 1.77% -- so
the headroom is 1.04x and 1.13x, not the "roughly 3x" an earlier draft
claimed.  That is deliberate and it is not a flakiness risk: the table, the
spline and SIGMAM are all deterministic, so the cross-platform spread is
~1e-15 relative rather than tenths of a percent.  Tight bounds here mean a
real change in any of the three shows up as a failure instead of being
absorbed.  T=3 keV and 1000 keV are pinned separately rather than tolerated.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
REPO = _HERE.parents[3]

# Mangled names for gfortran: module procedures are __<module>_MOD_<name>,
# bare externals get a trailing underscore. SIGMAM is not in a module
# (tr/trpnf.f90 declares it at file scope), hence the asymmetry.
SYM_SETUP = "__libnf_MOD_set_usigmav_nf"
SYM_SIGMAV = "__libnf_MOD_sigmav_nf"
SYM_MODEL_PNF = "__trcomm_param_MOD_model_pnf"
SYM_SIGMAM = "sigmam_"

ID_NF_DT = 1  # tr/libnf.f90: id_nf_DT = 1

# Table temperatures, from `tempa` in tr/libnf.f90. The spline is exact-ish
# here by construction; between them it interpolates raw sigma-v against
# log10(T) and can wander badly.
# 1000.0 is a table point but is deliberately absent: SIGMAM, not the spline,
# is the outlier there (see the module docstring), so including it would force
# a tolerance loose enough to hide real spline regressions at every other
# point. It is pinned separately in test_known_large_deviations.
TABLE_POINTS = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0)

# The band that matters for a burning plasma, and where the spline is at its
# best. Includes off-table points deliberately -- an on-table-only test would
# not notice a broken interpolant.
FUSION_BAND = (5.0, 7.0, 10.0, 15.0, 20.0, 30.0, 50.0, 70.0, 100.0)

TOL_TABLE = 0.06  # measured worst |ratio-1| over TABLE_POINTS: 0.0579 at 500 keV
TOL_BAND = 0.02   # measured worst over FUSION_BAND: 0.0177 at 30 keV
CM3_PER_M3 = 1.0e-6


def _parses_as_float(stdout: str) -> bool:
    """True only if the probe actually printed a number.

    The signal that matters is the value, not the exit status: a Fortran STOP
    ends the process with rc=0, so the library can die and still look like a
    clean run.
    """
    lines = [ln for ln in stdout.strip().splitlines() if ln.strip()]
    if not lines:
        return False
    try:
        float(lines[-1])
    except ValueError:
        return False
    return True


def _lib_path() -> Path:
    """Resolve libtrapi.so the same way trlib does, so this test and the
    wrapper never disagree about which artifact is under test."""
    env = os.environ.get("TRLIB_PATH")
    if env:
        return Path(env)
    return REPO / "tr" / "libtrapi.so"


@pytest.fixture(scope="module")
def nf():
    """Load libtrapi.so and build the reactivity splines.

    `set_usigmav_nf` is called with model_pnf left at its default 0. That is
    not incidental: upstream, the spline setup sat after CASE(0)'s RETURN, so
    at the default the tables stayed empty and any sigmav_nf call walked into
    SPL1DF's degenerate-grid guard and STOPped the host process. The port
    moves the setup ahead of the dispatch, and this fixture is what would
    catch a regression of that.
    """
    path = _lib_path()
    if not path.exists():
        pytest.skip(f"{path} not built; run `make -C tr libtrapi.so`")
    lib = ctypes.CDLL(str(path))

    # Gate the skip on libnf itself being absent, not on model_pnf. If the
    # library HAS libnf but model_pnf has moved -- Task 6 may well relocate it
    # between trcomm_param and trcomm_ctrl -- skipping all 22 tests with
    # "predates the libnf port" would be actively misleading. Then it is an
    # error, and the message says where to look.
    try:
        lib[SYM_SIGMAV]
    except (AttributeError, ValueError):  # pragma: no cover
        pytest.skip(f"{path} predates the libnf port ({SYM_SIGMAV} absent)")
    try:
        model_pnf = ctypes.c_int.in_dll(lib, SYM_MODEL_PNF)
    except ValueError:
        raise AssertionError(
            f"{path} exports {SYM_SIGMAV} but not {SYM_MODEL_PNF}. The symbol "
            "was probably moved between trcomm submodules; update "
            "SYM_MODEL_PNF here rather than letting these tests skip."
        )

    setup = getattr(lib, SYM_SETUP)
    setup.restype = None
    setup.argtypes = []

    sigmav = getattr(lib, SYM_SIGMAV)
    sigmav.restype = ctypes.c_double
    sigmav.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double)]

    sigmam = getattr(lib, SYM_SIGMAM)
    sigmam.restype = ctypes.c_double
    sigmam.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]

    assert model_pnf.value == 0, (
        f"{SYM_MODEL_PNF} is {model_pnf.value} at load time, not 0. Option A's "
        "guarantee is that the libnf path is off unless someone asks for it; "
        "the default lives in the declaration at tr/trcomm_param.f90."
    )
    # Health check BEFORE any in-process call into the library.
    #
    # Every test below evaluates sigmav_nf in this process. If the spline
    # setup has moved back behind the model_pnf dispatch, that call does not
    # raise -- it takes the interpreter down, and measured under --forked
    # pytest turns that into INTERNALERROR / "no tests ran", losing the whole
    # session rather than one file. Protecting only the one test that names
    # the hazard is not enough: the ratio tests reach the same code.
    #
    # So probe once in a subprocess and fail the fixture if it dies. Every
    # test then errors with this message instead of the session collapsing.
    import subprocess
    import sys
    import textwrap

    probe = textwrap.dedent(
        f"""
        import ctypes
        lib = ctypes.CDLL({str(path)!r})
        lib.{SYM_SETUP}()
        f = lib.{SYM_SIGMAV}
        f.restype = ctypes.c_double
        f.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double)]
        i = ctypes.c_int({ID_NF_DT})
        t = ctypes.c_double(10.0)
        print(repr(f(ctypes.byref(i), ctypes.byref(t))))
        """
    )
    health = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    # Judge on the OUTPUT, not the return code. A bare Fortran STOP exits 0 --
    # measured: the broken library prints "XX SPL1DF error in sigmav_nf" and
    # the process ends with rc=0. A returncode check would sail straight past
    # it, which is exactly what an earlier version of this guard did.
    if not _parses_as_float(health.stdout):
        raise AssertionError(
            f"the sigmav_nf(DT, 10 keV) probe produced no value at "
            f"model_pnf=0 (rc={health.returncode}), so calling it in-process "
            f"would end this pytest session. The spline setup in "
            f"tr/libnf.f90 has most likely moved back behind the model_pnf "
            f"dispatch.\nstdout: {health.stdout[-300:]}\n"
            f"stderr: {health.stderr[-300:]}"
        )

    setup()

    class NF:
        @staticmethod
        def sigmav_dt(t_kev: float) -> float:
            """libnf's D-T <sigma v>, in cm^3/s as tabulated."""
            i = ctypes.c_int(ID_NF_DT)
            t = ctypes.c_double(float(t_kev))
            return sigmav(ctypes.byref(i), ctypes.byref(t))

        @staticmethod
        def sigmam(t_kev: float) -> float:
            """tr's legacy D-T <sigma v>, in m^3/s. Equal ion temperatures."""
            t = ctypes.c_double(float(t_kev))
            return sigmam(ctypes.byref(t), ctypes.byref(t))

        @staticmethod
        def ratio(t_kev: float) -> float:
            return NF.sigmav_dt(t_kev) * CM3_PER_M3 / NF.sigmam(t_kev)

    return NF


def test_default_is_off(nf):
    """model_pnf must be 0 in a freshly loaded library.

    This is the whole of Option A stated as an assertion: the multi-reaction
    path exists but nothing selects it, so every committed baseline is
    reached by exactly the code path it was captured with.
    """
    # Not a second, independent load: measured, ctypes returns the SAME
    # handle and address for a repeat CDLL of the same path, so this observes
    # the memory the fixture already touched. What makes it meaningful is
    # --forked -- each test gets a fresh process, hence a fresh library.
    lib = ctypes.CDLL(str(_lib_path()))
    assert ctypes.c_int.in_dll(lib, SYM_MODEL_PNF).value == 0


def test_setup_survives_the_default(nf):
    """sigmav_nf must return a number at model_pnf=0, not kill the process.

    Upstream this STOPped: the spline setup ran only after the dispatch, so at
    the default the grid was all zeros and SPL1DF's degenerate-grid guard took
    the process down.

    Run in a SUBPROCESS, because an in-process regression here is worse than a
    red test. Measured against a library with the move reverted: under
    --forked pytest raises EOFError and reports INTERNALERROR, exit 3, "no
    tests ran" -- the whole session, not just this file. Without --forked, a
    bare Fortran STOP exits 0 and pytest reports a silent green. Either way
    the signal is lost. A subprocess turns both into one failing assertion.
    """
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent(
        f"""
        import ctypes
        lib = ctypes.CDLL({str(_lib_path())!r})
        lib.{SYM_SETUP}()
        f = lib.{SYM_SIGMAV}
        f.restype = ctypes.c_double
        f.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double)]
        i = ctypes.c_int({ID_NF_DT})
        t = ctypes.c_double(10.0)
        print(repr(f(ctypes.byref(i), ctypes.byref(t))))
        """
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert _parses_as_float(proc.stdout), (
        f"sigmav_nf(DT, 10 keV) at model_pnf=0 produced no value "
        f"(rc={proc.returncode} -- note a bare Fortran STOP exits 0, so the "
        f"return code proves nothing here). The spline setup has most likely "
        f"moved back behind the model_pnf dispatch in tr/libnf.f90.\n"
        f"stdout: {proc.stdout[-300:]}\nstderr: {proc.stderr[-300:]}"
    )
    v = float(proc.stdout.strip().splitlines()[-1])
    assert v > 0.0, f"sigmav_nf(DT, 10 keV) returned {v!r}"


@pytest.mark.parametrize("t_kev", TABLE_POINTS)
def test_matches_sigmam_at_table_points(nf, t_kev):
    """At tabulated temperatures the ported spline reproduces SIGMAM.

    Tolerance 6%: the measured worst case over these points is 5.79% at
    500 keV, and the table itself carries only two significant figures, so
    anything tighter would be pinning rounding noise.  (1000 keV is excluded
    from this set -- see the module docstring.)
    """
    r = nf.ratio(t_kev)
    assert abs(r - 1.0) < TOL_TABLE, (
        f"sigmav_nf(DT,{t_kev} keV)*1e-6 / SIGMAM = {r:.4f}, off by "
        f"{abs(r - 1.0) * 100:.2f}% (limit {TOL_TABLE * 100:.0f}%).\n"
        "Both are meant to be the same analytic D-T fit, svnf_dt being it "
        "tabulated. A miss here means the spline construction, the table, or "
        "the cm^3/s -> m^3/s conversion changed."
    )


@pytest.mark.parametrize("t_kev", FUSION_BAND)
def test_matches_sigmam_in_fusion_band(nf, t_kev):
    """5-100 keV, including off-table points, at the tighter 2%.

    This is the range a burning plasma actually occupies, and the one where
    the interpolant behaves. Measured worst case 1.77% at 30 keV. The
    off-table entries are the point: they are what would catch a broken
    interpolant that still happens to pass through every knot.
    """
    r = nf.ratio(t_kev)
    assert abs(r - 1.0) < TOL_BAND, (
        f"sigmav_nf(DT,{t_kev} keV)*1e-6 / SIGMAM = {r:.4f}, off by "
        f"{abs(r - 1.0) * 100:.2f}% (limit {TOL_BAND * 100:.0f}%)"
    )


def test_known_large_deviations(nf):
    """Pin the known-bad points instead of tolerating them silently.

T=3 keV reads 40% of SIGMAM (sparse 2->5 keV interval, the interpolant);
    T=1000 keV reads 146% (a table point, so SIGMAM's fit rather than the
    spline). Neither is introduced here, but leaving them unasserted would let
    a real change hide behind "it was always rough there". Wide brackets: the
    intent is to notice movement, not to fix these digits.
    """
    r3 = nf.ratio(3.0)
    r1000 = nf.ratio(1000.0)
    assert 0.35 < r3 < 0.45, (
        f"ratio at 3 keV is {r3:.4f}, measured 0.4012 when the port landed. "
        "This point is in the sparse 2->5 keV interval; a move here means the "
        "spline construction changed."
    )
    assert 1.40 < r1000 < 1.52, (
        f"ratio at 1000 keV is {r1000:.4f}, measured 1.4573 when the port "
        "landed. This is a TABLE point, so a move here implicates SIGMAM or "
        "the table itself, not the interpolation."
    )


def test_below_table_floor_returns_zero(nf):
    """T < 1 keV short-circuits to 0 rather than extrapolating.

    tr/libnf.f90 guards this explicitly. Worth pinning because the
    alternative -- extrapolating a log-grid spline below its first knot --
    would produce large positive garbage in exactly the regime where the true
    reactivity is negligible.
    """
    assert nf.sigmav_dt(0.5) == 0.0
