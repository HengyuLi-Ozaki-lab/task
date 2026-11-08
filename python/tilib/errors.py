"""Exception hierarchy for tilib.

Mirrors the ``enum ti_error`` codes declared in ``ti/ti_api.h``:

    TI_OK              = 0
    TI_ERR_INVALID     = 1  (invalid parameter name or value)
    TI_ERR_NOT_INIT    = 2  (ti_init has not been called yet)
    TI_ERR_CALC_FAILED = 3  (calculation / initialization failed)
    TI_ERR_NOT_IMPL    = 4  (L-2 stub return: not implemented)
"""
from __future__ import annotations


class TilibError(Exception):
    """Base class for all tilib errors."""


class TilibInitError(TilibError):
    """Initialization / finalize lifecycle violation."""


class TilibParamError(TilibError):
    """Invalid parameter name or value (ierr == 1)."""


class TilibStateError(TilibError):
    """Library not initialized (ierr == 2)."""


class TilibRunError(TilibError):
    """Calculation or get_state failed (ierr == 3)."""


class TilibNotImplementedError(TilibError):
    """Entry point is a stub and not yet implemented (ierr == 4)."""


# Aliases preferred by some callers / spec drafts.
TiLibError = TilibError
TiLibInvalidParam = TilibParamError
TiLibNotInitialized = TilibStateError
TiLibCalculationFailed = TilibRunError
TiLibNotImplemented = TilibNotImplementedError


_CODE_MAP = {
    1: TilibParamError,
    2: TilibStateError,
    3: TilibRunError,
    4: TilibNotImplementedError,
}


def raise_for_ierr(func: str, ierr: int) -> None:
    """Raise the matching subclass when ``ierr != 0``.

    Unknown codes fall back to the generic :class:`TilibError`.
    """
    if ierr == 0:
        return
    cls = _CODE_MAP.get(int(ierr), TilibError)
    raise cls(f"{func}: ierr={ierr}")


__all__ = [
    "TilibError",
    "TilibInitError",
    "TilibParamError",
    "TilibStateError",
    "TilibRunError",
    "TilibNotImplementedError",
    "TilibAbiError",
    "TiLibError",
    "TiLibInvalidParam",
    "TiLibNotInitialized",
    "TiLibCalculationFailed",
    "TiLibNotImplemented",
    "raise_for_ierr",
]

class TilibAbiError(TilibError):
    """libtiapi.so's ti_state_t layout is not the one this wrapper has (#246).

    Raised by :func:`tilib._ffi.load_library` before any struct is passed:
    the library does not export ``ti_state_abi_version`` / ``ti_state_size``
    (built before the layout check), or its version or sizeof differs from
    ``tilib._ffi.TiStateC``. The message names the fix (rebuild the
    library, or update the wrapper).
    """
