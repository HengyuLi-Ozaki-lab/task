"""High-level ``Trlib`` class.

See ``docs/superpowers/specs/2026-04-17-tr-library-design.md`` §6.3.

Usage::

    from trlib import Trlib

    with Trlib() as tr:
        tr.set_params(RR=7.5, BB=5.3)   # scalar kwargs only
        tr.set_param("PN[1]", 0.7)      # array elements via set_param
        tr.run(ntmax=100)
        state = tr.get_state()
        print(state.scalars["T"])
"""
from __future__ import annotations

import ctypes
from typing import Optional

from . import _ffi
from .errors import TrlibError, raise_for_ierr
from .state import TrState


class Trlib:
    """In-process handle to libtrapi.so. One instance per process.

    libtrapi.so holds singleton Fortran state (COMMON blocks), so
    creating more than one live :class:`Trlib` is not meaningful; the
    second ``__init__`` call will call ``tr_init`` again and reset the
    shared state. This matches the design-spec contract.
    """

    def __init__(self, lib_path: Optional[str] = None) -> None:
        self._lib = _ffi.load_library(lib_path)
        # Start closed so _open() can transition to open.
        self._closed = True
        self._open()

    # --- lifecycle ------------------------------------------------------
    def _open(self) -> None:
        if not self._closed:
            return
        ierr = self._lib.tr_init()
        raise_for_ierr("tr_init", ierr)
        self._closed = False

    def close(self) -> None:
        """Finalise the library. Idempotent."""
        if self._closed:
            return
        ierr = self._lib.tr_finalize()
        # Mark closed before raising so __del__ doesn't retry.
        self._closed = True
        raise_for_ierr("tr_finalize", ierr)

    def __enter__(self) -> "Trlib":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            # Destructors must never raise.
            pass

    @property
    def closed(self) -> bool:
        return self._closed

    # --- parameters -----------------------------------------------------
    def set_param(self, name: str, value: float) -> None:
        """Set one parameter by name. ``name`` is forwarded verbatim.

        Array elements use the ``NAME[i]`` syntax (e.g. ``"PN[1]"``);
        see the C ABI spec for the full registry.
        """
        if self._closed:
            raise TrlibError("set_param on closed Trlib")
        ierr = self._lib.tr_set_param(
            name.encode("ascii"), ctypes.c_double(float(value))
        )
        raise_for_ierr(f"tr_set_param('{name}', {value})", ierr)

    def set_params(self, **kwargs: float) -> None:
        """Bulk-set **scalar** parameters by keyword.

        Array elements are NOT supported here because Python keyword
        arguments cannot contain ``[`` or ``]``. Earlier drafts
        attempted a ``PN__1`` -> ``PN[1]`` convenience conversion via
        ``str.replace`` but that produced malformed names. To set an
        array element, call :py:meth:`set_param` directly::

            tr.set_param("PN[1]", 0.7)

        Names containing ``__`` are rejected up-front as a likely
        array-syntax mistake.
        """
        for k, v in kwargs.items():
            if "__" in k:
                raise TrlibError(
                    f"set_params() received '{k}' which contains '__'. "
                    "set_params is scalar-only; use "
                    "set_param('NAME[i]', value) for array elements."
                )
            self.set_param(k, v)

    # --- run / state ----------------------------------------------------
    def run(self, ntmax: int) -> None:
        """Advance the simulation ``ntmax`` time-steps.

        ``ntmax=0`` is a valid no-op used by the smoke test.
        """
        if self._closed:
            raise TrlibError("run on closed Trlib")
        ierr = self._lib.tr_run(int(ntmax))
        raise_for_ierr(f"tr_run({ntmax})", ierr)

    def get_state(self) -> TrState:
        """Copy the current simulation state into a :class:`TrState`."""
        if self._closed:
            raise TrlibError("get_state on closed Trlib")
        c = _ffi.TrStateC()
        ierr = self._lib.tr_get_state(ctypes.byref(c))
        raise_for_ierr("tr_get_state", ierr)
        return TrState.from_c(c)


__all__ = ["Trlib"]
