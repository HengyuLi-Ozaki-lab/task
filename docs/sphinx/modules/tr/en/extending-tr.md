# Extending TR

```{admonition} Audience
:class: note

This page is **maintainer-facing**. The reader has the
source tree checked out and is comfortable editing Fortran
and rebuilding `libtrapi.so`. Three concrete walkthroughs
follow — adding a scalar parameter, adding a transport-
model selector under `MDLKAI`, and adding a `TrState`
field. Each is a recipe, not a derivation.
```

---

## Walkthrough A — Add a new scalar parameter

The TR parameter registry uses a hand-written `SELECT CASE`
dispatch in `tr/tr_param_registry.f90:76+`. Adding a
parameter `FOO` is one new `CASE` line in that dispatch
plus a default in `tr/trinit.f90`.

**Recipe (5 steps):**

1. **Declare the variable.** If the parameter is new (not
   already in TRCOMM), declare it in the appropriate
   `tr/trcomm*.f90` module alongside similar parameters.
   If it already exists, skip this step.
2. **Add the registry case.** Add a line like
   `CASE ("FOO"); FOO = value` in the
   `SELECT CASE (TRIM(b))` block that starts at
   `tr/tr_param_registry.f90:76`. Place it near similar
   parameters to preserve the per-section grouping
   convention.
3. **Set a default.** Add `FOO = ...` to `tr/trinit.f90`
   alongside other initialisation.
4. **Rebuild.** `make -C tr libtrapi.so`.
5. **Use from Python.** `tr.set_param("FOO", x)` works
   immediately. No C ABI change is needed because
   `tr_set_param` is string-keyed (verified at
   `tr/tr_api.f90:124-128,136-148`).

For array-valued parameters, the bounds-checked idiom at
`tr/tr_param_registry.f90:101-106` is the template. The
existing `PA[i]` / `PN[i]` / `PNS[i]` / `PT[i]` cases
show the pattern: each `CASE` checks `idx` against
`SIZE(...)` and either assigns or sets `ierr = 1`.

---

## Walkthrough B — Add a new transport model under `MDLKAI`

Turbulent heat-transport coefficients are dispatched via
`SELECT CASE(MDLKAI)` at
`tr/trcoef_turbulence.f90:400`. (The earlier `select case`
at line 64 handles graph-label assignment, NOT the actual
coefficient computation.) Each `MDLKAI` value invokes a
different model.

The numbering convention (per the source-side comments at
`tr/trcoef_turbulence.f90:392-398`):

- `MDLKAI < 10` — constant-coefficient toy models.
- `10 ≤ MDLKAI < 20` — drift-wave (+ITG / +ETG) models.
- `20 ≤ MDLKAI < 30` — Rebu-Lalla family.
- `30 ≤ MDLKAI < 40` — current-diffusivity-driven (CDBM)
  family.
- `40 ≤ MDLKAI < 60` — drift-wave-ballooning models.
- `MDLKAI ≥ 60` — ITG / TEM / ETG model families.

**Recipe (4 steps):**

1. **Pick a `MDLKAI` value** in the appropriate range,
   choosing the next free integer if you are adding
   alongside existing models.
2. **Add a `CASE (N)` block** in
   `tr/trcoef_turbulence.f90` after line 400. The block
   should fill the appropriate transport-coefficient
   arrays — `AKDW` (heat anomalous), `ADDW` (particle
   anomalous), `AVK` (heat pinch / convective).
3. **Add auxiliary loaders if needed.** If the model
   needs auxiliary data (lookup tables, additional
   parameter validation), follow the existing per-family
   file split — adjacent `trcoef_*.f90` files (e.g.
   `tr/trcoef_neoclassical.f90`,
   `tr/trcoef_resistivity.f90`) are templates.
4. **Update {doc}`appendix-mdlkai`** so users can find
   your new case in the catalogue.

The same dispatch pattern applies to the other selector
axes — `MDLAD` (particle diffusion), `MDLAVK` (thermal
pinch), `MDLETA` (resistivity) — in their respective
`trcoef_*.f90` files. The recipe generalises.

---

## Walkthrough C — Add a new `TrState` field (ABI-impact recipe)

This is the most invasive walkthrough. Adding a field to
`tr_state_t` changes the C ABI, so external binary
consumers may need to be rebuilt or version-checked.

**Recipe (8 steps):**

1. **Compute the quantity.** If the value is not already
   in TRCOMM, add a TRCOMM variable in the appropriate
   `tr/trcomm*.f90` module and assign it in the routine
   where it naturally falls. A new derived diagnostic
   typically goes into `tr/trrslt_globals.f90` or
   `tr/trrslt_print.f90`.
