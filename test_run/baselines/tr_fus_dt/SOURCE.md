> **SUPERSEDED IN PART — read this first (P1 Task 7).**
>
> `metrics.json` beside this file has been RE-CAPTURED TWICE since the body of
> this document was written, from a reference binary carrying five corrections
> to trx (a 1e6 cm^3/s->m^3/s error in the reaction rate, a doubled RKEV in the
> alpha birth speed, a dead loop counter used as a species index,
> `PNF_NSNNFNR` accumulated without reset, and a missing W->MW conversion in
> ten power volume integrals), and from a corrected input deck.  Both are
> listed in full in `test_run/baselines/tr_fus_dt_hot/SOURCE.md`, which is
> authoritative for anything the two disagree on.  Corrections 1-4 are reported
> upstream as k-yoshimi/task#235 and #236.
>
> The body below is MIXED.  Current, re-measured against the capture that now
> sits beside this file: the first three "Verification and characteristics"
> bullets; the `TAUE1`/`TAUE2` half of Known caveats bullet 1; the figures in
> the heading note and the harness-registration note; the field counts in the
> EXACT-input warning; the re-run probe figures above the conditioning ladder
> (1.00 here, 2.32 on the hot deck); the ~62x / 1.4e4x fusion-signal figures
> under the ladder; and the 1.00-amplification arithmetic in the
> constant-reconciliation bullet.  Every other measured number below predates
> the corrections.
>
> That list is maintained by hand and has already been wrong twice.  If any
> number below disagrees with `tr_fus_dt_hot/SOURCE.md`, that file wins.
> Specifically:
>
> | below | actual, on the committed capture |
> |---|---|
> | `WPT` 4.3245989445 vs 4.3236370200, rel 2.2e-4 | `WPT` **4.4978791303379255** |
> | `BETA0` rel 1.6e-1 as the largest signal | the largest is `BETAP0` at rel
>   **1.4e-6**, `BETA0` next at **1.37e-6** |
> | determinism `sha256 1bba5692…` | superseded |
> | the `NTMAX` conditioning table, incl. **76.5** at NTMAX=5 | **1.00** — the
>   amplification was a product of the 1e6 error and does not survive its fix |
> | "a hot PT=10 keV variant thermally runs away" | it does not; the runaway
>   was the same 1e6 error, and the hot deck is now the primary oracle |
> | "`TAUE1`/`TAUE2` ≈ 4.3e-7, a near-0/0 diagnostic; exclude them" | **wrong,
>   and the reason was correction 5** — PINT carried PNF_TOT in W against five
>   terms in MW.  They are now **1.3796 s** and **2.1269 s** and are ordinary
>   comparison channels |
> | `PROFN2=0.15D0` in the capture deck | trx reads `PROFN2(NSM)`, so that set
>   species 1 only and left 2..4 at `trx/trinit.f90`'s 0.5; kyoshimi's
>   `PROFN2` is a
>   scalar covering every species.  The deck now spells all NSMAX values out |
>
> What still holds: the constant-reconciliation section, and the
> harness-registration note apart from its 1e-10 framing. The case
> *parameters* still hold; the sentence stating what the capture is FOR
> ("to be matched at 1e-10 ... once model_pnf is ported") does not -- the
> port landed and does not match. See the heading note below.
>
> This deck is retained as a near-threshold companion.  Its fusion signal is
> 6.2e-9, five orders below the hot deck's 1.11e-3, so it is a weak test of
> fusion -- which is itself the finding: most of what looked like fusion in the
> original capture was the unit error.

# tr_fus_dt — DT-fusion (model_pnf=1) reference capture, 1 keV

> The title of this file used to end "1e-10 reference oracle". It is not
> one: the port landed in `553b86a4` and this deck does not match at 1e-10
> (308 of 514 value fields exceed it), for reasons outside fusion that
> `tr_fus_dt_hot/SOURCE.md`'s "Known open gap" sets out. It is retained as
> the weak companion to that deck -- fusion signal rel `WPT` 6.2e-9 against
> the hot deck's 1.11e-3.

