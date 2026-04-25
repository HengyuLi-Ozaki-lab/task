# Fortran Design

`tot` is the **orchestrator** that bundles the existing eq / tr / ti /
fp / wr / wrx physics kernels into a single library (`libtotapi.so`).
It consists of a thin C-ABI entry layer (`tot_api.f90`), a routing
parameter registry (`tot_param_registry.f90`), and roughly 7
tot-specific `.f90` source files.

## Entry layer (`tot_api.f90`)

There are **6** functions called from C (the same extended set as `eq`
and `fp`).

| C symbol | Fortran side | Role |
|---|---|---|
| `tot_init`           | `tot_api_init`           | Calls `pl_init` → `eq_init` → `tr_init` → `ti_init` → `fp_init` → `wr_init` → `wrx_init` in order |
| `tot_set_param`      | `tot_api_set_param`      | Inspects the prefix and forwards to the appropriate `<mod>_param_set` |
| `tot_set_param_str`  | `tot_api_set_param_str`  | Same as above, for strings |
| `tot_run`            | `tot_api_run`            | `ntmax` time steps, coupling sub-modules |
| `tot_get_state`      | `tot_api_get_state`      | Copies `TrState`-based data + presence flags into the C struct |
| `tot_finalize`       | `tot_api_finalize`       | Finalises in reverse (LIFO) order |

All are declared `BIND(C, NAME="tot_xxx")` so the C ABI symbol names are
fixed.

## Parameter registry (`tot_param_registry.f90`)

This file has a special structure: only **9 prefix CASE entries**.

```fortran
SELECT CASE (prefix)
CASE ("eq")
   ierr = eq_param_set(name_after_colon, value)
CASE ("tr")
   ierr = tr_param_set(name_after_colon, value)
CASE ("ti")
   ierr = ti_param_set(name_after_colon, value)
CASE ("fp")
   ierr = fp_param_set(name_after_colon, value)
CASE ("wrx")
   ierr = wrx_param_set(name_after_colon, value)
CASE ("wr")
   ierr = wr_param_set(name_after_colon, value)
...
END SELECT
```

So `tot` itself **manages no individual parameters** — everything is
delegated to the other modules. This is why it is called an
"orchestrator".

## Coupling mechanism in `tot_run`

`run(ntmax)` **couples each sub-module step by step**. A representative
flow:

1. `eq_run(mode=1)`: solve the equilibrium (from `KNAMEQ`)
2. `eq_get_state` → pass flux-surface info to `tr` (via BPSD)
3. `tr_run(ntmax=1)`: one transport step
4. `tr_get_state` → pass temperature/density profiles to `wr` and `fp`
5. `wr_run` (if RF heating is enabled): ray tracing → absorption profile
6. `wr` results → fed back to `tr` as a heating term
7. `fp_run` (if fast-ion analysis is enabled): Fokker–Planck for the
   distribution function
8. `fp` results → fed back to `tr` as a particle source
9. Advance to the next time step

Data exchange between modules goes through **BPSD** (Plasma Simulation
Database); see {ref}`Common architecture <portal:common-architecture>`.

## Source layout inside the library

There are only ~7 `tot/*.f90` files, because the physics lives in the
other modules.

| Group | Main files | Role |
|---|---|---|
| **API layer** | `tot_api.f90`, `tot_param_registry.f90`, `tot_state.f90` | C-ABI entry + routing |
| **Orchestration** | `totloop.f90` (likely) | Time loop coupling sub-modules |
| **Common module** | `totcomm.f90` (likely) | tot-specific state (presence flags, etc.) |
| **Interactive menu** | `totmenu.f90` (likely) | `tot_x2` CLI only |
| **Regression** | `totregress.f90` (likely) | Phase 0 baseline |
| **Graphics** | `tot_graphics_stubs.f90` | Stubbed out in the library build |

## Memory consumption

`tot` consumes **the sum of all sub-module footprints** plus a small
tot-specific overhead.

```
tot memory ≈ tr + eq + ti + fp + wr + wrx + a few % overhead
```

Increasing `fp:NPMAX` and `fp:NTHMAX` easily puts this over 1 GB —
significantly hungrier than any stand-alone module.

## PIC build dependencies

```
libtotapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a
├── tr/libtrcomm_pic.a
├── ti/libticomm_pic.a
├── fp/libfpcomm_pic.a
├── wr/libwrcomm_pic.a
├── wrx/libwrxcomm_pic.a
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

It depends on **every module**: all of them must finish their PIC
archive before `tot` can be built (see {doc}`build`).

## References

- [`docs/tot-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/tot-library/architecture.md)
- {ref}`Common architecture <portal:common-architecture>`
- `tot/tot_api.h` — C-ABI header
- `tot/tot_api.f90` — Fortran entry side
- `tot/tot_param_registry.f90` — prefix routing
- design pages of the sub-modules
  - `docs/sphinx/modules/tr/en/design.md`
  - `docs/sphinx/modules/eq/en/design.md`
  - `docs/sphinx/modules/fp/en/design.md`
  - `docs/sphinx/modules/wr/en/design.md`
  - etc.
