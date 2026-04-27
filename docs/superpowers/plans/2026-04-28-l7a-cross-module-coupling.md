# L-7a Cross-Module Coupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Python-side scalar coupling pipeline (`TotPipeline.run_pipeline`) that orchestrates `fp → tr` driven-current handoff (RJT volume integral → tr's PNBCD scalar), exposed as a new MCP tool `run_pipeline`. The legacy `Tot` class (libtotapi.so wrapper, TR-only) is left untouched.

**Architecture:** New file `python/totlib/pipeline.py` hosts `TotPipeline`, a thin orchestrator that lazily instantiates per-module wrappers (`Fplib`, `Trlib`, ...) and applies hardcoded `COUPLING_RULES` between adjacent steps. No Fortran ABI changes. Profile/coordinate transforms (rho ↔ psi) deferred to L-7b via BPSD broker.

**Tech Stack:** Python 3.11+, ctypes (per-module wrappers already use it), pytest with `--forked --timeout=120 --timeout-method=signal`, FastMCP (existing tot_mcp pattern).

**Spec:** `docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md` (commit 0a12bd07)

**Phases (each is a separate PR per spec §10.7):**
- Phase 0: Pre-flight Research R1/R2/R3 (no code; spec update + commit only)
- Phase 1 (PR 1, Foundation): `TotPipeline` class + errors + mock-based unit tests
- Phase 2 (PR 2, Equivalence test): fp/tr 1e-10 tolerance verification
- Phase 3 (PR 3, MCP integration): `run_pipeline` tool + docs

Each PR independently builds on the previous and ends with the **CLAUDE.md pre-push gate** (`feature-dev:code-reviewer` + `codex:codex-rescue` review + `REVIEW_OK_<sha>` marker + `pytest --forked --timeout=120 --timeout-method=signal`).

---

## Phase 0 — Pre-flight Research

These tasks gate all implementation. **No code in `python/totlib/pipeline.py` until R1/R2/R3 outcomes are recorded in the spec's "Research outcomes" section.**

### Task R1: Singleton coexistence + state-leak verification

**Files:**
- Test scratch script: `/tmp/r1_singleton_check.py` (not committed)
- Modify: `docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md` — append outcomes to "Research outcomes" subsection of §8

- [ ] **Step 1: Confirm fp/tr lib*.so are built**

```bash
ls -la fp/libfpapi.so tr/libtrapi.so 2>&1
```

Expected: both files exist. If missing, run `scripts/setup.sh` (per handoff doc §"環境セットアップ"). If still missing on macOS, document the failure and stop — singleton coexistence cannot be verified without the libs.

- [ ] **Step 2: Write R1-a (concurrent live) verification script**

Create `/tmp/r1a_concurrent_live.py`:

```python
"""R1-a: Verify Fplib() and Trlib() can coexist in one process."""
import sys
sys.path.insert(0, "/Users/k-yoshimi/Dropbox/cursor/task/python")

from fplib import Fplib
from trlib import Trlib

# Baseline: fp alone
fp_solo = Fplib()
fp_solo.run(ntmax=1)
fp_solo_scalars = dict(fp_solo.get_state().scalars)
fp_solo.close()

# Baseline: tr alone
tr_solo = Trlib()
tr_solo.run(ntmax=1)
tr_solo_scalars = dict(tr_solo.get_state().scalars)
tr_solo.close()

# Concurrent: fp + tr both live
fp = Fplib()
tr = Trlib()
fp.run(ntmax=1)
tr.run(ntmax=1)
fp_concurrent_scalars = dict(fp.get_state().scalars)
tr_concurrent_scalars = dict(tr.get_state().scalars)
fp.close()
tr.close()

# Compare
import math
for key in fp_solo_scalars:
    a, b = fp_solo_scalars[key], fp_concurrent_scalars[key]
    if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-15):
        print(f"R1-a FAIL: fp.{key} solo={a} concurrent={b}")
        sys.exit(1)
for key in tr_solo_scalars:
    a, b = tr_solo_scalars[key], tr_concurrent_scalars[key]
    if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-15):
        print(f"R1-a FAIL: tr.{key} solo={a} concurrent={b}")
        sys.exit(1)
print("R1-a PASS: fp/tr concurrent live preserves single-module state at 1e-10")
```

- [ ] **Step 3: Run R1-a under --forked**

Run:
```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 /tmp/r1a_concurrent_live.py
```

Capture stdout. Expected: `R1-a PASS` line. If FAIL or exception, record exact error output for the spec.

- [ ] **Step 4: Write R1-b (re-init state-leak) verification script**

Create `/tmp/r1b_reinit_leak.py`:

```python
"""R1-b: Verify Trlib() close + reopen with same params yields same state."""
import sys, math
sys.path.insert(0, "/Users/k-yoshimi/Dropbox/cursor/task/python")
from trlib import Trlib

# Use a parameter set that the existing trlib tests exercise (small device).
# These values are illustrative — adjust to match an existing fixture if R1
# fails on minimum-input grounds; record the chosen fixture in the spec.
PARAMS_A = {"RR": 6.2, "RA": 2.0, "BB": 5.3, "RIP": 15.0, "MODELG": 2}
PARAMS_B = {"RR": 1.7, "RA": 0.5, "BB": 1.0, "RIP": 0.5, "MODELG": 2}

def run_one(params):
    tr = Trlib()
    for k, v in params.items():
        tr.set_param(k, v)
    tr.run(ntmax=1)
    state = dict(tr.get_state().scalars)
    tr.close()
    return state

state1 = run_one(PARAMS_A)        # cycle 1
state2 = run_one(PARAMS_B)        # cycle 2 — different params
state3 = run_one(PARAMS_A)        # cycle 3 — back to cycle 1's params

leak_keys = []
for key in state1:
    a, b = state1[key], state3[key]
    if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-15):
        leak_keys.append((key, a, b))

if leak_keys:
    print(f"R1-b FAIL: {len(leak_keys)} scalar(s) leaked across re-init:")
    for key, a, b in leak_keys:
        print(f"  {key}: cycle1={a} cycle3={b}")
    sys.exit(1)
print("R1-b PASS: tr re-init is clean (cycle1 == cycle3 at 1e-10)")
```

- [ ] **Step 5: Run R1-b**

Run:
```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 /tmp/r1b_reinit_leak.py
```

Capture stdout. Expected: `R1-b PASS` or detailed FAIL with leaked scalars.

- [ ] **Step 6: Record outcomes in the spec**

Use the Edit tool on `docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md`. Replace the line `- R1 結果: __未確定__` with one of:

If both PASS:
```markdown
- R1 結果: PASS (R1-a + R1-b 両方). Fplib/Trlib は同時 live 可能, かつ close→再 open で state がリークしない. Fallback A/B どちらも適用不要.
```

If R1-a FAIL:
```markdown
- R1 結果: R1-a FAIL. <err message>. Fallback A 採用 — TotPipeline._ensure_module で「他 module open 中なら一旦 close → 自 module を open」の dance を実装. パフォーマンス劣化容認.
```

If R1-b FAIL:
```markdown
- R1 結果: R1-a PASS / R1-b FAIL. リーク scalars: <list>. Fallback B 採用 — README で「`tot.close()` → 新 `TotPipeline()` を毎回作成」を強く推奨. MCP 側は既に force-close pattern で隔離済.
```

- [ ] **Step 7: Commit (R1 done, R2/R3 still pending)**

```bash
git add docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md
git commit -m "docs(spec): record L-7a R1 (singleton coexistence) outcome

R1-a (concurrent live) and R1-b (re-init state leak) verified per
the L-7a design spec. Outcome and fallback decision recorded.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task R2: rjt_volint extraction

**Files:**
- Inspect: `python/fplib/state.py`, `python/fplib/fplib.py`
- Test scratch script: `/tmp/r2_rjt_extraction.py` (not committed)
- Modify: spec "Research outcomes" subsection of §8

- [ ] **Step 1: Locate FpState's RJT and grid layout**

Run:
```bash
grep -n -E "(RJT|RG|nrmax|volume|grid)" /Users/k-yoshimi/Dropbox/cursor/task/python/fplib/state.py | head -30
```

Note: shape of `RJT`, presence of any volume-element array (e.g. `RG`, `DV`, `VOLP`), and any pre-aggregated scalar.

- [ ] **Step 2: Write extraction prototype**

Create `/tmp/r2_rjt_extraction.py`:

```python
"""R2: Determine how to compute RJT volume integral as a scalar."""
import sys
sys.path.insert(0, "/Users/k-yoshimi/Dropbox/cursor/task/python")
from fplib import Fplib

fp = Fplib()
fp.run(ntmax=1)
state = fp.get_state()

# Inspect what's available
print("FpState fields:", [a for a in dir(state) if not a.startswith("_")])
print("scalars keys:", list(state.scalars.keys()) if hasattr(state, "scalars") else "N/A")

# Probe RJT
rjt = getattr(state, "RJT", None)
if rjt is None:
    print("ERROR: state.RJT not found"); sys.exit(1)
print(f"RJT shape: len={len(rjt)} type={type(rjt[0]).__name__}")
print(f"RJT sample: {rjt[:3]} ...")

# Probe grid info needed for volume integral
for attr in ("RG", "DV", "VOLP", "nrmax"):
    val = getattr(state, attr, None)
    if val is not None:
        print(f"state.{attr}: {val if not hasattr(val, '__len__') else f'len={len(val)} sample={list(val)[:3]}'}")

