# `tr_fus_dt_hot` — D-T fusion at 10 keV, reference capture

`metrics.json` is a capture of the **bpsi `trx`** transport code, to be matched
by kyoshimi `tr` with `model_pnf=1`. It is the primary P1 Task 7 oracle; the
1 keV `tr_fus_dt` case is retained but is a much weaker test (see "Why 10 keV").

| Item | Value |
|---|---|
| Source tree | `task-trx-ref`, branch `ref/trx-regress-capture` |
| Input | `trx/in/trx_fus_dt_hot.in` (physically equivalent to `test_run/inputs/tr_fus_dt_hot.in`, but not byte-identical -- see Deck caveat) |
| Dumper | `trx/trregress.f90`, env-guarded by `TR_REGRESS_DUMP=1` |
| Extractor | `test_run/scripts/extract_tr_metrics.py` |
| Case | `modelg=2` analytic geometry, species e/D/T/He4, `NSMAX=4`, `NRMAX=50`, `NTMAX=5`, `PT=10 keV`, `PTS=1 keV` (edge is one tenth of core), `RIPS=2 -> RIPE=3` |
| Determinism | two consecutive runs give a bit-identical `tr_regress.dat` |
| Deck caveat | `PROFN2` is `PROFN2(NSM)` in trx and a bare scalar in kyoshimi, so the two decks are *not* byte-comparable on that line -- see "The two decks are not byte-identical, on purpose" |

## The reference is patched, and this section is the list

`trx` as shipped cannot serve as a 1e-10 oracle for fusion. Five defects were
found, each verified before being corrected -- defect 1 against an authority
outside the codebase (Bosch-Hale), defects 2-5 against internal authorities
that are unambiguous where they are cited -- and each carries a
`ref/trx-regress-capture ONLY` comment at its site. 1-4 are on the fusion path and are reported upstream as k-yoshimi/task#235
(defects 2-4) and #236 (defect 1); 5 is a diagnostic-only unit slip spanning
four subsystems
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
   power grew linearly in the number of `tr_pnf` calls — measured 1.0000x,
   2.0019x, 3.0037x on successive calls of this deck, reaching a factor of
   order the call count. The corrected build makes 46 calls over these five
   steps, counted with a `SAVE` counter at the routine entry; the defective
   build makes more, because the inflated alpha source costs the implicit
   solve extra iterations.

