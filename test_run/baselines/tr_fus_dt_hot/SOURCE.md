# `tr_fus_dt_hot` — D-T fusion at 10 keV, reference capture

`metrics.json` is a capture of the **bpsi `trx`** transport code, to be matched
by kyoshimi `tr` with `model_pnf=1`. It is the primary P1 Task 7 oracle; the
1 keV `tr_fus_dt` case is retained but is a much weaker test (see "Why 10 keV").

| Item | Value |
|---|---|
| Source tree | `task-trx-ref`, branch `ref/trx-regress-capture` |
| Input | `trx/in/trx_fus_dt_hot.in` (physics-identical to `test_run/inputs/tr_fus_dt_hot.in`) |
| Dumper | `trx/trregress.f90`, env-guarded by `TR_REGRESS_DUMP=1` |
| Extractor | `test_run/scripts/extract_tr_metrics.py` |
| Case | `modelg=2` analytic geometry, species e/D/T/He4, `NSMAX=4`, `NRMAX=50`, `NTMAX=5`, `PT=10 keV`, `PTS=1 keV` (edge is one tenth of core), `RIPS=2 -> RIPE=3` |
| Determinism | two consecutive runs give a bit-identical `tr_regress.dat` |
| Deck caveat | `PROFN2` is `PROFN2(NSM)` in trx and a bare scalar in kyoshimi, so the two decks are *not* byte-comparable on that line -- see "The two decks are not byte-identical, on purpose" |

## The reference is patched, and this section is the list

`trx` as shipped cannot serve as a 1e-10 oracle for fusion. Five defects were
found, each verified against an authority outside the codebase before being
corrected, and each carries a `ref/trx-regress-capture ONLY` comment at its
site. 1-4 are on the fusion path and are reported upstream alongside
k-yoshimi/task#235; 5 is a diagnostic-only unit slip spanning four subsystems
and is reported separately.

1. **Reaction rate 1e6 too large.** The `svnf_*` tables in `trx/libnf.f90` are
   in cm^3/s, and `sigmav_nf` returned them unconverted, while its consumer
   (`SNF = wgt*PN1*PN2*1.D20*RATE_NF`, with `RN` in 1e20 m^-3) needs m^3/s.
   Checked against Bosch-Hale (Nucl. Fusion 32 (1992) 611): read as cm^3/s the
   table reproduces the published D-T reactivity to 0.80-1.01 over 1-100 keV
   and peaks at 8.7e-16 cm^3/s. The identical table lives upstream as
   `trm/libsigma.f90`'s `sigmavma_dt`, and **both** of its consumers there
   convert — `trm/trpnf.f90` and `trx/trsigmavnf.f90` each write `*(1E-6)`.
   The `libnf` rewrite copied the table forward and dropped the conversion.
   Corrected at `sigmav_nf`'s one computed exit.

2. **Doubled `RKEV` in the birth speed.** `eng_nnf` is already in joules
   (`eng_idnf(id_nf_dt) = 3.5D3*RKEV`), and `trx/trpnf.f90` multiplied by
   `RKEV` again. Unfixed, `VF` came out at 1.27e-8 of its true value and
   `TAUF` was noise — negative at Te = 10 keV. Both siblings apply exactly one
   `RKEV`: trx's own `trpnb.f90`, and kyoshimi's `tr/trpnf.f90`.

3. **Dead loop counter used as a species index.** The slowing-down block read
   `PA(ns)` / `PZ(ns)` / `COULOG(1,ns,...)` where `ns` was the terminated
   counter of the preceding `DO NS=1,NSMAX`, i.e. `NSMAX+1`; `nsp`, the
   reaction's product species, was assigned one line above and never used. For
   this deck `trinit.f90`'s `DO NS=5,NSM` fallback gives `PA(5)=PZ(5)=1`
   instead of the alpha's 4 and 2. `TAUS` is unaffected (`PA/PZ**2` is 1 both
   ways); the error reaches `TAUF` through `VF`, which was 2x too large.

4. **`PNF_NSNNFNR` accumulated without reset.** It is the one output of five
   not zeroed at entry while being accumulated with `+`, so the alpha birth
   power grew linearly in the number of `tr_pnf` calls — measured 1x, 2x, 3x
   on successive calls of this deck, reaching a factor of order the call count
   (~40 over 5 steps).

