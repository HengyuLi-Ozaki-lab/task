# L-7b-ii Phase 2c PR-B — eq→tr rule activation + TotPipeline integration (design)

**Status**: design, pre-implementation
**Date**: 2026-05-26
**Tracking issues**: #208 (Phase 2c umbrella, closes when PR-B lands), #201 (Phase 2 umbrella, also closes)
**Predecessors**: PR #206 (Phase 2a), PR #207 (Phase 2b), PR #211 (#209 cascade), PR #212 (Phase 2c PR-A wrapper routing)
**Successor**: none — PR-B is the terminal step in Phase 2c.

## 1. Context

PR-A landed the plumbing: `MONO_LIB_PATH` env var → shared
`python/_runtime_mode.py` helper → all 6 wrappers consult it as
priority 0 in their `_default_lib_path()`. The mono image
(`libtotapi_mono.so`) shares one BPSD broker across eq/tr/fp/ti/wrx.

What is still missing for end-to-end usefulness:

- `python/totlib/pipeline.py:328` — `_MONO_ONLY_RULES` is still `{}`
  by deliberate Phase 2b restraint (Codex caught that prematurely
  populating it would cause user-facing regressions against
  still-per-module wrappers — that no longer applies after PR-A).
- No Layer-D test that actually drives
  `TotPipeline.run_pipeline([("eq", ...), ("tr", ...)])` on the mono
  image and asserts the `("eq","tr")` verify rule fires.

PR-B activates the rule and adds the Layer-D test. This is the
terminal step that closes #208 and #201.

## 2. Goal

`TotPipeline().run_pipeline([("eq", ...), ("tr", ...)])` on the mono
image MUST run the `("eq","tr")` verify rule and report it in
`PipelineResult.last("tr").coupling_applied`. On the default
per-module image the SAME pipeline call MUST succeed and NOT
activate the rule.

## 3. Scope

### In scope (PR-B)

1. Populate `_MONO_ONLY_RULES[("eq","tr")]` in
   `python/totlib/pipeline.py` with a single verify-kind rule that
   calls `Trlib.check_bpsd_pull()`.
2. New test file `python/totlib/tests/test_mono_pipeline_coupling.py`
   with **two** cases (per Codex 2026-05-26 review MED-6):
   - happy path on mono — rule fires, returns True;
   - dormant on default — rule absent from `coupling_applied`,
     pipeline still succeeds.
3. CI extension: append a step to the `mono build (Linux
   libtotapi_mono.so)` job that runs the new test.
4. Doc note in `python/totlib/README.md` mono routing section that
   the eq→tr rule is now active.

### Out of scope (PR-B)

- Other module-pair rules (e.g., ("tr","fp") for power/current
  transport coupling) — deferred to a future PR if a concrete user
  appears.
- Restructuring `_MONO_ONLY_RULES` to support per-rule activation
  conditions (mono is the only known activation condition today;
  YAGNI).
- Fortran source changes.
- `tot/tot_api.h` updates (PR-A already documented mono routing
  there; no ABI change in PR-B).

## 4. Design decisions

### D-1: Single verify rule, not transfer/decomposed

**Chosen**: one `CouplingRule(kind="verify", verify=_eq_to_tr_bpsd_check)`
in the `("eq","tr")` list, where `_eq_to_tr_bpsd_check(trlib_inst)`
returns `trlib_inst.check_bpsd_pull()`.
**Rejected**: per-BPSD-slot rules (one rule per device/equ1D/
metric1D slot). `Trlib.check_bpsd_pull` is already an aggregated
probe (PR #188) that returns True iff all required slots are
visible to tr; decomposing here would require new C ABI surface for
slot-level introspection and offers no actionable diagnostic gain.
**Why**: YAGNI. Trlib's existing probe is the natural granularity.

### D-2: Named module-level callable, not lambda

**Chosen**: define `_eq_to_tr_bpsd_check` as a `def` at module
scope; reference it from the rule.
**Rejected**: `verify=lambda trlib: trlib.check_bpsd_pull()`.
**Why**: `pipeline.run_pipeline` error messages use
`getattr(rule.verify, "__qualname__", repr(rule.verify))` for the
failed-rule callable repr (line 621-623). A lambda would show as
`<lambda>` and obscure the diagnosis. A named function shows as
`_eq_to_tr_bpsd_check` and lets us add a docstring.

### D-3: Layer-D negative test in scope

**Chosen**: include `test_eq_to_tr_rule_dormant_on_default` —
pipeline runs without `MONO_LIB_PATH` set, assert the rule does
NOT appear in `coupling_applied`.
**Rejected**: rely on Phase 2b's Layer-C overlay smoke alone.
**Why**: Codex 2026-05-26 design review MED-6 noted that the
overlay mechanism is tested at Layer-C but not exercised through
Layer-D (TotPipeline level). A future refactor of
`_detect_mono()` / `_build_active_rules()` could silently activate
the rule on non-mono; the negative test pins that contract at
the user-facing entry point.

### D-4: Lifecycle ordering — verify safe at TotPipeline phase

**Documented invariant**: in `TotPipeline.run_pipeline`, the
`("eq","tr")` verify rule fires AFTER `Trlib()` is instantiated
(which calls `tr_init`) but BEFORE `tr.run()`. This is later in
tr's lifecycle than the Layer-C smoke (which has tr_init inside
the tot_init bundle, BEFORE eq pushes BPSD).

