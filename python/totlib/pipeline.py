"""TotPipeline — Python-side scalar coupling orchestrator (L-7a).

Spec: docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md

This module composes existing per-module wrappers (Fplib, Trlib, ...)
to form a multi-step pipeline with hardcoded scalar coupling rules.
It does NOT touch libtotapi.so — that path is handled by the legacy
totlib.Tot class and remains untouched at L-7a.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Union


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
