"""ctypes layer of equlib: the library, its prototypes and ``equ_state_t``.

``EquStateC`` mirrors ``equ/equ_api.h`` (and ``equ/equ_state.f90``) field by
field. :func:`load_library` refuses a library whose layout differs
(``python/_abi_check.py``, EQ's #246 rule).

Lookup: an explicit path, then ``EQULIB_PATH``, then ``<repo>/equ/libequapi.so``.
EQU is not in the mono image, so ``MONO_LIB_PATH`` does not apply.
"""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Optional

from .errors import EqulibAbiError

EQU_STATE_ABI_VERSION = 1
EQU_MAX_NR = 257
EQU_MAX_NZ = 257
EQU_MAX_NV = 101
EQU_MAX_NSU = 1542
EQU_NCV = 19
EQU_DIAG_PARAM_LEN = 64
EQU_DIAG_MSG_LEN = 128

EQU_OK = 0
EQU_ERR_INVALID = 1
EQU_ERR_NOT_INIT = 2
EQU_ERR_CALC_FAILED = 3
EQU_ERR_NOT_IMPL = 4

D = ctypes.c_double
I = ctypes.c_int


class EquStateC(ctypes.Structure):
    _fields_ = [
        ("nr", I), ("nz", I), ("nv", I), ("nsu", I),
        ("mode", I), ("fct_steps", I), ("fct_converged", I), ("xpoint_status", I),
        ("erreq", D),
        ("raxis", D), ("zaxis", D), ("psi_axis", D),
        ("rsep", D), ("zsep", D), ("psi_sep", D),
        ("ip", D), ("ip_target", D), ("rbt", D),
        ("beta_t", D), ("beta_s", D), ("beta_j", D), ("li", D),
        ("q_axis", D), ("q_surf", D), ("q95", D), ("qqj", D),
        ("rmaj", D), ("rpla", D), ("elip", D), ("trig", D), ("el95", D), ("volume", D),
        ("cvac", D * EQU_NCV),
        ("rg", D * EQU_MAX_NR),
        ("zg", D * EQU_MAX_NZ),
        ("psi", D * EQU_MAX_NV),
        ("psit", D * EQU_MAX_NV),
        ("pressure", D * EQU_MAX_NV),
        ("q", D * EQU_MAX_NV),
        ("f", D * EQU_MAX_NV),
        ("vol", D * EQU_MAX_NV),
        ("rminor", D * EQU_MAX_NV),
        ("rcentre", D * EQU_MAX_NV),
        ("kappa", D * EQU_MAX_NV),
        ("delta", D * EQU_MAX_NV),
        ("rsu", D * EQU_MAX_NSU),
        ("zsu", D * EQU_MAX_NSU),
    ]


class EquDiagEntry(ctypes.Structure):
    _fields_ = [
        ("param", ctypes.c_char * EQU_DIAG_PARAM_LEN),
        ("code", I),
        ("msg", ctypes.c_char * EQU_DIAG_MSG_LEN),
    ]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def lib_filename() -> str:
    return "libequapi.dll" if sys.platform == "win32" else "libequapi.so"


def default_lib_path() -> Path:
    env = os.environ.get("EQULIB_PATH")
    if env:
        return Path(env)
    return _repo_root() / "equ" / lib_filename()


def _apply_prototypes(lib: ctypes.CDLL) -> ctypes.CDLL:
    c = ctypes.c_char_p
    protos = {
        "equ_init": [],
        "equ_read_parm": [c],
        "equ_set_param": [c, D],
        "equ_set_param_str": [c, c],
        "equ_validate": [ctypes.POINTER(EquDiagEntry), I, ctypes.POINTER(I)],
        "equ_run": [I],
        "equ_get_state": [ctypes.POINTER(EquStateC)],
        "equ_get_psi_rz": [I, I, ctypes.POINTER(D)],
        "equ_write_geqdsk": [c, I],
        "equ_last_error": [c, I],
        "equ_finalize": [],
    }
    for name, args in protos.items():
        fn = getattr(lib, name)
        fn.argtypes = args
        fn.restype = I
    return lib


def load_library(path: Optional[str] = None) -> ctypes.CDLL:
    """Load ``libequapi.so``, check its layout, attach the prototypes."""
    # Resolved: CDLL of a bare name ("libequapi.so") would search the
    # loader's directories instead of the path that was checked.
    p = (Path(path) if path else default_lib_path()).resolve()
    if not p.exists():
        raise FileNotFoundError(
            f"{lib_filename()} not found at {p}. Build it with "
            "`make -C equ libequapi.so` or set EQULIB_PATH."
        )
    mode = getattr(ctypes, "RTLD_LAZY", 1)
    lib = ctypes.CDLL(str(p), mode=mode)
    from _abi_check import AbiMismatchError, check_state_layout
    try:
        check_state_layout(lib, prefix="equ", struct=EquStateC,
                           expected_version=EQU_STATE_ABI_VERSION, lib_name=p.name)
    except AbiMismatchError as exc:
        raise EqulibAbiError(str(exc)) from exc
    return _apply_prototypes(lib)
