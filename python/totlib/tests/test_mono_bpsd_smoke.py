"""Layer-C: mono BPSD broker smoke test (#201 Phase 2b).

Verifies the runtime distinction between the monolithic
``libtotapi_mono.so`` and the default per-module ``libtotapi.so``:

  C-1 (test_mono_flag): ``tot_is_mono()`` returns 1 on the mono image,
      0 on the default image. Both must export the symbol (per L-7b-ii
      Phase 2b §4); older builds predating Phase 2b would fail
      ``getattr`` and SKIP this test.

  C-2 (test_bpsd_round_trip): drive the mono image through tot_init +
      tot_run(1), then call ``tr_check_bpsd_pull`` — expect ``ok=1``
      because eq's bpsd push lands in the same broker storage that tr
      reads from in the mono image.

  C-3 (test_distinguishes_per_module): same call against the default
      ``libtotapi.so`` returns ``tot_is_mono() == 0``. We do NOT run
      the BPSD round-trip on default — the per-module .so files each
      carry private bpsd storage and the call is structurally
      meaningless (Codex 2026-05-15 retrospective + L-7b-ii spec §0
      correction note).

These tests are environment-gated:

  - ``MONO_LIB_PATH`` env var must point at an existing
    ``libtotapi_mono.so``. CI's ``mono-build`` job sets this.
  - ``TOTLIB_PATH`` env var must point at an existing default
    ``libtotapi.so`` (for C-3 only).

Process isolation: required via ``pytest --forked``. The mono .so
carries module-level state (bpsd broker slots, trcomm, eq common
blocks) that bleeds across tests within the same process. Without
``--forked``, a prior test's eq push could let a later test's
``check_bpsd_pull`` pass for the wrong reason. CLAUDE.md's standard
flags (``--forked --timeout=120 --timeout-method=signal``) cover this.
"""
from __future__ import annotations

import ctypes
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


def _mono_path() -> str:
    """Path to libtotapi_mono.so from env, or empty string if absent."""
    p = os.environ.get("MONO_LIB_PATH", "")
    return p if p and os.path.exists(p) else ""


def _default_path() -> str:
    """Path to default libtotapi.so from env, or empty string if absent."""
    p = os.environ.get("TOTLIB_PATH", "")
    return p if p and os.path.exists(p) else ""


@unittest.skipUnless(
    _mono_path(),
    "MONO_LIB_PATH not set or missing; build with `make -C tot libtotapi_mono.so`",
)
class TestMonoFlag(unittest.TestCase):
    """C-1: tot_is_mono returns 1 on mono image."""

    def test_mono_flag(self):
        lib = ctypes.CDLL(_mono_path())
        lib.tot_is_mono.restype = ctypes.c_int
        lib.tot_is_mono.argtypes = []
        self.assertEqual(
            lib.tot_is_mono(), 1,
            "monolithic libtotapi_mono.so must report tot_is_mono() == 1",
        )


_EQDATA_FIXTURE = (
    REPO / "python" / "totlib" / "tests" / "fixtures" / "eqdata-HT6M"
)