fp.close()
```

- [ ] **Step 3: Run R2 probe**

Run:
```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 /tmp/r2_rjt_extraction.py
```

Capture full stdout to inform the helper implementation.

- [ ] **Step 4: Write the helper using observed state shape**

Based on the probe output, draft `compute_rjt_volint(state) -> float` that returns the RJT volume integral in **Amperes (A)**. Typical form (adjust to actual state attrs):

```python
def compute_rjt_volint(state) -> float:
    """fp's driven current as a scalar [A]: ∫ RJT(rho) dV.

    For uniform-rho grid: V_total = sum(RJT[i] * dV[i])
    where dV[i] is the volume element of cell i.

    Concrete implementation depends on what fp's state exposes —
    if state.VOLP exists use it; otherwise compute from RG (rho grid)
    and a torus volume formula 2π² * R0 * a² * rho * d_rho.
    """
    rjt = state.RJT
    # ... R2 outcome will determine the right form
```

- [ ] **Step 5: Validate against fp's documented total current**

If fp exposes any "total driven current" or "AJT_driven" scalar, sanity-check that `compute_rjt_volint(state) ≈ that scalar` at 1e-6 tolerance. If no comparison anchor exists, manually verify the output is in the right order of magnitude (~MA for ITER-scale, ~kA for small device).

- [ ] **Step 6: Record R2 outcome in the spec**

Edit spec §8 "Research outcomes":

```markdown
- R2 結果: `compute_rjt_volint(state)` is a Python helper in `python/totlib/pipeline.py`.
  Implementation:
  <paste the finalized function body>
  Returns Amperes. Sanity-check vs <scalar/anchor>: within X% relative.
  fplib に変更なし.
```

- [ ] **Step 7: Commit**

```bash
git add docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md
git commit -m "docs(spec): record L-7a R2 (rjt_volint extraction) outcome

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task R3: tr driven current param confirmation

**Files:**
- Inspect: `tr/tr_param_registry.f90`, `tr/trcomm_param.f90`, `tr/trinit.f90`
- Modify: spec "Research outcomes" subsection of §8

- [ ] **Step 1: Find the registered tr param**

Run:
```bash
grep -nE "(PNBCD|PNB|PNBI|PRFCD|PCD|drive)" /Users/k-yoshimi/Dropbox/cursor/task/tr/tr_param_registry.f90
```

Note the exact param name(s) registered for **scalar driven current** input.

- [ ] **Step 2: Inspect default and unit**

Find the param's declaration to determine units:

```bash
grep -nE "PNBCD" /Users/k-yoshimi/Dropbox/cursor/task/tr/trcomm_param.f90 \
                /Users/k-yoshimi/Dropbox/cursor/task/tr/trinit.f90 2>/dev/null
```

Check the F90 namelist comment / variable declaration for whether the value is in **A** or **MA** (typical for plasma codes is MA).

- [ ] **Step 3: Verify the param works via Python**

Quick scratch test to confirm:

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -c "
import sys; sys.path.insert(0, 'python')
from trlib import Trlib
tr = Trlib()
tr.set_param('PNBCD', 1.0)   # ← actual param name from step 1
tr.run(ntmax=1)
s = tr.get_state().scalars
print('AJT after PNBCD=1.0:', s.get('AJT'))
tr.close()
"
```

Expected: no exception. If `set_param` raises `TrlibParamError`, the param name is wrong — go back to step 1 and re-grep.

- [ ] **Step 4: Determine the transform factor**

Based on units found in step 2:
- If tr's param is in **MA** and `compute_rjt_volint` returns A: `transform = lambda v: v * 1e-6`
- If tr's param is in **A** and helper returns A: `transform = lambda v: v` (identity)
- If reversed: invert.

- [ ] **Step 5: Record R3 outcome in the spec**

Edit spec §8 "Research outcomes":

```markdown
- R3 結果: tr param 名 = `PNBCD` (or whatever step 1 confirmed).
  単位 = <A | MA>. Transform: `lambda v: v * <factor>` (注: fp output A → tr <unit>).
  確認方法: tr/tr_param_registry.f90:<line>, tr/trinit.f90:<line>.
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md
git commit -m "docs(spec): record L-7a R3 (tr driven current param) outcome

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task R4: Decision gate — proceed or revise spec

- [ ] **Step 1: Review all three outcomes**

Read the updated "Research outcomes" subsection. Is each gate green?
- R1: PASS or fallback strategy decided
- R2: helper code drafted and outputs sane magnitude
- R3: param name + unit + transform factor confirmed

- [ ] **Step 2: If any blocking failure, escalate**

If R3 fails (no scalar driven-current input on tr exists), the L-7a coupling pair must change. Stop, return to brainstorming, do not proceed to Phase 1. Update the spec to reflect the new pair (likely `wr → tr` PRFCD).

If R1-a + R1-b both fail, the singleton design is not viable. Stop, return to brainstorming, propose Fortran handle-based refactor (out of L-7a scope).

- [ ] **Step 3: If green, proceed to Phase 1**

Announce "Phase 0 (R1/R2/R3) complete; proceeding to Phase 1: Foundation".

---

## Phase 1 — Foundation (PR 1)

Adds `TotPipeline` class skeleton + new errors + mock-based unit tests. No `lib*.so` required to run these tests, so this PR can pass CI on any platform.

### Task 1.1: Add `TotPipeline*` errors

**Files:**
- Modify: `python/totlib/errors.py`
- Modify: `python/totlib/__init__.py`
- Test: `python/totlib/tests/test_pipeline_errors.py` (new)

- [ ] **Step 1: Write failing test**

Create `python/totlib/tests/test_pipeline_errors.py`:

```python
"""Verify the TotPipeline error hierarchy is wired correctly."""
import pytest
from totlib.errors import (
    TotlibError,
    TotPipelineError,
    TotPipelineUnknownModuleError,
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineRunError,
)


def test_tot_pipeline_error_inherits_totlib_error():
    assert issubclass(TotPipelineError, TotlibError)


@pytest.mark.parametrize("cls", [
    TotPipelineUnknownModuleError,
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineRunError,
])
def test_subclasses_inherit_pipeline_error(cls):
    assert issubclass(cls, TotPipelineError)


def test_run_error_carries_partial_result():
    sentinel = object()
    err = TotPipelineRunError(
        "boom",
        partial_result=sentinel,
        failed_step_index=1,
        failed_module="fp",
    )
    assert err.partial_result is sentinel
    assert err.failed_step_index == 1
    assert err.failed_module == "fp"
    assert "boom" in str(err)
```

- [ ] **Step 2: Run test to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_errors.py -v 2>&1 | head -20
```

Expected: ImportError on `TotPipelineError` (because not yet defined in totlib.errors).

- [ ] **Step 3: Implement the error classes**

Edit `python/totlib/errors.py`. Append at end of file:

```python
class TotPipelineError(TotlibError):
    """Base for TotPipeline-specific errors. Inherits TotlibError so existing
    `except TotlibError` callers continue to catch pipeline errors too."""


class TotPipelineUnknownModuleError(TotPipelineError):
    """A run_pipeline step references a module name not in _MODULE_REGISTRY."""


class TotPipelineCouplingError(TotPipelineError):
    """Coupling rule application failed (source key missing, transform raised,
    or pre-flight step validation failed). Original exception is on __cause__."""


class TotPipelineLifecycleError(TotPipelineError):
    """Operation attempted on a closed TotPipeline instance."""


class TotPipelineRunError(TotPipelineError):
    """Per-module exception during run_pipeline execution. Wraps the original
    error (on __cause__) and exposes the partial result up to the failure point.

    Attributes:
        partial_result: PipelineResult with steps completed before the failure.
        failed_step_index: Index in the steps list where the failure occurred.
        failed_module: Module name of the failed step.
    """

    def __init__(self, message, partial_result, failed_step_index, failed_module):
        super().__init__(message)
        self.partial_result = partial_result
        self.failed_step_index = failed_step_index
        self.failed_module = failed_module
