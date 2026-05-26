# Platform-keyed equivalence baselines — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** End the macOS-developer-only `1e-10` equivalence false-positive class (Issue #213) without skipping tests, without tolerance fudging. Introduce platform-keyed baselines at `test_run/baselines/<case>/<os>-gcc<major>/metrics.json` with hard-fail when no exact key matches, and regenerate the 20 macOS Homebrew GCC 15.2.0 baselines so macOS dev sees true 1e-10 equivalence locally.

**Architecture:** New top-level helper `python/_baseline_select.py` (`platform_key()` + `select_baseline()`). Existing 20 flat-layout baselines moved via `git mv` into `<case>/linux-gcc13/` subdirectories. `test_run/scripts/check_regression.sh` lines 47-48 updated to resolve the platform-keyed subdirectory for both compare and `--generate-baseline` modes (the existing `mkdir -p` at line 65 already handles new-subdir creation per in-house spec review note). All 7 `test_equivalence.py` files (eqlib/trlib/tilib/fplib/wrlib/wrxlib/totlib) call `select_baseline()` instead of opening a flat path. macOS regen via the existing `run_tests.sh` + `check_regression.sh --generate-baseline` loop produces 20 new `macos-gcc15/metrics.json` files.

**Tech Stack:** Python 3.10+ stdlib (`platform`, `subprocess`, `re`, `functools.lru_cache`), pytest 8 + pytest-forked, bash for `run_tests.sh` + `check_regression.sh`, gfortran (Homebrew GCC 15.2.0 on macOS dev rig). No Fortran or C ABI changes.

**Spec:** `docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md` (Codex 3-round SHIP IT, develop @ `3807ecc3`).

**Branch base:** `origin/develop` at `3807ecc3` or later.

**Subagent-worktree discipline:** every git/make/test command shown with absolute path prefix or `-C` flag (per `feedback_codex_worktree_sharing.md`, recurring incident class).

---

## File Structure

**Created:**
- `python/_baseline_select.py` (~75 lines: `platform_key()` + `select_baseline()` + `__all__`).
- `python/totlib/tests/test_baseline_select.py` (~80 lines: 3 unit tests per spec §12).
- `docs/baseline-regeneration.md` (~80 lines: model + how-to + new-platform process).
- 20 × `test_run/baselines/<case>/macos-gcc15/metrics.json` (regenerated on dev rig).

**Modified:**
- `test_run/scripts/check_regression.sh` (lines 47-48 + line 65 nearby): resolve platform-keyed subdir in both compare and `--generate-baseline` modes.
- `python/eqlib/tests/test_equivalence.py`: replace flat-path open with `select_baseline()`.
- `python/trlib/tests/test_equivalence.py`: same.
- `python/tilib/tests/test_equivalence.py`: same.
- `python/fplib/tests/test_equivalence.py`: same.
- `python/wrlib/tests/test_equivalence.py`: same (Codex spec-review HIGH-3 catch).
- `python/wrxlib/tests/test_equivalence.py`: same.
- `python/totlib/tests/test_equivalence.py`: same.

**Renamed (via `git mv`):**
- 20 × `test_run/baselines/<case>/metrics.json` → `<case>/linux-gcc13/metrics.json`.

**Untouched (load-bearing, do NOT change):**
- `test_run/scripts/compare_metrics.py` — tolerance stays `1e-10` per spec §3 out-of-scope.
- `.github/workflows/python-tests.yml` — whole-tree pytest at line 323 already covers new layout (no new test step needed).
- `.github/workflows/regen-baselines.yml` — fp/ti/wr/wrx exclusion stays per spec §3 out-of-scope (structural binary-build gap, separate PR).
- All Fortran source.

---

## Task 0: Worktree + baseline build

Working directory throughout this task: `/Users/k-yoshimi/Dropbox/cursor/task` (main checkout).

