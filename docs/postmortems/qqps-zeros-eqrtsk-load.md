# `QQPS` is all zeros after `MODELG=3` (EQRTSK) loads

**Date:** 2026-05-10 (fix); 2026-09-28 (review follow-up)
**Component:** `eq/` (TASK/EQ Fortran library)
**Severity:** Low. A silent data-quality bug: no crash, and callers that
use the per-`NR` `profile[].QPS` field are unaffected.
**Affects:** every consumer of `EqState.qqps` (the C-API / Python wire
field documented as "q profile (psi-surface)") after a binary EQDSK load
via `equnit::eq_load(MODELG=3)`, including the `eq` MCP server's
`get_state` payload.
**Fixed in:** `EQCALQ` (`eq/eqcalq.f90`), in two commits: the first fill
(cherry-picked as 97025c6e) and a follow-up after the pre-push reviews.
See "Fix" and "Review follow-up" below.

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

Final behaviour after the fix:

| Load path | `QQPS` |
| --- | --- |
| `MODELG=5` / `25` (g-eqdsk text, `EQDSKR`) | The file's q column, untouched |
| Everything else (`MODELG=3`/`9` `EQRTSK`, `8`, `15`, `EQCALC` solves) | The per-`NR` q profile resampled onto `PSIPS` |
| A `PSIPS` point outside the `PSIP` range | Clamped to the nearest end of the range (q on the first or last flux surface) |
| Degenerate `PSIP` grid (`SPL1DF` error 9) | `EQCALQ` fails; `eq_run` returns `EQ_ERR_CALC_FAILED` |

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
| `eq/eqcom1_mod.f90:63` | `REAL(8) :: QQPS(NPSM)` declaration |
| `eq/eq-eqdsk.f90:62`   | `read (neqdsk,2020) (QQPS(i),i=1,NPSMAX)`: the **g-eqdsk text** reader `EQDSKR`, the only code that reads a q column |
| `eq/eqfile.f90:110-112` | `EQ_READ` sends exactly `MODELG=5`/`25` to `EQDSKR`, then calls `EQCALQ` |
| `eq/equnit.f90:91`     | `eq_load` calls `EQCALQ` again after every load |
| `eq/eqcalq.f90` (`EQCALQ`) | The `QQPS` fill added by this fix |
| `eq/eq_api_common.f:186` | `QQPS_OUT(I) = QQPS(I)`: the C ABI getter |

`eq/eqfile.f90:149-153` (`EQRTSK`, the `MODELG=3` binary reader):

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
(`eq/eqcalq.f90`):

```fortran
      IF(MODELG.NE.5.AND.MODELG.NE.25) THEN
         PSIPLO=MIN(PSIP(1),PSIP(NRMAX))
         PSIPHI=MAX(PSIP(1),PSIP(NRMAX))
         DO NPS=1,NPSMAX
            PSIPQ=MIN(MAX(PSIPS(NPS),PSIPLO),PSIPHI)
            CALL SPL1DF(PSIPQ,QQPS(NPS),PSIP,UQPS,NRMAX,IERRQ)
            IF(IERRQ.NE.0) THEN
               WRITE(6,*) 'XX EQCALQ: SPL1DF for QQPS: IERR=',IERRQ
               QQPS(1:NPSMAX)=0.D0
               IF(IERR.EQ.0) IERR=IERRQ
               EXIT
            ENDIF
         ENDDO
      ENDIF
```

Design decisions:

1. **Where:** at the end of `EQCALQ`. Doing it inside `EQRTSK` would not
   work, because `UQPS` does not exist yet at that point of the
   `eq_load → eqload → EQ_READ → EQRTSK`, then `eqcalq`, chain.
2. **Reuse `UQPS` rather than cache a new `UQQPS` table:** `QQPS` and
   `profile[].QPS` then come from the same spline and stay consistent.
   `QQPS[0] == QAXIS` exactly; `QQPS[-1]` differs from `QSURF` by 4e-6
   for ITER01, because the file's `PSIPS[-1]` and the `PSIPA` that
   `EQAXIS` recomputes differ by 4.7e-5 (out of 103).
