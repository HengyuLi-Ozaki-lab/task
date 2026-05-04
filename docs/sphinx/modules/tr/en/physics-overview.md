# Physics overview

```{admonition} What this page covers
:class: note

Orientation, NOT a derivation. This page sketches what TR solves
and which approximations it makes, and points at where in the
codebase each claim lives. Audience: graduate students or
early-career researchers approaching transport modelling for the
first time. Equations are named, not written out — for the
mathematics consult a tokamak transport textbook (see "Further
reading" below).
```

---

## What TR solves

TR solves a set of one-dimensional radial transport equations on
a flux-surface-averaged grid. The output is the time evolution of
the radial profiles — density, temperature, current, the safety
factor `q`, and the derived scalar diagnostics in
{doc}`state` (`WPT`, `TAUE1`, `TAUE2`, `BETAN`, etc.).

The equations are assembled and solved implicitly per time step.
Source-term and transport-coefficient assembly happens in
`tr/trcalc.f90:TRCALC` (which combines beam, RF, fusion, ohmic,
radiation, and other contributions). The implicit-step solver
calls live at `tr/trexec.f90:67-99`: `BANDRD` at line 69 and the
LAPACK band-solver path `DGBTRF` / `DGBTRS` / `DGBSV` at lines
81 / 86 / 96 (the `'Solve matrix equation'` comment block at
line 65 sits just above this).

This page deliberately does NOT write the differential equations
in symbolic form. For derivations consult a transport textbook.

---

## Spatial grid and boundary conditions

- **Radial coordinate.** TR's grid is one-dimensional in a
  flux-surface label (a normalised-radius coordinate, often
  written `rho`). The cell count is set by `NRMAX`, with a
  compile-time upper bound of `TR_MAX_NRMAX = 500`
  (`tr/tr_api.h`). Profile arrays are length `NRMAX`. The
  detailed mesh layout — which arrays sit on cell centres
  versus cell edges — lives in {doc}`design`; this page only
  orients you to "there is a single radial axis" and "all
  radial profiles are arrays of length `NRMAX`".

- **Inner boundary.** At the magnetic axis (`NR = 1` in the
  array indexing) regularity / symmetry conditions apply
  automatically; users do not configure these.

- **Outer boundary.** At the plasma edge (`NR = NRMAX`),
  boundary values are imposed via the registry parameters
  (edge-pinning of profiles, Dirichlet-style); see
  {doc}`parameters` for the configurable surface values. TR
  does NOT solve a separate edge / SOL transport problem (see
  "Where TR fits" below).

- **Evolved vs parameterized.** What evolves in time is the
  profile arrays (density / temperature / current). The
  *transport coefficients* are recomputed each inner iteration
  from the current profiles (Codex round-3 verified this in
  `tr/trexec.f90`: inner-loop entry at line 56, matrix solve at
  62-99, profile update at 160-282, `TRCALC` recompute at 298).
  Heating sources, NB beam deposition, RF power profiles, and
  similar drivers enter as source terms also recomputed each
  step.

---

## Equations TR can solve

TR has seven transport-equation switches, each independently
ON/OFF at the registry level (the `MDLEQ*` set). The defaults
below come from `tr/trinit.f90:687-695`:

| Flag | Quantity | Default | Notes |
|---|---|---|---|
| `MDLEQB` | Poloidal B (current diffusion / `q` profile evolution) | 1 (ON) | |
| `MDLEQT` | Temperature (heat diffusion) | 1 (ON) | |
| `MDLEQN` | Particle density (per ion species) | 0 (OFF) | |
| `MDLEQU` | Rotation | 0 (OFF) | |
| `MDLEQZ` | Impurity | 0 (OFF) | |
| `MDLEQ0` | Neutral | 0 (OFF) | |
| `MDLEQE` | Electron-density handling — 0 / 1 / 2 mode (not boolean) | 0 (OFF) | each mode maps to a distinct electron / ion density-equation handling (`tr/trprep.f90:407-415`, `tr/trexec.f90:180-201`); only meaningful when `MDLEQN = 1` (`tr/trprep.f90:202-203`). For per-mode behaviour consult those source locations. |

**The default ON set is `{MDLEQB, MDLEQT}`** — out of the box,
TR evolves current and temperature only; particles, rotation,
impurities, and neutrals are *not* evolved unless their flag is
turned on. Cross-link to {doc}`parameters` for the user-facing
controls.

---

## Approximations

### Flux-surface averaging (1-D radial)

TR is "1-D" in the sense that all profile quantities are indexed
by a single radial coordinate. The 2-D equilibrium geometry comes
from the `eq` module via the BPSD broker: `tr_bpsd_get`
(`tr/trbpsd.f90:160-183`) pulls device + plasma quantities, and
the equilibrium / metric pull at `tr/trbpsd.f90:213-245` only
fires for the geometry-aware `MODELG` settings (the analytic-
equilibrium path skips it). The combined picture is "1.5-D" —
1-D transport on top of 2-D equilibrium — the standard
transport-code style.

### Quasi-stationary equilibrium

The equilibrium is assumed to vary on a slower time scale than
transport, so the BPSD coupling runs as `eq.run()` push → tr
pull within each transport step. TR does NOT solve a
self-consistent dynamic equilibrium. For scenarios where the
equilibrium evolves rapidly (transient disruption studies, e.g.)
the user must either re-run `eq` more frequently or accept the
quasi-stationary approximation.