- [ ] **Step 1: Sync develop**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git fetch origin develop --quiet
git checkout develop
git pull --quiet
git log --oneline -1
```

Expected: HEAD ≥ `3807ecc3 docs(spec): platform-keyed equivalence baselines (#213)`.

- [ ] **Step 2: Create worktree**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git worktree add .claude/worktrees/platform-keyed-baselines \
                  -b platform-keyed-baselines origin/develop
```

- [ ] **Step 3: Copy build-config artifacts**

```bash
cp /Users/k-yoshimi/Dropbox/cursor/task/make.header \
   /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines/make.header
cp /Users/k-yoshimi/Dropbox/cursor/task/mtxp/make.mtxp \
   /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines/mtxp/make.mtxp
ls -l /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines/make.header \
      /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines/mtxp/make.mtxp
```

- [ ] **Step 4: Verify bpsd symlink**

```bash
readlink /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/bpsd
```

Expected: `/Users/k-yoshimi/Dropbox/cursor/bpsd` (already created in prior sessions). If missing: `ln -s /Users/k-yoshimi/Dropbox/cursor/bpsd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/bpsd`.

- [ ] **Step 5: Build all `lib<mod>api.so` files (needed for macOS regen in Task 3)**

The macOS baseline regen in Task 3 calls `run_tests.sh` which invokes per-module standalone binaries (e.g. `tot/tot`, `fp/fp`). Build those plus the .so libs the equiv tests load:

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
# Full PIC chain (per PR-A/PR-B plan pattern):
make -C lib  libtask_pic.a libgrf_pic.a libmds_pic.a
make -C mtxp libmtxnompi_pic.o libmtxbnd_pic.o
make -C tr   bpsd_pic
make -C pl   libpl_noeq_pic
make -C eq   libeq_pic.a
make -C pl   libpl_pic.a
make -C dp   libdp_pic.a
make -C ob   libob_pic.a
make -C open-adas/adf11/adf11-lib lib-adf11_pic.a
make -C adpost lib-adpost_pic.a
make -C eq  libeqapi.so
make -C tr  libtrapi.so
make -C fp  libfpapi.so
make -C ti  libtiapi.so
make -C wr  libwrapi.so
make -C wrx libwrxapi.so
make -C tot libtotapi.so libtotapi_mono.so
# Standalone binaries for run_tests.sh:
make -C tot tot
make -C fp  fp
make -C ti  ti
make -C tr  tr
make -C eq  eqx2     # eqlib standalone uses eqx2
make -C wr  wr
make -C wrx wrx
ls -l eq/libeqapi.so tr/libtrapi.so fp/libfpapi.so ti/libtiapi.so \
      wr/libwrapi.so wrx/libwrxapi.so tot/libtotapi.so tot/libtotapi_mono.so
ls -l tot/tot fp/fp ti/ti tr/tr eq/eqx2 wr/wr wrx/wrx 2>&1 | head -20
```

Expected: every `lib*.so` and standalone binary present. If a standalone build target name is wrong (e.g. `eqx2` vs `eq`), check `<module>/Makefile` for the actual binary target name and substitute. (Cross-reference per `test_run/run_tests.sh` line ~50-80 where each module's binary is invoked — if you see `cd eq && ./eqx2 < ...` then the target is `eqx2`.)

- [ ] **Step 6: Baseline sanity — existing equivalence tests run cleanly on the worktree (before any changes)**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    eqlib/tests/test_equivalence.py \
    trlib/tests/test_equivalence.py \
    tilib/tests/test_equivalence.py \
    fplib/tests/test_equivalence.py \
    wrlib/tests/test_equivalence.py \
    wrxlib/tests/test_equivalence.py \
    totlib/tests/test_equivalence.py 2>&1) | tail -15
```

Expected on macOS today: eqlib/trlib/tilib/totlib pass; fplib + wrxlib fail (the #213 failures: `fp_dt1`, `fp_iter01`, `wrx_demo`, `wrx_iter01`). `wrlib` status unknown today — record it from this run for later comparison. Note the exact pass/fail count for the cumulative regression check in Task 4 Step 7.

---

## Task 1: Helper module + unit tests (TDD)

**Files:**
- Create: `python/_baseline_select.py`
- Create: `python/totlib/tests/test_baseline_select.py`

- [ ] **Step 1: Write the failing unit tests first**

Create `python/totlib/tests/test_baseline_select.py`:

```python
"""Unit tests for python/_baseline_select.py.

Pins the platform-key formula + select_baseline()'s hard-fail
contract from spec §6, independent of the per-module
test_equivalence.py integration tests that consume the helper.

Module-level pytest.mark.forked because the helper's
@functools.lru_cache on platform_key() bleeds across in-process
tests; forking gives each test a fresh process state.

Spec: docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

import pytest

pytestmark = [pytest.mark.forked]

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


class TestPlatformKey(unittest.TestCase):
    """platform_key() returns a normalized {os}-gcc{major} string."""

    def test_platform_key_format(self):
        from _baseline_select import platform_key

        key = platform_key()
        self.assertRegex(
            key,
            r"^(linux|macos|windows|freebsd|openbsd|sunos|aix)-gcc\d+$",
            f"platform_key returned malformed key: {key!r}",
        )


class TestSelectBaseline(unittest.TestCase):
    """select_baseline() resolves <case>/<platform-key>/metrics.json
    or hard-fails with an actionable message (spec §4 D-2)."""

    def test_returns_existing_file(self):
        import tempfile
        from _baseline_select import platform_key, select_baseline

        with tempfile.TemporaryDirectory() as td:
            case_dir = Path(td) / "fake_case"
            key = platform_key()
            (case_dir / key).mkdir(parents=True)
            metrics_path = case_dir / key / "metrics.json"
            metrics_path.write_text('{"scalars": {}}')

            resolved = select_baseline(case_dir)
            self.assertEqual(resolved, metrics_path)

    def test_hard_fails_when_missing(self):
        import tempfile
        from _baseline_select import select_baseline

        with tempfile.TemporaryDirectory() as td:
            case_dir = Path(td) / "fake_case"
            # Populate an UNRELATED platform-key subdir so the
            # error message has something to enumerate in "Available
            # platforms".
            (case_dir / "freebsd-gcc99").mkdir(parents=True)
            (case_dir / "freebsd-gcc99" / "metrics.json").write_text("{}")

            with self.assertRaises(FileNotFoundError) as ctx:
                select_baseline(case_dir)
            msg = str(ctx.exception)
            self.assertIn("Available platforms:", msg,
                          f"missing 'Available platforms:' in {msg!r}")
            self.assertIn("freebsd-gcc99", msg)
            self.assertIn("Regenerate", msg,
                          f"missing 'Regenerate' remedy in {msg!r}")
            self.assertIn("Do NOT silently fall back", msg,
                          "missing the explicit no-fallback warning")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
```

- [ ] **Step 2: Verify tests FAIL (no helper yet)**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    totlib/tests/test_baseline_select.py -v 2>&1) | tail -15
```

Expected: 3 ERROR with `ModuleNotFoundError: No module named '_baseline_select'`.

- [ ] **Step 3: Create the helper module**

Create `python/_baseline_select.py`:

```python
"""Resolve the equivalence baseline for the current runtime platform.

Owns the (os, gcc-major) platform-key contract introduced in
docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md
(#213). Tests at python/<mod>/tests/test_equivalence.py consume
the resolved path via select_baseline(); if no baseline matches
the runtime platform the test HARD FAILS with an actionable
message — skip would be invisibility per
feedback_equivalence_must_pass.md, soft fallback would
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
    `gfortran --version` — the trailing `\\) <major>.<minor>`
    pattern after the parenthetical vendor tag is the stable
    element across:

      Homebrew macOS:  'GNU Fortran (Homebrew GCC 15.2.0_1) 15.2.0'
      Ubuntu/Debian:   'GNU Fortran (Ubuntu 13.3.0-...) 13.3.0'
                       'GNU Fortran (Debian 12.2.0-14) 12.2.0'
      RHEL/Fedora:     'GNU Fortran (GCC) 11.4.1 20231218 ...'

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
    baseline matches the runtime platform. See spec §6.
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
        f"     <case>/{key}/metrics.json. See\n"
        "     docs/baseline-regeneration.md.\n"
        "  2. Use the CI canonical compiler (gfortran 13 on Linux\n"
        "     glibc) so your output matches the committed\n"
        "     linux-gcc13 baseline.\n"
        f"  3. Submit your '{key}' baselines as a PR after a\n"
        "     manual physics audit comparing to linux-gcc13.\n"
        "Do NOT silently fall back to a foreign-platform baseline\n"
        "— that would re-introduce the cross-platform false-positive\n"
        "this design eliminates."
    )


__all__ = ["platform_key", "select_baseline"]
```

- [ ] **Step 4: Verify tests PASS**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    totlib/tests/test_baseline_select.py -v 2>&1) | tail -10
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines add \
    python/_baseline_select.py \
    python/totlib/tests/test_baseline_select.py
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines commit -m "$(cat <<'EOF'
feat(python): _baseline_select helper for platform-keyed equivalence (#213)

Adds python/_baseline_select.py with platform_key() and
select_baseline(). Resolves test_run/baselines/<case>/<os>-gcc<maj>/
metrics.json per spec §6. Hard-fails with actionable message when
no exact key matches (skip would be invisibility per
feedback_equivalence_must_pass.md; soft fallback would re-introduce
the cross-platform false-positive this design eliminates).

platform_key() parses gfortran --version's trailing `\) <major>.<minor>`
pattern, robust across Homebrew/Ubuntu/Debian/RHEL distros (Codex
spec-review HIGH-2). Result lru_cache'd; subprocess overhead paid
once per Python process.

Test cases per spec §12: format regex, returns-existing-file,
hard-fails-when-missing (asserts "Available platforms:",
"Regenerate", and "Do NOT silently fall back" in the error
message). pytest.mark.forked module-level for cache isolation.

Per-module test_equivalence.py wiring + the existing baseline
migration follow in the next commits.

Spec: docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Documentation (`docs/baseline-regeneration.md`)

**Files:**
- Create: `docs/baseline-regeneration.md`

Written BEFORE the migration commit so the migration's commit-message can reference it as already-landed (and so the helper's error message points at a real file).

- [ ] **Step 1: Create the documentation**

Create `docs/baseline-regeneration.md`:

```markdown
# Baseline regeneration (equivalence tests)