3. **g-eqdsk loads keep the file's q (`MODELG=5`/`25`):** see "Review
   follow-up", finding 1.
4. **Out-of-range points are clamped, not zero-filled:** see "Review
   follow-up", finding 2.
5. **A degenerate `PSIP` grid fails the run:** `SPL1DF` error 9
   (`PSIP(1) == PSIP(NRMAX)`) returns no value. `EQCALQ` zeroes `QQPS`
   and returns 9 unless an earlier step already set an error. A unit-6
   message alone would not be enough, because API callers never see it:
   the MCP servers isolate the library's stdout. In practice the grid is
   never degenerate once `NRMAX >= 2`.
6. **No `STOP`:** per `CLAUDE.md` "Fortran library discipline", a
   library-reachable `STOP` aborts the host process (pytest, MCP
   server, ...).

## Review follow-up

The first version of the fix (97025c6e) ran the fill unconditionally and
wrote `0.0` whenever `SPL1DF` returned any error. Two independent
pre-push reviews found two problems:

1. **It overwrote the g-eqdsk q column (HIGH).** A `MODELG=5`/`25` load
   reads `QQPS` from the file, and `EQCALQ` runs right after that read
   (`eqfile.f90:112`) and again in `eq_load` (`equnit.f90:91`). The
   fill replaced the file's q with TASK's recomputed q: a column of 7.0
   came back as 0.578…3.325, and a negative-q file came back positive.
   task-web plots q(ψ) from `QQPS`, and its wiki says `MODELG=5` reads
   `QQPS` straight from the file.

   Fix: skip the fill when `MODELG` is 5 or 25. `EQ_READ` sends exactly
   those values to `EQDSKR`, the only code that reads a q column, and
   both `EQCALQ` calls on that path see the same `MODELG`. So the test
   matches "QQPS came from the file" without new state. `EQCALQ`
   already keys g-eqdsk handling on `MODELG`: the `MODELG=5` branches of
   `EQSETP`, `DPPFUNC` and `DTTFUNC` use the file's derivative columns.
   A "QQPS supplied by the file" flag was the alternative. It would
   differ only when an equilibrium is re-solved while `MODELG` is still
   5/25. No library caller does that: `eq_run` mode 0 is documented for
   `MODELG=2`, and the transport codes call `eq_calc` only in their
   coupled-EQ modes (`MODELG=9` in tr/trx/trm, geometry model 8/9 in
   trn), not after a g-eqdsk load. Only the interactive menu can, by
   typing `R` or `C` after `K`, and there `DPPFUNC`/`DTTFUNC` still read
   the file's columns. A flag would therefore add state to set, clear,
   and reset across `eq_finalize`/`eq_init` without making that
   combination consistent.
   Callers checked: `EQ_READ` and `eq_load` (`MODELG=5`/`25` untouched;
   `3`/`9`/`8`/`15` filled); `eq_run` mode 0 and `eq_calc` (`EQCALC`
   with `MODELG=2`/`9`: filled); the menu's `L`/`K` loads and `R`/`C`
   re-solves in `eqmenu.f90` (by `MODELG`, as above); and the other
   modules that call `eqcalq` after their own load (wm, fp, wr, ob),
   none of which read `QQPS`.

