# `QQPS` is all zeros after `MODELG=3` (EQRTSK) loads

**Date:** 2026-05-10 (fix); 2026-09-28 (two review follow-ups)
**Component:** `eq/` (TASK/EQ Fortran library), its C API and `eqlib`
**Severity:** Low. A silent data-quality bug: no crash, and callers that
use the per-`NR` `profile[].QPS` field are unaffected.
**Affects:** every consumer of `EqState.qqps` (the C-API / Python wire
field documented as "q profile (psi-surface)"), including the `eq` MCP
server's `get_state` payload and task-web's q(ψ) plot.
**Fixed in:** `EQCALQ` (`eq/eqcalq.f90`), in three commits: the first
fill (97025c6e) and two follow-ups after pre-push reviews (ccfe533a and
the commit that added this revision of the document). See "Fix" and
"Review follow-ups" below.

---

## TL;DR

`EQRTSK` (the binary EQDSK reader behind `MODELG=3`) reads `PSIPS`,
`PPPS`, `TTPS`, `TEPS` and `OMPS` on the psi-surface grid but **never
reads `QQPS`**: the on-disk format does not store it. `EQCALQ` then
recomputes `QPS` on the per-`NR` flux-surface grid (returned to callers
as `profile[].QPS`) but never projected it onto `PSIPS`. So the `QQPS`
slot in COMMON kept its zero-initialised value, and the C ABI getter
(`eq_api_common.f:186`, `QQPS_OUT(I) = QQPS(I)`) returned all zeros.

This is a TASK source-code bug, not an MCP or Python wrapper bug.

Final behaviour:

| Situation | `QQPS` |
| --- | --- |
| Just after a g-eqdsk load (`MODELG=5`/`25`, `EQDSKR`) | The file's q column, untouched |
| Any other load (`MODELG=3`/`9`, `8`, `15`), any `EQCALC` solve, or a re-solve after a g-eqdsk load | The per-`NR` q profile resampled onto `PSIPS` |
| A `PSIPS` point within 5% of the plasma span outside `[PSIP(1), PSIPA]` | Clamped to the nearest end, so the edge value equals `QSURF` |
| A `PSIPS` point further out | The run fails: `EQ_ERR_CALC_FAILED`, `QQPS` zeroed, reason from `eq_last_error` |
| Degenerate `PSIP` grid (`SPL1DF` error 9) | Same failure, with its own reason |

The follow-ups also made a g-eqdsk load of a missing file fail instead of
returning `EQ_OK` with the previous equilibrium, and added
`eq_last_error`, so every failed `eq_run` can say why.

## Symptom

After a normal load via the MCP server:

```python
# (after MODELG=3, KNAMEQ=eqdata.ITER01, run(mode=1))
state = eq.get_state()
print(state["QQPS"])  # → [0.0, 0.0, ..., 0.0]   (length 21 for ITER01)
print(state["scalars"]["QAXIS"])  # 0.5784   ← real q on axis
print(state["scalars"]["QSURF"])  # 3.3252   ← real q at LCFS
print(state["profile"][0]["QPS"]) # 0.5784   ← per-NR profile is fine
```

`QQPS` is documented as "q profile (psi-surface)" in
[`python/eqlib/state.py`](../../python/eqlib/state.py) and is exposed
in the C struct in [`eq/eq_api.h`](../../eq/eq_api.h). Users naturally
expect it to mirror `PPPS` / `TTPS` (which **are** populated). Instead
they got a length-`NPSMAX` array of `0.0`.

The bug is silent: no error, no warning, and `compare_metrics.py` did
not catch it because the equivalence baseline (`test_run/baselines/`)
only records `scalars + profile + dimensions`, not the psi-surface
arrays.

## Where it lives in the code