### Transport-model selector landscape

TR's transport coefficients come from several independent sources,
each with its own model selector. Layout verified at design time
against `tr/trinit.f90` and `tr/tr_param_registry.f90`:

**Selectors exposed in the public parameter registry** (settable
at runtime from `tr.set_param`,
`tr/tr_param_registry.f90:43-49,124-128`):

- **`MDLKAI` — turbulent heat transport.** Selects the
  turbulent (anomalous) heat-transport model. Options include
  CDBM, IFS-PPPL, GLF23, mixed Bohm/gyro-Bohm, and others; see
  {doc}`appendix-mdlkai` for the full list.
- **`MDLETA` — resistivity.** Selects the resistivity model used
  for current diffusion (the `MDLEQB` equation).
- **`MDLAD` — particle diffusion (model family).** Selects the
  particle-diffusion model. Multiple variants are available,
  including the Hinton-Hazeltine analytical form
  (`tr/trinit.f90:290-295`, `tr/trcoef_adhoc.f90:35-45`); it is
  a *model-family* selector, not a single ad-hoc switch.
- **`MDLAVK` — thermal pinch.** Selects the heat-pinch (inward
  heat-flux convective) model. **Not** a neoclassical selector
  — `MDLAVK` stands for the "anomalous V_K" / thermal-pinch
  model family (confirmed by `tr/trinit.f90:296-308` and
  the existing `parameters.md` entries on this page family).

**Selectors present in the Fortran source but NOT in the public
registry** (cannot be set from `tr.set_param`; retain compile-
time defaults from `tr/trinit.f90`):

- **`MDLKNC` — neoclassical heat / resistivity treatment.**
  Default at `tr/trinit.f90:306`.
- **`MDNCLS` — NCLASS module toggle** (the standard NCLASS
  neoclassical library). Defaults at `tr/trinit.f90:324` and
  `tr/trinit.f90:717`.

These two are the actual neoclassical knobs in TR but they are
not exposed for `tr.set_param`. Advanced users who need to
change them must edit `tr/trinit.f90` and rebuild.

The page's role is to give readers a map of the selector
landscape so they know which knob targets which physics — not
to document each selector exhaustively. For the runtime-settable
selectors see {doc}`parameters` and {doc}`appendix-mdlkai`. For
the non-registered selectors {doc}`design` is the entry point.

---

## Where TR fits

**Time scale.** TR is a transport-time-scale code. The natural
time step is milliseconds, total run time of order seconds
(consistent with the defaults `DT = 0.01 s` and `NTMAX = 100` at
`tr/trinit.f90:374,376`, total `1.0 s`). Faster phenomena are
not resolved.

**What TR resolves with simplified models** — these are reduced,
phenomenological models, not first-principles MHD:

- **Sawtooth oscillation.** `MDLST` selector
  (`tr/trinit.f90:392-402`). The mixing is implemented in
  `TRSAWT` (header at `tr/trcalc.f90:1072`, called from
  `tr/trloop.f90:59-65`), with the temperature / density / `q`
  redistribution step at `tr/trcalc.f90:1127-1150`. This is a
  phenomenological reconnection / mixing model, not a kink-mode
  solve.
- **ELM reduction.** `MDLELM` selector
  (`tr/trinit.f90:720-729`). A reduced ELM-frequency /
  ELM-energy-loss model rather than a first-principles
  pedestal-stability calculation.

**What TR does NOT model at all:**

- Edge / pedestal physics in any first-principles sense (no
  ETB-specific transport-barrier solve; boundary conditions are
  imposed at the outer radial cell).
- General MHD instabilities (kink, tearing, NTM, RWM, etc.) —
  only the simplified sawtooth and ELM-reduction switches above
  are present.
- 3-D effects (stellarator geometry, resonant magnetic
  perturbations) — TR assumes axisymmetry through the
  flux-surface averaging.
- Fast (gyrokinetic-scale) fluctuations directly — these enter
  only via the turbulent transport models, as transport
  coefficients.

For a comparison with related open transport codes (ASTRA,
JETTO-SANCO, TRANSP), see the table in
{doc}`limitations-and-references`. For runtime-stability and
diagnostic guidance, see
{doc}`numerical-stability-and-diagnostics`.

---

## Further reading

This section lists standard *general* tokamak transport
references for readers approaching the field for the first time.
TASK-specific publications and the comparison with related open
codes are in {doc}`limitations-and-references`.

The list below gives author + title (and the canonical edition
where one is uncontroversially the standard); publisher and year
are deliberately omitted because multiple editions and reprints
exist and the page does not assert which one the reader uses.
These are reading-list starting points, not authoritative
bibliographic citations.

- J. Wesson, *Tokamaks* (Oxford University Press, 4th edition)
  — encyclopedic textbook covering equilibrium, transport,
  stability, heating, diagnostics.
- R. D. Hazeltine & J. D. Meiss, *Plasma Confinement* —
  focused on the transport theory underlying codes like TR.
- J. P. Freidberg, *Ideal Magnetohydrodynamics* — equilibrium
  and stability foundation; the flux-surface coordinates TR uses
  come from this style of analysis.

The page does NOT cite specific equations or page numbers from
these books — they are bibliographic pointers.
