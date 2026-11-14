"""libnf's D-T reactivity fit, pinned against tr's legacy SIGMAM.

P1 Task 5 ports trx's multi-reaction fusion module into `tr` as an ADDITIVE
path: `model_pnf` defaults to 0, nothing dispatches to libnf yet (Task 6), and
the legacy MDLNF/SIGMAM D-T path is untouched. So the two things worth
asserting now are (a) the port is inert at the default, and (b) the ported
spline reproduces the reactivity the existing code already computes.

Every tolerance below comes from a sweep run against this repo's own
libtrapi.so, not from a specification. The measured ratio
`sigmav_nf(DT,T) / SIGMAM(T,T)` is (both sides m^3/s; the 1e-6 that once
stood in this formula moved into sigmav_nf in Task 7):

      T[keV]     ratio          T[keV]     ratio
           1    1.0021              30    0.9895
           2    0.9997              50    1.0068
           3    1.0214              70    1.0092
           5    1.0054             100    0.9958
           7    1.0079             200    0.9622
          10    1.0118             300    0.9679
          15    0.9985             500    1.0579
          20    0.9895            1000    1.4573  <--

Two things that measurement settled:

* **Units.** `svnf_*` is tabulated in cm^3/s and `SIGMAM` returns m^3/s.
  sigmav_nf now applies the conversion itself, so no factor belongs here.
  Confirmed by the ratio landing on 1.0 at
  every table point rather than by reading a comment.
* **Where they disagree.** Since HengyuLi-Ozaki-lab/task-web-client#58 the
  fit is a cubic spline of log10(<sigma v>) over log10(T) through the table's
  ten knots (1, 2, 5, 10, ... 1000 keV).  The spline of <sigma v> itself that
  stood there before swung between the low knots, where the D-T table climbs
  by 3.4 decades from 1 to 5 keV: 12.2 times SIGMAM at 1.2 keV, 0.10 of it at
  2.5 keV and 0.40 at 3 keV.  On 1-5 keV the ratio is now 0.952-1.022 (every
  0.05 keV; the worst at 1.3 keV).  The one large deviation left is T=1000 keV (+46%),
  and **1000 keV is a table point**, so the interpolant is not implicated. The
  table says 2.7e-22 m^3/s and SIGMAM says 1.85e-22; published D-T
  reactivity at 1000 keV is nearer the former, so this is SIGMAM's analytic
  fit degrading far outside the range it was built for -- not a port defect
  and not something a tolerance should paper over.

  That is one reaction and one curve; enough to set tolerances, not enough to
  generalise about either function, so nothing here claims more.

A 1e-10 gate would be meaningless against a two-significant-figure table.
`test_matches_sigmam_at_table_points` uses 6% against a measured worst of
5.79%, `test_matches_sigmam_in_fusion_band` 1.3% against 1.18%, and
`test_matches_sigmam_below_5_kev` 5% against 4.82% -- so the headroom is
1.04x, 1.10x and 1.04x, not the "roughly 3x" an earlier draft claimed.
That is deliberate and it is not a flakiness risk: the table, the spline and
SIGMAM are all deterministic, so the cross-platform spread is
~1e-15 relative rather than tenths of a percent.  Tight bounds here mean a
real change in any of the three shows up as a failure instead of being
absorbed.  T=1000 keV is pinned separately rather than tolerated.
"""
from __future__ import annotations

import ctypes
import math
from pathlib import Path

import pytest

# Mangled names for gfortran: module procedures are __<module>_MOD_<name>,
# bare externals get a trailing underscore. SIGMAM is not in a module
# (tr/trpnf.f90 declares it at file scope), hence the asymmetry.
SYM_SETUP = "__libnf_MOD_set_usigmav_nf"
SYM_SIGMAV = "__libnf_MOD_sigmav_nf"
SYM_MODEL_PNF = "__trcomm_param_MOD_model_pnf"
SYM_SIGMAM = "sigmam_"

