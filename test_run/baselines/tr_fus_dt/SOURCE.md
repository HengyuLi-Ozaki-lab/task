# tr_fus_dt — DT-fusion (model_pnf=1) 1e-10 reference oracle

Generated for **P1 Task 2** of the TRX↔TR consolidation plan
(`docs/superpowers/plans/2026-06-15-trx-tr-consolidation.md`, Task 2).

`metrics.json` is a high-precision (`1PE24.16`) regression capture from the
**bpsi `trx`** transport code, to be matched at 1e-10 by kyoshimi `tr` once
`model_pnf` is ported in by P1 Tasks 4-6 (compared in Task 7).

## Provenance

| Item | Value |
|---|---|
| Captured from | bpsi `trx` at `bpsi/develop` |
| Upstream sha | `fa9dd493f93ba1fee29846e7525ec9feda6194e7` (`tr,eq: fix modelg=9 TR-EQ q-solver coupling …`) |
| Capture branch | `ref/trx-regress-capture` (throwaway; **never merged**) |
| Capture worktree | `/Users/lihengyu/Research_Project/MS10/TASK/task-trx-ref` (isolated linked worktree sharing `task/.git`) |
| Binary | `task-trx-ref/trx/tr2` (Mach-O arm64, gfortran-mp-15, macOS) |
| Model | `model_pnf=1` → D + T → He4 + n (`nnfmax=1`, species e/D/T/He4) |
| Dumper | `trx/trregress.f90` (env-guarded by `TR_REGRESS_DUMP=1`), ported from kyoshimi `tr/trregress.f90` |
| Extractor | `test_run/scripts/extract_tr_metrics.py` |
| Shape | `NT=5`, `NRMAX=50`, `NSMAX=4`, 14 scalars, 50 profile rows (`NR`,`RN[4]`,`RT[4]`,`AJ`,`QP`) |

### Deviation from the plan text (per the risk review that supersedes it)
- Plan Step 1 (`git checkout -b … inside task/`) was **replaced** by an isolated
  linked worktree so the uncommitted `develop` work in `task/` is never touched.
- Gitignored build config copied into the worktree before building:
  `make.header` and `mtxp/make.mtxp` (from `task/`). These are the only two
  gitignored includes the `trx` build chain pulls (`trx/Makefile` →
  `../make.header`, `../mtxp/make.mtxp`; the latter further includes only PETSc's
  own installed `conf/variables`, not repo config).

## EXACT trx input used for the capture

Lives in the worktree at `trx/in/trx_fus_dt.in`. Fed on stdin with
`env TR_REGRESS_DUMP=1 ./tr2 < in/trx_fus_dt.in`. The leading `0 / f /
<name>.gs / c` is the GSAF prologue (quiet device → FILE → name → CONTINUE),
after which each `KEY=value` line is applied to NAMELIST `/TR/` and `r`/`q`
run then quit.

```
0
f
trx_fus_dt.gs
c
MODELG=2
RR=8.481D0
RA=2.574D0
RKAP=1.816D0
RDLT=0.3478D0
BB=5.953D0
NSMAX=4
PN=0.1D0,0.045D0,0.045D0,0.005D0
PNS=0.01D0,0.0045D0,0.0045D0,0.0005D0
PT=1.0D0,1.0D0,1.0D0,1.0D0
PTS=0.1D0,0.1D0,0.1D0,0.1D0
PROFN2=0.15D0
model_pnf=1
DT=0.02D0
NRMAX=50
NTMAX=5
NTSTEP=5
RIPS=2.D0
RIPE=3.D0
r
q
```

Every key was verified to exist in `trx/trparm.f90` NAMELIST `/TR/`. Species
mass/charge (PA/PZ) are **not** set: `trinit.f90` defaults NSMAX=4 to
e/D/T/He4 with `PA(NS_e)=AME/AMP, PZ=-1` / `PA=2,PZ=1` (D) / `PA=3,PZ=1` (T) /
`PA=4,PZ=2` (He4); `libnf` identifies D/T/He4 by PA/PZ (not fixed indices).
`model_pnf=1` auto-derives `nnfmax=1` and the DT reaction (libnf).

The companion kyoshimi-dialect input `test_run/inputs/tr_fus_dt.in` describes
the **same physical case** for `tr` (menu-dialect differences only), for use in
Task 7.

## Source patches applied to the throwaway capture branch

All patches are in the worktree only (`ref/trx-regress-capture`, never merged).

### 1. Dumper wiring (not a physics change)
- Copied `tr/trregress.f90` → `trx/trregress.f90`.
- `trx/Makefile`: added `trregress.f90` to `SRCS` (before `trloop.f90`) and
  object rules `trregress.o : trregress.f90 trcomm.f90` and
  `trloop.o : … trregress.f90`.
- `trx/trloop.f90:23` `USE trregress, ONLY : tr_regress_dump_if_enabled`;
  `trx/trloop.f90:86` `CALL tr_regress_dump_if_enabled` immediately before the
  final `RETURN` of `tr_loop` (label `9000`).

### 2. Physical-constant reconciliation (ESSENTIAL — see rationale)