5. **W not converted to MW in ten power volume integrals.** Every power
   integral in the *legacy* channels of `trx/trrslt.f90`'s `TRGLOB`
   divides by `1.D6` -- `POHT`, `PEXT`, `PRBT`/`PRCT`/`PRLT`/`PRSUMT`/
   `PCXT`/`PIET`. None of the newer per-channel aggregation blocks did: RF
   (`PIC`/`PLH`/`PEC`), NBI (`PNB`/`PNBIN`/`PNBCL`), fusion (`PNF`/`PNFIN`/
   `PNFCL`) and fusion-neutron (`PNFNN`). So `PNF_TOT` entered
   `PINT = POHT+PNB_TOT+PRF_TOT+PNF_TOT+PEXST` in W against five terms in
   MW, inflating `PINT` by 1e6 the moment `model_pnf=1`: `TAUE1` collapsed
   55.4 s -> 2.26e-4 s, `TAUE2` 1.081 s -> 2.26e-4 s, and `QF` was 1e6 high.
   The authority is internal and unambiguous, in three independent places.
   `trx/trprf.f90:18-20` is a **second writer** of `PIC_TOT`/`PLH_TOT`/
   `PEC_TOT`, setting them to `SUM(PICIN)` etc. -- the namelist input powers,
   in MW -- so before the fix `trrslt.f90:194-196` overwrote MW values with W
   and the same variable meant different things depending on which subroutine
   ran last. `trx/trhelp.f90:243` documents `PNB_TOT: NBI TOTAL INPUT POWER
   (MW)`. And the eight legacy siblings in `TRGLOB` itself all divide,
   as do the `[MW/...]` axis labels in `trx/trgrar.f90`. Kyoshimi `tr`'s own
   `trrslt_globals.f90:192-220` divides on every counterpart; trx is the
   outlier fork here, which is also why `TAUE1` works as an oracle channel at
   all.
   The solver never sees it: it consumes the W/m^3 profile `PNF_NSNNFNR`
   directly, which is why `WPT` carried a correct fusion signal while every
   `PINT`-derived diagnostic did not. The particle-source integrals beside
   these (`SNB_`, `SNF_`, `SNFNN_`, `SIE`, `SPEL`, `SPSC`) are in 1/s and
   correctly take no conversion.

   **Only one of the ten is exercised by this deck**, and six of them sit on
   quantities that are separately broken. `PNF_NSNNF` is the one this
   capture measures. Of the rest:

   - `PNFIN_NSNNFNR` and `PNBIN_NSNNBNR` have **no writer anywhere in
     `trx`** -- declaration, `ALLOCATE` without zero-init, `DEALLOCATE`, and
     reads in `trrslt.f90`, nothing else. So `PNFIN_TOT` and `PNBIN_TOT`
     integrate uninitialised heap. The two are not symmetric:
     `trx/trpnb.f90:496` *does* write the per-channel `PNBIN_NNBNR` with
     physics, which `trrslt.f90:226` then overwrites from the never-written
     3-D array -- so NBI loses good data. Fusion has no writer inside `trx`
     at all (`trx/trpnf.f90` contains no `PNFIN` token); the one in
     `trm/trpnf.f90:282` is a different fork directory and is not in this
     build.
   - `PIC_NSNICNR`/`PLH_NSNLHNR`/`PEC_NSNECNR` are assigned in exactly one
     place, `trx/trprf.f90:23-25`, which only *zeroes* them and only when
     total RF power is <= 0 -- so with RF on they are read uninitialised too.
   - `PNFCL_NSNNFNR` is zeroed at `trx/trpnf.f90:66` and never assigned,
     which is gap 1 above.
   - `PNFNN_NNF` feeds `PNFNN_TOT`, which has no reader in `trx` outside its
     declaration; its `NNF>1` entries reach `GVT` only at `NNFMAX>=2`.

   The unit correction is still right -- a W/m^3 integral belongs in MW
   however the array got its contents -- but on the five that read
   uninitialised memory it makes the printed number *plausible* rather than
   obviously 1e6-scaled, which is worth knowing. (The remaining one,
   `PNFCL_NSNNFNR`, is deterministically zero, so its printed number is 0 --
   neither plausible nor obviously wrong.) All of this is upstream's, not
   introduced here, and is reported with the correction.

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
never entered into the reduced solve — the run's `NEQ` table gives `NST=0` on
all four `NSV=1` rows — so `SNF`'s contribution is assembled and then dropped.
(An earlier revision said `SSIN` is never evaluated. It is: `tr/trcalc.f90:219`
writes `SSIN(NR,4)=SNF(NR)+…` under a guard on `MDLEQ0`, which is 0. And `SNF`
has other readers, `tr/trrslt_globals.f90`'s `SNFT` among them. The conclusion
below is unchanged; only the mechanism was wrong.)
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

That is measured, not inferred. Injecting at each of `tr_pnf`'s three
published arrays in turn and recomputing all 209 differentials of
`test_fusion_differential_matches_the_trx_reference`:

| injection | worst scalar | worst `RT` | over tolerance |
|---|---|---|---|
| `PNF_leg` x 1.10 | `TAUE2` 8.61x tol | `RT[27][4]` 5.06x tol | 209 / 209 |
| `TAUF_leg` x 1.10 | `TAUE2` 1.702e-1 (14.2x) | `RT[28][3]` 1.074 (53.7x) | 9 / 209 |
| `SNF_leg` x 1.10 | `TAUE2` 3.530e-3 | `RT[28][2]` 5.112e-3 | **0 / 209** |
| `SNF_leg` = 0 | `TAUE2` 3.530e-3 | `RT[28][2]` 5.112e-3 | **0 / 209** |

Both `SNF` rows are **bit-identical to the zero-error run in all 209
entries**. Deleting the alpha particle source outright is invisible, at any
magnitude, because `MDLEQN=0` keeps the density equations out of the reduced
solve. (Two independent gates, not one: `SNF`'s other consumer is `TRPELB`,
which `TRPELT` skips on `PELTOT<=0` and again on `MDLPEL==0`.)

An injection at `sigmav_nf` does **not** reach all three. `TAUF_NNFNR` is
built from `RN`, `RT`, `eng_nnf` and `COULOG` with no dependence on the
reaction rate, and `SNF` is inert — measured, `sigmav_nf` x 1.10 and
`PNF_leg` x 1.10 give differentials bit-identical in all 209 entries. So
every gain and shape figure in the section above was measured at `PNF`
alone. `TAUF` is not `PNF`'s equal on shape: the same radial form applied
to `TAUF_leg` gives 0.81x tolerance at `eps`=0.001 (**0 / 209, passes**),
1.39x at 0.002, and 6.02x at 0.01 — where the only entries over tolerance
are the four `RT[28][*]` and the worst scalar, 0.19x, is below its own
floor. So `TAUF` shape needs ~0.2%, and the `RT[28]`-exclusion fallback
quoted above is `PNF`-only: without those four entries `TAUF` shape has no
detector at any magnitude tested.

