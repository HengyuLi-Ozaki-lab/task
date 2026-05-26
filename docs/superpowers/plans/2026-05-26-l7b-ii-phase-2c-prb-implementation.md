# L-7b-ii Phase 2c PR-B — eq→tr rule activation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate the `("eq","tr")` BPSD coupling rule in `TotPipeline._MONO_ONLY_RULES` (now possible after PR-A's MONO_LIB_PATH plumbing landed) and add a Layer-D integration test that exercises the rule on the mono image + asserts it stays dormant on the default per-module path. This is the terminal step of Phase 2c and closes both #208 and #201.

**Architecture:** Single `def _eq_to_tr_bpsd_check(trlib_inst) -> bool` at module scope in `python/totlib/pipeline.py`, referenced from a `CouplingRule(kind="verify", ...)` entry in `_MONO_ONLY_RULES`. The verify rule fires after `_ensure_module("tr")` (which calls `tr_init`) but before `tr.run()` — empirically proven safe by a probe in spec §4 D-4. New test file at `python/totlib/tests/test_mono_pipeline_coupling.py` with two cases: happy path on mono + dormant on default per-module.

**Tech Stack:** Python 3.10+, pytest 8 + pytest-forked, `Trlib.check_bpsd_pull()` (already exists from PR #188), no Fortran or C ABI changes.

**Spec:** `docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md` (Codex 5-round SHIP IT, develop @ `21c18a2d`).

**Branch base:** `origin/develop` at `21c18a2d` or later.

**Subagent-worktree discipline (recurring incident class, see `feedback_codex_worktree_sharing.md`):** every command in this plan that runs `git` or `make` is shown with an explicit absolute-path prefix or `-C` flag. Implementer subagents MUST NOT trust an implicit `cd` between Bash tool calls. The controller MUST `git status` on the main checkout after every subagent dispatch to catch misplaced commits.

---

## File Structure

**Created:**
- `python/totlib/tests/test_mono_pipeline_coupling.py` — 2 Layer-D test cases (~140 lines including docstrings + fixtures).

**Modified:**
- `python/totlib/pipeline.py` — add named callable + populate `_MONO_ONLY_RULES` (~15-line diff in two adjacent blocks).
- `python/totlib/README.md` — append a "Phase 2c PR-B" paragraph to the existing Mono routing section (~10 lines).
- `.github/workflows/python-tests.yml` — append a step to the `mono build (Linux libtotapi_mono.so)` job (~18 lines).

**Untouched (load-bearing — do NOT change):**
- `python/totlib/pipeline.py::_build_active_rules()` / `_detect_mono()` — Phase 2b overlay mechanism stays as-is (spec §11 AC#7).
- Any Fortran source.
- Any `_ffi.py` loader logic — PR-A's loader contract stays untouched (spec §11 AC#6).

---

## Task 0: Worktree + baseline build

**Files:** none yet — environment setup.

Working directory throughout this task: `/Users/k-yoshimi/Dropbox/cursor/task` (main checkout). The new worktree path will be `/Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb`.

- [ ] **Step 1: Sync develop**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git fetch origin develop --quiet
git checkout develop
git pull --quiet
git log --oneline -1
```

Expected: HEAD ≥ `21c18a2d docs(spec): L-7b-ii Phase 2c PR-B — eq->tr rule activation design`.

- [ ] **Step 2: Create worktree**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git worktree add .claude/worktrees/l7b-ii-phase-2c-prb \
                  -b l7b-ii-phase-2c-prb origin/develop
```

Expected: worktree created on new branch tracking origin/develop.

- [ ] **Step 3: Copy build-config artifacts (gitignored, copied from main checkout)**

```bash
cp /Users/k-yoshimi/Dropbox/cursor/task/make.header \
   /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/make.header
cp /Users/k-yoshimi/Dropbox/cursor/task/mtxp/make.mtxp \
   /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/mtxp/make.mtxp
ls -l /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/make.header \
      /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/mtxp/make.mtxp
```

Expected: both files present.

- [ ] **Step 4: Verify bpsd symlink at the worktrees parent**

```bash
ls -la /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/bpsd
```

Expected: symlink resolves to `/Users/k-yoshimi/Dropbox/cursor/bpsd` (already set up in prior sessions; if missing, create with `ln -s /Users/k-yoshimi/Dropbox/cursor/bpsd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/bpsd`).

- [ ] **Step 5: Full PIC build chain**

This matches the CI workflow order. From the worktree root:

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
make -C lib libtask_pic.a libgrf_pic.a libmds_pic.a
make -C mtxp libmtxnompi_pic.o libmtxbnd_pic.o
make -C tr  bpsd_pic
make -C pl  libpl_noeq_pic
make -C eq  libeq_pic.a
make -C pl  libpl_pic.a
make -C dp  libdp_pic.a
make -C ob  libob_pic.a
make -C open-adas/adf11/adf11-lib lib-adf11_pic.a
make -C adpost lib-adpost_pic.a
# Build BOTH the per-module .so files needed by the negative test
# AND the mono image needed by the happy test:
make -C eq  libeqapi.so
make -C tr  libtrapi.so
make -C tot libtotapi.so libtotapi_mono.so
ls -l eq/libeqapi.so tr/libtrapi.so tot/libtotapi.so tot/libtotapi_mono.so
```

Expected: all four .so files present and non-empty.

- [ ] **Step 6: Baseline smoke — existing mono tests still green on this worktree**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
export TOTLIB_PATH="$PWD/tot/libtotapi.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    totlib/tests/test_mono_bpsd_smoke.py \
    totlib/tests/test_tot_init_eq_api_cascade.py \
    totlib/tests/test_mono_routing.py -v 2>&1) | tail -20
```

Expected: 17 passed (3 mono smoke + 2 cascade + 9 routing + 3 dormant placeholders if any — confirm count matches what's in PR-A's HEAD). `test_close_raises_exception_group_when_multiple_modules_fail` is NOT in the suites above so the pre-existing Python 3.10 failure does not appear here.

---

## Task 1: Populate `_MONO_ONLY_RULES` + happy-path test (TDD)

**Files:**
- Create: `/Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/python/totlib/tests/test_mono_pipeline_coupling.py`
- Modify: `/Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/python/totlib/pipeline.py`

- [ ] **Step 1: Write the failing happy-path test**

Create `python/totlib/tests/test_mono_pipeline_coupling.py` (full content; this file does not exist yet):

```python
"""Layer-D — TotPipeline rule firing on the mono image.

Phase 2c PR-B (#208). Drives eq -> tr through
TotPipeline.run_pipeline on the mono image and asserts the
("eq","tr") verify rule fires (mono) / stays dormant (default).

Process isolation: pytest.mark.forked module-level. The mono .so
carries module-level state across calls; without forking,
tot/eq/tr init state from a prior test could leak into this
test's pipeline.

Spec: docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
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


@unittest.skipUnless(
    _mono_path() and _EQDATA_FIXTURE.exists(),
    "MONO_LIB_PATH and/or eqdata-HT6M fixture missing; "
    "build with `make -C tot libtotapi_mono.so` and ensure PR #199 "
    "fixture is in place",
)
class TestEqToTrPipelineCoupling(unittest.TestCase):
    """Layer-D happy path: pipeline runs eq -> tr on mono, the
    ("eq","tr") verify rule fires, broker round-trip succeeds.
    """

    def test_eq_to_tr_bpsd_pipeline_succeeds_on_mono(self):
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it FAILS for the right reason**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    totlib/tests/test_mono_pipeline_coupling.py::TestEqToTrPipelineCoupling -v 2>&1) | tail -15
```

Expected: FAIL with an `AssertionError` saying "verify rule did not fire; coupling_applied=[]". The rule isn't populated yet — `_MONO_ONLY_RULES` is still `{}` per Phase 2b restraint.

- [ ] **Step 3: Modify `python/totlib/pipeline.py` — add the named callable and populate the rule**

Locate `_MONO_ONLY_RULES` (around line 328). Replace the existing header comment block AND the empty dict with:

```python
# ------------------------------------------------------------------
# Mono-only coupling rules
# ------------------------------------------------------------------
# Rules in this dict are activated ONLY when the loaded
# libtotapi*.so is the monolithic build (tot_is_mono() == 1). On
# the default per-module .so path each per-module library has
# private bpsd storage, so cross-module BPSD verification is
# meaningless there and these rules stay dormant via the
# _detect_mono() / _build_active_rules() overlay mechanism that
# Phase 2b put in place.
#
# Phase 2c PR-A (#212) plumbed the wrappers to honor MONO_LIB_PATH
# so all 6 wrappers can route to the same mono image. PR-B (this
# commit) activates the ("eq","tr") rule that PR-A's plumbing
# enables.
#
# Adding a new rule here?
#   1. Define a named module-level callable (not a lambda) so
#      pipeline.run_pipeline error messages show a meaningful
#      __qualname__ when the verify fails.
#   2. Verify the timing is safe at the rule-firing phase
#      (run_pipeline fires verify rules AFTER current-module init
#      but BEFORE current-module run — see lines 610-631).
#   3. Add a Layer-D integration test covering both the happy
#      mono path AND the dormant non-mono path (see
#      python/totlib/tests/test_mono_pipeline_coupling.py for
#      the ("eq","tr") example).

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

- [ ] **Step 4: Run the test to verify it now PASSES**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    totlib/tests/test_mono_pipeline_coupling.py::TestEqToTrPipelineCoupling -v 2>&1) | tail -10
```

Expected: 1 passed.

- [ ] **Step 5: Verify no regression in existing totlib tests**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
export TOTLIB_PATH="$PWD/tot/libtotapi.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    totlib/tests/ 2>&1) | tail -8
```

Expected: existing tests stay green except the pre-existing Python 3.10 `test_close_raises_exception_group_when_multiple_modules_fail` (NameError: ExceptionGroup). 1 failed + (164 + 1 new) = 166 passed acceptable.

- [ ] **Step 6: Commit**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
git add python/totlib/pipeline.py python/totlib/tests/test_mono_pipeline_coupling.py
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb commit -m "$(cat <<'EOF'
feat(totlib): activate ("eq","tr") BPSD verify rule on mono (#208 PR-B)

Populates TotPipeline._MONO_ONLY_RULES with a single verify-kind
CouplingRule that wraps Trlib.check_bpsd_pull(). The rule fires
when TotPipeline.run_pipeline([("eq",...),("tr",...)]) is invoked
against the mono image (_detect_mono() == True after PR-A's
MONO_LIB_PATH routing); it stays dormant on the default per-module
image via the existing _build_active_rules() overlay.

The rule body is a named module-level callable
(_eq_to_tr_bpsd_check) per spec §4 D-2 so pipeline error messages
show a meaningful __qualname__ instead of `<lambda>`.

Spec §4 D-4 empirical resolution: `eq_init -> eq_run(1) -> tr_init
-> tr_check_bpsd_pull` returns ok=1 on the mono image; tr_init
does NOT clear the bpsd broker slots that eq just pushed. This is
the ordering TotPipeline.run_pipeline exercises with no prior
tr-side set_param.

First Layer-D test
(test_mono_pipeline_coupling.py::TestEqToTrPipelineCoupling) drives
the full pipeline through eq -> tr on mono and asserts the rule
appears in result.last("tr").coupling_applied. Negative test
follows in the next commit.

Spec: docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Negative-path test

**Files:**
- Modify: `/Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/python/totlib/tests/test_mono_pipeline_coupling.py`

- [ ] **Step 1: Append the helper + negative test class to the existing test file**

Open `python/totlib/tests/test_mono_pipeline_coupling.py` and APPEND (above the `if __name__ == "__main__"` block):

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


@unittest.skipUnless(
    _default_per_module_so_present() and _EQDATA_FIXTURE.exists(),
    "per-module .so (eq/libeqapi.so, tr/libtrapi.so, "
    "tot/libtotapi.so) and/or eqdata-HT6M fixture missing; "
    "build via setup.sh or `make -C <mod> lib<mod>api.so`",
)
class TestEqToTrRuleDormantOnDefault(unittest.TestCase):
    """Layer-D negative path: rule must NOT fire on the default
    per-module image even though _MONO_ONLY_RULES is now populated.

    Pinned per Codex 2026-05-26 design review MED-6: if a future
    refactor of _detect_mono() or _build_active_rules() silently
    activates the overlay on non-mono, this test catches it.
    """

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

- [ ] **Step 2: Run both tests to verify both pass**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
export TOTLIB_PATH="$PWD/tot/libtotapi.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    totlib/tests/test_mono_pipeline_coupling.py -v 2>&1) | tail -10
```

Expected: 2 passed (TestEqToTrPipelineCoupling::test_eq_to_tr_bpsd_pipeline_succeeds_on_mono + TestEqToTrRuleDormantOnDefault::test_eq_to_tr_rule_dormant_on_default).

- [ ] **Step 3: Verify per-module wrapper tests stay green (regression check)**

The negative test exercises eqlib's and trlib's per-module load path. If that path is broken, the negative test would have failed in Step 2, but verify the per-module suites too:

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
unset MONO_LIB_PATH
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    eqlib/tests/ trlib/tests/ 2>&1) | tail -5
```

Expected: eqlib + trlib both green (47 + 57 ≈ 104 pass with skips). Pre-existing equiv failures in fplib/wrxlib (#213) are NOT in scope here.

- [ ] **Step 4: Commit**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
git add python/totlib/tests/test_mono_pipeline_coupling.py
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb commit -m "$(cat <<'EOF'
test(totlib): negative path — rule dormant on default per-module (#208 PR-B)

Adds TestEqToTrRuleDormantOnDefault to
python/totlib/tests/test_mono_pipeline_coupling.py. Asserts the
inverse contract to the happy-path test in the prior commit:
when MONO_LIB_PATH is unset, TotPipeline.run_pipeline([("eq",..),
("tr",..)]) completes without the ("eq","tr") verify rule firing.
Pipeline succeeds because the rule stays dormant via the Phase 2b
overlay mechanism (_detect_mono() returns False on the default
per-module image).

Skip-gate is _default_per_module_so_present() — checks the actual
.so paths eqlib/trlib/totlib will load via priority-2 repo
defaults. Per Codex 2026-05-26 spec round-3 review, TOTLIB_PATH
env var is NOT in the gate (eqlib/trlib don't honor it).

Pin for Codex 2026-05-26 design review MED-6: if a future refactor
of _detect_mono() / _build_active_rules() silently activates the
overlay on non-mono, this test catches it at the user-facing
TotPipeline entry point.

Spec: docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: CI workflow extension

**Files:**
- Modify: `/Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/.github/workflows/python-tests.yml`

- [ ] **Step 1: Locate the PR-A `Mono routing sanity (Phase 2c PR-A)` step**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
grep -nE "Mono routing sanity|test_mono_routing.py" .github/workflows/python-tests.yml
```

Note the line number of the existing step. The new PR-B step goes IMMEDIATELY AFTER it (same job: `mono build (Linux libtotapi_mono.so)`).

- [ ] **Step 2: Append the new step**

Insert this step in `.github/workflows/python-tests.yml` immediately after the existing `Mono routing sanity (Phase 2c PR-A)` step. Match the indentation (6 spaces before `- name:`):

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

- [ ] **Step 3: Verify yaml parses**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
python -c "import yaml; yaml.safe_load(open('.github/workflows/python-tests.yml')); print('yaml ok')"
```

Expected: `yaml ok`.

- [ ] **Step 4: Commit**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
git add .github/workflows/python-tests.yml
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb commit -m "$(cat <<'EOF'
ci(python-tests): mono pipeline coupling step (#208 PR-B)

Extends the mono build (Linux libtotapi_mono.so) job to run
python/totlib/tests/test_mono_pipeline_coupling.py with both
MONO_LIB_PATH and TOTLIB_PATH set so both test classes execute.
The default libtotapi.so and per-module .so files are already
built earlier in this job; PR-B reuses them.

Step is added directly after PR #212's "Mono routing sanity"
step in the same job.

Spec: docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: README documentation

**Files:**
- Modify: `/Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb/python/totlib/README.md`

- [ ] **Step 1: Append the PR-B paragraph to the Mono routing section**

Open `python/totlib/README.md`. Find the "Mono routing (Phase 2c PR-A, #208)" section (added by PR #212). At the END of that section, before the next `## ...` heading (or EOF if it's the last section), append:

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

- [ ] **Step 2: Sanity check the markdown renders**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
grep -nA2 "Phase 2c PR-B" python/totlib/README.md | head -10
```

Expected: the new paragraph appears once, no nested-fence breakage. (No formal markdown linter in this repo; visual check is sufficient.)

- [ ] **Step 3: Commit**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
git add python/totlib/README.md
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb commit -m "$(cat <<'EOF'
docs(totlib): note ("eq","tr") rule activation in README (#208 PR-B)

Appends a one-paragraph note to the existing Mono routing section
that PR #212 added. Documents that the eq -> tr BPSD coupling rule
now fires through TotPipeline.run_pipeline when MONO_LIB_PATH is
set, and stays dormant on the default per-module image.

No code or behavior changes — pure documentation.

Spec: docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Pre-push gate, push, PR, Bugbot wait

**Files:** none edited; controller-side workflow.

- [ ] **Step 1: Controller-side tripwire — main checkout is clean**

Per `feedback_codex_worktree_sharing.md`, after every subagent dispatch run this:

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git status --short && git branch --show-current
git log --oneline origin/develop..HEAD
```

Expected: branch=develop; `origin/develop..HEAD` is empty (no commits accidentally landed on main checkout's develop). If commits appear: recover via `cd <worktree>; git cherry-pick <orphan>; cd <main>; git reset --hard origin/develop`.

- [ ] **Step 2: Final cumulative test pass from the worktree**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
export TOTLIB_PATH="$PWD/tot/libtotapi.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    totlib/tests/ 2>&1) | tail -10
```

Expected: 1 failed (the pre-existing Python 3.10 ExceptionGroup test) + N passed where N includes the 2 new PR-B tests. The 1 fail is documented in PR #211 / #212 history and is NOT a PR-B regression.

- [ ] **Step 3: Launch BOTH reviewers in parallel on the cumulative diff**

In a single tool-call message, fire:

- `Agent(subagent_type="general-purpose", model="sonnet", description="In-house cumulative review of PR-B", prompt=...)` — anchor: plan adherence to this plan + spec §11 acceptance criteria 1-7.
- `Agent(subagent_type="codex:codex-rescue", description="Codex independent review of PR-B", prompt=...)` — anchor: cross-cutting code quality, lifecycle correctness, test isolation.

Reviewer prompts MUST give them: working dir = `/Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb`, branch = `l7b-ii-phase-2c-prb`, HEAD = the latest commit, base = `origin/develop @ 21c18a2d`, spec path = `docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md`.

Paste HIGH / MED findings back to the user before continuing. Address findings if any; re-review.

- [ ] **Step 4: Write the pre-push marker**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
HEAD_SHA=$(git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb rev-parse HEAD)
touch "$(git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb rev-parse --git-common-dir)/REVIEW_OK_$HEAD_SHA"
ls "$(git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb rev-parse --git-common-dir)/REVIEW_OK_$HEAD_SHA"
```

Expected: marker file present at `.git/REVIEW_OK_<sha>`.

- [ ] **Step 5: Push**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb
unset GITHUB_TOKEN
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/l7b-ii-phase-2c-prb push -u origin l7b-ii-phase-2c-prb
```

Expected: `pre-push: review marker present — OK` + new remote branch.

- [ ] **Step 6: Create the PR**

```bash
unset GITHUB_TOKEN
gh pr create --base develop --title "feat(totlib): activate eq->tr BPSD verify rule on mono (#208 Phase 2c PR-B)" --body "$(cat <<'EOF'
## Summary

Closes #208 (Phase 2c umbrella) and #201 (Phase 2 umbrella).

Activates the `("eq","tr")` BPSD coupling rule in
`TotPipeline._MONO_ONLY_RULES` — now possible after PR-A's
`MONO_LIB_PATH` plumbing landed (#212). Adds a Layer-D
integration test that drives `TotPipeline.run_pipeline([(eq,
...), (tr, ...)])` on the mono image AND asserts the rule stays
dormant on the default per-module image.

## What's in this PR (4 commits)

1. **`feat(totlib): activate ("eq","tr") BPSD verify rule on mono`** — populates `_MONO_ONLY_RULES` with the verify rule; named module-level callable (`_eq_to_tr_bpsd_check`) so error-message `__qualname__` is meaningful; Layer-D happy-path test.
2. **`test(totlib): negative path — rule dormant on default per-module`** — adds the inverse contract test pinning Codex MED-6.
3. **`ci(python-tests): mono pipeline coupling step`** — extends mono-build job to run the new test with both env vars set.
4. **`docs(totlib): note ("eq","tr") rule activation in README`** — 1-paragraph note appended to PR-A's mono routing section.

## Acceptance (spec §11)

- [x] `_MONO_ONLY_RULES[("eq","tr")]` populated per §6.
- [x] `test_mono_pipeline_coupling.py` with 2 cases (happy + dormant) per §7.
- [x] Both tests pass locally with `pytest --forked`.
- [x] CI step extends mono-build job per §8.
- [x] 1e-10 equivalence preserved (`test_equivalence.py` untouched).
- [x] PR-A `test_mono_routing.py` stays green (9 tests).
- [x] `_build_active_rules()` / `_detect_mono()` untouched — verified by `git diff origin/develop..HEAD -- python/totlib/pipeline.py` showing only the rule dict + new callable.
- [x] Both pre-push reviews HIGH/MED-free.

## Tests

- New `python/totlib/tests/test_mono_pipeline_coupling.py`: 2 tests, both pass locally + via `pytest --forked`. Portable Linux + macOS.
- Existing totlib tests unaffected (the 1 pre-existing Python-3.10 `ExceptionGroup` failure is the same as on develop baseline — see PR #211/#212 history, unrelated).

## Out of scope

- Other module-pair rules (e.g. ("tr","fp")) — deferred to future PRs.
- Restructuring `_MONO_ONLY_RULES` for per-rule activation conditions.
- Fortran source changes.
- `tot/tot_api.h` updates (PR-A already documented mono routing in the header).

## Spec + Plan

- Spec: `docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md` (Codex 5-round SHIP IT).
- Plan: `docs/superpowers/plans/2026-05-26-l7b-ii-phase-2c-prb-implementation.md`.

## Process notes

Subagent-driven implementation per `superpowers:subagent-driven-development`. Plan tasks 1-4 dispatched as fresh implementer subagents with two-stage review (spec compliance + code quality) per task. Every command in the plan uses `git -C <abs-path>` or `cd <abs-path>` per `feedback_codex_worktree_sharing.md` to defuse the recurring "subagent commits on main checkout" failure class (incidents: 2026-04-23 Codex, 2026-05-26 PR-A Task 5).

## Test plan

- [ ] CI green on `python-tests.yml` (3.11 + 3.13 + mono build with new coupling step)
- [ ] Bugbot completes with no remaining HIGH/MED
- [ ] After merge: #208 and #201 close automatically (PR body `Closes #208`)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 7: Monitor CI, then trigger Bugbot**

Wait for the workflow run to complete (~6-8 min based on PR #212 timing). When all checks SUCCESS:

```bash
unset GITHUB_TOKEN
gh pr comment <PR-NUM> --body "@cursor review"
```

Wait for Bugbot review (~5-15 min). Address any HIGH/MED findings; iterate. When Bugbot says "no new issues" AND all CI green:

```bash
unset GITHUB_TOKEN
gh pr merge <PR-NUM> --merge
```

Expected: PR merged with a merge commit; `#208` and `#201` auto-close via PR body's `Closes` lines.

- [ ] **Step 8: Post-merge bookkeeping**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git fetch origin develop --quiet
git checkout develop
git pull --quiet
git log --oneline -5
```

Expected: develop HEAD is the new merge commit; PR-B's 4 commits are visible in `origin/develop..HEAD` is empty.

---

## Self-review checklist (executed before sharing this plan)

**Spec coverage:**
- §3 In-scope items 1-4 ✅ (Tasks 1-4 map directly)
- §3 Out-of-scope respected (no other module pairs, no `_build_active_rules` changes, no Fortran)
- §4 D-1..D-4 each implemented (D-1 single verify in Task 1; D-2 named callable in Task 1; D-3 negative test in Task 2; D-4 invariant verified — empirical probe was done pre-spec)
- §6 helper code verbatim in Task 1 Step 3
- §7.2 happy test verbatim in Task 1 Step 1
- §7.3 negative test verbatim in Task 2 Step 1
- §8 CI step verbatim in Task 3 Step 2
- §9 README note verbatim in Task 4 Step 1
- §11 acceptance criteria 1-8 reachable by Task 5 exit

**Placeholder scan:** none — every code step has actual Python/YAML/shell text.

**Type / name consistency:** `_eq_to_tr_bpsd_check` (function), `("eq", "tr")` (tuple key), `Trlib.check_bpsd_pull` (method) match across all tasks and the spec.

**Subagent-worktree discipline:** every `git` / `make` command uses explicit `cd <abs-path>` or `-C <abs-path>` (per `feedback_codex_worktree_sharing.md`), defusing the recurring incident class.