Generated for **P1 Task 2** of the TRX↔TR consolidation plan
(`docs/superpowers/plans/2026-06-15-trx-tr-consolidation.md`, Task 2).

`metrics.json` is a high-precision (`1PE24.16`) regression capture from the
**bpsi `trx`** transport code. It was written to be matched at 1e-10 by
kyoshimi `tr` once `model_pnf` was ported in by P1 Tasks 4-6; the port
landed and the match does not hold, at 1e-10 or near it. What Task 7 does
compare, and against which deck, is in `tr_fus_dt_hot/SOURCE.md`.

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

> **This block is no longer verbatim what produced the capture.** The live
> deck also carries explanatory `!` comments this block does not; those are
> inert to the namelist read. The line that MATTERS is `PROFN2`, corrected
> below to the four-species form the reference deck now carries;
> as originally printed (a single `0.15D0`) the block reproduces only 54 of
> the 514 value fields in the `metrics.json` beside this file (104 of 564 if
> the 50 integer `NR` index columns, which can never differ, are counted; drift
> counts in this file use the 514 basis), worst rel 2.19 at `RT[49][1]`. The
> live deck is `task-trx-ref/trx/in/trx_fus_dt.in`, which the `## Reproduce`
> section reads directly and which reproduces all 514.

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
! PROFN2 is PROFN2(NSM) in trx and a bare scalar in kyoshimi tr, so one value
! here would set species 1 only and leave 2..4 at trx/trinit.f90's 0.5, which
! is NOT the kyoshimi deck's meaning.  All NSMAX values are spelled out.
PROFN2=0.15D0,0.15D0,0.15D0,0.15D0
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
- **`libnf.f90:509,530`** — the DT reaction-rate reduced mass
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

The first three bullets below were re-measured against the capture that now sits
beside this file; the figures the original revision carried are in the
supersession table at the top.

- **Deterministic:** repeated runs of the patched `tr2` on the input above
  produce a bit-identical `tr_regress.dat` (sha256 `2ae8c4a49f69209b…`).
- **`model_pnf` is exercised, but barely:** `model_pnf=1` vs `=0`, same binary,
  same deck but for that line — `WPT` 4.497879130 vs 4.497879102, rel
  **6.2e-9**, i.e. 62x the 1e-10 tolerance. The largest single signal is
  `BETAP0` at rel 1.40e-6 (1.4e4x), with `BETA0` at 1.37e-6. That is a real
  signal and it is reproducible, but 62x is not a comfortable margin, and it
  is why `tr_fus_dt_hot` (rel `WPT` 1.11e-3, 1.1e7x) replaced this deck as the
  primary Task 7 oracle.
- **Profiles are physical:** positive densities decreasing outward
  (min `RN` 3.00e-3), temperatures cooling core→edge (species 1, 1.0218 →
  0.0418 keV; min `RT` over all species 4.02e-2), no NaN/Inf. D and T
  **densities** are bit-identical; their **temperatures** differ by up to
  2.98e-3 relative, as the mass ratio (PA=2 vs 3) requires -- not a symmetry
  violation.
- **Conditioned for a 1e-10 comparison:** see the next section. This is the
  property that actually makes the file usable as an oracle, and it is why
  `NTMAX=5` rather than the 20 originally captured.

## Numerical conditioning — why `NTMAX=5`

> **SUPERSEDED — the whole ladder below, not only its `NTMAX=5` row.** Every
> figure in it was measured with the 1e6 reaction-rate error in place, which
> is what made the case nonlinear; the preamble records that `NTMAX=5` goes
> from 76.5 to 1.00 once it is fixed, and the same mechanism applies at every
> row. In particular the `NTMAX` 10→12 discontinuity described under the table
> is **unverified** on the corrected binary: Task 7 re-ran the probe only at
> `NTMAX=5`, on both this deck (1.00) and the hot deck (2.32). Treat the
> ladder as a record of what the uncorrected binary did.

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