5. **W not converted to MW in ten power volume integrals.** Every power
   integral in the *legacy* channels of `trx/trrslt.f90`'s `TR_GLOBAL`
   divides by `1.D6` -- `POHT`, `PEXT`, `PRBT`/`PRCT`/`PRLT`/`PRSUMT`/
   `PCXT`/`PIET`. None of the newer per-channel aggregation blocks did: RF
   (`PIC`/`PLH`/`PEC`), NBI (`PNB`/`PNBIN`/`PNBCL`), fusion (`PNF`/`PNFIN`/
   `PNFCL`) and fusion-neutron (`PNFNN`). So `PNF_TOT` entered
   `PINT = POHT+PNB_TOT+PRF_TOT+PNF_TOT+PEXST` in W against five terms in
   MW, inflating `PINT` by 1e6 the moment `model_pnf=1`: `TAUE1` collapsed
   55.4 s -> 2.26e-4 s, `TAUE2` 1.081 s -> 2.26e-4 s, and `QF` was 1e6 high.
   The authority is internal and unambiguous -- the eight legacy siblings in
   the same subroutine, and the `[MW/...]` axis labels in `trx/trgrar.f90`.
   The solver never sees it: it consumes the W/m^3 profile `PNF_NSNNFNR`
   directly, which is why `WPT` carried a correct fusion signal while every
   `PINT`-derived diagnostic did not. The particle-source integrals beside
   these (`SNB_`, `SNF_`, `SNFNN_`, `SIE`, `SPEL`, `SPSC`) are in 1/s and
   correctly take no conversion.

   A sixth, **not** corrected: `SNFNN_NR`/`PNFNN_NR` are summed from the
   charged-particle arrays `SNF_NNFNR`/`PNF_NNFNR` while the `_NNF` totals
   four lines later use `SNFNN_NNFNR`/`PNFNN_NNFNR`. The two are
   inconsistent, but which is intended is an upstream question and no oracle
   channel reads them.

## What this oracle does NOT exercise

Two gaps, both measured. Neither is a detail: together they mean this capture
validates the **alpha power and slowing-down** channel and nothing else.

**1. Collisional transfer.** `PNFCL_NSNNFNR` is zeroed in `trx/trpnf.f90` and
never assigned by any line in `trx`, so the alpha energy that leaves `RW` at
rate `1/TAUF` is discarded instead of heating the thermal species. That is a
missing block of physics rather than a typo, and supplying it here would make
this capture an implementation of ours rather than a record of upstream's, so
it was deliberately left alone. The kyoshimi side mirrors it: `tr_pnf`
publishes `SNF`, `PNF` and `TAUF` and does **not** write `PFIN`, `PFCL`, `RNF`
or `RTF`.

A consequence worth stating, because it is an internally inconsistent state in
the running solve rather than merely a missing term: `PNF` now drives
`RW(:,2)` non-zero while `RNF(:,2)`/`RTF(:,2)` stay 0, so `trrslt_globals.f90`
reports a fast-alpha energy with zero fast-alpha density and temperature, and
`trmodels.f90` sees a zero fast-alpha density gradient against a non-zero
fast-alpha energy.

**2. The particle source is not in the loop.** `MDLEQN` defaults to 0
(`tr/trinit.f90`) and neither deck overrides it, so the density equations are
never assembled and `SSIN` — the only consumer of `SNF` — is never evaluated.
Measured on this deck, `model_pnf=1` against `model_pnf=0`:

| | max relative change over 200 entries |
|---|---|
| `RN` | 0.0 (bit-identical) |
| `RT` | 1.2e-3 |

So `SNF_leg(nr) = SNF_NSNR(nsp,nr)` — the conversion from trx's signed
per-species array to kyoshimi's single positive scalar, and the highest-risk
line in the port — has **zero coverage from this oracle**. It is covered only
by `test_model_pnf_publishes_into_the_solver_arrays`, which checks that it is
non-zero and non-negative, not that it is right.

An earlier revision of this file recorded a third gap here: a 62%
quasineutrality deficit in the reference's edge ion densities. That was an
artefact of the capture deck, not of `trx` -- see the next section -- and
does not exist. Both codes close quasineutrality exactly, at every `NR`.

## The two decks are not byte-identical, on purpose

`PROFN2` is declared `PROFN2(NSM)` in `trx` -- see `trx/trparm.f90`'s
`&TR ... PROFN1,PROFN2,PROFN3:NSM` -- and as a bare scalar in kyoshimi `tr`,
whose help text lists `PROFN1,PROFN2,PROFT1,PROFT2,PROFU1,PROFU2` outside the
`:NSM` group. One value therefore means *every species* on the kyoshimi side
and *species 1 only* on the trx side, where 2..4 stay at `pl/plinit.f90`'s
0.5. The reference deck now spells all `NSMAX` values out and carries a
comment saying why; the kyoshimi deck keeps the single scalar, which is what
its namelist accepts.

