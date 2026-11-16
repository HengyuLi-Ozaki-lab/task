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
import re
import weakref
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Iterable, List, Optional, Union

from . import _ffi
from .errors import (
    TrFailure, TrlibError, TrlibParamError, TrlibRunError, TrlibStateError,
    raise_for_ierr,
)
from .state import TrState


_MAX_C_STRING_BYTES = 63              # name buffer is CHARACTER(LEN=64)
_MAX_C_STRING_VALUE_BYTES = 128       # value buffer is CHARACTER(LEN=128).
                                       # KNAMEQ holds 80: the library refuses
                                       # a longer value (rc 1), it is not cut


def _encode_name(s: str, max_bytes: int = _MAX_C_STRING_BYTES) -> bytes:
    """Encode a C string argument accepted by the TR registry.

    ``max_bytes`` is the Fortran buffer size minus 1 (for NUL). Names
    use the default; values passed to ``set_param_str`` use
    ``_MAX_C_STRING_VALUE_BYTES``.
    """
    if not isinstance(s, str):
        raise TrlibParamError(
            f"TR C string arguments must be str, got {type(s).__name__}"
        )
    try:
        encoded = s.encode("ascii")
    except UnicodeEncodeError as exc:
        raise TrlibParamError(
            f"TR C string {s!r} contains non-ASCII characters"
        ) from exc
    if b"\x00" in encoded:
        raise TrlibParamError(f"TR C string {s!r} contains an embedded NUL byte")
    if len(encoded) > max_bytes:
        raise TrlibParamError(
            f"TR C string {s!r} is {len(encoded)} bytes; "
            f"maximum is {max_bytes}"
        )
    return encoded


class TrDiagCode(IntEnum):
    """Diagnostic category codes returned by :py:meth:`Trlib.validate`.

    Mirrors ``enum tr_diag_code`` in ``tr/tr_api.h``. Use the integer
    value of the enum when comparing against :attr:`TrDiagEntryPy.code`,
    or compare directly: ``entry.code == TrDiagCode.OUT_OF_RANGE``.
    """

    OUT_OF_RANGE           = _ffi.TR_DIAG_OUT_OF_RANGE
    INCONSISTENT_PAIR      = _ffi.TR_DIAG_INCONSISTENT_PAIR
    OUT_OF_RANGE_AFTER_DEP = _ffi.TR_DIAG_OUT_OF_RANGE_AFTER_DEP
    FILE_MISSING           = _ffi.TR_DIAG_FILE_MISSING
    MISSING_REQUIRED       = _ffi.TR_DIAG_MISSING_REQUIRED


@dataclass(frozen=True)
class TrDiagEntryPy:
    """One pre-run validation diagnostic.

    User-facing return type for :py:meth:`Trlib.validate`. Strings are
    decoded from the underlying CHARACTER arrays with trailing NUL
    padding stripped — no ctypes objects leak through this dataclass.

    Attributes:
        param:   parameter name the diagnostic refers to (e.g. ``NSMAX``)
        code:    diagnostic category (compare against :class:`TrDiagCode`)
        message: human-readable description suitable for surfacing to UI
    """

    param: str
    code: int
    message: str


#: The largest count a C ``int`` holds. ctypes converts a Python integer to a
#: ``c_int`` argument with no range check (it keeps the low 32 bits), so
#: ``run`` checks the range itself.
_C_INT_MAX = 2**31 - 1


