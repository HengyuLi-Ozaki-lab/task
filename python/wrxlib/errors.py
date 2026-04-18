"""Exception hierarchy for wrxlib.

Mirrors the ``enum wrx_error`` codes declared in ``wrx/wrx_api.h``:

    WRX_OK              = 0
    WRX_ERR_INVALID     = 1  (invalid parameter name or value)
    WRX_ERR_NOT_INIT    = 2  (wrx_init has not been called yet)
    WRX_ERR_CALC_FAILED = 3  (calculation / initialization failed)
    WRX_ERR_NOT_IMPL    = 4  (L-2 stub return: not implemented)
"""
from __future__ import annotations


class WrxlibError(Exception):
    """Base class for all wrxlib errors."""


class WrxlibInitError(WrxlibError):
    """Initialization failed (wrx_init returned non-zero)."""


class WrxlibParamError(WrxlibError):
    """Invalid parameter name or value (ierr == 1)."""


class WrxlibStateError(WrxlibError):
    """Library not initialized (ierr == 2)."""


class WrxlibRunError(WrxlibError):
    """Calculation or get_state failed (ierr == 3)."""


class WrxlibNotImplementedError(WrxlibError):
    """Entry point is a stub and not yet implemented (ierr == 4)."""


# Aliases preferred by some callers / spec drafts.
WrxLibError = WrxlibError
WrxLibInvalidParam = WrxlibParamError
WrxLibNotInitialized = WrxlibStateError
WrxLibCalculationFailed = WrxlibRunError
WrxLibNotImplemented = WrxlibNotImplementedError


_CODE_MAP = {
    1: WrxlibParamError,
    2: WrxlibStateError,
    3: WrxlibRunError,
    4: WrxlibNotImplementedError,
}


def raise_for_ierr(func: str, ierr: int) -> None:
    """Raise the matching subclass when ``ierr != 0``.

    Unknown codes fall back to the generic :class:`WrxlibError`.
    """
    if ierr == 0:
        return
    cls = _CODE_MAP.get(int(ierr), WrxlibError)
    raise cls(f"{func}: ierr={ierr}")


# Alias: matches the naming used by some sibling packages (fplib, trlib).
raise_for_rc = raise_for_ierr
