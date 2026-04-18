"""wrlib: Python ctypes wrapper around ``wr/libwrapi.so``.

Two-layer package:

* :mod:`wrlib._ffi` is a thin ctypes binding that mirrors
  ``wr/wr_api.h`` exactly (``WrStateC`` structure + prototypes).
* :mod:`wrlib.wrlib` provides the high-level :class:`Wrlib` context
  manager and :class:`~wrlib.state.WrState` dataclass.

Example::

    from wrlib import Wrlib
    with Wrlib() as wr:
        wr.run(0)
        state = wr.get_state()
"""
from .wrlib import Wrlib
from .state import WrState
from .errors import (
    WrlibError,
    WrlibInitError,
    WrlibParamError,
    WrlibStateError,
    WrlibRunError,
    WrlibNotImplementedError,
    # Aliases kept for spec-style naming.
    WrLibError,
    WrLibInvalidParam,
    WrLibNotInitialized,
    WrLibCalculationFailed,
    WrLibNotImplemented,
    raise_for_ierr,
)

__all__ = [
    "Wrlib",
    "WrState",
    "WrlibError",
    "WrlibInitError",
    "WrlibParamError",
    "WrlibStateError",
    "WrlibRunError",
    "WrlibNotImplementedError",
    "WrLibError",
    "WrLibInvalidParam",
    "WrLibNotInitialized",
    "WrLibCalculationFailed",
    "WrLibNotImplemented",
    "raise_for_ierr",
]
