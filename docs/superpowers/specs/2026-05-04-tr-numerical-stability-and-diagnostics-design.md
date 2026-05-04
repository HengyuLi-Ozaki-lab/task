# TR Manual — Numerical stability & diagnostics (Appendix) — Design

**Status:** Draft
**Date:** 2026-05-04
**Project memory:** `project_tr_proper_manual.md` ("Numerical stability notes" + "Diagnostics & observability" — 1-session expansion target, item E in the deepening menu)
**Predecessors:** G item shipped earlier today (commit `a8b83311` — `limitations-and-references.md` Appendix); 7-module `applications.md` ja → en series; Sphinx bootstrap (#173).

---

## §1. Overview

Add a single bilingual page to the TR Sphinx chapter — the
"Numerical stability and diagnostics" appendix — covering 7 topics
across two sections:

- **Stability** (4 topics): time-stepping scheme, time-step selection,
  inner-iteration convergence, `tr_run` ierr=3 diagnosis
- **Diagnostics** (3 topics): reading tr2 console output,
  `validate()` output mapping, `TrState` diagnostic patterns

This is the "E" item from the deepening menu and forms an
operational pair with G (Known limitations & references): G
documents what TR cannot do; E documents how to keep TR healthy.

## §2. File structure

**New files (bilingual pair):**

- `docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md`
- `docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md`

**Edited files:**

- `docs/sphinx/modules/tr/en/index.md` — append `numerical-stability-and-diagnostics` to the Appendix toctree (after `limitations-and-references`)
- `docs/sphinx/modules/tr/ja/index.md` — same

No new MyST anchor labels are needed — the new page does not
require future cross-references from elsewhere; outgoing links
target existing pages.

## §3. Page structure

### Header
- Title (en): "Numerical stability and diagnostics"
- Title (ja): "数値安定性と診断"
- Brief 1-paragraph admonition: this page covers operational
  guidance for keeping TR runs healthy (stability) and reading
  signals when something goes wrong (diagnostics).

### §3.1 Section "Numerical stability"

Four subsections.

**1. Time-stepping scheme**

One paragraph stating TR uses an implicit scheme, citing
`tr/trexec.f90:494-498`. The advancement coefficient is `FADV`
(NOT `THETA` — that name is reserved elsewhere): `FADV = 0.5`
is Crank-Nicolson, `FADV = 1.0` is fully implicit. The default
in `tr/trinit.f90` is `FADV = 1.D0` — TR runs fully implicit
out of the box. Concrete consequence: a strict CFL condition
does NOT apply. Time-step selection is governed by truncation
error and inner-iteration convergence, not by an advection-style
stability bound.

**2. Time-step selection guidance**

One paragraph + small reference table. Practical rules:

- Smaller `DT` → smaller truncation error per step but more
  steps for the same total time.
- The default `DT = 0.01 s` (`tr_param_registry.f90`) suits
  equilibrium-scale runs; sub-millisecond `DT` is rarely
  required for transport-time-scale studies.
- For divergent / unstable cases, halve `DT` and retry — the
  recipe is implemented as `StableTrRunner` in
  {doc}`applications`.

Example (fixture-grounded, no fabricated typical values):

| Fixture | `DT` | `NTMAX` | Total time |
|---|---|---|---|
| `tot_demo2014_short` (Layer 1 baseline) | 0.01 s | 100 | 1.0 s |
| `tot_ht6m_short` (Layer 1 baseline) | 0.0001 s | 1000 | 0.1 s |

Both rows verified at design time against the fixture files
(`python/totlib/tests/fixtures/tot_demo2014_params.py` and
`python/totlib/tests/fixtures/tot_ht6m_params.py`); the
defaults flow through `tr/trinit.f90:374-376`. The ht6m fixture
runs 100× more steps at 100× smaller `DT` because its physical
time scale (sub-second) and resolution requirements differ —
demonstrating the wide range of `(DT, NTMAX)` pairs that
"equilibrium-scale" can mean in practice.

**3. Inner-iteration convergence (`EPSLTR`, `LMAXTR`)**

One paragraph + parameter recap. Behaviour: each time step runs
an inner iteration that converges toward `EPSLTR`. If the
iteration does not converge within `LMAXTR` steps, the run
**continues** with whatever residual is reached (rather than
aborting). The `--Inner ...` lines in tr2 console output flag
non-convergent steps. Defaults (`EPSLTR=0.001`, `LMAXTR=10`)
are conservative. For aggressive studies where `LMAXTR` is
saturated, raise `LMAXTR` first; only loosen `EPSLTR` if
profile-level diagnostics confirm the residual is local
(e.g. confined to one species or one radial cell).

**4. `tr_run` `ierr=3` (`CALC_FAILED`) diagnosis**

Two paragraphs:

- *What `ierr=3` means at the API boundary:* `tr_api_run`
  (`tr/tr_api.f90:227-245`) returns `TR_ERR_CALC_FAILED` for
  **any** non-zero result code from the underlying
  `tr_prep` / `tr_loop` routines. The wrapper deliberately
  collapses the full set of downstream failure classes into a
  single ABI code; `ierr=3` is therefore an umbrella signal that
  "something downstream did not finish cleanly" rather than a
  diagnosis of which subsystem failed. Narrowing it down is the
  user's job, via the recipe below.
- *Diagnostic recipe:*
  1. Run `validate()` first; if any blocking diagnostic
     (`FILE_MISSING`, `MISSING_REQUIRED`) is present, fix it.
     This is the cheapest way to rule out classes of failure
     before the run.
  2. Halve `DT` and retry (use {doc}`applications`
     `StableTrRunner`). If the failure was a numerical
     stiffness / inner-iteration symptom, this often clears it.
  3. Inspect tr2 console output for `Inner not converged` lines
     and diverging energies (see §3.2.5).
  4. Cross-check {doc}`parameters` and {doc}`parameter-setting`
     for parameter ranges and inter-parameter constraints that
     `validate()` may not catch.

### §3.2 Section "Diagnostics & observability"

Three subsections.

**5. Reading tr2 console output**

Pointer-style 4–6 lines, NOT a verbatim format dump. The
text references `tr/trrslt_print.f90:57,89,266` for callers
who need the exact format strings. Each per-step line carries
the time-evolution scalars described in {doc}`state` —
specifically `T` (current time [s]), `WPT` (stored energy [MJ]),
`TAUE1`/`TAUE2` (energy confinement times [s]), `Q0` (axis
safety factor), and `AJT` (total current [MA]). Episode summary
lines additionally print device-shape parameters and integrated
beam/RF powers. The exact layout depends on the print mode
(`MDLPRT`); the canonical format is the 5-block layout in
`trrslt_print.f90`.

**6. `validate()` output mapping (`TrDiagCode`)**

A subsection per `TrDiagCode` value, taken verbatim from the
enum in `tr/tr_api.h` and the tr-side wrapper:

- **`OUT_OF_RANGE`** — a parameter value sits outside the
  registry's allowed range (e.g. `NSMAX > 8`). One-line typical
  cause + corrective action.
- **`INCONSISTENT_PAIR`** — two related parameters disagree
  (e.g. `EXTERNAL_DRIVEN_I != 0` with `EXTERNAL_DRIVEN_RW <= 0`).
  Cross-link to {doc}`parameters` for affected pairs.
- **`OUT_OF_RANGE_AFTER_DEP`** — a parameter sits inside its
  registry range but conflicts with a runtime-deduced bound
  (e.g. `NRMAX` after equilibrium load).
- **`FILE_MISSING`** — required file path is empty / missing
  (e.g. `MODELG ∈ {3,5,7,8}` + empty `KNAMEQ`).
- **`MISSING_REQUIRED`** — a required parameter is unset.
  Distinct from `OUT_OF_RANGE` because the absence is the
  problem, not the value.

The page must NOT fabricate which validate codes fire for which
parameters beyond what is verifiable in the registry; it can
state typical examples but should anchor each example with a
concrete parameter name.

**7. `TrState` diagnostic patterns**

3–4 short subsections, each pointing at a `TrState` field
described in {doc}`state` and stating *what to look for*:

- *Stored-energy drift:* monitor `WPT` over time. A run reaching
  a quasi-steady state should plateau; an unbounded rise
  suggests source/sink imbalance.
- *q-profile peaking:* `Q0` (axis safety factor) below 1 is a
  rule-of-thumb threshold for sawtooth instability in tokamaks.
  TR does not model sawteeth, so persistent `Q0 < 1` may
  indicate that the resulting profile is non-physical at the
  axis — but the magnitude of the drift, and whether it
  matters for the diagnostic the user actually cares about,
  depend on the scenario.
- *Current relaxation:* the time over which `AJT` settles after
  a change in `EXTERNAL_DRIVEN_I` is a rule-of-thumb estimate of
  the resistive current relaxation time. Order-of-seconds for
  ITER-class devices, sub-second for smaller machines.
- *Energy confinement:* `TAUE1`/`TAUE2` are computed from
  `WPT` and the integrated input power; their ratio with
  empirical scaling laws (e.g. ITER89-P) is a standard sanity
  check.

The "rule-of-thumb" framing is required wherever the claim is
operational tokamak physics rather than a TR API contract — to
keep the no-fabrication discipline consistent with G.

## §4. Bilingual content

Same convention as G. Headings translated faithfully; table
column labels stay English; identifiers (`tr_state_t`, `WPT`,
`MDLPRT`, `LMAXTR`) inline-code in both languages.

## §5. What this page is NOT

- Not a numerics primer for implicit time-stepping schemes (the
  paragraph in §3.1.1 just states which scheme is used).
- Not a tokamak physics introduction (the rule-of-thumb claims
  in §3.2.7 are framed as such).
- Not a reproduction of `parameters.md` or `state.md` content
  — it cross-links to them for definitions and uses them as
  the source of truth for parameter / field meanings.
- Not a complete catalog of every console-output format string
  in `trrslt_print.f90` — that lives in the source and the
  page points at it.

## §6. Test / verification

- Build: `make -C docs/sphinx html` should succeed without new
  warnings (locally blocked by missing `furo` install — same as
  G; CI handles full build).
- Manual: render and visually verify the new appendix entry
  appears under "Appendix" in en + ja, and that all `{doc}`
  cross-references resolve.
- No code or test changes; pytest is N/A.

## §7. Pre-push gate

Same as G: 2 reviewers in parallel (in-house + Codex), REVIEW_OK
marker, push. Reviewer focus:

- **Factual accuracy** of TR-specific claims: implicit scheme,
  default values, ierr=3 causes, `TrDiagCode` meanings.
- **No fabrication:** no concrete typical values for "good `DT`"
  beyond fixture-grounded examples; no fabricated tr2 output
  formats; no claims about parameter ranges that are not
  verified against `tr_param_registry.f90`.
- **Cross-link correctness:** `{doc}` targets exist; the
  appendix toctree update lands cleanly.
- **Hedging discipline:** "rule-of-thumb" is used wherever the
  claim is operational tokamak physics rather than a TR API
  contract.
- **Bilingual parity:** en and ja line up structurally.
- **No content drift from `parameters.md`/`state.md`:** the new
  page does not duplicate definitions; it cross-links to them.

## §8. Out of scope (deferred)

- Adding numeric stability *examples* (i.e. running TR with
  pathological `DT` values and recording the failure modes).
  Tutorial T6 in the project memory covers this; defer to that.
- A complete `TrDiagCode` audit against
  `tr_param_registry.f90`'s actual diagnostic emissions
  (separate possible PR; this page documents the codes, it does
  not exhaustively map every parameter to a code).
- An `MDLPRT` print-mode reference table (separate possible PR;
  this page just notes the variable's existence).
- Mesh / radial-resolution (`NRMAX`) sensitivity guidance.
  Codex design-stage review (LOW 9) flagged this as a topic
  readers might expect; deferring to a future "tutorials"
  cluster (D in the menu).
- Singular-matrix / negative-temperature recovery paths inside
  `tr_loop`. Same Codex flag; this is internals territory and
  belongs in `design.md` if it is documented at all.
- Restart / checkpoint diagnostics. TR has no built-in
  checkpoint API at the L-7 baseline, so this is moot for the
  current page.

## §9. Acceptance criteria

1. ✅ `docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md` exists with all 7 subsections.
2. ✅ ja counterpart exists with structurally aligned content.
3. ✅ Both `index.md` files include `numerical-stability-and-diagnostics` in the Appendix toctree (after `limitations-and-references`).
4. ✅ The §3.1.1 paragraph correctly states TR is implicit, names the `FADV` advancement coefficient (NOT `THETA`), and cites the default `FADV = 1.D0` (fully implicit) from `tr/trinit.f90` together with the scheme-selector comments at `tr/trexec.f90:494-498`.
5. ✅ The §3.1.2 fixture table is grounded in the actual fixture files (`tot_demo2014_short`: `DT=0.01`, `NTMAX=100`, total `1.0s`; `tot_ht6m_short`: `DT=0.0001`, `NTMAX=1000`, total `0.1s`).
6. ✅ All 5 `TrDiagCode` values in §3.2.6 match the enum in `tr/tr_api.h`.
7. ✅ All "rule-of-thumb" claims in §3.2.7 are explicitly hedged.
8. ✅ All `{doc}` cross-references resolve.
9. ✅ Both reviewers (in-house + Codex) post-implementation report no HIGH findings.
