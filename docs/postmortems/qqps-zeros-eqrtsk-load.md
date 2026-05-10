# `QQPS` is all zeros after `MODELG=3` (EQRTSK) loads

**Date:** 2026-05-10
**Component:** `eq/` (TASK/EQ Fortran library)
**Severity:** Low — silent data quality bug, no crash, downstream callers
that use the per-`NR` `profile[].QPS` field are unaffected.
**Affects:** every consumer of `EqState.qqps` (the C-API / Python wire
field documented as "q profile (psi-surface)") after a binary EQDSK load
via `equnit::eq_load(MODELG=3)`. Includes the `eq` MCP server's
`get_state` payload.
**Fixed in:** `EQCALQ` (`eq/eqcalq.f90`). See "Fix" below.

---

## TL;DR

`EQRTSK` (the binary EQDSK reader behind `MODELG=3`) reads `PSIPS`,
`PPPS`, `TTPS`, `TEPS`, `OMPS` on the psi-surface grid but **never
reads `QQPS`** — the on-disk format does not store it. Downstream
`EQCALQ` recomputes `QPS` on the per-`NR` flux-surface grid (returned
to callers as `profile[].QPS`) but never projects it onto `PSIPS`. The
`QQPS` slot in COMMON therefore stays at its zero-initialised value,
and the C ABI getter (`eq_api_common.f:186 — `QQPS_OUT(I) = QQPS(I)`)
faithfully returns all zeros.

This is a TASK source-code bug, not an MCP / Python wrapper bug.

## Symptom

After a normal load via the MCP server:

```python
import json
# (after MODELG=3, KNAMEQ=eqdata.ITER01, run(mode=1))
state = eq.get_state()
print(state["QQPS"])  # → [0.0, 0.0, ..., 0.0]   (length 21 for ITER01)
print(state["scalars"]["QAXIS"])  # 0.5784   ← real q on axis
print(state["scalars"]["QSURF"])  # 3.3252   ← real q at LCFS
print(state["profile"][0]["QPS"]) # 0.5784   ← per-NR profile is fine
```

`QQPS` is documented as "q profile (psi-surface)" in
[`python/eqlib/state.py:60-70`](../../python/eqlib/state.py) and is exposed
in the C struct in [`eq/eq_api.h`](../../eq/eq_api.h). Users naturally
expect it to mirror `PPPS` / `TTPS` (which **are** populated). Instead
they get a length-`NPSMAX` array of `0.0`.

The bug is silent: no error, no warning, and `compare_metrics.py` did
not catch it because the equivalence baseline (`test_run/baselines/`)
only records `scalars + profile + dimensions`, not the psi-surface
arrays.

## Where it lives in the code

Five total references to `QQPS` in `eq/`:

| Site | Role |
| --- | --- |
| `eq/eqcom1_mod.f90:63` | `REAL(8) :: QQPS(NPSM)` declaration in COMMON |
| `eq/eq-eqdsk.f90:61`   | `read (neqdsk,2020) (QQPS(i),i=1,NPSMAX)` — **g-eqdsk text** path; correctly populates QQPS for non-`MODELG=3` loads |
| `eq/eq-eqdsk.f90:129, 147` | Two commented-out debug `write` statements |
| `eq/eq_api_common.f:186` | `QQPS_OUT(I) = QQPS(I)` — C ABI getter |

`eq/eqfile.f90:148-153` (`EQRTSK`, the `MODELG=3` binary reader):

```fortran
READ(21) (PSIPS(NPS),NPS=1,NPSMAX)
READ(21) (PPPS(NPS),NPS=1,NPSMAX)
READ(21) (TTPS(NPS),NPS=1,NPSMAX)
READ(21) (TEPS(NPS),NPS=1,NPSMAX)
READ(21) (OMPS(NPS),NPS=1,NPSMAX)
!  ← no `READ(21) (QQPS(NPS),NPS=1,NPSMAX)`
```

`EQCALQ` (the equilibrium-recompute called by `equnit::eq_load`) only
builds q on the per-`NR` mesh:

* `eq/eqcalq.f90:983` — `CALL SPL1D(PSIP, QPS, DERIV, UQPS, NRMAX, 0, IERR)`
  builds the spline `UQPS` from `(PSIP, QPS)` on the flux-surface grid
  of length `NRMAX`.
* `eq/eqcom3_mod.f90` declares `UPSITV / UQPV / UTTV` (volume-grid
  splines) and `UPPPS / UTTPS` (psi-surface splines for pressure and
  toroidal field), but **no `UQQPS` or `UDQQPS`** — so historically
  there was nothing to interpolate `QPS` onto `PSIPS` either.

## Root cause

`MODELG=3` (`EQRTSK` binary) and `MODELG=5` (`g-eqdsk` text) take
different code paths to populate the psi-surface arrays. The text
path **reads** `QQPS` directly from the file (`eq-eqdsk.f90:61`); the
binary path skips it because the legacy on-disk schema never wrote it.

`EQCALQ` was happy to build `UQPS` from the per-`NR` mesh (because
that's the spline downstream metric routines need internally), but
nobody added the symmetric step of re-sampling that spline onto
`PSIPS` to keep `QQPS` consistent. The COMMON-block slot is
zero-initialised at process start and is never touched by the
`MODELG=3` path, so the C-API getter returns zeros.

## Fix

Add a final post-pass at the end of `EQCALQ` that interpolates `UQPS`
onto `PSIPS` and stores the result in `QQPS`. Diff (`eq/eqcalq.f90`):

```diff
       SUBROUTINE EQCALQ(IERR)

+      USE libspl1d
       USE plcomm
       USE eqcom0_mod
       USE eqcom1_mod
       USE eqcom3_mod
       IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
       INTEGER, INTENT(OUT) :: IERR
       ...
       CALL EQSETS_RHO(IERR)
       CALL EQSETS(IERR)
+!
+!     ----- Project per-NR QPS onto the PSIPS (psi-surface) grid
+!           to populate QQPS, mirroring how PPPS / TTPS live on
+!           PSIPS. EQRTSK (MODELG=3 binary) does not store QQPS in
+!           the file (eq/eqfile.f90 EQRTSK skips it), so without
+!           this loop QQPS stays at the zero-initialised COMMON
+!           value and the C-API getter returns all zeros for the
+!           psi-surface q profile. UQPS was just built above by
+!           SPL1D(PSIP,QPS,...) so SPL1DF gives the same q profile
+!           as profile[].QPS, just resampled onto PSIPS.
+!           Failures are logged but non-fatal (per CLAUDE.md:
+!           library-reachable STOP would abort the host process);
+!           callers that need QQPS see the warning and fall back
+!           to profile[].QPS.
+!
+      IERR_SAVE = IERR
+      DO NPS=1,NPSMAX
+         CALL SPL1DF(PSIPS(NPS),QQPS(NPS),PSIP,UQPS,NRMAX,IERR)
+         IF(IERR.NE.0) THEN
+            WRITE(6,*) 'XX SPL1DF for QQPS at NPS=',NPS,' IERR=',IERR
+            QQPS(NPS) = 0.D0
+         END IF
+      END DO
+      IERR = IERR_SAVE
 !
 !     ----- Phase L-0 regression dump (env-guarded, no-op unless
 ...
```

Key design decisions:

1. **Where:** at the end of `EQCALQ`, after `EQCALQP` has already
   built `UQPS`. Putting it inside `EQRTSK` itself would not work
   because `UQPS` does not exist yet at that point in the
   `equnit::eq_load → eqload → ... → eqcalq` chain.
2. **Why `SPL1DF` instead of caching a new `UQQPS` table:** by
   reusing the existing `UQPS` we guarantee that `QQPS` and
   `profile[].QPS` are derived from the same spline, so they stay
   numerically consistent. The endpoint match `QQPS[0] == QAXIS` is
   bit-exact; `QQPS[NPSMAX-1] == QSURF` agrees to ~4 ppm (smoothness
   defect at the LCFS boundary, where the per-`NR` mesh extends into
   a vacuum region).
3. **Error handling — `IERR_SAVE`:** the original `EQCALQ` returns
   the `IERR` left over from `EQSETS`. We must not let an `SPL1DF`
   warning at e.g. one boundary `PSIPS` value override that. We
   save and restore `IERR` around the loop and log per-point
   failures to unit 6.
4. **No `STOP`:** per `CLAUDE.md` "Fortran library discipline" any
   library-reachable `STOP` aborts the host process (pytest, MCP
   server, …). On a per-point spline failure we zero-fill that slot
   and continue.

## Verification

Three new regression tests in
[`python/eqlib/tests/test_qqps_psi_surface.py`](../../python/eqlib/tests/test_qqps_psi_surface.py)
cover the bug and the fix:

| Test | Asserts |
| --- | --- |
| `test_qqps_not_all_zero` | `any(q != 0)` after EQRTSK load — directly catches the regression. |
| `test_qqps_endpoints_match_scalars` | `QQPS[0] ≈ QAXIS` and `QQPS[-1] ≈ QSURF` to `1e-4` (3e-5 relative). |
| `test_qqps_monotone_for_iter_baseline` | Monotonicity holds for the ITER01 fixture. (Would need relaxing if a non-monotone-q fixture is ever added.) |

TDD trace:

| Stage | Result |
| --- | --- |
| Pre-fix baseline | `47 passed, 1 skipped` |
| RED (test added, fix not yet applied) | `2 failed` for the documented reasons (all zeros / `QQPS[0]=0 != QAXIS=0.578`); `1 passed` vacuously (all-zero is monotone). |
| GREEN (fix applied) | `50 passed, 1 skipped`. **Equivalence baselines `test_eq_iter01` and `test_eq_tst2` still pass at `1e-10` tolerance** — the fix only adds non-zero data; the comparator doesn't read `QQPS`, so no baseline regeneration is needed. |

Run command:

```bash
EQLIB_PATH=$(pwd)/eq/libeqapi.so \
  python -m pytest python/eqlib/tests/ \
  --forked --timeout=120 --timeout-method=signal
```

## Why no equivalence-baseline drift

[`test_run/baselines/eq_iter01/metrics.json`](../../test_run/baselines/eq_iter01/metrics.json)
records only `scalars + profile + NRMAX/NPSMAX/...` keys; it omits
`QQPS / PPPS / TTPS / PSIPS` entirely. `compare_metrics.py` and
`extract_eq_metrics.py` likewise contain no reference to `QQPS`. So
flipping `QQPS` from all-zero to physically-correct values cannot
break the 1e-10 baseline.

(That said: this episode is itself an argument for *expanding* the
recorded baselines to include the psi-surface arrays in a follow-up,
so the next "silent zero" can't sneak past CI.)

## Discovery path

1. Observed via the `eq` MCP server's `get_state` after running an
   ITER01 EQDSK load: `QQPS` was a length-21 array of `0.0` even
   though `profile[].QPS` looked sensible (`0.578` → `3.33`).
2. Grep showed only five references to `QQPS` in `eq/`; the
   `MODELG=3` binary reader was not among them.
3. Confirmed by inspecting `EQRTSK`'s `READ` sequence
   (`eq/eqfile.f90:148-153`).

## Follow-ups not done in this PR

* Add `QQPS / PPPS / TTPS / PSIPS` to the equivalence-baseline
  comparator and regenerate the baselines, so future regressions on
  the psi-surface arrays are detected at 1e-10.
* Audit other Fortran COMMON-block slots that the C ABI exposes for
  the same "read but never written by some path" pattern (e.g. is
  `TEPS` populated by `MODELG=3`? Is `OMPS`? Both *are* `READ`
  by `EQRTSK` but I have not verified they survive `EQCALQ` /
  `EQ_BPSD_PUT` round-trips).
* Document the `MODELG=3` vs `MODELG=5` semantic divergence
  (binary vs g-eqdsk text) in `docs/eq-library/`.
