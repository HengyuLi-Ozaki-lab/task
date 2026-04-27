"""TotPipeline — Python-side scalar coupling orchestrator (L-7a).

Spec: docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md

This module composes existing per-module wrappers (Fplib, Trlib, ...)
to form a multi-step pipeline with hardcoded scalar coupling rules.
It does NOT touch libtotapi.so — that path is handled by the legacy
totlib.Tot class and remains untouched at L-7a.
"""

import importlib

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple, Union

from .errors import (
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineUnknownModuleError,
)


@dataclass(frozen=True)
class CouplingRule:
    """A single source-to-sink scalar coupling between adjacent steps.

    Frozen so the registry can be hashable in the future (rule dedup,
    set-based lookups) and to prevent accidental mutation by callers.

    src_state_key resolves a value from the source module's get_state():

    * str  -> looked up in prev_state.scalars (only valid for modules
      that expose a .scalars dict — Tr/Eq/Wr/Wrx/Ti).
    * callable(prev_state, params) -> float. params is TotPipeline._params,
      a dict of every set_param call so far keyed as "<ns>:<bare>" (used
      by fp's compute_rjt_volint which needs tr's RR/RA).

    dst_param is the bare parameter name on the sink module (set via
    sink.set_param). transform is applied to the source value (e.g. unit
    conversion) before it reaches the sink.
    """

    src_state_key: Union[str, Callable[[Any, Dict[str, Any]], float]]
    dst_param: str
    transform: Callable[[float], float] = lambda v: v
    doc: str = ""


@dataclass
class PipelineStep:
    """Snapshot of one completed pipeline step."""

    module: str
    scalars: Dict[str, float]
    coupling_applied: List[str]


@dataclass
class PipelineResult:
    """Aggregated result from a run_pipeline call."""

    steps: List[PipelineStep] = field(default_factory=list)

    def last(self, module: str) -> PipelineStep:
        """Return the most recent step for the given module name.

        Raises KeyError if the module never ran in this result.
        """
        for step in reversed(self.steps):
            if step.module == module:
                return step
        raise KeyError(module)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable representation for MCP transport.

        For repeated modules, later steps overwrite earlier in the
        flat per-module map; the full timeline is preserved under
        the "_steps" key. Values reference the underlying step.scalars
        dicts directly (no defensive copy) — callers that mutate the
        returned dict will perturb the originating PipelineStep.
        """
        out: Dict[str, Any] = {}
        for step in self.steps:
            out[step.module] = step.scalars  # later steps overwrite earlier
        out["_steps"] = [
            {
                "module": s.module,
                "scalars": s.scalars,
                "coupling_applied": s.coupling_applied,
            }
            for s in self.steps
        ]
        return out


_MODULE_REGISTRY: Dict[str, Tuple[str, str, str]] = {
    # name : (package, wrapper_class, base_error_class)
    "fp":  ("fplib",  "Fplib",  "FplibError"),
    "tr":  ("trlib",  "Trlib",  "TrlibError"),
    "eq":  ("eqlib",  "Eq",     "EqlibError"),
    "wr":  ("wrlib",  "Wrlib",  "WrlibError"),
    "wrx": ("wrxlib", "Wrxlib", "WrxlibError"),
    "ti":  ("tilib",  "TiLib",  "TilibError"),    # NB: wrapper class TiLib (capital L) but TilibError
}


def _import_wrapper(name: str):
    """Lazy-import the per-module wrapper class for `name`.

    Only modules actually used in a pipeline are loaded (matters on
    macOS where wr/wrx may not have buildable lib*.so). Raises
    TotPipelineUnknownModuleError if name is not in _MODULE_REGISTRY.
    """
    if name not in _MODULE_REGISTRY:
        raise TotPipelineUnknownModuleError(
            f"unknown module {name!r}; expected one of {sorted(_MODULE_REGISTRY)}"
        )
    pkg, cls_name, _ = _MODULE_REGISTRY[name]
    return getattr(importlib.import_module(pkg), cls_name)


def _import_module_error(name: str) -> type:
    """Lazy-import the base error class for module `name`.

    Same lazy pattern as _import_wrapper — only the errors.py for the
    requested module is imported. Used by run_pipeline to determine
    which exceptions to catch + wrap as TotPipelineRunError.
    """
    if name not in _MODULE_REGISTRY:
        raise TotPipelineUnknownModuleError(
            f"unknown module {name!r}; expected one of {sorted(_MODULE_REGISTRY)}"
        )
    pkg, _, err_cls_name = _MODULE_REGISTRY[name]
    errors_mod = importlib.import_module(f"{pkg}.errors")
    return getattr(errors_mod, err_cls_name)


class TotPipeline:
    """Python-side multi-module orchestrator with scalar coupling.

    Lazy-instantiates per-module wrappers (Fplib, Trlib, ...) only when
    referenced by set_param or run_pipeline. Coupling between adjacent
    steps follows COUPLING_RULES (populated in Task 1.5 / 2.2).

    Mutually exclusive with the legacy totlib.Tot class — both call
    tr_init internally and same-process coexistence is undefined.
    """

    def __init__(self) -> None:
        self._modules: Dict[str, Any] = {}
        # Track every set_param call, indexed by namespaced key. Used by
        # CouplingRule callables that need cross-module context (e.g. fp's
        # compute_rjt_volint needs tr's RR/RA). Per spec §5.4.
        self._params: Dict[str, Any] = {}
        self._closed: bool = False

    def __enter__(self) -> "TotPipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _ensure_module(self, name: str):
        if self._closed:
            raise TotPipelineLifecycleError("TotPipeline is closed")
        if name not in self._modules:
            cls = _import_wrapper(name)
            self._modules[name] = cls()
        return self._modules[name]

    def set_param(self, namespaced: str, value) -> None:
        """Set a per-module parameter via 'module:name' addressing.

        E.g. set_param('fp:NSAMAX', 2). String values are routed to
        set_param_str on the sink wrapper; numeric values to set_param.
        Records the value into self._params after the wrapper accepts
        it (failed validation in the wrapper keeps _params consistent).
        """
        if self._closed:
            raise TotPipelineLifecycleError("TotPipeline is closed")
        if ":" not in namespaced:
            raise TotPipelineCouplingError(
                f"param name must be prefixed with '<module>:', got {namespaced!r}"
            )
        ns, bare = namespaced.split(":", 1)
        module = self._ensure_module(ns)
        if isinstance(value, str):
            module.set_param_str(bare, value)
        else:
            module.set_param(bare, float(value))
        self._params[namespaced] = value

    def close(self) -> None:
        """Finalize all opened module wrappers. Idempotent. If any close
        raises, all remaining modules are still finalized; the first
        exception is re-raised after the loop."""
        if self._closed:
            return
        errors = []
        for name, module in list(self._modules.items()):
            try:
                module.close()
            except Exception as e:  # noqa: BLE001 — caller wants to see all
                errors.append(e)
        self._modules.clear()
        self._closed = True
        if errors:
            raise errors[0]
