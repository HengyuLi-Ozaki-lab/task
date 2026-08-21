"""P1 Task 6: the model_pnf dispatch into the ported multi-reaction path.

What this pins is the *contract* of the dispatch, not the physics the ported
routines compute -- cross-validating the reaction sources against trx is P1
Task 7.  Concretely:

* ``model_pnf`` reaches the library at all (it is registered in
  ``tr_param_registry``; before Task 6 it was declared but unreachable, so
  the dispatch was dead code no caller could switch on);
* each accepted value derives the reaction count the ported ``set_usigmav_nf``
  documents, and arms ``nf_multi_ready``;
* the default (0) leaves the path disarmed;
* changing only ``model_pnf`` between runs resizes the ``trcomm_nf`` arrays,
  even though ``ALLOCATE_TRCOMM``'s early-return guard does not watch
  ``nnfmax``;
* an undefined value is refused through ``ierr`` rather than by aborting --
  ``set_usigmav_nf`` answered this with a bare ``STOP`` before this branch
  converted it, and a ``STOP`` reached through the ``.so`` kills the host
  process (CLAUDE.md, Fortran library discipline; issue #142);
* ``model_pnf`` is reset by ``tr_init``, so a second in-process session does
  not inherit the first one's value;
* the reaction loop is exercised above ``sigmav_nf``'s 1 keV table floor,
  which no committed fixture reaches on its own.

The flags are read straight out of the shared library because they are
module-scope state with no accessor on the C ABI -- adding one purely for a
test would widen the ABI for no caller.  Both are plain integers/logicals, so
``ctypes.c_int.in_dll`` is well defined for them. The allocatable arrays are
read too, through the first word of their gfortran descriptor -- see
``_read_source_array``. That is a compiler implementation detail rather than a
documented ABI, so it is confined to the two helpers that do it, and used only
where the alternative would be widening the C ABI with an accessor no caller
wants.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path

import pytest

from trlib import Trlib
from trlib.errors import TrlibError

from .fixtures import tr_tst2_params as FIXTURE

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REPO = Path(__file__).resolve().parents[3]
HOT_BASELINE_DIR = REPO / "test_run" / "baselines" / "tr_fus_dt_hot"

# gfortran mangling: __<module>_MOD_<lowercased name>
SYM_READY = "__trcomm_nf_MOD_nf_multi_ready"
SYM_NNFMAX = "__trcomm_ctrl_MOD_nnfmax"
SYM_NF_ERR = "__libnf_MOD_nf_last_error"
SYM_NF_COUNT = "__libnf_MOD_nf_error_count"
SYM_MODEL_PNF = "__trcomm_param_MOD_model_pnf"

# From tr/libnf.f90::set_usigmav_nf. 12 and 14 are aliases of 2 and 4 that
# select the same reaction set, so they must agree with their base value.
REACTION_COUNT = {0: 0, 1: 1, 2: 4, 3: 6, 4: 13, 12: 4, 14: 13}

UNDEFINED_MODEL_PNF = 9


def _lib() -> ctypes.CDLL:
    """The same shared object Trlib drives.

    Resolved through the wrapper's own loader so this honours TRLIB_PATH /
    MONO_LIB_PATH exactly as the rest of the suite does; dlopen returns the
    already-mapped image, so ``in_dll`` reads the live module state.
    """
    from trlib._ffi import load_library

    return load_library()


@pytest.fixture()
def probe(monkeypatch):  # noqa: PT004 (yield fixture)
    """Run one fixture case at a given model_pnf; report the resulting state.

    Chdir into the fixtures directory because tr_tst2 is a MODELG=3 case and
    tr_prep loads the eqdata file named by KNAMEQ from the working directory.
    """
    lib = _lib()
    monkeypatch.chdir(FIXTURES_DIR)

    def run(model_pnf: int) -> dict:
        with Trlib() as tr:
            FIXTURE.apply(tr)
            tr.set_param("model_pnf", model_pnf)
            tr.run(1)
            return {
                "nnfmax": ctypes.c_int.in_dll(lib, SYM_NNFMAX).value,
                "ready": bool(ctypes.c_int.in_dll(lib, SYM_READY).value),
            }

    try:
        yield run
    finally:
        # model_pnf lives in module state that outlives a finalize. Under
        # --forked this fixture's process dies anyway, but a plain pytest run
        # shares one interpreter, and leaking model_pnf=14 into whatever runs
        # next would silently put it on the new path.
        ctypes.c_int.in_dll(lib, SYM_MODEL_PNF).value = 0


def test_model_pnf_is_settable():
    """Registered in tr_param_registry -- otherwise the dispatch is dead code."""
    with Trlib() as tr:
        tr.set_param("model_pnf", 0)


def test_model_pnf_accepts_the_uppercase_spelling():
    """Every other registry entry is uppercase and the CASE compare is literal."""
    with Trlib() as tr:
        tr.set_param("MODEL_PNF", 0)


@pytest.mark.parametrize("model_pnf", sorted(REACTION_COUNT))
def test_reaction_count_and_arming(probe, model_pnf):
    state = probe(model_pnf)
    assert state["nnfmax"] == REACTION_COUNT[model_pnf], (
        f"model_pnf={model_pnf} should select {REACTION_COUNT[model_pnf]} "
        f"reactions, got {state['nnfmax']}"
    )
    # The path is armed exactly when there is something to evaluate.
    assert state["ready"] is (model_pnf != 0)


def test_default_leaves_the_path_disarmed(probe):
    """model_pnf=0 is the default; the legacy MDLNF path must own the run.

    Arms the path first. Asserting {0, False} from a cold process would only
    be reading the module initialisers (trcomm_ctrl.f90's nnfmax=0 and
    trcomm_nf.f90's nf_multi_ready=.FALSE.) and would still pass with the
    whole dispatch deleted; coming back to 0 from 4 is the real claim.
    """
    assert probe(4) == {"nnfmax": 13, "ready": True}
    assert probe(0) == {"nnfmax": 0, "ready": False}


def test_switching_model_pnf_resizes(probe):
    """ALLOCATE_TRCOMM's early-return guard does not watch nnfmax.

    nrmax/nsmax/nszmax/nsnmax are identical across these three runs, so the
    guard short-circuits; only allocate_trcomm_nf's own size check makes the
    second and third runs correct.  Without it tr_prep_pnf refuses with
    ierr=3, which tr_prep propagates and tr_api_run maps to
    TR_ERR_CALC_FAILED -- so the symptom is a raised TrlibRunError, not a
    False `ready`.
    """
    assert probe(1)["nnfmax"] == 1
    assert probe(4) == {"nnfmax": 13, "ready": True}
    assert probe(1) == {"nnfmax": 1, "ready": True}


def _read_source_array(lib, symbol, nstm, nnfmax, nrmax):
    """Read a (NSTM,nnfmax,NRMAX) allocatable out of the loaded image.

    gfortran lays an array descriptor out with base_addr as its first word,
    so the descriptor symbol's first pointer-sized field is the data. That is
    an implementation detail of the compiler, not a documented ABI -- it is
    used here rather than widening the C ABI with an accessor that no caller
    would want, and it is confined to this helper. Returns column-major data
    flat, i.e. index (ns-1) + nstm*(nnf-1) + nstm*nnfmax*(nr-1).
    """
    addr = ctypes.c_void_p.in_dll(lib, symbol)
    assert addr.value, f"{symbol} is not allocated"
    return list((ctypes.c_double * (nstm * nnfmax * nrmax)).from_address(addr.value))


def _read_source_array_2d(lib, symbol, n1, n2):
    """Read a rank-2 allocatable; see _read_source_array for the caveat."""
    addr = ctypes.c_void_p.in_dll(lib, symbol)
    assert addr.value, f"{symbol} is not allocated"
    return list((ctypes.c_double * (n1 * n2)).from_address(addr.value))


def test_reaction_loop_runs_and_its_output_is_reset_every_step(monkeypatch):
    """Drive tr_pnf where it computes something, and pin the per-step reset.

    Every committed fixture sits at or below sigmav_nf's 1 keV table floor
    (tr_tst2 at ~0.01 keV; tr_iter01 and tr_m0904 at exactly 1.0 keV, the
    first knot), so without raising PT the ported reaction loop evaluates to
    zero everywhere and every assertion about it would hold vacuously. This
    uses tr_iter01 -- a real 4-species (e,D,T,He4) case, so PA/PZ/PN stay
    consistent -- and lifts PT well inside the table. Raising NSMAX on a
    2-species fixture instead does not work: the unset PA/PZ for the added
    species yield a NaN temperature.

    Two independent assertions, because neither alone covers the reset:

    1. ABSOLUTE. SNF in the dd2 slice must equal one step's worth,
       wgt * RN(D)^2 * 1e20 * sigmav_nf(dd2, RT(D)), recomputed here from
       the post-run state with sigmav_nf called through the same ctypes
       binding test_libnf.py uses. tr_pnf accumulates with +/-, so if the
       resets were dropped entirely this reads N times too large. wgt=0.5
       for dd2 (tr/libnf.f90).

    2. STOICHIOMETRIC. Within one reaction's slice, dd2 is
       D + D -> T + <p>: both reactants are D and the tracked product is H,
       so the D slot takes -SNF twice and the H slot +SNF once, ratio
       exactly -2. This one is insensitive to a symmetric loss of the reset
       (both slots would scale together) but catches an ASYMMETRIC bound:
       D is at ns=2 and H at NS_H=6 with NSMAX=4, so a reset bounded by
       1:NSMAX -- as in trx, whose arrays are NSMAX-dimensioned, rather
       than 1:NSTM as they are here -- clears D and not H. Verified
       discriminating: restoring that bound makes the ratio read -0.039.

    The -0.039 is not -2/NSTEPS. tr_pnf runs once per TRCALC, and TRCALC
    runs LMAXTR times in the converge loop plus once after it plus once in
    tr_eval, so the denominator is the number of tr_pnf calls (~51 over
    these 5 steps), not the number of steps.
    """
    from .fixtures import tr_iter01_params as HOT

    lib = _lib()
    monkeypatch.chdir(FIXTURES_DIR)

    NSTM = 8
    NNFMAX = REACTION_COUNT[2]      # dt, dd1, dd2, dd3
    NNF_DD2, ID_NF_DD2, WGT_DD2 = 3, 3, 0.5   # slot, libnf id, weight
    NS_D, NS_H = 2, 6
    NSTEPS = 5

    sigmav = lib.__libnf_MOD_sigmav_nf
    sigmav.restype = ctypes.c_double
    sigmav.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double)]

    with Trlib() as tr:
        HOT.apply(tr)
        for i in range(1, 5):
            tr.set_param(f"PT[{i}]", 20.0)   # keV, well inside the table
            tr.set_param(f"PTS[{i}]", 2.0)
        # tr_iter01 ships MDLNF=1, and tr_prep refuses both switches at once:
        # they write the same SNF/PNF/TAUF and would double-count the D-T
        # alphas, once from SIGMAM and once from libnf.
        tr.set_param("MDLNF", 0)
        tr.set_param("model_pnf", 2)
        tr.set_param("NTMAX", NSTEPS)
        tr.run(NSTEPS)

        # nf_error_count, not nf_last_error: tr_pnf clears the latter at
        # entry and runs ~51 times over these 5 steps, so it only describes
        # the final call and a failure inside the converge loop leaves no
        # trace in it. The counter is never cleared by tr_pnf.
        assert ctypes.c_int.in_dll(lib, SYM_NF_COUNT).value == 0, (
            "sigmav_nf tripped a guard that used to be a bare STOP: "
            f"nf_error_count={ctypes.c_int.in_dll(lib, SYM_NF_COUNT).value}, "
            f"last code {ctypes.c_int.in_dll(lib, SYM_NF_ERR).value} "
            "(1=id_nf range, 2=NaN or >1000 keV, 3=spline)"
        )
        assert bool(ctypes.c_int.in_dll(lib, SYM_READY).value)
        assert ctypes.c_int.in_dll(lib, SYM_NNFMAX).value == NNFMAX, (
            "nnfmax moved; the strides below would read the wrong elements"
        )

        nsmax = ctypes.c_int.in_dll(lib, "__trcom0_MOD_nsmax").value
        nrmax = ctypes.c_int.in_dll(lib, "__trcom0_MOD_nrmax").value
        # TRCALC reassigns NRMAX to NROMAX/NRAMAX when RHOA /= 1, while these
        # arrays keep the extent ALLOCATE_TRCOMM gave them -- the strides
        # below would then read the wrong elements, silently.
        rhoa = ctypes.c_double.in_dll(lib, "__trcomm_ctrl_MOD_rhoa").value
        assert rhoa == 1.0, (
            f"RHOA={rhoa} != 1; NRMAX is no longer the allocated extent and "
            f"the raw-descriptor strides in this test are invalid"
        )
        snf = _read_source_array(
            lib, "__trcomm_nf_MOD_snf_nsnnfnr", NSTM, NNFMAX, nrmax
        )
        rn = _read_source_array_2d(lib, "__trcomm_profile_MOD_rn", nrmax, NSTM)
        rt = _read_source_array_2d(lib, "__trcomm_profile_MOD_rt", nrmax, NSTM)

    assert NS_H > nsmax, (
        f"this case no longer reaches the out-of-NSMAX slot it exists to "
        f"cover: NS_H={NS_H} is within NSMAX={nsmax}"
    )

    def at(ns, nnf, nr):
        return snf[(ns - 1) + NSTM * (nnf - 1) + NSTM * NNFMAX * (nr - 1)]

    checked = 0
    for nr in range(1, nrmax + 1):
        h = at(NS_H, NNF_DD2, nr)
        if h == 0.0:
            continue
        checked += 1

        # (1) absolute: one step's worth, not N accumulated
        n_d = rn[(nr - 1) + nrmax * (NS_D - 1)]
        t_d = rt[(nr - 1) + nrmax * (NS_D - 1)]
        rate = sigmav(ctypes.byref(ctypes.c_int(ID_NF_DD2)),
                      ctypes.byref(ctypes.c_double(t_d)))
        expected = WGT_DD2 * n_d * n_d * 1.0e20 * rate
        ratio_txt = f"{h / expected:.4f}" if expected else "n/a (expected 0)"
        assert abs(h - expected) <= 1e-10 * abs(expected), (
            f"SNF_NSNNFNR(H,dd2,{nr}) = {h:.9e}, expected one step's "
            f"{expected:.9e} (ratio {ratio_txt}). tr_pnf accumulates, so a "
            f"multiple of the expected value means its outputs were not "
            f"reset at entry."
        )

        # (2) stoichiometric: D takes -SNF twice, H takes +SNF once
        ratio = at(NS_D, NNF_DD2, nr) / h
        assert abs(ratio + 2.0) < 1e-12, (
            f"SNF(D)/SNF(H) at nr={nr} is {ratio}, not -2. D is inside "
            f"NSMAX={nsmax} and H is not, so an asymmetric reset bound "
            f"clears one and leaves the other accumulating."
        )

    assert checked, (
        "the D-D -> T + p channel produced nothing, so the reaction loop did "
        "not run and both assertions above were vacuous"
    )


def test_undefined_model_pnf_returns_instead_of_aborting(probe):
    """An unknown model_pnf must come back as ierr, not as a process abort.

    Upstream, set_usigmav_nf answered this with a bare STOP, which from
    inside a dlopened .so takes down the interpreter. It now returns
    ierr_nf=2, tr_prep propagates it, and tr_api_run maps it to
    TR_ERR_CALC_FAILED. So the assertion is really that the interpreter is
    still alive to raise -- a STOP would fail this test by killing the
    pytest-forked child, not by raising something else.
    """
    with pytest.raises(TrlibError):
        probe(UNDEFINED_MODEL_PNF)

    # Still usable afterwards: the refusal must not have left state wedged.
    assert probe(0)["ready"] is False


def test_session_state_is_released_and_reset_across_a_cycle(monkeypatch):
    """A second in-process session must inherit nothing from the first.

    Five pieces of module-scope state that outlive a finalize unless
    something resets them:

      model_pnf, nnfmax          -- reset in tr_init only
      nf_error_count, nf_last_error -- reset in nf_finalize and tr_init
      libnf::id_nf_nnf           -- an ALLOCATABLE with no initialiser,
                                    freed in nf_finalize from
                                    tr_api_finalize

    Measured discrimination: deleting the nnfmax reset fails this with
    `assert 13 == 0`, and deleting the nf_finalize call fails the
    outlived-finalize assertion.

    Deleting tr_init's nf_error_count or nf_last_error reset does NOT fail
    it -- but they are not dead code, only unobserved from here.
    nf_finalize has already zeroed both by the time the second init runs,
    so this test cannot see the difference; a caller driving libnf directly
    through the .so between a finalize and the next init can, because those
    calls move the counter with no tr_api call in between. Kept for that
    window and against a future re-init path that skips finalize.
    model_pnf and nnfmax are a different case -- nf_finalize does not touch
    them, and this test does pin both.

    Session 1 runs HOT (PT above sigmav_nf's 1 keV floor) and at
    model_pnf=4. The heat is not incidental: on a cold fixture every
    sigmav_nf call returns 0 without touching nf_error_count, so a counter
    assertion here would pass with the tr_init reset deleted.

    nnfmax and id_nf_nnf are read right after the second init, BEFORE run().
    By the time tr_prep has run, set_usigmav_nf's CASE(0) has set nnfmax=0
    and rebuilt the table anyway, so a post-run check proves nothing. The
    window that matters is init..tr_prep, where tr_api_init calls
    ALLOCATE_TRCOMM directly and would size the trcomm_nf arrays from the
    dead session's reaction count.
    """
    from .fixtures import tr_iter01_params as HOT

    lib = _lib()
    monkeypatch.chdir(FIXTURES_DIR)

    def id_nf_nnf_allocated():
        return ctypes.c_void_p.in_dll(lib, "__libnf_MOD_id_nf_nnf").value is not None

    with Trlib() as tr:
        HOT.apply(tr)
        for i in range(1, 5):
            tr.set_param(f"PT[{i}]", 2000.0)   # above the table top -> errors
            tr.set_param(f"PTS[{i}]", 2000.0)
        tr.set_param("MDLNF", 0)   # mutually exclusive with model_pnf
        tr.set_param("model_pnf", 4)
        tr.set_param("NTMAX", 1)
        tr.run(1)
        assert ctypes.c_int.in_dll(lib, SYM_NNFMAX).value == 13
        assert ctypes.c_int.in_dll(lib, SYM_NF_COUNT).value > 0, (
            "session 1 was supposed to fail sigmav_nf; without that the "
            "counter assertion below passes trivially"
        )
        assert id_nf_nnf_allocated()

    # --- finalize has run ---
    assert not id_nf_nnf_allocated(), (
        "libnf's reaction table outlived finalize; the next session's "
        "tr_prep_pnf would read ALLOCATED(id_nf_nnf) as .TRUE. for a table "
        "it never built"
    )

    with Trlib() as tr:
        assert ctypes.c_int.in_dll(lib, SYM_MODEL_PNF).value == 0
        assert ctypes.c_int.in_dll(lib, SYM_NNFMAX).value == 0
        assert ctypes.c_int.in_dll(lib, SYM_NF_COUNT).value == 0
        assert not id_nf_nnf_allocated()

        FIXTURE.apply(tr)          # never mentions model_pnf
        tr.run(1)
        assert ctypes.c_int.in_dll(lib, SYM_MODEL_PNF).value == 0
        assert bool(ctypes.c_int.in_dll(lib, SYM_READY).value) is False


def test_model_pnf_is_reset_by_init(monkeypatch):
    """A second in-process session must not inherit the first one's model_pnf.

    The declaration initialiser in trcomm_param.f90 is static -- it runs once
    at image load and tr_api_init does not re-execute it -- so Option A's
    "off unless asked for" guarantee rests on trinit's explicit reset, next
    to MDLNF's. Without that line this test fails: the second Trlib() would
    still see model_pnf=4 and arm the path.

    Deliberately does NOT use the `probe` fixture, whose teardown zeroes
    model_pnf and would mask exactly what is under test.
    """
    lib = _lib()
    monkeypatch.chdir(FIXTURES_DIR)

    with Trlib() as tr:
        FIXTURE.apply(tr)
        tr.set_param("MDLNF", 0)   # mutually exclusive with model_pnf
        tr.set_param("model_pnf", 4)
        tr.run(1)
        assert ctypes.c_int.in_dll(lib, SYM_MODEL_PNF).value == 4

    with Trlib() as tr:
        # Read BEFORE run(). nnfmax is the assertion that needs this: by the
        # time tr_prep has run, set_usigmav_nf's CASE(0) has set it to 0
        # anyway, so a post-run check passes with the tr_init reset deleted.
        # The window that matters is init..tr_prep, because tr_api_init calls
        # ALLOCATE_TRCOMM directly -- with a stale nnfmax=13 that sizes the
        # trcomm_nf arrays from the dead session's reaction count (~125 KB at
        # the default) before tr_prep resizes them, giving the default path a
        # different heap history than a first session had. That is the hazard
        # the bit-exactness note in trcomm_nf names.
        assert ctypes.c_int.in_dll(lib, SYM_MODEL_PNF).value == 0
        assert ctypes.c_int.in_dll(lib, SYM_NNFMAX).value == 0
        assert ctypes.c_int.in_dll(lib, SYM_NF_COUNT).value == 0

        FIXTURE.apply(tr)          # never mentions model_pnf
        tr.run(1)
        assert ctypes.c_int.in_dll(lib, SYM_MODEL_PNF).value == 0
        assert bool(ctypes.c_int.in_dll(lib, SYM_READY).value) is False


def _drive_sigmav_nf(steps):
    """Call sigmav_nf directly in a subprocess; return its stdout.

    `steps` is a list of (id_nf, temperature_expr) pairs, or the string
    "reset" to call nf_reset_log between them.

    A subprocess because the messages come from a Fortran WRITE to unit 6,
    which pytest's capture does not reliably intercept -- the same reason
    test_libnf.py probes in a subprocess.
    """
    import subprocess
    import sys
    import textwrap

    from trlib._ffi import _default_lib_path

    body = "\n".join(
        "        reset()" if st == "reset" else f"        call({st[0]}, {st[1]})"
        for st in steps
    )
    src = textwrap.dedent(
        """
        import ctypes
        lib = ctypes.CDLL(%r)
        setup = lib.__libnf_MOD_set_usigmav_nf
        setup.argtypes = [ctypes.POINTER(ctypes.c_int)]
        e = ctypes.c_int(-1)
        setup(ctypes.byref(e))
        assert e.value == 0, e.value
        f = lib.__libnf_MOD_sigmav_nf
        f.restype = ctypes.c_double
        f.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double)]
        def call(i, t):
            return f(ctypes.byref(ctypes.c_int(i)), ctypes.byref(ctypes.c_double(t)))
        def reset():
            lib.__libnf_MOD_nf_reset_log()
        if True:
        """
        % str(_default_lib_path())
    ) + body + "\n"
    src += '\n        print("PROBE-COMPLETE")\n'
    out = subprocess.run(
        [sys.executable, "-c", src], capture_output=True, text=True, timeout=60
    )
    # Judge on the OUTPUT, not the return code. A bare Fortran STOP exits 0,
    # so a returncode check sails straight past a library-reachable abort --
    # test_libnf.py carries the same note, having been bitten by it before.
    # Without this sentinel a STOP reintroduced at any sigmav_nf error site
    # would leave the counts below looking exactly right.
    assert "PROBE-COMPLETE" in out.stdout, (
        f"probe did not reach the end (rc={out.returncode}); the library "
        f"aborted the host process.\nstdout:\n{out.stdout}\n"
        f"stderr:\n{out.stderr[-800:]}"
    )
    return out.stdout


NAN = 'float("nan")'
OVER = "above the 1000 keV table top"
NANMSG = "NaN temperature"
BADID = "undefined id_nf"

# Three of the four nf_logged sites. The fourth, NF_LOG_SPL, fires only on a
# SPL1DF evaluation failure, which no input to sigmav_nf can provoke once the
# splines are built -- so it stays unpinned, and the assertions below say
# "these three", not "every site".
REACHABLE_SITES = [(1, "2000.0"), (1, NAN), (99, "10.0")]


def test_each_reporting_site_logs_once_and_independently():
    """The logging latch is keyed per reporting site, not per error code.

    This is the pin that was missing while the mechanism was rewritten three
    times across review rounds. NaN and over-range both return
    NF_ERR_TEMP, so a latch keyed on the returned code silences the NaN
    message after any over-range one -- and NaN is the branch that exists
    precisely because NaN slips past both ordered comparisons and reaches
    LOG10. Collapsing NF_LOG_NAN and NF_LOG_HIGH back to one index would
    restore that defect while leaving the rest of the suite green.
    """
    out = _drive_sigmav_nf(REACHABLE_SITES + REACHABLE_SITES)
    assert out.count(NANMSG) == 1, (
        "the NaN site was silenced by the over-range one, so the latch is "
        f"keyed on the error code rather than the reporting site:\n{out}"
    )
    assert out.count(OVER) == 1, out
    assert out.count(BADID) == 1, out


def test_nf_reset_log_re_arms_each_reachable_site():
    """tr_prep calls this, which is what gives each prepare a fresh voice.

    Without it, trmenu's second interactive R run reports nothing at all --
    tr_init runs once per process and the R handler goes straight to
    tr_prep.
    """
    out = _drive_sigmav_nf(REACHABLE_SITES + ["reset"] + REACHABLE_SITES)
    for msg in (OVER, NANMSG, BADID):
        assert out.count(msg) == 2, (
            f"{msg!r} appeared {out.count(msg)} times, expected 2 -- "
            f"nf_reset_log did not re-arm this site:\n{out}"
        )


def _run_hot_in_subprocess(script_body):
    """Drive a real Trlib session in a subprocess and return its stdout.

    Same reason as _drive_sigmav_nf: the diagnostics come from Fortran WRITEs
    to unit 6. Ends with a sentinel because a library-reachable STOP exits 0.
    """
    import subprocess
    import sys
    import textwrap

    src = textwrap.dedent(
        """
        import sys, os
        sys.path.insert(0, %r)
        from trlib import Trlib
        import trlib.tests.fixtures.tr_iter01_params as HOT
        os.chdir(%r)
        def hot(tr, pt=1.0e5):
            HOT.apply(tr)
            # tr_iter01 ships MDLNF=1; tr_prep refuses both switches at
            # once because they write the same SNF/PNF/TAUF and would
            # double-count the D-T alphas, SIGMAM once and libnf once.
            tr.set_param("MDLNF", 0)
            for i in range(1, 5):
                tr.set_param("PT[%%d]" %% i, pt)
                tr.set_param("PTS[%%d]" %% i, pt)
            tr.set_param("model_pnf", 2)
        """
        % (str(Path(__file__).resolve().parents[2]), str(FIXTURES_DIR))
    ) + textwrap.dedent(script_body) + '\nprint("PROBE-COMPLETE")\n'
    out = subprocess.run(
        [sys.executable, "-c", src], capture_output=True, text=True, timeout=180
    )
    assert "PROBE-COMPLETE" in out.stdout, (
        f"probe did not reach the end (rc={out.returncode}):\n"
        f"{out.stdout[-2000:]}\n{out.stderr[-800:]}"
    )
    return out.stdout


def test_each_prepare_gets_a_fresh_voice():
    """tr_prep's nf_reset_log call, pinned at the CALL SITE.

    The sibling test drives nf_reset_log directly, which proves the routine
    works but not that anything invokes it. Deleting `CALL nf_reset_log` from
    tr_prep leaves that test green -- and that deletion is exactly the defect
    this branch found by hand: trmenu's R handler re-preps without ever
    returning through tr_init, so the second interactive run went silent.

    Here set_param clears g_prepared, so the second run() re-preps, and the
    over-range message must appear once per prepare.
    """
    out = _run_hot_in_subprocess(
        """
        with Trlib() as tr:
            hot(tr)
            tr.set_param("NTMAX", 1)
            tr.run(1)
            tr.set_param("NTMAX", 1)   # clears g_prepared -> next run re-preps
            tr.run(1)
        """
    )
    assert out.count(OVER) == 2, (
        f"expected one {OVER!r} per prepare, got {out.count(OVER)}. "
        f"tr_prep is not re-arming the latches, so every run after the first "
        f"is silent:\n{out[-1500:]}"
    )


def test_trcalc_summary_is_throttled_to_one_line_per_prepare():
    """trcalc's nf_summary_logged gate, pinned.

    tr_pnf runs several times per step, so an ungated WRITE here emits one
    line per call -- measured 22 over 5 steps at this temperature. Dropping
    the `.NOT.nf_summary_logged` term leaves the rest of the suite green.
    """
    out = _run_hot_in_subprocess(
        """
        with Trlib() as tr:
            hot(tr)
            tr.set_param("NTMAX", 5)
            tr.run(5)
        """
    )
    n = out.count("XX TRCALC: tr_pnf ierr=")
    assert n == 1, (
        f"expected exactly 1 throttled TRCALC summary, got {n} -- tr_pnf is "
        f"called many times per prepare, so this is one line per CALL:\n"
        f"{out[-1500:]}"
    )


# --- P1 Task 7: the publish into the arrays the solver reads ---

def _hot_dt(tr):
    """A 10 keV D-T configuration on tr_iter01, with MDLNF disarmed."""
    from .fixtures import tr_iter01_params as HOT

    HOT.apply(tr)
    tr.set_param("MDLNF", 0)
    for i in range(1, 5):
        tr.set_param(f"PT[{i}]", 10.0)
        tr.set_param(f"PTS[{i}]", 1.0)


def _profiles(lib, nrmax):
    """SNF, PNF and TAUF -- the three arrays tr_pnf publishes."""
    out = {}
    for name, sym in (("SNF", "__trcomm_profile_MOD_snf"),
                      ("PNF", "__trcomm_profile_MOD_pnf"),
                      ("TAUF", "__trcomm_profile_MOD_tauf")):
        addr = ctypes.c_void_p.in_dll(lib, sym)
        assert addr.value, f"{sym} is not allocated"
        out[name] = list((ctypes.c_double * nrmax).from_address(addr.value))
    return out


def test_model_pnf_publishes_into_the_solver_arrays(monkeypatch):
    """model_pnf=1 must move SNF, PNF and TAUF -- otherwise it drives nothing.

    Task 6 left the path writing only trcomm_nf arrays that nothing reads, so
    model_pnf changed no output at all. This is the assertion that would have
    caught that, and that catches a regression of the three publish lines in
    tr_pnf: delete them and every other test in this file still passes.

    At MDLNF=0 TRCALC zeroes SNF/PNF and sets TAUF=1.0 every step, so the
    model_pnf=0 values below are those placeholders, not stale data.
    """
    lib = _lib()
    monkeypatch.chdir(FIXTURES_DIR)

    def run(model_pnf):
        with Trlib() as tr:
            _hot_dt(tr)
            tr.set_param("model_pnf", model_pnf)
            tr.set_param("NTMAX", 1)
            tr.run(1)
            nrmax = ctypes.c_int.in_dll(lib, "__trcom0_MOD_nrmax").value
            return _profiles(lib, nrmax)

    off, on = run(0), run(1)

    assert all(v == 0.0 for v in off["SNF"]), "MDLNF=0 should leave SNF zeroed"
    assert all(v == 0.0 for v in off["PNF"]), "MDLNF=0 should leave PNF zeroed"
    assert all(v == 1.0 for v in off["TAUF"]), "MDLNF=0 sets TAUF to 1.0"

    assert any(v != 0.0 for v in on["SNF"]), (
        "model_pnf=1 left SNF at zero -- tr_pnf is not publishing the particle "
        "source, so the ported path drives nothing"
    )
    assert any(v != 0.0 for v in on["PNF"]), "model_pnf=1 left PNF at zero"
    assert any(v != 1.0 for v in on["TAUF"]), (
        "TAUF is still the 1.0 placeholder -- the slowing-down block did not run"
    )
    # The alpha source is positive and its power follows it.
    assert min(on["SNF"]) >= 0.0, "the He4 source must not go negative"
    assert min(on["PNF"]) >= 0.0


# --- P1 Task 7: the whole-solve fusion differential, against trx ---

# test_run/inputs/tr_fus_dt_hot.in, with two deliberate differences: NRMAX is
# omitted (it has no CASE in tr_param_registry, and trinit.f90:376 already
# defaults it to the deck's 50), and MDLNF=0 is added (also already the
# trinit.f90:416 default, but the legacy path must be off for this comparison
# and saying so beats relying on a default).  Every other name IS registered,
# and tr_param_registry's CASE DEFAULT returns ierr=1 which raise_for_ierr
# turns into an exception, so nothing here can be silently dropped.
#
# Through the C ABI this reproduces the standalone kyoshimi tr2 run of the same
# deck bit-for-bit, all 514 fields at rel 0.0.  It does NOT reproduce the
# committed *reference* captures -- 204 of 514 fields match, worst 6.7e-4 at
# AJ[48].  That gap is the two forks' transport divergence, which is exactly
# what comparing differentials is for.
HOT_DECK = dict(
    MODELG=2, RR=8.481, RA=2.574, RKAP=1.816, RDLT=0.3478, BB=5.953,
    NSMAX=4, PROFN2=0.15, DT=0.02, NTMAX=5, NTSTEP=5,
    RIPS=2.0, RIPE=3.0, MDLNF=0,
)
HOT_PN = (0.1, 0.045, 0.045, 0.005)
HOT_PNS = (0.01, 0.0045, 0.0045, 0.0005)

# One tolerance for both channel sets, sized off the noisier one: RT, worst
# 5.1e-3 at RT[NR=28][s=2], so 2e-2 leaves 3.9x.  That is THE margin -- the
# scalars' own worst (TAUE2, 3.5e-3) never binds, because RT trips first at
# every error size.  The floor is not the port.  With fusion off the two forks
# already differ by 2.9e-4 in WPT after these five steps (they are identical
# at T=0 to 5.7e-16), so each code's fusion perturbation lands on a slightly
# different state.  Tightening belongs with closing that gap --
# test_run/baselines/tr_fus_dt_hot/SOURCE.md, "Known open gap".
#
# What this resolves: the perturbation is 1.1e-3 relative, small enough that
# the response is linear, so a systematic factor error eps in the ported alpha
# power shows up as rel ~ eps.  Scaling the kyoshimi differential by (1+eps)
# over all 209 entries, the first crosses 2e-2 at eps = 1.5% (RT[28][2] at
# 2.019e-2; 5 entries at 1.75%, 185 at 2%).  So this catches a ~1.5% error in
# alpha heating -- a wrong branching ratio, the 3.5/17.6 MeV split misapplied
# (19.9%), a dropped term -- not merely the order-of-magnitude defects the
# port's history supplies (the cm^3/s rate is 1e6, the un-reset PNF
# accumulator a factor of order the call count -- 46 over these five steps on
# the corrected build, more on the defective one -- the doubled RKEV larger
# still).
#
# The two profile channels not used here fail for a different reason than a
# loose tolerance: both carry points where the reference shows no fusion
# signal, which trips FUSION_SIGNAL_FLOOR below before the tolerance check is
# reached.  AJ has 3 such points of 50 (worst rel 6.4e-2 at NR=42, where the
# reference signal is 1.3e-8); QP has 10, including NR=50 where d_ref is
# exactly zero.  Over the points that DO clear the floor both are quiet -- AJ
# 2.3e-3, QP 3.5e-3, comparable to RT's 5.1e-3.  So the margin here is a
# property of the channel selection, not of the construction, and anyone
# adding a channel must re-measure rather than assume.
FUSION_DIFFERENTIAL_TOL = 2e-2
FUSION_CHANNELS = ("WPT", "BETA0", "BETAP0", "BETAA", "BETAN",
                   "TAUE1", "TAUE2", "Q0", "ALI")

# Every compared entry must show a reference signal at least this large,
# relative to its model_pnf=0 value.  Guards against comparing noise: an exact
# `d_ref != 0` passes on a last-bit difference.  Measured smallest real
# signals are ALI at 4.4e-6 and RT's quietest point at 1.3e-6, so this sits
# an order below the physics and eight above double-precision rounding.
FUSION_SIGNAL_FLOOR = 1e-7


def _run_hot_deck(model_pnf):
    """The Task 7 oracle deck through the C ABI. Returns the whole state."""
    with Trlib() as tr:
        for name, value in HOT_DECK.items():
            tr.set_param(name, value)
        for i in range(1, 5):
            tr.set_param(f"PN[{i}]", HOT_PN[i - 1])
            tr.set_param(f"PNS[{i}]", HOT_PNS[i - 1])
            tr.set_param(f"PT[{i}]", 10.0)
            tr.set_param(f"PTS[{i}]", 1.0)
        tr.set_param("model_pnf", model_pnf)
        tr.run(HOT_DECK["NTMAX"])
        return tr.get_state().to_dict()


def _differentials(ref_on, ref_off, on, off, entries):
    """(label, d_ref, d_kyo, base, rel) for each (label, getter) in entries.

    ``base`` is |value at model_pnf=0| on the reference side -- the scale the
    signal floor is measured against.
    """
    out = []
    for label, get in entries:
        d_ref = get(ref_on) - get(ref_off)
        d_kyo = get(on) - get(off)
        base = abs(get(ref_off))
        out.append((label, d_ref, d_kyo, base,
                    abs(d_kyo - d_ref) / abs(d_ref) if d_ref else float("inf")))
    return out


def test_fusion_differential_matches_the_trx_reference(monkeypatch):
    """The Task 7 validation, as a test rather than a number in a document.

    Both reference captures are committed, so the comparison is a *differential*
    -- (model_pnf=1 minus model_pnf=0), taken separately in each code and then
    compared -- rather than an absolute baseline diff.  That matters twice
    over.  It suppresses the two forks' unrelated transport-layer divergence
    far better than any absolute comparison, though not completely -- the
    residual is what sets the floor documented below -- and it is far less
    compiler-sensitive than an absolute capture, which is why this runs
    everywhere while test_equivalence.py's 1e-10 cases are Linux-canonical.

    RT is compared per (NR, species) as well, because the scalars here are all
    species-summed, volume-integrated or axis-extrapolated: a wrong radial
    *shape* of PNF redistributes the power while leaving its volume integral --
    and so WPT, BETA* and TAUE -- nearly unchanged, and would otherwise be
    invisible.  The per-species resolution is free rather than load-bearing on
    this path: no alpha power reaches the thermal species at all.  PFCL enters
    PIN, and it is zeroed every step at trcalc.f90:57; its only other writers
    are TRNFDT and TRNFDHe3, which SELECT CASE(MDLNF) reaches at 1:4 and 5:6 --
    not at the 0 this deck sets.  So a mis-split is currently unreachable, and
    would matter the day PNFCL is implemented.  RN is deliberately not compared:
    MDLEQN=0 leaves the density equations out of the reduced solve, so the
    reference's own RN differential is identically zero at all 200 points and
    there is nothing to compare against.  That gap is real and is what
    SOURCE.md's "What this oracle does NOT exercise" is about.

    Absolute agreement against the baseline is 6.7e-4 at worst and does NOT
    reach 1e-10; SOURCE.md's "Known open gap" says why, and it is not fusion.
    """
    monkeypatch.chdir(FIXTURES_DIR)

    ref_off = json.loads((HOT_BASELINE_DIR / "metrics_model_pnf_0.json")
                         .read_text())
    ref_on = json.loads((HOT_BASELINE_DIR / "metrics.json").read_text())

    off, on = _run_hot_deck(0), _run_hot_deck(1)

    # The grid is an unpinned dependency otherwise: HOT_DECK deliberately does
    # not set NRMAX, and NSMAX/NT reaching the library is assumed by every
    # index below.  Cheap to state, and it fails loudly if a default moves.
    for grid in ("NRMAX", "NSMAX", "NT"):
        expected = ref_on[grid]
        assert ref_off[grid] == expected, (
            f"{grid}: the two committed captures disagree ({ref_off[grid]} vs "
            f"{expected}) -- they are not the same case"
        )
        for label, got in (("model_pnf=0", off[grid]), ("model_pnf=1", on[grid])):
            assert got == expected, (
                f"{grid}: this run has {got}, the reference capture has "
                f"{expected} ({label}). The deck is not reproducing the "
                f"oracle -- comparing differentials across grids is meaningless"
            )

    entries = [(k, lambda d, k=k: d["scalars"][k]) for k in FUSION_CHANNELS]
    for nr in range(ref_on["NRMAX"]):
        for ns in range(ref_on["NSMAX"]):
            entries.append((
                f"RT[NR={nr + 1}][s={ns + 1}]",
                lambda d, nr=nr, ns=ns: d["profile"][nr]["RT"][ns],
            ))

    rows = _differentials(ref_on, ref_off, on, off, entries)

    # A channel whose reference model_pnf=0 value is exactly zero has no scale
    # to measure a signal against, so the floor below cannot be applied to it.
    # Skipping it silently would let a dead channel pass -- metrics.json has
    # two such scalars today (AJRFT, RQ1), neither in FUSION_CHANNELS, and the
    # comment above invites adding channels.  Refuse instead.
    unscaled = [(lb, dr) for lb, dr, _, base, _ in rows if not base]
    assert not unscaled, (
        f"{len(unscaled)} of {len(rows)} compared entries have a reference "
        f"model_pnf=0 value of exactly zero, so FUSION_SIGNAL_FLOOR has no "
        f"scale to apply and this comparison cannot say anything about them. "
        f"Choose channels with a non-zero baseline. First: {unscaled[0][0]} "
        f"(d_ref={unscaled[0][1]:.3e})"
    )

    # With `unscaled` empty, `base` is non-zero everywhere below, so a zero
    # d_ref lands here rather than reaching the tolerance check as rel = inf.
    quiet = [(lb, dr, base) for lb, dr, _, base, _ in rows
             if abs(dr) / base <= FUSION_SIGNAL_FLOOR]
    assert not quiet, (
        f"{len(quiet)} of {len(rows)} compared entries show no reference "
        f"fusion signal above {FUSION_SIGNAL_FLOOR:.0e} relative -- the "
        f"committed captures are not a model_pnf=0/1 pair, or the case "
        f"changed. First: {quiet[0][0]} d_ref={quiet[0][1]:.3e} "
        f"base={quiet[0][2]:.3e}"
    )

    bad = [r for r in rows if r[4] > FUSION_DIFFERENTIAL_TOL]
    if bad:
        worst = max(bad, key=lambda r: r[4])
        detail = "\n".join(
            f"    {lb:22s} kyoshimi {dk:+.9e}  reference {dr:+.9e}  "
            f"rel {rel:.3e}"
            for lb, dr, dk, _, rel in sorted(bad, key=lambda r: -r[4])[:12]
        )
        raise AssertionError(
            f"{len(bad)} of {len(rows)} fusion differentials exceed "
            f"{FUSION_DIFFERENTIAL_TOL:.1e}; worst {worst[0]} at "
            f"rel {worst[4]:.3e}\n"
            f"  (differential = model_pnf=1 minus model_pnf=0, taken "
            f"separately in each code)\n{detail}"
        )

    # A reference regenerated from a build with fusion effectively disabled
    # would give a tiny-but-nonzero d_ref that a matching kyoshimi tracks, so
    # every ratio above passes while nothing is being validated. Pin the
    # absolute size of the signal against the committed reference's own.
    signal = abs(on["scalars"]["WPT"] - off["scalars"]["WPT"]) \
        / abs(off["scalars"]["WPT"])
    ref_signal = abs(ref_on["scalars"]["WPT"] - ref_off["scalars"]["WPT"]) \
        / abs(ref_off["scalars"]["WPT"])
    assert ref_signal > 1e-4, (
        f"the committed reference's own WPT fusion signal is {ref_signal:.3e}, "
        f"below the 1.11e-3 it was captured at -- the baselines have been "
        f"regenerated from a build that is not running fusion"
    )
    assert signal > 1e-4, (
        f"model_pnf=1 moved WPT by {signal:.3e} relative; the reference moves "
        f"it by {ref_signal:.3e}, so the ported path is not driving the solve"
    )


def test_model_pnf_ge_2_stays_diagnostic_only(monkeypatch):
    """nnfmax > 1 evaluates the reaction set but publishes nothing.

    tr carries one fusion fast-ion slot, so only a single reaction can be
    wired. This pins that the gate is a gate and not an accident: with it
    removed, model_pnf=2 would publish a one-reaction slice of a four-reaction
    set.
    """
    lib = _lib()
    monkeypatch.chdir(FIXTURES_DIR)
    with Trlib() as tr:
        _hot_dt(tr)
        tr.set_param("model_pnf", 2)
        tr.set_param("NTMAX", 1)
        tr.run(1)
        assert ctypes.c_int.in_dll(lib, SYM_NNFMAX).value == 4
        assert bool(ctypes.c_int.in_dll(lib, SYM_READY).value)
        nrmax = ctypes.c_int.in_dll(lib, "__trcom0_MOD_nrmax").value
        p = _profiles(lib, nrmax)
    assert all(v == 0.0 for v in p["SNF"]), "nnfmax>1 must not publish SNF"
    assert all(v == 0.0 for v in p["PNF"]), "nnfmax>1 must not publish PNF"
    assert all(v == 1.0 for v in p["TAUF"]), "nnfmax>1 must not publish TAUF"


def test_mdlnf_and_model_pnf_together_are_refused(monkeypatch):
    """Both write SNF/PNF/TAUF; tr_pnf runs second and would silently win.

    Combining them would also count the same D-T alphas twice, once from
    SIGMAM and once from libnf. tr_prep refuses with ierr=10.
    """
    monkeypatch.chdir(FIXTURES_DIR)
    with pytest.raises(TrlibError):
        with Trlib() as tr:
            from .fixtures import tr_iter01_params as HOT

            HOT.apply(tr)          # ships MDLNF=1
            tr.set_param("model_pnf", 1)
            tr.run(1)


def test_a_publishing_failure_aborts_the_step(monkeypatch):
    """The other half of the reporting/propagation split.

    At nnfmax == 1 the path publishes, so a sigmav_nf failure must abort
    rather than let the step continue with SNF and PNF silently zeroed while
    TAUF is still computed from the profiles. Its complement -- that a failure
    at nnfmax > 1 must NOT abort, because nothing published -- is pinned by
    the three hot tests above, which run at model_pnf=2 and 4 and expect the
    run to complete.

    Without this, deleting the whole propagation block from trcalc leaves the
    suite green: the "do not abort a dead diagnostic" side was protected and
    the "do abort a live one" side was not.
    """
    from .fixtures import tr_iter01_params as HOT

    lib = _lib()
    monkeypatch.chdir(FIXTURES_DIR)

    # The assertions live INSIDE the context: leaving it calls tr_finalize,
    # which calls nf_finalize, which zeroes both counters. pytest.raises
    # swallows the exception so the block continues.
    with Trlib() as tr:
        HOT.apply(tr)
        tr.set_param("MDLNF", 0)
        for i in range(1, 5):
            tr.set_param(f"PT[{i}]", 2000.0)   # above the 1000 keV table top
            tr.set_param(f"PTS[{i}]", 2000.0)
        tr.set_param("model_pnf", 1)           # nnfmax == 1 -> publishing
        with pytest.raises(TrlibError):
            tr.run(1)

        # tr_api_run flattens every failure to TR_ERR_CALC_FAILED, so the
        # raise alone cannot say WHERE it came from -- tr_prep's refusal
        # surfaces identically. Pin the origin: sigmav_nf must have run and
        # failed on its temperature guard, which is what tr_pnf propagated.
        assert ctypes.c_int.in_dll(lib, SYM_NF_COUNT).value > 0, (
            "nothing tripped sigmav_nf, so the abort came from elsewhere -- "
            "this test would then pass for the wrong reason"
        )
        assert ctypes.c_int.in_dll(lib, SYM_NF_ERR).value == 2, (
            "expected NF_ERR_TEMP (2), the >1000 keV guard; got "
            f"{ctypes.c_int.in_dll(lib, SYM_NF_ERR).value}"
        )