@unittest.skipUnless(
    _mono_path() and _EQDATA_FIXTURE.exists(),
    "MONO_LIB_PATH and/or eqdata-HT6M fixture missing; "
    "build mono with `make -C tot libtotapi_mono.so` and ensure PR #199 "
    "fixture is in place",
)
class TestBpsdRoundTrip(unittest.TestCase):
    """C-2: eq push -> tr pull round-trip succeeds on mono image.

    Test strategy: drive eq through eq_run(mode=1) which calls
    equnit::eq_load(), and eq_load() invokes eq_bpsd_put() that
    pushes (device, equ1D, metric1D) slots into the BPSD broker. In
    the mono image those slots land in the same broker storage that
    tr reads from, so tr_check_bpsd_pull() succeeds.

    Why eq_run(0) won't work: the analytic Grad-Shafranov path
    (CASE 0 of eq_api_run) calls EQCALC + EQCALQ but NOT
    eq_bpsd_put (see eq/equnit.f90:eq_calc for the wrapper that DOES
    push). Only eq_run(1) hits the eq_load -> eq_bpsd_put path
    that's symmetric with the default tot equivalence test driver.

    We chdir into a tmpdir + stage the committed eqdata-HT6M fixture
    so KNAMEQ resolves correctly without polluting the repo root.
    """

    def test_bpsd_round_trip(self):
        import shutil
        import tempfile

        lib = ctypes.CDLL(_mono_path())
        # tot init/finalize (full lifecycle, brings up all sub-modules
        # including eq_api's C-ABI g_initialized via the cascade added
        # in #209 — direct ctypes callers no longer need a separate
        # eq_init() round trip after tot_init()).
        lib.tot_init.restype = ctypes.c_int
        lib.tot_init.argtypes = []
        lib.tot_finalize.restype = ctypes.c_int
        lib.tot_finalize.argtypes = []
        # tr's BPSD-pull probe (shipped in PR #188; co-linked into
        # libtotapi_mono.so along with all other tr PIC objects).
        lib.tr_check_bpsd_pull.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.tr_check_bpsd_pull.restype = None
        # eq C ABI for driving the BPSD push. eq_api's g_initialized
        # is flipped by the tot_init cascade (#209), so we go straight
        # to eq_set_param / eq_run below.
        lib.eq_set_param.restype = ctypes.c_int
        lib.eq_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]
        lib.eq_set_param_str.restype = ctypes.c_int
        lib.eq_set_param_str.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        lib.eq_run.restype = ctypes.c_int
        lib.eq_run.argtypes = [ctypes.c_int]

        # chdir into a temp dir so eq_load resolves KNAMEQ relative to
        # cwd without polluting the repo root with eqdata side-files.
        prev = os.getcwd()
        with tempfile.TemporaryDirectory(prefix="mono_bpsd_smoke_") as td:
            shutil.copy2(_EQDATA_FIXTURE, Path(td) / "eqdata-HT6M")
            os.chdir(td)
            try:
                rc = lib.tot_init()
                self.assertEqual(rc, 0, f"tot_init returned {rc}")
                try:
                    # No explicit eq_init() — #209 cascade flips
                    # eq_api's g_initialized from inside tot_api_init.
                    rc = lib.eq_set_param(b"MODELG", ctypes.c_double(3.0))
                    self.assertEqual(rc, 0, f"eq_set_param(MODELG=3) -> {rc}")
                    rc = lib.eq_set_param_str(b"KNAMEQ", b"eqdata-HT6M")
                    self.assertEqual(rc, 0, f"eq_set_param_str(KNAMEQ) -> {rc}")
                    # eq_run(mode=1) -> equnit::eq_load -> eq_bpsd_put,
                    # populating the (device, equ1D, metric1D) BPSD slots.
                    rc = lib.eq_run(1)
                    self.assertEqual(rc, 0, f"eq_run(1) returned {rc}")

                    ok = ctypes.c_int(-1)
                    lib.tr_check_bpsd_pull(ctypes.byref(ok))
                    self.assertEqual(
                        ok.value, 1,
                        f"mono image: tr_check_bpsd_pull returned "
                        f"ok={ok.value}, expected 1. This is the "
                        "broker-share invariant: eq just pushed BPSD "
                        "slots via eq_run(1) -> eq_load -> eq_bpsd_put; "
                        "if tr cannot pull them, the mono image is "
                        "not actually sharing the broker as designed.",
                    )
                finally:
                    lib.tot_finalize()
            finally:
                os.chdir(prev)


@unittest.skipUnless(
    _default_path(),
    "TOTLIB_PATH not set or missing; build with `make -C tot libtotapi.so`",
)
class TestDistinguishesPerModule(unittest.TestCase):
    """C-3: default libtotapi.so reports tot_is_mono() == 0."""

    def test_default_is_not_mono(self):
        lib = ctypes.CDLL(_default_path())
        lib.tot_is_mono.restype = ctypes.c_int
        lib.tot_is_mono.argtypes = []
        self.assertEqual(
            lib.tot_is_mono(), 0,
            "default per-module libtotapi.so must report tot_is_mono() == 0; "
            "if this returns 1 the mono build was selected by mistake at "
            "link time (check that tot_is_mono.f90, not tot_is_mono_mono.f90, "
            "was linked into libtotapi.so).",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
