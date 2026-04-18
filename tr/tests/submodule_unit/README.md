# Phase 2 submodule unit tests

Standalone unit tests for the six submodules introduced by PR #11
(Phase 2 split of `tr/trcomm.f90`):

| Submodule         | Has alloc/dealloc? | Tests                                              |
| ----------------- | ------------------ | -------------------------------------------------- |
| `trcomm_const`    | no (PARAMETERs)    | smoke check on PI, AEE, AME, AMM, VC, RMU0, EPS0, RKEV |
| `trcomm_param`    | no (scalar inputs) | scalar assignment / readback (RR, RA, BB, DT)      |
| `trcomm_ctrl`     | yes                | alloc, dealloc, idempotent (3 cycles), shape       |
| `trcomm_mtx`      | yes                | alloc, dealloc, idempotent (3 cycles), shape       |
| `trcomm_profile`  | yes                | alloc, dealloc, idempotent (3 cycles), shape       |
| `trcomm_globals`  | yes                | alloc, dealloc, idempotent (3 cycles), shape       |

Each submodule's allocate/deallocate routine is invoked **directly**
(without going through `ALLOCATE_TRCOMM` / `DEALLOCATE_TRCOMM`) so a
regression in any single submodule is caught in isolation. Sizing
variables in `TRCOM0` (`NEQMAXM`, `NRMP`, etc.) are set up in a small
local helper `setup_sizes` that mirrors the derivation logic from
`ALLOCATE_TRCOMM`.

The test framework is intentionally minimal: a single Fortran program
with one subroutine per test case, a `(failed_count, total_count)`
counter pair, and `STOP 0` / `STOP 1` for the overall result.

## Build & run

Prerequisites: `tr2` already built (so `tr/libtr2.a` and the
`pl/eq/lib/mtxp/bpsd` libraries exist).

```sh
cd tr/tests/submodule_unit
make            # build test_trcomm_submodules
make run        # build (if needed) and run; STOP 0 = all tests passed
```

Expected output:

```
OK: all 14 submodule tests passed
STOP 0
```

## Test sizes

`setup_sizes` uses `NRMAX = 50`, `NSMAX = 2`, `NSZMAX = 0`, `NSNMAX = 2`
(matching the `tr_init` defaults) and recomputes the derived sizes
exactly as `ALLOCATE_TRCOMM` does:

```fortran
NEQMAXM = 3 * (NSMAX + NSZMAX + NSNMAX) + 1
NVM     = NEQMAXM
MWM     = 4 * NEQMAXM - 1
MLM     = NEQMAXM * NRMAX
NRMP    = NRMAX + 1
NGLF    = NRMAX
LDAB    = 6 * NEQMAXM
```