| Site | Role |
| --- | --- |
| `eq/eqcom1_mod.f90` | `QQPS(NPSM)`; also `QQPS_FROM_FILE` and `EQ_ERRMSG`, added by the second follow-up |
| `eq/eq-eqdsk.f90:62`   | `read (neqdsk,2020) (QQPS(i),i=1,NPSMAX)`: the **g-eqdsk text** reader `EQDSKR`, the only code that reads a q column; it now also sets `QQPS_FROM_FILE` |
| `eq/eqfile.f90` (`EQ_READ`) | Sends exactly `MODELG=5`/`25` to `EQDSKR`, then calls `EQCALQ`; clears the flag before every load |
| `eq/equnit.f90:91`     | `eq_load` calls `EQCALQ` again after every load |
| `eq/eqcalc.f90` (`EQLOOP`) | Every re-solve (`EQCALC`, the menu's `C`) comes through here; clears the flag |
| `eq/eqcalq.f90` (`EQCALQ`) | The `QQPS` fill |
| `eq/eq_api_common.f:186` | `QQPS_OUT(I) = QQPS(I)`: the C ABI getter |
| `eq/eq_api.f90` | `eq_last_error`; `eq_init`/`eq_finalize` reset the flag |

`eq/eqfile.f90` (`EQRTSK`, the `MODELG=3` binary reader):

```fortran
READ(21) (PSIPS(NPS),NPS=1,NPSMAX)
READ(21) (PPPS(NPS),NPS=1,NPSMAX)
READ(21) (TTPS(NPS),NPS=1,NPSMAX)
READ(21) (TEPS(NPS),NPS=1,NPSMAX)
READ(21) (OMPS(NPS),NPS=1,NPSMAX)
!  ← no `READ(21) (QQPS(NPS),NPS=1,NPSMAX)`
```

`EQCALQ` builds q only on the per-`NR` mesh: `EQSETS` calls
`SPL1D(PSIP, QPS, DERIV, UQPS, NRMAX, 0, IERR)`, the natural cubic
spline of `QPS` on the `NRMAX` flux-surface values `PSIP`.
`eq/eqcom3_mod.f90` has psi-surface splines for pressure and `F`
(`UPPPS` / `UTTPS`) but none for q, so before this fix nothing
interpolated `QPS` onto `PSIPS` either.

## Root cause

`MODELG=3` (`EQRTSK` binary) and `MODELG=5` (g-eqdsk text) populate the
psi-surface arrays differently. The text path **reads** `QQPS` from the
file (`eq-eqdsk.f90:62`); the binary path cannot, because the legacy
on-disk schema never wrote it, and `EQCALC` never computed it.

`EQCALQ` builds `UQPS` from the per-`NR` mesh (downstream metric
routines need it internally), but nobody added the matching step of
resampling that spline onto `PSIPS`. The COMMON-block slot is
zero-initialised at process start and nothing on the `MODELG=3` path
writes it, so the C-API getter returned zeros.

## Fix

At the end of `EQCALQ`, after `EQSETS` has built `UQPS`
(`eq/eqcalq.f90`; error handling abridged):

```fortran
      IF(.NOT.QQPS_FROM_FILE) THEN
         PSIPLO=MIN(PSIP(1),PSIPA)
         PSIPHI=MAX(PSIP(1),PSIPA)
         PSIPTOL=0.05D0*(PSIPHI-PSIPLO)
         IERRQ=0
         DO NPS=1,NPSMAX
            IF(PSIPS(NPS).LT.PSIPLO-PSIPTOL.OR. &
               PSIPS(NPS).GT.PSIPHI+PSIPTOL) THEN
               ! EQ_ERRMSG: 'EQCALQ: PSIPS(n)=... is more than 5% outside
               !   the plasma psi range [...]: the psi-surface grid does
               !   not match this equilibrium'
               IERRQ=201
               EXIT
            ENDIF
         ENDDO
         IF(IERRQ.EQ.0) THEN
            PSIPLO=MAX(PSIPLO,MIN(PSIP(1),PSIP(NRMAX)))
            PSIPHI=MIN(PSIPHI,MAX(PSIP(1),PSIP(NRMAX)))
            DO NPS=1,NPSMAX
               PSIPQ=MIN(MAX(PSIPS(NPS),PSIPLO),PSIPHI)
               CALL SPL1DF(PSIPQ,QQPS(NPS),PSIP,UQPS,NRMAX,IERRQ)
               IF(IERRQ.NE.0) THEN  ! error 9: degenerate PSIP grid
                  ! EQ_ERRMSG set
                  IERRQ=202
                  EXIT
               ENDIF
            ENDDO
         ENDIF
         IF(IERRQ.NE.0) THEN
            QQPS(1:NPSMAX)=0.D0
            IF(IERR.EQ.0) IERR=IERRQ
         ENDIF
      ENDIF
```

Design decisions:

1. **Where:** at the end of `EQCALQ`. Doing it inside `EQRTSK` would not
   work, because `UQPS` does not exist yet at that point of the
   `eq_load → eqload → EQ_READ → EQRTSK`, then `eqcalq`, chain.
2. **Reuse `UQPS` rather than cache a new `UQQPS` table:** `QQPS` and
   `profile[].QPS` then come from the same spline and stay consistent.
   `QQPS[0] == QAXIS` exactly. For ITER01, `QQPS[-1]` differs from
   `QSURF` by 4e-6 because the file's `PSIPS[-1]` is 4.7e-5 (out of 103)
   inside the `PSIPA` that `EQAXIS` recomputes.
3. **Keep a g-eqdsk q column, tracked by a flag, not by `MODELG`.**
   `EQDSKR` sets `QQPS_FROM_FILE` after reading the column. Anything
   that replaces the equilibrium clears it: `EQ_READ` before every load
   and `EQLOOP` on every re-solve. `eq_init` and `eq_finalize` also
   reset it. So "the file's column still describes this equilibrium" is
   exactly "the flag is set". See "Review follow-ups" for why a
   `MODELG` test was not enough.
4. **Tolerance, then clamp to the plasma range.** Measured mismatches
   between a file's `PSIPS` and the recomputed `PSIPA` are at most 1%.
   A point less than 5% of the plasma span outside `[PSIP(1), PSIPA]`
   is clamped to the nearest end. At `PSIPA` that gives `QSURF` (they
   agree to 1e-15), with or without the vacuum extension of `PSIP`.
   The clamp also stays inside the `PSIP` grid, so `SPL1DF` never
   extrapolates. A point further out means the grid does not describe
   this equilibrium, so the run fails. Clamping it would invent values.
5. **Failures are reported, not logged.** An out-of-range grid (201) or
   a degenerate `PSIP` grid (202, `SPL1DF` error 9) zeroes `QQPS`
   rather than leaving a partial or stale column. It fails `EQCALQ`,
   so `eq_run` returns `EQ_ERR_CALC_FAILED`, and it stores the reason
   in `EQ_ERRMSG`. The new C function `eq_last_error` returns that
   reason: API callers never see unit-6 output, because the MCP servers
   isolate stdout. `eqlib`'s `Eq.run()` puts the reason in its
   exception, and the eq MCP server passes it on in its `ToolError`.
6. **No `STOP`:** per `CLAUDE.md` "Fortran library discipline", a
   library-reachable `STOP` aborts the host process (pytest, MCP
   server, ...).

## Review follow-ups

### First follow-up (ccfe533a)

The first version (97025c6e) ran the fill unconditionally and wrote
`0.0` whenever `SPL1DF` returned any error. Two pre-push reviews found
two problems:

1. **It overwrote the g-eqdsk q column.** `EQCALQ` runs right after
   `EQDSKR` (`eqfile.f90`) and again in `eq_load`. A column of 7.0 came
   back as 0.578…3.325, and a negative-q file came back positive.
   ccfe533a skipped the fill when `MODELG` was 5 or 25.
2. **It reintroduced a silent zero.** `SPL1DF` returns error 1 or 2
   (point more than half an average cell outside the grid) and still a
   value, but the loop stored `0.0` while the run reported success.
   The trigger was a g-eqdsk whose axis psi was 0.1% deeper than the
   one `EQAXIS` finds, loaded with `NSUMAX=0` and `NRMAX=1000`, or
   saved and reloaded as `MODELG=3`. ccfe533a clamped every point into
   the `PSIP` range.

### Second follow-up

Two more pre-push reviews agreed that both ccfe533a fixes were too
blunt:

1. **The clamp was unbounded and hid wrong grids.** With the grid
   stretched ×2, `SPL1DF` reported nothing and 14 of 33 `QQPS` entries
   were silently the q at the vacuum edge. With the grid sign-flipped,
   32 of 33 were the axis q. The upper bound was also `PSIP(NRMAX)`, which with the
   default vacuum extension is the vacuum edge. So a point just past
   the LCFS got the vacuum model's q: a 0.1% offset gave 3.3337 instead
   of `QSURF` 3.3249 (3.3929 at 1%).
   Fix: decision 4. The tolerance is 5% of the plasma span, the clamp
   is to `[PSIP(1), PSIPA]`, and anything further out fails the run.
2. **`MODELG` 5/25 is not "`QQPS` came from the current file".**
   `eq_run(mode=0)` does not check `MODELG`, so through `eqlib` or the
   MCP server:
   - a fresh `MODELG=5` solve returned success with `QQPS` all zeros;
   - after a g-eqdsk load, a re-solve kept the old file's 7.0 column
     while `QSURF` moved to 3.204. The menu's `K` then `R` did the same.

   ccfe533a argued that no library caller re-solves with `MODELG=5`.
   That was wrong: mode 0 is reachable with any `MODELG`.
   Fix: decision 3, the flag.

The second follow-up also fixed two errors in the same class:

3. **A missing g-eqdsk file loaded "successfully".** `EQ_READ` called
   `EQCALQ` after `EQDSKR` failed, and `EQCALQ` reset the error. After
   an ITER01 load, the call returned `EQ_OK` with the previous
   equilibrium. In a fresh session `EQCALQ` ran on an empty state and
   the process died, which the new MCP test showed on ccfe533a's
   library.
   Fix: `EQ_READ` skips `EQCALQ` when `EQDSKR` fails. It also sets
   `IERR=0` before dispatching (it was undefined for `MODELG=15`), and
   an unknown `MODELG` now fails deterministically with a reason.
   `EQ_READ` names the file in the reason:
   `EQ_READ: MODELG=5 load failed: KNAMEQ='…' not found`.
4. **Tests:** see "Verification".

After the second follow-up, the reviewers' reproductions give:

- 0.1% and 1% offsets: `QQPS[-1]` = 3.3249 = `QSURF`.
- ×2 grid: fails with `EQCALQ: PSIPS(18)= 1.0990E+02 is more than 5%
  outside the plasma psi range [ 0.0000E+00, 1.0344E+02]: …`.
- Sign-flipped grid: fails at `PSIPS(3)=-6.4649E+00`.
- Fresh `MODELG=5` solve: `QQPS` = 0.5307…1.8826.
- Re-solve after a g-eqdsk load: `QQPS` = 0.6169…3.2041.
- Missing file: `EqlibCalculationFailedError` with the reason above.

## Verification

The tests are
[`python/eqlib/tests/test_qqps_psi_surface.py`](../../python/eqlib/tests/test_qqps_psi_surface.py)
(19 tests),
[`python/eqlib/tests/test_run_errors.py`](../../python/eqlib/tests/test_run_errors.py)
(2), and one integration test in
`python/mcp-servers/eq_mcp/tests/test_server.py`. The g-eqdsk files are
written into `tmp_path` from the committed `eqdata.ITER01` fixture, so
no new fixture is committed.

| Test | Asserts |
| --- | --- |
| `TestQqpsAfterEqrtskLoad` (4) | After an EQRTSK load: `QQPS` not all zero; `QQPS[0] ≈ QAXIS` and `QQPS[-1] ≈ QSURF` (alignment only, since those come from the same spline); interior points equal an independent natural spline of the exported `(PSIP, QPS)` profile to `1e-10` (observed 7e-16); monotone for ITER01. |
| `test_geqdsk_q_column_survives_the_load` (4) | `MODELG=5` and `25`, q = 7.0 and a negative column: returned unchanged. |
| `test_modelg5_solve_without_a_file_fills_qqps` | Fresh `MODELG=5` `eq_run(mode=0)` gives the resampled q, not zeros. |
| `test_solve_after_a_geqdsk_load_replaces_the_file_column` | g-eqdsk load (7.0), then `eq_run(mode=0)`: `QQPS` recomputed on the new grid. |
| `test_a_new_session_after_a_geqdsk_load_fills_qqps` | After a g-eqdsk load, finalize, and init, the next load fills `QQPS`. The flag reset in `eq_init`/`eq_finalize` is not observable separately: every API path to `EQCALQ` also passes `EQ_READ` or `EQLOOP`. |
| `test_other_load_and_solve_paths_fill_qqps` (2) | The `EQCALC` solve (`MODELG=2`) and a `MODELG=9` EQRTSK load get the fill. |
| `test_psips_point_just_past_the_lcfs_gets_qsurf` (3) | Offsets of 0.1% and 4.9% with the vacuum extension, and 0.1% with `NSUMAX=0, NRMAX=1000` (the `SPL1DF` out-of-range case): `QQPS[-1] = QSURF` to `1e-10`, and every point equals the clamped spline. |
| `test_psips_grid_far_outside_the_plasma_fails_the_run` (3) | 5.1% offset, ×2 grid, sign-flipped grid. `eq_run` raises `EqlibCalculationFailedError` carrying the `eq_last_error` reason. `QQPS` is then all zero, the next load works, and the reason is cleared. |
| `test_missing_geqdsk_fails_and_keeps_the_previous_equilibrium` | Raises with the file name and "not found"; the state is unchanged. |
| `test_file_load_with_an_analytic_modelg_fails_with_the_reason` | `eq_run(mode=1)` with `MODELG=2` fails and names `MODELG=2`. |
| MCP `test_run_failure_carries_the_reason` | The server's `ToolError` for a missing g-eqdsk contains the reason. |

TDD trace:

| Stage | Result |
| --- | --- |
| First fix, pre-fix baseline | `47 passed, 1 skipped` |
| First fix, RED | `2 failed` (all zeros / `QQPS[0]=0 != QAXIS=0.578`); `1 passed` vacuously (all-zero is monotone) |
| First fix, GREEN | `50 passed, 1 skipped` |
| First follow-up, new tests on 97025c6e's library | `3 failed`, `4 passed` |
| First follow-up, fixed library | eqlib `70 passed, 1 skipped`; eq MCP `46 passed` |
| Second follow-up, final tests on ccfe533a's library | `9 failed`, `12 passed` (the passes are regression guards); the MCP test's process died (missing-file load in a fresh session) |
| Second follow-up, fixed library | eqlib `84 passed, 1 skipped`; eq MCP `47 passed` |

In the follow-up rows the skip is `test_sweep`, which needs
`test_run/test_output/eq_iter01/` data. The 1e-10 equivalence baselines
`test_eq_iter01` and `test_eq_tst2` pass after every commit.

Run command (the CI flags):

```bash
python -m pytest python/eqlib/tests python/mcp-servers/eq_mcp/tests \
  -q -p no:cacheprovider --forked --timeout=120 --timeout-method=signal
```

## Why no equivalence-baseline drift

[`test_run/baselines/eq_iter01/metrics.json`](../../test_run/baselines/eq_iter01/metrics.json)
records only `scalars + profile + NRMAX/NPSMAX/...` keys; it omits
`QQPS / PPPS / TTPS / PSIPS` entirely. `compare_metrics.py` and
`extract_eq_metrics.py` likewise contain no reference to `QQPS`. So
flipping `QQPS` from all-zero to physically correct values cannot
break the 1e-10 baseline.

(That said, this episode is itself an argument for *expanding* the
recorded baselines to include the psi-surface arrays in a follow-up, so
the next "silent zero" cannot sneak past CI.)

## Discovery path

1. Observed via the `eq` MCP server's `get_state` after loading ITER01
   from its EQDSK file: `QQPS` was a length-21 array of `0.0`, even
   though `profile[].QPS` looked sensible (`0.578` → `3.33`).
2. A grep showed only five references to `QQPS` in `eq/`; the
   `MODELG=3` binary reader was not among them.
3. Confirmed by inspecting `EQRTSK`'s `READ` sequence (`eq/eqfile.f90`).
4. Two rounds of pre-push review (each an in-house reviewer plus Codex)
   found the problems in "Review follow-ups", each with a reproduction.

## Follow-ups not done here

* Add `QQPS / PPPS / TTPS / PSIPS` to the equivalence-baseline
  comparator and regenerate the baselines, so future regressions on
  the psi-surface arrays are detected at 1e-10.
* Audit other Fortran COMMON-block slots that the C ABI exposes for
  the same "read but never written by some path" pattern (e.g. is
  `TEPS` populated by `MODELG=3`? Is `OMPS`? Both *are* `READ`
  by `EQRTSK`, but nobody has checked that they survive the `EQCALQ` /
  `EQ_BPSD_PUT` round trips).
* Document the `MODELG=3` vs `MODELG=5` semantic divergence
  (binary vs g-eqdsk text) in `docs/eq-library/`.
* The loaders still abort the host process on a malformed file: most of
  `EQDSKR`'s and `EQRTSK`'s `READ`s have no `ERR=`/`IOSTAT=` (issue
  #142 class).
