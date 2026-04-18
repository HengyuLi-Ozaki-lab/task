"""Direct ctypes-layer tests.

These exercise :mod:`wrlib._ffi` without going through the high-level
``Wrlib`` class. They verify that:

* the package imports without a libwrapi.so on disk (load is lazy),
* :class:`WrStateC` has the expected size and layout,
* :func:`load_library` errors clearly when the .so is missing,
* when libwrapi.so **is** present, prototypes are attached and the 5
  symbols resolve.

Tests that require the shared library are skipped automatically when
it has not been built yet.
"""
from __future__ import annotations

import ctypes
import os
import unittest
from pathlib import Path

# Make sure the package is importable when tests are run from the
# repo root with ``python3 -m unittest discover``.
import sys
HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]  # .../python
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from wrlib import _ffi  # noqa: E402


REPO = HERE.parents[3]
DEFAULT_SO = REPO / "wr" / "libwrapi.so"


class TestFfiImport(unittest.TestCase):
    """Importing _ffi must not require libwrapi.so on disk."""

    def test_module_imports(self):
        self.assertTrue(hasattr(_ffi, "WrStateC"))
        self.assertTrue(hasattr(_ffi, "load_library"))

    def test_constants_match_header(self):
        # Must match wr/wr_api.h exactly.
        self.assertEqual(_ffi.WR_MAX_NRAYMAX, 100)
        self.assertEqual(_ffi.WR_MAX_NRSMAX, 200)
        self.assertEqual(_ffi.WR_MAX_NRLMAX, 400)
        self.assertEqual(_ffi.WR_MAX_NRAY_EQ, 9)
        self.assertEqual(_ffi.WR_OK, 0)
        self.assertEqual(_ffi.WR_ERR_INVALID, 1)
        self.assertEqual(_ffi.WR_ERR_NOT_INIT, 2)
        self.assertEqual(_ffi.WR_ERR_CALC_FAILED, 3)
        self.assertEqual(_ffi.WR_ERR_NOT_IMPL, 4)


