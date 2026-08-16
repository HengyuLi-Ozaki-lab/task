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
* an undefined value is refused through ``ierr`` rather than through the bare
  ``STOP`` inside ``set_usigmav_nf``, which would kill the host process
  (CLAUDE.md, Fortran library discipline; issue #142).

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
def probe(monkeypatch):
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

    return run


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
    """model_pnf=0 is the default; the legacy MDLNF path must own the run."""
    assert probe(0) == {"nnfmax": 0, "ready": False}


def test_switching_model_pnf_resizes(probe):
    """ALLOCATE_TRCOMM's early-return guard does not watch nnfmax.

    nrmax/nsmax/nszmax/nsnmax are identical across these three runs, so the
    guard short-circuits; only allocate_trcomm_nf's own size check makes the
    second and third runs correct.  Without it tr_prep_pnf refuses with
    ierr=3 (tables and arrays disagree) and `ready` comes back False.
    """
    assert probe(1)["nnfmax"] == 1
    assert probe(4) == {"nnfmax": 13, "ready": True}
    assert probe(1) == {"nnfmax": 1, "ready": True}


def test_undefined_model_pnf_returns_instead_of_aborting(probe):
    """set_usigmav_nf STOPs on an unknown value; tr_prep must screen it first.

    A STOP reached through the library takes down the host process, so the
    fact that this raises a catchable Python exception -- i.e. the
    interpreter is still alive to raise it -- is the assertion.
    """
    with pytest.raises(TrlibError):
        probe(UNDEFINED_MODEL_PNF)

    # Still usable afterwards: the refusal must not have left state wedged.
    assert probe(0)["ready"] is False