ID_NF_DT = 1  # tr/libnf.f90: id_nf_DT = 1

# Table temperatures, from `tempa` in tr/libnf.f90. The fit passes through the
# table here (test_fit_returns_the_table_at_its_knots); between them it
# interpolates log10(sigma-v) against log10(T).
# 1000.0 is a table point but is deliberately absent: SIGMAM, not the spline,
# is the outlier there (see the module docstring), so including it would force
# a tolerance loose enough to hide real spline regressions at every other
# point. It is pinned separately in test_known_large_deviations.
TABLE_POINTS = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0)

# The band that matters for a burning plasma, and where the spline is at its
# best. Includes off-table points deliberately -- an on-table-only test would
# not notice a broken interpolant.
FUSION_BAND = (5.0, 7.0, 10.0, 15.0, 20.0, 30.0, 50.0, 70.0, 100.0)

# Between the knots at 1, 2 and 5 keV, every 0.05 keV: where the D-T table
# climbs by 3.4 decades, the range HengyuLi-Ozaki-lab/task-web-client#58 was
# about.  RISE_GRID: 1 ... 50 keV, where every table rises.
LOW_GRID = tuple(1.0 + 0.05 * k for k in range(81))   # 1 ... 5 keV
RISE_GRID = tuple(1.0 + 0.05 * k for k in range(981))  # 1 ... 50 keV

TOL_TABLE = 0.06  # measured worst |ratio-1| over TABLE_POINTS: 0.0579 at 500 keV
TOL_BAND = 0.013  # measured worst over FUSION_BAND: 0.0118 at 10 keV (every 0.05 keV: 0.0126, 24.5 keV)
TOL_LOW = 0.05    # measured worst over LOW_GRID: 0.0482 at 1.3 keV

