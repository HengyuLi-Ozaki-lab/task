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

## The reference is patched, and this section is the list

`trx` as shipped cannot serve as a 1e-10 oracle for fusion. Four defects on its
fusion path were found, each verified against an authority outside the codebase
before being corrected, and each carries a `ref/trx-regress-capture ONLY`
comment at its site. Reported upstream alongside k-yoshimi/task#235.

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

**And the channel `SNF` feeds is the one the reference is worst at.** The trx
capture's ion densities do not close against its own electron density, while
kyoshimi's do exactly:

| NR | n_e (both, identical) | kyoshimi Σ Z_i n_i | trx Σ Z_i n_i |
|---|---|---|---|
| 1 | 9.999865e-02 | 9.999865e-02 | 9.999550e-02 |
| 25 | 9.636862e-02 | 9.636862e-02 | 8.845502e-02 |
| 50 | 6.001157e-02 | 6.001157e-02 | 2.269606e-02 |

A 62% quasineutrality deficit at the edge. Until that is understood, this
capture should not be used to validate anything a particle source touches.

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

| | fusion signal, rel. `WPT` | 1e-12 perturbation amplification | margin under 1e-10 |
|---|---|---|---|
| 1 keV | 4.0e-09 | 1.00 | ~1.0e6x |
| 10 keV | **1.0e-03** | 1.56 | ~6.4e5x |

**The hot case wins on signal alone -- 2.6e5x more of it -- and is very
slightly WORSE conditioned.** Both are far enough from the tolerance for that
not to matter: amplification x double-precision rounding is the floor a
comparison can resolve, so 1.56 x 1e-16 = 1.6e-16 still leaves ~6.4e5x of
headroom.

The 1 keV `SOURCE.md` records an amplification of 76.5 for its own deck. That
figure was measured before the corrections, and it does not survive them: with
the 1e6 unit error in place the case was strongly nonlinear, and removing it
takes the amplification to 1.00. Do not carry 76.5 forward; it describes a
binary that no longer exists.

For orientation, the kyoshimi side gives rel. `WPT` = 1.11e-3 on the same deck
against the reference's 1.04e-3 -- they agree to 7.3%.

The 1 keV capture is retained and was re-taken with the corrected binary. Its
signal is genuine but small, which is itself the finding: most of what looked
like fusion in the original 1 keV capture was defect 1.

**`TAUE1`/`TAUE2` are meaningless here** and should be excluded from any
comparison. With no external heating the energy confinement time is a 0/0
diagnostic; it was already flagged in the 1 keV `SOURCE.md`.

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

The whole-solve comparison does **not** reach 1e-10, for a reason outside
fusion, and the gap is larger than a scalar-only summary suggests. Comparing a
kyoshimi `model_pnf=1` run against this baseline.  The enumeration is every
scalar and every profile field of `metrics.json` with `TAUE1`/`TAUE2`
dropped, 562 entries, of which 50 are the integer `NR` index columns that
can never differ -- they are left in for reproducibility but they pad the
sample with guaranteed zeros, which is why the median below is 4.0e-2 and
not the 4.6e-2 of the 512 comparable entries.  Relative error is
`|k-b|/|b|`; `compare_metrics.py` normalises by `max(|a|,|b|)` instead, under
which the worst entry reads 0.62 rather than 1.64:

| | |
|---|---|
| median relative difference | 4.0e-2 |
| entries above 6.8e-2 | 160 / 562 |
| entries above 1e-1 | 128 / 562 |
| worst | 1.64 at `RN[50]` (He4) |

It is structural, not noise: it grows monotonically toward the edge and is
bit-identical between the 1 keV and 10 keV captures. With fusion OFF on both
sides the scalars differ by 4.6e-2..6.8e-2, and the difference is already
present at `T=0` before any time evolution (on the 1 keV deck, kyoshimi
`WP` 4.82 MJ / `Q0` 7.385 against trx 4.49 / 8.196), so it originates in
initial-profile construction. The quasineutrality violation above is part of
the same picture.

Against that, the fusion differentials agree to 3.8e-2..1.6e-1 — the same
order as the baseline gap, which is the most that can be said while the gap
stands. The tighter figure is per-call: instrumenting the first `tr_pnf` call
on both sides gave `TAUF` agreeing to 3.6e-6 and `SNF`/`PNF` to 6.3e-5. That
was a one-off measurement with temporary `WRITE`s in both trees; the
instrumentation is not committed and the number is **not reproducible from
this tree**. Treat it as an upper bound on the port's own error, not a
measurement of it — the two codes' input states already differ.

Closing the initialisation gap is a separate task. Until it lands, the
absolute 1e-10 gate is unreachable here for reasons that have nothing to do
with the fusion port.

## Reproduce

```bash
cd task-trx-ref/trx
env TR_REGRESS_DUMP=1 ./tr2 < in/trx_fus_dt_hot.in > /tmp/trx_hot.log
python3 ../../task-p1-libnf/test_run/scripts/extract_tr_metrics.py tr_regress.dat \
  > ../../task-p1-libnf/test_run/baselines/tr_fus_dt_hot/metrics.json
```

`run_tests.sh` cannot drive this on macOS — it needs `declare -A`, and the
system bash is 3.2. Drive the binary directly as above.
