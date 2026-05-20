"""Regression: tot_init must cascade eq_api_init (#209).

Before #209: tot_api_init brought up tr/ti/fp/wr but NOT eq_api. eq_api
maintained its own `g_initialized` flag, so callers driving the eq C ABI
directly after `tot_init()` would hit EQ_ERR_NOT_INIT on the first
`eq_set_param` unless they also explicitly called `eq_init()`. The
Phase 2b Layer-C smoke test (`test_mono_bpsd_smoke.py`) documented this
as a foot-gun.

After #209 (Option A from the issue body): tot_api_init cascades
eq_api_init alongside the other per-module API inits, so direct ctypes
callers see a single tot_init() lifecycle that brings everything up.

These tests pin the post-fix contract: after `tot_init()` (no explicit
`eq_init()`), `eq_set_param("MODELG", 3.0)` must return EQ_OK, not
EQ_ERR_NOT_INIT.

Process isolation: `--forked` required. eq_api's module-level
g_initialized bleeds across tests within the same process; without
forking a later test could observe leftover True state from an earlier
test's lifecycle and pass for the wrong reason.

Library coverage: tested on both the default per-module image
(`TOTLIB_PATH=...libtotapi.so`) and the monolithic image
(`MONO_LIB_PATH=...libtotapi_mono.so`). The dual-flag dynamic is
identical in both — eq_api.f90's g_initialized is module-local to the
eq_api object, regardless of which .so it ends up linked into.
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


def _lib_path(env: str) -> str:
    p = os.environ.get(env, "")
    return p if p and os.path.exists(p) else ""


EQ_OK = 0
EQ_ERR_NOT_INIT = 2


class _CascadeBase:
    """Drive tot_init() and assert eq_set_param succeeds without an
    explicit eq_init() call.

    Subclasses set ``LIB_PATH`` to point at the image under test.
    """

    LIB_PATH: str = ""

    def test_eq_set_param_succeeds_without_explicit_eq_init(self):
        lib = ctypes.CDLL(self.LIB_PATH)
        lib.tot_init.restype = ctypes.c_int
        lib.tot_init.argtypes = []
        lib.tot_finalize.restype = ctypes.c_int
        lib.tot_finalize.argtypes = []
        lib.eq_set_param.restype = ctypes.c_int
        lib.eq_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]

        rc = lib.tot_init()
        self.assertEqual(rc, 0, f"tot_init returned {rc}")
        try:
            # The whole point of this regression test: do NOT call
            # lib.eq_init() here. tot_init() should have cascaded it.
            rc = lib.eq_set_param(b"MODELG", ctypes.c_double(3.0))
            self.assertEqual(
                rc, EQ_OK,
                f"eq_set_param(MODELG=3) returned {rc} after tot_init() "
                f"with no explicit eq_init(). EQ_ERR_NOT_INIT (rc=2) means "
                f"tot_api_init did NOT cascade eq_api_init — #209 regression.",
            )
        finally:
            lib.tot_finalize()


@unittest.skipUnless(
    _lib_path("TOTLIB_PATH"),
    "TOTLIB_PATH not set or missing; build with `make -C tot libtotapi.so`",
)
class TestTotInitCascadeDefault(_CascadeBase, unittest.TestCase):
    LIB_PATH = _lib_path("TOTLIB_PATH")


@unittest.skipUnless(
    _lib_path("MONO_LIB_PATH"),
    "MONO_LIB_PATH not set or missing; build with `make -C tot libtotapi_mono.so`",
)
class TestTotInitCascadeMono(_CascadeBase, unittest.TestCase):
    LIB_PATH = _lib_path("MONO_LIB_PATH")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
