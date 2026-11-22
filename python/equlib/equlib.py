"""``Equ``: the in-process handle to ``libequapi.so`` (TASK/EQU).

    from equlib import Equ
    with Equ() as equ:
        equ.read_parm("equparm")           # an &EQU namelist file
        equ.set_param("TCUR", 0.3)         # override any name
        equ.run()                          # mode 1: the menu's R
        state = equ.get_state()
        equ.write_geqdsk("quest.geqdsk")

EQU keeps its state in Fortran modules: one live ``Equ`` per process.
File names (``KNAMCOIL``, the paths given here) are relative to the working
directory, as in the program.
"""
from __future__ import annotations

import ctypes
import math
import os
import threading
import weakref
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Union

from . import _ffi
from .errors import (EqulibCalculationFailedError, EqulibInitError, EqulibInvalidParamError,
                     raise_for_rc)
from .state import EquState

_NAME_MAX = 63          # bytes of a name (the C side holds 64 with the NUL)
_VALUE_MAX = 80         # the longest CHARACTER of &EQU
_PATH_MAX = 1023
_DIAG_CAP = 64
_C_INT_MAX = 2**31 - 1


@dataclass(frozen=True)
class EquDiag:
    """One finding of :meth:`Equ.validate`."""

    param: str
    code: int
    message: str


def _encode(text: str, what: str, limit: int) -> bytes:
    if not isinstance(text, str):
        raise EqulibInvalidParamError(f"{what} must be a str, not {type(text).__name__}")
    if "\x00" in text:
        raise EqulibInvalidParamError(f"{what} contains a NUL character")
    try:
        raw = text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise EqulibInvalidParamError(f"{what} must be ASCII: {text!r}") from exc
    if len(raw.rstrip(b" ")) > limit:
        raise EqulibInvalidParamError(f"{what} is longer than {limit} characters")
    return raw


# One owner of the Fortran state per process, whatever subclass holds it.
_OWNER_LOCK = threading.Lock()
_owner: Optional["weakref.ReferenceType[Equ]"] = None


