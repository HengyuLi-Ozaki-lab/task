"""wrxlib: Python ctypes wrapper around ``wrx/libwrxapi.so``.

Sister package to :mod:`wrlib`. Two-layer design:

* :mod:`wrxlib._ffi` is a thin ctypes binding that mirrors
  ``wrx/wrx_api.h`` exactly (``WrxStateC`` structure + prototypes).
* :mod:`wrxlib.wrxlib` provides the high-level :class:`Wrxlib` context
  manager and :class:`~wrxlib.state.WrxState` dataclass.

Example::

    from wrxlib import Wrxlib
    with Wrxlib() as wrx:
        wrx.set_params(MODELG=2, RR=6.2, BB=5.3, NSMAX=2)
        wrx.set_param("RFIN[1]", 170.0e3)
        wrx.run(0)
        state = wrx.get_state()
"""
from .wrxlib import Wrxlib
from .state import WrxState
from .errors import (
    WrxlibError,
    WrxlibInitError,
    WrxlibParamError,
    WrxlibStateError,
    WrxlibRunError,
    WrxlibNotImplementedError,
    # Aliases kept for spec-style naming.
    WrxLibError,
    WrxLibInvalidParam,
    WrxLibNotInitialized,
    WrxLibCalculationFailed,
    WrxLibNotImplemented,
    raise_for_ierr,
    raise_for_rc,
)

__all__ = [
    "Wrxlib",
    "WrxState",
    "WrxlibError",
    "WrxlibInitError",
    "WrxlibParamError",
    "WrxlibStateError",
    "WrxlibRunError",
    "WrxlibNotImplementedError",
    "WrxLibError",
    "WrxLibInvalidParam",
    "WrxLibNotInitialized",
    "WrxLibCalculationFailed",
    "WrxLibNotImplemented",
    "raise_for_ierr",
    "raise_for_rc",
]
