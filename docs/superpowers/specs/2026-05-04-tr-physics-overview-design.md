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
  implicitly per time step (cite `tr/trcalc.f90:TRCALC` for
  source / coefficient assembly, `tr/trexec.f90:65` 'Solve
  matrix equation' for the implicit step).
- The page deliberately does NOT write the differential
  equations in symbolic form — readers should consult a
  tokamak transport textbook for derivations (see "Further
  reading" below).

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
  | `MDLEQE` | Electron density (separate flag) | 0 (OFF) | turn on for electron-density evolution distinct from `MDLEQN` |

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
geometry comes from the `eq` module via the BPSD broker: see
`tr/trbpsd.f90` for the pull side. The combined picture is
"1.5-D" (1-D transport on top of 2-D equilibrium), the
standard transport-code style.

**b. Quasi-stationary equilibrium**

The equilibrium is assumed to vary on a slower time scale
than transport, so the BPSD coupling is push (eq) → get (tr)
within each transport step. TR does not solve a
self-consistent dynamic equilibrium; readers running
scenarios where the equilibrium evolves rapidly (transient
disruption studies, etc.) need to either re-run `eq` more
frequently or accept the approximation.

**c. Neoclassical-vs-turbulent transport split**

Transport coefficients are assembled from three sources, each
with its own model selector (cite `tr/tr_param_registry.f90`):

- Turbulent (anomalous) transport: `MDLKAI` selects the
  model (CDBM, IFS-PPPL, GLF23, mixed Bohm/gyro-Bohm, etc.;
  see {doc}`appendix-mdlkai`).
- Neoclassical transport: `MDLAVK` selects the model.
- Residual / ad-hoc anomalous diffusion: `MDLAD` (a
  separate ad-hoc additive term; not the
  neoclassical-vs-turbulent split itself).

The implementation step verifies these flag names against
`tr/tr_param_registry.f90`; if any flag is misnamed in the
spec, the implementation corrects to the actual source name.

### §3.4 Section "Where TR fits"

~20 lines. One paragraph + bulleted list.

Content:

- **Time scale.** TR is a transport-time-scale code: the
  natural time step is milliseconds, total run time of order
  seconds (consistent with the defaults at
  `tr/trinit.f90:374,376` — `DT = 0.01s`, `NTMAX = 100`,
  total `1.0s`). Faster phenomena are not resolved.
- **What TR does NOT model:** bulleted list, each item one
  line:
  - Sawtooth instabilities (no internal-kink mode in core)
  - Edge / pedestal physics (no ETB-specific model;
    boundary conditions are imposed at the outer radial cell)
  - MHD instabilities (kink, tearing, ELMs)
  - 3-D effects (stellarator geometry, resonant magnetic
    perturbations) — TR assumes axisymmetry through the
    flux-surface averaging
  - Fast (gyrokinetic-scale) fluctuations — these enter only
    via the turbulent transport models, as transport
    coefficients
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
- Pointers (no page numbers — the reader is expected to use
  these as starting points, not as citations the page is
  asserting):
  - J. Wesson, *Tokamaks* (Oxford, 4th edition, 2011) —
    encyclopedic textbook covering equilibrium, transport,
    stability, heating, diagnostics.
  - R. D. Hazeltine & J. D. Meiss, *Plasma Confinement*
    (Dover, 2003) — focused on the transport theory
    underlying codes like TR.
  - J. P. Freidberg, *Ideal Magnetohydrodynamics* (Springer,
    1987) — equilibrium and stability foundation; the
    flux-surface coordinates TR uses come from here.

The page does NOT cite specific equations or page numbers
from these books — they are bibliographic pointers, not
authoritative claims.

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

1. ✅ `docs/sphinx/modules/tr/en/physics-overview.md` exists with all 5 sections.
2. ✅ ja counterpart exists with structurally aligned content.
3. ✅ Both `index.md` files prepend `physics-overview` to the User guide toctree (before `build`).
4. ✅ §3.2 table lists all 7 `MDLEQ*` flags with names and defaults that match `tr/trinit.f90:687-695` byte-for-byte.
5. ✅ §3.2 explicitly states the default ON set is `{MDLEQB, MDLEQT}`.
6. ✅ §3.3 names `MDLKAI`, `MDLAVK`, `MDLAD` and cites `tr/tr_param_registry.f90` for them; flag names verified to exist in source.
7. ✅ §3.3 cites `tr/trbpsd.f90` for the eq → tr BPSD pull side.
8. ✅ §3.4 explicitly lists items TR does NOT model (sawtooth / pedestal / MHD / 3-D / gyrokinetic-scale).
9. ✅ §3.5 lists ≥ 3 standard tokamak-transport textbooks as bibliographic pointers (no page numbers, no fabricated quotes).
10. ✅ All `{doc}` cross-references resolve to existing files in both `en/` and `ja/`.
11. ✅ Both reviewers (in-house + Codex) post-implementation report no HIGH findings.