# Every reaction of tr/libnf.f90 (id_nf_DT = 1 ... id_nf_THe36 = 13), and
# its five tables with one reaction that reads each (sigmav_nf's SELECT CASE).
ALL_REACTIONS = tuple(range(1, 14))
TABLES = (("dt", 1), ("dd", 2), ("dhe3", 5), ("tt", 7), ("the3", 8))


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
    """The file trlib itself would load: its own resolver, so TRLIB_PATH,
    MONO_LIB_PATH, the installed location and the platform's file name are
    all the wrapper's, and this test cannot be on another artifact."""
    from trlib._ffi import _default_lib_path

    return Path(_default_lib_path())


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

    # Neither symbol is a reason to skip.  The only skip is the one above, a
    # library that was not built; a library that is there and lacks either
    # symbol is an error, and each message says where to look.
    try:
        lib[SYM_SIGMAV]
    except (AttributeError, ValueError):  # pragma: no cover
        # libnf is part of every libtrapi.so this tree builds: a missing
        # symbol is a renamed or hidden one, and skipping would hide it.
        raise AssertionError(
            f"{path} has no {SYM_SIGMAV}: libnf's sigmav_nf was renamed, "
            f"made PRIVATE, or left out of the library"
        ) from None
    try:
        model_pnf = ctypes.c_int.in_dll(lib, SYM_MODEL_PNF)
    except ValueError:
        raise AssertionError(
            f"{path} exports {SYM_SIGMAV} but not {SYM_MODEL_PNF}. The symbol "
            "was probably moved between trcomm submodules; update "
            "SYM_MODEL_PNF here rather than letting these tests skip."
        )

    # P1 Task 6 gave set_usigmav_nf an INTENT(OUT) ierr: upstream it reported
    # every failure with a bare STOP, which kills this pytest process from
    # inside the .so (CLAUDE.md; issue #142). Passing the argument is not
    # optional -- with argtypes=[] the callee writes its status through
    # whatever the register happens to hold.
    _setup = getattr(lib, SYM_SETUP)
    _setup.restype = None
    _setup.argtypes = [ctypes.POINTER(ctypes.c_int)]

    def setup():
        ierr = ctypes.c_int(-1)
        _setup(ctypes.byref(ierr))
        assert ierr.value == 0, (
            f"{SYM_SETUP} failed with ierr={ierr.value} at "
            f"model_pnf={model_pnf.value} (1=spline setup, 2=undefined "
            f"model_pnf, 3=species absent)"
        )

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
        _e = ctypes.c_int(-1)
        lib.{SYM_SETUP}(ctypes.byref(_e))   # INTENT(OUT) ierr (Task 6)
        assert _e.value == 0, _e.value
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
            """libnf's D-T <sigma v>, in m^3/s.

        The svnf_* tables are tabulated in cm^3/s; sigmav_nf converts at
        its exit, so what comes back here is already m^3/s and directly
        comparable with SIGMAM.
        """
            i = ctypes.c_int(ID_NF_DT)
            t = ctypes.c_double(float(t_kev))
            return sigmav(ctypes.byref(i), ctypes.byref(t))

        @staticmethod
        def sigmav(id_nf: int, t_kev: float) -> float:
            """libnf's <sigma v> of reaction ``id_nf`` (tr/libnf.f90), in m^3/s."""
            i = ctypes.c_int(int(id_nf))
            t = ctypes.c_double(float(t_kev))
            return sigmav(ctypes.byref(i), ctypes.byref(t))

        @staticmethod
        def sigmam(t_kev: float) -> float:
            """tr's legacy D-T <sigma v>, in m^3/s. Equal ion temperatures."""
            t = ctypes.c_double(float(t_kev))
            return sigmam(ctypes.byref(t), ctypes.byref(t))

        @staticmethod
        def ratio(t_kev: float) -> float:
            # No unit factor: sigmav_nf now returns m^3/s, the same units as
            # SIGMAM. Until Task 7 it returned the raw cm^3/s table and this
            # line carried a 1e-6, which meant the test could not have
            # noticed the missing conversion -- it asserted the ratio the
            # defect produced. The bare ratio pins the units too.
            return NF.sigmav_dt(t_kev) / NF.sigmam(t_kev)

    NF.lib = lib          # for the tests that read module state beside the calls
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
        _e = ctypes.c_int(-1)
        lib.{SYM_SETUP}(ctypes.byref(_e))   # INTENT(OUT) ierr (Task 6)
        assert _e.value == 0, _e.value
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
        f"sigmav_nf(DT,{t_kev} keV) / SIGMAM = {r:.4f}, off by "
        f"{abs(r - 1.0) * 100:.2f}% (limit {TOL_TABLE * 100:.0f}%).\n"
        "Both are meant to be the same analytic D-T fit, svnf_dt being it "
        "tabulated. A miss here means the spline construction, the table, or "
        "the cm^3/s -> m^3/s conversion changed."
    )


@pytest.mark.parametrize("t_kev", FUSION_BAND)
def test_matches_sigmam_in_fusion_band(nf, t_kev):
    """5-100 keV, including off-table points, at the tighter 1.3%.

    This is the range a burning plasma actually occupies. Measured worst
    case 1.18% at 10 keV. The off-table entries are the point: they are what
    would catch a broken interpolant that still happens to pass through every
    knot.
    """
    r = nf.ratio(t_kev)
    assert abs(r - 1.0) < TOL_BAND, (
        f"sigmav_nf(DT,{t_kev} keV) / SIGMAM = {r:.4f}, off by "
        f"{abs(r - 1.0) * 100:.2f}% (limit {TOL_BAND * 100:.0f}%)"
    )


