"""Direct ctypes-layer tests.

These exercise :mod:`wrxlib._ffi` without going through the high-level
``Wrxlib`` class. They verify that:

* the package imports without a libwrxapi.so on disk (load is lazy),
* :class:`WrxStateC` has the expected size and layout,
* :func:`load_library` errors clearly when the .so is missing,
* when libwrxapi.so **is** present, prototypes are attached and the 5
  symbols resolve.

Tests that require the shared library are skipped automatically when
it has not been built yet.
"""
from __future__ import annotations

import ctypes
import os
import sys
import unittest
from pathlib import Path

# Make sure the package is importable when tests are run from the
# repo root with ``python3 -m unittest discover``.
HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]  # .../python
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from wrxlib import _ffi  # noqa: E402


REPO = HERE.parents[3]
DEFAULT_SO = REPO / "wrx" / "libwrxapi.so"


class TestFfiImport(unittest.TestCase):
    """Importing _ffi must not require libwrxapi.so on disk."""

    def test_module_imports(self):
        self.assertTrue(hasattr(_ffi, "WrxStateC"))
        self.assertTrue(hasattr(_ffi, "load_library"))

    def test_constants_match_header(self):
        # Must match wrx/wrx_api.h exactly.
        self.assertEqual(_ffi.WRX_MAX_NRAYMAX, 100)
        self.assertEqual(_ffi.WRX_MAX_NSAMAX, 8)
        self.assertEqual(_ffi.WRX_OK, 0)
        self.assertEqual(_ffi.WRX_ERR_INVALID, 1)
        self.assertEqual(_ffi.WRX_ERR_NOT_INIT, 2)
        self.assertEqual(_ffi.WRX_ERR_CALC_FAILED, 3)
        self.assertEqual(_ffi.WRX_ERR_NOT_IMPL, 4)


class TestWrxStateCLayout(unittest.TestCase):
    """Structural checks on the ctypes mirror of ``wrx_state_t``."""

    def test_has_expected_fields(self):
        names = [f[0] for f in _ffi.WrxStateC._fields_]
        for n in (
            "nraymax", "nstpmax", "nsamax", "nsmax",
            "modelg", "mdlwrq", "pwr_tot",
            "nstpmax_nray", "pwr_nray",
            "pwr_nsa", "pwr_nsa_nray",
            "pos_pwrmax_rs_nsa", "pwrmax_rs_nsa",
            "pos_pwrmax_rl_nsa", "pwrmax_rl_nsa",
        ):
            self.assertIn(n, names, f"missing field {n}")

    def test_field_order_matches_header(self):
        # Must match wrx_api.h declaration order verbatim so the
        # ctypes layout is bit-for-bit equivalent to the C struct.
        expected = [
            "nraymax", "nstpmax", "nsamax", "nsmax",
            "modelg", "mdlwrq", "pwr_tot",
            "nstpmax_nray", "pwr_nray",
            "pwr_nsa", "pwr_nsa_nray",
            "pos_pwrmax_rs_nsa", "pwrmax_rs_nsa",
            "pos_pwrmax_rl_nsa", "pwrmax_rl_nsa",
        ]
        actual = [f[0] for f in _ffi.WrxStateC._fields_]
        self.assertEqual(actual, expected)

    def test_size_matches_header_math(self):
        # 6 ints (header scalars) + 1 double (pwr_tot)
        # + NRAYMAX ints (nstpmax_nray)
        # + NRAYMAX doubles (pwr_nray)
        # + NSAMAX doubles (pwr_nsa)
        # + NRAYMAX * NSAMAX doubles (pwr_nsa_nray)
        # + 4 * NSAMAX doubles (pos/pwrmax for rs and rl)
        #
        # Compilers may pad the 6 ints to 32 bytes (to align the
        # following double on an 8-byte boundary), so we accept
        # either exact layout or the padded one. The NRAYMAX int block
        # (400 bytes) stays 8-byte aligned already.
        nray = _ffi.WRX_MAX_NRAYMAX
        nsa = _ffi.WRX_MAX_NSAMAX
        core = (
            1 * 8                    # pwr_tot
            + nray * 4               # nstpmax_nray
            + nray * 8               # pwr_nray
            + nsa * 8                # pwr_nsa
            + nray * nsa * 8         # pwr_nsa_nray
            + 4 * nsa * 8            # rs/rl pwrmax
        )
        sz = ctypes.sizeof(_ffi.WrxStateC)
        candidates = (
            6 * 4 + core,            # packed ints
            6 * 4 + 4 + core,        # packed + tail pad
            6 * 4 + 8 + core,        # padded to 8-byte before pwr_tot
        )
        self.assertIn(
            sz,
            candidates,
            f"unexpected WrxStateC size {sz}, candidates={candidates}",
        )

    def test_array_dimensions(self):
        s = _ffi.WrxStateC()
        self.assertEqual(len(s.nstpmax_nray), _ffi.WRX_MAX_NRAYMAX)
        self.assertEqual(len(s.pwr_nray), _ffi.WRX_MAX_NRAYMAX)
        self.assertEqual(len(s.pwr_nsa), _ffi.WRX_MAX_NSAMAX)
        self.assertEqual(len(s.pwr_nsa_nray), _ffi.WRX_MAX_NRAYMAX)
        self.assertEqual(len(s.pwr_nsa_nray[0]), _ffi.WRX_MAX_NSAMAX)
        self.assertEqual(len(s.pos_pwrmax_rs_nsa), _ffi.WRX_MAX_NSAMAX)
        self.assertEqual(len(s.pwrmax_rs_nsa), _ffi.WRX_MAX_NSAMAX)
        self.assertEqual(len(s.pos_pwrmax_rl_nsa), _ffi.WRX_MAX_NSAMAX)
        self.assertEqual(len(s.pwrmax_rl_nsa), _ffi.WRX_MAX_NSAMAX)