class Trlib:
    """In-process handle to libtrapi.so. One instance per process.

    libtrapi.so holds singleton Fortran state (COMMON blocks), so
    creating more than one live :class:`Trlib` is not meaningful; the
    second ``__init__`` call will call ``tr_init`` again and reset the
    shared state. This matches the design-spec contract.
    """

    _live_instance = None

    def __init__(self, lib_path: Optional[str] = None) -> None:
        # Start closed so _open() can transition to open.
        self._closed = True
        self._claim_live_instance()
        try:
            self._lib = _ffi.load_library(lib_path)
            self._open()
        except Exception:
            self._release_live_instance()
            raise

    # --- lifecycle ------------------------------------------------------
    def _claim_live_instance(self) -> None:
        cls = self.__class__
        ref = cls._live_instance
        live = ref() if ref is not None else None
        if live is not None:
            raise TrlibStateError(
                "another live Trlib() instance exists; COMMON-block backend "
                "cannot be safely shared"
            )
        cls._live_instance = weakref.ref(self)

    def _release_live_instance(self) -> None:
        cls = self.__class__
        ref = cls._live_instance
        if ref is not None and ref() is self:
            cls._live_instance = None

    def _open(self) -> None:
        if not self._closed:
            return
        ierr = self._lib.tr_init()
        raise_for_ierr("tr_init", ierr)
        self._closed = False

    def close(self) -> None:
        """Finalise the library. Idempotent."""
        if self._closed:
            self._release_live_instance()
            return
        ierr = self._lib.tr_finalize()
        # Mark closed before raising so __del__ doesn't retry.
        self._closed = True
        self._release_live_instance()
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
            _encode_name(name), ctypes.c_double(float(value))
        )
        raise_for_ierr(f"tr_set_param('{name}', {value})", ierr)

    def set_param_str(self, name: str, value: str) -> None:
        """Set one string-valued parameter (e.g. ``KNAMEQ``).

        ``libtrapi.so`` exposes ``tr_set_param_str`` as of the L-6
        registry-extension PR. Older builds will raise :class:`TrlibError`
        because :mod:`trlib._ffi` leaves the attribute missing; update
        the .so via ``make -C tr libtrapi.so`` to recover.
        """
        if self._closed:
            raise TrlibError("set_param_str on closed Trlib")
        try:
            fn = self._lib.tr_set_param_str
        except AttributeError as exc:
            raise TrlibError(
                "libtrapi.so does not export tr_set_param_str; "
                "rebuild the shared library after the L-6 registry "
                "extension PR."
            ) from exc
        ierr = fn(
            _encode_name(name),
            _encode_name(value, _MAX_C_STRING_VALUE_BYTES),
        )
        raise_for_ierr(f"tr_set_param_str('{name}', '{value}')", ierr)

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

        ``ntmax=0`` prepares (when a parameter was set) and takes no step, but the loop's exit still sets RIPS =
        RIPE: a pending current ramp is lost and RIP stays where it was (``tr/tr_api.h``). ``continue_run(0)`` only
        checks.

        Raises :class:`TrlibParamError`, before the library is called, for
        a count outside 0 to 2**31 - 1: ``tr_run`` takes a C ``int``, and a
        larger count would arrive modulo 2**32 (``2**32 + 20`` ran twenty
        steps).
        """
        if self._closed:
            raise TrlibError("run on closed Trlib")
        count = int(ntmax)
        if not 0 <= count <= _C_INT_MAX:
            raise TrlibParamError(
                f"tr_run: the step count must be 0 to {_C_INT_MAX} "
                "(tr_run takes a C int)"
            )
        ierr = self._lib.tr_run(count)
        if ierr == _ffi.TR_ERR_CALC_FAILED:
            # The library records the first failure of the run: say what it was.
            raise TrlibRunError(f"tr_run({ntmax}): ierr={ierr}", failure=self._failure_or_none())
        raise_for_ierr(f"tr_run({ntmax})", ierr)

    def continue_run(self, nsteps: int) -> None:
        """Advance the prepared case ``nsteps`` more steps without preparing again (``tr_continue``).

        The control parameters set since the last :meth:`run` or :meth:`continue_run` (:meth:`param_class` 1:
        RIPE, PNBTOT, PICTOT, PECTOT, PLHTOT, NTEQIT, TPRST) take effect at its first step; ``nt`` and the history
        go on, and RIP ramps from the last call's RIPE to RIPE over these steps. It equals ``tr2``'s ``C`` on the
        same cut (not with NCLASS: ``tr/tr_api.h``); a run in several calls is not bit for bit one call (each call
        begins with the loop's prologue).

        Raises :class:`TrlibParamError` with ``failure`` (kind ``REFUSED``) when the library refuses: no prepared
        case, the last run failed (until a :meth:`run` prepares again: after any set), a structural parameter set
        since the preparation (``failure.detail`` names the last one; :meth:`run` prepares again), or a value
        :meth:`run`'s checks refuse; and, before the call, for a count outside 0 to 2**31 - 1 (``failure`` None).
        :class:`TrlibRunError` with ``failure`` when the loop fails, as :meth:`run`.
        """
        if self._closed:
            raise TrlibError("continue_run on closed Trlib")
        count = int(nsteps)
        if not 0 <= count <= _C_INT_MAX:
            raise TrlibParamError(
                f"tr_continue: the step count must be 0 to {_C_INT_MAX} "
                "(tr_continue takes a C int)"
            )
        ierr = self._scalar_fn("tr_continue")(count)
        if ierr == _ffi.TR_ERR_CALC_FAILED:
            raise TrlibRunError(f"tr_continue({nsteps}): ierr={ierr}", failure=self._failure_or_none())
        if ierr == _ffi.TR_ERR_INVALID:
            failure = self._failure_or_none()
            why = f": {failure.detail}" if failure is not None else ""
            raise TrlibParamError(f"tr_continue({nsteps}) refused{why}", failure=failure)
        raise_for_ierr(f"tr_continue({nsteps})", ierr)

    def param_class(self, name: str) -> int:
        """1 for a control parameter (:meth:`continue_run` takes it in), 0 for a structural one (a name the setter
        takes, or any ``eq:`` name: :meth:`run` prepares again after it), -1 for a name the setter does not know."""
        if self._closed:
            raise TrlibError("param_class on closed Trlib")
        return int(self._scalar_fn("tr_param_class")(_encode_name(name)))

    def _failure_or_none(self) -> Optional[TrFailure]:
        try:
            return self.last_error()
        except TrlibError:  # a library built before tr_last_error
            return None

    def last_error(self) -> TrFailure:
        """The first failure of the last :meth:`run` or :meth:`continue_run`, or ``kind == "NONE"``.

        Cleared at the start of every ``run`` and ``continue_run``. Older builds without
        ``tr_last_error`` raise :class:`TrlibError`.
        """
        if self._closed:
            raise TrlibError("last_error on closed Trlib")
        try:
            fn = self._lib.tr_last_error
        except AttributeError as exc:
            raise TrlibError(
                "libtrapi.so does not export tr_last_error; "
                "rebuild the shared library."
            ) from exc
        e = _ffi.TrDiagEntry()
        fn(ctypes.byref(e))
        kind = e.param.decode("ascii", errors="replace").rstrip("\x00")
        msg = e.msg.decode("ascii", errors="replace").rstrip("\x00")
        nt, time, detail = 0, 0.0, msg
        m = re.match(r"nt=(-?\d+) t=\s*(\S+) s: (.*)$", msg)
        if m:
            nt, time, detail = int(m.group(1)), float(m.group(2)), m.group(3)
        return TrFailure(kind=kind, code=int(e.code), nt=nt, time=time, detail=detail)

    def get_state(self) -> TrState:
        """Copy the current simulation state into a :class:`TrState`."""
        if self._closed:
            raise TrlibError("get_state on closed Trlib")
        c = _ffi.TrStateC()
        ierr = self._lib.tr_get_state(ctypes.byref(c))
        raise_for_ierr("tr_get_state", ierr)
        state = TrState.from_c(c)
        # All the named scalars (the 14 of the struct are among them, read from the same globals). A library built
        # before the scalar table (PR 1's) keeps the 14 that from_c filled.
        if hasattr(self._lib, "tr_scalar_count") and hasattr(self._lib, "tr_get_scalar"):
            state.scalars = {n: self.get_scalar(n) for n in self.scalar_names()}
        return state

    # --- outputs by name (PR 2 of #96) ----------------------------------
    def _scalar_fn(self, symbol: str):
        try:
            return getattr(self._lib, symbol)
        except AttributeError as exc:
            raise TrlibError(
                f"libtrapi.so does not export {symbol}; rebuild the shared library."
            ) from exc

    def scalar_names(self) -> List[str]:
        """The names :meth:`get_scalar` accepts, in the library's order (31)."""
        if self._closed:
            raise TrlibError("scalar_names on closed Trlib")
        count = int(self._scalar_fn("tr_scalar_count")())
        fn = self._scalar_fn("tr_scalar_name")
        names = []
        for i in range(1, count + 1):
            buf = ctypes.create_string_buffer(64)
            raise_for_ierr(f"tr_scalar_name({i})", fn(i, buf, 64))
            names.append(buf.value.decode("ascii"))
        return names

    def get_scalar(self, name: str) -> float:
        """One global result by name, as of the last step TR computed the globals on.

        TRGLOB computes them on output steps and on the last step of a run, so they are current after
        :meth:`run`. Units are those of ``tr/trrslt_globals.f90`` (``tr_mcp``'s state schema lists them).
        An unknown name raises :class:`TrlibParamError`.
        """
        if self._closed:
            raise TrlibError("get_scalar on closed Trlib")
        fn = self._scalar_fn("tr_get_scalar")
        value = ctypes.c_double(0.0)
        ierr = fn(_encode_name(name), ctypes.byref(value))
        raise_for_ierr(f"tr_get_scalar('{name}')", ierr)
        return float(value.value)

    # --- the run's history by name (PR 2 of #96, Task 5b) ----------------
    def history_names(self) -> List[str]:
        """The names of the recorded columns, "T" (the time) first."""
        if self._closed:
            raise TrlibError("history_names on closed Trlib")
        count = int(self._scalar_fn("tr_history_count")())
        fn = self._scalar_fn("tr_history_name")
        names = []
        for i in range(1, count + 1):
            buf = ctypes.create_string_buffer(64)
            raise_for_ierr(f"tr_history_name({i})", fn(i, buf, 64))
            names.append(buf.value.decode("ascii"))
        return names

    def history_length(self) -> int:
        """Rows recorded since the last preparation: the state at t = 0, then one per ``NGTSTP`` steps.

        A row is recorded at every step that is a multiple of ``NGTSTP``, so a call of :meth:`run` adds the multiples among the
        steps it runs (``nsteps // NGTSTP`` only when it starts on one: ``run(5)`` twice adds 3 and 3, ``run(1)`` adds 0 or 1). 0 before the
        first run. ``tr_prep`` starts the history again, so a run after a changed parameter does.
        """
        if self._closed:
            raise TrlibError("history_length on closed Trlib")
        return int(self._scalar_fn("tr_history_length")())

    def history_full(self) -> bool:
        """True when the history holds 10001 rows (``NTM``): TR then stops recording, silently on its side."""
        if self._closed:
            raise TrlibError("history_full on closed Trlib")
        return bool(self._scalar_fn("tr_history_full")())

    def history(self, names: Union[None, str, Iterable[str]] = None) -> Dict[str, "object"]:
        """The recorded columns by name, as ``{name: numpy.ndarray}`` of float64 (lists without numpy).

        ``names`` is one name, several, or ``None`` for every column of :meth:`history_names`. The values are
        TR's single-precision history. The last row agrees with :meth:`get_scalar` to about 1e-7 (relative) only
        when the last step of the call was recorded (a multiple of ``NGTSTP``) and the buffer was not full: after
        ``run(1)`` with the defaults ``history("T")["T"][-1]`` is 0 while ``get_scalar("T")`` is ``DT``, and
        recording stops at capacity (:meth:`history_full` is true), so the history lags the state once the run
        advances past it; a history that fills exactly at the end of a call is still current. An unknown name raises
        :class:`TrlibParamError`.
        """
        if self._closed:
            raise TrlibError("history on closed Trlib")
        if names is None:
            wanted = self.history_names()
        elif isinstance(names, str):
            wanted = [names]
        else:
            wanted = list(names)
        fn = self._scalar_fn("tr_history_get")
        rows = self.history_length()
        out: Dict[str, object] = {}
        for name in wanted:
            buf = (ctypes.c_double * max(rows, 1))()
            got = ctypes.c_int(0)
            raise_for_ierr(f"tr_history_get('{name}')", fn(_encode_name(name), buf, rows, ctypes.byref(got)))
            values = buf[: int(got.value)]
            if _ffi.HAS_NUMPY:
                import numpy as np
                out[name] = np.array(values, dtype=np.float64)
            else:  # pragma: no cover - numpy is optional
                out[name] = list(values)
        return out

    # --- validation (Issue #143) ---------------------------------------
    def validate(self) -> List[TrDiagEntryPy]:
        """Run pre-run cross-parameter validation.

        Returns the list of diagnostics produced by ``tr_validate``
        (read-only against the current tr state). The recommended
        workflow is::

            tr.set_params(...)
            diags = tr.validate()
            if diags:
                # surface / fix / re-validate, then run
                ...
            tr.run(...)

        Return-code mapping (``tr_api_validate`` contract):

        * ``TR_OK`` (0)            -> empty list (clean state)
        * ``TR_ERR_INVALID`` (1)   -> non-empty list (the diagnostics
          themselves are the payload; ``ierr == 1`` only signals
          "diagnostics present" so callers do not need to inspect the
          C-level return code)
        * ``TR_ERR_NOT_INIT`` (2)  -> :class:`TrlibStateError`

        Older builds without ``tr_validate`` raise :class:`TrlibError`
        (rebuild via ``make -C tr libtrapi.so``). The method does not
        modify any tr state.
        """
        if self._closed:
            raise TrlibError("validate on closed Trlib")
        try:
            fn = self._lib.tr_validate
        except AttributeError as exc:
            raise TrlibError(
                "libtrapi.so does not export tr_validate; "
                "rebuild the shared library after the #143 PR."
            ) from exc

        cap = _ffi.TR_DIAG_DEFAULT_CAP
        buf = (_ffi.TrDiagEntry * cap)()
        ndiag = ctypes.c_int(0)
        ierr = fn(buf, cap, ctypes.byref(ndiag))
        # tr_validate counts every finding, also those beyond the buffer, and
        # changes no state: ask once more with room for all of them.
        if ndiag.value > cap and ierr in (_ffi.TR_OK, _ffi.TR_ERR_INVALID):
            cap = int(ndiag.value)
            buf = (_ffi.TrDiagEntry * cap)()
            ierr = fn(buf, cap, ctypes.byref(ndiag))

        # Contract: ierr==2 (NOT_INIT) is the only one that maps to an
        # exception; ierr==0 and ierr==1 both return the list (empty /
        # not).
        if ierr == _ffi.TR_ERR_NOT_INIT:
            raise TrlibStateError(f"tr_validate: ierr={ierr}")
        if ierr not in (_ffi.TR_OK, _ffi.TR_ERR_INVALID):
            # Defensive: future codes should not silently masquerade
            # as success. Reuse the central ierr -> exception mapping.
            raise_for_ierr("tr_validate", ierr)

        n = int(ndiag.value)
        # Fortran push_diag increments nlocal past diag_cap but skips
        # the write (tr_api.f90), so ndiag_out can exceed cap. Clamp
        # and warn so the caller knows results are truncated instead
        # of IndexError-ing off the end of the ctypes buffer.
        if n > cap:
            import warnings
            warnings.warn(
                f"tr_validate produced {n} diagnostics but buffer "
                f"capacity is {cap}; results are truncated. Increase "
                f"trlib._ffi.TR_DIAG_DEFAULT_CAP.",
                RuntimeWarning,
                stacklevel=2,
            )
            n = cap
        out: List[TrDiagEntryPy] = []
        for i in range(n):
            entry = buf[i]
            param = entry.param.decode("ascii", errors="replace").rstrip("\x00")
            message = entry.msg.decode("ascii", errors="replace").rstrip("\x00")
            out.append(TrDiagEntryPy(
                param=param,
                code=int(entry.code),
                message=message,
            ))
        return out

    def check_bpsd_pull(self) -> bool:
        """Verify that BPSD has the 3 eq-pushed slots (device, equ1D,
        metric1D) by performing a non-mutating round-trip pull into
        local discardable types. plasmaf is excluded: it is tr's own
        BPSD output, absent on a fresh eq -> tr pipeline.

        Used by TotPipeline as a pre-tr-run verification of the eq -> tr
        BPSD coupling: after eq.run() pushes equ1D/metric1D into BPSD,
        a False return signals broker failure / missing eq step / wrong
        pipeline order. TRCOMM is unaffected.

        Returns True iff all 3 BPSD slots are pullable (per-slot ierr==0).
        """
        if self._closed:
            raise TrlibError("check_bpsd_pull on closed Trlib")
        ok = ctypes.c_int(0)
        self._lib.tr_check_bpsd_pull(ctypes.byref(ok))
        return ok.value == 1


__all__ = ["Trlib", "TrDiagCode", "TrDiagEntryPy"]