**Empirical resolution**: the design author verified on 2026-05-26
that on the mono image, calling
`eq_init → eq_run(1, MODELG=3, KNAMEQ=eqdata-HT6M) → tr_init →
tr_check_bpsd_pull` returns `ok=1`. The broker storage survives
tr_init (tr_init sets up trcomm + ALLOCATE_TRCOMM but does NOT
clear the bpsd broker slots that eq just pushed).

**Scope of the empirical resolution** (Codex 2026-05-26 spec review
LOW-1): the probe covers exactly the ordering used by §7.2 / §7.3,
which is the ordering `TotPipeline.run_pipeline([("eq",...),
("tr",...)])` produces when neither tr nor eq has been instantiated
beforehand. `TotPipeline.set_param("tr:...", ...)` lazily
instantiates `Trlib` (`pipeline.py:_ensure_module`), so a user who
sets a tr param before running the pipeline would get a different
ordering — but PR-B's tests never call `set_param("tr:...", ...)`,
so the probed ordering is the only one PR-B's test contract
exercises. The D-4 invariant is therefore scoped to that ordering;
future PRs that exercise tr-first orderings need their own probe.

**Why this matters**: Codex 2026-05-26 design review MED-7
flagged this as a concrete unknown. The empirical probe resolves it
before implementation — `Trlib.check_bpsd_pull()` is correct at
the verify-firing phase.

## 5. Architecture

```
python/totlib/
  pipeline.py                          # MODIFIED — D-1, D-2: populate
                                       #   _MONO_ONLY_RULES (~10-line diff)
  tests/
    test_mono_pipeline_coupling.py     # NEW — D-3: 2 test cases
  README.md                            # MODIFIED — 1-paragraph note

.github/workflows/
  python-tests.yml                     # MODIFIED — new pytest step in
                                       #   mono build (Linux) job
```

No new top-level files. No Fortran changes. No C ABI changes.

## 6. Rule definition

```python
# python/totlib/pipeline.py — append above _MONO_ONLY_RULES

def _eq_to_tr_bpsd_check(trlib_inst) -> bool:
    """Verify eq's BPSD push is visible to tr (mono image only).

    Returns True iff Trlib.check_bpsd_pull() finds the device /
    equ1D / metric1D slots that eq pushed during eq_run(1). On the
    default per-module image this would always return False because
    each per-module .so has private bpsd storage — but the rule
    only activates when _detect_mono() == True so the path is never
    exercised against the default image.
    """
    return trlib_inst.check_bpsd_pull()


_MONO_ONLY_RULES: Dict[Tuple[str, str], List[CouplingRule]] = {
    ("eq", "tr"): [
        CouplingRule(
            kind="verify",
            verify=_eq_to_tr_bpsd_check,
            doc="eq -> tr BPSD broker round-trip (mono image only)",
        ),
    ],
}
```

The existing header comment block above `_MONO_ONLY_RULES`
(lines 294-327) documents the Phase 2b restraint that this commit
lifts. The header is rewritten in PR-B to reflect the new state.

## 7. Tests

### 7.1 `python/totlib/tests/test_mono_pipeline_coupling.py` (new)

Module-level setup:

