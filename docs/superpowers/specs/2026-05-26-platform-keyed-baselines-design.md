# Platform-keyed equivalence baselines (design)

**Status**: design, pre-implementation
**Date**: 2026-05-26
**Tracking issue**: #213 (fplib + wrxlib equiv tests fail 1e-10 on develop baseline)
**Predecessors**: PR #211 (#209 cascade), PR #212 (Phase 2c PR-A), PR #214 (Phase 2c PR-B)

## 1. Context

The current Layer-1 equivalence-test infrastructure compares
freshly-replayed `lib<mod>api.so` output against a single
canonical `test_run/baselines/<case>/metrics.json` file using
`compare_metrics.py` at hard-coded tolerance `1e-10`. This design
implicitly assumes:

- floating-point output is deterministic across compilers and libm
  vendors at 1e-10, OR
- baselines and tests always run in the same environment.

Both assumptions break in practice. Baselines are regenerated on
clavius (Linux gfortran 13.3.0 + glibc libm — see memory
`reference_clavius_baseline_regen.md`). Local development on macOS
uses Homebrew GCC 15.2.0 + Apple libm. Empirically (Codex 2026-05-26
investigation):

- `fpsave.f90:1509,1623` SQRT/relativistic terms + `wrcalpwr.f90:215`
  ray-power accumulation + `wrexecr.f90:137,877` SIN/COS/SQRT ray
  marching are all transcendental-heavy. Iteration depth amplifies
  single-step libm drift past 1e-10.
- 4 tests fail on develop @ `5a59b96f`: `fplib::test_dt1` (1 mismatch
  @ 2.354e-10), `fplib::test_iter01` (40+ RPCT mismatches up to
  4.447e-9), `wrxlib::test_demo` (~1), `wrxlib::test_iter01`
  (pwr_tot @ 1.382e-9).
- eq/tr/ti equiv tests pass on the same macOS environment because
  their solver patterns are single-shot (no iteration amplification).
- No fp/wrx Fortran code changes since baseline regen 2026-05-10 —
  this is environmental drift, not a regression.

The existing `regen-baselines.yml` workflow already documents this
class of issue by EXCLUDING fp/ti/wr/wrx from automatic regen (only
eq/tr/tot are regenerated automatically). `tr_m0904/KNOWN_ISSUE.md`
documents cross-host compiler drift more generally. So the design
gap is recognized but not yet fixed.

