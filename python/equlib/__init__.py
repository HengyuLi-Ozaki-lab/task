"""equlib: Python interface to TASK/EQU, the free-boundary equilibrium code.

The wrapper of ``equ/libequapi.so`` (design:
``docs/superpowers/specs/2026-11-22-equ-library-design.md``). See README.md.
"""
from .equlib import Equ, EquDiag
from .errors import (
    EqulibAbiError, EqulibCalculationFailedError, EqulibError, EqulibInitError,
    EqulibInvalidParamError, EqulibNotImplementedError, EqulibNotInitializedError,
)
from .state import EquState

__all__ = [
    "Equ", "EquDiag", "EquState", "EqulibError", "EqulibInitError",
    "EqulibInvalidParamError", "EqulibNotInitializedError",
    "EqulibCalculationFailedError", "EqulibNotImplementedError", "EqulibAbiError",
]
