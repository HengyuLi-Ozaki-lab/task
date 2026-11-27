# EQ: the axis search's message and a grid that reaches R <= 0 (tw#188, tw#214 part 2, tw#217 part 1)

Status: design approved by the author on 2026-11-24. One product-only pull request into `kyoshimi-develop`, from
`fix/eq-validate-group` at `44a0d010`. The issues are task-web-client's (the fork has issues disabled).

## Scope

| Issue | Part done here | Left out |
|---|---|---|
| tw#188: with `MDLEQF >= 10` an axis that triangularity moves out of the box fails the run (`ierr=103`); `validate()` checks only where the axis starts | the failure's message says in which iteration of the solve the axis left the box, that it moves as the solve goes on, and that the box must hold its whole path | a `validate()` margin for the path (the author's decision of 2026-11-24: `validate()` sees only the start, has no warning level, and an empirical margin could refuse inputs that run) |
| tw#214: EQAXIS's message for a NaN axis, and for an axis within rounding of an edge | part 2: the message names the bound the axis crossed and by how much, so `ZGMAX = 0` no longer reads `0.0000` against `0.0000` | part 1 (NaN) is done: `find_axis` returns 102 for a point that is not finite (tw#204, fork #28) |
| tw#217: the default wall `RB = 1.2` m puts R <= 0 inside a small device's grid and nothing says so | part 1: `validate()` flags an analytic solve whose grid `RR -/+ RB` reaches R <= 0 | part 2, a default `RB` that follows `RA`: a change of a default, so a question for the lead first (R8); added to the list of questions |