This is worth stating plainly because the two decks were byte-identical apart
from a graphics filename, so the divergence read as a code difference for as
long as it stood. It was the whole of what earlier revisions of this file
recorded as a structural, initialisation-side gap between the codes:

| | before | after |
|---|---|---|
| T=0, all 564 `metrics.json` fields | -- | 560 bit-identical, worst **5.7e-16** |
| after 5 steps, median | 4.0e-2 | **2.5e-8** |
| after 5 steps, worst | 1.64 at `RN[50]` | **6.7e-4** at `AJ[48]` |
| entries above 1e-3 | 128+ / 562 | **0** / 514 |
| reference edge quasineutrality | 62% deficit | closes exactly |

A trap worth recording: writing the four-element form into the *kyoshimi* deck
does not fail loudly. gfortran's namelist read assigns as it parses, so
`PROFN2=0.15D0,0.15D0,0.15D0,0.15D0` against a scalar sets it to 0.15 and
*then* reports `## PARM INPUT ERROR.` -- the value lands, the error is
cosmetic, and the run is indistinguishable from the scalar form. The reverse
(one value into trx) is silent in both directions.

## Why 10 keV, and why the 1 keV case was not enough

`tr_fus_dt` (1 keV) was originally chosen because a 10 keV variant appeared to
run away thermally. That runaway was an artefact of defect 1: with the alpha
source 1e6 too large, self-heating with no loss balance diverges. With the
corrections applied the hot case is stable, and it is better on both axes:

Both columns are measured **on the reference side** (corrected `trx`, the
binary that produced the committed baselines). "Fusion signal" is the relative
change in `WPT` between `model_pnf=1` and `model_pnf=0` -- same binary, same
deck but for that one line. Amplification is the largest relative change over
all entries of `metrics.json` for a relative 1e-12 perturbation of `PN(1)`,
the method the 1 keV `SOURCE.md` documents.

| | fusion signal, rel. `WPT` | 1e-12 perturbation amplification | resolution floor | margin under 1e-10 |
|---|---|---|---|---|
| 1 keV | 6.2e-09 | 1.00 (`RN[2][1]`) | 1.0e-16 | ~1.0e6x |
| 10 keV | **1.11e-03** | 2.32 (`AJ[48]`) | 2.3e-16 | ~4.3e5x |

**The hot case wins on signal alone -- 1.8e5x more of it -- and is somewhat
WORSE conditioned.** Both are far enough from the tolerance for that not to
matter: amplification x double-precision rounding is the floor a comparison
can resolve, so 2.32 x 1e-16 = 2.3e-16 still leaves ~4.3e5x of headroom.

The 1 keV `SOURCE.md` records an amplification of 76.5 for its own deck. That
figure was measured before the corrections, and it does not survive them: with
the 1e6 unit error in place the case was strongly nonlinear, and removing it
takes the amplification to 1.00. Do not carry 76.5 forward; it describes a
binary that no longer exists.

For orientation, the kyoshimi side gives rel. `WPT` = 1.1132e-3 on the same
deck against the reference's 1.1129e-3 -- they agree to 6.8e-4.

The 1 keV capture is retained and was re-taken with the corrected binary. Its
signal is genuine but small, which is itself the finding: most of what looked
like fusion in the original 1 keV capture was defect 1.

**`TAUE1`/`TAUE2` are ordinary comparison channels.** Earlier revisions of
this file, and the 1 keV `SOURCE.md`, said the opposite -- that with no
external heating the confinement time is a 0/0 diagnostic and must be
excluded. That was wrong twice over. `PINT` is not near zero here: it is the
ohmic 0.539 MW. What made `TAUE` look degenerate was defect 5, which put
`PNF_TOT` into `PINT` in W. Corrected, both codes track each other:
`TAUE1` 55.44 -> 44.59 s on the reference against 55.47 -> 44.60 s on
kyoshimi, the `model_pnf` differentials agreeing to 1.6e-3, and `TAUE2` to
3.5e-3.

## Constants

Unchanged from the 1 keV capture: `trx/trcomm.f90` shadows bpsd's CODATA-2018
`AEE`/`AME`/`AMP` with kyoshimi's CODATA-2006 values so every `USE TRCOMM`
consumer sees them. In particular `AMP` there is `1.672621637D-27`, the same
number as kyoshimi's `AMM`, so the slowing-down block agrees on both sides.

