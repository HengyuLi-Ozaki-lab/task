# PNBTOT Registry Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register `PNBTOT` (NBI Total Input Power, MW) in `tr_param_registry` so `libtrapi.so` clients can drive NBI through `set_param`, and verify via Layer-1 equivalence at 1e-10 with NBI on (`tr_iter01` fixture).

**Architecture:** Single registry CASE addition in `tr/tr_param_registry.f90`, paired fixture (`tr_iter01_params.py`) and `.in` (`tr_iter01.in`) updates so Fortran tr2 baseline and libtrapi.so replay describe the same NBI-on physics, plus 4 documentation surfaces (en + ja tutorials, MCP server metadata, LaTeX manual) that currently document PNBTOT as INVALID.

**Tech Stack:** Fortran (gfortran, free-form), Python 3.10/3.13 (pytest --forked), GNU make, MyST Markdown (Sphinx), LaTeX.

**Spec:** `docs/superpowers/specs/2026-05-05-tr-pnbtot-registry-design.md` (commit `971a9b1c`)

**Branch:** `chore/pre-push-hook-worktree-compat` (continuing from HEAD `1a747e0f`)

**Commit strategy (3 commits):**
1. **C1:** Registry change (Fortran USE + CASE) + smoke test passes
2. **C2:** Atomic physics-state change — fixture + `.in` + regenerated baseline (3 files together; splitting them temporarily breaks Layer-1 equivalence)
3. **C3:** Documentation updates (en/ja tutorials + MCP server + LaTeX manual)

---

## Task 1: Pre-flight build + baseline equivalence sanity

**Goal:** Confirm the current tree compiles and `test_iter01` PASSES at 1e-10 BEFORE touching anything. Establishes the "before" reference so any later regression is attributable to our changes, not pre-existing drift.

**Files:**
- Build only: `tr/libtrapi.so`, `tr/tr2`
- Read: `python/trlib/tests/test_equivalence.py`

- [ ] **Step 1: Build libtrapi.so**

```
make -C tr libtrapi.so 2>&1 | tail -20
```
Expected: ends with `libtrapi.so` link line, no `Error` lines.

- [ ] **Step 2: Build tr2**

```
make -C tr tr2 2>&1 | tail -20
```
Expected: ends with `tr2` link line.

