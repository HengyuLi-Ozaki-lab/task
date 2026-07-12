# Linux-canonical equivalence policy (design)

**Status**: design, pre-implementation
**Date**: 2026-05-26
**Tracking issue**: #213 (fplib + wrxlib equiv tests fail 1e-10 on macOS)
**Supersedes**: `docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md` + `docs/superpowers/plans/2026-05-26-platform-keyed-baselines-implementation.md` (kept as design-history; see §11)

## 1. Context

The earlier comprehensive design (`platform-keyed-baselines`) proposed carrying per-platform baselines `<case>/<os>-gcc<major>/metrics.json` with hard-fail when no exact key matches. Implementation revealed two structural blockers that Codex surfaced (2026-05-26 review rounds):

1. **6 of 7 modules cannot build standalone Fortran binaries on macOS**: `fp/fp`, `ti/ti`, `tr/tr2`, `eq/eq`, `wr/wr`, `wrx/wrx` link against real GFLIBS (`-lg3d-gfc64 -lgsp-gfc64 -lgdp-gfc64`) which Homebrew does not provide. Only `tot/tot` has `tot_static_stubs.f90` for graphics-free linking. Per memory `reference_clavius_baseline_regen.md`: macOS lacks the graphics libs.

2. **6-8 of 20 baseline cases lack Python fixtures**: `eq_jt60`, `fp_jt60`, `ti_min`, `ti_w`, `tr_m0904`, `wrx_jt60`, plus possible name-mismatched `tot_*_short` cases. Those baselines were generated on Linux clavius via the standalone-binary regen workflow; nobody ever wrote `<case>_params.py` for them. They are dead baselines — committed but never exercised by any `test_equivalence.py`.

The platform-keyed design assumed both gaps would be closed by this PR. Realistically, closing them requires per-module Fortran static-stubs (6 modules × Phase-L-like work) AND new Python fixtures for 6-8 cases. That is multi-day scope creep for what #213 actually wants: stop the macOS-only false-positive class.

This spec pivots to a simpler design recommended by Codex: declare equivalence Linux-canonical, skip on non-Linux with a documented platform-scoped policy.

## 2. Goal