```python
"""Layer-D — TotPipeline rule firing on the mono image.

Phase 2c PR-B (#208). Drives eq -> tr through
TotPipeline.run_pipeline on the mono image and asserts the
("eq","tr") verify rule fires (mono) / stays dormant (default).

Process isolation: pytest.mark.forked module-level. The mono .so
carries module-level state across calls; without forking,
tot/eq/tr init state from a prior test could leak into this
test's pipeline.
"""
import os, shutil, sys, tempfile, unittest
from pathlib import Path
import pytest

pytestmark = [pytest.mark.forked]

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

_EQDATA_FIXTURE = (
    REPO / "python" / "totlib" / "tests" / "fixtures" / "eqdata-HT6M"
)

def _mono_path() -> str:
    p = os.environ.get("MONO_LIB_PATH", "")
    return p if p and os.path.exists(p) else ""
```

### 7.2 Happy-path test (mono)

```python
@unittest.skipUnless(
    _mono_path() and _EQDATA_FIXTURE.exists(),
    "MONO_LIB_PATH and/or eqdata-HT6M fixture missing",
)
class TestEqToTrPipelineCoupling(unittest.TestCase):

    def test_eq_to_tr_bpsd_pipeline_succeeds_on_mono(self):
        """Layer-D happy path: pipeline runs eq -> tr on mono,
        ("eq","tr") verify rule fires, broker round-trip succeeds.
        """
        import _runtime_mode
        from totlib import TotPipeline

        _runtime_mode.mono_lib_path.cache_clear()
        result = None
        with tempfile.TemporaryDirectory(prefix="prb_") as td:
            shutil.copy2(_EQDATA_FIXTURE, Path(td) / "eqdata-HT6M")
            prev = os.getcwd()
            os.chdir(td)
            try:
                with TotPipeline() as p:
                    p.set_param("eq:MODELG", 3.0)
                    p.set_param("eq:KNAMEQ", "eqdata-HT6M")
                    result = p.run_pipeline([
                        ("eq", {"mode": 1}),
                        ("tr", {"ntmax": 1}),
                    ])
            finally:
                os.chdir(prev)

        # Assertions OUTSIDE the `with TotPipeline()` block (Codex
        # 2026-05-26 LOW-5: a __exit__ failure should not be able
        # to mask the assertion).
        self.assertIsNotNone(result, "run_pipeline returned None")
        tr_step = result.last("tr")
        self.assertIn(
            "eq -> tr BPSD broker round-trip",
            " ".join(tr_step.coupling_applied),
            f"verify rule did not fire; coupling_applied="
            f"{tr_step.coupling_applied}",
        )
```

### 7.3 Negative-path test (default per-module)

```python
def _default_per_module_so_present() -> bool:
    """Return True iff every per-module .so the negative test
    actually loads via the resolution chain exists at its default
    repo path. eqlib/trlib/totlib wrappers each look in
    <repo>/<mod>/lib<mod>api.so (priority 2 in PR-A's spec §D-5),
    so we check those directly. Per Codex 2026-05-26 spec round-3
    review, TOTLIB_PATH is NOT included here: eqlib and trlib do
    not honor it (they use EQLIB_PATH / TRLIB_PATH respectively),
    so gating on it would either over-skip (false-negative on
    TOTLIB_PATH-only setups) or under-cover (false-positive when
    eq/tr .so are missing).
    """
    return all(
        (REPO / mod / f"lib{name}.so").exists()
        for mod, name in (
            ("eq", "eqapi"),
            ("tr", "trapi"),
            ("tot", "totapi"),
        )
    )


class TestEqToTrRuleDormantOnDefault(unittest.TestCase):
    """Layer-D negative path: rule must NOT fire on the default
    per-module image even though _MONO_ONLY_RULES is now populated.

    Pinned per Codex 2026-05-26 design review MED-6: if a future
    refactor of _detect_mono() or _build_active_rules() silently
    activates the overlay on non-mono, this test catches it.

    Skip-gated on the per-module .so files that eqlib / trlib /
    totlib will actually load via their resolution chain when
    MONO_LIB_PATH is unset (Codex 2026-05-26 spec review LOW-2:
    the wrappers don't all honor TOTLIB_PATH; each has its own
    <MOD>LIB_PATH or repo-default).
    """

    @unittest.skipUnless(
        _default_per_module_so_present() and _EQDATA_FIXTURE.exists(),
        "per-module .so (eq/libeqapi.so, tr/libtrapi.so, "
        "tot/libtotapi.so) and/or eqdata-HT6M fixture missing; "
        "build via setup.sh or `make -C <mod> lib<mod>api.so`",
    )
    def test_eq_to_tr_rule_dormant_on_default(self):
        import _runtime_mode
        from totlib import TotPipeline

        # Unset MONO_LIB_PATH so the wrappers route to per-module
        # .so files via their priority-1 env vars (EQLIB_PATH /
        # TRLIB_PATH / TOTLIB_PATH) or priority-2 repo defaults.
        # _detect_mono() reads tot_is_mono() from the totlib
        # wrapper's loaded image, which is the default
        # libtotapi.so, returning 0 — so the overlay stays inactive.
        original_mono = os.environ.pop("MONO_LIB_PATH", None)
        _runtime_mode.mono_lib_path.cache_clear()

        result = None
        try:
            with tempfile.TemporaryDirectory(prefix="prb_neg_") as td:
                shutil.copy2(_EQDATA_FIXTURE, Path(td) / "eqdata-HT6M")
                prev = os.getcwd()
                os.chdir(td)
                try:
                    with TotPipeline() as p:
                        p.set_param("eq:MODELG", 3.0)
                        p.set_param("eq:KNAMEQ", "eqdata-HT6M")
                        # IMPORTANT: this is expected to SUCCEED.
                        # On default per-module .so, eq's BPSD push
                        # lands in libeqapi's private storage; tr
                        # reads from libtrapi's private storage. The
                        # rule MUST stay dormant or the pipeline
                        # would fail for the wrong reason (the
                        # verify would return False).
                        result = p.run_pipeline([
                            ("eq", {"mode": 1}),
                            ("tr", {"ntmax": 1}),
                        ])
                finally:
                    os.chdir(prev)
        finally:
            if original_mono is not None:
                os.environ["MONO_LIB_PATH"] = original_mono
            _runtime_mode.mono_lib_path.cache_clear()

        self.assertIsNotNone(result, "run_pipeline returned None")
        tr_step = result.last("tr")
        self.assertNotIn(
            "eq -> tr BPSD broker round-trip",
            " ".join(tr_step.coupling_applied),
            f"rule should NOT fire on default per-module image; "
            f"coupling_applied={tr_step.coupling_applied}",
        )
```

