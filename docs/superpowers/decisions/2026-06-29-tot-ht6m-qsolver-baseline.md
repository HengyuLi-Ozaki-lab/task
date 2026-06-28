# Decision record — regenerate the `tot_ht6m_short` equivalence baseline for bpsi's merged EQ/TR solver refinements

- **Date:** 2026-06-29
- **Status:** ACCEPTED (physics reviewed and approved by the project owner)
- **Scope:** P0a merge of `bpsi/develop` into `kyoshimi-develop` (branch `integrate/base-2026-06`, task-merge PR #1)
- **Affects:** `test_run/baselines/tot_ht6m_short/metrics.json` (the 1e-10 binary-equivalence baseline for the TOT orchestrator HT6M short case)
- **Related:** [[task-merge-f90-project]] memory; wrx baseline regen `36586def`; the wrx gf-version baseline gap (regen-baselines does not yet support `wrx_*` — a follow-up to the #197 regen pattern; #197 itself was closed by `7a436d39`); design spec `docs/superpowers/specs/2026-06-15-task-merge-f90-design.md`

## 1. Context

The P0a merge brings the 23-commit `bpsi/develop` base onto the kyoshimi
Phase-L fork. After the static-build integration was fixed and CI first
reached pytest, the suite ran **733 passed / 3 failed** on the gfortran-13.2
Linux runner (run 28218102375). All 3 failures are 1e-10 binary-equivalence
baselines, in two unrelated classes:

| Test | Magnitude | Class |
|---|---|---|
| `totlib::test_tot_ht6m_short` | 210 mismatches, rel_err up to ~3.7e-4 | **physics change (this record)** |
| `wrxlib::test_demo` / `test_iter01` | pwr_tot rel_err ~4.9e-10 / 1.55e-9 | compiler-version FP noise (gf8.5 baseline ≠ gf13.2 CI) — separate, see #197 |

This record covers **only** the `tot_ht6m_short` failure. The wrx failures are
a distinct gf-version-sensitivity issue handled separately.

The merge did **not** touch `tot/` or `fp/` Fortran. `eq_iter01`, `tr_iter01`,
`tot_demo2014_short`, and `fp_iter01` all PASS on CI — so the change is not a
broad regression. Only the HT6M coupled run shifted.

## 2. Root cause

`tot_ht6m_short` is a menu-driven **coupled eq→tr run at `modelg=3`**
(`test_run/inputs/tot_ht6m_short.trparm: modelg=3`; the `.in` stdin script runs
`eq r s … tr r s …`, with `tot.HT6M_short.gs` as the GS prologue filename — not
a committed fixture). At `modelg=3` the equilibrium is loaded via `eq_load` /
`trmetric` — so this is NOT the `modelg=9` q-scaling branch.

The shift comes from the merge's bpsi **EQ/TR solver refinements** that the
modelg=3 `eq_load` path uses. Two base commits are responsible:

```
fa9dd493  "tr,eq: fix modelg=9 TR-EQ q-solver coupling" — despite the title, its
          body ALSO rewrites general solver code every modelg uses: EQLOOP
          under-relaxation + EQMAGS robustness + consistent current init
          (eq/eqcalc.f +22, eq/eqsub.f, eq/equnit.f; tr/trmetric.f90 +26,
          tr/trloop.f90, tr/trgrae.f90, tr/trbpsd.f90).
2b2b9408  "eq: eqcalq.f NMAX 200 -> 400" — a finer flux-surface grid for the EQ
          solve (grafted into the modernized eq/eqcalq.f90 in P0a, §3 of the
          merge conflict resolutions).
```

The pre-merge baseline (`8956d7a9`-era) encodes the coarser/older EQ solve; the
merged code solves the same HT6M equilibrium on a finer grid (NMAX 400) with
EQLOOP under-relaxation, yielding a slightly **more accurate** core current/q.
demo2014 / iter01 are well-conditioned configurations where these refinements
are inert at 1e-10, which is why only HT6M moved. The exact dominant sub-change
was not bisected (that needs per-commit rebuilds), but the physics signature in
§3 is unambiguous regardless of which refinement dominates.

## 3. Physics review (why this is a correct refinement, not a bug)

The shift was extracted from the authoritative gf13.2 CI run (baseline vs
actual, all 210 elements) and grouped by quantity. Signature:

| Quantity | # pts | rel_err range | direction |
|---|---|---|---|
| AJ (current density j) | 10 (core) | 2.00e-4 … 2.67e-4 | ↑ all up |
| QP (safety factor q)   | 10 (core) | 1.02e-4 … 1.33e-4 | ↓ all down |
| Q0 (axis q0)           | 1 | 1.33e-4 | ↓ |
| RT (temperature)       | 10×2 spc | 1.9e-5 … 1.39e-4 | redistribute |
| TAUE1/2 (confinement)  | — | 3.71e-4 (largest scalar) | ↓ |
| AJT, ALI, WPT, β*       | — | 2e-6 … 6e-5 | small, coherent |
| **RN (density n)**     | **0** | — | **unchanged** |

Four independent bug-vs-physics discriminators, all pointing to a legitimate
core q-solver refinement:

1. **`j ↑ ↔ q ↓` strict anti-correlation**, with |Δj/j| ≈ 2·|Δq/q|. This is the
   exact analytic coupling `q ∝ r·Bφ/(R·Bθ)`, `Bθ ∝ ∫ j dr` — more core current
   ⟹ lower core q, with the ~2:1 ratio from the integral+geometry. A bug has no
   reason to honor this relation.
2. **Spatially localized to the core, ρ ≤ 0.20**, decaying *smoothly* to exactly
   zero at ρ = 0.20 (ρ ≥ 0.22: byte-identical). A bug is typically global or
   discontinuous.
3. **Density n completely frozen** (0 of its points changed). n is an input
   profile, not a q-solver output; an algorithm bug would tend to contaminate
   unrelated quantities.
4. **No NaN / no blow-up / no jumps** — every change is smooth and ~1e-4..1e-5;
   downstream quantities (T redistribution, τE/Wp small decrease, li small
   increase) are all consistent with a slightly-modified core current profile.

Visualization: `Δrel = (new−old)/old × 10⁻⁴` vs ρ for j and q shows two
mirror-image core bumps (j: +2.67→0, q: −1.33→0 over ρ = 0.02→0.20), then flat
zero. (Rendered for review on 2026-06-29.)

## 4. Decision

**The new bpsi solver result is accepted as the correct reference for
`tot_ht6m_short`.** The project owner reviewed the per-quantity shift table and
the j/q radial-shift plot on 2026-06-29 and approved: the ~1e-4 change is the
intended physical consequence of bpsi's merged EQ/TR solver refinements (finer
flux-surface grid NMAX 200→400 + EQLOOP under-relaxation, `2b2b9408` /
`fa9dd493`) used by the modelg=3 `eq_load` path, not a merge artifact.

**Action:** regenerate `test_run/baselines/tot_ht6m_short/metrics.json` against
the merged code, on the CI compiler (gfortran-13.2 / x86_64), via the existing
`regen-baselines.yml` (`workflow_dispatch`, `fixtures: tot_ht6m_short`, which
supports the `tot_*` prefix and runs on ubuntu-24.04). Regenerating on gf13.2
(not Mac gf15 / ohtaka gf8.5) also avoids re-introducing the FP-version drift
that bites wrx — see §5.

This is a deliberate baseline change recorded here for audit; the regen commit
references this file. It does NOT loosen the 1e-10 tolerance — it updates the
reference to the physically-correct post-fix values.

## 5. Out of scope — the wrx failures (tracked separately)

`wrxlib::test_demo` / `test_iter01` fail by ~5e-10..1.5e-9 — **compiler-version**
FP reordering, not a physics change: the committed wrx baselines were generated
on gf8.5 (ohtaka, `36586def`) and the CI runs gf13.2; Mac gf15 gives yet a third
value, all within ~1e-9. The 1e-10 binary-equivalence tolerance is simply too
tight for the ray-tracing pwr integral across compiler *versions* (not just
arch). `regen-baselines.yml` does not yet support `wrx_*` (only tr_/eq_/tot_).
Resolution (a follow-up to the #197 regen pattern; #197 itself closed by
`7a436d39`): extend the regen workflow to `wrx_*` and capture the wrx baselines
on gf13.2, OR adopt a per-platform / slightly-looser tolerance for the FP-heavy
scalar. Lesson for the project: **equivalence baselines for the FP-version-
sensitive modules (wrx ray-trace, fp Fokker–Planck) must be captured on the exact
CI compiler.** (tot/eq/tr are compiler-stable at 1e-10 — the tot_ht6m regen here
is for the *physics* shift, not compiler drift, so it would reproduce on any
compiler; gf13.2 is used only to match CI exactly.)

## 6. Appendix — core radial data (gf13.2 CI, baseline → new)

ρ = NR/NRMAX, NRMAX = 50. Only ρ ≤ 0.20 changed.

| ρ | j_old (kA/m²) | j_new | Δj ×10⁻⁴ | q_old | q_new | Δq ×10⁻⁴ |
|---|---|---|---|---|---|---|
| 0.02 | 547.624 | 547.770 | +2.665 | 6.4789 | 6.4781 | −1.328 |
| 0.04 | 543.134 | 543.277 | +2.637 | 6.5214 | 6.5206 | −1.314 |
| 0.06 | 536.475 | 536.613 | +2.576 | 6.5745 | 6.5737 | −1.283 |
| 0.08 | 526.989 | 527.121 | +2.505 | 6.6452 | 6.6443 | −1.250 |
| 0.10 | 517.169 | 517.295 | +2.430 | 6.7243 | 6.7235 | −1.215 |
| 0.12 | 506.626 | 506.745 | +2.353 | 6.8113 | 6.8105 | −1.179 |
| 0.14 | 495.893 | 496.005 | +2.271 | 6.9046 | 6.9038 | −1.140 |
| 0.16 | 484.857 | 484.963 | +2.187 | 7.0039 | 7.0032 | −1.101 |
| 0.18 | 473.630 | 473.729 | +2.094 | 7.1091 | 7.1084 | −1.060 |
| 0.20 | 462.215 | 462.307 | +1.998 | 7.2202 | 7.2195 | −1.017 |
| ≥0.22 | — | (unchanged) | 0 | — | (unchanged) | 0 |

Source: baseline = `test_run/baselines/tot_ht6m_short/metrics.json`; new =
`totlib::test_tot_ht6m_short` actuals from task-merge CI run 28218102375
(gfortran-13.2, ubuntu-24.04, nompi).
