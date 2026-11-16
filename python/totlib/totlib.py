"""High-level :class:`Tot` class wrapping ``libtotapi.so``.

TOT is the integrated TASK orchestrator: its parameter space is the
**union** of the per-module registries (eq, tr, fp, ti, wr, wrx). To
disambiguate same-named parameters across those modules, every name
passed to :py:meth:`Tot.set_param` MUST carry a namespace prefix in the
form ``"<ns>:<name>"``. See :data:`totlib._ffi.TOT_NAMESPACES` for the
full list.

Examples::

    from totlib import Tot

    with Tot() as tot:
        tot.set_param("eq:RR",  6.2)        # equilibrium major radius [m]
        tot.set_param("tr:DT",  0.01)       # transport time step [s]
        tot.set_param("fp:NSMAX", 2)        # FP species count
        tot.set_param("ti:RR",  6.2)        # TI major radius [m]
        tot.set_param("wrx:RFIN", 170.0)    # WRX RF frequency [GHz]
        tot.set_params({"tr:RA": 2.0, "tr:BB": 5.3})
        tot.run(ntmax=10)
        state = tot.get_state()

L-6 fan-out is wired: ``tot_init`` brings up eq + tr + ti + fp + wr
(eq since #209; with rollback on per-module init failure); ``tot_run``
advances the TR-authoritative loop only — cross-module coupling lives in
:class:`~totlib.pipeline.TotPipeline` (L-7a, Python-side) instead of
inside ``libtotapi.so``. The wrapper still accepts ``TOT_ERR_NOT_IMPL``
from ``tot_init`` and ``tot_finalize``, a leftover of the pre-L-6 stubs;
the live path is OK end-to-end on a built ``libtotapi.so``.
"""
from __future__ import annotations

import ctypes
import weakref
from typing import Any, Iterable, Mapping, Optional, Tuple, Union

from . import _ffi
from .errors import (
    TotlibError,
    TotlibInvalidParamError,
    TotlibNotInitializedError,
    raise_for_rc,
)
from .state import TotState


# Type alias for the items accepted by ``set_params``.
ParamItem = Union[Mapping[str, Any], Iterable[Tuple[str, Any]]]
_MAX_C_STRING_BYTES = 63              # intentional: tot_api_set_param name
                                       # buffer is CHARACTER(LEN=128), but
                                       # we share the 63-byte name cap with
                                       # the sibling packages (eq/tr/fp) so
                                       # the same param-name conventions
                                       # apply across modules.
_MAX_C_STRING_VALUE_BYTES = 256       # value buffer is CHARACTER(LEN=256);
                                       # the eq: and tr: registries refuse a
                                       # KNAMEQ of more than 80 characters
                                       # (rc 1): a long path is not cut


def _encode_name(s: str, max_bytes: int = _MAX_C_STRING_BYTES) -> bytes:
    """Encode a C string argument accepted by the TOT registry.

    ``max_bytes`` is the Fortran buffer size minus 1 (for NUL). Names
    use the default; values passed to ``set_param_str`` use
    ``_MAX_C_STRING_VALUE_BYTES`` (the Fortran buffer holds 256 bytes;
    the modules' file-name parameters hold 80 characters and refuse more).
    """
    if not isinstance(s, str):
        raise TotlibInvalidParamError(
            f"TOT C string arguments must be str, got {type(s).__name__}"
        )
    try:
        encoded = s.encode("ascii")
    except UnicodeEncodeError as exc:
        raise TotlibInvalidParamError(
            f"TOT C string {s!r} contains non-ASCII characters"
        ) from exc
    if b"\x00" in encoded:
        raise TotlibInvalidParamError(
            f"TOT C string {s!r} contains an embedded NUL byte"
        )
    if len(encoded) > max_bytes:
        raise TotlibInvalidParamError(
            f"TOT C string {s!r} is {len(encoded)} bytes; "
            f"maximum is {max_bytes}"
        )
    return encoded