On the kyoshimi side the matching hazard is closed structurally: `trpnf_multi`
imports from `libnf` with an explicit `ONLY` list, because `libnf` does a
module-level `USE bpsd_constants` and a bare `USE` re-exports `AEE`/`AME`/
`AMP` (CODATA-2018) and `PI` into the consumer.  `PI` is bit-identical
between the two, so it can only ever be an ambiguity -- which is how this
was found.  `RKEV` is not in `bpsd_constants` at all, so naming it without
`USE trcomm` is a compile error, not a silent wrong value.  The three that do
diverge are `AEE`/`AME`/`AMP`; `AMP` by 1.714e-7, about 1700x the 1e-10 gate.

## Known open gap

The whole-solve comparison does **not** reach 1e-10, and the reason is now
narrow and locatable. Comparing a kyoshimi `model_pnf=1` run against this
baseline over every scalar and every profile field of `metrics.json` -- 564
entries, of which 50 are the integer `NR` index columns that can never differ
and are excluded below. Relative error is `|k-b|/|b|`; `compare_metrics.py`
normalises by `max(|a|,|b|)` instead, which can only make these smaller:

| | |
|---|---|
| median relative difference | 2.5e-8 |
| 90th percentile | 3.1e-4 |
| worst | **6.7e-4** at `AJ[48]` |
| entries above 1e-3 | 0 / 514 |
| entries above 1e-4 | 209 / 514 |

The four worst after `AJ[48]` are `TAUE2` (5.9e-4) and the core points of the
temperature profile, `RT[1..4][1]` at 3.2e-4.

**It is not in initialisation.** Run both codes at `NTMAX=0` and 560 of the
564 fields are bit-identical, the remaining four -- `AJ[29]`, `AJ[36]`,
`QP[50]`, `Q0` -- differing at 5.7e-16, i.e. last-bit. The divergence appears
in the first transport step and grows slowly: measured with fusion OFF on both
sides, `WPT` differs by 0.0 at `NTMAX=1`, 1.9e-4 at 2, and 2.9e-4 at 5. So it
is a transport-layer difference between the two forks, not a profile-
construction difference, and it has nothing to do with the fusion port.

(A caution on reading `NTMAX=1`: with `NTSTEP=5` the scalar diagnostics are
evaluated only at initialisation, so a `NTMAX=1` dump pairs `T=0` scalars with
post-step profile arrays. Use `NTMAX=0` for a true initial-state comparison.)

Against that floor, the fusion differentials -- `model_pnf=1` minus
`model_pnf=0`, taken separately in each code and then compared -- agree as
follows:

| channel | signal, rel. to `model_pnf=0` | differential agreement |
|---|---|---|
| `Q0` | 6.0e-6 | 8.0e-5 |
| `ALI` | -4.4e-6 | 1.1e-4 |
| `BETA0`, `BETAP0` | 2.8e-3 | 6.0e-4 |
| `WPT`, `BETAA`, `BETAN` | 1.11e-3 | 6.8e-4 |
| `TAUE1` | -0.196 | 1.6e-3 |
| `TAUE2` | 1.0e-3 | 3.5e-3 |

The differential does **not** cancel the fork's transport difference, and the
agreement column is the same order as the 2.9e-4 baseline: the two codes'
fusion perturbations land on slightly different states, so 6.8e-4 is the floor
this construction can resolve, not a measurement of the port's error. An
earlier one-off instrumentation of the first `tr_pnf` call gave `TAUF`
agreeing to 3.6e-6 and `SNF`/`PNF` to 6.3e-5; that instrumentation is not
committed and the figures are **not reproducible from this tree**. Treat them
as the tighter upper bound they are.

Closing the transport-step gap is a separate task. Until it lands the absolute
1e-10 gate is unreachable here, for reasons outside fusion.

## Reproduce

```bash
cd task-trx-ref/trx
env TR_REGRESS_DUMP=1 ./tr2 < in/trx_fus_dt_hot.in > /tmp/trx_hot.log
python3 ../../task-p1-libnf/test_run/scripts/extract_tr_metrics.py tr_regress.dat \
  > ../../task-p1-libnf/test_run/baselines/tr_fus_dt_hot/metrics.json
```

`run_tests.sh` cannot drive this on macOS — it needs `declare -A`, and the
system bash is 3.2. Drive the binary directly as above.