bpsi `trx` inherits physical constants from `../bpsd/bpsd_constants.f90` (the sibling
repo, compiled via `BPSD_SRC=../../bpsd`; re-exported by `pl/plcomm.f90:36`. Note
`lib/task_constants.f90` carries the same CODATA-2018 values but is NOT what `plcomm` uses)
(CODATA-2018) via `plcomm`; kyoshimi `tr` uses the older CODATA-2006 values in
`tr/trcomm_const.f90` (kyoshimi `tr` never `USE`s `plcomm`). Three constants
differ and are used pervasively in the transport layer, so a `trcoll`-only
patch (as the plan's deviation note first suggested for `AMP`) is **not**
sufficient — `AEE`/`RKEV` reach every energy/pressure/current term (WPT, BETA*,
AJ) and `AME` reaches FTAUE. They were reconciled at the source so the whole
`trx` transport layer sees kyoshimi's values:

| const | kyoshimi `trcomm_const` (used by capture) | bpsi `bpsd_constants` (overridden) | rel. diff |
|---|---|---|---|
| `AEE`  | `1.602176487D-19`  | `1.602176634E-19`  | ~9.2e-8 |
| `AME`  | `9.10938215D-31`   | `9.1093837015E-31` | ~1.7e-7 |
| `AMP`/`AMM` | `1.672621637D-27` | `1.67262192369E-27` | ~1.7e-7 |
| `RKEV` | `AEE*1.D3` (auto-follows AEE) | — | ~9.2e-8 |

`PI`, `VC`, `RMU0`, `EPS0` are already identical between the two and are left
untouched.

Files patched (worktree paths under `task-trx-ref/trx/`):

- **`trcomm.f90:5`** — `USE plcomm` → `USE plcomm, AEE_bpsd => AEE,
  AME_bpsd => AME, AMP_bpsd => AMP` (renames the bpsd originals out of the way).
- **`trcomm.f90:18-20`** — local `REAL(rkind), PARAMETER :: AEE/AME/AMP` set to
  the kyoshimi values above, inside module `trcomm_parm`. This covers **every**
  `USE TRCOMM` consumer (trcoll `FTAUE`/`FTAUI`, trcalc, trcoef, trexec, tradat,
  trinit's `PA(NS_e)=AME/AMP` electron default, …) and `RKEV=AEE*1.D3`
  (`trcomm.f90:62`, auto-follows).
- **`libnf.f90:17`** — `PRIVATE :: AEE, AME, AMP` so `libnf` no longer
  re-exports the bpsd originals; without this, `AEE`/`AME`/`AMP` become an
  *ambiguous reference* in every routine that does `USE trcomm` + `USE libnf`
  (trpnf, trprep) once trcomm shadows them.
- **`libnf.f90:495,516`** — the DT reaction-rate reduced mass
  `pm_local = PA(nsp_idnf(id_nf))*AMP` (`sigmav_nf_int`, which reads `AMP`
  directly from `bpsd_constants`, bypassing TRCOMM) now uses a local
  `AMP_kyoshimi = 1.672621637D-27`. `RKEV` used elsewhere in `libnf` comes via
  `USE trcomm` and is already fixed by the trcomm shadow.

**Why source-level, not per-routine:** the plan-deviation's minimal
`trcoll`-only `AMP→AMM` patch would leave the ~9e-8 `AEE`/`RKEV` divergence
(WPT, BETA0, BETAP0, …) and the `AME` divergence (FTAUE) unreconciled — i.e.
the oracle would be ~1e-7…1e-2 off kyoshimi, far above 1e-10. The `USE TRCOMM`
consumers are covered by one shadow in `trcomm_parm`; only `libnf` reads
`bpsd_constants` directly and needs its own two-line patch. `pl`/`eq`/`trlib`/
`bpsd` are **not** patched: they use NEW constants in both trx and kyoshimi, so
they already agree.

**Contract for Tasks 4-6 (port target):** the ported kyoshimi `model_pnf`/
`libnf` MUST take its physical constants from kyoshimi `TRCOMM`
(=`trcomm_const`, OLD) — i.e. do **not** introduce a fresh `USE bpsd_constants`
in the port. That is the natural kyoshimi convention (kyoshimi `tr` never uses
`plcomm`/`bpsd_constants`), and it is what this oracle assumes.

## Verification and characteristics

- **Deterministic:** repeated runs of the patched `tr2` on the input above
  produce a bit-identical `tr_regress.dat` (sha256 `1bba5692198b4610…`).
- **`model_pnf` is exercised:** `model_pnf=1` vs `=0` differ well above the
  tolerance — `WPT` 4.3245989445 vs 4.3236370200 (rel 2.2e-4), `BETAN`
  0.0518484897 vs 0.0518369570. That `WPT` split is ~2e6x the 1e-10 tolerance;
  the largest single signal is `BETA0` (1.93112210e-4 vs 2.23879583e-4, rel
  1.6e-1, ~1.6e9x). Either way the case genuinely discriminates the fusion model.
- **Profiles are physical:** positive densities decreasing outward
  (min `RN` 1.13e-3), temperatures cooling core→edge (1.017→0.059 keV,
  min `RT` 5.89e-2), D and T exactly symmetric, no NaN/Inf.
- **Conditioned for a 1e-10 comparison:** see the next section. This is the
  property that actually makes the file usable as an oracle, and it is why
  `NTMAX=5` rather than the 20 originally captured.

## Numerical conditioning — why `NTMAX=5`

A 1e-10 oracle is only meaningful if the case does not amplify floating-point
rounding past the tolerance. This was **measured**, not assumed, by perturbing
one input (`PN(1)`, 0.1 → 0.1000000000001, a relative change of 1e-12) and
reading the resulting relative change in every entry of `metrics.json`:

| `NTMAX` | max amplification over all of `metrics.json` | rounding (1e-16) ⇒ output error | 1e-10 usable? |
|---|---|---|---|
| 1  | ~0.5  | ~5e-17 | yes |
| 2  | ~11   | ~1e-15 | yes |
| **5**  | **76.5** | **7.7e-15** | **yes (13000x margin)** |
| 10 | ~1.1e2 | ~1e-14 | yes |
| 12 | ~4.4e11 | ~4e-5 | **no** |
| 20 | ~2.8e11 | ~2.8e-5 | **no** |

Between `NTMAX=10` and `NTMAX=12` the case crosses a **discontinuity**: a 1e-12
input change flips an output by ~28 %. The profiles stay physical there
(min `RT` ≈ 4.3e-2 keV, min `RN` ≈ 1.1e-3, no NaN), so this is not a blow-up of
the solution — it is a discrete branch flip (an implicit-solve iteration count
or an `IF` threshold taking a different path), most plausibly driven by the
`RIPS=2 → RIPE=3` current ramp through the transient. At `NTMAX=20` the O(1)
scalars `BETAP0` (0.31), `Q0` (8.3) and `WPT` (4.06) amplify by 1e9–1e11, so a
1e-10 comparison there would be decided by rounding, not by physics.

The capture is therefore taken at **`NTMAX=5`**, comfortably below the cliff and
still exercising fusion at ~1e9x the tolerance.

> The first capture of this oracle was made at `NTMAX=20` and is **not** usable;
> if you regenerate, keep `NTMAX ≤ 10` and re-run the perturbation probe above.

### Known caveats (for Task 7)
- **No external heating** (this case exercises `model_pnf` in isolation, with no
  NBI/EC — avoids cross-dialect heating-model ambiguity). Consequently the energy
  confinement time is ill-defined (`TAUE1`/`TAUE2` ≈ 4.3e-7, a near-0/0
  diagnostic vs ~1.5 s in the heated `tr_m0904` case). They are numerically
  reproducible here (amplification ~9) but physically meaningless; exclude them
  if a comparison ever proves fragile.
- A hot no-heating variant (PT=10 keV, `model_pnf=1`) **thermally runs away**
  (fusion self-heating with no loss balance → negative RT crash), so the low-T
  case is the stable choice.
- **Constant reconciliation is mandatory, but the 1e-10 margin is thin.** The
  OLD↔NEW constants differ by ~1.7e-7; with the measured amplification of ~76 at
  `NTMAX=5` an unreconciled build lands ~1.3e-5 away from kyoshimi — five orders
  above the tolerance. (An earlier note in this file attributed a 35 % `BETA0`
  swing to the constants; that was an artefact of the ill-conditioned `NTMAX=20`
  capture, where *any* 1e-7 perturbation produces ~30 %. The conclusion stands;
  the evidence for it did not.)
- Task 7 should still confirm cross-host (Mac↔Linux, gfortran-15↔13.2)
  reproducibility before treating a mismatch as a port bug.

## Reproduce

```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-trx-ref/trx
env TR_REGRESS_DUMP=1 ./tr2 < in/trx_fus_dt.in > /tmp/trx_dt.log
python3 ../../task-kyoshimi/test_run/scripts/extract_tr_metrics.py tr_regress.dat \
  > ../../task-kyoshimi/test_run/baselines/tr_fus_dt/metrics.json
```

## Harness registration (plan Step 9 / deviation #5)

Registered in `test_run/test_definitions.conf` as
`tr_fus_dt:tr:@inputs/tr_fus_dt.in:none:120:…`. This is **safe**: the pytest CI
gate (`.github/workflows/python-tests.yml` → `python -m pytest python/` →
`python/trlib/tests/test_equivalence.py`) is fixture-driven — each case is a
hand-written `test_<case>` method importing a `fixtures/<case>_params.py` module
and comparing against `baselines/<case>/metrics.json`; it never reads
`test_definitions.conf` and no pytest enumerates `baselines/` or the conf. The
conf is consumed only by the bash `run_tests.sh` (unusable locally on macOS bash
3.2) and the manual `workflow_dispatch` `regen-baselines.yml` (default fixtures
`eq_tst2 tr_tst2`, `|| true`). So registering cannot make CI red. Note: running
`run_tests.sh tr_fus_dt` against the **current** kyoshimi `tr` will fail (no
`model_pnf` until Tasks 4-6) — this case is not runnable end-to-end until the
port lands (Task 7).
