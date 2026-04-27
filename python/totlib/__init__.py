"""totlib: Python ctypes wrapper around ``tot/libtotapi.so``.

Two-layer package:

* :mod:`totlib._ffi` is a thin ctypes binding that mirrors
  ``tot/tot_api.h`` exactly (``TotStateC`` structure + 6 entry-point
  prototypes).
* :mod:`totlib.totlib` provides the high-level :class:`Tot` context
  manager and :class:`~totlib.state.TotState` dataclass.

TOT is the integrated TASK orchestrator, so its parameter space is the
**union** of the per-module registries. Every parameter name passed
through :py:meth:`Tot.set_param` MUST carry a namespace prefix:
``"eq:RR"``, ``"tr:DT"``, ``"fp:NSMAX"``, ``"ti:RR"``, ``"wr:RFIN"``,
``"wrx:RFIN"`` and so on.

Example::

    from totlib import Tot

    with Tot() as tot:
        tot.set_param("eq:RR", 6.2)
        tot.set_param("tr:DT", 0.01)
        # tot.run(ntmax=10)            # NOT_IMPL until L-6 fan-out
        # state = tot.get_state()      # NOT_IMPL until L-6 fan-out
"""
from .totlib import Tot
from .state import TotState
from .pipeline import (
    TotPipeline,
    CouplingRule,
    PipelineStep,
    PipelineResult,
)
from .errors import (
    TotlibError,
    TotlibInitError,
    TotlibInvalidParamError,
    TotlibNotInitializedError,
    TotlibCalculationFailedError,
    TotlibNotImplementedError,
    TotLibError,
    TotLibInvalidParam,
    TotLibNotInitialized,
    TotLibCalculationFailed,
    TotLibNotImplemented,
    TotPipelineError,
    TotPipelineUnknownModuleError,
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineRunError,
    raise_for_rc,
    raise_for_ierr,
)

__all__ = [
    "Tot",
    "TotState",
    "TotPipeline",
    "CouplingRule",
    "PipelineStep",
    "PipelineResult",
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
    "TotPipelineError",
    "TotPipelineUnknownModuleError",
    "TotPipelineCouplingError",
    "TotPipelineLifecycleError",
    "TotPipelineRunError",
    "raise_for_rc",
    "raise_for_ierr",
]
