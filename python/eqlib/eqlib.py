"""High-level :class:`Eq` class wrapping ``libeqapi.so``.

See ``docs/superpowers/specs/2026-04-17-tr-library-design.md`` §6.3 for
the common 2-layer design shared with trlib / tilib; eq follows the same
contract with one extra entry point (``eq_set_param_str``).

Usage::

    from eqlib import Eq

    with Eq() as eq:
        eq.set_params(RR=3.0, BB=3.0, RIP=1.0)
        eq.set_param("PSIB[0]", 0.0)        # array element (0-origin!)
        eq.set_param_str("KNAMEQ", "eqdata")  # string parameter
        eq.run(mode=1)                       # 1 == real EQDSK load
        state = eq.get_state()
        print(state.scalars["raxis"])
"""
from __future__ import annotations

import ctypes
from typing import Any, Mapping, Optional

from . import _ffi
from .errors import EqlibError, raise_for_rc
from .state import EqState


class Eq:
    """In-process handle to libeqapi.so. One instance per process.

    libeqapi.so holds singleton Fortran state (COMMON blocks plus
    ``eqcom*_mod`` MODULE variables). Creating more than one live
    :class:`Eq` is not meaningful; the second ``__init__`` will call
    ``eq_init`` again and reset the shared state.
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
        rc = self._lib.eq_init()
        raise_for_rc("eq_init", rc)
        self._closed = False

    def close(self) -> None:
        """Finalise the library. Idempotent."""
        if self._closed:
            return
        rc = self._lib.eq_finalize()
        # Mark closed before raising so __del__ doesn't retry.
        self._closed = True
        raise_for_rc("eq_finalize", rc)

    def __enter__(self) -> "Eq":
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
        """Set one numeric parameter by name.

        ``name`` is forwarded verbatim to ``eq_set_param``; parsing
        of array subscripts (``"PSIB[0]"``, ``"RIPFC[3]"``) happens in
        ``eq_param_registry.f90`` (Phase L-3).

        EQ-specific note: ``PSIB`` is **0-origin** because the
        underlying Fortran is ``REAL(8) :: PSIB(0:5)``. Bare
        ``"PSIB"`` (no subscript) is rejected with ``rc == 1`` because
        the registry uses idx == -1 as the "no subscript" sentinel.
        Use ``set_param("PSIB[0]", v)``. All other 1D parameters
        (``RIPFC``, ``RPFC``, ``ZPFC``, ``WPFC``) are 1-origin.
        """
        if self._closed:
            raise EqlibError("set_param on closed Eq")
        rc = self._lib.eq_set_param(
            name.encode("ascii"), ctypes.c_double(float(value))
        )
        raise_for_rc(f"eq_set_param('{name}', {value})", rc)

    def set_param_str(self, name: str, value: str) -> None:
        """Set one string-valued parameter (e.g. ``KNAMEQ``).

        Supported names (CHARACTER(LEN=80) on the Fortran side):
        ``KNAMEQ, KNAMEQ2, KNAMWR, KNAMWM, KNAMFP, KNAMFO, KNAMPF``.

        Older builds without ``eq_set_param_str`` will raise
        :class:`EqlibError`; rebuild the .so via
        ``make -C eq libeqapi.so`` to recover.
        """
        if self._closed:
            raise EqlibError("set_param_str on closed Eq")
        try:
            fn = self._lib.eq_set_param_str
        except AttributeError as exc:
            raise EqlibError(
                "libeqapi.so does not export eq_set_param_str; "
                "rebuild the shared library after the L-3 registry PR."
            ) from exc
        rc = fn(name.encode("ascii"), value.encode("ascii"))
        raise_for_rc(f"eq_set_param_str('{name}', '{value}')", rc)

    def set_params(self, *args: Mapping[str, Any], **kwargs: Any) -> None:
        """Bulk-set scalar parameters.

        Accepts either a single dict positional argument, a list of
        ``(name, value)`` pairs, or scalar kwargs::

            eq.set_params(RR=3.0, BB=3.0)
            eq.set_params({"RR": 3.0, "BB": 3.0})
            eq.set_params([("RR", 3.0), ("BB", 3.0)])

        Array elements are NOT supported here because Python keyword
        arguments cannot contain ``[`` or ``]``. To set an array
        element, call :py:meth:`set_param` directly::

            eq.set_param("PSIB[0]", 0.0)

        Names containing ``__`` are rejected up-front as a likely
        array-syntax mistake (matches trlib / tilib behaviour).
        """
        items: list = []
        if args:
            if len(args) > 1:
                raise EqlibError(
                    "set_params() takes at most one positional argument; "
                    f"got {len(args)}"
                )
            arg0 = args[0]
            if isinstance(arg0, Mapping):
                items.extend(arg0.items())
            else:
                # Assume iterable of (name, value) pairs.
                items.extend(arg0)
        items.extend(kwargs.items())

        for k, v in items:
            if "__" in k:
                raise EqlibError(
                    f"set_params() received '{k}' which contains '__'. "
                    "set_params is scalar-only; use "
                    "set_param('NAME[i]', value) for array elements."
                )
            self.set_param(k, v)

    # --- run / state ----------------------------------------------------
    def run(self, mode: int = 1) -> None:
        """Run the EQ solver.

        Modes:
            1 (default) - real EQDSK load via ``equnit::eq_load`` using
                the current ``MODELG`` + ``KNAMEQ``. This is currently
                the only implemented mode.
            0 - reserved for EQCALQ-style direct solve, returns
                ``EQ_ERR_NOT_IMPL`` (pending future implementation).
            other - returns ``EQ_ERR_NOT_IMPL``.
        """
        if self._closed:
            raise EqlibError("run on closed Eq")
        rc = self._lib.eq_run(int(mode))
        raise_for_rc(f"eq_run({mode})", rc)

    def get_state(self) -> EqState:
        """Copy the current EQ state into an :class:`EqState`."""
        if self._closed:
            raise EqlibError("get_state on closed Eq")
        c = _ffi.EqStateC()
        rc = self._lib.eq_get_state(ctypes.byref(c))
        raise_for_rc("eq_get_state", rc)
        return EqState.from_c(c)


__all__ = ["Eq"]