The Layer-1 equivalence tests
(`python/<mod>/tests/test_equivalence.py`) compare a freshly-replayed
`lib<mod>api.so` output against a baseline `metrics.json` at relative
tolerance `1e-10`. The baseline is stored under a **platform key**
that captures the (OS, gcc-major) tuple of the host that generated
it:

```
test_run/baselines/<case>/<os>-gcc<major>/metrics.json
```

Examples: `linux-gcc13/` (clavius, CI canonical), `macos-gcc15/`
(Homebrew GCC 15.2.0 dev rig).

## Why this exists

`compare_metrics.py` uses one hard-coded tolerance: `1e-10` relative.
Floating-point output drifts past that tolerance across:

- libm implementations (Apple BSD vs glibc): single ULP differences
  in transcendentals (exp, log, sin, cos, Bessel).
- gfortran major versions: codegen differences in math intrinsics.
- iteration-heavy solvers (FP collision operator, ray-tracing) amplify
  the per-step drift into multi-decade rel_err blowups.

Single-flat-baseline design forced "either match Linux clavius
output or fail" — which failed on every macOS dev machine and was
the recurring `feedback_equivalence_must_pass.md` discipline
breach. Platform-keyed baselines preserve the strict 1e-10 contract
WITHIN a platform while making cross-platform expectation honest.

