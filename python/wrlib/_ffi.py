"""Low-level ctypes FFI for libwrapi.so.

Mirrors ``wr/wr_api.h`` (C ABI). Higher-level helpers live in
``wrlib.py``; this module intentionally exposes only raw ctypes objects
so tests can exercise the boundary directly.

Library-path resolution order (first match wins):

1. explicit ``path`` argument to :func:`load_library`
2. ``WRLIB_PATH`` environment variable
3. ``<repo>/wr/libwrapi.so`` (standard L-4 build location)
4. ``<repo>/lib/libwrapi.so`` (install-style location, future-proofing)

The package layout is ``python/wrlib/_ffi.py`` so the repository root is
two parents above this file (``__file__.parents[2]``).
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
from typing import Optional

# Optional numpy (we never require it; state.py uses lists).
try:
    import numpy as _np  # noqa: F401
    HAS_NUMPY = True
except ImportError:  # pragma: no cover - numpy is optional
    HAS_NUMPY = False


# ---------------------------------------------------------------------
# Layout constants. Must match wr/wr_api.h exactly.
# ---------------------------------------------------------------------
WR_MAX_NRAYMAX = 100
WR_MAX_NRSMAX = 200
WR_MAX_NRLMAX = 400
WR_MAX_NRAY_EQ = 9


# ---------------------------------------------------------------------
# Error codes (kept in sync with wr_api.h::enum wr_error).
# ---------------------------------------------------------------------
WR_OK = 0
WR_ERR_INVALID = 1
WR_ERR_NOT_INIT = 2
WR_ERR_CALC_FAILED = 3
WR_ERR_NOT_IMPL = 4


# ---------------------------------------------------------------------
# ctypes mirror of wr_state_t from wr/wr_api.h.
#
# Memory-layout note (also in wr_api.h):
#   In C, rays_end[NRAYMAX][NRAY_EQ] is row-major.
#   In Fortran the matching declaration is rays_end(NRAY_EQ, NRAYMAX)
#   column-major. Both lay out the same bytes; only the index order
#   differs.
# ---------------------------------------------------------------------
class WrStateC(ctypes.Structure):
    _fields_ = [
        ("nraymax", ctypes.c_int),
        ("nrsmax", ctypes.c_int),
        ("nrlmax", ctypes.c_int),
        ("pos_pwrmax_rs", ctypes.c_double),
        ("pwrmax_rs", ctypes.c_double),
        ("pos_pwrmax_rl", ctypes.c_double),
        ("pwrmax_rl", ctypes.c_double),
        ("nstp_end", ctypes.c_int * WR_MAX_NRAYMAX),
        ("pos_pwrmax_rs_nray", ctypes.c_double * WR_MAX_NRAYMAX),
        ("pwrmax_rs_nray", ctypes.c_double * WR_MAX_NRAYMAX),
        ("pos_pwrmax_rl_nray", ctypes.c_double * WR_MAX_NRAYMAX),
        ("pwrmax_rl_nray", ctypes.c_double * WR_MAX_NRAYMAX),
        ("rays_end", (ctypes.c_double * WR_MAX_NRAY_EQ) * WR_MAX_NRAYMAX),
        ("pos_nrs", ctypes.c_double * WR_MAX_NRSMAX),
        ("pwr_nrs", ctypes.c_double * WR_MAX_NRSMAX),
        ("pos_nrl", ctypes.c_double * WR_MAX_NRLMAX),
        ("pwr_nrl", ctypes.c_double * WR_MAX_NRLMAX),
    ]


# ---------------------------------------------------------------------
# Library loader.
# ---------------------------------------------------------------------
def _repo_root() -> Path:
    """Return the repository root (two parents up from this file)."""
    return Path(__file__).resolve().parents[2]


def _candidate_paths() -> list[Path]:
    """All library paths that :func:`load_library` will try in order."""
    root = _repo_root()
    return [root / "wr" / "libwrapi.so", root / "lib" / "libwrapi.so"]


def _default_lib_path() -> Path:
    """Resolve the default ``libwrapi.so`` path.

    Honours ``WRLIB_PATH`` first; otherwise returns the first existing
    candidate. If none exists, returns the canonical build location so
    the error message from :func:`load_library` mentions it directly.
    """
    env = os.environ.get("WRLIB_PATH")
    if env:
        return Path(env)
    for cand in _candidate_paths():
        if cand.exists():
            return cand
    return _candidate_paths()[0]


def _apply_prototypes(lib: ctypes.CDLL) -> ctypes.CDLL:
    """Attach argtypes / restype to the 5 exported C ABI symbols."""
    lib.wr_init.restype = ctypes.c_int
    lib.wr_init.argtypes = []

    lib.wr_run.restype = ctypes.c_int
    lib.wr_run.argtypes = [ctypes.c_int]

    lib.wr_set_param.restype = ctypes.c_int
    lib.wr_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]

    lib.wr_get_state.restype = ctypes.c_int
    lib.wr_get_state.argtypes = [ctypes.POINTER(WrStateC)]

    lib.wr_finalize.restype = ctypes.c_int
    lib.wr_finalize.argtypes = []
    return lib


# RTLD_LAZY: resolve symbols on first use rather than at dlopen. The
# L-4 build of libwrapi.so may retain a handful of symbols that are
# reachable only from graphics-only code paths that the C ABI never
# calls. Lazy binding is safe for the 5 exported C ABI entry points
# and matches the pattern established by trlib._ffi.
_RTLD_LAZY = 1


def load_library(path: Optional[str] = None) -> ctypes.CDLL:
    """Load libwrapi.so and return the CDLL handle with prototypes applied.

    Uses ``RTLD_LAZY`` because libwrapi.so may retain unresolved
    symbols pointing into graphics-only call paths that the C ABI
    never reaches. Lazy binding defers resolution to first call, so
    the 5 exported entry points load cleanly.

    Raises :class:`FileNotFoundError` with an actionable message when
    the library is not where we looked.
    """
    p = Path(path) if path else _default_lib_path()
    if not p.exists():
        tried = [str(x) for x in _candidate_paths()]
        raise FileNotFoundError(
            f"libwrapi.so not found at {p}. "
            f"Tried WRLIB_PATH and {tried}. "
            "Build it via `make -C wr libwrapi.so` or set WRLIB_PATH."
        )
    # ctypes.RTLD_LAZY may not be defined on all Python builds; fall
    # back to the numeric constant 1 which matches glibc dlfcn.h.
    mode = getattr(ctypes, "RTLD_LAZY", _RTLD_LAZY)
    lib = ctypes.CDLL(str(p), mode=mode)
    return _apply_prototypes(lib)


__all__ = [
    "WR_MAX_NRAYMAX",
    "WR_MAX_NRSMAX",
    "WR_MAX_NRLMAX",
    "WR_MAX_NRAY_EQ",
    "WR_OK",
    "WR_ERR_INVALID",
    "WR_ERR_NOT_INIT",
    "WR_ERR_CALC_FAILED",
    "WR_ERR_NOT_IMPL",
    "WrStateC",
    "HAS_NUMPY",
    "load_library",
]
