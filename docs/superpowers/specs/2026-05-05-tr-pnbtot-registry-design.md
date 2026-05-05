# PNBTOT Registry Extension — Design Spec

**Date**: 2026-05-05
**Branch**: `chore/pre-push-hook-worktree-compat` (continuing from
HEAD `20d87da0` after the CI hot-fix; PNBTOT diff to be reviewed
as `20d87da0..HEAD` at push time)
**Author**: Kazuyoshi Yoshimi
**Status**: Approved scope; pending implementation plan

## 1. Goal

Register `PNBTOT` (NBI Total Input Power, MW) in the Layer-3 parameter
registry so that `libtrapi.so` clients can drive Neutral Beam Injection
through `set_param("PNBTOT", value)`. Verify functional correctness via
the Layer-1 equivalence test against the Phase 0 Fortran baseline at
1e-10 tolerance, with NBI **on**.

## 2. Motivation

`PNBTOT` is the only knob that turns NBI from off to on (`trpnb.f90:46`:
`IF (PNBTOT.LE.0.D0) RETURN`). All other NBI scalars (`PNBR0`, `PNBRW`,
`PNBENG`, `PNBRTG`) are already in the registry (L-6 work, lines 145–148
of `tr/tr_param_registry.f90`), but they have no effect without
`PNBTOT > 0`. The current registry surface therefore advertises NBI
parameters that, for any client that goes through `tr_param_set` only,
silently do nothing.

This gap is also documented as a known limitation in the D1 tutorials
(`docs/sphinx/modules/tr/{en,ja}/tutorials.md` line 116):

> `PNBTOT` is the actual NB amplitude in MW but is **not** in the tr
> parameter registry — `set_param("PNBTOT", ...)` raises `INVALID`.

Closing this gap removes the only remaining NBI-knob limitation called
out in the D1 tutorial.

## 3. Non-goals

- Adding `PNBVY`, `PNBVW`, `PNBCD` to the registry. These are only
  consumed by `TRNBIB` (`MDLNB=3` or `4`); the default `MDLNB=1`
  dispatches to `TRNBIA` which uses only `PNBR0/PNBRW/PNBTOT/PNBENG`.
  Adding them would expand the API surface without a covering test.
- Changing the default `MDLNB` (stays at `1` per `trinit.f90:449`).
- Touching the `tr_tst2` fixture/baseline. TST-2 is a non-ITER
  device fixture and unrelated to the ITER NBI scenario being
  exercised here. Layer-1 `test_tst2` continues to pass unmodified.
- Refactoring the registry dispatch (deferred to a future PR if/when
  the `SELECT CASE` exceeds maintainable size).

## 4. Scope (7 files + 2 build steps)

### 4.1 Registry (Fortran)

**`tr/tr_param_registry.f90`**:
- Line 52 (`USE trcomm, ONLY: ...`): add `PNBTOT` to the NBI group.
- Line 145–148 (NBI `CASE` block): insert
  `CASE ("PNBTOT"); PNBTOT = value` as the first NBI entry (before
  `PNBR0`), so the block reads in physical order
  total-power → deposition-shape (R0/RW) → beam-energy → tangency.

### 4.2 Test fixture (Python)

**`python/trlib/tests/fixtures/tr_iter01_params.py`**:
- `SCALARS` dict: insert `"PNBTOT": 25.0,` adjacent to the existing
  `"PNBR0"/"PNBRW"/"PNBENG"/"PNBRTG"` entries (lines 26–29).
- Update the leading docstring line 10–12 to mention PNBTOT in the
  L-6 extension list.

### 4.3 Phase-0 namelist input (Fortran)

**`test_run/inputs/tr_iter01.in`**:
- After line 17 (`PNBRTG=6.2`), add `   PNBTOT=25.D0`.

This file is what `./test_run/run_tests.sh tr_iter01` feeds into
`tr2`; without this addition the regenerated baseline would still
have NBI off (`PNBTOT=0` default from `trinit.f90:440`) and the
Layer-1 1e-10 comparison would fail.

### 4.4 Layer-1 baseline regeneration

**`test_run/baselines/tr_iter01/metrics.json`**:
- Regenerate by running:
  ```
  make -C tr tr2
  make -C tr libtrapi.so       # registry change must be reflected too
  ./test_run/run_tests.sh tr_iter01
  python test_run/scripts/extract_tr_metrics.py \
      test_run/test_output/tr_iter01/tr_regress.dat \
      > test_run/baselines/tr_iter01/metrics.json
  ```
  (`extract_tr_metrics.py` takes a positional `tr_regress.dat` and
  writes JSON to stdout; per `test_run/scripts/check_regression.sh:32`
  the dump filename for `tr_*` tests is fixed.)
