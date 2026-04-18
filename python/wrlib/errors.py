"""Exception hierarchy for wrlib.

Mirrors the ``enum wr_error`` codes declared in ``wr/wr_api.h``:

    WR_OK              = 0
    WR_ERR_INVALID     = 1  (invalid parameter name or value)
    WR_ERR_NOT_INIT    = 2  (wr_init has not been called yet)
    WR_ERR_CALC_FAILED = 3  (calculation / initialization failed)
    WR_ERR_NOT_IMPL    = 4  (L-2 stub return: not implemented)
"""
from __future__ import annotations


class WrlibError(Exception):
    """Base class for all wrlib errors."""


class WrlibInitError(WrlibError):
    """Initialization failed (wr_init returned non-zero)."""


class WrlibParamError(WrlibError):
    """Invalid parameter name or value (ierr == 1)."""


class WrlibStateError(WrlibError):
    """Library not initialized (ierr == 2)."""


class WrlibRunError(WrlibError):
    """Calculation or get_state failed (ierr == 3)."""


class WrlibNotImplementedError(WrlibError):
    """Entry point is a stub and not yet implemented (ierr == 4)."""


# Aliases preferred by some callers / spec drafts.
WrLibError = WrlibError
WrLibInvalidParam = WrlibParamError
WrLibNotInitialized = WrlibStateError
WrLibCalculationFailed = WrlibRunError
WrLibNotImplemented = WrlibNotImplementedError


_CODE_MAP = {
    1: WrlibParamError,
    2: WrlibStateError,
    3: WrlibRunError,
    4: WrlibNotImplementedError,
}


def raise_for_ierr(func: str, ierr: int) -> None:
    """Raise the matching subclass when ``ierr != 0``.

    Unknown codes fall back to the generic :class:`WrlibError`.
    """
    if ierr == 0:
        return
    cls = _CODE_MAP.get(int(ierr), WrlibError)
    raise cls(f"{func}: ierr={ierr}")