## Determining your platform key

```bash
python -c "from _baseline_select import platform_key; print(platform_key())"
```

Examples:
- `linux-gcc13` (clavius, CI canonical)
- `macos-gcc15` (Homebrew Apple Silicon dev rig)

## When you see a "No baseline for platform" error

`select_baseline()` hard-fails when your runtime platform key has
no committed baseline. Three remedies (most → least preferred):

1. **Use the canonical compiler.** Install gfortran 13 on Linux
   glibc (Ubuntu / Debian / RHEL) so your output matches the
   committed `linux-gcc13/` baseline. CI uses this and most
   contributors should too.
2. **Regenerate baselines for your platform.** For each case:
   ```bash
   bash test_run/run_tests.sh <case>
   bash test_run/scripts/check_regression.sh \
        <case> test_run/test_output/<case> \
        test_run/baselines 1e-10 --generate-baseline
   ```
   This writes `test_run/baselines/<case>/<your-key>/metrics.json`.
   Loop over all 20 cases (see §macOS regen flow below).
3. **Add a new supported platform.** Commit your `<your-key>/`
   baselines as a PR with a manual physics-audit appendix comparing
   one or two scalars per case against the existing `linux-gcc13`
   baseline. Rel_err under 5e-9 = libm-drift class (likely OK);
   under 1e-7 with a reasoned justification per scalar = borderline;
   over 1e-7 = real bug, do not commit until investigated.

**Never use soft fallback.** Reading a foreign-platform baseline
silently re-introduces the false-positive class this design
eliminates.

## macOS regen flow (20 cases)

```bash
cd /path/to/task
for case in eq_iter01 eq_jt60 eq_tst2 \
            fp_dt1 fp_iter01 fp_jt60 \
            ti_ar ti_min ti_w \
            tot_demo2014_short tot_ht6m_short \
            tr_iter01 tr_m0904 tr_tst2 \
            wr_iter_lhcd wr_test001 wr_tst2_ec \
            wrx_demo wrx_iter01 wrx_jt60 ; do
    bash test_run/run_tests.sh "$case"
    bash test_run/scripts/check_regression.sh \
         "$case" \
         "test_run/test_output/$case" \
         "test_run/baselines" \
         1e-10 \
         --generate-baseline
done
```

## File layout

```
test_run/baselines/
  <case>/
    linux-gcc13/metrics.json    # CI canonical
    macos-gcc15/metrics.json    # macOS dev rig (Homebrew GCC 15.x)
    # ... more platforms as contributors add them
```

The platform key formula is `{platform.system().lower(), gcc-major}`
where `darwin` is normalized to `macos`. See
`python/_baseline_select.py:platform_key()` for the canonical
implementation.

## Adding a new platform

1. Run `python -c "from _baseline_select import platform_key; print(platform_key())"`
   to see your key.
2. Generate baselines for all 20 cases via the loop above.
3. Spot-compare 1-2 scalars per case against the existing
   `linux-gcc13` baseline to verify drift magnitudes match the
   expected libm-drift class (< 5e-9 typically; > 1e-7 is a red
   flag).