def test_matches_sigmam_below_5_kev(nf):
    """1-5 keV, between the knots at 1, 2 and 5 keV, every 0.05 keV, at 5%.

    The D-T table climbs by 3.4 decades over this range.  The cubic
    spline of <sigma v> itself that fitted it before
    HengyuLi-Ozaki-lab/task-web-client#58 swung to 12.2 times SIGMAM at
    1.2 keV and 0.10 of it at 2.5 keV; the spline of log10(<sigma v>) keeps
    within 4.82% (0.952 at 1.3 keV).
    """
    # `not ... <`: a NaN ratio fails `<` and is reported, where `>=` would drop it.
    off = [(t, r) for t in LOW_GRID if not abs((r := nf.ratio(t)) - 1.0) < TOL_LOW]
    assert not off, (
        f"sigmav_nf(DT) / SIGMAM is off by {TOL_LOW * 100:.0f}% or more at "
        f"{len(off)} of {len(LOW_GRID)} temperatures on 1-5 keV, first "
        f"{off[0][0]:.2f} keV ({off[0][1]:.4f}), worst "
        f"{max(off, key=lambda x: abs(x[1] - 1.0))[1]:.4f}: the fit between "
        "the low knots changed"
    )


@pytest.mark.parametrize("table,id_nf", TABLES)
def test_fit_returns_the_table_at_its_knots(nf, table, id_nf):
    """At each temperature of `tempa` the fit gives the table's own value.

    The table and its temperatures are read from the library, so this checks,
    for each of the five tables and not against a copy of their numbers, that
    the fit passes through the table's points and that the cm^3/s -> m^3/s
    conversion is applied.  Any interpolating fit passes through them; what
    the tolerance adds is precision: measured worst 3.4e-14 relative (the old
    fit, 1.8e-12, fails it at T-He3, 2 keV).
    """
    tempa = list((ctypes.c_double * 10).in_dll(nf.lib, "__libnf_MOD_tempa"))
    table_cm3 = list((ctypes.c_double * 10).in_dll(nf.lib, f"__libnf_MOD_svnf_{table}"))
    for t_kev, cm3 in zip(tempa, table_cm3):
        got = nf.sigmav(id_nf, t_kev)
        # abs=0: approx's default abs of 1e-12 m^3/s would pass any value here (~1e-22)
        assert got == pytest.approx(cm3 * 1e-6, rel=1e-12, abs=0.0), (
            f"sigmav_nf(id_nf={id_nf}, {t_kev} keV) = {got!r} m^3/s; the "
            f"table svnf_{table} says {cm3!r} cm^3/s there"
        )


@pytest.mark.parametrize("table,id_nf", TABLES)
def test_rates_rise_from_1_to_50_kev(nf, table, id_nf):
    """Every table's rate rises with T from 1 to 50 keV, every 0.05 keV.

    The tables rise there (the first to fall is D-T's, between 50 and
    100 keV).  This holds the fit's shape between the points, which the sign
    test below no longer can: 10 to a power is never negative.  The cubic
    spline of <sigma v> itself that stood before
    HengyuLi-Ozaki-lab/task-web-client#58 fell between points for D-T,
    D-He3 and T-He3; with the log fit no table falls before 66.65 keV
    (D-T).
    """
    values = [nf.sigmav(id_nf, t) for t in RISE_GRID]
    # `not v1 > v0`: a NaN fails `>` and is reported.
    falls = [(t, v0, v1) for t, v0, v1 in zip(RISE_GRID[1:], values, values[1:])
             if not v1 > v0]
    assert not falls, (
        f"sigmav_nf(id_nf={id_nf}) does not rise at {len(falls)} of "
        f"{len(RISE_GRID) - 1} steps on 1-50 keV, first at {falls[0][0]:.2f} keV "
        f"({falls[0][1]:.3e} -> {falls[0][2]:.3e} m^3/s), where svnf_{table} rises"
    )