2. **It reintroduced a silent zero (MED).** `SPL1DF` returns error 1
   or 2 when the point lies more than half an average cell outside the
   grid, and it still returns a value (a cubic extrapolation from the
   end cell). The loop discarded that value and wrote `0.0`, while the
   run reported success. Reproduction: build a g-eqdsk whose axis psi is
   0.1% deeper than the one `EQAXIS` finds. Its `PSIPS` grid then ends
   0.1% beyond `PSIPA`. Load it with `NSUMAX=0`, so `PSIP` ends at the
   LCFS, and `NRMAX=1000`, so 0.1% is more than half an average cell.
   The result was `QQPS[-1] = 0.0`. Once finding 1 is fixed, that
   g-eqdsk load no longer runs the fill, but saving the state and
   reloading it as `MODELG=3` still reaches it, since `EQRTSK` keeps the
   saved `PSIPS`.

   Fix: clamp each `PSIPS` point into the `PSIP` range before
   `SPL1DF`. `FNPSIP` (`eq/eqsplf.f90`) already clamps its argument to
   the `PSIT` range the same way, and `TTFUNC`/`DTTFUNC` clamp to the
   end of `PSIPS`. With the clamp, `SPL1DF` cannot report 1/2, so its
   only possible error is 9 (decision 5). Clamping was chosen over
   keeping the extrapolated value because the extrapolation is
   unbounded for a large mismatch: a cubic from one small end cell
   carried over many cells. A point beyond the last flux surface also
   has no q of its own, so q on that surface is the defensible value.
   A point inside the range reaches `SPL1DF` with the same argument as
   in the first fix, so its value does not change. The ITER01 load and
   the analytic `mode=0` run, with or without `NSUMAX=0` and
   `NRMAX=1000`, have no point outside the range.

The first version's comment also said callers "see the warning" and can
fall back to `profile[].QPS`. API callers never see unit-6 output,
because the MCP servers isolate stdout. The comment now says so.

## Verification

[`python/eqlib/tests/test_qqps_psi_surface.py`](../../python/eqlib/tests/test_qqps_psi_surface.py)
has seven tests. The g-eqdsk files are written into `tmp_path` from the
committed `eqdata.ITER01` fixture, so no new fixture is committed.

| Test | Asserts |
| --- | --- |
| `test_qqps_not_all_zero` | `any(q != 0)` after an EQRTSK load: the original bug. |
| `test_qqps_endpoints_match_scalars` | `QQPS[0] ≈ QAXIS`, `QQPS[-1] ≈ QSURF` to `1e-4`. The scalars come from the same `UQPS`, so this checks alignment only. |
| `test_qqps_interior_matches_independent_spline` | Each interior `QQPS` point equals a natural cubic spline of the exported `(PSIP, QPS)` profile, built independently in Python, to `1e-10` relative (observed 7e-16). |
| `test_qqps_monotone_for_iter_baseline` | Monotone for ITER01; would need relaxing for a non-monotone-q fixture. |
| `test_geqdsk_q_column_survives_the_load[q_constant_7]` | A `MODELG=5` file with q = 7.0 returns exactly that column. |
| `test_geqdsk_q_column_survives_the_load[q_negative]` | Same for a negative q column. |
| `test_psips_point_beyond_psip_range_is_clamped` | Saved-and-reloaded offset grid (see finding 2): the last `PSIPS` point is more than half a cell beyond `PSIP`, no `QQPS` entry is `0.0`, and `QQPS[-1]` is q on the last flux surface. |

TDD trace:

| Stage | Result |
| --- | --- |
| First fix, pre-fix baseline | `47 passed, 1 skipped` |
| First fix, RED | `2 failed` (all zeros / `QQPS[0]=0 != QAXIS=0.578`); `1 passed` vacuously (all-zero is monotone) |
| First fix, GREEN | `50 passed, 1 skipped` |
| Follow-up, suite on 97025c6e's library | `66 passed, 1 skipped` (eqlib); `46 passed` (eq MCP server) |
| Follow-up, new tests on 97025c6e's library | `3 failed` (both `MODELG=5` cases came back as TASK's q 0.578…3.325; the reloaded offset grid had `QQPS[-1] = 0.0`), `4 passed` |
| Follow-up, fixed library | `70 passed, 1 skipped` (eqlib); `46 passed` (eq MCP server) |

In the follow-up rows the skip is `test_sweep`, which needs
`test_run/test_output/eq_iter01/` data. The 1e-10 equivalence baselines
`test_eq_iter01` and `test_eq_tst2` pass after both commits.

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
3. Confirmed by inspecting `EQRTSK`'s `READ` sequence
   (`eq/eqfile.f90:149-153`).
4. The two pre-push reviews of 97025c6e found the g-eqdsk overwrite and
   the zero fill (see "Review follow-up").

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
