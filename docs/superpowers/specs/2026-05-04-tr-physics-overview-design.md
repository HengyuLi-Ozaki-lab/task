# TR Manual — Physics overview (User guide first entry) — Design

**Status:** Draft
**Date:** 2026-05-04
**Project memory:** `project_tr_proper_manual.md` ("Physics / domain context (new)" — 1-session expansion target, item A in the deepening menu)
**Predecessors today:**
- G appendix (`limitations-and-references`, commits `11f2b16d` / `5ad9a4a6` / `8081073b` / `a8b83311`)
- E appendix (`numerical-stability-and-diagnostics`, commits `ad01cc89` / `4745ba24` / `fc74599d`)
- 7-module `applications.md` ja → en series (final tr translation at `169c17a9` / `c3d1ce82`)

---

## §1. Overview

Add a bilingual orientation page to the TR Sphinx chapter — the
"Physics overview" — covering 5 topics:

1. **What TR solves** (1-D radial transport on a flux-surface-averaged grid)
2. **Equations TR can solve** (the 7 `MDLEQ*` flags + their on/off defaults)
3. **Approximations** (flux-surface averaging, quasi-stationary equilibrium, neoclassical-vs-turbulent transport split)
4. **Where TR fits** (time scale, what TR does not model)
5. **Further reading** (standard tokamak transport textbooks, by pointer)

The page is the first entry in the "User guide" toctree — readers
arriving at the tr chapter from `index.md` see the physics
context **before** the build / hello-world / parameters pages.

This is the "A" item from the deepening menu in
`project_tr_proper_manual.md`, sized at 1 session.

## §2. File structure

**New files (bilingual pair):**

- `docs/sphinx/modules/tr/en/physics-overview.md`
- `docs/sphinx/modules/tr/ja/physics-overview.md`

**Edited files:**

- `docs/sphinx/modules/tr/en/index.md` — prepend
  `physics-overview` to the User guide toctree (above `build`)
- `docs/sphinx/modules/tr/ja/index.md` — same

No new MyST anchor labels are needed; outgoing cross-links
target existing pages.

## §3. Page structure

### Header

- Title (en): "Physics overview"
- Title (ja): "物理の概観"
- One-paragraph admonition stating the audience (graduate
  students or early-career researchers approaching transport
  modelling for the first time) and the page's role
  (orientation, NOT a derivation; equations are named, not
  written out).

### §3.1 Section "What TR solves"

~20 lines. One paragraph plus 1–2 callouts.

Content:

- TR solves a set of 1-D radial transport equations on a
  flux-surface-averaged grid; the output is the time evolution
  of the radial profiles (density, temperature, current, q
  profile, etc.).
- The equations are assembled and the matrix is solved
  implicitly per time step. Cite `tr/trcalc.f90:TRCALC` for
  source / coefficient assembly, and `tr/trexec.f90:67-99` for
  the implicit-step solver calls (`BANDRD` at line 69, the
  LAPACK band-solver path `DGBTRF`/`DGBTRS`/`DGBSV` at lines
  81 / 86 / 96 — the `'Solve matrix equation'` comment block
  at line 65 sits just above this).