def test_known_large_deviations(nf):
    """Pin the known-bad point instead of tolerating it silently.

    T=1000 keV reads 146% of SIGMAM (a table point, so SIGMAM's fit rather
    than the spline). It is not introduced here, but leaving it unasserted
    would let a real change hide behind "it was always rough there". A wide
    bracket: the intent is to notice movement, not to fix these digits.  The
    deviations between the low knots that stood here too (12.2 times at
    1.2 keV, 0.10 at 2.5 keV, 0.40 at 3 keV) went with
    HengyuLi-Ozaki-lab/task-web-client#58; test_matches_sigmam_below_5_kev
    holds that range.
    """
    r1000 = nf.ratio(1000.0)
    assert 1.40 < r1000 < 1.52, (
        f"ratio at 1000 keV is {r1000:.4f}, measured 1.4573 when the port "
        "landed. This is a TABLE point, so a move here implicates SIGMAM or "
        "the table itself, not the interpolation."
    )


@pytest.mark.parametrize("id_nf", ALL_REACTIONS)
def test_reactivity_is_never_negative(nf, id_nf):
    """A reaction rate is not negative, anywhere on the table, for any reaction.

    The other tests here look at D-T only.  Every reaction shares the fit (ten
    knots at 1, 2, 5, 10, ... keV), and a cubic spline of a function that
    climbs by decades between two knots can dip below zero there.  Before
    HengyuLi-Ozaki-lab/task-web-client#58 the spline of <sigma v> itself did,
    for D-He3 (5, 6) on 2.05-4.70 keV and T-He3 (8-13) on 1.05-1.95 and
    5.10-8.55 keV, and SPL1DF succeeded, so libnf reported nothing.  A spline
    of log10(<sigma v>) has no sign to lose, so this now holds against a
    return to a fit of <sigma v> itself; test_rates_rise_from_1_to_50_kev
    holds the shape.
    """
    grid = [1.0 + 0.05 * k for k in range(19981)]      # 1 ... 1000 keV
    negative = [(t, v) for t in grid if (v := nf.sigmav(id_nf, t)) < 0.0]
    assert not negative, (
        f"sigmav_nf(id_nf={id_nf}) is negative at {len(negative)} of "
        f"{len(grid)} temperatures, from {negative[0][0]:.2f} to "
        f"{negative[-1][0]:.2f} keV; most negative "
        f"{min(v for _, v in negative):.3e} m^3/s"
    )


@pytest.mark.parametrize("id_nf", ALL_REACTIONS)
def test_reactivity_is_evaluated_and_finite(nf, id_nf):
    """Every reaction, over the whole table: a finite number, and no error counted.

    The sign test above cannot see a NaN or an infinity (`v < 0` is False for
    both), nor an evaluation that failed: sigmav_nf returns 0 when SPL1DF
    reports an error, and counts it in nf_error_count.
    """
    errors = ctypes.c_int.in_dll(nf.lib, "__libnf_MOD_nf_error_count")
    before = errors.value
    grid = [1.0 + 0.05 * k for k in range(19981)]      # 1 ... 1000 keV
    values = [nf.sigmav(id_nf, t) for t in grid]
    not_finite = [(t, v) for t, v in zip(grid, values) if not math.isfinite(v)]
    assert not not_finite, (
        f"sigmav_nf(id_nf={id_nf}) is not finite at {len(not_finite)} "
        f"temperatures, first {not_finite[0]}"
    )
    assert errors.value == before, (
        f"sigmav_nf(id_nf={id_nf}) counted {errors.value - before} evaluation "
        f"errors on 1-1000 keV (each returns 0, which the sign test accepts)"
    )
    assert any(v != 0.0 for v in values), f"sigmav_nf(id_nf={id_nf}) is 0 everywhere"


def test_below_table_floor_returns_zero(nf):
    """T < 1 keV short-circuits to 0 rather than extrapolating.

    tr/libnf.f90 guards this explicitly. Worth pinning because the
    alternative -- extrapolating a log-grid spline below its first knot --
    would produce large positive garbage in exactly the regime where the true
    reactivity is negligible.
    """
    assert nf.sigmav_dt(0.5) == 0.0