class Tot:
    """In-process handle to libtotapi.so. One instance per process.

    libtotapi.so holds singleton Fortran state (COMMON blocks plus
    per-module module variables), so a second live :class:`Tot` is
    refused: its ``__init__`` raises
    :class:`~totlib.errors.TotlibNotInitializedError`. trlib / eqlib /
    tilib refuse a second live instance the same way.
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
            raise TotlibNotInitializedError(
                "another live Tot() instance exists; COMMON-block backend "
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
        rc = self._lib.tot_init()
        # L-6 fan-out: tot_init returns TOT_OK on success. TOT_ERR_NOT_IMPL
        # came from the pre-L-6 stubs; such a build is refused at load
        # now (#246), so accepting it here is only a leftover.
        if rc not in (_ffi.TOT_OK, _ffi.TOT_ERR_NOT_IMPL):
            raise_for_rc("tot_init", rc)
        self._closed = False

    def close(self) -> None:
        """Finalise the library. Idempotent."""
        if self._closed:
            self._release_live_instance()
            return
        rc = self._lib.tot_finalize()
        # Mark closed before raising so __del__ doesn't retry.
        self._closed = True
        self._release_live_instance()
        if rc not in (_ffi.TOT_OK, _ffi.TOT_ERR_NOT_IMPL):
            raise_for_rc("tot_finalize", rc)

    def __enter__(self) -> "Tot":
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

    # --- parameter naming guard ----------------------------------------
    @staticmethod
    def _validate_namespaced_name(name: str) -> None:
        """Reject names without a recognised ``<ns>:`` prefix.

        We catch the easy mistake (no colon, empty bare, unknown
        namespace) up-front in Python so the user gets a precise error
        message instead of the generic ``rc=1`` from
        ``tot_param_registry.f90``. Names that pass this check are
        forwarded verbatim to the C ABI; the per-module registries on
        the other side may still reject them with rc=1 if the bare
        name is unknown to that module.
        """
        if not isinstance(name, str) or ":" not in name:
            raise TotlibInvalidParamError(
                f"tot parameter name {name!r} is missing a namespace "
                f"prefix. tot is the orchestrator: every name must be "
                f"of the form '<ns>:<name>' where <ns> is one of "
                f"{_ffi.TOT_NAMESPACES}. "
                f"Examples: 'eq:RR', 'tr:DT', 'fp:NSMAX', 'ti:RR', "
                f"'wr:RFIN', 'wrx:RFIN'."
            )
        prefix, _, bare = name.partition(":")
        if not prefix or not bare:
            raise TotlibInvalidParamError(
                f"tot parameter name {name!r} has an empty namespace "
                f"prefix or empty bare name; expected '<ns>:<name>'."
            )
        if prefix not in _ffi.TOT_NAMESPACES:
            raise TotlibInvalidParamError(
                f"tot parameter name {name!r} uses unknown namespace "
                f"prefix {prefix!r}; supported prefixes are "
                f"{_ffi.TOT_NAMESPACES}."
            )

    # --- parameters -----------------------------------------------------
    def set_param(self, name: str, value: float) -> None:
        """Set one numeric parameter by namespaced name.

        ``name`` MUST be of the form ``"<ns>:<bare>"`` where ``<ns>``
        is one of ``("eq", "tr", "fp", "ti", "wr", "wrx")``. The bare
        name (after the colon) is forwarded to the matching per-module
        registry (eq_param_set, tr_param_set, etc.). Array element
        syntax ``"<ns>:NAME[i]"`` is supported for any per-module
        registry that accepts subscripts (e.g. ``"tr:PN[1]"``).

        Raises :class:`~totlib.errors.TotlibInvalidParamError` when:

        * ``name`` lacks a ``:`` prefix
        * the prefix is empty or unknown
        * the bare name is unknown to the per-module registry
          (caught downstream and reported as rc=1)
        """
        if self._closed:
            raise TotlibError("set_param on closed Tot")
        name_b = _encode_name(name)
        self._validate_namespaced_name(name)
        rc = self._lib.tot_set_param(
            name_b, ctypes.c_double(float(value))
        )
        raise_for_rc(f"tot_set_param('{name}', {value})", rc)

    def set_param_str(self, name: str, value: str) -> None:
        """Set one string-valued parameter by namespaced name.

        Only the ``tr:`` and ``eq:`` namespaces back string setters at
        L-3 (KNAMEQ etc.). Other namespaces will return rc=1 from the
        Fortran side and raise
        :class:`~totlib.errors.TotlibInvalidParamError`.

        Older builds of libtotapi.so without ``tot_set_param_str``
        will raise :class:`~totlib.errors.TotlibError`; rebuild the
        .so via ``make -C tot libtotapi.so`` to recover.
        """
        if self._closed:
            raise TotlibError("set_param_str on closed Tot")
        name_b = _encode_name(name)
        value_b = _encode_name(value, _MAX_C_STRING_VALUE_BYTES)
        self._validate_namespaced_name(name)
        try:
            fn = self._lib.tot_set_param_str
        except AttributeError as exc:
            raise TotlibError(
                "libtotapi.so does not export tot_set_param_str; "
                "rebuild the shared library from the L-3 registry PR."
            ) from exc
        rc = fn(name_b, value_b)
        raise_for_rc(f"tot_set_param_str('{name}', '{value}')", rc)

    def set_params(self, *args: ParamItem, **kwargs: Any) -> None:
        """Bulk-set namespaced parameters.

        Because Python keyword identifiers cannot contain a colon,
        kwargs alone CANNOT express namespaced names like ``"eq:RR"``.
        Pass a dict (or list of pairs) instead::

            tot.set_params({"eq:RR": 6.2, "tr:DT": 0.01})
            tot.set_params([("fp:NSMAX", 2), ("ti:RR", 6.2)])

        kwargs are still accepted but every key MUST already include a
        ``:`` somewhere (impossible from real Python kwargs, so this
        branch is mostly for ``**dict`` callers); they are validated
        the same way as positional dict entries.
        """
        items: list = []
        if args:
            if len(args) > 1:
                raise TotlibError(
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
            # Each name is fully validated by set_param; we just
            # forward. The early namespace check inside set_param
            # gives a much clearer error than the C-side rc=1.
            self.set_param(k, v)

    # --- run / state ----------------------------------------------------
    def run(self, ntmax: int) -> None:
        """Advance the integrated simulation ``ntmax`` time-steps.

        L-6 fan-out: ``tot_run`` dispatches to ``tr_api_run(ntmax)``
        (the dominant solver and the only one whose state is exposed
        via ``tot_state_t``). ``fp_api_run`` and ``wr_api_run`` are
        intentionally NOT invoked; cross-module coupling lives in
        :class:`~totlib.pipeline.TotPipeline` (L-7a, Python-side)
        instead of inside ``libtotapi.so``.

        ``ntmax=0`` prepares (when a parameter was set) and takes no step, but the loop's exit still sets RIPS = RIPE:
        a pending current ramp is lost and RIP stays where it was (the ``tr_run(0)`` note in ``tr/tr_api.h``).
        ``continue_run(0)`` only checks.
        """
        if self._closed:
            raise TotlibError("run on closed Tot")
        rc = self._lib.tot_run(int(ntmax))
        raise_for_rc(f"tot_run({ntmax})", rc)

    def continue_run(self, nsteps: int) -> None:
        """Advance the prepared case ``nsteps`` more steps without preparing again (``tot_continue``).

        ``tot_continue`` calls TR's ``tr_continue`` (``Trlib.continue_run``), as :meth:`run` calls ``tr_run``: the
        control parameters set since the last :meth:`run` or :meth:`continue_run` (``tr:RIPE``, ``tr:PNBTOT``,
        ``tr:PICTOT``, ``tr:PECTOT``, ``tr:PLHTOT``, ``tr:NTEQIT``, ``tr:TPRST``) take effect at its first step;
        ``nt``, ``T`` and the history go on. Every other ``tr:`` name and every ``eq:`` name is structural: set after
        a preparation it makes :meth:`continue_run` refuse, and the next :meth:`run` prepares again. There is no
        ``param_class`` here: ``Trlib.param_class`` answers for the same names (``eq:`` names are 0).

        Raises :class:`TotlibInvalidParamError` when TR refuses (no preparation yet, a failed run, a structural set
        since the preparation -- the message carries TR's record, which names the last one -- a bad value) or for a
        negative count, :class:`TotlibCalculationFailedError` when the loop fails.
        """
        if self._closed:
            raise TotlibError("continue_run on closed Tot")
        try:
            fn = self._lib.tot_continue
        except AttributeError as exc:
            raise TotlibError(
                "libtotapi.so does not export tot_continue; rebuild the shared library."
            ) from exc
        rc = fn(int(nsteps))
        if rc == 1:
            raise TotlibInvalidParamError(f"tot_continue({nsteps}): rc=1{self._tr_record_text()}")
        raise_for_rc(f"tot_continue({nsteps})", rc)

    def _tr_record_text(self) -> str:
        """TR's last failure record as ``": <text>"`` ('' when it cannot be read): tot has no record of its own, and
        ``tr_last_error`` is the one of the TR this ``Tot`` drives (the same image in mono; ``libtotapi.so`` links
        ``libtrapi.so``, the library ``trlib`` loads)."""
        try:
            from trlib import _ffi as tr_ffi
            lib = getattr(self._lib, "tr_last_error", None) or tr_ffi.load_library().tr_last_error
            e = tr_ffi.TrDiagEntry()
            lib(ctypes.byref(e))
            msg = e.msg.decode("ascii", errors="replace").rstrip("\x00")
            return f": {msg}" if msg else ""
        except Exception:
            return ""

    def get_state(self) -> TotState:
        """Copy the current TOT state into a :class:`TotState`.

        L-6 aggregates the TR-authoritative slots (``tr_present=1``,
        plus all 14 integrated scalars (incl. AJRFT) and the RN/RT/AJ/QP profiles).
        ``ti_present`` / ``fp_present`` / ``wr_present`` stay 0
        because those modules are init'd but not advanced from
        ``tot_run``; their state is reachable via per-module wrappers
        (``from trlib import Trlib`` etc.) or via
        :class:`~totlib.pipeline.TotPipeline` (L-7a).
        """
        if self._closed:
            raise TotlibError("get_state on closed Tot")
        c = _ffi.TotStateC()
        rc = self._lib.tot_get_state(ctypes.byref(c))
        raise_for_rc("tot_get_state", rc)
        return TotState.from_c(c)

    def get_scalar(self, name: str) -> float:
        """One of TR's named global results, ``"tr:<NAME>"`` (``Trlib.scalar_names()`` lists them).

        ``tot_get_scalar`` removes the prefix and asks TR (``tr_get_scalar``), so the value is the one
        ``Trlib.get_scalar`` returns for the TR this ``Tot`` drives. A name without ``tr:`` or an unknown one
        raises :class:`TotlibInvalidParamError`.
        """
        if self._closed:
            raise TotlibError("get_scalar on closed Tot")
        try:
            fn = self._lib.tot_get_scalar
        except AttributeError as exc:
            raise TotlibError(
                "libtotapi.so does not export tot_get_scalar; rebuild the shared library."
            ) from exc
        value = ctypes.c_double(0.0)
        rc = fn(_encode_name(name), ctypes.byref(value))
        raise_for_rc(f"tot_get_scalar('{name}')", rc)
        return float(value.value)

    # --- the run's history by name (Task 5b of #96) ----------------------
    def _history_fn(self, symbol: str):
        try:
            return getattr(self._lib, symbol)
        except AttributeError as exc:
            raise TotlibError(
                f"libtotapi.so does not export {symbol}; rebuild the shared library."
            ) from exc

    def history_names(self) -> list:
        """The names of the recorded columns as ``"tr:<NAME>"``, ``tr:T`` (the time) first."""
        if self._closed:
            raise TotlibError("history_names on closed Tot")
        count = int(self._history_fn("tot_history_count")())
        fn = self._history_fn("tot_history_name")
        names = []
        for i in range(1, count + 1):
            buf = ctypes.create_string_buffer(64)
            raise_for_rc(f"tot_history_name({i})", fn(i, buf, 64))
            names.append(buf.value.decode("ascii"))
        return names

    def history_length(self) -> int:
        """Rows TR has recorded since its last preparation (see ``Trlib.history_length``)."""
        if self._closed:
            raise TotlibError("history_length on closed Tot")
        return int(self._history_fn("tot_history_length")())

    def history_full(self) -> bool:
        """True when TR's history holds all its 10001 rows."""
        if self._closed:
            raise TotlibError("history_full on closed Tot")
        return bool(self._history_fn("tot_history_full")())

    def history(self, names: Optional[Iterable[str]] = None) -> dict:
        """TR's time history by name, ``{"tr:<NAME>": numpy.ndarray}`` (``Trlib.history`` through tot).

        ``names`` carry the ``tr:`` prefix; ``None`` returns every column. A name without it or an unknown
        one raises :class:`TotlibInvalidParamError`.
        """
        if self._closed:
            raise TotlibError("history on closed Tot")
        if names is None:
            wanted = self.history_names()
        elif isinstance(names, str):
            wanted = [names]
        else:
            wanted = list(names)
        fn = self._history_fn("tot_history_get")
        rows = self.history_length()
        out = {}
        for name in wanted:
            buf = (ctypes.c_double * max(rows, 1))()
            got = ctypes.c_int(0)
            raise_for_rc(f"tot_history_get('{name}')", fn(_encode_name(name), buf, rows, ctypes.byref(got)))
            values = buf[: int(got.value)]
            if _ffi.HAS_NUMPY:
                import numpy as np
                out[name] = np.array(values, dtype=np.float64)
            else:  # pragma: no cover - numpy is optional
                out[name] = list(values)
        return out


__all__ = ["Tot"]
