# Numerical stability and diagnostics

```{admonition} What this page covers
:class: note

Operational guidance for keeping TR runs healthy (stability) and
for reading the signals when something goes wrong (diagnostics).
This page pairs with {doc}`limitations-and-references`: that page
documents what TR cannot do; this page documents how to keep TR
doing what it can.
```

---

## Numerical stability

### Time-stepping scheme

TR uses an implicit time-stepping scheme. The advancement
coefficient is `FADV` (do not confuse with `THETA`, which is
reserved elsewhere): `FADV = 0.5` is Crank-Nicolson and
`FADV = 1.0` is fully implicit. The value is hard-coded inside
the time-step routine itself — `tr/trexec.f90:498` assigns
`FADV = 1.D0` unconditionally — so TR runs fully implicit out
of the box and there is no public knob to switch to
Crank-Nicolson without editing the source. The scheme-selector
comments at `tr/trexec.f90:494-498` document the meaning of
each value.

Concrete consequence: a strict CFL condition does NOT apply.
Time-step selection is governed by truncation error and
inner-iteration convergence, not by an advection-style
stability bound.

### Time-step selection guidance

`DT` selection is governed by two competing concerns:

- Smaller `DT` reduces truncation error per step but requires
  more steps for the same total time.
- Larger `DT` is cheaper per step but makes the inner iteration
  (see below) work harder, and at some point the scheme can no
  longer reduce the residual within `LMAXTR` iterations.

The defaults are `DT = 0.01 s` (`tr/trinit.f90:374`) and
`NTMAX = 100` (`tr/trinit.f90:376`), which together advance the
simulation by 1.0 s. These suit equilibrium-scale runs;
sub-millisecond `DT` is rarely required for transport-time-scale
studies but is sometimes necessary for source-driven transients
(see the `ht6m` row below).

For divergent or unstable cases the practical recipe is to halve
`DT` and retry — the `StableTrRunner` wrapper in
{doc}`applications` implements exactly this.

Examples (fixture-grounded):

| Fixture | `DT` | `NTMAX` | Total time |
|---|---|---|---|
| `tot_demo2014_short` (Layer 1 baseline) | 0.01 s | 100 | 1.0 s |
| `tot_ht6m_short` (Layer 1 baseline) | 0.0001 s | 1000 | 0.1 s |

The `demo2014` fixture sets only `NTMAX` at
`python/totlib/tests/fixtures/tot_demo2014_params.py:74` and
inherits `DT = 0.01` from the trinit defaults. The `ht6m`
fixture overrides both at
`python/totlib/tests/fixtures/tot_ht6m_params.py:63-64`,
running 100× more steps at 100× smaller `DT` because its
physical time scale (sub-second) and resolution requirements
differ.

### Inner-iteration convergence (`EPSLTR`, `LMAXTR`)

Each time step runs an inner iteration that converges toward
`EPSLTR` (relative residual threshold). The convergence checks
live at `tr/trexec.f90:112-128` (per species, per radial
cell). The exit-on-iteration-budget guard sits at
`tr/trexec.f90:138-141`: when the iteration counter reaches
`LMAXTR` the loop exits *without* setting `IERR` and *without*
writing a console diagnostic, so the run **silently continues**
with whatever residual was reached. There is no per-step flag
to detect saturation; the only signal is whether profile-level
diagnostics (e.g. drift in `WPT` or `Q0`, see below) start to
look unphysical.

Defaults are `EPSLTR = 0.001` and `LMAXTR = 10`, which is
conservative. If you suspect that runs are saturating `LMAXTR`,
the lightweight check is to raise `LMAXTR` and re-run: if
results change, the previous setting was insufficient. Only
loosen `EPSLTR` if profile-level diagnostics confirm that the
residual is local (e.g. confined to one species or one radial
cell) rather than a sign of an underlying numerical problem.

### `tr_run` `ierr=3` (`CALC_FAILED`) diagnosis

`tr_api_run` (`tr/tr_api.f90:227-245`) returns
`TR_ERR_CALC_FAILED` for **any** non-zero result code from the
underlying `tr_prep` / `tr_loop` routines. The wrapper
deliberately collapses the full set of downstream failure
classes into a single ABI code; `ierr=3` is therefore an
umbrella signal that "something downstream did not finish
cleanly", not a diagnosis of which subsystem failed. Narrowing
it down is the user's job.

Diagnostic recipe:

1. Run `validate()` first; if any blocking diagnostic
   (`FILE_MISSING`, `MISSING_REQUIRED` — see below) is present,
   fix it. This is the cheapest way to rule out classes of
   failure before launching the run.
2. Halve `DT` and retry (use `StableTrRunner` in
   {doc}`applications`). If the failure was a numerical
   stiffness or inner-iteration symptom, this often clears it.
3. Inspect tr2 console output for diverging energies and
   profile drift (see "Reading tr2 console output" below).
   Note that inner-iteration saturation does *not* surface
   in the console (see §"Inner-iteration convergence"
   above), so its presence has to be inferred from
   profile-level signals.
4. Cross-check {doc}`parameters` and {doc}`parameter-setting`
   for parameter ranges and inter-parameter constraints that
   `validate()` may not catch.

---

## Diagnostics & observability

### Reading tr2 console output

