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
    TotPipelineRunError,
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


def _state_to_scalars(state) -> Dict[str, float]:
    """Extract a flat dict of numeric scalars from any module's state.

    Modules that expose state.scalars dict (Tr, Eq, Wr, Wrx, Ti) — return
    a shallow copy. Modules that don't (Fp) — extract numeric top-level
    dataclass attributes (excluding bool, str, and non-numeric).

    Per spec §5.3. Required because FpState lacks the uniform .scalars
    dict the spec originally assumed (R1/R2 finding).
    """
    if hasattr(state, "scalars") and isinstance(state.scalars, dict):
        return dict(state.scalars)
    out: Dict[str, float] = {}
    for name in dir(state):
        if name.startswith("_"):
            continue
        val = getattr(state, name, None)
        if callable(val):
            continue
        if isinstance(val, bool):
            continue
        if isinstance(val, (int, float)):
            out[name] = float(val)
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


# ------------------------------------------------------------------
# Coupling rule registry
# ------------------------------------------------------------------
# L-7a scope: only ('fp','tr') is populated. Concrete src_state_key,
# dst_param, transform are filled in Phase 2 (Equivalence test PR)
# after R2/R3 outcomes are recorded in the spec.
# L-7b will add more pairs (('wr','fp'), ('wr','tr'), ('eq','tr'), ...)
# without changing the orchestrator code.

COUPLING_RULES: Dict[Tuple[str, str], List[CouplingRule]] = {
    # ("fp", "tr"): [...]    ← Phase 2 fills this
}


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

        Note: only fp/tr/eq currently expose set_param_str; wr/wrx/ti
        accept numeric params only. Passing a string value to one of
        those raises TotPipelineCouplingError (rather than a bare
        AttributeError leaking out of getattr).

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
            setter = getattr(module, "set_param_str", None)
            if setter is None:
                raise TotPipelineCouplingError(
                    f"module {ns!r} does not accept string parameters "
                    f"(set_param_str not defined); got {namespaced!r}={value!r}"
                )
            setter(bare, value)
            self._params[namespaced] = value
        else:
            # Store the coerced value so coupling rules reading self._params
            # see the same scalar the wrapper actually received (e.g. True is
            # forwarded as 1.0, so 1.0 is what _params should hold).
            coerced = float(value)
            module.set_param(bare, coerced)
            self._params[namespaced] = coerced

    def close(self) -> None:
        """Finalize all opened module wrappers. Idempotent. If any close
        raises, all remaining modules are still finalized; on a single
        failure the original exception is re-raised, on multiple failures
        an ExceptionGroup carrying every collected error is raised so no
        cleanup failure is silently dropped."""
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
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise ExceptionGroup(
                f"{len(errors)} module(s) failed to close", errors
            )

    @staticmethod
    def _validate_steps(steps) -> None:
        """Pre-flight: reject malformed steps before any side effects."""
        if not steps:
            raise TotPipelineCouplingError("steps must be non-empty")
        for i, item in enumerate(steps):
            if not isinstance(item, tuple) or len(item) != 2:
                raise TotPipelineCouplingError(
                    f"steps[{i}] must be (module_name, kwargs) tuple, got {item!r}"
                )
            name, kwargs = item
            if name not in _MODULE_REGISTRY:
                raise TotPipelineUnknownModuleError(
                    f"steps[{i}].module = {name!r}; expected one of "
                    f"{sorted(_MODULE_REGISTRY)}"
                )
            if not isinstance(kwargs, dict):
                raise TotPipelineCouplingError(
                    f"steps[{i}].kwargs must be dict, got {type(kwargs).__name__}"
                )

    def _extract_source(self, prev_state, rule: CouplingRule) -> float:
        """Resolve a rule's source value from the previous module's state.

        - If src_state_key is a callable, invoke it with (prev_state, self._params).
          The params dict carries every set_param call so the rule can pull
          cross-module context (e.g. fp's compute_rjt_volint needs tr's RR/RA).
        - If src_state_key is a string, look it up in
          _state_to_scalars(prev_state) — handles both .scalars-bearing modules
          and FpState's top-level attribute layout.
        Wraps lookup/computation errors as TotPipelineCouplingError.
        """
        try:
            if callable(rule.src_state_key):
                return float(rule.src_state_key(prev_state, self._params))
            scalars = _state_to_scalars(prev_state)
            return float(scalars[rule.src_state_key])
        except KeyError as e:
            raise TotPipelineCouplingError(
                f"source state key {rule.src_state_key!r} missing from "
                f"prev_state scalars; rule: {rule.doc!r}"
            ) from e
        except Exception as e:
            raise TotPipelineCouplingError(
                f"source extraction failed for rule {rule.doc!r}: {e}"
            ) from e

    def run_pipeline(self, steps) -> PipelineResult:
        """Run the given module steps in order, applying COUPLING_RULES
        between adjacent (prev, current) pairs.

        Returns a PipelineResult. Per-module exceptions during execution
        are wrapped as TotPipelineRunError exposing partial_result.
        """
        if self._closed:
            raise TotPipelineLifecycleError("TotPipeline is closed")
        self._validate_steps(steps)

        result_steps: List[PipelineStep] = []
        prev_name = None
        prev_state = None

        for i, (name, kwargs) in enumerate(steps):
            # The catch below is broad on purpose: any Exception during step
            # execution (per-module domain error, TypeError from bad kwargs,
            # etc.) is wrapped as TotPipelineRunError so partial_result is
            # always available to the caller. Keyboard/system signals are NOT
            # caught.
            try:
                module = self._ensure_module(name)
                applied: List[str] = []

                if prev_name is not None:
                    for rule in COUPLING_RULES.get((prev_name, name), []):
                        raw = self._extract_source(prev_state, rule)
                        try:
                            transformed = rule.transform(raw)
                        except Exception as e:
                            raise TotPipelineCouplingError(
                                f"transform failed for rule {rule.doc!r}: {e}"
                            ) from e
                        module.set_param(rule.dst_param, transformed)
                        # Record the injected value so subsequent rules can see it
                        # (mirrors set_param's _params bookkeeping).
                        self._params[f"{name}:{rule.dst_param}"] = transformed
                        applied.append(rule.doc)

                module.run(**kwargs)
                cur_state = module.get_state()
                # _state_to_scalars adapter handles fp (no .scalars) and tr (.scalars dict) uniformly.
                result_steps.append(PipelineStep(
                    module=name,
                    scalars=_state_to_scalars(cur_state),
                    coupling_applied=applied,
                ))
                prev_name, prev_state = name, cur_state
            except Exception as e:  # noqa: BLE001 — see comment above
                raise TotPipelineRunError(
                    f"step {i} ({name}) failed: {e}",
                    partial_result=PipelineResult(steps=result_steps),
                    failed_step_index=i,
                    failed_module=name,
                ) from e

        return PipelineResult(steps=result_steps)