2. **Add the C-side field** in the `tr_state_c` derived
   type at `tr/tr_state.f90:43-67`. Append the
   `REAL(C_DOUBLE)` (or appropriate kind) at the **end**
   of the type so existing field offsets stay stable —
   this minimises the breakage surface for binary
   consumers.
3. **Mirror in `tr/tr_api.h:49-60`** as a matching
   `double` (or correct C type), again at the struct end.
4. **Populate the field inside `tr_api_get_state`.** Three
   blocks exist in `tr/tr_api.f90`:
   - **Zero-init** at `:263-283` (the new field should be
     added there too if it has no sensible compute-time-
     zero baseline).
   - **Scalar copy** at `:299-315` — the AJRFT precedent
     lives here. For a new scalar, follow that pattern.
   - **Per-radius / per-species profile loops** at
     `:321-330` — for a new array field, follow the
     `RN` / `RT` / `AJ` / `QP` loop pattern.
5. **Bump `TR_STATE_ABI_VERSION`** at `tr/tr_api.h:38`.
   The current value is `2`; bump to the next integer
   (currently `3`).
6. **Mirror in the ctypes side** at
   `python/trlib/_ffi.py:94-120` — append a tuple to
   `TrStateC._fields_`. Use the same field order as the
   BIND-C struct so the two layouts stay byte-compatible.
7. **Surface in the Python `TrState` dataclass** at
   `python/trlib/state.py`. Two cases:
   - *Scalar field*: add the field name to the
     `SCALAR_FIELDS` list (`python/trlib/state.py:22-28`).
     Inside `from_c` (which starts at `:74`), the scalar
     dict-comprehension at `:87` walks `SCALAR_FIELDS` and
     populates `state.scalars["YOUR_FIELD"]` automatically;
     the dimension dict-comprehension at `:81-84` is a
     separate stage that handles `nrmax` / `nsmax`. The
     dataclass construction at `:92-100` returns the
     assembled `TrState`. The new field becomes
     accessible as `state.scalars["YOUR_FIELD"]` without
     further code changes.
   - *Array / profile field* (1-D or 2-D, indexed by
     `nrmax` or `nrmax × nsmax`): add a top-level
     attribute on the `TrState` dataclass and the
     corresponding `from_c` parser line by hand,
     mirroring how `AJ` / `RN` / `RT` are handled.
8. **Update {doc}`state`** with the new attribute or
   scalar key.

### Trap: Fortran/C array-order mirroring (2-D fields)

Fortran is column-major and C is row-major. The existing
`RN` / `RT` fields handle this by **transposing** the
index order between the Fortran declaration and the C
declaration:

- Fortran: `RN(TR_MAX_NSMAX, TR_MAX_NRMAX)` at
  `tr/tr_state.f90:60-61`.
- C: `RN[TR_MAX_NRMAX][TR_MAX_NSMAX]` at
  `tr/tr_api.h:53-54`.
- ctypes mirror at `python/trlib/_ffi.py:112-113` follows
  the C layout.

Any new 2-D field must follow the same transposition
pattern or the bytes will be reinterpreted incorrectly.

### Test plan

After the 8 steps:

1. `make -C tr libtrapi.so` — rebuild.
2. Smoke-test:
   ```python
   from trlib import Trlib
   with Trlib() as tr:
       state = tr.get_state()
       print(state.scalars["YOUR_FIELD"])  # for scalars
       # or print(state.YOUR_FIELD) for profiles
   ```
3. Run the canonical pytest sweep:
   ```bash
   PYTHONPATH=python python3 -m pytest --forked \
       --timeout=120 --timeout-method=signal \
       python/trlib/tests/
   ```
   to confirm no regression.

### Worked example: AJRFT (L-7b-i)

The L-7b-i PR — `#187`, merged commit `e049a1e4` — is the
canonical worked example. The exact touch points to imitate:

- `tr/tr_state.f90:64-66` — BIND-C field
- `tr/tr_api.h:57-59` — C field
- `python/trlib/_ffi.py:116-119` — ctypes field
- `python/trlib/state.py:27` — scalar registration in
  `SCALAR_FIELDS`

That PR also bumped `TR_STATE_ABI_VERSION` from `1` to `2`,
which is the same step Recipe C step 5 does.

---

## See also

- {doc}`design` — overall Fortran-side architecture and
  build dependencies.
- {doc}`appendix-mdlkai` — the catalogue of existing
  `MDLKAI` cases.
- {doc}`state` — user-facing `TrState` reference.
- {doc}`physics-overview` — the selector landscape
  (`MDLKAI` / `MDLETA` / `MDLAD` / `MDLAVK` /
  `MDLKNC` / `MDNCLS`) at orientation level.