End the macOS-only false-positive class (#213) without expanding scope to fix the structural gaps that block platform-keyed baselines. macOS dev continues to use `lib<mod>api.so` via Python wrappers for development; equivalence verification is Linux CI's responsibility on every push.

## 3. Scope

### In scope

1. Add `@unittest.skipUnless(IS_LINUX, "<actionable reason>")` to the `TestEquivalence` class in all 7 `test_equivalence.py` files (eqlib, trlib, tilib, fplib, wrlib, wrxlib, totlib).
2. New `docs/baseline-policy.md` documenting:
   - Linux gfortran on Ubuntu CI runner is the canonical equivalence environment.
   - macOS / non-Linux developers run the library via Python wrappers for development; equivalence verification runs only on Linux CI.
   - Rationale for not maintaining macOS baselines (the two structural gaps in §1).
   - How a future contributor can promote a new platform to canonical (closes both gaps).
3. Memory update: extend `feedback_equivalence_must_pass.md` (NOT a new peer file — Codex 2026-05-26 spec-review LOW: pin to avoid duplicate policy fragments) to distinguish **principled platform-scoped skip** (documented, Linux CI is canonical) from **invisibility skip** (no reason, no canonical fallback). The latter remains forbidden.
4. Mark the prior `platform-keyed-baselines-design.md` + implementation plan as `**SUPERSEDED**` at the top, pointing at this spec. Keep them as design-history.
5. File a new tracking issue for the Python-fixture-parity gap (6-8 dead baselines). It is the prerequisite if platform-keyed is revisited in the future.

### Out of scope

- Carrying macOS baselines (`<case>/macos-gcc15/metrics.json`).
- Migrating existing baselines under `<case>/linux-gcc13/`.
- Writing Python fixtures for the 6-8 dead baselines.
- Building per-module Fortran static-stubs for graphics-free macOS standalone link.
- Tolerance changes (`compare_metrics.py` keeps `1e-10`).
- CI changes (`python-tests.yml:323` whole-tree pytest already covers all 7 modules on Ubuntu).

## 4. Design decisions

### D-1: Skip granularity = module-level on the test class

**Chosen**: `@unittest.skipUnless(IS_LINUX, ...)` at the `TestEquivalence` class declaration. All cases in the class skip together on non-Linux.

**Rejected**: per-test skip, per-fixture-platform check.

**Why**: equivalence is a CLASS-LEVEL contract (all cases verify the same compiler/libm against a single canonical baseline set). Per-test skip would suggest some cases work on macOS — they don't, by design. Class-level matches the policy.

### D-2: Platform detection = `sys.platform.startswith("linux")`

**Chosen**: `IS_LINUX = sys.platform.startswith("linux")`.

**Rejected**:
- `platform.system() == "Linux"` — equivalent but less idiomatic in pytest world.
- `os.uname().sysname.lower() == "linux"` — extra import, same answer.

**Why**: `sys.platform.startswith("linux")` is the canonical pytest-world predicate. It correctly matches WSL (`linux`) and Linux containers on macOS Docker. Per Codex 2026-05-26 review MED-6: this is acceptable — the policy is "Linux userland", not "physical host OS". The skip message and `docs/baseline-policy.md` clarify the policy applies to Linux userland of any flavor; users testing in a Linux container on macOS see tests RUN, not skip.

### D-3: Skip message references the policy doc

**Chosen**: skip message includes a one-line explanation + pointer to `docs/baseline-policy.md`.

**Rejected**: a generic "macOS not supported" message.

**Why**: a developer hitting the skip needs to understand (a) what's verified instead, (b) why, (c) how to verify locally via a Linux container (the documented workaround in §7 R-4). The full reasoning lives in the doc; the skip message is a signpost. The skip itself is NOT overridable by env var — the policy is "Linux userland or no equiv check" (Codex 2026-05-26 spec-review MED — earlier draft said "override" without a mechanism).

### D-4: `docs/baseline-policy.md` is the canonical reference

**Chosen**: a single Markdown file at `docs/baseline-policy.md` (top-level docs/ — not under `superpowers/`) documenting the policy + how to promote a new platform to canonical in the future.

**Rejected**:
- Inline policy block in `feedback_equivalence_must_pass.md` memory — memory is too dense for newcomers.
- Section in `python/totlib/README.md` — wrong layering (policy spans 7 modules).

**Why**: top-level `docs/` is where cross-cutting policy lives. Memory + per-module READMEs cross-reference it.

### D-5: Distinguish "principled platform-scoped skip" from "invisibility skip" in memory

**Chosen**: extend `feedback_equivalence_must_pass.md` (Codex 2026-05-26 spec-review LOW) — keeping the principled-skip rule next to the invisibility-skip rule avoids policy fragmentation. The memory enumerates the two skip classes:

- **Invisibility skip** (FORBIDDEN): no reason recorded, no canonical environment runs the test, the skip just lets CI go green while real bugs hide.
- **Principled platform-scoped skip** (ALLOWED if documented): the test verifies behavior on a specific canonical platform; off-platform skip is explicit; CI on the canonical platform runs the test every push.

**Why**: without this distinction, future contributors might cargo-cult the `@skipUnless` pattern as a way to silence flaky tests. The memory codifies the difference so the pattern remains principled.

### D-6: File a separate tracking issue for the Python-fixture-parity gap

**Chosen**: open a new issue listing the 6-8 cases without Python fixtures (`eq_jt60`, `fp_jt60`, `ti_min`, `ti_w`, `tr_m0904`, `wrx_jt60`, plus name-mismatch resolution for `tot_*_short`). The issue is the prerequisite for any future platform-keyed baseline work.

**Why**: the gap is structural and predates #213. Leaving it implicit lets the design-history specs (`platform-keyed-baselines-design.md` etc.) be re-attempted later without the same execution blockers.

## 5. Implementation outline

This spec deliberately does NOT have a separate implementation-plan file. The implementation is 10 file touches in 3 logical commits — small enough to inline here.

### Commit 1: Add `@skipUnless(IS_LINUX, ...)` to all 7 test_equivalence.py

For each of `python/{eqlib,trlib,tilib,fplib,wrlib,wrxlib,totlib}/tests/test_equivalence.py`:

```python
# Add to module-level imports if missing:
import sys

# Add module-level constant near other constants:
IS_LINUX = sys.platform.startswith("linux")

# Decorate the existing TestEquivalence class:
@unittest.skipUnless(
    IS_LINUX,
    "Equivalence tests are Linux-canonical. The 1e-10 baselines "
    "live in test_run/baselines/<case>/metrics.json and were "
    "generated on Linux gfortran 13.x (Ubuntu CI runner). macOS / "
    "non-Linux dev runs the lib<mod>api.so via the Python wrapper; "
    "correctness is verified by Linux CI on every push. See "
    "docs/baseline-policy.md.",
)
class TestEquivalence(unittest.TestCase):
    ...
```

(Each file's actual class may have a different name — apply to whichever class drives the equivalence cases. eqlib uses `TestEquivalence`; trlib similar; totlib has `TestEquivalence` per current source.)

### Commit 2: `docs/baseline-policy.md`

New file documenting the policy. ~80 lines covering:

- The 1e-10 contract: what it asserts (Linux gfortran 13.x baseline reproducibility) and what it does not (cross-platform bit-equiv).
- Why macOS / non-Linux skip the equivalence suite.
- Pointer to the structural blockers (graphics-libs gap + Python-fixture gap).
- "If you want equivalence verified locally": run a Linux container, install gfortran 13.x, run `pytest python/<mod>/tests/test_equivalence.py`.
- "If you want to add macOS as canonical": prerequisite issue (the new tracking ticket).

### Commit 3: Memory update + supersede old design docs

- Update `memory/feedback_equivalence_must_pass.md` per §4 D-5 (extend the existing rule with the principled-skip class; no new peer memory file).
- Prepend `**SUPERSEDED by docs/superpowers/specs/2026-05-26-linux-canonical-equiv-policy-design.md ...**` to both the old spec and old plan.

(Memory edit is controller-side; not a code change.)

## 6. Tests

The change itself is purely a skip directive. Verifying it:

- On macOS: running `pytest python/eqlib/tests/test_equivalence.py -v` should report SKIPPED instead of running. Same for all 7 modules.
- On Linux (controlled — verify via CI run on the PR): all 7 equivalence suites still run as they do today (no behavior change on Linux).
- No new test files. The existing test suite IS the test of the change.

## 7. Risks

### R-1: macOS-only Fortran bug slips through CI

Real but scoped (Codex 2026-05-26 HIGH-Q2). Formal mitigation: the `lib<mod>api.so` is still exercised on macOS via the Python wrappers' OWN test suites (test_eqlib.py, test_trlib.py, etc. which load + call functions in libeqapi.so). Those wrap-level tests catch ABI / load / call-pattern issues even though they don't enforce 1e-10 equivalence. Beyond that, a hypothetical macOS-only numerical drift that produces *physically wrong* values (not just bit-shifted ones) is **more likely to be noticed** by users who run larger-scale macOS simulations (transport runs, parameter sweeps) than to remain silent — but this is informal observation, NOT a formal guarantee (Codex 2026-05-26 spec-review MED — earlier draft over-claimed by saying "would be visible").

### R-2: Linux CI environment drift

Future Ubuntu image bumps to gfortran 14 / 15 would break the linux-gcc13 baseline. Mitigation: the policy doc says "promote a new platform to canonical" via the prerequisite tracking issue's process. If CI flips, baselines need regen on the new canonical compiler and the doc updated.

### R-3: Developer confusion ("why skipped?")

Mitigation: the skip message is verbose + points at the doc. The doc is the entry point.

### R-4: Codex's MED-6 — `sys.platform.startswith("linux")` matches WSL / Linux Docker on macOS

Acceptable. The policy is about Linux userland; WSL + containerized Linux are Linux userland. If a contributor sets up a Linux container on macOS Docker explicitly to verify equivalence, that's the documented workaround.

## 8. Acceptance criteria

PR is ready to merge when:

1. All 7 `test_equivalence.py` files have the `@skipUnless(IS_LINUX, ...)` directive on their `TestEquivalence` class.
2. Running pytest on macOS shows 7 SKIPPED equivalence suites + 0 failures from those suites; the #213 fp/wrx 4 failures are gone.
3. `docs/baseline-policy.md` exists and clearly states the policy + rationale.
4. Memory updated per §4 D-5 to distinguish principled-skip from invisibility-skip.
5. Old `platform-keyed-baselines-design.md` + implementation plan prepended with SUPERSEDED note.
6. New follow-up issue filed listing the 6-8 dead-baseline cases (per §4 D-6 — content composable from §1's gap description). `docs/baseline-policy.md` links to that issue (Codex 2026-05-26 spec-review LOW — discoverability).
7. Linux CI (`python-tests.yml:323` whole-tree pytest) continues to run + pass all 7 equivalence suites on Ubuntu.
8. Both in-house and Codex pre-push reviews HIGH/MED-free.

## 9. References

- Issue #213: fplib + wrxlib equiv tests fail 1e-10 tolerance.
- Codex 2026-05-26 design pivot review: recommended Option F with explicit reasoning.
- Codex earlier reviews surfaced the structural gaps (graphics-libs + Python-fixture).
- Memory `feedback_equivalence_must_pass.md` — the rule this design refines.
- Memory `reference_clavius_baseline_regen.md` — current Linux-canonical baseline-gen convention.
- Superseded specs (kept as design history):
  - `docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md`
  - `docs/superpowers/plans/2026-05-26-platform-keyed-baselines-implementation.md`
