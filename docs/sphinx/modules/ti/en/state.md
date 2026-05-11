# Output Parameters and Physical Quantities (`TiState`)

`ti.get_state()` returns a `TiState` dataclass — the complete list of
quantities you can read as the simulation result. Its fields correspond
to the `ti_state_t` C struct in `ti/ti_api.h`.

## Dimension fields

| Field | Meaning |
|---|---|
| `state.nt`      | Time-step counter |
| `state.nrmax`   | Active radial-point count |
| `state.nsa_max` | Number of active species (those that actually have profile equations) |
| `state.nsmax`   | Number of species in TICOMM (same as `NSMAX`) |

```{note}
The difference between `nsa_max` (active) and `nsmax`: from the
`NSMAX` species in TICOMM, `ti` extracts only the "active species"
that actually have profile equations, and uses that count to size
the profile arrays. Generally `nsa_max ≤ nsmax`.
```

## Scalars (`state.scalars` and `state.scalars_int`)

Unlike `tr`, `ti` returns **2 floating-point scalars and 2 integer
counters**. The emphasis is on convergence diagnostics rather than
physical performance metrics.

### `state.scalars` (floats, 2 entries)

| Key | Unit | Meaning |
|---|---|---|
| `T`                 | s | Simulation time |
| `residual_loop_max` | — | Maximum iteration residual (convergence diagnostic) |

### `state.scalars_int` (integer counters, 2 entries)

| Key | Meaning |
|---|---|
| `icount_loop_max` | Actual outer iteration count |
| `icount_mat_max`  | Actual matrix-solver iteration count |

A standard convergence check is to verify that `residual_loop_max`
falls below `EPSLOOP`.

```python
state.scalars["T"]                          # current time
state.scalars["residual_loop_max"]          # residual
state.scalars_int["icount_loop_max"]        # iteration count
```

```{important}
Plasma performance metrics like `WPT` and `BETAN` (which `tr`
provides) are **not** included in `TiState`. In `ti`, you are expected
to compute these on the user side by integrating the profiles after
the run (this may be added to the API in the future).
```

## Profile quantities (radial profiles)

`ti` returns **8** profile fields, more than `tr`:

```python
state.RNA[nr][nsa]    # density [10^20 m^-3] — active species
state.RTA[nr][nsa]    # temperature [keV] — active species
state.RUA[nr][nsa]    # toroidal flow velocity [m/s] — active species
state.RBP[nr]         # poloidal magnetic field [T]
state.RQP[nr]         # safety factor profile
state.RJP[nr]         # current density profile [MA/m^2]
state.ZEFF[nr]        # effective charge profile
state.BETA[nr]        # β profile
```

`RNA` / `RTA` / `RUA` are indexed by **active species** with extent
`nsa_max`. Indices are 0-origin (Python convention).

## Helper methods

```python
state.to_dict()       # JSON-ready dict, compatible with the Phase 0 baseline
                      # ("scalars" + "scalars_int" + profiles)
```

For the full attribute list see the `TiState` autodoc in
{doc}`api-reference`.

## Differences from `tr`'s `TrState`

| | `TrState` (tr) | `TiState` (ti) |
|---|---|---|
| **Scalar count** | 13 (`T`, `WPT`, `BETAN`, …) | 2 (`T`, residual) + 2 integer counters |
| **Performance metrics** | included (`BETAN`, `TAUE`, …) | **not included** (computed on the user side) |
| **Profile count** | 4 (`RN`, `RT`, `AJ`, `QP`) | 8 (`RNA`, `RTA`, `RUA`, `RBP`, `RQP`, `RJP`, `ZEFF`, `BETA`) |
| **Species axis** | `NSMAX` (all species in `tr`) | `nsa_max` (active species) |
| **Convergence diagnostic** | none | `residual_loop_max`, `icount_*` |

## Computing performance metrics — example

Since `ti` does not return `BETAN` or `TAUE` directly, compute them
from the profiles:

```python
import numpy as np

state = ti.get_state()
RA = ti_input["RA"]      # minor radius (the value the user set)
BB = ti_input["BB"]
RIP = ti_input["RIP"]

# Volume-averaged β (approximation)
beta_avg = np.mean(state.BETA[:state.nrmax])

# Normalized β (Troyon)
betan = beta_avg * 100 / (RIP / (RA * BB))

print(f"<β> = {beta_avg:.4f}, βN = {betan:.2f}")
```