- The page deliberately does NOT write the differential
  equations in symbolic form — readers should consult a
  tokamak transport textbook for derivations (see "Further
  reading" below).

### §3.1.5 Section "Spatial grid and boundary conditions"

~15 lines. One paragraph + 1–2 short bullets.

Content (Codex review LOW 4 fill-in):

- **Radial coordinate.** TR's grid is one-dimensional in a
  flux-surface label (rho-like normalised radius). The cell
  count is set by `NRMAX` (default in
  `tr/trinit.f90`) and bounded at compile time by
  `TR_MAX_NRMAX = 500` (`tr/tr_api.h`). The mesh layout —
  which arrays live on cell centres vs cell edges — is
  documented in {doc}`design`; this page only orients
  readers to "there is a single radial axis" and "all
  radial profiles are arrays of length `NRMAX`".
- **Inner boundary.** At the magnetic axis (`NR = 1` in
  the array indexing), regularity / symmetry conditions
  apply automatically; users do not configure these.
- **Outer boundary.** At the plasma edge (`NR = NRMAX`),
  values are imposed via the registry parameters (e.g.
  edge-pinning of profiles); see {doc}`parameters` for the
  configurable surface values. TR does NOT solve a
  separate edge / SOL transport problem (see §3.4 below).
- **Evolved vs parameterized.** The transport coefficients
  (turbulent + neoclassical contributions, see §3.3) are
  computed *once per inner iteration* from the current
  profiles and held constant during that step's matrix
  solve; what *evolves in time* is the profile arrays
  (density / temperature / current). Heating sources, NB
  beam deposition, RF power profiles, etc. enter as source
  terms also recomputed each step.

This subsection is intentionally short and orientation-only;
specific array layouts and edge-condition mechanics belong
in {doc}`design` and {doc}`parameters`.

### §3.2 Section "Equations TR can solve"

~30 lines. One paragraph plus a table.

Content:

- TR has 7 transport-equation switches; each can be set to
  ON / OFF independently. The names and defaults come from
  `tr/trinit.f90:687-695` (verified at design time).
- Table:

  | Flag | Quantity | Default | Notes |
  |---|---|---|---|
  | `MDLEQB` | Poloidal B (current diffusion / q profile evolution) | 1 (ON) | |
  | `MDLEQT` | Temperature (heat diffusion) | 1 (ON) | |
  | `MDLEQN` | Particle density (per ion species) | 0 (OFF) | |
  | `MDLEQU` | Rotation | 0 (OFF) | |
  | `MDLEQZ` | Impurity | 0 (OFF) | |
  | `MDLEQ0` | Neutral | 0 (OFF) | |
  | `MDLEQE` | Electron density handling — 0 / 1 / 2 mode (not boolean) | 0 (OFF) | each mode maps to a distinct electron / ion density-equation handling (`tr/trprep.f90:407-415`, `tr/trexec.f90:180-201`); only meaningful when `MDLEQN = 1` (`tr/trprep.f90:202-203`). For the per-mode behaviour see those source locations. |

- Default-out-of-the-box ON set is `{MDLEQB, MDLEQT}` →
  TR by default evolves current and temperature only;
  particles, rotation, impurities, neutrals are NOT evolved
  unless their flag is turned on.
- Cross-link to {doc}`parameters` for the user-facing
  controls (the registry exposes these flags by name).

The implementation step verifies these flag names + defaults
against `tr/trinit.f90:687-695` and DOES NOT introduce flags
that don't exist in source.

### §3.3 Section "Approximations"

~25 lines. Three short subsections, one paragraph each.

**a. Flux-surface averaging (1-D radial)**

TR is "1-D" in the sense that all profile quantities are
indexed by a single radial coordinate. The 2-D equilibrium
geometry comes from the `eq` module via the BPSD broker:
`tr_bpsd_get` (`tr/trbpsd.f90:160-183`) pulls device + plasma
quantities, and the equilibrium / metric pull at
`tr/trbpsd.f90:213-245` only fires for the geometry-aware
`MODELG` settings (the analytic-equilibrium path skips it).
The combined picture is "1.5-D" (1-D transport on top of 2-D
equilibrium), the standard transport-code style.

**b. Quasi-stationary equilibrium**

The equilibrium is assumed to vary on a slower time scale
than transport, so the BPSD coupling is push (eq) → get (tr)
within each transport step. TR does not solve a
self-consistent dynamic equilibrium; readers running
scenarios where the equilibrium evolves rapidly (transient
disruption studies, etc.) need to either re-run `eq` more
frequently or accept the approximation.

**c. Transport-model selector landscape**

TR's transport coefficients come from several independent
sources, each with its own model selector. The actual flag
layout (verified at design time against `tr/trinit.f90` and
`tr/tr_param_registry.f90`):

Selectors that are **exposed in the public parameter
registry** (`tr/tr_param_registry.f90:43-49,124-128`) — i.e.
settable from `tr.set_param`:

- **Turbulent heat transport — `MDLKAI`**: selects the
  turbulent (anomalous) heat-transport model (CDBM,
  IFS-PPPL, GLF23, mixed Bohm/gyro-Bohm, and others — see
  {doc}`appendix-mdlkai`).
- **Resistivity model — `MDLETA`**: selects the resistivity
  model used for current diffusion.
- **Particle diffusion — `MDLAD`**: selects the particle-
  diffusion model. Multiple variants are available, including
  the Hinton-Hazeltine analytical form
  (`tr/trinit.f90:290-295`, `tr/trcoef_adhoc.f90:35-45`); it
  is a *model-family* selector, not a single ad-hoc switch.
- **Thermal pinch — `MDLAVK`**: selects the heat-pinch
  (inward heat-flux convective) model. *This is NOT a
  neoclassical selector* — `MDLAVK` stands for the
  "anomalous V_K" / thermal-pinch model family, confirmed
  by `tr/trinit.f90:296-308` and `parameters.md:213-216`.

Selectors **present in the Fortran source but NOT in the
public parameter registry** — i.e. they cannot be changed at
run time from `tr.set_param`, and retain their compile-time
defaults from `tr/trinit.f90`:

- **Neoclassical transport handling — `MDLKNC` and
  `MDNCLS`**: `MDLKNC` selects a neoclassical heat /
  resistivity treatment, and `MDNCLS` toggles the NCLASS
  module. These are the actual neoclassical knobs but they
  are *not* registered for `tr.set_param`; advanced users who
  need to change them must edit `tr/trinit.f90` and rebuild.

The page's role is to give readers a map of the selector
landscape so they know which knob targets which physics —
not to document each selector exhaustively. For the runtime-
settable selectors see {doc}`parameters` and
{doc}`appendix-mdlkai`. For the non-registered selectors,
{doc}`design` is the entry point.

### §3.4 Section "Where TR fits"

~20 lines. One paragraph + bulleted list.

Content:

- **Time scale.** TR is a transport-time-scale code: the
  natural time step is milliseconds, total run time of order
  seconds (consistent with the defaults at
  `tr/trinit.f90:374,376` — `DT = 0.01s`, `NTMAX = 100`,
  total `1.0s`). Faster phenomena are not resolved.
- **What TR resolves with simplified models** (caveat:
  these are reduced models, not first-principles MHD):
  - **Sawtooth oscillation** — `MDLST` selector
    (`tr/trinit.f90:392-402`); the actual mixing is
    implemented in `TRSAWT` (header at `tr/trcalc.f90:1072`,
    called from `tr/trloop.f90:59-65`), with the temperature /
    density / q redistribution step at
    `tr/trcalc.f90:1127-1150`. This is a phenomenological
    reconnection / mixing model, not a kink-mode solve.
  - **ELM reduction** — `MDLELM` selector
    (`tr/trinit.f90:720-729`). Again a reduced ELM-frequency
    / ELM-energy-loss model rather than a first-principles
    pedestal-stability calculation.
- **What TR does NOT model at all:**
  - Edge / pedestal physics in any first-principles sense
    (no ETB-specific transport-barrier solve; boundary
    conditions are imposed at the outer radial cell).
  - General MHD instabilities (kink, tearing, NTM, RWM, etc.)
    — only the simplified sawtooth and ELM-reduction switches
    above are present.
  - 3-D effects (stellarator geometry, resonant magnetic
    perturbations) — TR assumes axisymmetry through the
    flux-surface averaging.
  - Fast (gyrokinetic-scale) fluctuations directly — these
    enter only via the turbulent transport models, as
    transport coefficients.
- **Comparison with other codes:** see the comparison table
  in {doc}`limitations-and-references`.

### §3.5 Section "Further reading"

~15 lines. One short paragraph + 3 textbook pointers.

Content:

- One paragraph: this section lists standard *general*
  tokamak transport references for readers approaching the
  field for the first time. TASK-specific publications and
  the comparison with related open codes are in
  {doc}`limitations-and-references`.
- Pointers (author + title + edition only; no publisher or
  year — these are reading-list starting points, not
  authoritative bibliographic citations the page is asserting):
  - J. Wesson, *Tokamaks* (Oxford University Press, 4th
    edition) — encyclopedic textbook covering equilibrium,
    transport, stability, heating, diagnostics.
  - R. D. Hazeltine & J. D. Meiss, *Plasma Confinement* —
    focused on the transport theory underlying codes like TR.
  - J. P. Freidberg, *Ideal Magnetohydrodynamics* —
    equilibrium and stability foundation; the flux-surface
    coordinates TR uses come from this style of analysis.

The page does NOT cite specific equations or page numbers
from these books — they are bibliographic pointers. The
4th-edition designation for Wesson is the well-known one;
publisher / year fields are deliberately omitted because
multiple editions and reprints exist and the page does not
assert which one the reader uses.

## §4. Bilingual content

Same convention as G / E. Headings translated faithfully;
table column labels (`Flag`, `Quantity`, `Default`, `Notes`)
stay English; identifiers (`MDLEQB`, `MDLKAI`, `tr/trinit.f90`)
inline-code in both languages. Textbook titles and author
names stay English in both ja and en files; the surrounding
prose is translated.

## §5. What this page is NOT

- Not a transport-physics derivation (the equations are
  named, not written; readers should use the textbooks for
  derivations).
- Not a numerical-methods primer (the implicit time-stepping
  details live in {doc}`numerical-stability-and-diagnostics`).
- Not a parameter reference (the `MDLEQ*` flags are sketched
  here at the level "what does this flag turn on"; the full
  parameter table is in {doc}`parameters`).
- Not a TASK-publication bibliography (TASK-specific papers
  and the open-code comparison are in
  {doc}`limitations-and-references`).
- Not a tutorial (no working code; tutorials belong in the
  D item — multi-scenario tutorials).

## §6. Test / verification

- Build: `make -C docs/sphinx html` should succeed without
  new warnings (locally blocked by missing `furo` install —
  same as G / E; CI handles full broken-ref check).
- Manual: render and visually check that the User guide
  toctree starts with `physics-overview` and that all
  `{doc}` cross-references resolve.
- No code or test changes; pytest is N/A.

## §7. Pre-push gate

Same as G / E: 2 reviewers in parallel (in-house + Codex),
REVIEW_OK marker, push. Reviewer focus:

- **Factual accuracy of TR-specific claims.** The `MDLEQ*`
  flag names and defaults must match `tr/trinit.f90:687-695`
  byte-for-byte. The transport-model selector names
  (`MDLKAI` / `MDLAVK` / `MDLAD`) must match
  `tr/tr_param_registry.f90`.
- **No fabrication of physics.** No specific equation forms,
  no specific quantitative values (e.g. no "ITER-scale
  diffusion coefficients are around 1 m^2/s"), no claims
  about regimes or instabilities beyond what is publicly
  uncontroversial.
- **Hedging discipline for tokamak-physics claims.** Anything
  beyond "TR has a switch for X" is operational tokamak
  physics; the wording should make that clear ("rule of
  thumb", "in tokamak transport practice", etc., consistent
  with G's discipline).
- **Cross-link correctness.** `{doc}` targets exist; the
  toctree update lands cleanly.
- **Bilingual parity.** en and ja line up structurally.
- **Textbook pointer hygiene.** No fabricated page numbers,
  no fabricated quotes; titles + edition years verified to
  match commonly-cited editions.

## §8. Out of scope (deferred)

- Specific transport-equation derivations (defer to textbooks;
  if the user later wants a derivation page, that is a
  separate item, NOT part of A).
- A comprehensive `MDLKAI` / `MDLAVK` / `MDLAD` cross-table
  (the existing `appendix-mdlkai.md` already covers
  `MDLKAI`; deepening that is out of A's scope).
- A pedestal / ELM / sawtooth modelling discussion (TR does
  not model these; mentioning that they are out of scope is
  in scope for this page, but explaining how other codes do
  is not).
- Tokamak vs stellarator vs RFP comparison (TR is
  axisymmetric — this page just notes the assumption,
  doesn't compare).
- A bibliography of Fukuyama-group papers (defer to
  {doc}`limitations-and-references` once verified citations
  exist; no fabrication).

## §9. Acceptance criteria

1. ✅ `docs/sphinx/modules/tr/en/physics-overview.md` exists with sections §3.1, §3.1.5, §3.2, §3.3, §3.4, §3.5 (six sections after the Codex LOW 4 fill-in).
2. ✅ ja counterpart exists with structurally aligned content.
3. ✅ Both `index.md` files prepend `physics-overview` to the User guide toctree (before `build`).
4. ✅ §3.1.5 documents the radial coordinate, `NRMAX`, the inner / outer boundary handling, and the evolved-vs-parameterized distinction.
5. ✅ §3.2 table lists all 7 `MDLEQ*` flags with names and defaults that match `tr/trinit.f90:687-695` byte-for-byte. The `MDLEQE` row explicitly notes the 0/1/2 mode and the dependency on `MDLEQN = 1` (Codex MED 1).
6. ✅ §3.2 explicitly states the default ON set is `{MDLEQB, MDLEQT}`.
7. ✅ §3.3c names `MDLKAI` (turbulent heat), `MDLETA` (resistivity), `MDLAD` (particle-diffusion **model selector** — incl. Hinton-Hazeltine, NOT solely 'anomalous'), `MDLAVK` (thermal pinch — explicitly NOT a neoclassical selector), and separately `MDLKNC` / `MDNCLS` for neoclassical handling. The misidentification of `MDLAVK` as the neoclassical knob (Codex HIGH 1 against the original draft) is fixed. The page additionally states which selectors are exposed in `tr/tr_param_registry.f90:43-49,124-128` (i.e. user-settable) versus which exist only as compile-time defaults in `tr/trinit.f90` (i.e. `MDLKNC` / `MDNCLS`).
8. ✅ §3.3a cites `tr_bpsd_get` at `tr/trbpsd.f90:160-183` for the device / plasma pull and `tr/trbpsd.f90:213-245` for the equilibrium / metric pull (only fires for relevant `MODELG`) — Codex MED 2.
9. ✅ §3.4 distinguishes "TR resolves with simplified models" (sawtooth via `MDLST` / `TRSAWT` — header at `tr/trcalc.f90:1072`, redistribution at `tr/trcalc.f90:1127-1150`; ELM reduction via `MDLELM`) from "TR does NOT model at all" (full MHD / pedestal / 3-D / gyrokinetic) — Codex HIGH 2 from the first design review, with the redistribution line range corrected per Codex re-review MED 1.
10. ✅ §3.5 lists ≥ 3 standard tokamak-transport textbooks as bibliographic pointers, with publisher / year deliberately omitted to avoid asserting unverified bibliographic claims (Codex LOW 1).
11. ✅ All `{doc}` cross-references resolve to existing files in both `en/` and `ja/`.
12. ✅ Both reviewers (in-house + Codex) post-implementation report no HIGH findings.
