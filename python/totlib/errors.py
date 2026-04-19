"""Exception hierarchy for totlib.

Mirrors the ``enum tot_error`` codes declared in ``tot/tot_api.h``:

    TOT_OK              = 0
    TOT_ERR_INVALID     = 1  (invalid parameter name or value, or
                              missing/unknown namespace prefix)
    TOT_ERR_NOT_INIT    = 2  (tot_init has not been called yet)
    TOT_ERR_CALC_FAILED = 3  (per-module init / calculation failed)
    TOT_ERR_NOT_IMPL    = 4  (entry point is a stub: tot_init / tot_run /
                              tot_get_state / tot_finalize at L-3 scope)

The same hierarchy follows the trlib / eqlib / tilib pattern so test
patterns can be shared. ``raise_for_rc`` (and the alias
``raise_for_ierr``) maps non-zero return codes to the matching subclass.
"""
from __future__ import annotations


class TotlibError(Exception):
    """Base class for all totlib errors."""


class TotlibInitError(TotlibError):
    """Initialization / finalize lifecycle violation."""


class TotlibInvalidParamError(TotlibError):
    """Invalid parameter name or value (rc == 1).

    The most common cause for TOT specifically is forgetting the
    ``<ns>:`` namespace prefix. The tot parameter space is the union
    of six per-module registries (eq, tr, fp, ti, wr, wrx), so callers
    MUST disambiguate with a prefix such as ``"eq:RR"``, ``"tr:DT"``,
    ``"fp:NSMAX"``, ``"ti:RR"``, ``"wr:RFIN"``, or ``"wrx:RFIN"``.
    Bare ``"RR"`` is rejected by tot_param_registry.f90.
    """


class TotlibNotInitializedError(TotlibError):
    """Library not initialized (rc == 2)."""


class TotlibCalculationFailedError(TotlibError):
    """tot_run / tot_get_state returned non-zero (rc == 3)."""


class TotlibNotImplementedError(TotlibError):
    """Entry point is a stub and not yet implemented (rc == 4).

    At Phase L-3 / L-4 scope, ``tot_init``, ``tot_run``,
    ``tot_get_state`` and ``tot_finalize`` all return this code; only
    ``tot_set_param`` and ``tot_set_param_str`` are real. L-6+ will
    wire up the per-module fan-out and these stubs will start returning
    ``TOT_OK``.
    """


# Spec-style aliases (kept consistent with eqlib / trlib).
TotLibError = TotlibError
TotLibInvalidParam = TotlibInvalidParamError
TotLibNotInitialized = TotlibNotInitializedError
TotLibCalculationFailed = TotlibCalculationFailedError
TotLibNotImplemented = TotlibNotImplementedError


_CODE_MAP = {
    1: TotlibInvalidParamError,
    2: TotlibNotInitializedError,
    3: TotlibCalculationFailedError,
    4: TotlibNotImplementedError,
}


def raise_for_rc(func: str, rc: int) -> None:
    """Raise the matching subclass when ``rc != 0``.

    Unknown codes fall back to the generic :class:`TotlibError`.
    """
    if rc == 0:
        return
    cls = _CODE_MAP.get(int(rc), TotlibError)
    raise cls(f"{func}: rc={rc}")


# Alias matching the trlib naming.
raise_for_ierr = raise_for_rc


__all__ = [
    "TotlibError",
    "TotlibInitError",
    "TotlibInvalidParamError",
    "TotlibNotInitializedError",
    "TotlibCalculationFailedError",
    "TotlibNotImplementedError",
    "TotLibError",
    "TotLibInvalidParam",
    "TotLibNotInitialized",
    "TotLibCalculationFailed",
    "TotLibNotImplemented",
    "raise_for_rc",
    "raise_for_ierr",
]