- [ ] **Step 3: Run baseline regression to populate test_run/test_output/tr_iter01/**

```
./test_run/run_tests.sh tr_iter01 2>&1 | tail -20
```
Expected: `tr_iter01: PASSED`. Side effect: `test_run/test_output/tr_iter01/` now contains `eqdata.ITER01` (needed by Layer-1 test).

- [ ] **Step 4: Run Layer-1 equivalence (before state)**

```
cd python && pytest trlib/tests/test_equivalence.py::TestEquivalence::test_iter01 \
    --forked --timeout=120 --timeout-method=signal -v 2>&1 | tail -20
```
Expected: `1 passed`. If SKIPPED, fix the eqdata gating before continuing — a SKIPPED equivalence test does not validate anything (CLAUDE.md `feedback_equivalence_must_pass.md`).

- [ ] **Step 5: No commit**

This task only verifies environment health. Nothing tracked changed.

---

## Task 2: Add PNBTOT to tr_param_registry (USE + CASE)

**Goal:** Register `PNBTOT` so `set_param("PNBTOT", value)` is no longer rejected with `INVALID`. Smoke-test acceptance immediately to catch any module-state issue.

**Files:**
- Modify: `tr/tr_param_registry.f90` (lines 52, 144)
- Test (smoke): inline Python one-liner, no permanent file added

- [ ] **Step 1: Add PNBTOT to USE list**

Edit `tr/tr_param_registry.f90` line 52. Current:
```
       PNBR0, PNBRW, PNBENG, PNBRTG, &
```
After:
```
       PNBTOT, PNBR0, PNBRW, PNBENG, PNBRTG, &
```

- [ ] **Step 2: Add PNBTOT CASE to NBI block**

Edit `tr/tr_param_registry.f90`, find:
```
    !     NBI
    CASE ("PNBR0");  PNBR0  = value
```
Insert one line BEFORE `CASE ("PNBR0")`:
```
    !     NBI
    CASE ("PNBTOT"); PNBTOT = value
    CASE ("PNBR0");  PNBR0  = value
```
Reading order in the block becomes: total-power → deposition-shape (R0/RW) → beam-energy → tangency.

- [ ] **Step 3: Rebuild libtrapi.so**

```
make -C tr libtrapi.so 2>&1 | tail -20
```
Expected: ends with `libtrapi.so` link line, no `Error`.

If link fails with `undefined reference to PNBTOT` or similar stale-mod error, the PIC variant didn't pick up `trcomm.mod_pic`. Workaround per spec §8.1:
```
make -C tr clean && make -C tr libtrapi.so
```

- [ ] **Step 4: Smoke test — registry-and-consumption confirmation**

```
PYTHONPATH=python python -c "
from trlib import Trlib
tr = Trlib()
tr.set_param('PNBTOT', 25.0)
tr.run(0)
tr.close()
print('OK')
"
```
Expected: prints `OK`, no exception.

If `set_param('PNBTOT', 25.0)` raises `TrlibParamError` (= ierr=1 INVALID from registry DEFAULT branch), Step 2 was not picked up — re-check the CASE line and re-run Step 3 with `make clean` workaround.

If `run(0)` raises (e.g., `tr_prep` failure with no eqdata since this minimal fixture doesn't set MODELG=2), substitute the smoke with:
```
PYTHONPATH=python python -c "
from trlib import Trlib
with Trlib() as tr:
    tr.set_param('PNBTOT', 25.0)
print('SET_PARAM_OK')
"
```
This still proves registry acceptance even without `tr_prep`. The full consumer-reach test is Task 5 (Layer-1 equiv).

- [ ] **Step 5: Re-run Layer-1 (still passes since fixture/baseline unchanged)**

```
cd python && pytest trlib/tests/test_equivalence.py::TestEquivalence::test_iter01 \
    --forked --timeout=120 --timeout-method=signal -v 2>&1 | tail -10
```
Expected: `1 passed`. Confirms registry change did not perturb the existing equivalence (PNBTOT=0 default; nothing physics-side changed).

- [ ] **Step 6: Commit (C1)**

```
git add tr/tr_param_registry.f90
git commit -m "$(cat <<'EOF'
feat(tr): register PNBTOT in tr_param_registry

Adds PNBTOT (NBI total input power, MW) to the Layer-3 parameter
registry so libtrapi.so clients can drive NBI through set_param.
The other NBI scalars (PNBR0/PNBRW/PNBENG/PNBRTG) were already
registered (L-6 work) but had no effect because PNBTOT — the only
knob that turns NBI on (trpnb.f90:46) — was missing.

CASE inserted before PNBR0 so the NBI block reads in physical
order: total-power -> deposition-shape -> beam-energy -> tangency.
PNBTOT was already in trcomm_param.f90:35; this commit only adds
the registry USE + CASE wiring.

Spec: docs/superpowers/specs/2026-05-05-tr-pnbtot-registry-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add PNBTOT to fixture (intentional failing equivalence)

**Goal:** Update the Python fixture so `libtrapi.so` runs with NBI on. This DELIBERATELY breaks the equivalence test until Task 4 brings the Fortran baseline in line.

**Files:**
- Modify: `python/trlib/tests/fixtures/tr_iter01_params.py` (lines 10, 26)

- [ ] **Step 1: Update SCALARS dict**

Edit `python/trlib/tests/fixtures/tr_iter01_params.py`. Current lines 25-30:
```python
SCALARS = {
    "MODELG": 3,
    "NSMAX":  4,
    "PROFN2": 0.15,
    "MDLNF":  1,
    "PNBR0":  0.0,
```
Insert `PNBTOT` line BEFORE `PNBR0` (matches registry order):
```python
SCALARS = {
    "MODELG": 3,
    "NSMAX":  4,
    "PROFN2": 0.15,
    "MDLNF":  1,
    "PNBTOT": 25.0,
    "PNBR0":  0.0,
```

- [ ] **Step 2: Update docstring L-6 listing**

Edit `python/trlib/tests/fixtures/tr_iter01_params.py` lines 10-12. Current:
```
  - L-6 extension:   MODELG, PROFN2, MDLNF, PNBR0/PNBRW/PNBENG/PNBRTG,
                     PIC*, PEC*, PLH* scalars, and KNAMEQ via
                     ``tr_param_set_str``.
```
After (add PNBTOT before PNBR0):
```
  - L-6 extension:   MODELG, PROFN2, MDLNF,
                     PNBTOT/PNBR0/PNBRW/PNBENG/PNBRTG,
                     PIC*, PEC*, PLH* scalars, and KNAMEQ via
                     ``tr_param_set_str``.
```

- [ ] **Step 3: Run Layer-1 (expected FAIL — divergence is the point)**

```
cd python && pytest trlib/tests/test_equivalence.py::TestEquivalence::test_iter01 \
    --forked --timeout=120 --timeout-method=signal -v 2>&1 | tail -30
```
Expected: `1 failed` with diff on `WPT`, `BETAN`, `BETAP0`, `TAUE1`, `TAUE2` (and radial `RT`/`AJ`). This is the **intentional intermediate failing state** — fixture now drives NBI on, baseline still has NBI off.

If equiv test PASSES here, something is wrong: either the fixture didn't pick up the PNBTOT entry, or the registry wasn't actually wired in Task 2. Diagnose before proceeding.

- [ ] **Step 4: Stage but DO NOT commit yet**

```
git add python/trlib/tests/fixtures/tr_iter01_params.py
git status -s
```
Expected: only `M python/trlib/tests/fixtures/tr_iter01_params.py` staged. C2 will combine this with `.in` + baseline updates in Task 5.

---

## Task 4: Add PNBTOT to tr_iter01.in (Fortran namelist)

**Goal:** Update the Phase-0 input that `tr2` reads so the regenerated baseline matches the fixture's NBI-on setup.

**Files:**
- Modify: `test_run/inputs/tr_iter01.in` (after line 17)

- [ ] **Step 1: Add PNBTOT line after PNBRTG**

Edit `test_run/inputs/tr_iter01.in`. Current lines 14-18:
```
   PNBR0=0.D0
   PNBRW=1.D0
   PNBENG=1000.D0
   PNBRTG=6.2
   PICCD=0.1D0
```
Insert `PNBTOT=25.D0` after `PNBRTG=6.2`:
```
   PNBR0=0.D0
   PNBRW=1.D0
   PNBENG=1000.D0
   PNBRTG=6.2
   PNBTOT=25.D0
   PICCD=0.1D0
```

- [ ] **Step 2: Verify via grep**

```
grep -n PNBTOT test_run/inputs/tr_iter01.in
```
Expected: one hit `18:   PNBTOT=25.D0` (or similar line number).

- [ ] **Step 3: Stage (still no commit)**

```
git add test_run/inputs/tr_iter01.in
```

---

## Task 5: Regenerate baseline with NBI on

**Goal:** Re-run Fortran `tr2` against the updated `.in`, extract metrics, commit fixture + `.in` + baseline atomically (C2). Layer-1 equivalence then passes again.

**Files:**
- Modify: `test_run/baselines/tr_iter01/metrics.json` (regenerate from `tr2` output)

- [ ] **Step 1: Re-run Phase-0 runner**

```
./test_run/run_tests.sh tr_iter01 2>&1 | tail -20
```
Expected: `tr_iter01: PASSED`. The runner produces fresh `test_run/test_output/tr_iter01/tr_regress.dat`.

- [ ] **Step 2: Extract regenerated metrics**

```
python test_run/scripts/extract_tr_metrics.py \
    test_run/test_output/tr_iter01/tr_regress.dat \
    > test_run/baselines/tr_iter01/metrics.json
```
Expected: no stderr output. The script uses positional `tr_regress.dat` arg and writes JSON to stdout (no `--output` flag).

- [ ] **Step 3: Sanity-check the diff is plausible**

```
git diff --stat test_run/baselines/tr_iter01/metrics.json
git diff test_run/baselines/tr_iter01/metrics.json | grep -E '"WPT"|"BETAN"|"TAUE1"' | head -10
```
Expected: `WPT` increased substantially (NBI heating; pre-PR was ~41 MJ; post-PR with 25 MW NBI should be larger), `BETAN` and `TAUE1` shifted. If WPT is unchanged or decreased significantly, NBI wasn't actually engaged — re-check `MDLNB` default (should be 1 per `trinit.f90:449`) and Task 4's `.in` edit.

- [ ] **Step 4: Stage baseline**

```
git add test_run/baselines/tr_iter01/metrics.json
git status -s
```
Expected: 3 files staged (`fixtures/tr_iter01_params.py`, `inputs/tr_iter01.in`, `baselines/tr_iter01/metrics.json`).

- [ ] **Step 5: Re-run Layer-1 equivalence (the contract)**

```
cd python && pytest trlib/tests/test_equivalence.py \
    --forked --timeout=120 --timeout-method=signal -v 2>&1 | tail -10
```
Expected: `2 passed` (`test_iter01` + `test_tst2`). Both at 1e-10 tolerance. NO SKIP, NO XFAIL — per CLAUDE.md `feedback_equivalence_must_pass.md`, SKIPped equivalence is invisibility, not validation.

If `test_iter01` FAILS, the fixture's `PNBTOT` value and the `.in`'s `PNBTOT` value diverge or the baseline regen used a stale `tr2` (rebuild via `make -C tr tr2` and re-run from Step 1).

- [ ] **Step 6: Commit (C2 — atomic physics state)**

```
git commit -m "$(cat <<'EOF'
test(tr): drive ITER01 fixture with PNBTOT=25 MW (NBI on)

Atomic update of the three files that must move together:
- python/trlib/tests/fixtures/tr_iter01_params.py: SCALARS gains
  PNBTOT=25.0 (placed before PNBR0 to match registry order)
- test_run/inputs/tr_iter01.in: namelist gains PNBTOT=25.D0 so
  tr2 baseline matches libtrapi.so replay
- test_run/baselines/tr_iter01/metrics.json: regenerated via
  ./test_run/run_tests.sh tr_iter01 + extract_tr_metrics.py

PNBTOT=25.0 chosen on codebase corpus grounding: tr/in/tr.ITER01.in:38
uses the same value with the same ITER01 geometry params. Layer-1
equivalence (test_equivalence.py::test_iter01) PASSES at 1e-10 with
the new baseline; test_tst2 unaffected.

Spec: docs/superpowers/specs/2026-05-05-tr-pnbtot-registry-design.md §4.2-4.4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Update D1 tutorials (en + ja) — drop PNBTOT-INVALID claim

**Goal:** Remove the two places in each D1 tutorial that document PNBTOT as not-in-registry / INVALID. Both surfaces become factually wrong the moment Task 2's commit lands; this brings them into truth.

**Files:**
- Modify: `docs/sphinx/modules/tr/en/tutorials.md` (lines 116-122, 224-230)
- Modify: `docs/sphinx/modules/tr/ja/tutorials.md` (lines 116-121, ~224-230)

- [ ] **Step 1: en tutorial — remove PNBTOT bullet from "what fails silently" list**

Edit `docs/sphinx/modules/tr/en/tutorials.md`. Current lines 108-122:
```
- **`RR × BB`** (geometry sweep). The BPSD broker pull
  overwrites `RR`/`RA`/`BB`/`RIP`/`RKAP`/`RDLT` from the
  loaded equilibrium device on the first `tr.run(...)`
  call, clobbering any user `set_param("RR", ...)`.
- **`RIPS × RIPE`** (plasma-current ramp sweep). The
  same BPSD pull recalibrates `RIPS`/`RIPE` from the
  metric-derived current; user overrides are
  overwritten.
- **`PNBTOT × <anything>`** (NBI total-power sweep).
  `PNBTOT` is the actual NB amplitude in MW but is
  **not** in the tr parameter registry —
  `set_param("PNBTOT", ...)` raises `INVALID`. The
  visible knob `PNBR0` looks tempting but is the radial
  *position* of NB deposition in metres, not an
  amplitude.
```
Replace the **entire `PNBTOT × <anything>` bullet** (lines 116-122) with — keeping the surrounding RR/BB and RIPS/RIPE bullets, since those are still BPSD-clobbered. The remaining text becomes:
```
- **`RR × BB`** (geometry sweep). The BPSD broker pull
  overwrites `RR`/`RA`/`BB`/`RIP`/`RKAP`/`RDLT` from the
  loaded equilibrium device on the first `tr.run(...)`
  call, clobbering any user `set_param("RR", ...)`.
- **`RIPS × RIPE`** (plasma-current ramp sweep). The
  same BPSD pull recalibrates `RIPS`/`RIPE` from the
  metric-derived current; user overrides are
  overwritten.
```
(That is: remove 7 lines starting with `- **\`PNBTOT × <anything>\`**` through `amplitude.`.)

The narrative continues with "PT[1] and PN[1] survive" so removing one bullet leaves the structure coherent.

- [ ] **Step 2: en tutorial — drop the trailing PNBTOT-pending note in the optimisation-studies bullet**

Edit `docs/sphinx/modules/tr/en/tutorials.md` lines 224-230. Current:
```
- For shape-optimisation studies (`RKAP × RDLT` or
  `RR × BB`), switch to `MODELG=2` (analytic
  equilibrium) so geometry knobs survive — under
  `MODELG=3` the BPSD pull would clobber them. For
  NBI-amplitude sweeps, `PNBTOT` first needs registry
  registration (a planned change tracked outside this
  tutorial).
```
After:
```
- For shape-optimisation studies (`RKAP × RDLT` or
  `RR × BB`), switch to `MODELG=2` (analytic
  equilibrium) so geometry knobs survive — under
  `MODELG=3` the BPSD pull would clobber them. NBI
  total power is now driven via `set_param("PNBTOT",
  <MW>)` (registered as of this PR).
```

- [ ] **Step 3: ja tutorial — remove PNBTOT bullet (mirror Step 1)**

Edit `docs/sphinx/modules/tr/ja/tutorials.md`. Current lines 116-121:
```
- **`PNBTOT × <anything>`** (NBI 総出力スイープ):
  `PNBTOT` は本来の NB 振幅 (MW 単位) ですが, tr の
  パラメータレジストリに **未登録** です —
  `set_param("PNBTOT", ...)` は `INVALID` を投げます.
  fixture で見える `PNBR0` は NBI 堆積の半径 *位置*
  (m) で振幅ではない, という罠もあります.
```
**Delete these 6 lines entirely.** Surrounding RR/BB and RIPS/RIPE bullets (lines 107-115) remain as the only entries in the "silently fails" list.

- [ ] **Step 4: ja tutorial — drop the trailing PNBTOT-pending note (mirror Step 2)**

Edit `docs/sphinx/modules/tr/ja/tutorials.md` lines 224-230. Current:
```
- 形状最適化研究 (`RKAP × RDLT` や `RR × BB`) は
  `MODELG=2` (解析平衡) に切り替えれば geometry が
  生き残ります — `MODELG=3` だと BPSD プルが上書き
  します. NBI 振幅スイープは, 先に `PNBTOT` を
  レジストリ登録する必要があります (本チュートリアル
  とは別管理の作業).
```
After:
```
- 形状最適化研究 (`RKAP × RDLT` や `RR × BB`) は
  `MODELG=2` (解析平衡) に切り替えれば geometry が
  生き残ります — `MODELG=3` だと BPSD プルが上書き
  します. NBI 総電力は本 PR より `set_param("PNBTOT",
  <MW>)` で操作可能になりました.
```

- [ ] **Step 5: Verify no stale PNBTOT-INVALID claim remains**

```
grep -n "PNBTOT" docs/sphinx/modules/tr/en/tutorials.md docs/sphinx/modules/tr/ja/tutorials.md
```
Expected: each file has exactly one PNBTOT mention (the new "registered as of this PR" note in Step 2/4). No "INVALID", no "未登録", no "not in the registry".

- [ ] **Step 6: Sphinx build smoke (ensure tutorials.md still parses)**

```
make -C docs/sphinx html 2>&1 | tail -20
```
Expected: ends with `build succeeded`. WARNING about deleted anchors is acceptable; ERROR is not. If sphinx is not configured locally, defer to CI.

- [ ] **Step 7: Stage but DO NOT commit yet**

```
git add docs/sphinx/modules/tr/en/tutorials.md docs/sphinx/modules/tr/ja/tutorials.md
```

---

## Task 7: Update MCP server metadata + LaTeX manual (combined with Task 6 commit C3)

**Goal:** Add PNBTOT to the two remaining places that enumerate the registry surface for users (MCP discovery + LaTeX manual table).

**Files:**
- Modify: `python/mcp-servers/tr_mcp/server.py` (line 142, before `PNBR0`)
- Modify: `docs/manual/task-library-manual.tex` (line 721)

- [ ] **Step 1: Add PNBTOT to MCP server NBI group**

Edit `python/mcp-servers/tr_mcp/server.py` lines 142-143. Current:
```python
    # --- heating / current-drive scalars ---------------------------
    "PNBR0":  {"type": "float", "group": "nbi",  "description": "NBI deposition center [m]"},
```
After (insert PNBTOT line BEFORE PNBR0):
```python
    # --- heating / current-drive scalars ---------------------------
    "PNBTOT": {"type": "float", "group": "nbi",  "description": "NBI total input power [MW]"},
    "PNBR0":  {"type": "float", "group": "nbi",  "description": "NBI deposition center [m]"},
```

- [ ] **Step 2: Run MCP server tests**

```
PYTHONPATH=python pytest python/mcp-servers/tr_mcp/tests/ \
    --forked --timeout=60 --timeout-method=signal -v 2>&1 | tail -10
```
Expected: all PASSED. If a test enumerates the parameter dict count, it may need a small bump — fix and re-run.

- [ ] **Step 3: Add PNBTOT to LaTeX manual NBI row**

Edit `docs/manual/task-library-manual.tex` line 721. Current:
```
\texttt{PNBR0}, \texttt{PNBRW}, \texttt{PNBENG}, \texttt{PNBRTG} & double & NBI 位置/幅/エネルギー \\
```
After:
```
\texttt{PNBTOT}, \texttt{PNBR0}, \texttt{PNBRW}, \texttt{PNBENG}, \texttt{PNBRTG} & double & NBI 全電力/位置/幅/エネルギー \\
```

- [ ] **Step 4: LaTeX build smoke (best-effort)**

```
make -C docs/sphinx pdf-en 2>&1 | tail -10 || echo "skip: PDF build not available locally"
```
Expected: either succeeds with `Output written` or skip if TinyTeX not installed locally; CI will catch true regressions.

- [ ] **Step 5: Stage and commit (C3)**

```
git add docs/sphinx/modules/tr/en/tutorials.md \
        docs/sphinx/modules/tr/ja/tutorials.md \
        python/mcp-servers/tr_mcp/server.py \
        docs/manual/task-library-manual.tex
git commit -m "$(cat <<'EOF'
docs(tr): wire PNBTOT through user-facing surfaces

Now that PNBTOT is registered, four user-facing surfaces are no
longer truthful:
- D1 tutorials (en + ja): remove the bullet stating PNBTOT raises
  INVALID; replace the trailing pending-registration footnote
  with a working set_param("PNBTOT", <MW>) instruction
- python/mcp-servers/tr_mcp/server.py: add PNBTOT to the nbi group
  so MCP-driven workflows can discover the parameter
- docs/manual/task-library-manual.tex: add \texttt{PNBTOT} to the
  NBI row of the parameter table

Spec: docs/superpowers/specs/2026-05-05-tr-pnbtot-registry-design.md §4.5-4.7

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Pre-push gate (CLAUDE.md mandatory)

**Goal:** Run the full pre-push gate per `CLAUDE.md`: local tests green + parallel reviewers + REVIEW_OK marker. Push only after.

**Files:** No code change; only review + push artifacts.

- [ ] **Step 1: Final local test sweep**

```
cd python && pytest trlib/tests/test_equivalence.py trlib/tests/test_property_boundary.py \
    --forked --timeout=120 --timeout-method=signal -v 2>&1 | tail -20
```
Expected: `test_iter01`, `test_tst2` PASSED at 1e-10. `test_NSMAX_in_range` XFAILed (per `20d87da0` hot-fix), other property tests PASSED.

- [ ] **Step 2: Verify acceptance criteria from spec §12**

```
# AC: registry-and-consumption smoke
PYTHONPATH=python python -c "
from trlib import Trlib
tr = Trlib()
tr.set_param('PNBTOT', 25.0)
tr.run(0)
tr.close()
print('AC_SMOKE_OK')
"

# AC: .in contains PNBTOT
grep PNBTOT test_run/inputs/tr_iter01.in
```
Expected: `AC_SMOKE_OK` printed; `grep` returns one hit `   PNBTOT=25.D0`.

- [ ] **Step 3: Launch in-house + Codex reviewers in parallel**

In one assistant message, fire both:
- `Agent(subagent_type="superpowers:code-reviewer", prompt="...PNBTOT diff 1a747e0f..HEAD review...")` (CLAUDE.md uses legacy `feature-dev:code-reviewer` name; the actual available agent is `superpowers:code-reviewer`)
- `Agent(subagent_type="codex:codex-rescue", prompt="...PNBTOT diff 1a747e0f..HEAD review...")`

Both prompts include:
- Branch + base ref (`1a747e0f..HEAD`)
- Spec link (`docs/superpowers/specs/2026-05-05-tr-pnbtot-registry-design.md`)
- 3 commits to review (C1, C2, C3)
- Focus: registry-USE/CASE correctness, fixture/`.in`/baseline parity, doc-claim consistency, CLAUDE.md test-discipline (no SKIP/--ignore-glob/strict creep)

Paste HIGH/MED findings to user. Apply fixes if any. If a fix changes HEAD substantially, re-launch reviewers.

- [ ] **Step 4: Write REVIEW_OK marker**

```
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
ls "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
```
Expected: marker file exists. `--git-common-dir` resolves to the shared `.git` from both main checkout and worktrees per CLAUDE.md.

- [ ] **Step 5: Push**

```
git push origin chore/pre-push-hook-worktree-compat 2>&1 | tail -10
```
Expected: pre-push hook prints `pre-push: review marker present — OK`, push succeeds. If hook rejects, the marker SHA does not match HEAD (likely from `--amend` or rebase) — recreate marker for current HEAD and retry.

---

## Task 9: Verify CI green

**Goal:** Confirm the pushed commits go green on GitHub Actions before declaring the task done.

**Files:** none (read-only check)

- [ ] **Step 1: Find new run IDs**

```
env -u GITHUB_TOKEN gh run list --limit 3 --branch chore/pre-push-hook-worktree-compat 2>&1 | head -5
```
Expected: 2 in_progress runs (push + PR). Note the push run's databaseId. (`GITHUB_TOKEN` is invalid in this env; `env -u` strips it so gh falls back to keyring auth.)

- [ ] **Step 2: Wait for completion (background)**

```
RUN_ID=<from Step 1>
until env -u GITHUB_TOKEN gh run view $RUN_ID --json status -q .status 2>/dev/null | grep -q completed; do sleep 30; done
env -u GITHUB_TOKEN gh run view $RUN_ID --json status,conclusion,databaseId,displayTitle
```
Run with `run_in_background: true` so the assistant gets a notification on completion.

- [ ] **Step 3: Verify success**

Expected: `"conclusion":"success"`. If failure, fetch logs and triage:
```
env -u GITHUB_TOKEN gh run view $RUN_ID --log-failed 2>&1 | head -100
```
Common causes:
- Equivalence drift on a Linux-vs-macOS Fortran-arithmetic edge: investigate the failing scalar; do NOT just bump tolerance
- BPSD patch did not auto-apply: check `docs/external-patches/bpsd/` and the CI workflow
- New PNBTOT mention in a doc surface I missed: grep for "PNBTOT" across the repo and update consistently

---

## Self-review

- **Spec coverage** (§4.1–4.7 + §12 AC):
  - §4.1 registry change → Task 2 (USE + CASE) ✓
  - §4.2 fixture → Task 3 ✓
  - §4.3 `.in` → Task 4 ✓
  - §4.4 baseline regen → Task 5 ✓
  - §4.5 en + ja tutorials → Task 6 ✓
  - §4.6 MCP server → Task 7 ✓
  - §4.7 LaTeX manual → Task 7 ✓
  - §4.8 build steps → Task 1 (initial) + Task 2 Step 3 (rebuild after registry change) ✓
  - §8 verification → Tasks 1, 2 Step 4-5, 5 Step 5, 8 Step 1-2 ✓
  - §9 pre-push gate → Task 8 ✓
  - §12 AC items 1-7 → Task 8 Step 1-2 (smoke + grep) + Task 5 Step 5 (equiv) + Task 1+2 Step 3 (builds) + Task 6+7 Step 5 (docs verified by stage manifest) + Task 8 Step 4-5 (gate) ✓

- **Placeholder scan**: no `TBD`/`TODO`/"add appropriate"/"similar to". Each step shows the exact code/command. ✓

- **Type consistency**: PNBTOT is a Fortran `REAL(rkind)` everywhere (registry signature `tr_param_set(name, value)` already takes `REAL(rkind)`); Python side uses `float`; LaTeX uses `double` matching existing rows. ✓

- **Risk gaps**: spec §10's BPSD-SIGABRT and stale-mod-pic risks are mentioned in Task 2 Step 3 fallback; the 1e-10 baseline-regen discipline is enforced by Task 5 Step 5 + CLAUDE.md cross-ref.

---

## Out-of-scope (reaffirmed from spec §11)

- Property-based PNBTOT sweep (0/10/25/50 MW monotonic WPT check) — future Layer-4 PR
- MDLNB explicit registration — already in registry
- PICTOT/PECTOT same-class registry gaps — separate single-knob PRs

---

## Cross-references

- Spec: `docs/superpowers/specs/2026-05-05-tr-pnbtot-registry-design.md` (commit `971a9b1c`)
- Memory: `feedback_equivalence_must_pass.md`, `feedback_review_before_push.md`, `feedback_use_valgrind.md`, `project_bpsd_species_kid_oob_patch.md`
- Existing reference for PNBTOT corpus value: `tr/in/tr.ITER01.in:38`
- Phase L registry design: `docs/superpowers/specs/2026-04-17-tr-library-design.md` §5.3