4. Submit a PR with the new `<your-key>/` baselines + a physics
   audit appendix in the PR description.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines add docs/baseline-regeneration.md
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines commit -m "$(cat <<'EOF'
docs: baseline regeneration guide (#213)

New file docs/baseline-regeneration.md documents the (os, gcc-major)
platform-key model, the hard-fail no-soft-fallback policy, how to
determine your platform key, the three remedies the
select_baseline() error message refers to, and the 20-case macOS
regen loop. Committed before the migration commit so the helper's
error message references a file that already exists.

Spec: docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Migration — `git mv` + `check_regression.sh` + 7 `test_equivalence.py`

This is the structural commit. After it: CI Linux green (linux-gcc13
baselines exist), macOS hard-fails for all 7 modules (no macos-gcc15
baselines yet — added in Task 4).

**Files:**
- Modify: `test_run/scripts/check_regression.sh` (~3-line patch around lines 47-48)
- Renamed: 20 × `test_run/baselines/<case>/metrics.json` → `<case>/linux-gcc13/metrics.json`
- Modify: 7 × `python/<mod>/tests/test_equivalence.py`

- [ ] **Step 1: Migrate flat baselines to linux-gcc13/**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
for case_dir in test_run/baselines/*/; do
    case_name="${case_dir%/}"
    case_name="${case_name##*/}"
    flat="test_run/baselines/${case_name}/metrics.json"
    if [ -f "$flat" ]; then
        mkdir -p "test_run/baselines/${case_name}/linux-gcc13"
        git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines mv \
            "$flat" \
            "test_run/baselines/${case_name}/linux-gcc13/metrics.json"
    fi
done
find test_run/baselines -name metrics.json | wc -l
find test_run/baselines -name metrics.json -type f | head -5
```

Expected: 20 files renamed; the count of `metrics.json` files stays
at 20; the head listing shows paths ending in `linux-gcc13/metrics.json`.

- [ ] **Step 2: Update `test_run/scripts/check_regression.sh`**

Locate the line `METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"`
(line 48). It must become platform-key-aware. Modify the script as follows:

Before the existing line 48, INSERT a block that resolves the
platform key via the same shell-side logic the Python helper uses:

```bash
# Resolve platform-keyed subdirectory (per #213 spec §6).
# Matches python/_baseline_select.py::platform_key() exactly.
_os_name=$(uname -s | tr '[:upper:]' '[:lower:]')
case "$_os_name" in
    darwin) _os_key=macos ;;
    *)      _os_key="$_os_name" ;;
esac
_gcc_major=$(gfortran --version 2>/dev/null \
    | head -1 \
    | sed -E 's/.*\)\s+([0-9]+)\.[0-9]+.*/\1/')
if [ -z "$_gcc_major" ] || ! echo "$_gcc_major" | grep -qE '^[0-9]+$'; then
    echo "ERROR: cannot determine gfortran major version" >&2
    echo "       gfortran --version output:" >&2
    gfortran --version >&2 2>&1 || echo "       (gfortran not on PATH)" >&2
    exit 2
fi
PLATFORM_KEY="${_os_key}-gcc${_gcc_major}"
```

Then change line 48 from:

```bash
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"
```

to:

```bash
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/$PLATFORM_KEY/metrics.json"
```

The existing `mkdir -p "$(dirname "$METRICS_BASE")"` at line 65
(per in-house spec-review note) already handles the new subdirectory
creation for `--generate-baseline` mode, so no further changes
are needed there.

- [ ] **Step 3: Verify `check_regression.sh` resolves the right path**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
# Dry-run resolution check (compare mode would fail because we
# haven't built any test_output yet; we just check the platform key
# is correctly substituted):
bash -x test_run/scripts/check_regression.sh \
    tot_demo2014_short \
    /tmp/nonexistent_test_output \
    test_run/baselines \
    1e-10 2>&1 | grep "METRICS_BASE\|PLATFORM_KEY" | head -5
```

Expected: a line like `+ METRICS_BASE=test_run/baselines/tot_demo2014_short/macos-gcc15/metrics.json` (or whatever your local key is). The script will still fail downstream because the output directory doesn't exist — that's expected. We're only verifying the path computation.

- [ ] **Step 4: Update 7 `test_equivalence.py` files — eqlib pattern**

For `python/eqlib/tests/test_equivalence.py`, locate the line that opens the baseline (typically `baseline_path = BASELINES_DIR / case_name / "metrics.json"` or passed via the `--baseline` arg to `compare_metrics.py`). The exact form differs per module but the change pattern is identical:

Before:
```python
BASELINES_DIR = REPO / "test_run" / "baselines"
# ... somewhere later ...
baseline_path = BASELINES_DIR / case_name / "metrics.json"
```

After:
```python
from _baseline_select import select_baseline  # top-level
BASELINES_DIR = REPO / "test_run" / "baselines"
# ... somewhere later ...
baseline_path = select_baseline(BASELINES_DIR / case_name)
```

Top-level import per spec §10 (same reasoning as PR-A's spec R-3).

Apply this transformation to all 7 files:
- `python/eqlib/tests/test_equivalence.py`
- `python/trlib/tests/test_equivalence.py`
- `python/tilib/tests/test_equivalence.py`
- `python/fplib/tests/test_equivalence.py`
- `python/wrlib/tests/test_equivalence.py`
- `python/wrxlib/tests/test_equivalence.py`
- `python/totlib/tests/test_equivalence.py`

The exact line numbers + variable names differ per file; locate via:
```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
for f in python/{eqlib,trlib,tilib,fplib,wrlib,wrxlib,totlib}/tests/test_equivalence.py; do
    echo "=== $f ==="
    grep -nE 'BASELINES_DIR|metrics\.json|baseline_path|--baseline' "$f" | head -10
done
```

If a file constructs the path via subprocess args (e.g.
`--baseline=str(BASELINES_DIR / case_name / "metrics.json")`), wrap
the path in `select_baseline()` instead. Add the top-level
`from _baseline_select import select_baseline` near the existing
imports.

- [ ] **Step 5: Verify Linux baseline path resolves correctly in tests**

On macOS dev rig, the eq/tr/ti/tot tests would historically pass at
1e-10 against linux-gcc13 baselines (drift was within tolerance for
those single-shot solvers). After Task 3, on macOS, ALL tests will
hard-fail because `select_baseline()` looks for `macos-gcc15/` which
doesn't exist yet.

That is the EXPECTED state after Task 3. Don't run the full
equivalence suite here — it will produce a confusing "all fail" log
that's correct-but-misleading. Instead, verify the helper resolves
linux-gcc13 correctly on a hypothetical Linux runtime by manually
constructing the path:

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
ls test_run/baselines/tot_demo2014_short/linux-gcc13/metrics.json
```

Expected: file exists (just moved into place by Task 3 Step 1).

- [ ] **Step 6: Commit (large but atomic migration)**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines add \
    test_run/baselines \
    test_run/scripts/check_regression.sh \
    python/eqlib/tests/test_equivalence.py \
    python/trlib/tests/test_equivalence.py \
    python/tilib/tests/test_equivalence.py \
    python/fplib/tests/test_equivalence.py \
    python/wrlib/tests/test_equivalence.py \
    python/wrxlib/tests/test_equivalence.py \
    python/totlib/tests/test_equivalence.py
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines status --short
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines commit -m "$(cat <<'EOF'
refactor(equiv): platform-keyed baseline layout (#213 part 2/3)

Migrates 20 flat-layout baselines to <case>/linux-gcc13/metrics.json
via git mv. The data is unchanged — these baselines were generated
on Linux gfortran 13.3.0 (clavius, per reference_clavius_baseline_regen.md)
and the new directory name simply records that provenance.

check_regression.sh resolves the platform-keyed subdirectory in
both compare and --generate-baseline modes. The shell-side
platform_key derivation matches python/_baseline_select.py exactly
(same os normalization, same trailing `\) <maj>.<min>` regex).
Existing mkdir -p at line 65 already handles new-subdir creation
for --generate-baseline mode (in-house spec-review note).

All 7 test_equivalence.py files (eqlib/trlib/tilib/fplib/wrlib/
wrxlib/totlib) now call select_baseline() instead of opening
flat-path metrics.json. Top-level import per spec §10 / PR-A R-3.

After this commit:
  - CI Linux (Ubuntu gfortran 13.x): all 7 equiv suites stay green.
    select_baseline() finds <case>/linux-gcc13/metrics.json.
  - macOS dev rig (Homebrew GCC 15.x): all 7 equiv suites HARD FAIL
    with "No baseline for platform 'macos-gcc15'" because the
    macos-gcc15/ baselines don't exist yet. This is intentional and
    resolved by the next commit (macOS regen).

Spec: docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: macOS baseline regeneration (20 cases)

**Files:**
- Create: 20 × `test_run/baselines/<case>/macos-gcc15/metrics.json`

- [ ] **Step 1: Record gfortran version for PR description**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
gfortran --version | head -2
python -c "from _baseline_select import platform_key; print(platform_key())"
```

Save both outputs verbatim — they go in the PR description per spec §13 R-1.

- [ ] **Step 2: Run the 20-case regen loop**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
for case in eq_iter01 eq_jt60 eq_tst2 \
            fp_dt1 fp_iter01 fp_jt60 \
            ti_ar ti_min ti_w \
            tot_demo2014_short tot_ht6m_short \
            tr_iter01 tr_m0904 tr_tst2 \
            wr_iter_lhcd wr_test001 wr_tst2_ec \
            wrx_demo wrx_iter01 wrx_jt60 ; do
    echo "=== $case ==="
    bash test_run/run_tests.sh "$case"
    bash test_run/scripts/check_regression.sh \
         "$case" \
         "test_run/test_output/$case" \
         "test_run/baselines" \
         1e-10 \
         --generate-baseline 2>&1 | tail -3
done
ls test_run/baselines/*/macos-gcc15/metrics.json | wc -l
```

Expected: `20` macos-gcc15 metrics.json files generated.

If any case fails to run_tests.sh (e.g., missing standalone binary,
namelist parse error), record the failing case + error message and
STOP. Surface to controller for triage. Per spec R-1: a real bug
masquerading as drift is a red flag and must be investigated
before commit.

- [ ] **Step 3: R-1 spot-comparison sanity check**

For 4 known-drifting cases (the #213 failures + 1 control), assert
the rel_err between linux-gcc13 and macos-gcc15 baselines is in the
expected libm-drift class (< 5e-9 per spec R-1):

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
for case in fp_dt1 fp_iter01 wrx_demo wrx_iter01; do
    echo "=== $case ==="
    python test_run/scripts/compare_metrics.py \
        "test_run/baselines/$case/linux-gcc13/metrics.json" \
        "test_run/baselines/$case/macos-gcc15/metrics.json" \
        --tolerance 5e-9 2>&1 | tail -8
done
```

Expected: each comparison shows FAIL at 5e-9 with rel_err in the
1e-10..5e-9 range (matching the #213 ticket — fp_iter01 worst case
4.447e-9, wrx_iter01 pwr_tot 1.382e-9). If any case shows rel_err
≥ 5e-9 with no clear physical explanation, STOP and surface to
controller — that's the red-flag class from R-1.

Also do a `>= 1e-7` hard-fail check across all 20 cases:

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
for case in eq_iter01 eq_jt60 eq_tst2 \
            fp_dt1 fp_iter01 fp_jt60 \
            ti_ar ti_min ti_w \
            tot_demo2014_short tot_ht6m_short \
            tr_iter01 tr_m0904 tr_tst2 \
            wr_iter_lhcd wr_test001 wr_tst2_ec \
            wrx_demo wrx_iter01 wrx_jt60 ; do
    result=$(python test_run/scripts/compare_metrics.py \
        "test_run/baselines/$case/linux-gcc13/metrics.json" \
        "test_run/baselines/$case/macos-gcc15/metrics.json" \
        --tolerance 1e-7 2>&1 | grep -E "FAIL|OK" | head -1)
    echo "$case: $result"
done
```

Expected: every case shows `OK: metrics match within tol=1e-07`.
Any FAIL is an unconditional red flag (real bug, not libm drift) —
STOP and surface.

- [ ] **Step 4: Run the equivalence test suite on macOS — should now be ALL GREEN**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    eqlib/tests/test_equivalence.py \
    trlib/tests/test_equivalence.py \
    tilib/tests/test_equivalence.py \
    fplib/tests/test_equivalence.py \
    wrlib/tests/test_equivalence.py \
    wrxlib/tests/test_equivalence.py \
    totlib/tests/test_equivalence.py 2>&1) | tail -15
```

Expected: ALL 7 modules pass. The 4 originally-failing fp/wrx tests
(`fp_dt1`, `fp_iter01`, `wrx_demo`, `wrx_iter01`) now pass against
the macos-gcc15 baselines — #213 closed locally.

- [ ] **Step 5: Commit (20 baseline files + verification record)**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines add test_run/baselines
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines status --short
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines commit -m "$(cat <<'EOF'
feat(equiv): macos-gcc15 baselines (20 cases) — closes #213

Adds test_run/baselines/<case>/macos-gcc15/metrics.json for all 20
cases (eq/fp/ti/tot/tr/wr/wrx). Generated on:

  gfortran: GNU Fortran (Homebrew GCC 15.2.0_1) 15.2.0
  platform_key(): macos-gcc15

via the documented loop (docs/baseline-regeneration.md). All 7
test_equivalence.py suites now pass on macOS at 1e-10 against the
macos-gcc15 baselines — the 4 originally-failing fp/wrx tests in
#213 (fp_dt1, fp_iter01, wrx_demo, wrx_iter01) close.

R-1 spot-comparison (linux-gcc13 vs macos-gcc15):
  fp_dt1.RPCT[0]:    rel_err = 2.354e-10 (well under 5e-9 threshold)
  fp_iter01 worst:   rel_err = 4.447e-9  (just under 5e-9 threshold)
  wrx_demo:          rel_err = 2.238e-9
  wrx_iter01.pwr_tot: rel_err = 1.382e-9

All 20 cases verified < 1e-7 (the unconditional hard-fail
threshold). No real-bug-masquerading-as-drift signature detected.

Linux CI continues to use linux-gcc13 baselines unchanged; pure
data addition for macOS coverage.

Spec: docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md
Closes #213

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

The exact rel_err numbers in the commit body MAY differ slightly from those shown above (they're from the original #213 reproduction). Substitute the actual numbers from the Task 4 Step 3 output.

---

## Task 5: Pre-push gate + push + PR + Bugbot wait + merge

**Files:** none edited; controller-side workflow.

- [ ] **Step 1: Controller-side tripwire — main checkout clean**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git status --short && git branch --show-current
git log --oneline origin/develop..HEAD
```

Expected: branch=develop; origin/develop..HEAD empty (no commits accidentally landed on main checkout's develop). Per `feedback_codex_worktree_sharing.md`.

- [ ] **Step 2: Final cumulative test pass from the worktree**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal \
    eqlib/tests/test_equivalence.py \
    trlib/tests/test_equivalence.py \
    tilib/tests/test_equivalence.py \
    fplib/tests/test_equivalence.py \
    wrlib/tests/test_equivalence.py \
    wrxlib/tests/test_equivalence.py \
    totlib/tests/test_equivalence.py \
    totlib/tests/test_baseline_select.py 2>&1) | tail -15
```

Expected: all green (7 equiv suites + 3 unit tests).

- [ ] **Step 3: Launch BOTH reviewers in parallel**

In a single tool-call message fire:

- `Agent(subagent_type="general-purpose", model="sonnet", description="In-house cumulative review", prompt=…)` — anchor: plan adherence + spec §14 acceptance criteria.
- `Agent(subagent_type="codex:codex-rescue", description="Codex independent review", prompt=…)` — anchor: cross-cutting code quality, regex robustness, R-1 audit verification.

Reviewer prompts give: working dir `/Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines`, branch `platform-keyed-baselines`, HEAD = latest commit, base `origin/develop @ 3807ecc3`, spec path.

Paste HIGH / MED findings back. Iterate with fix-up commits if any.

- [ ] **Step 4: Pre-push marker**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
HEAD_SHA=$(git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines rev-parse HEAD)
touch "$(git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines rev-parse --git-common-dir)/REVIEW_OK_$HEAD_SHA"
```

- [ ] **Step 5: Push**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines
unset GITHUB_TOKEN
git -C /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/platform-keyed-baselines push -u origin platform-keyed-baselines
```

- [ ] **Step 6: Create the PR**

```bash
unset GITHUB_TOKEN
gh pr create --base develop --title "feat(equiv): platform-keyed baselines + macos-gcc15 (#213)" --body "$(cat <<'EOF'
## Summary

Closes #213. Ends the macOS-developer-only `1e-10` equivalence
false-positive class without skipping tests or fudging tolerances.
Introduces platform-keyed baselines at
`test_run/baselines/<case>/<os>-gcc<major>/metrics.json` with
hard-fail when no exact key matches; regenerates the 20 macOS
Homebrew GCC 15.2.0 baselines so macOS dev sees true 1e-10
equivalence locally.

## What's in this PR (4 commits)

1. **`feat(python): _baseline_select helper`** — `platform_key()` +
   `select_baseline()` with cross-distro `gfortran --version` parser
   (Homebrew + Ubuntu + Debian + RHEL). 3 unit tests.
2. **`docs: baseline regeneration guide`** — `docs/baseline-regeneration.md`
   model + how-to + new-platform PR process. Committed before the
   migration so the helper's error message references a real file.
3. **`refactor(equiv): platform-keyed baseline layout`** — git mv
   20 flat baselines to `<case>/linux-gcc13/`, update
   `check_regression.sh` to resolve platform-keyed paths, wire all 7
   `test_equivalence.py` to call `select_baseline()`.
4. **`feat(equiv): macos-gcc15 baselines (20 cases) — closes #213`** —
   regenerated on Homebrew GCC 15.2.0; R-1 spot-comparisons in
   commit body show all rel_err < 5e-9 (no real-bug-masquerading-
   as-drift signature). All 7 test_equivalence.py suites now pass
   on macOS at 1e-10.

## R-1 audit (linux-gcc13 vs macos-gcc15)

(Implementer substitutes actual numbers from Task 4 Step 3 here.)

  fp_dt1.RPCT[0]:     rel_err = 2.354e-10
  fp_iter01 worst:    rel_err = 4.447e-9
  wrx_demo:           rel_err = 2.238e-9
  wrx_iter01.pwr_tot: rel_err = 1.382e-9
  ... (all 20 cases verified < 1e-7 unconditional threshold)

## Acceptance (spec §14)

- [x] `python/_baseline_select.py` exists per §6.
- [x] 20 baselines migrated flat → `linux-gcc13/`.
- [x] 20 `macos-gcc15/metrics.json` exist with R-1 audit appendix.
- [x] All 7 `test_equivalence.py` call `select_baseline()`.
- [x] `check_regression.sh` resolves platform-keyed subdir.
- [x] `docs/baseline-regeneration.md` exists.
- [x] 3 unit tests pass.
- [x] All previously-passing equiv tests still pass on the same
      platforms locally (post-push CI confirms Linux side).

## Out of scope

- macOS CI job (cost — `python-tests.yml` continues to be Linux-only).
- Other platforms (Windows, gcc14, etc.) — added via the documented
  new-platform PR process.
- `regen-baselines.yml` extension for fp/ti/wr/wrx (separate concern
  — needs binary-build infrastructure).
- Fortran source changes.

## Spec + Plan

- Spec: `docs/superpowers/specs/2026-05-26-platform-keyed-baselines-design.md`
- Plan: `docs/superpowers/plans/2026-05-26-platform-keyed-baselines-implementation.md`

## Test plan

- [ ] CI green on `python-tests.yml` (line 323 whole-tree pytest
      now finds linux-gcc13 baselines via `select_baseline()`)
- [ ] Bugbot HIGH/MED clean
- [ ] After merge: #213 auto-close via PR body

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 7: Bugbot + CI wait, then merge**

When all CI checks SUCCESS:
```bash
unset GITHUB_TOKEN
gh pr comment <PR-NUM> --body "@cursor review"
```

Wait for Bugbot. Address HIGH/MED if any. When Bugbot clean AND CI green:
```bash
unset GITHUB_TOKEN
gh pr merge <PR-NUM> --merge
```

Expected: PR merged; `#213` auto-close via `Closes #213` in PR body.

- [ ] **Step 8: Post-merge bookkeeping**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git fetch origin develop --quiet
git checkout develop
git pull --quiet
git log --oneline -6
```

Expected: develop HEAD is the new merge commit; the 4 implementation commits are visible.

---

## Self-review checklist (run before sharing this plan)

**Spec coverage:**
- §3 in-scope items 1-6 ✅ (Tasks 1-4 map directly)
- §3 out-of-scope respected (no .github changes, no Fortran, no
  compare_metrics.py tolerance fudge)
- §4 D-1..D-6 each represented (D-1 platform key in §6 code; D-2
  hard-fail in §6 + test_baseline_select::test_hard_fails_when_missing;
  D-3 no macOS CI — no .github changes; D-4 flat layout abolished
  via Task 3 git mv; D-5 macOS baselines committed in Task 4; D-6
  helper at python/ top level)
- §6 helper API verbatim in Task 1 Step 3
- §7 per-module pattern in Task 3 Step 4
- §8 migration in Task 3 Step 1
- §9 macOS regen loop in Task 4 Step 2
- §10 no CI changes — respected
- §11 docs in Task 2
- §12 unit tests in Task 1 Step 1
- §13 R-1 sanity check in Task 4 Step 3 (5e-9 + 1e-7 thresholds)
- §14 acceptance reachable by Task 5 exit

**Placeholder scan:** none — every code/command step has actual content. The "Implementer substitutes actual numbers from Task 4 Step 3 here" line in the PR body explicitly directs runtime data insertion, not a TBD.

**Type / name consistency:** `_baseline_select`, `platform_key`,
`select_baseline`, `<os>-gcc<major>`, `linux-gcc13`, `macos-gcc15`
match across all tasks and the spec.

**Subagent-worktree discipline:** every `git` / `make` / `bash`
command shows explicit `cd <abs-path>` or `-C <abs-path>` (per
`feedback_codex_worktree_sharing.md`). Controller-side tripwire at
Task 5 Step 1.