No equation, default or result changes: the messages and one `validate()` finding. The optimizer guard in task-web
(tw#188's "the guard following") is task-web's change.

## What happens now (measured at `44a0d010`, macOS arm64, gfortran 15, -O0 with run-time checks, eqlib, one process per case)

Defaults (RR 3, RA 1, `MODELG` 2) unless named:

| Case | `validate()` | `run(0)` |
|---|---|---|
| `MDLEQF` 10, `RDLT` 0.4, `RGMIN` 2.97 | `[]` | `EQAXIS: the search for the magnetic axis ended at (R, Z) = (2.9666, 0.0000), outside the box RGMIN..RGMAX = [2.9700, 4.5000], ZGMIN..ZGMAX = [-2.0000, 2.0000] that MDLEQF >= 10 holds the axis to: set the box around it (ierr=103)` |
| `MDLEQF` 10, `RDLT` 0.2, `RGMIN` 3.0 | `[]` | the same, `(2.9991, -0.0000)`, `[3.0000, 4.5000]` (the axis ends at 3.0219 with the default box: it leaves the box on the way) |
| `MDLEQF` 10, `ZGMAX` 0 | `ZGMAX`: OUT_OF_RANGE_AFTER_DEP | `(3.0332, 0.0000)` against `ZGMIN..ZGMAX = [-2.0000, 0.0000]`: reads as inside |
| `MDLEQF` 10 | `[]` | runs: RAXIS 3.07021, ZAXIS -7.5e-13 |
| PLATO (RR 0.7, RA 0.18, RKAP 1.9, RDLT 0.4, BB 0.3, RIP 0.04), default RB 1.2 | `[]` | runs on a grid R = -0.5 .. 1.9 m: QSURF 5.6464, PVOL 0.78477 |
| PLATO, RB 0.216 (1.2 RA) | `[]` | runs: QSURF 6.4713, PVOL 0.81022 |
| PLATO, RB 0.7 (= RR) | `[]` | runs: QSURF 6.0520, PVOL 0.79972 (the grid's first point at R = 0) |

The iteration: EQLOOP (`eq/eqcalc.f90:320-395`) calls EQRHSV, which calls EQCALV and so EQAXIS, in each of its
`NLOOP = 1..NLPMAX` iterations, before EQSOLV: iteration 1 reads the initial psi (EQPSIN), whose axis is at the start,
`(RR, 0)`; iteration 2 on reads the solve's psi. EQAXIS is also called outside the loop (EQCALQ's EQSETP after the
solve, the file loads), where no iteration applies.

## Design

### 1. EQAXIS's message (`eq/eqsub.f90`, `eq/eqcalc.f90`, `eq/eqcom1_mod.f90`)

- **The iteration.** A new module integer `EQ_NLOOP` in `eqcom1_mod` (beside `EQ_ERRMSG`), 0 by default. EQLOOP sets it
  to `NLOOP` at the top of each iteration and back to 0 on every way out (convergence, `IERR` from EQRHSV, `NLPMAX`
  exceeded). EQAXIS only reads it.
- **The bound crossed.** EQAXIS names the first window test that fails, in the order R low, R high, Z low, Z high, and
  the distance past it in `ES` form (two digits): `3.4E-03 below RGMIN`, `2.0E-05 above ZGMAX` (with `MDLEQF < 10`:
  `RR-RB`, `RR+RB`, `-RKAP*RB`, `RKAP*RB`). If no test can be named (a value the comparisons do not order), the
  clause is left out.
- **Outside the loop and in iteration 1** (`EQ_NLOOP <= 1`): today's message with the clause after the point, so the
  file loads' and today's tests' phrases stay (`python/eqlib/tests/test_load_errors.py:71-98` matches "the search for
  the magnetic axis ended at (R, Z) = (", "outside the box RGMIN..RGMAX = [1.5000, 4.5000], ZGMIN..ZGMAX = [-2.0000,
  2.0000]" and the end "(ierr=103)"):
  `EQAXIS: the search for the magnetic axis ended at (R, Z) = (3.0000, -0.0000), 2.0E-05 above ZGMAX, outside the box
  RGMIN..RGMAX = [1.5000, 4.5000], ZGMIN..ZGMAX = [-2.0000, -0.0000] that MDLEQF >= 10 holds the axis to (ierr=103)`
  (ZGMAX = -2e-5, measured; ZGMAX = 0 fails in iteration 2, about 1e-11 above it, and gets the in-loop form)
  (today's ": set the box around it" goes, to make room for the clause; no test of the library quotes it, task-web's
  wiki does (`eq/MDLEQF.md`, `eq/MODELG.md`, `eq/RGMAX.md`), refreshed at the `deps.lock` bump with its line citations).
- **In iteration 2 on**, a shorter form that leads with the crossing (what TR's `tr_last_error` keeps, below), the
  bound's value in place of the whole box, the iteration and the path (measured):
  `EQAXIS: the axis is 3.4E-03 below RGMIN = 2.9700 at (R, Z) = (2.9666, 0.0000), in iteration 2 of the solve: it moves
  as the solve goes on, and the box (MDLEQF >= 10) must hold its path (ierr=103)`; with `MDLEQF < 10`: `EQAXIS: the
  axis is <d> below RR-RB = <v> at (R, Z) = (r, z), in iteration N of the solve, outside RR -/+ RB, -/+ RKAP*RB
  (MDLEQF < 10) (ierr=103)`, without the path sentence (that window is the grid itself); no input was found that
  reaches this form (MDLEQF 0 with a wall inside the plasma fails in EQCALQP, Q0 < 0 with 102), so it is reviewed,
  not tested. Without a clause (a NaN point): `EQAXIS: the axis is at (R, Z) = (r, z), outside its window, ...`. "It
  moves", not "from (RR, 0)": a continued solve (the program's `C`) starts from the last equilibrium.
- **Length.** `EQ_ERRMSG` is `CHARACTER(256)` and stays so (TR and the C callers read it; eqlib's buffer is 512).
  With coordinates and bounds of 9 characters each (|x| < 1000 m) and a three-digit iteration the longest form is 243
  characters (the box form; the in-loop forms at most 206, the window form 212); a longer one falls back to today's
  "values unprintable" message through `IOSTAT`, as now. TR's `tr_last_error` keeps about 72 characters of EQ's
  message (a 128-character field, `TR_DIAG_MSG_LEN` in `tr/tr_state.f90`, after a 55-character prefix such as `nt=12
  t= 1.2340000E+00 s: eq_calc in tr_loop (NTEQIT): `): the in-loop forms put the bound and the distance there; the
  other forms keep today's head, which shows the point's R there as today's does. TR is not changed here (its field
  is in a `BIND(C)` struct; a longer one is TR's change). The unit-6 line (`XX EQAXIS: AXIS OUT OF PLASMA:`
  and the message) stays.
- `IERR = 103` and every path of the solve are unchanged.

### 2. `validate()`: a grid that reaches R <= 0 (`eq/eq_api.f90`)

- For an analytic solve (`analytic`, as the other checks define it), `RR - RB <= 0`: one diagnostic,
  `INCONSISTENT_PAIR` on `RB`, after the `RB < RA` check:
  `RR -/+ RB = [-0.500, 1.900] reaches R <= 0 (RB=1.200 >= RR=0.700): set RB below RR (e.g. RB = 1.2*RA)`
  (101 characters of the 127; values with their leading zero, formatted before the message is written). The hint
  fits the case: with `1.2*RA >= RR` it is `set RB below RR, at least RA=<RA>`; with `RA >= RR` no wall fits, and the
  ending is `, and no wall fits: RA=<RA> >= RR (raise RR or lower RA)` (at most 122 characters). A value that cannot
  be printed, or a message over 127 characters, gives the static `RR -/+ RB reaches R <= 0 (RB >= RR; values
  unprintable)`, which gives no advice (in the `RA >= RR` case "set RB below RR" would be wrong).
- Why the analytic solve and every `MDLEQF`: EQTORZ puts the psi grid on `RR -/+ RB` for every analytic solve
  (`eq/eqcalc.f90:899-912`; the box RGMIN..ZGMAX is not that grid), and the file loads bring their own grid.
- It changes no run: `eq_run` does not read `validate()`. It reaches the callers that ask before a run: eqlib's
  `Eq.validate()`, the EQ MCP server's `validate` tool, and through them task-web, which already refuses `RB >= RR` for
  an analytic run (task-web #133), the same condition.
- The header comment's category list and the long comment at the box checks gain this check and the limit of tw#188
  (the path is not seen before the run; the failure's message says where and when).

### 3. Tests (`python/eqlib/tests/`, one test per case, no `subTest`)

- `ZGMAX = -2e-5` (it fails in iteration 1 on every build; `ZGMAX = 0` fails in iteration 2 on rounding of about 1e-12,
  which a Linux `-O3` build may not repeat): `2.0E-05 above ZGMAX` with the box printed as before, `[-2.0000, -0.0000]`.
- `RDLT` 0.4 with `RGMIN` 2.97, and `RDLT` 0.2 with `RGMIN` 2.9995 (the axis starts 5e-4 inside, ends at 3.0219 with
  the default box and passes 2.9991 on the way): the in-loop form, `in iteration N` with N >= 2, the crossing within
  the first 72 characters; it fits in 256 characters and is not the fallback.
- `EQ_NLOOP` back to 0: a TST-2 load after a solve in the same instance, converged and failed, gets the box form.
- A file load that fails in EQAXIS (the existing `test_load_errors.py` cases) keeps its phrases, with the clause.
- `validate()`: PLATO with the default RB is flagged (`RB`, `INCONSISTENT_PAIR`); RB 0.216 is not; RB = RR exactly is
  flagged; RB just below RR is not; a file `MODELG` with the same numbers is not checked; the defaults return `[]`.
- Through the EQ MCP server's `validate` tool, the new finding is returned (one test).
- Mutation check: the new `validate()` condition (`<=` to `<`, the check removed) and the clause's bound order, each
  seen to fail a test.
- Results unchanged: every state scalar of about ten cases (defaults; `MDLEQF` 10 with `RDLT` -0.4..0.4; PLATO with
  three RB values; ITER-like and a file load) equal to the bit before and after, measured on the built libraries.

### 4. Documents

- The EQ pages of `docs/sphinx/modules/eq` (en, ja) where they list `validate()`'s checks and `ierr=103`; eqlib's
  README if it lists them; the CHANGELOG; row AG of `docs/product-line/upstream-status.md` in the last commit, after
  `kyoshimi-develop` is merged in (R9).

## Verification

The full suite with the CI flags on macOS (all seven libraries, `MONO_LIB_PATH` unset), the C checks (`eq_api_check`),
the results-unchanged comparison above, the pull request's four checks.

## Questions for the lead (R8, no change made)

- tw#217 part 2: should `RB` follow `RA` when it is not set (for example `RB = 1.2*RA`, which keeps the default case's
  wall at 1.2 m)? It would change every run that sets `RA` and leaves `RB`; TR's `MODELG` 9 hands EQ `RB = RA + 0.1`
  (`tr/trbpsd.f90:120-128`), which EQ drops (tw#207).

## The upstream route

Product-only as cut (`eq/eq_api.f90`'s `validate()` and the message of EQAXIS are the product line's, from fork #18, #21
(`40141ef9`, tw#187) and #28); the ledger row says what would go upstream after the sync.