```

- [ ] **Step 4: Update `__init__.py` exports**

Edit `python/totlib/__init__.py`. Find the `from .errors import (` block and append the five new names. Add them to `__all__` too.

```python
from .errors import (
    TotlibError,
    TotlibInitError,
    TotlibInvalidParamError,
    TotlibNotInitializedError,
    TotlibCalculationFailedError,
    TotlibNotImplementedError,
    TotPipelineError,
    TotPipelineUnknownModuleError,
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineRunError,
)
```

(Update `__all__` at the bottom to include the same five names.)

- [ ] **Step 5: Run test to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_errors.py -v 2>&1 | head -20
```

Expected: 6 passed (test_tot_pipeline_error_inherits_totlib_error, 4× parametrized, test_run_error_carries_partial_result).

- [ ] **Step 6: Commit**

```bash
git add python/totlib/errors.py python/totlib/__init__.py python/totlib/tests/test_pipeline_errors.py
git commit -m "feat(totlib): add TotPipeline error hierarchy

Five new exception classes for the L-7a pipeline:
- TotPipelineError (base, extends TotlibError)
- TotPipelineUnknownModuleError, TotPipelineCouplingError,
  TotPipelineLifecycleError
- TotPipelineRunError carrying partial_result + failed_step_index +
  failed_module attributes for debugging mid-pipeline failures.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.2: Pipeline data classes (`CouplingRule`, `PipelineStep`, `PipelineResult`)

**Files:**
- Create: `python/totlib/pipeline.py`
- Test: `python/totlib/tests/test_pipeline_dataclasses.py` (new)

- [ ] **Step 1: Write failing test**

Create `python/totlib/tests/test_pipeline_dataclasses.py`:

```python
"""Unit tests for pipeline.py data classes."""
import pytest
from totlib.pipeline import CouplingRule, PipelineStep, PipelineResult


def test_coupling_rule_defaults():
    r = CouplingRule(src_state_key="x", dst_param="Y")
    assert r.transform(3.0) == 3.0    # default identity
    assert r.doc == ""


def test_coupling_rule_with_transform():
    r = CouplingRule(
        src_state_key="x",
        dst_param="Y",
        transform=lambda v: v * 2,
        doc="double it",
    )
    assert r.transform(2.0) == 4.0
    assert r.doc == "double it"


def test_pipeline_step_holds_scalars_and_coupling():
    s = PipelineStep(module="fp", scalars={"a": 1.0}, coupling_applied=["doc1"])
    assert s.module == "fp"
    assert s.scalars == {"a": 1.0}
    assert s.coupling_applied == ["doc1"]


def test_pipeline_result_last():
    s1 = PipelineStep("fp", {"a": 1.0}, [])
    s2 = PipelineStep("tr", {"b": 2.0}, ["fp->tr"])
    r = PipelineResult(steps=[s1, s2])
    assert r.last("fp") is s1
    assert r.last("tr") is s2


def test_pipeline_result_last_returns_most_recent_for_repeated_module():
    """When the same module appears twice, last() returns the latest step."""
    s1 = PipelineStep("fp", {"a": 1.0}, [])
    s2 = PipelineStep("tr", {"b": 2.0}, [])
    s3 = PipelineStep("fp", {"a": 99.0}, [])
    r = PipelineResult(steps=[s1, s2, s3])
    assert r.last("fp") is s3


def test_pipeline_result_last_raises_keyerror():
    r = PipelineResult(steps=[PipelineStep("fp", {}, [])])
    with pytest.raises(KeyError):
        r.last("nope")


def test_pipeline_result_to_dict_flattens():
    r = PipelineResult(steps=[
        PipelineStep("fp", {"a": 1.0}, []),
        PipelineStep("tr", {"b": 2.0}, ["fp RJT -> tr PNBCD"]),
    ])
    d = r.to_dict()
    assert d["fp"] == {"a": 1.0}
    assert d["tr"] == {"b": 2.0}
    assert "_steps" in d
    assert len(d["_steps"]) == 2
    assert d["_steps"][1]["coupling_applied"] == ["fp RJT -> tr PNBCD"]
```

- [ ] **Step 2: Run test to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_dataclasses.py -v 2>&1 | head -10
```

Expected: ModuleNotFoundError on `totlib.pipeline`.

- [ ] **Step 3: Create pipeline.py with data classes**

Create `python/totlib/pipeline.py`:

```python
"""TotPipeline — Python-side scalar coupling orchestrator (L-7a).

Spec: docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md

This module composes existing per-module wrappers (Fplib, Trlib, ...)
to form a multi-step pipeline with hardcoded scalar coupling rules.
It does NOT touch libtotapi.so — that path is handled by the legacy
totlib.Tot class and remains untouched at L-7a.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Union


@dataclass(frozen=True)
class CouplingRule:
    """A single source-to-sink scalar coupling between adjacent steps.

    src_state_key resolves a value from the source module's get_state().
    dst_param is the bare parameter name on the sink module (set via
    sink.set_param). transform is applied to the source value (e.g. unit
    conversion) before it reaches the sink.
    """

    src_state_key: Union[str, Callable[[Any], float]]
    dst_param: str
    transform: Callable[[float], float] = lambda v: v
    doc: str = ""


@dataclass
class PipelineStep:
    """Snapshot of one completed pipeline step."""

    module: str
    scalars: dict[str, float]
    coupling_applied: list[str]


@dataclass
class PipelineResult:
    """Aggregated result from a run_pipeline call."""

    steps: list[PipelineStep] = field(default_factory=list)

    def last(self, module: str) -> PipelineStep:
        """Return the most recent step for the given module name.

        Raises KeyError if the module never ran in this result.
        """
        for step in reversed(self.steps):
            if step.module == module:
                return step
        raise KeyError(module)

    def to_dict(self) -> dict:
        """JSON-serializable representation for MCP transport."""
        out: dict[str, Any] = {}
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
```

- [ ] **Step 4: Run test to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_dataclasses.py -v 2>&1 | head -20
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add python/totlib/pipeline.py python/totlib/tests/test_pipeline_dataclasses.py
git commit -m "feat(totlib): add CouplingRule/PipelineStep/PipelineResult dataclasses

Pure data carriers for the run_pipeline orchestrator. CouplingRule is
frozen (immutable) so the registry can be hashable in the future.
PipelineResult.last(module) returns the most recent matching step,
to_dict() is the MCP serialization format.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.3: Module registry + lazy import helpers

**Files:**
- Modify: `python/totlib/pipeline.py`
- Test: `python/totlib/tests/test_pipeline_registry.py` (new)

- [ ] **Step 1: Write failing test**

Create `python/totlib/tests/test_pipeline_registry.py`:

```python
"""Test _MODULE_REGISTRY and lazy resolvers."""
import pytest
from totlib.pipeline import (
    _MODULE_REGISTRY,
    _import_wrapper,
    _import_module_error,
)
from totlib.errors import TotPipelineUnknownModuleError


def test_registry_has_all_six_modules():
    assert set(_MODULE_REGISTRY) == {"fp", "tr", "eq", "wr", "wrx", "ti"}


def test_registry_entries_have_three_fields():
    for name, entry in _MODULE_REGISTRY.items():
        assert len(entry) == 3, f"{name}: {entry}"
        pkg, cls, err = entry
        assert pkg.endswith("lib"), f"{name}: pkg={pkg}"
        assert err.endswith("Error"), f"{name}: err={err}"


def test_import_wrapper_unknown_raises():
    with pytest.raises(TotPipelineUnknownModuleError) as exc_info:
        _import_wrapper("nope")
    assert "nope" in str(exc_info.value)


def test_import_module_error_unknown_raises():
    with pytest.raises(TotPipelineUnknownModuleError):
        _import_module_error("nope")


def test_import_wrapper_returns_class_for_fp():
    """fp's wrapper class should be importable (does not require libfpapi.so;
    only the class object is returned, not an instance)."""
    cls = _import_wrapper("fp")
    assert cls.__name__ == "Fplib"


def test_import_module_error_returns_class_for_fp():
    err_cls = _import_module_error("fp")
    assert err_cls.__name__ == "FplibError"
    assert issubclass(err_cls, Exception)
```

- [ ] **Step 2: Run test to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_registry.py -v 2>&1 | head -10
```

Expected: ImportError on `_MODULE_REGISTRY` from totlib.pipeline.

- [ ] **Step 3: Add registry + helpers to pipeline.py**

Edit `python/totlib/pipeline.py`. Add at the top (after the `from __future__ import` line):

```python
import importlib

from .errors import (
    TotPipelineUnknownModuleError,
)
```

Then below the dataclasses (after `PipelineResult`), append:

```python
_MODULE_REGISTRY: dict[str, tuple[str, str, str]] = {
    # name : (package, wrapper_class, base_error_class)
    "fp":  ("fplib",  "Fplib",  "FplibError"),
    "tr":  ("trlib",  "Trlib",  "TrlibError"),
    "eq":  ("eqlib",  "Eq",     "EqlibError"),
    "wr":  ("wrlib",  "Wrlib",  "WrlibError"),
    "wrx": ("wrxlib", "Wrxlib", "WrxlibError"),
    "ti":  ("tilib",  "Tilib",  "TilibError"),
}


def _import_wrapper(name: str):
    """Lazy-import the per-module wrapper class for `name`.

    Only modules actually used in a pipeline are loaded. Raises
    TotPipelineUnknownModuleError if name is not in _MODULE_REGISTRY.
    """
    if name not in _MODULE_REGISTRY:
        raise TotPipelineUnknownModuleError(
            f"unknown module {name!r}; expected one of {sorted(_MODULE_REGISTRY)}"
        )
    pkg, cls_name, _ = _MODULE_REGISTRY[name]
    return getattr(importlib.import_module(pkg), cls_name)


def _import_module_error(name: str) -> type[Exception]:
    """Lazy-import the base error class for module `name`.

    Same lazy pattern as _import_wrapper — only the errors.py for the
    requested module is imported.
    """
    if name not in _MODULE_REGISTRY:
        raise TotPipelineUnknownModuleError(
            f"unknown module {name!r}; expected one of {sorted(_MODULE_REGISTRY)}"
        )
    pkg, _, err_cls_name = _MODULE_REGISTRY[name]
    errors_mod = importlib.import_module(f"{pkg}.errors")
    return getattr(errors_mod, err_cls_name)
```

- [ ] **Step 4: Run test to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_registry.py -v 2>&1 | head -20
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add python/totlib/pipeline.py python/totlib/tests/test_pipeline_registry.py
git commit -m "feat(totlib): add module registry + lazy import helpers

_MODULE_REGISTRY maps short names (fp/tr/eq/wr/wrx/ti) to
(package, wrapper_class, base_error_class) triples.
_import_wrapper / _import_module_error keep the lazy-load contract
from spec section 5.5: only modules used in the current pipeline
get their lib*.so / errors.py loaded.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.4: TotPipeline class — init, set_param, lifecycle

**Files:**
- Modify: `python/totlib/pipeline.py`
- Test: `python/totlib/tests/test_pipeline.py` (new — extended in subsequent tasks)

- [ ] **Step 1: Write failing tests for init/set_param/close**

Create `python/totlib/tests/test_pipeline.py`:

```python
"""Unit tests for TotPipeline — mock-based, no lib*.so required."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from totlib.errors import (
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineUnknownModuleError,
)
from totlib.pipeline import TotPipeline


@pytest.fixture
def patch_wrappers(monkeypatch):
    """Replace _import_wrapper / _import_module_error with mocks.

    The returned dict allows tests to inspect which wrappers were
    requested, capture set_param/run/get_state calls, and inject errors.
    """
    fp_mock_class = MagicMock(name="FplibClass")
    tr_mock_class = MagicMock(name="TrlibClass")
    fp_err_class = type("FplibError", (Exception,), {})
    tr_err_class = type("TrlibError", (Exception,), {})

    classes = {"fp": fp_mock_class, "tr": tr_mock_class}
    err_classes = {"fp": fp_err_class, "tr": tr_err_class}

    def fake_import_wrapper(name):
        if name not in classes:
            raise TotPipelineUnknownModuleError(name)
        return classes[name]

    def fake_import_module_error(name):
        if name not in err_classes:
            raise TotPipelineUnknownModuleError(name)
        return err_classes[name]

    monkeypatch.setattr("totlib.pipeline._import_wrapper", fake_import_wrapper)
    monkeypatch.setattr("totlib.pipeline._import_module_error", fake_import_module_error)

    # Each instance is fresh — track via .return_value
    return {"classes": classes, "errors": err_classes}


def test_init_does_not_open_anything(patch_wrappers):
    pipe = TotPipeline()
    assert pipe._modules == {}
    assert pipe._closed is False
    # No wrapper class was instantiated
    patch_wrappers["classes"]["fp"].assert_not_called()
    patch_wrappers["classes"]["tr"].assert_not_called()


def test_set_param_lazy_opens_target_module_only(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("fp:NSAMAX", 2)
    # fp is opened
    patch_wrappers["classes"]["fp"].assert_called_once()
    # tr is NOT opened
    patch_wrappers["classes"]["tr"].assert_not_called()
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.set_param.assert_called_once_with("NSAMAX", 2.0)


def test_set_param_string_routes_to_set_param_str(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("tr:KNAMEQ", "/path/to/eqdsk")
    tr_inst = patch_wrappers["classes"]["tr"].return_value
    tr_inst.set_param_str.assert_called_once_with("KNAMEQ", "/path/to/eqdsk")
    tr_inst.set_param.assert_not_called()


def test_set_param_no_namespace_raises(patch_wrappers):
    pipe = TotPipeline()
    with pytest.raises(TotPipelineCouplingError, match="prefixed"):
        pipe.set_param("nokoron", 1.0)


def test_set_param_unknown_module_raises(patch_wrappers):
    pipe = TotPipeline()
    with pytest.raises(TotPipelineUnknownModuleError):
        pipe.set_param("xx:something", 1.0)


def test_close_finalizes_all_open_modules(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("fp:A", 1.0)
    pipe.set_param("tr:B", 2.0)
    pipe.close()
    patch_wrappers["classes"]["fp"].return_value.close.assert_called_once()
    patch_wrappers["classes"]["tr"].return_value.close.assert_called_once()
    assert pipe._closed is True


def test_close_is_idempotent(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("fp:A", 1.0)
    pipe.close()
    # Second close should not raise and should not re-call close()
    pipe.close()
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.close.assert_called_once()


def test_close_finalizes_remaining_modules_on_error(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("fp:A", 1.0)
    pipe.set_param("tr:B", 2.0)
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    tr_inst = patch_wrappers["classes"]["tr"].return_value
    fp_inst.close.side_effect = RuntimeError("fp boom")
    with pytest.raises(RuntimeError, match="fp boom"):
        pipe.close()
    # tr.close was still called despite fp.close raising
    tr_inst.close.assert_called_once()


def test_set_param_after_close_raises_lifecycle(patch_wrappers):
    pipe = TotPipeline()
    pipe.close()
    with pytest.raises(TotPipelineLifecycleError):
        pipe.set_param("fp:A", 1.0)


def test_context_manager_closes_on_normal_exit(patch_wrappers):
    with TotPipeline() as pipe:
        pipe.set_param("fp:A", 1.0)
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.close.assert_called_once()


def test_context_manager_closes_on_exception(patch_wrappers):
    with pytest.raises(ValueError):
        with TotPipeline() as pipe:
            pipe.set_param("fp:A", 1.0)
            raise ValueError("inner")
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.close.assert_called_once()
```

- [ ] **Step 2: Run test to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline.py -v 2>&1 | head -20
```

Expected: ImportError on `TotPipeline` from totlib.pipeline.

- [ ] **Step 3: Implement TotPipeline (lifecycle subset)**

Edit `python/totlib/pipeline.py`. Append at end of file:

```python
from .errors import (
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
)


class TotPipeline:
    """Python-side multi-module orchestrator with scalar coupling.

    Lazy-instantiates per-module wrappers (Fplib, Trlib, ...) only when
    referenced. Coupling between adjacent steps follows COUPLING_RULES.

    Mutually exclusive with the legacy totlib.Tot class — both call
    tr_init internally and same-process coexistence is undefined.
    """

    def __init__(self) -> None:
        self._modules: dict[str, Any] = {}
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

    def close(self) -> None:
        """Finalize all opened module wrappers. Idempotent. If any close
        raises, all remaining modules are still finalized; the first
        exception is re-raised after the loop."""
        if self._closed:
            return
        errors: list[Exception] = []
        for name, module in list(self._modules.items()):
            try:
                module.close()
            except Exception as e:  # noqa: BLE001 — caller wants to see all
                errors.append(e)
        self._modules.clear()
        self._closed = True
        if errors:
            raise errors[0]
```

- [ ] **Step 4: Run test to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline.py -v 2>&1 | head -40
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add python/totlib/pipeline.py python/totlib/tests/test_pipeline.py
git commit -m "feat(totlib): add TotPipeline lifecycle + set_param

Implements __init__/__enter__/__exit__/_ensure_module/set_param/close.
- Lazy module instantiation: wrappers are created on first use.
- set_param routes strings to set_param_str, numerics to set_param.
- close is idempotent and finalizes all modules even when one raises;
  the first exception is re-raised so the root cause is visible.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.5: COUPLING_RULES + run_pipeline core

**Files:**
- Modify: `python/totlib/pipeline.py`
- Modify: `python/totlib/tests/test_pipeline.py` (extend)

- [ ] **Step 1: Write failing tests for run_pipeline**

Append to `python/totlib/tests/test_pipeline.py`:

```python
# ============================================================
# run_pipeline behavior
# ============================================================

from totlib.errors import TotPipelineRunError


def _make_state(scalars):
    state = MagicMock()
    state.scalars = dict(scalars)
    return state


def test_run_pipeline_empty_steps_raises(patch_wrappers):
    pipe = TotPipeline()
    with pytest.raises(TotPipelineCouplingError, match="non-empty"):
        pipe.run_pipeline([])


def test_run_pipeline_unknown_module_raises(patch_wrappers):
    pipe = TotPipeline()
    with pytest.raises(TotPipelineUnknownModuleError):
        pipe.run_pipeline([("xx", {})])


def test_run_pipeline_bad_kwargs_raises(patch_wrappers):
    pipe = TotPipeline()
    with pytest.raises(TotPipelineCouplingError, match="kwargs"):
        pipe.run_pipeline([("fp", "not_a_dict")])


def test_run_pipeline_calls_module_run_and_collects_state(patch_wrappers):
    pipe = TotPipeline()
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.get_state.return_value = _make_state({"foo": 1.5})
    result = pipe.run_pipeline([("fp", {"ntmax": 5})])
    fp_inst.run.assert_called_once_with(ntmax=5)
    assert result.last("fp").scalars == {"foo": 1.5}
    assert result.last("fp").coupling_applied == []


def test_run_pipeline_applies_coupling_rule(patch_wrappers, monkeypatch):
    """Inject a known rule for ('fp','tr') and verify it propagates."""
    from totlib.pipeline import CouplingRule
    rules = {
        ("fp", "tr"): [
            CouplingRule(
                src_state_key="rjt_total",
                dst_param="PNBCD",
                transform=lambda v: v * 2.0,
                doc="test rule",
            ),
        ]
    }
    monkeypatch.setattr("totlib.pipeline.COUPLING_RULES", rules)
    pipe = TotPipeline()
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    tr_inst = patch_wrappers["classes"]["tr"].return_value
    fp_inst.get_state.return_value = _make_state({"rjt_total": 5.0})
    tr_inst.get_state.return_value = _make_state({"AJT": 99.0})
    result = pipe.run_pipeline([("fp", {"ntmax": 1}), ("tr", {"ntmax": 1})])
    # tr.set_param was called with the transformed value
    tr_inst.set_param.assert_any_call("PNBCD", 10.0)
    assert "test rule" in result.last("tr").coupling_applied


def test_run_pipeline_missing_source_state_raises_coupling_error(
    patch_wrappers, monkeypatch
):
    from totlib.pipeline import CouplingRule
    rules = {
        ("fp", "tr"): [
            CouplingRule(src_state_key="missing_key", dst_param="X", doc="r"),
        ]
    }
    monkeypatch.setattr("totlib.pipeline.COUPLING_RULES", rules)
    pipe = TotPipeline()
    patch_wrappers["classes"]["fp"].return_value.get_state.return_value = (
        _make_state({"other_key": 1.0})
    )
    with pytest.raises(TotPipelineRunError) as exc_info:
        pipe.run_pipeline([("fp", {"ntmax": 1}), ("tr", {"ntmax": 1})])
    # Wrapped underlying cause is TotPipelineCouplingError
    assert isinstance(exc_info.value.__cause__, TotPipelineCouplingError)
    assert exc_info.value.failed_module == "tr"
    assert exc_info.value.failed_step_index == 1


def test_run_pipeline_partial_failure_carries_partial_result(
    patch_wrappers, monkeypatch
):
    """When step 2 raises, the error carries step 1's snapshot."""
    pipe = TotPipeline()
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    tr_inst = patch_wrappers["classes"]["tr"].return_value
    fp_inst.get_state.return_value = _make_state({"foo": 7.0})
    tr_err_class = patch_wrappers["errors"]["tr"]
    tr_inst.run.side_effect = tr_err_class("tr boom")
    with pytest.raises(TotPipelineRunError) as exc_info:
        pipe.run_pipeline([("fp", {"ntmax": 1}), ("tr", {"ntmax": 1})])
    err = exc_info.value
    assert err.failed_step_index == 1
    assert err.failed_module == "tr"
    assert len(err.partial_result.steps) == 1
    assert err.partial_result.steps[0].module == "fp"
    assert err.partial_result.steps[0].scalars == {"foo": 7.0}


def test_run_pipeline_after_close_raises_lifecycle(patch_wrappers):
    pipe = TotPipeline()
    pipe.close()
    with pytest.raises(TotPipelineLifecycleError):
        pipe.run_pipeline([("fp", {})])
```

- [ ] **Step 2: Run extended test to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline.py -v 2>&1 | tail -30
```

Expected: existing 11 still pass, 8 new tests fail with AttributeError on `run_pipeline`.

- [ ] **Step 3: Add COUPLING_RULES + run_pipeline implementation**

Edit `python/totlib/pipeline.py`. After `_import_module_error` and **before** `class TotPipeline`, add:

```python
# ------------------------------------------------------------------
# Coupling rule registry
# ------------------------------------------------------------------
# L-7a scope: only ('fp','tr') is populated. Concrete src_state_key,
# dst_param, transform are filled in Phase 2 (Equivalence test PR)
# after R2/R3 outcomes are recorded in the spec.
# L-7b will add more pairs (('wr','fp'), ('wr','tr'), ('eq','tr'), ...)
# without changing the orchestrator code.

COUPLING_RULES: dict[tuple[str, str], list[CouplingRule]] = {
    # ("fp", "tr"): [...]    ← Phase 2 fills this
}
```

Then in `class TotPipeline`, add `_validate_steps`, `_extract_source`, and `run_pipeline`:

```python
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

    @staticmethod
    def _extract_source(prev_state, rule: CouplingRule) -> float:
        """Resolve a rule's source value from the previous module's state.

        - If src_state_key is a string, look it up in prev_state.scalars.
        - If src_state_key is a callable, invoke it with prev_state.
        Wraps lookup/computation errors as TotPipelineCouplingError.
        """
        try:
            if callable(rule.src_state_key):
                return float(rule.src_state_key(prev_state))
            return float(prev_state.scalars[rule.src_state_key])
        except KeyError as e:
            raise TotPipelineCouplingError(
                f"source state key {rule.src_state_key!r} missing from "
                f"prev_state.scalars; rule: {rule.doc!r}"
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

        result_steps: list[PipelineStep] = []
        prev_name: str | None = None
        prev_state = None

        for i, (name, kwargs) in enumerate(steps):
            base_err = _import_module_error(name)
            try:
                module = self._ensure_module(name)
                applied: list[str] = []

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
                        applied.append(rule.doc)

                module.run(**kwargs)
                cur_state = module.get_state()
                result_steps.append(PipelineStep(
                    module=name,
                    scalars=dict(cur_state.scalars),
                    coupling_applied=applied,
                ))
                prev_name, prev_state = name, cur_state
            except (base_err, TotPipelineCouplingError) as e:
                raise TotPipelineRunError(
                    f"step {i} ({name}) failed: {e}",
                    partial_result=PipelineResult(steps=result_steps),
                    failed_step_index=i,
                    failed_module=name,
                ) from e

        return PipelineResult(steps=result_steps)
```

Also, at the top of the file with the other error imports, add `TotPipelineRunError`, `TotPipelineUnknownModuleError`:

```python
from .errors import (
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineRunError,
    TotPipelineUnknownModuleError,
)
```

- [ ] **Step 4: Run extended tests to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline.py -v 2>&1 | tail -30
```

Expected: 19 passed (11 lifecycle + 8 run_pipeline).

- [ ] **Step 5: Commit**

```bash
git add python/totlib/pipeline.py python/totlib/tests/test_pipeline.py
git commit -m "feat(totlib): implement TotPipeline.run_pipeline orchestrator

- COUPLING_RULES registry (empty at this commit; ('fp','tr') is filled
  in Phase 2 after R2/R3 outcomes).
- _validate_steps performs side-effect-free pre-flight checks.
- _extract_source resolves both string and callable src_state_key,
  wrapping lookup/computation errors as TotPipelineCouplingError.
- run_pipeline iterates steps, applies coupling rules between adjacent
  pairs, and wraps per-module errors as TotPipelineRunError with the
  partial PipelineResult attached for debugging.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.6: Export TotPipeline from totlib package

**Files:**
- Modify: `python/totlib/__init__.py`
- Test: `python/totlib/tests/test_pipeline_export.py` (new)

- [ ] **Step 1: Write failing test**

Create `python/totlib/tests/test_pipeline_export.py`:

```python
"""Verify TotPipeline is exported at the package level."""

def test_tot_pipeline_importable_from_package():
    from totlib import TotPipeline
    assert TotPipeline.__name__ == "TotPipeline"


def test_tot_pipeline_in_dunder_all():
    import totlib
    assert "TotPipeline" in totlib.__all__


def test_legacy_tot_still_exported():
    """Backwards compat: existing Tot import path must continue to work."""
    from totlib import Tot
    assert Tot.__name__ == "Tot"
```

- [ ] **Step 2: Run test to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_export.py -v 2>&1 | head -10
```

Expected: ImportError on `from totlib import TotPipeline`.

- [ ] **Step 3: Update `__init__.py`**

Edit `python/totlib/__init__.py`. After the `from .totlib import Tot` line, add:

```python
from .pipeline import TotPipeline, CouplingRule, PipelineStep, PipelineResult
```

In the `__all__` list, append `"TotPipeline"`, `"CouplingRule"`, `"PipelineStep"`, `"PipelineResult"`.

- [ ] **Step 4: Run test to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_export.py -v 2>&1 | head -10
```

Expected: 3 passed.

- [ ] **Step 5: Run full Phase 1 test suite**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline*.py -v 2>&1 | tail -15
```

Expected: 29 passed (4 errors + 7 dataclasses + 6 registry + 19 pipeline + 3 export).

- [ ] **Step 6: Commit**

```bash
git add python/totlib/__init__.py python/totlib/tests/test_pipeline_export.py
git commit -m "feat(totlib): export TotPipeline + dataclasses at package level

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.7: Phase 1 pre-push gate (PR 1)

- [ ] **Step 1: Run Phase 1 tests with the canonical CI flags**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  timeout 300 python3 -m pytest --forked --timeout=120 --timeout-method=signal \
    python/totlib/tests/test_pipeline*.py -v 2>&1 | head -c 1M | tail -40
```

Expected: 29 passed, 0 failed. (No SKIPs allowed per CLAUDE.md.)

- [ ] **Step 2: Run general-purpose code-reviewer**

Use the Task/Agent tool: launch `Agent(subagent_type="feature-dev:code-reviewer", ...)` with a prompt that summarizes the Phase 1 diff (commits since `52481e9f`, excluding the spec) and asks for HIGH/MED issues. Paste the response back.

- [ ] **Step 3: Run codex:codex-rescue review**

Launch `Agent(subagent_type="codex:codex-rescue", ...)` with the same diff range and a prompt asking for factual errors / Fortran-vs-Python doc divergence / spec compliance. Paste the response back.

- [ ] **Step 4: Address HIGH/MED findings**

Iterate: fix → re-run pytest → re-review until both reviewers report no HIGH/MED issues.

- [ ] **Step 5: Place REVIEW_OK marker**

```bash
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
```

- [ ] **Step 6: Push PR 1 branch**

```bash
git push -u origin chore/pre-push-hook-worktree-compat
```

(Pre-push hook validates the marker.)

- [ ] **Step 7: Open PR 1**

Use `gh pr create --title "feat(totlib): TotPipeline foundation (L-7a Phase 1)" --body "$(cat <<'EOF'
## Summary
- New \`TotPipeline\` class in \`python/totlib/pipeline.py\` (Python-side scalar coupling orchestrator)
- TotPipeline error hierarchy (5 new exception types) in \`python/totlib/errors.py\`
- COUPLING_RULES registry, mock-based unit tests (29 tests, lib*.so not required)
- Legacy \`Tot\` class is unchanged

## Test plan
- [ ] \`pytest --forked --timeout=120 --timeout-method=signal python/totlib/tests/test_pipeline*.py\` (29 pass)
- [ ] Existing \`test_totlib.py\` still passes unchanged

## Spec
\`docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md\`

## Follow-ups (separate PRs)
- PR 2: \`test_pipeline_equiv.py\` + \`compute_rjt_volint\` helper + COUPLING_RULES population
- PR 3: \`run_pipeline\` MCP tool + docs

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"`

---

## Phase 2 — Equivalence Test (PR 2)

Adds the 1e-10 equivalence test that compares hand-written `fp → tr` coupling against `run_pipeline`. Requires `libfpapi.so` and `libtrapi.so` to be built. PR 2 starts from a clean branch off PR 1 (or merges PR 1 first).

### Task 2.1: Implement `compute_rjt_volint` helper

**Files:**
- Modify: `python/totlib/pipeline.py`
- Test: `python/totlib/tests/test_pipeline_helpers.py` (new)

- [ ] **Step 1: Write failing test using a synthetic state**

Create `python/totlib/tests/test_pipeline_helpers.py`:

```python
"""Test the compute_rjt_volint helper using a synthetic state object."""
from unittest.mock import MagicMock
import math
import pytest
from totlib.pipeline import compute_rjt_volint


def test_compute_rjt_volint_uniform_profile():
    """For RJT(rho)=const, the integral should equal const * total volume."""
    state = MagicMock()
    # Plug in the exact attribute names confirmed by R2 (e.g. RJT, RG, nrmax)
    # Replace these with the names recorded in the spec's Research outcomes.
    state.RJT = [1.0, 1.0, 1.0, 1.0]
    # ... additional attributes per R2 outcome
    expected_volume = 1.0  # ← compute analytically from chosen grid
    result = compute_rjt_volint(state)
    assert math.isclose(result, expected_volume * 1.0, rel_tol=1e-12), \
        f"got {result}, expected {expected_volume}"


def test_compute_rjt_volint_zero_profile():
    state = MagicMock()
    state.RJT = [0.0, 0.0, 0.0, 0.0]
    assert compute_rjt_volint(state) == 0.0
```

**Note:** the synthetic state shape MUST match what R2 confirmed. If R2 found that fp's volume integral requires `state.RG` + cell widths, mock `state.RG` accordingly. Update the test attributes from the R2 outcome before running.

- [ ] **Step 2: Run test to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_helpers.py -v 2>&1 | head -10
```

Expected: ImportError on `compute_rjt_volint`.

- [ ] **Step 3: Implement helper based on R2 outcome**

Edit `python/totlib/pipeline.py`. Add (placement: top-level, after `_import_module_error`):

```python
def compute_rjt_volint(state) -> float:
    """fp's driven current as a scalar [Amperes]: ∫ RJT(rho) dV.

    Implementation paste-in from spec §8 R2 outcome. Operates only on
    Python-side state attributes — no FFI calls.
    """
    # ← Paste the R2-derived implementation here.
    # The function must return a float in Amperes regardless of the
    # underlying grid (uniform-rho or otherwise).
    raise NotImplementedError("Fill me in from R2 outcome")
```

Replace the `raise NotImplementedError` with the concrete implementation derived from R2.

- [ ] **Step 4: Run test to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline_helpers.py -v 2>&1 | head -10
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add python/totlib/pipeline.py python/totlib/tests/test_pipeline_helpers.py
git commit -m "feat(totlib): add compute_rjt_volint helper

Computes the fp driven-current volume integral as a scalar in Amperes.
Implementation derived from spec §8 R2 outcome. No fplib changes —
helper operates on Python-side state attributes only.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 2.2: Populate COUPLING_RULES[("fp","tr")]

**Files:**
- Modify: `python/totlib/pipeline.py`
- Modify: `python/totlib/tests/test_pipeline.py` (extend)

- [ ] **Step 1: Write failing test that the rule is registered**

Append to `python/totlib/tests/test_pipeline.py`:

```python
def test_coupling_rules_has_fp_to_tr():
    from totlib.pipeline import COUPLING_RULES
    rules = COUPLING_RULES.get(("fp", "tr"), [])
    assert len(rules) == 1, f"expected exactly 1 rule, got {rules!r}"
    rule = rules[0]
    # The dst_param must match what R3 confirmed (e.g. 'PNBCD').
    # If R3 produced a different name, update this assertion.
    assert rule.dst_param == "PNBCD"
    assert "RJT" in rule.doc or "driven current" in rule.doc.lower()
```

- [ ] **Step 2: Run test to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline.py::test_coupling_rules_has_fp_to_tr -v 2>&1 | head -10
```

Expected: `assert 0 == 1` (empty rule list).

- [ ] **Step 3: Populate the rule with R2/R3 values**

Edit `python/totlib/pipeline.py`. Replace the empty `COUPLING_RULES = {}` body with:

```python
COUPLING_RULES: dict[tuple[str, str], list[CouplingRule]] = {
    ("fp", "tr"): [
        CouplingRule(
            src_state_key=compute_rjt_volint,    # callable: profile→scalar
            dst_param="PNBCD",                   # ← R3 outcome
            transform=lambda v: v * 1e-6,        # ← R3 outcome (A→MA);
                                                 # adjust if R3 confirmed otherwise
            doc="fp driven current (RJT volume integral) [A] -> tr PNBCD [MA]",
        ),
    ],
}
```

Replace `dst_param`, `transform`, and `doc` with the exact values from R3.

- [ ] **Step 4: Run test to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/totlib/tests/test_pipeline.py -v 2>&1 | tail -25
```

Expected: 20 passed (19 prior + 1 new).

- [ ] **Step 5: Commit**

```bash
git add python/totlib/pipeline.py python/totlib/tests/test_pipeline.py
git commit -m "feat(totlib): populate COUPLING_RULES[('fp','tr')]

Single rule wires fp's compute_rjt_volint(state) to tr's PNBCD scalar
parameter (per spec §8 R2/R3 outcomes). The transform converts from
Amperes (fp output) to MA (tr input).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 2.3: Equivalence test (lib*.so required)

**Files:**
- Test: `python/totlib/tests/test_pipeline_equiv.py` (new)
- Optional fixture: `python/totlib/tests/fixtures/pipeline_equiv_params.py` (if needed for shared setup)

- [ ] **Step 1: Verify lib*.so are buildable in CI**

Run:
```bash
ls fp/libfpapi.so tr/libtrapi.so 2>&1
```

If missing, run `make` for each. Document the build commands in the test file's docstring so CI knows how to provision.

- [ ] **Step 2: Identify a working fixture parameter set**

Look at existing fp/tr unit tests for the smallest fixture that runs without errors:

```bash
grep -nE "set_param.*[\"']" python/fplib/tests/*.py | head -20
grep -nE "set_param.*[\"']" python/trlib/tests/*.py | head -20
```

Pick a fixture that produces a non-zero RJT (otherwise the coupling test is vacuous — both patterns will trivially agree).

- [ ] **Step 3: Write the equivalence test**

Create `python/totlib/tests/test_pipeline_equiv.py`:

```python
"""Equivalence test: hand-written fp→tr coupling vs run_pipeline.

CLAUDE.md non-negotiable: must pass at 1e-10 relative tolerance.
Requires libfpapi.so + libtrapi.so. Run with --forked --timeout=120
--timeout-method=signal per CLAUDE.md test discipline.

Per spec §9.2.
"""
import math
import os
import pytest

from fplib import Fplib
from trlib import Trlib
from totlib import TotPipeline
from totlib.pipeline import compute_rjt_volint


def _libs_present() -> bool:
    repo = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    return all(
        os.path.exists(os.path.join(repo, p))
        for p in ("fp/libfpapi.so", "tr/libtrapi.so")
    )


pytestmark = pytest.mark.skipif(
    not _libs_present(),
    reason="requires libfpapi.so + libtrapi.so — run scripts/setup.sh first",
)


# Bare-name params (existing fp/trlib unit tests use these forms).
# Update the values to match the smallest fixture confirmed in step 2.
FP_PARAMS = {
    "NSAMAX": 2,
    # ← additional fp params per the chosen fixture
}
TR_PARAMS = {
    "RR": 6.2,
    "RA": 2.0,
    "BB": 5.3,
    "RIP": 15.0,
    "MODELG": 2,
    # ← additional tr params per the chosen fixture
}
NTMAX_FP = 5
NTMAX_TR = 1


def _baseline():
    """Pattern X: hand-written coupling."""
    fp = Fplib()
    fp.set_params(**FP_PARAMS)
    fp.run(ntmax=NTMAX_FP)
    fp_state = fp.get_state()
    rjt_volint = compute_rjt_volint(fp_state)
    fp_scalars = dict(fp_state.scalars)
    fp.close()

    tr = Trlib()
    tr.set_params(**TR_PARAMS)
    tr.set_param("PNBCD", rjt_volint * 1e-6)   # ← R3 transform
    tr.run(ntmax=NTMAX_TR)
    tr_scalars = dict(tr.get_state().scalars)
    tr.close()
    return fp_scalars, tr_scalars


def _through_pipeline():
    """Pattern Y: run_pipeline."""
    pipeline_params = (
        {f"fp:{k}": v for k, v in FP_PARAMS.items()}
        | {f"tr:{k}": v for k, v in TR_PARAMS.items()}
    )
    pipe = TotPipeline()
    for k, v in pipeline_params.items():
        pipe.set_param(k, v)
    result = pipe.run_pipeline([
        ("fp", {"ntmax": NTMAX_FP}),
        ("tr", {"ntmax": NTMAX_TR}),
    ])
    pipe.close()
    return dict(result.last("fp").scalars), dict(result.last("tr").scalars), result


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-15)


def test_fp_tr_pipeline_equiv_scalars_match():
    fp_x, tr_x = _baseline()
    fp_y, tr_y, _ = _through_pipeline()
    mismatches = []
    for key in fp_x:
        if not _close(fp_x[key], fp_y[key]):
            mismatches.append(("fp", key, fp_x[key], fp_y[key]))
    for key in tr_x:
        if not _close(tr_x[key], tr_y[key]):
            mismatches.append(("tr", key, tr_x[key], tr_y[key]))
    assert not mismatches, (
        f"{len(mismatches)} scalar(s) deviate beyond 1e-10:\n"
        + "\n".join(f"  {mod}.{k}: baseline={a} pipeline={b}"
                    for mod, k, a, b in mismatches)
    )


def test_pipeline_records_coupling_doc():
    _, _, result = _through_pipeline()
    tr_step = result.last("tr")
    assert tr_step.coupling_applied, "coupling_applied is empty"
    assert any("RJT" in d or "driven current" in d.lower()
               for d in tr_step.coupling_applied), \
        f"expected RJT/driven current doc, got {tr_step.coupling_applied!r}"
```

- [ ] **Step 4: Run the equivalence test**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  timeout 600 python3 -m pytest --forked --timeout=120 --timeout-method=signal \
    python/totlib/tests/test_pipeline_equiv.py -v 2>&1 | head -c 1M | tail -40
```

Expected: 2 passed (no skips!). If skipped due to missing libs, run `scripts/setup.sh` first. If a scalar deviates, the per-key diff in the assertion message points to which physical quantity is off — investigate (likely either compute_rjt_volint or the transform factor).

- [ ] **Step 5: Commit**

```bash
git add python/totlib/tests/test_pipeline_equiv.py
git commit -m "test(totlib): add fp→tr equivalence test at 1e-10 tolerance

Compares pattern X (hand-written Fplib + Trlib + compute_rjt_volint
+ tr.set_param('PNBCD', ...)) vs pattern Y (TotPipeline.run_pipeline).
Per CLAUDE.md, equivalence tests at 1e-10 must pass — no SKIP allowed.
Requires libfpapi.so + libtrapi.so.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 2.4: Phase 2 pre-push gate (PR 2)

- [ ] **Step 1: Run the full Phase-2 test suite**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  timeout 600 python3 -m pytest --forked --timeout=120 --timeout-method=signal \
    python/totlib/tests/test_pipeline*.py -v 2>&1 | head -c 1M | tail -40
```

Expected: 32 passed (29 prior Phase 1 + helpers 2 + COUPLING_RULES test 1 = 32 mock; equivalence 2 + records-doc 1 = 3 lib-required, brings total to 35 if libs present). All pass with 0 skips on a machine that has the libs.

- [ ] **Step 2: code-reviewer + codex:codex-rescue**

Same protocol as Task 1.7 steps 2–4. The diff range for PR 2 review is "PR 1 merge commit" → "current HEAD".

- [ ] **Step 3: REVIEW_OK marker + push**

```bash
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
git push
```

- [ ] **Step 4: Open PR 2**

```bash
gh pr create --title "test(totlib): fp→tr equivalence test (L-7a Phase 2)" --body "$(cat <<'EOF'
## Summary
- \`compute_rjt_volint(state)\` helper in \`python/totlib/pipeline.py\` (per spec §8 R2)
- COUPLING_RULES[('fp','tr')] populated with R3 values
- \`test_pipeline_equiv.py\` verifies hand-written coupling and run_pipeline produce identical scalars at 1e-10 relative tolerance

## Test plan
- [ ] \`pytest --forked --timeout=120 --timeout-method=signal python/totlib/tests/test_pipeline_equiv.py\` passes on a machine with libfpapi.so + libtrapi.so
- [ ] No new SKIPs introduced

## Depends on
- PR 1 (TotPipeline foundation)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Phase 3 — MCP Integration (PR 3)

Adds the `run_pipeline` MCP tool and docs. Builds on the merged Phase 1 + 2 base.

### Task 3.1: MCP tool `run_pipeline` + force-close gate

**Files:**
- Modify: `python/mcp-servers/tot_mcp/server.py`
- Test: `python/mcp-servers/tot_mcp/tests/test_pipeline_tool.py` (new)

- [ ] **Step 1: Read current server.py to find STATE pattern**

Run:
```bash
grep -nE "(STATE|_force_close|@tool|run_and_get_state)" /Users/k-yoshimi/Dropbox/cursor/task/python/mcp-servers/tot_mcp/server.py | head -30
```

Note the global `STATE` variable, `_force_close()` helper, and decorator pattern (FastMCP).

- [ ] **Step 2: Write failing tests**

Create `python/mcp-servers/tot_mcp/tests/test_pipeline_tool.py`:

```python
"""Tests for the new run_pipeline MCP tool."""
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Replace TotPipeline with a stub that records all calls."""
    captured = {"params": {}, "steps": None, "closed": False}

    class StubPipeline:
        def __init__(self):
            captured["init"] = True

        def set_param(self, k, v):
            captured["params"][k] = v

        def run_pipeline(self, steps):
            captured["steps"] = steps
            from totlib.pipeline import PipelineStep, PipelineResult
            return PipelineResult(steps=[
                PipelineStep("fp", {"foo": 1.0}, []),
                PipelineStep("tr", {"bar": 2.0}, ["fp -> tr"]),
            ])

        def close(self):
            captured["closed"] = True

    # Patch the import path used inside server.py
    monkeypatch.setattr("tot_mcp.server.TotPipeline", StubPipeline)
    return captured


def test_run_pipeline_tool_calls_pipeline(stub_pipeline):
    from tot_mcp.server import handle_run_pipeline
    out = handle_run_pipeline(
        steps=[
            {"module": "fp", "kwargs": {"ntmax": 5}},
            {"module": "tr", "kwargs": {"ntmax": 1}},
        ],
        params={"fp:NSAMAX": 2},
    )
    assert out["fp"] == {"foo": 1.0}
    assert out["tr"] == {"bar": 2.0}
    assert stub_pipeline["steps"] == [("fp", {"ntmax": 5}), ("tr", {"ntmax": 1})]
    assert stub_pipeline["params"] == {"fp:NSAMAX": 2}


def test_run_pipeline_tool_force_closes_legacy_state(stub_pipeline, monkeypatch):
    """If legacy STATE is live when run_pipeline is invoked, it must be force-closed."""
    legacy_close_called = []
    legacy_stub = MagicMock()
    legacy_stub.close.side_effect = lambda: legacy_close_called.append(True)
    monkeypatch.setattr("tot_mcp.server.STATE", legacy_stub)

    from tot_mcp.server import handle_run_pipeline
    handle_run_pipeline(
        steps=[{"module": "fp", "kwargs": {}}],
        params=None,
    )
    assert legacy_close_called, "legacy STATE.close() was not called"


def test_run_pipeline_tool_force_closes_prev_pipeline(stub_pipeline, monkeypatch):
    """Successive run_pipeline calls must isolate state (existing HIGH audit pattern)."""
    from tot_mcp.server import handle_run_pipeline
    handle_run_pipeline(
        steps=[{"module": "fp", "kwargs": {}}], params=None,
    )
    # The first call set captured['closed'] via stub close; second invocation
    # must produce a fresh pipeline (re-init).
    captured = stub_pipeline
    captured["closed"] = False
    handle_run_pipeline(
        steps=[{"module": "fp", "kwargs": {}}], params=None,
    )
    # The second call's pre-amble closed the first pipeline.
    assert captured["closed"] is True


def test_run_pipeline_tool_validates_input(stub_pipeline):
    from tot_mcp.server import handle_run_pipeline
    from totlib.errors import TotPipelineCouplingError
    with pytest.raises(TotPipelineCouplingError):
        handle_run_pipeline(steps=[{"module": "fp"}], params=None)  # missing kwargs key
```

- [ ] **Step 3: Run tests to verify FAIL**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/mcp-servers/tot_mcp/tests/test_pipeline_tool.py -v 2>&1 | head -10
```

Expected: ImportError on `handle_run_pipeline` from tot_mcp.server.

- [ ] **Step 4: Add the tool to server.py**

Edit `python/mcp-servers/tot_mcp/server.py`. Near the top with other imports:

```python
from totlib import TotPipeline
from totlib.errors import TotPipelineCouplingError
```

Add a module-level pipeline state next to `STATE`:

```python
PIPELINE_STATE: TotPipeline | None = None
```

Add helpers `_force_close_pipeline` and `_normalize_pipeline_steps`:

```python
def _force_close_pipeline() -> None:
    """Close PIPELINE_STATE if open, mirroring the existing _force_close pattern
    (HIGH audit fix 2026-04-22 in run_and_get_state)."""
    global PIPELINE_STATE
    if PIPELINE_STATE is not None:
        try:
            PIPELINE_STATE.close()
        finally:
            PIPELINE_STATE = None


def _normalize_pipeline_steps(steps: list[dict]) -> list[tuple[str, dict]]:
    """MCP transports steps as a list of dicts; TotPipeline expects tuples.

    Validates the dict shape upfront so a malformed payload raises
    TotPipelineCouplingError before any side effects (matches the
    spec §6.2 _validate_steps philosophy at the MCP boundary)."""
    normalized: list[tuple[str, dict]] = []
    for i, item in enumerate(steps):
        if not isinstance(item, dict):
            raise TotPipelineCouplingError(
                f"steps[{i}] must be a dict, got {type(item).__name__}"
            )
        if "module" not in item:
            raise TotPipelineCouplingError(
                f"steps[{i}] missing required key 'module'"
            )
        if "kwargs" not in item:
            raise TotPipelineCouplingError(
                f"steps[{i}] missing required key 'kwargs' "
                f"(use {{}} for an empty kwargs dict)"
            )
        normalized.append((item["module"], item["kwargs"]))
    return normalized
```

Then add the `handle_run_pipeline` function and register it as a tool. Match the existing FastMCP decorator style — find the existing `@MCP.tool` (or similar) and add:

```python
def handle_run_pipeline(
    steps: list[dict],
    params: dict | None = None,
) -> dict:
    """Run a multi-module pipeline with scalar coupling.

    Args:
        steps: e.g. [{"module": "fp", "kwargs": {"ntmax": 5}},
                     {"module": "tr", "kwargs": {"ntmax": 1}}]
        params: optional bulk param setter, e.g. {"fp:NSAMAX": 2}

    Returns:
        PipelineResult.to_dict() — flat per-module final scalars plus
        a "_steps" timeline.
    """
    global STATE, PIPELINE_STATE

    # Mutually exclusive with legacy STATE — force-close if live.
    if STATE is not None:
        try:
            STATE.close()
        finally:
            STATE = None

    _force_close_pipeline()

    PIPELINE_STATE = TotPipeline()
    if params:
        for k, v in params.items():
            PIPELINE_STATE.set_param(k, v)
    normalized = _normalize_pipeline_steps(steps)
    return PIPELINE_STATE.run_pipeline(normalized).to_dict()
```

Register the handler with the MCP framework — match the existing pattern. If FastMCP `@MCP.tool` is used, decorate `handle_run_pipeline` accordingly. (Read the existing `@<MCP>.tool` site once more to confirm the exact decorator name; do not guess.)

- [ ] **Step 5: Run tests to verify PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  python3 -m pytest python/mcp-servers/tot_mcp/tests/test_pipeline_tool.py -v 2>&1 | head -20
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add python/mcp-servers/tot_mcp/server.py python/mcp-servers/tot_mcp/tests/test_pipeline_tool.py
git commit -m "feat(tot_mcp): add run_pipeline tool with force-close gate

Backed by TotPipeline. Mutually exclusive with legacy STATE — when
run_pipeline is called, any live legacy STATE is force-closed first.
Successive run_pipeline calls also force-close the previous pipeline,
mirroring the HIGH audit fix (2026-04-22) on run_and_get_state.

Steps payload normalization rejects missing 'module'/'kwargs' keys
before any side effects, raising TotPipelineCouplingError.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.2: Update tot_mcp README

**Files:**
- Modify: `python/mcp-servers/tot_mcp/README.md`

- [ ] **Step 1: Read current README**

```bash
sed -n '1,60p' /Users/k-yoshimi/Dropbox/cursor/task/python/mcp-servers/tot_mcp/README.md
```

- [ ] **Step 2: Add a `run_pipeline` section**

Use Edit to append (or insert at a contextually appropriate location near other tools):

````markdown
### Tool: `run_pipeline`

Multi-module scalar coupling pipeline (L-7a). Backed by `totlib.TotPipeline`.

**Args:**
- `steps`: list of `{"module": "<name>", "kwargs": {...}}`. Module names: `fp`, `tr`, `eq`, `wr`, `wrx`, `ti`.
- `params`: optional `{"<module>:<param>": value, ...}` to set before the pipeline runs.

**Returns:** `{"<module>": {<scalars>, ...}, "_steps": [...]}` — final scalars per module plus a timeline.

**Currently implemented coupling rule (L-7a):**
- `fp → tr`: `compute_rjt_volint(fp_state)` (Amperes) → `tr.PNBCD` (MA, transform `× 1e-6`).

**Example:**

```json
{
  "steps": [
    {"module": "fp", "kwargs": {"ntmax": 5}},
    {"module": "tr", "kwargs": {"ntmax": 1}}
  ],
  "params": {"fp:NSAMAX": 2, "tr:RR": 6.2}
}
```

**Isolation:** Each call force-closes the legacy `STATE` (Tot) and any previous pipeline before starting, matching the HIGH audit pattern from `run_and_get_state`.

**Limits:** L-7a covers only scalar coupling. Profile-level coupling (e.g. wr deposition profile, eq q-profile) is deferred to L-7b via the BPSD broker.
````

- [ ] **Step 3: Commit**

```bash
git add python/mcp-servers/tot_mcp/README.md
git commit -m "docs(tot_mcp): document run_pipeline tool

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.3: Update totlib README

**Files:**
- Modify: `python/totlib/README.md`

- [ ] **Step 1: Add a TotPipeline section**

Use Edit to add a section after the existing Tot description:

````markdown
## TotPipeline (L-7a, Python-side scalar coupling)

`TotPipeline` is a thin orchestrator that composes existing per-module
wrappers (`Fplib`, `Trlib`, ...) with hardcoded scalar coupling rules.
It does NOT use `libtotapi.so` — that path is handled by the legacy
`Tot` class above and is left untouched.

**When to use which:**
- TR-only transport solver, regression tests → `Tot`
- Multi-module scalar coupling pipelines → `TotPipeline`
- Direct module access → `from <mod>lib import <Mod>`

**Same-process coexistence with `Tot` is undefined** — both call
`tr_init` internally. Pick one.

**Example:**

```python
from totlib import TotPipeline

with TotPipeline() as tot:
    tot.set_param("fp:NSAMAX", 2)
    tot.set_param("tr:RR", 6.2)
    tot.set_param("tr:RA", 2.0)
    result = tot.run_pipeline([
        ("fp", {"ntmax": 5}),
        ("tr", {"ntmax": 1}),
    ])
    print(result.last("tr").scalars)
```

**Coupling rules (L-7a):**
- `fp → tr`: fp's RJT volume integral [A] → tr's `PNBCD` [MA].

**Failure handling:** `TotPipelineRunError.partial_result` carries
the steps completed before the failure, useful for mid-pipeline
debugging.

See `docs/superpowers/specs/2026-04-28-l7a-cross-module-coupling-design.md`
for the full design.
````

- [ ] **Step 2: Commit**

```bash
git add python/totlib/README.md
git commit -m "docs(totlib): document TotPipeline (L-7a)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.4: Update tot/applications.md (ja + en)

**Files:**
- Modify: `docs/sphinx/modules/tot/ja/applications.md`
- Modify: `docs/sphinx/modules/tot/en/applications.md`

- [ ] **Step 1: Locate the L-7 placeholder section in ja**

```bash
grep -n "L-7" /Users/k-yoshimi/Dropbox/cursor/task/docs/sphinx/modules/tot/ja/applications.md
```

- [ ] **Step 2: Replace the L-7 placeholder with a runnable L-7a example in ja**

Use Edit to swap out the `# tot.run_module("fp", ntmax=10)` style placeholders with a working `TotPipeline` snippet, AND keep a paragraph noting "L-7a 範囲: fp→tr scalar のみ. wr/eq の profile coupling は L-7b 以降". Match the document's existing tone (concise, code-first).

```python
from totlib import TotPipeline

with TotPipeline() as tot:
    tot.set_param("fp:NSAMAX", 2)
    tot.set_param("tr:RR", 6.2)
    tot.set_param("tr:RA", 2.0)
    result = tot.run_pipeline([
        ("fp", {"ntmax": 5}),
        ("tr", {"ntmax": 1}),
    ])
    print(result.last("tr").scalars["AJT"])
```

Add an admonition (`{warning}` per the doc convention) explicitly stating L-7a's scope limit.

- [ ] **Step 3: Mirror the change to the en version**

Same change to `docs/sphinx/modules/tot/en/applications.md`. Keep the wording aligned with the other modules' "Possible extensions / Combination patterns / Auto-stabilizing" pattern from commit 7699b72c.

- [ ] **Step 4: Build the ja and en sphinx docs to verify no errors**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/docs/sphinx && \
  make SPHINXOPTS="" tot-ja tot-en 2>&1 | head -c 200000 | tail -40
```

Expected: no warnings/errors specific to applications.md.

- [ ] **Step 5: Commit**

```bash
git add docs/sphinx/modules/tot/ja/applications.md docs/sphinx/modules/tot/en/applications.md
git commit -m "docs(tot-applications): replace L-7 placeholder with L-7a TotPipeline

ja + en updated to a runnable run_pipeline example. L-7a scope
(scalar-only, fp→tr) is called out in a warning admonition;
profile-level coupling (wr/eq via BPSD) is noted as L-7b follow-up.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.5: Phase 3 pre-push gate (PR 3)

- [ ] **Step 1: Run the full L-7a test suite**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task && \
  timeout 600 python3 -m pytest --forked --timeout=120 --timeout-method=signal \
    python/totlib/tests/ python/mcp-servers/tot_mcp/tests/test_pipeline_tool.py \
    -v 2>&1 | head -c 1M | tail -40
```

Expected: all pass, 0 SKIPs (assuming libs are present), 0 fails.

- [ ] **Step 2: code-reviewer + codex:codex-rescue**

Same protocol as Tasks 1.7 / 2.4.

- [ ] **Step 3: REVIEW_OK marker + push**

```bash
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
git push
```

- [ ] **Step 4: Open PR 3**

```bash
gh pr create --title "feat(tot_mcp): run_pipeline tool + docs (L-7a Phase 3)" --body "$(cat <<'EOF'
## Summary
- New \`run_pipeline\` MCP tool in \`python/mcp-servers/tot_mcp/server.py\` backed by \`TotPipeline\`
- Force-close gate makes pipeline calls mutually exclusive with legacy \`STATE\`
- Updated \`python/totlib/README.md\`, \`python/mcp-servers/tot_mcp/README.md\`, and \`docs/sphinx/modules/tot/{ja,en}/applications.md\`

## Test plan
- [ ] \`pytest --forked --timeout=120 --timeout-method=signal python/mcp-servers/tot_mcp/tests/test_pipeline_tool.py\` (4 pass)
- [ ] \`make tot-ja tot-en\` builds without warnings/errors

## Depends on
- PR 1 (TotPipeline foundation)
- PR 2 (compute_rjt_volint + COUPLING_RULES + equivalence test)

## Closes the L-7a series
Follow-ups (L-7b) tracked in separate issues:
- profile-level coupling via BPSD ABI exposure
- additional pairs: wr→fp, wr→tr, eq→tr profile
- \`tot.couple(src, dst)\` declarative API

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review (run after writing the plan)

Use this checklist on the plan itself:

1. **Spec coverage**: every section of `2026-04-28-l7a-cross-module-coupling-design.md` is addressed by some task. ✓
2. **No placeholders**: no "TBD" / "fill in details" left. The only `← R2 outcome` / `← R3 outcome` markers are deliberate gating points that the engineer fills from the spec's Research outcomes (Task R2 step 6 and R3 step 5). ✓
3. **Type/name consistency**: `TotPipeline`, `CouplingRule`, `PipelineStep`, `PipelineResult`, `_MODULE_REGISTRY`, `_import_wrapper`, `_import_module_error`, `compute_rjt_volint`, `COUPLING_RULES`, `handle_run_pipeline`, `_force_close_pipeline`, `_normalize_pipeline_steps` are used consistently across tasks. ✓
4. **TDD discipline**: every code task starts with a failing test, then minimal implementation, then green. ✓
5. **CLAUDE.md compliance**: pre-push gate (code-reviewer + codex:codex-rescue + REVIEW_OK marker + `--forked --timeout=120 --timeout-method=signal`) appears at the end of each PR phase. ✓
