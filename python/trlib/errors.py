"""Exception hierarchy for trlib.

Mirrors the ``enum tr_error`` codes declared in ``tr/tr_api.h``:

    TR_OK              = 0
    TR_ERR_INVALID     = 1  (invalid parameter name or value)
    TR_ERR_NOT_INIT    = 2  (tr_init has not been called yet)
    TR_ERR_CALC_FAILED = 3  (calculation / initialization failed)
    TR_ERR_NOT_IMPL    = 4  (L-2 stub return: not implemented)
"""
from __future__ import annotations


class TrlibError(Exception):
    """Base class for all trlib errors."""


class TrlibInitError(TrlibError):
    """Initialization failed (tr_init returned non-zero)."""


class TrlibParamError(TrlibError):
    """Invalid parameter name or value (ierr == 1)."""


class TrlibStateError(TrlibError):
    """Library not initialized (ierr == 2)."""


class TrlibRunError(TrlibError):
    """Calculation or get_state failed (ierr == 3)."""


class TrlibNotImplementedError(TrlibError):
    """Entry point is a stub and not yet implemented (ierr == 4)."""


# Aliases preferred by some callers / spec drafts.
TrLibError = TrlibError
TrLibInvalidParam = TrlibParamError
TrLibNotInitialized = TrlibStateError
TrLibCalculationFailed = TrlibRunError
TrLibNotImplemented = TrlibNotImplementedError


_CODE_MAP = {
    1: TrlibParamError,
    2: TrlibStateError,
    3: TrlibRunError,
    4: TrlibNotImplementedError,
}


def raise_for_ierr(func: str, ierr: int) -> None:
    """Raise the matching subclass when ``ierr != 0``.

    Unknown codes fall back to the generic :class:`TrlibError`.
    """
    if ierr == 0:
        return
    cls = _CODE_MAP.get(int(ierr), TrlibError)
    raise cls(f"{func}: ierr={ierr}")