## 8. CI

Append this step to the `mono build (Linux libtotapi_mono.so)` job
in `.github/workflows/python-tests.yml`, immediately after PR-A's
`Mono routing sanity (Phase 2c PR-A)` step:

```yaml
      - name: Mono pipeline coupling (Phase 2c PR-B)
        # #208 PR-B — drives eq -> tr through TotPipeline.run_pipeline
        # on the mono image and asserts the ("eq","tr") verify rule
        # fires (TestEqToTrPipelineCoupling). Also exercises the
        # negative case via TestEqToTrRuleDormantOnDefault — that
        # test skip-gates on the per-module .so files at the repo
        # default paths (eq/libeqapi.so, tr/libtrapi.so,
        # tot/libtotapi.so), which the per-module build steps
        # earlier in this job have already produced.
        #
        # TOTLIB_PATH is set so the totlib wrapper picks the
        # default libtotapi.so from the workspace consistently with
        # other tests in this job. eqlib / trlib do NOT honor
        # TOTLIB_PATH; they resolve via the repo default at
        # workspace/eq/libeqapi.so etc.
        env:
          MONO_LIB_PATH: ${{ github.workspace }}/tot/libtotapi_mono.so
          TOTLIB_PATH: ${{ github.workspace }}/tot/libtotapi.so
          PYTHONPATH: python
        run: |
          python -m pytest python/totlib/tests/test_mono_pipeline_coupling.py \
                 --forked --timeout=120 --timeout-method=signal -v
```

Both test classes run in the same step. `MONO_LIB_PATH` lets the
happy-path class execute against the mono image; the negative class
ignores `MONO_LIB_PATH` per its own `os.environ.pop` and gates on
the per-module `.so` files which the mono-build job has already
produced earlier (per-module build chain runs before the mono build
in `python-tests.yml`). The default `libtotapi.so` artifact is also
present from PR #207's "Build default libtotapi.so" step, and
`TOTLIB_PATH` is set so the totlib wrapper picks it consistently.

## 9. Documentation

Update `python/totlib/README.md` mono routing section. After the
existing PR-A paragraph, append:

```markdown
**Phase 2c PR-B (#208 follow-up)**: the `("eq","tr")` BPSD coupling
rule is now active in `_MONO_ONLY_RULES`. When `MONO_LIB_PATH` is
set, `TotPipeline.run_pipeline([("eq", ...), ("tr", ...)])` runs
the rule via `Trlib.check_bpsd_pull()` and reports it in
`PipelineResult.last("tr").coupling_applied`. On the default
per-module image the rule stays dormant — eq and tr each have
their own private bpsd storage so cross-module verification is
meaningless there.
```