The standalone `tr2` driver prints a per-step block plus
periodic episode summaries via the `WRITE(6, …)` statements in
`tr/trrslt_print.f90`. The full set of formats lives in that
file; the layout depends on the print mode (`MDLPRT`).

The compact per-step block (`tr/trrslt_print.f90:266-269`,
KID 7/8 modes) prints four scalars:

- `T` — current simulation time [s]
- `WPT` — total stored energy [MJ]
- `TAUE1` / `TAUE2` — energy confinement times [s]

These are the fastest signals for spotting an unhealthy run.
Episode-summary blocks
(`tr/trrslt_print.f90:280-284` and surrounding) add the
device-shape parameters and current-related scalars:

- `Q0` — axis safety factor
- `AJTTOR` — total plasma current including the toroidal
  component (note: this is `AJTTOR`, not `AJT`; both fields
  exist in the print blocks and they are not the same
  quantity)
- Integrated beam / RF powers

These map onto the fields populated by `tr.get_state()` (see
{doc}`state`), so reading the console output is a quick way
to sanity-check what `get_state()` will return — but match
the variable name carefully when comparing console scalars
against `TrState` attributes.

### `validate()` output mapping (`TrDiagCode`)

`tr.validate()` returns a list of diagnostics, each carrying
one of five `TrDiagCode` values from the enum at
`tr/tr_api.h:69-75` (mirrored in `python/trlib/_ffi.py:58-62`).
The enum reserves five categories, but the **current
implementation** of `tr_api_validate` only emits two of them:
`OUT_OF_RANGE` and `FILE_MISSING`. The other three
(`INCONSISTENT_PAIR`, `OUT_OF_RANGE_AFTER_DEP`,
`MISSING_REQUIRED`) are reserved for future categories — the
slots exist in the enum so the API surface is stable, but the
checks have not been wired up yet (`tr/tr_api.f90:365-378`
documents this).

The two currently-emitted categories:

- **`OUT_OF_RANGE`** — a parameter value sits outside the
  range that `tr_api_validate` checks. Validate's `NSMAX`
  check, for example, compares against the run-time species
  bound `NSM = 4` (not the compile-time C ABI bound
  `TR_MAX_NSMAX = 8`), so `NSMAX = 5` reaches `validate()`
  and is reported here (`tr/tr_api.f90:402-403`). Note: values
  beyond the registry's own range — e.g. `NSMAX > 8` — are
  rejected by `set_param` *before* validate runs
  (`tr/tr_param_registry.f90:95-97`), so you will not see
  them in the diagnostic list. Validate's job is to catch the
  values the registry accepted but the run-time still cannot
  use.

- **`FILE_MISSING`** — a required file path is empty or
  points at a file the library cannot open. Typical example:
  `MODELG ∈ {3, 5, 7, 8}` paired with empty `KNAMEQ`.

The reserved categories (no emissions in the current
implementation):

- **`INCONSISTENT_PAIR`** — reserved for future use, intended
  for pairs of parameters that individually pass range checks
  but jointly form an invalid configuration. Note that the
  `EXTERNAL_DRIVEN_I != 0` + `EXTERNAL_DRIVEN_RW <= 0` check
  is currently emitted as `OUT_OF_RANGE` rather than as a
  pair-level diagnostic
  (`tr/tr_api.f90:419-425`).

- **`OUT_OF_RANGE_AFTER_DEP`** — reserved for future use,
  intended for parameters that pass their declared range but
  conflict with a bound deduced at runtime (e.g. `NRMAX`
  capped by the equilibrium grid).

- **`MISSING_REQUIRED`** — reserved for future use, intended
  to flag required parameters that were never set
  (distinguished from `OUT_OF_RANGE` because the *absence* is
  the problem, not the value).

The recommended workflow is to call `validate()` after
`set_params()` and before `run()`, which is exactly what
{doc}`parameter-setting` Method D demonstrates.

### `TrState` diagnostic patterns

The {doc}`state` page lists the fields that `get_state()`
populates. Below are *what to look for* in those fields when
running a transport simulation. Each item is a rule of thumb,
not a TR API contract — the magnitudes and thresholds depend
on the scenario.

- **Stored-energy drift.** Monitor `WPT` over time. A run
  approaching a quasi-steady state should plateau; an unbounded
  rise typically indicates a source/sink imbalance.

- **q-profile peaking.** `Q0` (axis safety factor) below 1 is
  a rule-of-thumb threshold for sawtooth instability in
  tokamaks. TR does not model sawteeth, so persistent
  `Q0 < 1` may indicate that the resulting profile is
  non-physical at the axis — but the magnitude of the drift,
  and whether it matters for the diagnostic the user actually
  cares about, depend on the scenario.

- **Current relaxation.** The time over which `AJT` settles
  after a change in `EXTERNAL_DRIVEN_I` is a rule-of-thumb
  estimate of the resistive current relaxation time. Order of
  seconds for ITER-class devices, sub-second for smaller
  machines.

- **Energy confinement.** `TAUE1` / `TAUE2` are computed from
  `WPT` and the integrated input power. Comparing their ratio
  with empirical scaling laws (e.g. ITER89-P) is a standard
  sanity check for whether the simulation is in a physically
  sensible regime.