class TestWrStateCLayout(unittest.TestCase):
    """Structural checks on the ctypes mirror of ``wr_state_t``."""

    def test_has_expected_fields(self):
        names = [f[0] for f in _ffi.WrStateC._fields_]
        for n in (
            "nraymax", "nrsmax", "nrlmax",
            "pos_pwrmax_rs", "pwrmax_rs",
            "pos_pwrmax_rl", "pwrmax_rl",
            "nstp_end",
            "pos_pwrmax_rs_nray", "pwrmax_rs_nray",
            "pos_pwrmax_rl_nray", "pwrmax_rl_nray",
            "rays_end",
            "pos_nrs", "pwr_nrs",
            "pos_nrl", "pwr_nrl",
        ):
            self.assertIn(n, names, f"missing field {n}")

    def test_size_matches_header_math(self):
        # 3 ints + 4 doubles (global pwrmax scalars)
        # + NRAYMAX ints (nstp_end)
        # + 4 * NRAYMAX doubles (per-ray pwrmax scalars)
        # + NRAYMAX * NRAY_EQ doubles (rays_end)
        # + 2 * NRSMAX doubles (pos_nrs, pwr_nrs)
        # + 2 * NRLMAX doubles (pos_nrl, pwr_nrl)
        #
        # Compilers may pad the 3 ints to 16 bytes (to align the first
        # double on an 8-byte boundary), so we accept either exact layout
        # or the padded one. The NRAYMAX int block also starts on an
        # 8-byte boundary after 4 doubles so needs no further padding.
        nray = _ffi.WR_MAX_NRAYMAX
        nrs = _ffi.WR_MAX_NRSMAX
        nrl = _ffi.WR_MAX_NRLMAX
        neq = _ffi.WR_MAX_NRAY_EQ
        core = (
            4 * 8                    # global scalars
            + nray * 4               # nstp_end
            + 4 * nray * 8           # per-ray pwrmax scalars
            + nray * neq * 8         # rays_end
            + 2 * nrs * 8            # pos_nrs, pwr_nrs
            + 2 * nrl * 8            # pos_nrl, pwr_nrl
        )
        # NRAYMAX=100 ints (=400 bytes) is already 8-byte aligned, but
        # if NRAYMAX were odd the compiler might pad. Accept the range.
        sz = ctypes.sizeof(_ffi.WrStateC)
        candidates = (
            12 + core,               # packed ints
            16 + core,               # padded ints
            12 + core + 4,           # packed + post-nstp_end pad
            16 + core + 4,           # padded + post-nstp_end pad
        )
        self.assertIn(
            sz,
            candidates,
            f"unexpected WrStateC size {sz}",
        )

    def test_array_dimensions(self):
        # rays_end: [NRAYMAX][NRAY_EQ] row-major in C, equivalent to
        # Fortran rays_end(NRAY_EQ, NRAYMAX) column-major -- same memory.
        s = _ffi.WrStateC()
        self.assertEqual(len(s.nstp_end), _ffi.WR_MAX_NRAYMAX)
        self.assertEqual(len(s.pos_pwrmax_rs_nray), _ffi.WR_MAX_NRAYMAX)
        self.assertEqual(len(s.pwrmax_rs_nray), _ffi.WR_MAX_NRAYMAX)
        self.assertEqual(len(s.pos_pwrmax_rl_nray), _ffi.WR_MAX_NRAYMAX)
        self.assertEqual(len(s.pwrmax_rl_nray), _ffi.WR_MAX_NRAYMAX)
        self.assertEqual(len(s.rays_end), _ffi.WR_MAX_NRAYMAX)
        self.assertEqual(len(s.rays_end[0]), _ffi.WR_MAX_NRAY_EQ)
        self.assertEqual(len(s.pos_nrs), _ffi.WR_MAX_NRSMAX)
        self.assertEqual(len(s.pwr_nrs), _ffi.WR_MAX_NRSMAX)
        self.assertEqual(len(s.pos_nrl), _ffi.WR_MAX_NRLMAX)
        self.assertEqual(len(s.pwr_nrl), _ffi.WR_MAX_NRLMAX)


class TestLoadLibraryMissing(unittest.TestCase):
    """Error-path test that runs whether or not .so exists."""

    def test_load_bogus_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            _ffi.load_library("/nonexistent/path/to/libwrapi.so")

    def test_candidate_paths_listed(self):
        cands = _ffi._candidate_paths()
        self.assertTrue(any(str(p).endswith("wr/libwrapi.so") for p in cands))
        self.assertTrue(any(str(p).endswith("lib/libwrapi.so") for p in cands))


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libwrapi.so not built at {DEFAULT_SO}; run `make -C wr libwrapi.so`",
)
class TestLoadLibraryReal(unittest.TestCase):
    """Tests that require the real shared library on disk."""

    def test_load_default(self):
        lib = _ffi.load_library()
        self.assertIsInstance(lib, ctypes.CDLL)
        for sym in (
            "wr_init", "wr_run", "wr_set_param", "wr_get_state", "wr_finalize"
        ):
            self.assertTrue(hasattr(lib, sym), f"missing export {sym}")

    def test_env_override(self):
        old = os.environ.get("WRLIB_PATH")
        os.environ["WRLIB_PATH"] = str(DEFAULT_SO)
        try:
            lib = _ffi.load_library()
            self.assertIsInstance(lib, ctypes.CDLL)
        finally:
            if old is None:
                os.environ.pop("WRLIB_PATH", None)
            else:
                os.environ["WRLIB_PATH"] = old

    def test_prototypes_applied(self):
        lib = _ffi.load_library()
        self.assertEqual(lib.wr_init.restype, ctypes.c_int)
        self.assertEqual(lib.wr_run.argtypes, [ctypes.c_int])
        self.assertEqual(
            lib.wr_set_param.argtypes,
            [ctypes.c_char_p, ctypes.c_double],
        )


if __name__ == "__main__":
    unittest.main()