## 10. Risks

### R-1: tr_init wiping the broker on the mono image

**Status**: RESOLVED empirically before implementation (see D-4).
Probe on 2026-05-26 confirmed `ok=1` from `tr_check_bpsd_pull`
after `eq_init → eq_run(1) → tr_init` ordering. If a future
Fortran change to `tr_init` adds explicit broker reset, the
PR-B happy-path test will fail loud — that's intentional regression
coverage.

### R-2: Fixture chdir under pytest-forked

Each test forks its own subprocess; `os.chdir` is process-local.
No cross-test interference even within the same pytest run. The
test uses `try/finally` to chdir back, defending against future
runs without `--forked`.

### R-3: Rule fires before tr.run, not after

The verify rule asserts the broker round-trip BEFORE tr advances
its transport solver. This is the design intent — we are verifying
the eq→tr handoff, not the tr step itself. A subtle reader may
expect `tr.run()` to have happened first; the rule's docstring
documents the timing.

## 11. Acceptance criteria

PR-B is ready to merge when:

1. `python/totlib/pipeline.py::_MONO_ONLY_RULES` contains the
   `("eq","tr")` verify rule defined in §6.
2. `python/totlib/tests/test_mono_pipeline_coupling.py` exists
   with the two test cases from §7.
3. Both tests pass locally with `pytest --forked --timeout=120
   --timeout-method=signal`. The happy-path test requires
   `MONO_LIB_PATH` set. The negative test requires the per-module
   `.so` files at the repo default paths (`eq/libeqapi.so`,
   `tr/libtrapi.so`, `tot/libtotapi.so`); `TOTLIB_PATH` is optional
   and only steers the totlib wrapper if set.
4. CI's mono-build job runs the new test step green.
5. 1e-10 equivalence
   (`python/totlib/tests/test_equivalence.py`) preserved.
6. PR-A's `test_mono_routing.py` (9 tests) stays green — PR-B does
   not regress the loader contract.
7. `_MONO_ONLY_RULES` activation is conditional on `_detect_mono()
   == True` — the existing overlay mechanism is untouched.
8. Both in-house and Codex pre-push reviews HIGH/MED-free.

## 12. References

- Parent issue: #208 (Phase 2c umbrella — closes when PR-B lands)
- Phase 2 umbrella: #201 (also closes)
- Predecessor PRs: #206 (Phase 2a), #207 (Phase 2b), #211 (#209
  cascade), #212 (Phase 2c PR-A)
- Predecessor specs:
  - `docs/superpowers/specs/2026-05-03-l7b-ii-bpsd-broker-coupling-design.md`
  - `docs/superpowers/specs/2026-05-18-l7b-ii-phase-2b-design.md`
  - `docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md`
- Codex design review 2026-05-26 round 1 (pre-spec): MED-7
  resolved empirically (broker survives tr_init); MED-6 (Layer-D
  negative test) folded into scope per user choice; LOW-5 (assert
  outside `with`) folded into §7.2 + §7.3.
- Codex design review 2026-05-26 round 2 (post-spec): SHIP IT with
  2 LOW clarifications — D-4 scope narrowed to the §7.2/§7.3
  ordering (LOW-1); negative-test skip-gate changed from
  `TOTLIB_PATH` env to per-module `.so` existence check (LOW-2).
- Codex design review 2026-05-26 round 3 (spec polish): LOW — the
  round-2 LOW-2 fix still left a vestigial `TOTLIB_PATH` branch in
  the helper. Removed entirely; helper now gates only on
  `<repo>/{eq/libeqapi.so,tr/libtrapi.so,tot/libtotapi.so}`.
- Codex design review 2026-05-26 round 4 (final sweep): LOW × 3 —
  cleared residual `TOTLIB_PATH`-centric phrasing in §7.3 docstring,
  §8 CI step comment, §8 narrative, and §11 acceptance criterion 3.
  CI step env block keeps `TOTLIB_PATH` set (steers totlib's
  priority-1 fallback) but the docstring/comments now correctly
  describe the negative test's skip-gate as per-module .so
  existence, not env-var presence.
- Memory: `feedback_codex_worktree_sharing.md` (subagent dispatch
  worktree pinning — applies to PR-B execution too).
