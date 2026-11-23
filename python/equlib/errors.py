"""Exceptions of equlib, one per ``enum equ_error`` code of ``equ/equ_api.h``.

    EQU_OK              = 0
    EQU_ERR_INVALID     = 1  invalid name, value, mode or call order
    EQU_ERR_NOT_INIT    = 2  equ_init has not been called
    EQU_ERR_CALC_FAILED = 3  the solve or a file write failed
    EQU_ERR_NOT_IMPL    = 4  equ_run mode above 1

The names follow eqlib's (``EqlibInvalidParamError`` and so on).
"""
from __future__ import annotations


class EqulibError(Exception):
    """Base class of every equlib error."""


class EqulibInitError(EqulibError):
    """A life-cycle violation (a second live ``Equ``; use after close)."""


class EqulibInvalidParamError(EqulibError):
    """rc 1: an invalid name, value, mode, or a call out of order."""


class EqulibNotInitializedError(EqulibError):
    """rc 2: the library is not initialised."""


class EqulibCalculationFailedError(EqulibError):
    """rc 3: the solve or the G-EQDSK write failed."""


class EqulibNotImplementedError(EqulibError):
    """rc 4: a run mode above 1."""


class EqulibAbiError(EqulibError):
    """The library's ``equ_state_t`` layout is not this wrapper's."""


_CODE_MAP = {
    1: EqulibInvalidParamError,
    2: EqulibNotInitializedError,
    3: EqulibCalculationFailedError,
    4: EqulibNotImplementedError,
}


def raise_for_rc(func: str, rc: int, detail: str = "") -> None:
    """Raise the class of ``rc`` (``EqulibError`` for an unknown code)."""
    if rc == 0:
        return
    cls = _CODE_MAP.get(int(rc), EqulibError)
    message = f"{func}: rc={rc}"
    if detail:
        message += f": {detail}"
    raise cls(message)


__all__ = [
    "EqulibError", "EqulibInitError", "EqulibInvalidParamError",
    "EqulibNotInitializedError", "EqulibCalculationFailedError",
    "EqulibNotImplementedError", "EqulibAbiError", "raise_for_rc",
]