- Expected scalar deltas (NBI off → on, 25 MW): `WPT`, `BETAN`,
  `BETAP0`, `BETA0`, `BETAA`, `TAUE1`, `TAUE2`, plus radial
  `RT`/`AJ`/`QP` profile shifts.

### 4.5 D1 tutorials (Sphinx, en + ja)

**`docs/sphinx/modules/tr/en/tutorials.md`**:
- Line 116–119: rewrite the `PNBTOT × <anything>` bullet from
  "PNBTOT is **not** in the registry — raises `INVALID`" to a
  factual statement that PNBTOT *is* now registered (with default 0
  → NBI off; set non-zero to drive NBI), and use it as the
  recommended NBI sweep handle. Keep the surrounding warnings about
  RR/RIPS being BPSD-clobbered (those are unaffected).
- Line ~228–230 (in the "shape-optimisation studies" bullet, which
  ends with "For NBI-amplitude sweeps, `PNBTOT` first needs registry
  registration (a planned change tracked outside this tutorial)."):
  delete the trailing "PNBTOT first needs registry registration..."
  sentence — it referenced the limitation that this PR closes.

**`docs/sphinx/modules/tr/ja/tutorials.md`**:
- Line 116–119: same rewrite (Japanese counterpart of the en
  tutorial bullet — `set_param("PNBTOT", ...)` は `INVALID` を
  投げます → factually correct counterpart).
- Line ~227–230: same deletion (the
  「NBI 振幅スイープは, 先に `PNBTOT` をレジストリ登録する必要が
  あります (本チュートリアルとは別管理の作業).」 sentence).

### 4.6 MCP server metadata (Python)

**`python/mcp-servers/tr_mcp/server.py`**:
- Line ~143: add an entry to the NBI group:
  ```python
  "PNBTOT": {"type": "float", "group": "nbi",
             "description": "NBI total input power [MW]"},
  ```
  Place it before `PNBR0` so the natural reading order is
  total-power → deposition-shape.

### 4.7 LaTeX manual

**`docs/manual/task-library-manual.tex`**:
- Line 721 NBI row: add `\texttt{PNBTOT}` to the listed knobs:
  ```
  \texttt{PNBTOT}, \texttt{PNBR0}, \texttt{PNBRW}, \texttt{PNBENG},
  \texttt{PNBRTG} & double & NBI 全電力/位置/幅/エネルギー
  ```

### 4.8 Build artifacts (not committed)

- `tr/tr2` (gitignored binary): rebuild via `make -C tr tr2`
- `tr/libtrapi.so` (gitignored): rebuild via `make -C tr libtrapi.so`

These are prerequisites for the baseline regeneration step (4.4) and
for running the equivalence test locally.

## 5. Why `PNBTOT = 25.0`

Selected on **codebase corpus grounding**, not on external physics
references:

| Candidate | Source | Verdict |
|---|---|---|
| 10.0 MW | `tr/in/tr.M0904*.in`, `tr/in/tr2.inSS25` | Different device; rejected |
| **25.0 MW** | **`tr/in/tr.ITER01.in:38`** | **Same ITER01 scenario; accepted** |
| 33.0 MW | ITER design (1 NBI unit) | Codebase-external; rejected |
| 100.0 MW | `tr/in/tr.M0904*.in` ramp-end | Different device; rejected |

The `tr_iter01.in` fixture is named, and shares all geometry/equilibrium
parameters (`MODELG=3`, `KNAMEQ='eqdata.ITER01'`, `RIPS=2`, `RIPE=7`,
`PNBENG=1000` keV, `PNBR0=0`, `PNBRW=1`, `PNBRTG=6.2`), with
`tr/in/tr.ITER01.in`. Adopting that file's `PNBTOT=25.D0` keeps the
fixture trivially traceable: any future reader can `grep PNBTOT
tr/in/tr.ITER01.in` and find the source. ITER NBI design is 1 MeV ×
33 MW per injector, with operational scenarios in the 16–33 MW range,
so 25 MW is also physically defensible.

## 6. Why include `tr_iter01.in` in scope (not in the user instruction)

Layer-1 equivalence (`test_equivalence.py`) compares the libtrapi.so
replay (driven from `tr_iter01_params.py`) against
`test_run/baselines/tr_iter01/metrics.json`. The baseline is
regenerated by running Fortran `tr2` against `test_run/inputs/tr_iter01.in`.

If the fixture sets `PNBTOT=25` but the `.in` does not, then:
- libtrapi.so runs with NBI on (PNBTOT=25)
- tr2 runs with NBI off (PNBTOT=0 default)
- baseline metrics reflect NBI off
- 1e-10 comparison **fails on every NBI-affected scalar**

The user-instruction omission is a likely oversight (the user did
explicitly note that "WPT/BETAN/TAUE1 will change → baseline must be
regenerated", which implies parity between the two run paths). The
spec makes this dependency explicit.

## 7. Why include the 3 documentation files (not in user instruction)

These are user-facing surfaces that **make explicit truth claims about
PNBTOT**:

1. `docs/sphinx/modules/tr/{en,ja}/tutorials.md`: states
   `set_param("PNBTOT", ...)` raises `INVALID`. Becomes false the
   moment the registry CASE is added — leaving it would publish
   contradictory documentation in a single PR.
2. `python/mcp-servers/tr_mcp/server.py`: enumerates registry knobs
   for MCP clients. PNBTOT being absent means MCP-driven workflows
   cannot discover the parameter.
3. `docs/manual/task-library-manual.tex`: parameter table summarises
   the registry surface. Same argument as #1.

All three are short edits (1–4 lines each) and ship in the same PR
to avoid stale-documentation regression.

## 8. Verification plan

### 8.1 Build

```
make -C tr libtrapi.so 2>&1 | tail -20    # registry change compiles
make -C tr tr2          2>&1 | tail -20    # baseline-gen binary builds
```

`tr/Makefile` line 535 has an explicit dep
`$(OBJDIR)/tr_param_registry.o : tr_param_registry.f90 trcomm.f90 ...`
for the non-PIC build, so adding `PNBTOT` to the USE list triggers
a rebuild for `tr2`. The PIC variant (`$(OBJDIR_PIC)/...`, used by
`libtrapi.so`) goes through the generic
`$(OBJDIR_PIC)/%.o: %.f90` rule (line 257) and does **not** track
inter-module deps explicitly; if a stale `mod_pic/trcomm.mod` is
suspected (e.g. if `libtrapi.so` builds clean but
`set_param("PNBTOT", ...)` returns `INVALID`), do
`make -C tr clean && make -C tr libtrapi.so` and retry.

### 8.2 Phase-0 baseline regeneration

```
./test_run/run_tests.sh tr_iter01          # depends on eq_iter01 (auto)
```

The test runner produces `test_run/test_output/tr_iter01/`; the
extractor turns the dump into `metrics.json`:

```
python test_run/scripts/extract_tr_metrics.py \
    test_run/test_output/tr_iter01/tr_regress.dat \
    > test_run/baselines/tr_iter01/metrics.json
```
(Same form as §4.4. The script takes a positional `tr_regress.dat`
path and writes JSON to stdout — there is no `--output` flag.)

Diff `git diff test_run/baselines/tr_iter01/metrics.json` should show
non-trivial drift on `WPT`, `BETAN`, `TAUE1`, etc. (NBI on changes
heating).

### 8.3 Layer-1 equivalence (the contract)

```
cd python && pytest trlib/tests/test_equivalence.py \
    --forked --timeout=120 --timeout-method=signal -v
```

Both `test_iter01` and `test_tst2` must PASS at 1e-10. `test_tst2`
is unaffected (no fixture change); `test_iter01` exercises the new
PNBTOT path through libtrapi.so and confirms the result matches the
freshly-regenerated baseline.

### 8.4 Test-discipline guardrails (per CLAUDE.md)

- No `--ignore-glob`, `--deselect`, `pytest.mark.skip`, or
  `pytest.mark.xfail` on the equivalence test. If 1e-10 does not
  match, debug the registry assignment / namelist parity until it
  does.
- `test_iter01` SKIP (e.g., from missing eqdata) is treated as a
  failure; the runner script must be invoked first to populate
  `test_run/test_output/tr_iter01/`.

## 9. Pre-push gate (per `CLAUDE.md`)

For the single push at the end of this work:

1. **Local pytest** (8.3) green at 1e-10.
2. **In-house code review**: `Agent(subagent_type="superpowers:code-reviewer")`
   on diff `20d87da0..HEAD` (PNBTOT-only diff, excluding the CI hot-fix
   which is already pushed). CLAUDE.md still references the legacy
   `feature-dev:code-reviewer` name; the actually-available agent in
   this session is `superpowers:code-reviewer`.
3. **Codex independent review**: `Agent(subagent_type="codex:codex-rescue")`
   on the same diff. (Both reviewers fired in parallel in one message.)
4. **Marker file**:
   ```
   touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
   ```
5. `git push origin chore/pre-push-hook-worktree-compat`

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `make -C tr libtrapi.so` warns/breaks on PNBTOT addition | PNBTOT already in `trcomm_param.f90:35` USE list — pure additive registry change; build smoke-tests in §8.1 catch any module-state issue early |
| Baseline drift outside expected scalars (e.g. unrelated profile noise) | If unexpected fields drift, debug before committing the new baseline. Don't blindly accept |
| `tr2` build fails in current env (gfortran, BPSD patches) | The `tr2` target predates this work and produced the existing baseline; if it fails today, fix the build (don't bypass the baseline regen step) |
| Existing untracked files (`.worktrees/`, `docs/doc-design/`, `tr/libtrapi.so`, etc.) accidentally staged | Use explicit `git add <path>` for each touched file; never `git add -A` |
| `test_iter01` SKIP due to missing `eqdata.ITER01` under `test_run/test_output/tr_iter01/` | The Phase-0 runner (§8.2) populates that directory as a side effect; running it before pytest is the canonical workaround per `test_equivalence.py:179–184` |
| **BPSD-driven SIGABRT during `make -C tr libtrapi.so`** (heap corruption observed historically when BPSD patches drift, per `$CLAUDE_MEMORY_DIR/memory/feedback_use_valgrind.md` and PR #140 / `project_bpsd_species_kid_oob_patch.md`) | If build links clean but `./test_run/run_tests.sh tr_iter01` crashes with SIGABRT, re-run under `valgrind` (installed); BPSD patches under `docs/external-patches/bpsd/` should auto-apply in CI but local tree may need a `git clean -df bpsd/` + re-patch cycle. Do NOT proceed to baseline regen on an unstable libtrapi.so |
| `extract_tr_metrics.py` silently drops unknown scalar keys if a future `tr_regress.dat` schema adds them (the SCALAR_KEYS allowlist on line 18-21 filters; unknown keys are skipped with `pass`) — header-field mismatch DOES raise `SystemExit` (lines 60-67) | If `metrics.json` is missing a newly-added scalar, check the `SCALAR_KEYS` set in `extract_tr_metrics.py:18` and extend it. Surface argparse / SystemExit messages on non-zero exit code |

## 11. Out-of-scope follow-ups (do not include here)

- Property-based PNBTOT sweep test (vary 0/10/25/50 MW, check
  monotonic WPT increase). Belongs in a future Layer-4 sweep PR.
- MDLNB explicit registration (already in registry; no fixture
  change needed).
- Other heating-knob gaps (e.g. `PICTOT`, `PECTOT` are not in the
  registry either — out of scope for this single-knob PR).

## 12. Acceptance criteria

- [ ] `make -C tr libtrapi.so` builds clean
- [ ] `make -C tr tr2` builds clean
- [ ] **Direct registry-and-consumption confirmation**:
      ```
      python -c "
      from trlib import Trlib
      tr = Trlib()
      tr.set_param('PNBTOT', 25.0)
      tr.run(0)        # exercise tr_prep → trpnb.f90:46 PNBTOT consumer
      tr.close()
      "
      ```
      runs without raising. `set_param` proves the registry CASE is
      wired (raises `TrlibParamError` on unknown keys per
      `errors.py:46`); `run(0)` reaches `trpnb.f90:46`'s
      `IF (PNBTOT.LE.0.D0) RETURN` branch with PNBTOT=25 → the value
      travels through to the NBI consumer. Independent of the
      equivalence run (§8.3) which is the true correctness contract
- [ ] `test_run/inputs/tr_iter01.in` contains `PNBTOT=25.D0`
      (`grep PNBTOT test_run/inputs/tr_iter01.in` returns one hit)
- [ ] `./test_run/run_tests.sh tr_iter01` completes; diff of
      regenerated `metrics.json` shows expected NBI-on deltas on
      `WPT/BETAN/TAUE1` (sanity-check the magnitude is non-trivial)
- [ ] `pytest python/trlib/tests/test_equivalence.py --forked
      --timeout=120 --timeout-method=signal` PASSES (no SKIP, no
      xfail) for both `test_iter01` and `test_tst2`
- [ ] D1 tutorials (en + ja) no longer claim PNBTOT is INVALID
- [ ] MCP server lists PNBTOT under nbi group
- [ ] LaTeX manual NBI row includes `\texttt{PNBTOT}`
- [ ] Pre-push gate steps 1–4 satisfied; push succeeds

## 13. Cross-references

- `docs/superpowers/specs/2026-04-17-tr-library-design.md` §5
  (registry design)
- `docs/superpowers/plans/2026-04-18-tr-library-L6-test-4layers.md`
  (Layer-1 equivalence iteration protocol)
- `tr/trpnb.f90` (NBI implementation; consumers of PNBTOT)
- `tr/trinit.f90:440,449` (defaults: `PNBTOT=0`, `MDLNB=1`)
- `tr/in/tr.ITER01.in:38` (canonical ITER01 sample with
  `PNBTOT=25.D0`)
