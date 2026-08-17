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
``ctypes.c_int.in_dll`` is well defined here (unlike the allocatable arrays,
which are descriptors and are deliberately not poked at).
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

import pytest

from trlib import Trlib
from trlib.errors import TrlibError

from .fixtures import tr_tst2_params as FIXTURE

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

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
