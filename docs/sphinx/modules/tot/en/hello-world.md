# Minimal hello-world

```python
from totlib import Tot

with Tot() as tot:
    # Specify sub-module parameters using prefixes
    tot.set_param("eq:RR", 6.5)              # eq module's RR
    tot.set_param("eq:BB", 5.3)              # eq's BB
    tot.set_param("tr:NSMAX", 2)             # tr's species count
    tot.set_param("tr:NTMAX", 100)           # tr's number of timesteps
    tot.run(ntmax=10)                         # 10-step integrated simulation
    state = tot.get_state()                   # retrieve integrated state
print(state.scalars["T"], state.scalars["BETAN"])
```

## Line-by-line walkthrough

`tot` is the **orchestrator**, which runs the eq / tr / ti / fp / wr / wrx
modules in an integrated way. You attach a **`<module>:` prefix** to each
parameter name to indicate which sub-module it belongs to:

- `eq:RR` → eq module's `RR`
- `tr:NSMAX` → tr module's `NSMAX`
- `fp:NPMAX` → fp module's `NPMAX`
- and so on

## Expected output

```
0.1  0.42
```

## Sub-modules orchestrated by tot

`tot` calls the following sub-modules sequentially or in parallel:

| Sub-module | Prefix | Role |
|---|---|---|
| `eq`  | `eq:`  | Solves the MHD equilibrium and provides flux-surface info |
| `tr`  | `tr:`  | 1D transport calculation |
| `ti`  | `ti:`  | Integrated transport (alternative) |
| `fp`  | `fp:`  | Fokker–Planck (fast-ion distribution) |
| `wr`  | `wr:`  | RF ray tracing |
| `wrx` | `wrx:` | RF beam tracing |

For example, an "equilibrium + transport + ECRH heating" simulation:

```python
tot.set_param("eq:RR", 6.5)         # device for the equilibrium
tot.set_param("tr:NSMAX", 2)        # transport species count
tot.set_param("wr:RF", 170e9)       # ECRH frequency
tot.set_param("wr:RPI", 8.5)        # injection point
tot.run(ntmax=100)                   # time-evolve everything coupled
```

## Differences from stand-alone modules

| | Stand-alone module (e.g. `Trlib`) | `tot` |
|---|---|---|
| Parameter name | `RR`, `BB`, ... | `tr:RR`, `tr:BB`, ... |
| Equilibrium data | from outside via `pl_*` | obtained dynamically by running `eq` internally |
| RF heating consistency | profiles from a separate run via `set_param` | obtained dynamically by running `wr`/`wrx` |
| Automatic coupling | none | yes |

## Why use `tot`

Reasons to use `tot`:

- **Self-consistent simulation**: equilibrium (`eq`) → transport
  (`tr`/`ti`) → Fokker–Planck (`fp`) → RF (`wr`/`wrx`) all computed on
  the **same plasma state**
- **Self-consistent time evolution**: each sub-module updates while
  seeing the latest results of the others
- **No manual coupling code**: would normally require a program that
  calls `Trlib`, `Eq`, `Wrlib`, etc. in turn — `tot` does it in one shot