class Equ:
    """Handle to libequapi.so. Context manager; ``close()`` is idempotent.

    One live handle per process (EQU's state is one set of Fortran modules),
    and not for use from several threads at once.
    """

    def __init__(self, lib_path: Optional[str] = None) -> None:
        global _owner
        self._closed = True
        with _OWNER_LOCK:
            live = _owner() if _owner is not None else None
            if live is not None and not live._closed:
                raise EqulibInitError("another live Equ() exists in this process: "
                                      "EQU's state is one set of Fortran modules")
            _owner = weakref.ref(self)
            try:
                self._lib = _ffi.load_library(lib_path)
                raise_for_rc("equ_init", self._lib.equ_init())
                self._closed = False
            except Exception:
                _owner = None
                raise

    # --- life cycle ----------------------------------------------------
    @property
    def closed(self) -> bool:
        return self._closed

    def __enter__(self) -> "Equ":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        global _owner
        if self._closed:
            return
        self._lib.equ_finalize()
        self._closed = True
        with _OWNER_LOCK:
            if _owner is not None and _owner() is self:
                _owner = None

    def reset(self) -> None:
        """``equ_init`` again: every input back to EQU's defaults."""
        self._check_open()
        raise_for_rc("equ_init", self._lib.equ_init())

    def _check_open(self) -> None:
        if self._closed:
            raise EqulibInitError("this Equ is closed")

    def last_error(self) -> str:
        self._check_open()
        buf = ctypes.create_string_buffer(512)
        self._lib.equ_last_error(buf, len(buf))
        return buf.value.decode("ascii", "replace")

    def _raise(self, func: str, rc: int) -> None:
        if rc != 0:
            raise_for_rc(func, rc, self.last_error())

    # --- inputs --------------------------------------------------------
    def read_parm(self, path: Union[str, "os.PathLike[str]"]) -> None:
        """Read an ``&EQU`` namelist file (as the program reads ``equparm``)."""
        self._check_open()
        raw = _encode(str(path), "path", _PATH_MAX)
        self._raise("equ_read_parm", self._lib.equ_read_parm(raw))

    def set_param(self, name: str, value: float) -> None:
        """A numeric parameter: ``NAME`` or ``NAME[i]`` (Fortran's index)."""
        self._check_open()
        raw = _encode(name, "name", _NAME_MAX)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EqulibInvalidParamError(f"{name}: a number is needed, not {value!r}")
        if not math.isfinite(float(value)):
            raise EqulibInvalidParamError(f"{name}: {value!r} is not finite")
        self._raise(f"equ_set_param({name})", self._lib.equ_set_param(raw, float(value)))

    def set_param_str(self, name: str, value: str) -> None:
        """DEVICE, DEVNAM, TITLE or KNAMCOIL."""
        self._check_open()
        rn = _encode(name, "name", _NAME_MAX)
        rv = _encode(value, f"{name}'s value", _VALUE_MAX)
        self._raise(f"equ_set_param_str({name})", self._lib.equ_set_param_str(rn, rv))

    def set_params(self, params: Union[Mapping[str, Any], Iterable[tuple[str, Any]], None] = None,
                   **kwargs: Any) -> None:
        """Several at once, in order; a ``str`` value goes to ``set_param_str``.

        Not transactional: the names before a refused one stay set.
        """
        items: list[tuple[str, Any]] = []
        if params is not None:
            items.extend(params.items() if isinstance(params, Mapping) else params)
        items.extend(kwargs.items())
        for name, value in items:
            if isinstance(value, str):
                self.set_param_str(name, value)
            else:
                self.set_param(name, value)

    def validate(self) -> list[EquDiag]:
        """Every check of the inputs in one batch; ``[]`` when none fails."""
        self._check_open()
        cap = _DIAG_CAP
        while True:
            arr = (_ffi.EquDiagEntry * cap)()
            n = ctypes.c_int(0)
            rc = self._lib.equ_validate(arr, cap, ctypes.byref(n))
            if rc not in (_ffi.EQU_OK, _ffi.EQU_ERR_INVALID):
                self._raise("equ_validate", rc)
            if n.value <= cap:     # the library counts past cap: ask again
                break
            cap = n.value
        return [EquDiag(arr[i].param.decode("ascii", "replace"), int(arr[i].code),
                        arr[i].msg.decode("ascii", "replace"))
                for i in range(n.value)]

    # --- run and results -----------------------------------------------
    def run(self, mode: int = 1) -> None:
        """Mode 1: the menu's R; mode 0: its first step (equ_prof)."""
        self._check_open()
        if isinstance(mode, bool) or not isinstance(mode, int) or abs(mode) > _C_INT_MAX:
            raise EqulibInvalidParamError(f"mode must be an int, not {mode!r}")
        self._raise(f"equ_run({mode})", self._lib.equ_run(mode))

    def get_state(self) -> EquState:
        """The result of the last successful run."""
        self._check_open()
        st = _ffi.EquStateC()
        self._raise("equ_get_state", self._lib.equ_get_state(ctypes.byref(st)))
        if st.nr == 0:
            raise EqulibInvalidParamError("get_state: no equilibrium (run first)")
        return EquState.from_c(st)

    def get_psi_rz(self):
        """psi(R, Z) as a numpy array indexed ``[i_r, i_z]``."""
        import numpy as np
        self._check_open()
        st = _ffi.EquStateC()
        self._raise("equ_get_state", self._lib.equ_get_state(ctypes.byref(st)))
        nr, nz = st.nr, st.nz
        if nr == 0:
            raise EqulibInvalidParamError("get_psi_rz: no equilibrium (run first)")
        buf = (ctypes.c_double * (nr * nz))()
        self._raise("equ_get_psi_rz", self._lib.equ_get_psi_rz(nr, nz, buf))
        # C order psi[(iz-1)*nr + (ir-1)]: reshape (nz, nr), transpose to [ir, iz].
        return np.frombuffer(buf, dtype=np.float64).reshape(nz, nr).T.copy()

    def write_geqdsk(self, path: Union[str, "os.PathLike[str]"], overwrite: bool = False) -> None:
        """Write the last run's equilibrium as G-EQDSK (EQU's own writer).

        EQU's file name holds 80 ASCII characters; a longer path, or one
        whose directories are not ASCII, is written from its directory under
        its base name: the process's working directory is changed for the
        call and put back, so no other thread may rely on it meanwhile.
        """
        self._check_open()
        text = str(path)
        if text.isascii() and len(text) <= _VALUE_MAX:
            raw = _encode(text, "path", _VALUE_MAX)
            self._raise("equ_write_geqdsk",
                        self._lib.equ_write_geqdsk(raw, 1 if overwrite else 0))
            return
        head, base = os.path.split(os.path.abspath(text))
        raw = _encode(base, "the file name", _VALUE_MAX)
        here = os.getcwd()
        try:
            os.chdir(head)
        except OSError as exc:
            raise EqulibCalculationFailedError(f"write_geqdsk: {head}: {exc}") from exc
        try:
            rc = self._lib.equ_write_geqdsk(raw, 1 if overwrite else 0)
        finally:
            os.chdir(here)
        self._raise("equ_write_geqdsk", rc)