class TestLoadLibraryMissing(unittest.TestCase):
    """Error-path test that runs whether or not .so exists."""

    def test_load_bogus_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            _ffi.load_library("/nonexistent/path/to/libwrxapi.so")

    def test_candidate_paths_listed(self):
        cands = _ffi._candidate_paths()
        self.assertTrue(any(str(p).endswith("wrx/libwrxapi.so") for p in cands))
        self.assertTrue(any(str(p).endswith("lib/libwrxapi.so") for p in cands))


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libwrxapi.so not built at {DEFAULT_SO}; run `make -C wrx libwrxapi.so`",
)
class TestLoadLibraryReal(unittest.TestCase):
    """Tests that require the real shared library on disk."""

    def test_load_default(self):
        lib = _ffi.load_library()
        self.assertIsInstance(lib, ctypes.CDLL)
        for sym in (
            "wrx_init", "wrx_run", "wrx_set_param",
            "wrx_get_state", "wrx_finalize",
        ):
            self.assertTrue(hasattr(lib, sym), f"missing export {sym}")

    def test_env_override(self):
        old = os.environ.get("WRXLIB_PATH")
        os.environ["WRXLIB_PATH"] = str(DEFAULT_SO)
        try:
            lib = _ffi.load_library()
            self.assertIsInstance(lib, ctypes.CDLL)
        finally:
            if old is None:
                os.environ.pop("WRXLIB_PATH", None)
            else:
                os.environ["WRXLIB_PATH"] = old

    def test_prototypes_applied(self):
        lib = _ffi.load_library()
        self.assertEqual(lib.wrx_init.restype, ctypes.c_int)
        self.assertEqual(lib.wrx_run.argtypes, [ctypes.c_int])
        self.assertEqual(
            lib.wrx_set_param.argtypes,
            [ctypes.c_char_p, ctypes.c_double],
        )


if __name__ == "__main__":
    unittest.main()