CI status (clarification from earlier draft, corrected by Codex
spec-review HIGH-5 line 323 reading): `python-tests.yml:323` runs
`python -m pytest python/ --forked ...` — a **whole-tree** sweep
that exercises every per-module `test_equivalence.py` including
fp/ti/wr/wrx. On Ubuntu (CI's runner) the existing `linux-gcc13`
baselines match the gfortran-13.x output and these tests pass. The
"silent for 16 days" framing in earlier-session notes was wrong:
CI WAS catching real regressions; only the macOS-local developer
experience was opaque (no automated macOS coverage). The #213
issue is therefore a macOS-developer-convenience gap, not a CI
gap — which slightly narrows the scope (no new CI test steps
needed; the migration is transparent at CI level).

## 2. Goal

End the false-positive class of "macOS dev sees fp/wrx equiv fail
even though no code changed" WITHOUT relaxing the equivalence
contract anywhere. The principled fix:

- Treat the 1e-10 tolerance as a contract about **per-environment
  reproducibility**, not cross-platform determinism.
- Carry one baseline set per supported `(os, gcc-major)` platform.
- Test resolves baseline via a deterministic platform key. If no
  baseline exists for the runtime platform, **hard fail with an
  actionable message** — never silently fall back. Skip would
  violate `feedback_equivalence_must_pass.md`; soft fallback would
  re-introduce the cross-platform false positive that triggered
  this redesign.

The result: developers on each supported platform see real bit-level
1e-10 equivalence; developers on unsupported platforms see a clear
"regenerate or downgrade" path.

## 3. Scope

### In scope

1. New helper `python/_baseline_select.py` with `platform_key()` and
   `select_baseline(case_dir)` functions.
2. Restructure all **20 existing baselines** (3 eq + 3 fp + 3 ti +
   2 tot + 3 tr + 3 wr + 3 wrx — verified by `find
   test_run/baselines -name metrics.json | wc -l` on develop @
   `5a59b96f`) under
   `test_run/baselines/<case>/<platform-key>/metrics.json`. Today's
   baselines (generated on Linux gfortran 13.3.0) become
   `<case>/linux-gcc13/metrics.json` (`git mv`). Flat
   `<case>/metrics.json` layout is **abolished** — no
   backward-compat support.
3. Generate macOS Homebrew GCC 15.2.0 baselines for **every one of
   the 20 cases**, commit as `<case>/macos-gcc15/metrics.json`.
4. Migrate all **seven** `test_equivalence.py` files (eqlib, trlib,
   tilib, fplib, wrxlib, **wrlib**, totlib — `wrlib` was missed in
   the first design draft per Codex 2026-05-26 review HIGH-3) to
   call `select_baseline(case_dir)` instead of
   `case_dir / "metrics.json"`.
5. Update `test_run/scripts/check_regression.sh` (lines 47-48 hard-
   code the flat path `$BASELINES_DIR/$TEST_NAME/metrics.json`) to
   resolve the platform-keyed subdirectory. The script supports both
   compare and `--generate-baseline` modes; both modes must produce
   / consume the platform-keyed path.
6. Documentation: `docs/baseline-regeneration.md` (or similar) with
   the `(os, gcc-major)` model + how to add new platforms.

### Out of scope

- Adding a macOS job to CI. GitHub Actions macOS runners are ~10×
  Linux billing; the user chose Linux-only CI explicitly. macOS
  developers carry their `macos-gcc15` baselines locally; CI does
  not enforce them.
- Soft fallback to canonical Linux baseline. Hard fail is the user's
  explicit choice.
- Other platforms (Windows, Linux-gcc14, macos-gcc14, ...) — added
  reactively when a real user appears; gate is "submit baselines as
  a PR after physics audit comparing to linux-gcc13".
- Fortran source changes. This is purely test infrastructure.
- Tolerance scheme changes. `compare_metrics.py` still hard-codes
  `1e-10` — the platform-keyed baselines make that tolerance
  meaningful again instead of compensating for environmental drift.
- **`regen-baselines.yml` extension to cover fp/ti/wr/wrx**. Per
  Codex 2026-05-26 review HIGH-5: the workflow today doesn't just
  exclude fp/ti/wr/wrx at the dispatch step (lines 177-188); it
  also doesn't build the standalone binaries those modules need
  (lines 136-145). Expanding the workflow needs binary-build steps
  that are out of scope for a test-infrastructure PR. Today's
  linux-gcc13 baselines for fp/ti/wr/wrx are already committed (the
  20-case set being migrated in §2 above), so the regen workflow
  gap is dormant unless the implementer of a FUTURE fp/wrx code
  change needs to regenerate them — at which point the workflow
  expansion becomes urgent and gets its own PR. Local regen via
  `test_run/run_tests.sh` + `check_regression.sh --generate-baseline`
  works today for all modules and is the path the implementer of
  THIS PR uses for the macOS baselines.

## 4. Design decisions

### D-1: Platform key formula = `{os}-gcc{major}`

**Chosen**: `f"{os}-gcc{major}"` (e.g. "linux-gcc13", "macos-gcc15").
**Rejected**:
- `{os}` alone — same OS but different gcc majors (13 vs 15) can
  drift past 1e-10 (today's bug). Coarse enough to be invisible.
- `{os}-gfortran-{full-version}` — every patch release would need
  its own baseline. Real-world friction.
**Why**: gfortran patch releases within a major (13.1, 13.2, 13.3)
are usually FP-stable; major bumps (13 → 15) can change codegen.
This formula minimizes baseline churn while catching real
codegen-level drift.

### D-2: Hard fail when exact key missing

**Chosen**: `select_baseline()` raises `FileNotFoundError` with an
actionable message listing available platforms + 3 remedies (regen,
use CI canonical compiler, submit PR after audit).
**Rejected**:
- Skip — violates `feedback_equivalence_must_pass.md` ("SKIPPED
  tests don't count as verification — they're invisibility").
- Soft fallback to canonical — re-introduces the cross-platform
  false-positive this design eliminates.
**Why**: principled — the test is asserting per-environment
reproducibility. An unsupported environment cannot satisfy that
contract; the right answer is a loud, actionable failure.

### D-3: No CI macOS job

**Chosen**: Linux-only CI (current state). macOS baselines carried
in repo for developer convenience but CI doesn't read them.
**Rejected**: add macOS GitHub Actions runner job.
**Why**: cost (~10× Linux). The macOS baseline-carry-in-repo
pattern gives developers fast local feedback; CI canonical stays
on the one OS where the bulk of regression checking happens.

### D-4: Existing baselines = linux-gcc13 (no flat-layout fallback)

**Chosen**: `git mv test_run/baselines/<case>/metrics.json
test_run/baselines/<case>/linux-gcc13/metrics.json` for every case.
Drop the flat layout entirely. Tests that don't pass through
`select_baseline()` after this PR are broken.
**Rejected**: keep flat layout as fallback when `linux-gcc13/` is
missing.
**Why**: backward-compat would create two truths and obscure the
design intent. Comprehensive scope (user's choice) means the cutover
is clean.

### D-5: macOS baselines committed to repo, not generated on-demand

**Chosen**: developer regenerates `<case>/macos-gcc15/metrics.json`
once, commits the JSON files (~3-15 KB each × 20 cases ≈ 150 KB
total). Subsequent macOS test runs read the committed baseline.
**Rejected**: generate on-demand into `.gitignore`'d directory.
**Why**: committed = reproducible across developers + visible in
PR diffs (drift catches reviewer attention). On-demand =
per-machine state, invisible drift.

### D-6: `_baseline_select` lives at `python/` top level

**Chosen**: `python/_baseline_select.py` at the same level as
`python/_runtime_mode.py` (PR-A).
**Rejected**: `python/totlib/_baseline_select.py` (would invert
layering: per-module wrappers would depend on totlib). Same logic
as PR-A spec D-3.
**Why**: matches existing helper-module pattern from PR #212.

## 5. Architecture

```
python/
  _baseline_select.py             # NEW — D-6: platform_key() + select_baseline()
  _runtime_mode.py                # unchanged (PR-A)
  eqlib/tests/test_equivalence.py # MODIFIED — replace flat path with select_baseline()
  trlib/tests/test_equivalence.py # MODIFIED — same
  tilib/tests/test_equivalence.py # MODIFIED — same
  fplib/tests/test_equivalence.py # MODIFIED — same
  wrlib/tests/test_equivalence.py # MODIFIED — same (added per Codex round-1 HIGH-3)
  wrxlib/tests/test_equivalence.py# MODIFIED — same
  totlib/tests/test_equivalence.py# MODIFIED — same

test_run/
  scripts/
    check_regression.sh           # MODIFIED — lines 47-48 hard-code flat path
                                  #   $BASELINES_DIR/$TEST_NAME/metrics.json;
                                  #   both compare and --generate-baseline modes
                                  #   must use platform-keyed subdir
  baselines/
    <case>/
      linux-gcc13/metrics.json    # MOVED from <case>/metrics.json (existing data, unchanged)
      macos-gcc15/metrics.json    # NEW — regenerated on macOS Homebrew gcc 15.2.0
    # ... for each of the 20 existing cases

(no .github/workflows/ changes — see §10 for rationale)

docs/
  baseline-regeneration.md        # NEW (or update existing) — document the (os, gcc-major) model
```

Boundary: no Fortran or C ABI changes. No `compare_metrics.py`
changes (the tolerance stays `1e-10`; what changes is which
baseline file the comparator gets pointed at).

## 6. Helper API contract

`python/_baseline_select.py`:

```python
"""Resolve the equivalence baseline for the current runtime platform.

Owns the (os, gcc-major) platform-key contract introduced in
docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md
(#213). Tests at `python/<mod>/tests/test_equivalence.py` consume
the resolved path via `select_baseline()`; if no baseline matches
the runtime platform the test HARD FAILS with an actionable
message — skip would be invisibility per
`feedback_equivalence_must_pass.md`, soft fallback would
re-introduce the cross-platform false-positive this design
eliminates.
"""
from __future__ import annotations

import functools
import platform
import re
import subprocess
from pathlib import Path


@functools.lru_cache(maxsize=None)
def platform_key() -> str:
    """Return e.g. 'linux-gcc13' or 'macos-gcc15'.

    OS comes from platform.system(); 'darwin' is normalized to
    'macos' for user-facing readability. GCC major is parsed from
    `gfortran --version` — the convention matches Homebrew GCC
    (e.g. 'gcc (GCC) 13.3.0') and Linux distro gfortran
    (e.g. 'GNU Fortran (GCC) 13.3.0').

    Raises RuntimeError if gfortran is unavailable or its version
    string cannot be parsed.
    """
    sys_name = platform.system().lower()
    os_key = "macos" if sys_name == "darwin" else sys_name
    try:
        out = subprocess.run(
            ["gfortran", "--version"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "Cannot determine platform key: gfortran --version "
            "failed. Equivalence tests require gfortran to be on "
            "PATH so the (os, gcc-major) baseline can be resolved."
        ) from exc
    # Parse the trailing version number, not the parenthetical
    # vendor tag. The version string differs across distros:
    #   Homebrew macOS:  'GNU Fortran (Homebrew GCC 15.2.0_1) 15.2.0'
    #   Ubuntu/Debian:   'GNU Fortran (Ubuntu 13.3.0-...) 13.3.0'
    #                    'GNU Fortran (Debian 12.2.0-14) 12.2.0'
    #   RHEL/Fedora:     'GNU Fortran (GCC) 11.4.1 20231218 ...'
    # The trailing `<major>.<minor>` after the closing paren is
    # the one stable element across all of these (per Codex
    # 2026-05-26 spec review HIGH-2).
    m = re.search(r"\)\s+(\d+)\.\d+", out)
    if not m:
        raise RuntimeError(
            f"Cannot parse gfortran major version from --version "
            f"output:\n{out}\nExpected something like "
            "'GNU Fortran (Homebrew GCC 15.2.0_1) 15.2.0' or "
            "'GNU Fortran (Ubuntu 13.3.0-...) 13.3.0'."
        )
    return f"{os_key}-gcc{m.group(1)}"


def select_baseline(case_dir: Path) -> Path:
    """Return path to <case_dir>/<platform-key>/metrics.json.

    Raises FileNotFoundError with an actionable message if no
    baseline matches the runtime platform. The error lists the
    available platforms under `case_dir` and three remedies
    (regenerate, use CI canonical compiler, submit PR).
    """
    key = platform_key()
    cand = case_dir / key / "metrics.json"
    if cand.exists():
        return cand
    available = []
    if case_dir.is_dir():
        available = sorted(
            p.name for p in case_dir.iterdir() if p.is_dir()
        )
    raise FileNotFoundError(
        f"No baseline for platform '{key}' under {case_dir}.\n"
        f"Available platforms: {available}\n"
        "Fix one of:\n"
        "  1. Regenerate baselines on your platform via\n"
        "     test_run/run_tests.sh + check_regression.sh's\n"
        "     --generate-baseline mode (per case). Writes\n"
        "     <case>/" + key + "/metrics.json. See\n"
        "     docs/baseline-regeneration.md.\n"
        "  2. Use the CI canonical compiler (gfortran 13 on Linux\n"
        "     glibc) so your output matches the committed\n"
        "     linux-gcc13 baseline.\n"
        "  3. Submit your '" + key + "' baselines as a PR after a\n"
        "     manual physics audit comparing to linux-gcc13.\n"
        "Do NOT silently fall back to a foreign-platform baseline\n"
        "— that would re-introduce the cross-platform false-positive\n"
        "this design eliminates."
    )


__all__ = ["platform_key", "select_baseline"]
```

`lru_cache` on `platform_key()` avoids repeated `gfortran --version`
subprocess overhead across multiple tests in the same process.

## 7. Per-module test_equivalence.py modification pattern

The change to each of the 6 test files is identical in shape.
Example for `python/fplib/tests/test_equivalence.py`:

**Before**:
```python
BASELINES_DIR = REPO / "test_run" / "baselines"
# ...
baseline_path = BASELINES_DIR / case_name / "metrics.json"
```

**After**:
```python
from _baseline_select import select_baseline   # top-level import
BASELINES_DIR = REPO / "test_run" / "baselines"
# ...
baseline_path = select_baseline(BASELINES_DIR / case_name)
```

Top-level import (not function-local) per the same reasoning as
PR-A spec §10 R-3.

## 8. Baseline migration

Step-by-step `git mv` for every existing case:

```bash
cd test_run/baselines
for case in */; do
    case_name="${case%/}"
    if [ -f "$case_name/metrics.json" ]; then
        mkdir -p "$case_name/linux-gcc13"
        git mv "$case_name/metrics.json" "$case_name/linux-gcc13/metrics.json"
    fi
done
```

Existing cases (verify list at implementation time): `eq_*`, `tr_*`,
`tot_*`, `fp_*`, `wrx_*`, `ti_*`, `wr_*`. 20 directories (verified
by `find test_run/baselines -name metrics.json | wc -l` on develop
@ `5a59b96f`).

## 9. macOS baseline generation

The implementer runs the following loop on macOS Homebrew GCC 15.2.0
for each of the 20 cases (concrete command per Codex 2026-05-26
spec-review MED-4 — no fictional `make -C tot baselines` target):

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
for case in eq_iter01 eq_jt60 eq_tst2 \
            fp_dt1 fp_iter01 fp_jt60 \
            ti_ar ti_min ti_w \
            tot_demo2014_short tot_ht6m_short \
            tr_iter01 tr_m0904 tr_tst2 \
            wr_iter_lhcd wr_test001 wr_tst2_ec \
            wrx_demo wrx_iter01 wrx_jt60 ; do
    bash test_run/run_tests.sh "$case"   # generates test_output/$case/<module>_regress.dat
    bash test_run/scripts/check_regression.sh \
         "$case" \
         "test_run/test_output/$case" \
         "test_run/baselines" \
         1e-10 \
         --generate-baseline
done
```

After the `check_regression.sh` change in §5 (platform-keyed
subdirectory resolution), `--generate-baseline` writes to
`<case>/macos-gcc15/metrics.json`. The implementer commits the 20
new JSON files as a single commit and includes the verbatim
`gfortran --version` output in the PR description (so future macOS
maintainers can reproduce the exact platform).

## 10. CI changes

**None.** The existing `python-tests.yml:323` whole-tree `pytest
python/ --forked ...` already exercises all 7 `test_equivalence.py`
files including fplib/wrlib/wrxlib/tilib. As long as the `git mv`
migration in §8 puts the existing baselines under `linux-gcc13/`
unchanged, CI's Ubuntu gfortran 13.x output continues to match and
the existing equivalence assertions stay green.

`regen-baselines.yml` is left untouched per §3 Out of scope (the
fp/ti/wr/wrx exclusion there is structural — workflow lacks the
binary-build steps those modules need; that's a separate PR's
concern).

## 11. Documentation

New file `docs/baseline-regeneration.md` (or extend an existing
reference document if there is a natural home — implementer's call
at write time). Content:

- The `(os, gcc-major)` model + rationale.
- How to determine your platform key
  (`python -c "from _baseline_select import platform_key; print(platform_key())"`).
- How to regenerate baselines for your platform.
- How to add a new supported platform (regen + audit + PR).
- Hard-fail message + the three remedies.

Memory `reference_clavius_baseline_regen.md` should also gain a
one-paragraph note pointing to the new doc.

## 12. Tests

The platform-keyed baseline design is itself testable. New unit
test `python/tests/test_baseline_select.py` (or under
`python/totlib/tests/` per the cross-cutting test home convention
established by PR-A's `test_mono_routing.py`):

1. `test_platform_key_format`: `platform_key()` returns a string
   matching the regex `(linux|macos|...)-gcc\d+`. Hermetic — does
   not depend on which platform actually runs.
2. `test_select_baseline_returns_existing_file`: with a tmpdir
   structured as `<case>/<platform-key>/metrics.json`, the helper
   returns that path.
3. `test_select_baseline_hard_fails_when_missing`: with a tmpdir
   that has an UNRELATED platform-key subdir, the helper raises
   `FileNotFoundError` with the actionable message containing
   "Available platforms" and "regenerate".

These tests pin the helper contract independently of the per-module
equivalence tests.

The per-module equivalence tests themselves serve as the
integration-level test of the design: after the migration, every
test that was passing before should still pass on the same
platform.

## 13. Risks

### R-1: macOS baseline regen producing unexpected results

The macOS baselines are generated fresh on the implementer's machine.
If something is genuinely wrong in fp/wrx Fortran on macOS Homebrew
GCC 15.2.0 (a real bug masked by the previously-failing equivalence
tests), the regen would commit those wrong values into the macOS
baseline.

Mitigation: the PR description must include a per-case
`linux-gcc13` vs `macos-gcc15` spot-comparison for the specific
scalars known to drift today (#213 captured `fp_iter01` worst-case
rel_err **4.447e-9** and `wrx_iter01.pwr_tot` rel_err
**1.382e-9**). The implementer asserts each new macos-gcc15 scalar
differs from the corresponding linux-gcc13 scalar by **rel_err <
5e-9** (Codex 2026-05-26 spec-review MED-6 — earlier draft's
`1e-7` threshold was too loose to catch real-bug-masked-as-drift
scenarios). Any case with drift ≥ 5e-9 holds the PR for
investigation; ≥ 1e-7 is unconditional hard fail (a real bug, not
libm drift).

### R-2: macOS-CI gap means macOS regressions go undetected

By design (D-3). Mitigation: developer responsibility documented in
the new `docs/baseline-regeneration.md`. macOS users running tests
locally still see regressions immediately because their committed
baseline is checked against fresh output.

### R-3: New supported platforms (e.g. linux-gcc14)

Mitigation: documented in D-2's hard-fail message and the new docs.
Standard process: regenerate + physics audit + PR.

### R-4: Implementer accidentally commits wrong-platform baselines

Mitigation: CI's existing `pytest --forked` on linux-gcc13 catches
any case where the linux-gcc13 baseline drifted; the regen workflow
overwrites only the linux-gcc13/ subtree, so accidentally-committed
macos-gcc15 baselines would survive a regen run rather than getting
clobbered — visible in any future diff.

## 14. Acceptance criteria

PR is ready to merge when:

1. `python/_baseline_select.py` exists with the contract from §6.
2. Every `test_run/baselines/<case>/metrics.json` has been moved
   to `<case>/linux-gcc13/metrics.json`.
3. `test_run/baselines/<case>/macos-gcc15/metrics.json` exists for
   every case present in `linux-gcc13/`. PR description includes a
   spot-comparison sanity check confirming drift is in the
   1e-10..1e-9 range (per R-1).
4. All seven `test_equivalence.py` files (eqlib, trlib, tilib, fplib, wrlib,
   wrxlib, totlib) call `select_baseline()` instead of opening a
   flat path.
5. `test_run/scripts/check_regression.sh` resolves the platform-keyed
   subdirectory in both compare and `--generate-baseline` modes.
6. `docs/baseline-regeneration.md` (or equivalent) explains the
   model.
7. Unit tests at §12 pass.
8. All previously-passing equiv tests still pass on the same
   platforms (no `python-tests.yml` changes needed — line 323's
   whole-tree pytest already covers them).
9. Issue #213 closes. Two halves:
    a. Locally (verifiable by implementer pre-push): the 4
       originally-failing fp/wrx tests now pass on macOS against
       the new macos-gcc15 baselines.
    b. CI Linux (verifiable only post-push, per Codex 2026-05-26
       spec-review MED-7): existing whole-tree pytest at line 323
       stays green. The migration is a pure `git mv` (data
       unchanged), so the post-push verification is high-confidence
       but technically requires the actual CI run.
10. Both in-house and Codex pre-push reviews HIGH/MED-free.

## 15. References

- Issue #213: fplib + wrxlib equivalence tests fail 1e-10 tolerance
  on develop.
- Codex 2026-05-26 design investigation (this session) —
  identified specific transcendental-heavy code paths and confirmed
  drift is environmental, not regression.
- Memory `feedback_equivalence_must_pass.md` — SKIP / xfail of
  equivalence tests is invisibility; this design hard-fails instead.
- Memory `reference_clavius_baseline_regen.md` — current
  baseline-host conventions; should be updated to point at the new
  doc when this PR lands.
- Predecessor spec patterns: `2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md`
  (helper module placement = D-6 here).
- Existing CI gap: `tr_m0904/KNOWN_ISSUE.md` documents the
  cross-host drift class informally; this PR is the structural
  fix.