An earlier revision of this file recorded a third gap here: a 62%
quasineutrality deficit in the reference's edge ion densities. That was an
artefact of the capture deck, not of `trx` -- see the next section. The
deficit was real as measured (62.18% at `NR=50`) but it was the deck's, and
with the deck corrected there is no gap to record: both codes close
quasineutrality to round-off, identically -- worst 1.4e-15 relative at
`NR=46`, exactly zero at 7 of the 50 radii.

## The two decks are not byte-identical, on purpose

`PROFN2` is declared `PROFN2(NSM)` in `trx` -- see `trx/trparm.f90`'s
`&TR ... PROFN1,PROFN2,PROFN3:NSM` -- and as a bare scalar in kyoshimi `tr`,
whose help text lists `PROFN1,PROFN2,PROFT1,PROFT2,PROFU1,PROFU2` outside the
`:NSM` group. One value therefore means *every species* on the kyoshimi side
and *species 1 only* on the trx side, where 2..4 stay at `trx/trinit.f90`'s
0.5. (Both `pl/plinit.f90` and `trx/trinit.f90` write 0.5, but `trmain.f90`
calls `pl_init` before `tr_init`, so trinit is the operative writer -- visible
in `PROFN3`, where the two disagree and the run reports trinit's 0.0.) The reference deck now spells all `NSMAX` values out and carries a
comment saying why; the kyoshimi deck keeps the single scalar, which is what
its namelist accepts.

This is worth stating plainly because the two decks carried the same value on
every parameter line -- 19 keys, zero mismatches -- so the divergence read as a
code difference for as long as it stood. (They were never byte-identical: the
kyoshimi deck has a comment header and three-space indentation, and spells
`modelg` in lower case. Comparing parameter *values* is what could not see
this, because a scalar-vs-array difference does not show up there.) It was the whole of what earlier revisions of this file
recorded as a structural, initialisation-side gap between the codes:

Both columns are the same 514 entries -- every scalar and profile field of
`metrics.json` except the 50 integer `NR` index columns, which can never
differ -- against the same unchanged kyoshimi `model_pnf=1` run. Earlier
revisions quoted a 562-entry figure that included the index columns and
dropped `TAUE`; that convention is not used anywhere in this file any more.

| | before | after |
|---|---|---|
| T=0 | -- | 510 / 514 bit-identical, worst **5.7e-16** |
| after 5 steps, median | 4.7e-2 | **4.8e-8** |
| after 5 steps, 90th pct | 3.0e-1 | **3.1e-4** |
| after 5 steps, worst | 1.8e5 (`TAUE1`) | **6.7e-4** (`AJ[48]`) |
| entries above 1e-2 | 400 / 514 | **0** / 514 |
| entries above 1e-3 | 446 / 514 | **0** / 514 |
| reference edge quasineutrality | 62% deficit | closes to 1.4e-15 |

The 1.8e5 worst in the "before" column is `TAUE1` under defect 5; the deck
alone accounts for the median and the profile entries.

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

For orientation, the kyoshimi side gives rel. `WPT` = 1.113271e-3 on the same
deck against the reference's 1.112831e-3 -- they agree to 4.0e-4. That is a
different quantity from the 6.8e-4 differential agreement reported under
"Known open gap": each side is normalised by its own `model_pnf=0` `WPT`, and
those two differ by 2.9e-4.

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
| median relative difference | 4.8e-8 |
| 90th percentile | 3.1e-4 |
| worst | **6.7e-4** at `AJ[48]` |
| entries above 1e-3 | 0 / 514 |
| entries above 1e-4 | 209 / 514 |

The five worst after `AJ[48]` are `TAUE2` (5.9e-4) and the core points of the
temperature profile, `RT[1..4][1]` at 3.2e-4.

**It is not in initialisation.** Run both codes at `NTMAX=0` and 510 of the
514 are bit-identical, the remaining four -- `AJ[29]`, `AJ[36]`, `QP[50]`,
`Q0` -- differing at worst 5.7e-16, i.e. last-bit. (All four are non-index
fields, so this is 560 of 564 on the index-inclusive count.) The divergence
appears once the solve starts and grows slowly: measured with fusion OFF on
both sides, `WPT` differs by 1.9e-4 after two steps and 2.9e-4 after five. So
it is a transport-layer difference between the two forks, not a profile-
construction difference, and it has nothing to do with the fusion port.

(`NTMAX=1` is missing from that sequence deliberately. With `NTSTEP=5` the
scalar diagnostics are evaluated only at initialisation, so a `NTMAX=1` dump
pairs `T=0` scalars with post-step profile arrays -- its `WPT` reads 0.0
because it is still the `T=0` value, not because a step changed nothing. Use
`NTMAX=0` for a true initial-state comparison and `NTMAX>=2` for the growth.)

Against that floor, the fusion differentials -- `model_pnf=1` minus
`model_pnf=0`, taken separately in each code and then compared -- agree as
follows:

| scalar channel | signal, rel. to `model_pnf=0` | differential agreement |
|---|---|---|
| `Q0` | 6.0e-6 | 8.0e-5 |
| `ALI` | -4.4e-6 | 1.1e-4 |
| `BETA0`, `BETAP0` | 2.8e-3 | 6.0e-4 |
| `WPT`, `BETAA`, `BETAN` | 1.11e-3 | 6.8e-4 |
| `TAUE1` | -0.196 | 1.6e-3 |
| `TAUE2` | 1.0e-3 | 3.5e-3 |

The table is the nine scalars. `test_fusion_differential_matches_the_trx_reference`
also compares `RT` per (NR, species), 200 more entries whose worst is
**5.1e-3** at `RT[NR=28][s=2]`, noisier than any scalar. `RT[28]` sits on
the node of the RT fusion differential (`RT[27][*]` carry the opposite
sign), so its denominator is near zero -- and that single property cuts
both ways depending on the defect, which is why the two families are held
to different tolerances (scalars 1.2e-2, `RT` 2.0e-2) and why neither may
be dropped:

| injected defect | worst scalar | worst `RT` |
|---|---|---|
| gain, `eps`=1.5% (`sigmav_nf` x (1+eps)) | `TAUE2` 1.85e-2 | -- |
| shape, `eps`=0.1% (radial, volume-neutral) | `TAUE2` 3.17e-3, **below its own 3.53e-3 floor** | `RT[28][3]` 9.98e-2 = **5.0x** tolerance |
| shape, `eps`=1% | `Q0` 4.76e-3, still invisible | `RT[28][3]` 9.56e-1 = **47.8x** |

For a gain error the node moves with the error, `RT[28][2]`'s differential
scales by only ~0.61*`eps`, and `TAUE2` binds from `eps` ~ 0.5% upward. For
a shape error the near-zero denominator amplifies instead, and `RT[28]` is
the most sensitive entry in the test by two orders of magnitude while every
scalar is blind -- a volume integral is exactly what a shape error
preserves. Detection is ~0.85% on gain and ~0.1% on shape **at `PNF`**;
see "What this oracle does NOT exercise" for what that does and does not
say about `TAUF` and `SNF`. One tolerance sized off `RT` would have given
1.65% on gain and nothing better on shape.

The ~0.1% belongs to `RT[28]`'s node position on this deck at this step
count, not to the channel. Excluding the four `RT[28][*]` entries, shape
detection is ~0.9%: at shape `eps`=0.001 the worst remaining entry is
`TAUE2` at 0.26x its tolerance, at `eps`=0.01 it is `RT[27][1]` at 1.11x.
Those four also carry the weakest reference signals of all 209 — 13.0x,
14.6x, 15.1x and 27.2x `FUSION_SIGNAL_FLOOR`. If the node drifts toward
zero the floor assert fires and the test goes red; if it drifts away, shape
detection degrades an order of magnitude with nothing failing. Re-measure
the shape row if the deck, the grid or `NTMAX` changes.

The differential does **not** cancel the fork's transport difference, and the
agreement column is the same order as the 2.9e-4 baseline: the two codes'
fusion perturbations land on slightly different states. So **5.1e-3** over
the 209 entries actually compared -- 3.5e-3 if you restrict to the scalars,
6.8e-4 for `WPT` alone -- is the floor this construction can resolve, not a
measurement of the port's error. An
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
system bash is 3.2. Drive the binary directly as above. Every comparison
figure in this file was obtained that way, not through `run_tests.sh`:
`tr/tr2` and `trx/tr2` on their respective decks under `TR_REGRESS_DUMP=1`,
extracted with `extract_tr_metrics.py`, diffed field by field. Labels here
are 1-based `FIELD[NR][species]`; `compare_metrics.py` prints the same
entries 0-based as `profile[NR-1].FIELD[species-1]`.
