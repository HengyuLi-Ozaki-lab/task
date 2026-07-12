# Sweep / property_fanout FIXTURES_DIR fallback (design)

**Status**: design, pre-implementation
**Date**: 2026-06-08
**Tracking issue**: [#192](https://github.com/k-yoshimi/task/issues/192) — CI: stage eqdata.ITER01/TST-2 so test_equivalence.py actually runs (currently silent SKIP)
**Builds on**: PR #149 (eq fallback), PR #195 (tr equiv mirror), commit `615959e3` (tot equiv mirror) — same pattern, extended to sweep/fanout
**Reviewed by**: Codex (4 independent passes — scope, approach, scope §1, verification plan §3)

## 1. Context

Issue #192 was filed 2026-05-11 with the symptom "`test_equivalence::test_{iter01,tst2}` silently SKIPs on CI". That specific class of skips was resolved by PR #149 / PR #195 / commit `615959e3`, which added a `FIXTURES_DIR` fallback to each module's `test_equivalence._check_case`: dev-generated `eqdata.<DEV>` under `test_run/test_output/<case>/` is preferred, with a fallback to committed `python/<mod>/tests/fixtures/eqdata.<DEV>` when the dev path is absent.

A 2026-05-28 develop CI log audit confirms the residual silent-SKIPs are now in **three OTHER test files** that never got the fallback:

| File | Skip site | Style |
|---|---|---|
| `python/eqlib/tests/test_sweep.py:117-123` | Inner `self.skipTest` in test method | Per-test |
| `python/trlib/tests/test_sweep.py:58-62` | Class-level `@unittest.skipUnless(ITER01_EQDATA.exists())` | Decorator |
| `python/trlib/tests/test_property_fanout.py:74-79` | `setUp()` `self.skipTest` | Per-instance |

These tests check **only** `test_run/test_output/<case>/eqdata.<DEV>`. On Linux CI, `python-tests.yml` never invokes `./test_run/run_tests.sh tr_iter01 tr_tst2 eq_iter01`, so `test_output/<case>/` is absent and all three tests SKIP silently.

The committed fixture files needed for fallback **already exist**:

- `python/eqlib/tests/fixtures/eqdata.ITER01` (45956 bytes, committed 2026-05-10)
- `python/trlib/tests/fixtures/eqdata.ITER01` (45956 bytes, committed 2026-05-12)
- `python/trlib/tests/fixtures/eqdata.TST-2` (45956 bytes, committed 2026-05-10)

## 2. Goal

Extend the `test_equivalence` FIXTURES_DIR fallback pattern to the three remaining sweep/fanout sites so all currently-silent-SKIPs become PASSED rows on canonical Linux CI. No new fixtures, no new infrastructure, no CI workflow changes — pure mirror of an existing pattern that has been on develop for months without incident.

## 3. Investigation findings

### 3.1 Why the original "stage via run_tests.sh" approach was superseded

Issue body proposed building `eq/eq` + `tr/tr2` legacy binaries in CI and running `./test_run/run_tests.sh` to populate `test_output/`. That approach requires graphics libraries (`libg{3d,sp,dp}-gfc64`) not in standard Ubuntu apt repos. The fallback-fixture pattern (PR #149) avoided this complexity entirely; PR #195 and commit `615959e3` adopted it across tr/tot. The same approach finishes the job for sweep/fanout.

### 3.2 Multi-run fixture-write risk — empirically non-existent

Codex flagged that sweep/fanout call the Fortran library multiple times (9 cells × NTMAX=5 in sweep, paired runs per param in fanout), creating a theoretical risk of `cwd`-relative file writes polluting the committed fixture directory. Verified empirically (2026-06-07):

- `grep "OPEN(.*FILE=" eq/*.f90` returns only env-guarded debug dumps (`eqregress.f`, env var required) — no writes during normal `eq_run`.
- `grep "OPEN(.*FILE=" tr/*.f90` returns writes in `trfile.f90` (`KFNLOG`, `TRFLNM`) but those are tied to the legacy `tr2` binary's menu-driven `s` save command, not the `libtrapi.so` C ABI run path.
- Empirical sweep run: 9 cycles of `tr.run(5)` inside `python/trlib/tests/fixtures/` left the directory byte-identical (ls before/after `diff` exit 0, both 9-line listings).

Conclusion: `FIXTURES_DIR` is safe as `cwd` for sweep/fanout — no fixture pollution. No tmpdir-copy infrastructure needed.

### 3.3 Existing fixture files cover all three sites

| Site | Required fixture | Status |
|---|---|---|
| eq sweep | `python/eqlib/tests/fixtures/eqdata.ITER01` | ✅ committed |
| tr sweep | `python/trlib/tests/fixtures/eqdata.ITER01` | ✅ committed |
| tr fanout | `python/trlib/tests/fixtures/eqdata.TST-2` | ✅ committed |

## 4. Scope

### In scope

1. **`python/eqlib/tests/test_sweep.py`** — modify the inner-skipTest site (L117-123). Resolve `eqdata_dir` to `TEST_OUTPUT_DIR / "eq_iter01"` if present, else `FIXTURES_DIR` if `eqdata.ITER01` lives there, else `skipTest`. ~10 LOC change.

2. **`python/trlib/tests/test_sweep.py`** — replace the module-top constants `ITER01_WORKDIR` / `ITER01_EQDATA` and class-level `@skipUnless(ITER01_EQDATA.exists())` with a module-top resolver function `_resolve_iter01_cwd() -> Path | None` that returns either path or `None`. Keep `@skipUnless(ITER01_CWD is not None, "...")` at class level. Test body's `os.chdir(ITER01_CWD)` continues to work unchanged. ~20 LOC change.

3. **`python/trlib/tests/test_property_fanout.py`** — replace the static class attributes `WORKDIR` / `EQDATA` with a `@classmethod setUpClass(cls)` that resolves both. `_pushd(self.WORKDIR)` in the test body works unchanged because `WORKDIR` becomes the resolved value. Drop the `setUp` skipTest (now done at `setUpClass`-level via `raise unittest.SkipTest`). ~20 LOC change.

4. **Docstring updates** in each of the 3 files — update the "run `./test_run/run_tests.sh <case>` first" hint to "run `./test_run/run_tests.sh <case>` first (or rely on committed fixture under FIXTURES_DIR)".

### Out of scope

- `test_equivalence.py` refactor to use a shared helper (Approach B was rejected; YAGNI — the 4-module fallback inline pattern has been on develop for months without incident, refactoring it now is unrelated churn).
- Pollution-prevention infrastructure (verified empirically non-existent for the wrapper path).
- CI binary-build approach (`make -C eq eq` + `make -C tr tr2` + apt install graphics libs) — superseded by fallback-fixture per PR #149/#195 precedent.
- New committed fixtures (the 3 needed already exist).
- Updating `test_equivalence` (already works).

### Branch / PR

- Branch: `feat/sweep-fanout-fallback-192` from develop
- Single PR closing #192 via `Closes #192` keyword

## 5. Per-site implementation

### 5.1 `python/eqlib/tests/test_sweep.py`

**Current shape** (L117-123 area):

```python
eqdata_dir = TEST_OUTPUT_DIR / "eq_iter01"
knameq = eq_iter01_params.STRINGS.get("KNAMEQ", "eqdata.ITER01")
if not (eqdata_dir / knameq).exists():
    self.skipTest(
        f"eqdata '{knameq}' missing under {eqdata_dir}; "
        "run `./test_run/run_tests.sh eq_iter01` first."
    )
```

**After** (add `FIXTURES_DIR = HERE.parent / "fixtures"` at module-top alongside `TEST_OUTPUT_DIR`):

```python
candidate = TEST_OUTPUT_DIR / "eq_iter01"
knameq = eq_iter01_params.STRINGS.get("KNAMEQ", "eqdata.ITER01")
if (candidate / knameq).exists():
    eqdata_dir = candidate
elif (FIXTURES_DIR / knameq).exists():
    # CI / fresh checkout fallback: use committed fixture eqdata.
    eqdata_dir = FIXTURES_DIR
else:
    self.skipTest(
        f"eqdata '{knameq}' missing under {candidate} or {FIXTURES_DIR}; "
        "run `./test_run/run_tests.sh eq_iter01` first "
        "(or rely on committed fixture)."
    )
```

Rest of test body (`with _pushd(eqdata_dir):`) unchanged.

### 5.2 `python/trlib/tests/test_sweep.py`

**Current shape** (L36-62 area):

```python
TEST_OUTPUT_DIR = REPO / "test_run" / "test_output"
ITER01_WORKDIR = REPO / "test_run" / "test_output" / "tr_iter01"
ITER01_EQDATA = ITER01_WORKDIR / "eqdata.ITER01"

@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
@unittest.skipUnless(_trlib_importable(), "python/trlib not importable")
@unittest.skipUnless(
    ITER01_EQDATA.exists(),
    f"eqdata.ITER01 missing at {ITER01_EQDATA}; "
    "run `./test_run/run_tests.sh tr_iter01` first (requires eq_iter01).",
)
class TestSweep(unittest.TestCase):
    ...
        os.chdir(ITER01_WORKDIR)
```

**After**:

```python
FIXTURES_DIR = HERE.parent / "fixtures"
TEST_OUTPUT_DIR = REPO / "test_run" / "test_output"
KNAMEQ_ITER01 = "eqdata.ITER01"


def _resolve_iter01_cwd() -> Path | None:
    """Resolve cwd for tr_iter01: prefer dev-generated test_output, else committed FIXTURES_DIR."""
    candidate = TEST_OUTPUT_DIR / "tr_iter01"
    if (candidate / KNAMEQ_ITER01).exists():
        return candidate
    if (FIXTURES_DIR / KNAMEQ_ITER01).exists():
        return FIXTURES_DIR
    return None


ITER01_CWD = _resolve_iter01_cwd()


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
@unittest.skipUnless(_trlib_importable(), "python/trlib not importable")
@unittest.skipUnless(
    ITER01_CWD is not None,
    f"{KNAMEQ_ITER01} missing under {TEST_OUTPUT_DIR}/tr_iter01 or {FIXTURES_DIR}; "
    f"run `./test_run/run_tests.sh tr_iter01` first (or rely on committed fixture).",
)
class TestSweep(unittest.TestCase):
    ...
        os.chdir(ITER01_CWD)  # resolved at module load
```

Drop `ITER01_WORKDIR` and `ITER01_EQDATA` module constants entirely (replaced by `ITER01_CWD`).

### 5.3 `python/trlib/tests/test_property_fanout.py`

**Current shape** (L63-79 area):

```python
@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
@unittest.skipUnless(_trlib_importable(), "python/trlib not importable")
class TestTrlibFanoutParity(unittest.TestCase):
    """scalar-set vs element-set parity for PROFN1/PROFN2."""

    WORKDIR = TEST_OUTPUT_DIR / "tr_tst2"
    EQDATA = WORKDIR / "eqdata.TST-2"

    def setUp(self):
        if not self.EQDATA.exists():
            self.skipTest(
                f"eqdata missing at {self.EQDATA}; "
                "run `./test_run/run_tests.sh tr_tst2` first."
            )
```

**After** (add `FIXTURES_DIR = HERE.parent / "fixtures"` at module-top):

```python
@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
@unittest.skipUnless(_trlib_importable(), "python/trlib not importable")
class TestTrlibFanoutParity(unittest.TestCase):
    """scalar-set vs element-set parity for PROFN1/PROFN2."""

    WORKDIR: Path  # resolved by setUpClass
    EQDATA: Path

    @classmethod
    def setUpClass(cls):
        knameq = "eqdata.TST-2"
        candidate = TEST_OUTPUT_DIR / "tr_tst2"
        if (candidate / knameq).exists():
            cls.WORKDIR = candidate
        elif (FIXTURES_DIR / knameq).exists():
            cls.WORKDIR = FIXTURES_DIR
        else:
            raise unittest.SkipTest(
                f"{knameq} missing under {candidate} or {FIXTURES_DIR}; "
                "run `./test_run/run_tests.sh tr_tst2` first "
                "(or rely on committed fixture)."
            )
        cls.EQDATA = cls.WORKDIR / knameq
```

Drop the `setUp(self)` method entirely (the per-test skip check is now subsumed by `setUpClass`).

### 5.4 Skip-message and inline-comment updates

The user-visible skip-message strings in each of the 3 sites already get updated as part of the §5.1-5.3 code changes (each new `skipTest` / `@skipUnless` message references both `test_output/<case>/` and `FIXTURES_DIR` and points at "rely on committed fixture" as the alternative). No top-level module docstring rewrites are required — `python/trlib/tests/test_property_fanout.py` has no skip-related top docstring, and the other two files' top docstrings do not mention `test_output` paths. The inline comment "CI / fresh checkout fallback: use committed fixture eqdata." in §5.1 is the only new comment line; §5.2 and §5.3 changes are self-documenting via the resolver/setUpClass function bodies.

## 6. Verification plan

### 6.1 macOS local verification (pre-push)

**Pre-flight (mandatory):**

| Check | Command | Expected |
|---|---|---|
| 0a. Libs built | `ls eq/libeqapi.so tr/libtrapi.so` | Both files exist (else run `make -C eq libeqapi.so` and `make -C tr libtrapi.so`) |
| 0b. test_output **absent** (so fallback fires naturally) | `for d in eq_iter01 tr_iter01 tr_tst2; do [ ! -d test_run/test_output/$d ] && echo "$d absent ✓" \|\| { echo "$d PRESENT — move to /tmp first"; exit 1; }; done` | 3 lines of "absent ✓" |

**Main checks:**

| # | Check | Command | Expected |
|---|---|---|---|
| 1 | Resolver fallback unit smoke (tr sweep) | `PYTHONPATH=python python -c "from trlib.tests.test_sweep import _resolve_iter01_cwd, FIXTURES_DIR; assert _resolve_iter01_cwd() == FIXTURES_DIR; print('OK fallback')"` | `OK fallback` |
| 2 | Resolver priority-path verification via symlink | (see §6.1.2 below for full block) | `OK priority path: test_output preferred` + cleanup confirmation |
| 3 | Collection check | `PYTHONPATH=python pytest --collect-only -v python/{eqlib,trlib}/tests/test_sweep.py python/trlib/tests/test_property_fanout.py` | 3 test methods discovered, no ImportError |
| 4a | Pollution check — **capture pre-state** | `ls -la python/eqlib/tests/fixtures/ python/trlib/tests/fixtures/ > /tmp/fixtures_before.txt` | file created (no expected stdout) |
| 4b | **Main**: fallback path PASS | `PYTHONPATH=python pytest -v python/{eqlib,trlib}/tests/test_sweep.py python/trlib/tests/test_property_fanout.py --timeout=180` | 3 tests PASSED (verbose so names visible), no SKIPPED |
| 5 | Pollution check — **diff post-state** | `ls -la python/eqlib/tests/fixtures/ python/trlib/tests/fixtures/ > /tmp/fixtures_after.txt && diff /tmp/fixtures_before.txt /tmp/fixtures_after.txt` | exit 0 (no diff) |
| 6 | Full module regression | `PYTHONPATH=python pytest python/ --timeout=180 -q` | Existing PASS preserved |

#### 6.1.2 Step 2 priority-path full block

```bash
# Setup: simulate test_output presence via file-level symlink (resolver uses Path.exists which follows symlinks).
mkdir -p test_run/test_output/tr_iter01
ln -sf "$(pwd)/python/trlib/tests/fixtures/eqdata.ITER01" \
       test_run/test_output/tr_iter01/eqdata.ITER01

# Assert resolver picks test_output (not FIXTURES_DIR).
PYTHONPATH=python python -c "
from pathlib import Path
from trlib.tests.test_sweep import _resolve_iter01_cwd, TEST_OUTPUT_DIR
result = _resolve_iter01_cwd()
expected = TEST_OUTPUT_DIR / 'tr_iter01'
assert result == expected, f'expected {expected}, got {result}'
print('OK priority path: test_output preferred')
"

# Cleanup
rm -f test_run/test_output/tr_iter01/eqdata.ITER01
rmdir test_run/test_output/tr_iter01

# Re-verify 0b (absent state restored)
[ ! -d test_run/test_output/tr_iter01 ] && echo "cleanup OK"
```

Note: only `tr_sweep` exposes a module-top resolver function (per §5.2), so **step 1 (resolver smoke) and step 2 (priority-path symlink) cover only `tr_sweep`**. `eq_sweep` (§5.1) inlines its resolution inside the test body; `tr_fanout` (§5.3) inlines its resolution inside `setUpClass`. **Both `eq_sweep` and `tr_fanout` rely entirely on step 4 (the actual pytest run on the fallback path) for verification.** Step 3 (collection) and step 5 (pollution) cover all 3 sites uniformly.

### 6.2 Linux CI verification (canonical 1e-10)

Codex audit confirmed that `.github/workflows/python-tests.yml` builds the `.so` libs (L183-213) and stages output only for `tot_demo2014_short` / `tot_ht6m_short` (L243-287). No `run_tests.sh` invocation for `tr_iter01`, `tr_tst2`, or `eq_iter01`. So `test_output/<case>/eqdata.<DEV>` is **naturally absent on CI** — the FIXTURES_DIR fallback fires automatically once this fix lands.

PR description includes:

> **How to verify on Linux CI:** In the `python-tests.yml` pytest step, the following 3 tests must show as **PASSED** (not SKIPPED):
>
> - `python/eqlib/tests/test_sweep.py::TestSweep::test_3x3_grid_completes`
> - `python/trlib/tests/test_sweep.py::TestSweep::test_3x3_grid_completes`
> - `python/trlib/tests/test_property_fanout.py::TestTrlibFanoutParity::test_scalar_vs_elementwise_parity`
>
> CI runs with `--tb=short -ra` (`.github/workflows/python-tests.yml:323-329`); the `-ra` summary at the end of the pytest output lists all SKIPPED rows. **Verification: no SKIPPED row for any of the 3 test IDs above appears in the `-ra` summary.**

### 6.3 Pre-push gate

Same as PR #220 (CLAUDE.md non-negotiable):

1. macOS local pytest §6.1 step 4 + step 6 pass
2. `feature-dev:code-reviewer` (with fallback to `superpowers:code-reviewer` if unavailable)
3. `codex:codex-rescue` independent pass in parallel
4. Paste both reviewers' HIGH/MED findings to user, get agreement
5. `touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"`
6. `git push -u origin feat/sweep-fanout-fallback-192`
7. Wait for Bugbot COMPLETED before merge

### 6.4 Success criteria

- ✅ CI `-ra` summary contains zero SKIPPED rows for these 3 test IDs (CI runs `pytest --tb=short -ra` without `-v`, so PASSED rows appear as dots; the `-ra` summary is the authoritative SKIPPED enumeration)
- ✅ macOS local: no regression in existing PASS, FIXTURES_DIR byte-identical pre/post
- ✅ Bugbot COMPLETED
- ✅ #192 auto-closes via `Closes #192` in PR description (manual `gh issue close 192` backstop if needed)

## 7. Implementation hand-off

The next step is `superpowers:writing-plans` to produce a step-by-step implementation plan. Conventions resolved in this spec (writing-plans should not relitigate):

- **Branch name**: `feat/sweep-fanout-fallback-192`
- **3 sites**: eq sweep (per-test inline), tr sweep (module-top resolver), tr fanout (setUpClass)
- **Pattern**: mirror existing `test_equivalence._check_case` fallback (precedent: PR #149, PR #195, commit `615959e3`)
- **Fixtures**: 3 already committed (eq + tr × ITER01, tr × TST-2); no new files
- **No CI workflow changes** — this PR is pure Python changes to 3 test files

Open questions for writing-plans to resolve at implementation time (none currently — all design questions closed during brainstorming):

- (none — Codex cleared §1 / §2 / §3)

## 8. References

- Predecessor PRs: #149 (eq fallback initial), #195 (tr equiv mirror), commit `615959e3` (tot equiv mirror)
- PR #216 — Linux-canonical equivalence policy (`docs/baseline-policy.md`)
- Memory: `feedback_equivalence_must_pass.md` (no invisibility skips; principled platform-scoped skips OK)
- Memory: `feedback_never_skip_tests.md` (no `--ignore-glob`, no preemptive `skip.if`)
- Issue #192: https://github.com/k-yoshimi/task/issues/192