The capture is therefore taken at **`NTMAX=5`**. It still exercises fusion, but
at ~62x the tolerance (rel `WPT` 6.2e-9 against 1e-10; the largest single
field, `BETAP0`, is 1.4e4x) -- not the ~1e9x an earlier revision claimed, which
was the pre-correction `BETA0` signal.

> The first capture of this oracle was made at `NTMAX=20`. Whether it is
> usable on the corrected binary is unmeasured -- the cliff that ruled it out
> was a product of the 1e6 error. If you regenerate at any `NTMAX`, re-run the
> perturbation probe and record what it gives; do not carry the ladder's
> numbers, in either direction.

### Known caveats (for Task 7)
- **No external heating** (this case exercises `model_pnf` in isolation, with no
  NBI/EC — avoids cross-dialect heating-model ambiguity). **SUPERSEDED from
  here:** the original revision concluded that the confinement time is
  therefore a near-0/0 diagnostic (`TAUE1`/`TAUE2` ≈ 4.3e-7) and must be
  excluded. It is not. `PINT` is the ohmic power, not zero, and the collapse
  was oracle correction #5 -- `PNF_TOT` entering `PINT` in W against five
  terms in MW. On the committed capture `TAUE1` is **1.3796 s** and `TAUE2`
  **2.1269 s**, and the hot deck's counterparts are the two most sensitive
  *scalar* channels in `test_fusion_differential_matches_the_trx_reference`
  (three `RT` entries beat `TAUE2`, four beat `TAUE1`). Do not
  exclude them.
- **SUPERSEDED.** This bullet said a hot no-heating variant (PT=10 keV,
  `model_pnf=1`) *thermally runs away* (fusion self-heating with no loss
  balance → negative RT crash), so the low-T case is the stable choice. The
  runaway was the 1e6 reaction-rate error; corrected, the hot deck is stable
  and is now the **primary** Task 7 oracle. See
  `tr_fus_dt_hot/SOURCE.md`, "Why 10 keV".
- **Constant reconciliation is mandatory, but the 1e-10 margin is thin.** The
  OLD↔NEW constants differ by ~1.7e-7 (`AMP` by 1.714e-7); with the corrected
  amplification of 1.00 at `NTMAX=5` an unreconciled build lands ~1.7e-7 away
  from kyoshimi — about 1.7e3x, three orders above the tolerance. (The ~76
  amplification this bullet used to invoke does not survive the corrections;
  see the marker above the ladder.) (An earlier note in this file attributed a 35 % `BETA0`
  swing to the constants; that was an artefact of the ill-conditioned `NTMAX=20`
  capture, where *any* 1e-7 perturbation produces ~30 %. The conclusion stands;
  the evidence for it did not.)
- Task 7 should still confirm cross-host (Mac↔Linux, gfortran-15↔13.3)
  reproducibility before treating a mismatch as a port bug.

## Reproduce

```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-trx-ref/trx
env TR_REGRESS_DUMP=1 ./tr2 < in/trx_fus_dt.in > /tmp/trx_dt.log
python3 ../../task-p1-libnf/test_run/scripts/extract_tr_metrics.py tr_regress.dat \
  > ../../task-p1-libnf/test_run/baselines/tr_fus_dt/metrics.json
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
`eq_iter01 eq_tst2 tot_demo2014_short tot_ht6m_short eq_jt60 tr_iter01
tr_tst2`, `|| true`). So registering cannot make CI red. Note: `model_pnf` landed in `553b86a4`, so
this case now runs end-to-end and `run_tests.sh tr_fus_dt` would report
REGRESSION. `run_tests.sh` itself cannot run here (macOS bash 3.2, as above),
so the drift was measured by driving `tr/tr2` on `inputs/tr_fus_dt.in` with
`TR_REGRESS_DUMP=1` and diffing the extracted metrics against this baseline:
308 of 514 value fields exceed 1e-10, median rel 2.2e-7, worst 2.5e-4 at
`RT[48][1]` (this file's 1-based `RT[NR][species]` labelling;
`compare_metrics.py` prints the same entry 0-based as `profile[47].RT[0]`).
`test_definitions.conf` flags exactly that as expected drift.
