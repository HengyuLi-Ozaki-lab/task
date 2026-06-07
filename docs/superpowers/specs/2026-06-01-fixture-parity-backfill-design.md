# Python fixture parity backfill (design)

**Status**: design, pre-implementation
**Date**: 2026-06-01
**Tracking issue**: [#215](https://github.com/k-yoshimi/task/issues/215) — Python fixture parity for the 6-8 dead-baseline equivalence cases
**Builds on**: [`2026-05-26-linux-canonical-equiv-policy-design.md`](2026-05-26-linux-canonical-equiv-policy-design.md) (#213 / PR #216)
**Reviewed by**: Codex (3 independent passes — scope, fixture content, verification plan; plus one pre-push pass on the implementation)

## 0. Errata (post-implementation registry corrections)

Three §5 fixture-content tables were corrected during implementation after auditing each module's `*_param_registry.f90`. The original §5 tables below are preserved as historical record; the **as-shipped** content is summarized here. Codex pre-push review (2026-06-02) flagged the spec-vs-code divergence; this erratum closes it.

| Fixture | Spec §5 said | As-shipped (registry-correct) | Authoritative commit |
|---|---|---|---|
| `fp_jt60_params.py` SCALARS | included `PROFN2, PROFT2, PMAX, MODELC` | dropped from SCALARS | `52709160` |
| `fp_jt60_params.py` ARRAYS | did not include `PMAX, MODELC` | added `PMAX={1: 20.0}, MODELC={1: 4}` (Fortran namelist scalar-form assigns index 1 only, NOT broadcast — per `fp_iter01_params.py:52-61` precedent) | `52709160` |
| `fp_jt60_params.py` UNREGISTERED_KEYS | `("KNAMFP",)` | `("KNAMFP", "PROFN2", "PROFT2")` (PROFN2/PROFT2 have no CASE entry in `fp/fp_param_registry.f90`) | `52709160` |
| `tr_m0904_params.py` SCALARS | included `MDNCLS, PNBCD` | dropped from SCALARS | `92da504d` (pre-corrected at implementation, no separate fix commit) |
| `tr_m0904_params.py` UNREGISTERED_KEYS | not specified | `("MDNCLS", "PNBCD")` (neither has a CASE entry in `tr/tr_param_registry.f90`) | `92da504d` |

The `wrx_jt60_params.py` table had a similar drift (PROFN1/PROFN2/PROFT1/PROFT2 should be ARRAYS not SCALARS per `wrx_param_registry.f90:113-125`); the as-shipped fixture at commit `a3fa6ad9` already has these in ARRAYS as `[v, v]` per `wrx_iter01_params.py:45-48` precedent. The original spec §5.4 ARRAYS row did NOT list them — this erratum confirms they belong there.

The pattern that drove all three corrections: any namelist key registered as array-only (`IF (idx > SIZE(...)) RETURN; X(idx) = value`) in `<mod>_param_registry.f90` MUST live in ARRAYS, not SCALARS — bare-name `set_param(name, value)` against an array-only registration parses to `idx=0` and returns `ierr` silently.

## 1. Context

PR #216 (merged 2026-05-28) closed #213 by establishing the **Linux-canonical equivalence policy**: canonical Linux CI runs the 1e-10 baseline comparison; other platforms skip via `@skipUnless(IS_LINUX)` with a principled message naming the policy doc. See `docs/baseline-policy.md`.

The policy resolves the macOS false-positive class but exposes a coverage gap: several baselines in `test_run/baselines/` have no corresponding `python/<mod>/tests/fixtures/<case>_params.py`, so the Linux-canonical suite covers only the wired cases — not the full baseline corpus. These dead baselines are committed but never exercised by any `test_equivalence.py`.

This spec backfills that gap.

## 2. Goal

Make Linux-canonical equivalence coverage match the committed baseline corpus, so "passes on canonical CI" means "1e-10 matches every committed baseline that the wrapper can replay", not "matches a hand-picked subset".

## 3. Investigation findings

Gap analysis (`ls test_run/baselines/` vs `find python -name '*_params.py'`) and Codex independent verification:

### Truly missing fixtures (4 cases — actionable now)

| Case | Source | Notes |
|---|---|---|
| `fp_jt60` | `test_run/inputs/fp_jt60.in` (&fp, 19 keys) | Pure namelist; `MODELC=4`; no external data |
| `ti_w` | `test_run/inputs/ti_w.in` (&ti, 18 keys) | W-impurity case; `KID_NS(3)='W'`; uses 2D arrays `MODEL_BND(1,3)` |
| `tr_m0904` | `test_run/inputs/tr_m0904.in` (18 keys) | `modelg=2` analytic geometry (no eqdata); baseline has `KNOWN_ISSUE.md` documenting env-dependent drift on non-canonical builds |
| `wrx_jt60` | `test_run/inputs/wrx_jt60.in` (&wr, 33 keys) | Largest; `MODELG=2`; uses Fortran `N*X` replicated initializers (`RFIN(1)=2*110.D3`) and explicit per-element indexing (`NCMIN(1)=-3`) |

### Misnamed (already covered, needs rename)

`python/tilib/tests/fixtures/ti_iter01_params.py` actually mirrors `ti_min.in` (its docstring at L8 admits this; `BASELINE_NAME="ti_min"` at L51). `test_ti_min` already passes via it. The filename lies and propagates the confusion to four other importers. Rename and clean.

### Out of scope (blocker — separate follow-up issue)

`eq_jt60` is **not** included in this PR. Its source `eq/in/eq.injt60` references `eqdata.jt60` (binary EQDSK) and `eqjt60.gs` (EQRTSK input). Neither file exists in the working tree, and `git rev-list --all --objects | grep -i jt60` returns no matches — they have **never been committed**. The 2026-04-19 baseline commit (`52e9288e`) was generated from a developer's local data that was not preserved.

A new follow-up issue must be filed: "Regenerate `eqjt60.gs` + `eqdata.jt60` on canonical Linux and wire `eq_jt60_params.py`." It will be referenced as `Out of scope (follow-up: #NNN): eq_jt60` in the PR description.

## 4. Scope

### In scope

1. Four new fixture files (Python only — namelist translation, no Fortran changes):
   - `python/fplib/tests/fixtures/fp_jt60_params.py`
   - `python/tilib/tests/fixtures/ti_w_params.py`
   - `python/trlib/tests/fixtures/tr_m0904_params.py`
   - `python/wrxlib/tests/fixtures/wrx_jt60_params.py`
2. Four new test methods, one per module, wired into existing `TestEquivalence` classes. **Names follow per-module convention** (eq/ti use `test_<mod>_<case>`; fp/tr/wrx use bare `test_<case>` — verified against existing methods in each file):
   - `test_jt60` in `python/fplib/tests/test_equivalence.py` (after `test_dt1` at L209) — bare convention
   - `test_ti_w` in `python/tilib/tests/test_equivalence.py` (after `test_ti_ar` at L159) — prefixed convention
   - `test_m0904` in `python/trlib/tests/test_equivalence.py` (after `test_tst2` at L230) — bare convention
   - `test_jt60` in `python/wrxlib/tests/test_equivalence.py` (after `test_demo` at L184) — bare convention
3. Rename `python/tilib/tests/fixtures/ti_iter01_params.py` → `ti_min_params.py`. Five importers must update:
   - `python/tilib/tests/test_equivalence.py:154`
   - `python/tilib/tests/test_property_boundary.py:55`
   - `python/tilib/tests/test_sweep.py:67`
   - `python/tilib/tests/test_sweep.py:74`
   - `python/tilib/tests/test_property_fanout.py:61`
   - Plus the fixture's own docstring intro (clean misleading "named iter01 but mirrors ti_min" notice).
4. Register `wrx_jt60` in `test_run/test_definitions.conf` (one new line after `wrx_demo`).
5. File the eq_jt60 follow-up issue BEFORE pushing the PR so the PR description can reference its number.

### Out of scope

- `eq_jt60` fixture + test (blocked on data regeneration — separate follow-up issue).
- Adding `fp/ti/wrx` modules to `.github/workflows/regen-baselines.yml` allowlist (workflow currently allowlists only `tr_*, eq_*, tot_*`; new cases under those prefixes are auto-covered, others are out of scope for this PR — file separately if needed).
- TOT fixture cosmetic name mismatch (`tot_demo2014_params.py` filename omits `_short`; `BASELINE_NAME` is correct so not a wiring bug).
- Renaming or restructuring existing test methods beyond the rename above.

## 5. Per-fixture design

All four new fixtures follow the existing pattern (template based on `eq_tst2_params.py`):

```python
"""<one-line docstring> mirroring <SOURCE_INPUT> (<&namelist> block)."""
from __future__ import annotations
import warnings

SCALARS: dict = {...}            # routed via set_param(name, float(value))
ARRAYS: dict  = {...}            # routed via set_param(f"{name}[{i}]", float(v))
STRINGS: dict = {...}            # routed via set_param_str(name, str(value))
UNREGISTERED_KEYS: tuple = (...) # registry-unknown keys: skip + warn

SOURCE_INPUT  = "test_run/inputs/<case>.in"
BASELINE_NAME = "<case>"
# Plus module-specific attrs the test harness reads (MODE / NTMAX / etc.).

def apply(handle) -> None: ...
```

### 5.1 `fp_jt60_params.py`

| Bucket | Content |
|---|---|
| SCALARS | `NSMAX=3, PROFN2=0.5, PROFT2=2.0, NRMAX=11, RMIN=0.1, RMAX=0.4, NTMAX=1, PMAX=20.0, NPMAX=100, NTHMAX=100, MODELC=4` |
| ARRAYS | `PA={2:2.0, 3:1.0}, PZ={2:1.0, 3:1.0}, PN=[0.3, 0.285, 0.015], PNS=[0.03, 0.0285, 0.0015], PTPR=[3.7]*3, PTPP=[3.7]*3, PTS=[0.4]*3` |
| STRINGS | (none — `KNAMFP=' '` is no-op in wrapper path) |
| UNREGISTERED_KEYS | `("KNAMFP",)` per Codex finding at `fp/fp_param_registry.f90:171-180` |
| `apply` signature | `def apply(fp) -> None:` — mirror `python/fplib/tests/fixtures/fp_dt1_params.py:68` |

### 5.2 `ti_w_params.py`

| Bucket | Content |
|---|---|
| SCALARS | `NSMAX=3, DN0=0.1, DT0=1.0, DR0=1.0, DRS=3.0, NRMAX=20, NTSTEP=1, NGTSTEP=1, NGRSTEP=1, NTMAX=5` |
| 1D ARRAYS (dict, sparse indices) | `NPA={3:74}, PM={3:183.84}, PZ={3:74.0}, ID_NS={3:10}, NZMIN_NS={3:20}, NZMAX_NS={3:45}, DN0_NS={1:0.0, 2:0.0}` |
| 2D ARRAYS (NEW pattern) | `MODEL_BND={(1,3):2}, BND_VALUE={(1,3):1e-3}` → key syntax `MODEL_BND[1,3]` / `BND_VALUE[1,3]` per `ti/ti_param_registry.f90:121-133,195-215` |
| STRINGS (array element) | `KID_NS={3:'W'}` → `ti.set_param_str("KID_NS[3]", "W")` |
| Module attr | `NTMAX = 5` (read by `_check_case(ntmax=fixture.NTMAX)` at `python/tilib/tests/test_equivalence.py:148`; must match SCALARS["NTMAX"]) |
| `apply` signature | `def apply(ti) -> None:` — mirror `python/tilib/tests/fixtures/ti_ar_params.py:85` |
| `apply` extension | Needs new helper branch for 2D-dict keys (existing inline loop handles 1D dict + list). Add inline to this fixture; if a second 2D case arises, factor to a shared helper. |

### 5.3 `tr_m0904_params.py`

| Bucket | Content |
|---|---|
| SCALARS | `MODELG=2, RR=8.481, RA=2.574, RKAP=1.816, RDLT=0.3478, BB=5.953, NSMAX=4, PROFN2=0.15, MDNCLS=1, MDLNF=1, PNBCD=1.0, PNBR0=1.0, DT=0.02, NTSTEP=50, NTMAX=50, RIPS=2.0, RIPE=3.0` |
| ARRAYS | `PN=[0.1, 0.045, 0.045, 0.005], PNS=[0.01, 0.0045, 0.0045, 0.0005], PT=[1.0]*4, PTS=[0.1]*4` |
| STRINGS | (none) |
| `apply` signature | `def apply(tr) -> None:` — mirror `python/trlib/tests/fixtures/tr_tst2_params.py:71` |
| Docstring note | One-line reference to `test_run/baselines/tr_m0904/KNOWN_ISSUE.md` and the policy that canonical-CI drift, if observed, triggers a new issue (not preemptive `@xfail`). |

### 5.4 `wrx_jt60_params.py` (largest, list-form arrays per Codex)

| Bucket | Content |
|---|---|
| SCALARS (~22) | `BB=3.5, RA=1.0, RR=3.4, RB=1.1, NSMAX=2, MODELG=2, MDLWRQ=1, MODELQ=0, Q0=1.2, QA=4.0, PROFJ=1, PROFN1=2, PROFN2=1, PROFT1=2, PROFT2=1, MDLWRI=2, MDLWRW=0, MDLWRG=1, MDLWRP=1, pne_threshold=1e-6, DELS=1e-3, SMAX=1.5, NRAYMAX=2` |
| ARRAYS (lists, mirroring `wrx_iter01_params.py:60-68`) | `MODELP=[206,206], MODELV=[3,0], PN=[0.5,0.5], PNS=[0.025,0.025], PTPR=[5.0,5.0], PTPP=[5.0,5.0], PTS=[0.3,0.3], PA=[2.0, 5.4462e-4], PZ=[1.0,-1.0], NCMIN=[-3,-3], NCMAX=[3,3], RFIN=[110e3, 110e3], RPIN=[4.5,4.5], ZPIN=[0.0,0.0], PHIIN=[0.0,0.0], ANGPIN=[0.0,10.0], ANGTIN=[15.0,25.0], UUIN=[1.0,1.0], MODEWIN=[1,1]` |
| STRINGS | (none — `KNAMWR='wrx_jt60.data'` is no-op in wrapper path per Codex finding at `python/wrxlib/tests/fixtures/wrx_iter01_params.py:71-76`) |
| UNREGISTERED_KEYS | `("KNAMWR",)` |
| `apply` signature | `def apply(lib) -> None:` — mirror `python/wrxlib/tests/fixtures/wrx_iter01_params.py:89` (wrx fixtures use `lib`, not `wrx`) |
| Codex constraint | Existing fixtures use `for i, v in enumerate(arr, start=1): lib.set_param(f"{name}[{i}]", float(v))` (see `python/wrxlib/tests/fixtures/wrx_iter01_params.py:99-101`). The `enumerate` path iterates list values, not dict items; dict-form arrays would iterate dict keys and silently misapply. All array params in this fixture **must** be lists. |

### 5.5 `ti_iter01_params.py` → `ti_min_params.py` rename

- `git mv` the file
- Update five importers (listed in §4 item 3)
- Update fixture docstring: drop the misleading "named ti_iter01 but mirrors ti_min" notice; write a natural ti_min docstring
- Sanity: `git grep -n "ti_iter01_params" python/` returns zero after the rename

### 5.6 `test_run/test_definitions.conf` registration

Insert one line after the `wrx_demo` definition:

```
wrx_jt60:wrx:@inputs/wrx_jt60.in:none:120:WRX JT-60 ECCD case
```

Note: `test_definitions.conf` timeout governs the `run_tests.sh`-driven Fortran path (baseline regen), not `python-tests.yml`. The Python wrapper run on CI is gated by `--timeout=120` in `.github/workflows/python-tests.yml:323-326` — that is the binding constraint for the equivalence-test path.

## 6. Verification plan

### 6.1 macOS local verification (before push)

The Linux-canonical policy delegates 1e-10 equivalence to canonical CI; macOS cannot build `<mod>/<mod>` standalone binaries (graphics-libs gap per `reference_clavius_baseline_regen.md`). Local verification therefore covers structural correctness, not numerical equivalence:

| Check | Command | Expected |
|---|---|---|
| Fixture import smoke | `python -c "from <mod>.tests.fixtures import <case>_params; print(<case>_params.BASELINE_NAME)"` × 5 (4 new + ti_min) | No exception |
| Existing-tests regression | `PYTHONPATH=python pytest python/{fplib,tilib,trlib,wrxlib}/tests/ --forked --timeout=120 --timeout-method=signal -x` | Existing PASS stays PASS; equiv classes SKIP via `@skipUnless(IS_LINUX)`. If `--forked` fails on Darwin, drop `--forked` and rerun (no global `--forked` config, per Codex check at `python/conftest.py` not-found) |
| New `test_*` collection | `pytest --collect-only python/<mod>/tests/test_equivalence.py` × 4 modules | Each shows 1 new method + existing methods |
| Rename completeness | `git grep -n "ti_iter01_params" python/` | Zero matches |
| Driver-side conf syntax | `bash test_run/run_tests.sh --list 2>&1 \| grep wrx_jt60` | Shows the new line per `test_run/run_tests.sh:6-17` |

### 6.2 Linux CI verification (canonical 1e-10)

Canonical job: `.github/workflows/python-tests.yml`. It invokes `pytest python/...` directly with `--timeout=120` at L323-326 (it does **not** call `test_run/run_tests.sh`). Expected PASS:

- `TestEquivalence.test_jt60` in `python/fplib/tests/test_equivalence.py`
- `TestEquivalence.test_ti_w` in `python/tilib/tests/test_equivalence.py`
- `TestEquivalence.test_m0904` in `python/trlib/tests/test_equivalence.py`
- `TestEquivalence.test_jt60` in `python/wrxlib/tests/test_equivalence.py`
- `TestEquivalence.test_ti_min` (existing, post-rename — must remain PASSED)

PR description must include explicit verification language:

> **How to verify on Linux CI**: In the `python-tests.yml` job output, confirm pytest summary shows the fully-qualified test IDs `python/fplib/tests/test_equivalence.py::TestEquivalence::test_jt60`, `python/tilib/.../test_ti_w`, `python/trlib/.../test_m0904`, `python/wrxlib/.../test_jt60`, and `python/tilib/.../test_ti_min` as **PASSED** (not SKIPPED). A SKIPPED row indicates the canonical-platform guard mis-fired or the test method didn't import its fixture correctly.

### 6.3 If tr_m0904 drifts on canonical CI

Stance: this is canonical-platform drift = new bug class, not the "Class 2 principled platform-scoped skip" allowed by `feedback_equivalence_must_pass.md`.

1. Do NOT revert this PR.
2. File a new issue with the CI log, recording gfortran/libbpsd/LAPACK versions.
3. Mark `test_m0904` (in `python/trlib/tests/test_equivalence.py`) with `@pytest.mark.xfail(strict=True, reason="#<new>")` in a follow-up commit. `strict=True` ensures the marker is removed automatically when the upstream drift is resolved.
4. Reference `#197` (clavius vs CI gfortran 3e-9 drift) as related prior work.

### 6.4 If tr_m0904 exceeds pytest --timeout=120 on canonical CI

The binding timeout is the pytest argument in `.github/workflows/python-tests.yml:323-326`, **not** `test_definitions.conf`. Decision:

- If wrapper run is inherently slow due to `NTMAX=50` (proportional to baseline runtime) → bump `--timeout` to 240 in the same follow-up commit. Do not preemptively bump.
- If runtime regressed unexpectedly (slower than ratio to `tr_iter01` would predict) → revert and root-cause first.

### 6.5 Pre-push gate (CLAUDE.md non-negotiable)

1. macOS local pytest from §6.1 passes
2. Launch reviewer agents on the branch diff. CLAUDE.md names `feature-dev:code-reviewer`; if the Agent tool reports it unavailable at runtime, fall back to `superpowers:code-reviewer` (the alternate name from `.claude/handoff-2026-05-02.md:189-190`); if neither resolves, confirm correct name with the user before pushing.
3. Launch `codex:codex-rescue` in parallel for independent cross-cutting review
4. Paste both agents' HIGH/MED findings to the user; get agreement before pushing
5. `touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"` — confirmed correct path against `scripts/pre-push.sh:43-44`
6. `git push -u origin <branch>` — no `--no-verify`, no `--admin`
7. Wait for Bugbot COMPLETED before merge per `feedback_bugbot_wait.md`

### 6.6 Follow-up issue ordering and #215 close mechanics

1. **First**: file the eq_jt60 follow-up issue on GitHub, capture its number `#NNN`.
2. **Then**: push the PR. The PR description **must** include `Closes #215` on its own line (no parentheses around the issue number) — this is the GitHub auto-close keyword form. The `Out of scope (follow-up: #NNN): eq_jt60` line goes in a separate "Out of scope" section so the parenthetical does not interfere with auto-close keyword parsing.
3. **After merge**: verify `#215` actually closed. If GitHub auto-close did not trigger (the prior arc on #208/#211/#213 showed this happening when the keyword was buried in parenthetical-after-issue formatting), manually run `gh issue close 215 --comment "Closed via PR #<merged-PR>"` as a backstop.

## 7. Success criteria

- ✅ PR passes canonical Linux CI: 4 new + 1 rename, all PASSED (not SKIPPED)
- ✅ Bugbot COMPLETED
- ✅ macOS local: no regression to existing PASS, equiv classes SKIP cleanly
- ✅ `git grep ti_iter01_params python/` returns zero
- ✅ `wrx_jt60` appears in `test_run/run_tests.sh --list` output
- ✅ eq_jt60 follow-up issue filed
- ✅ #215 closed after merge, via auto-close keyword or manual `gh issue close 215` backstop

## 8. Implementation hand-off

The next step is `superpowers:writing-plans` to produce a step-by-step implementation plan. Conventions resolved in this spec (writing-plans should not relitigate):

- **Branch name**: `feat/fixture-parity-215` (matches repo convention from prior work — short, prefixed `feat/`, issue number in slug; cf. `feat/totlib-pipeline-phase1` in PR #178)
- **Test-method naming**: per-module convention codified in §4 item 2 (fp/tr/wrx bare, ti prefixed)
- **`apply()` signatures**: each fixture's signature is specified in §5 (`apply(fp)`, `apply(ti)`, `apply(tr)`, `apply(lib)` for wrx)
- **Array-form rule for wrx**: lists only, never dicts (§5.4 Codex constraint)

Open questions for writing-plans to resolve before any code lands:

1. **ti 2D-array key syntax verification** — Codex confirms `[row,col]` form at `ti/ti_param_registry.f90:121-133,195-215`. Implementation should construct the key string accordingly and verify via the C ABI's `set_param` path on a single test call before committing the fixture.
2. **wrx dict-rejection vs silent-misapply** — confirm what happens at runtime if a wrx fixture passes a dict-form array (rejected loud, vs silently iterated as keys). If silently misapplied, add a defensive `assert isinstance(arr, list)` in the new fixture's `apply` to catch future fixture mistakes early.
3. **wrx `nstpmax_arg` default propagation** (Codex Q10b, unresolved): `wrx_jt60.in` has no explicit `NSTPMAX`; verify the wrapper's default at `wrx/wrx_api.f90:176-190` matches the Fortran driver's default before considering the fixture complete.
4. **regen-baselines.yml allowlist re-verification** (Codex Q9): read `.github/workflows/regen-baselines.yml:177-184` once at implementation time to confirm `tr_m0904` is covered by the existing `tr_*` pattern and that fp/ti/wrx exclusion is intentional. Do not modify the file unless verification reveals a mismatch that affects this PR (in which case file a separate issue rather than expand scope).

## 9. References

- Predecessor spec: `docs/superpowers/specs/2026-05-26-linux-canonical-equiv-policy-design.md`
- Policy doc: `docs/baseline-policy.md`
- Related memory: `feedback_equivalence_must_pass.md` (Class 1 / Class 2 skip distinction)
- Related memory: `reference_clavius_baseline_regen.md` (Linux-canonical environment)
- Related memory: `feedback_review_before_push.md` (pre-push gate)
- Related issue: #215 (this), #197 (gfortran-version drift), #213 (closed; predecessor)
- Related test discipline: `feedback_never_skip_tests.md` (no invisibility skips)
