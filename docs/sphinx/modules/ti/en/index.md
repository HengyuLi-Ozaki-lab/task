# `ti` — Transport-Integrated

```{admonition} What you'll learn
:class: tip

How to call TASK/TI (the **transport-integrated** module: transport +
auxiliary physics — NBI, EC, LH, IC, fusion, impurities, neoclassical
— all integrated together) from Python via `tilib`. We cover building
the shared library, the minimal hello-world, the 77 registered
parameters and the 18+ `MODEL_*` switches, the FAQ, and the tests.
```

## What `ti` does

**TASK/TI** performs **time-evolving 1-D integrated plasma simulations**
of tokamaks. It extends `tr` (pure transport) by integrating the
following:

- **Transport**: turbulent + neoclassical (`MODEL_KAI`, `MODEL_NC`)
- **Heating / current drive**: NBI, ECRF, LHRF, ICRF (`MODEL_NB`,
  `MODEL_EC`, `MODEL_LH`, `MODEL_IC`, `MODEL_CD`)
- **Particle sources**: fueling, pellets, wall/SOL (`MODEL_PSC`,
  `MODEL_PEL`)
- **Fusion**: DT/DHe³ reactions + α heating (`MODEL_NF`)
- **Synchrotron radiation**: (`MODEL_SYNC`)
- **Impurities**: multi-charge-state model (`ID_NS`, `NZMIN_NS`,
  `NZMAX_NS` arrays)

Representative output quantities:

- `RNA[nr][nsa]`, `RTA[nr][nsa]` — density and temperature profiles per active species
- `RUA[nr][nsa]` — toroidal flow velocity profile
- `RBP[nr]`, `RQP[nr]`, `RJP[nr]` — poloidal magnetic field / safety factor / current
- `ZEFF[nr]`, `BETA[nr]` — effective charge and β profiles
- Scalars: `T` (time), iteration residuals and counters

## User guide

```{toctree}
:maxdepth: 1

build
hello-world
parameters
parameter-setting
state
context-manager
faq
```

## Reference

```{toctree}
:maxdepth: 1

quickstart
api-reference
```

## Internals

```{toctree}
:maxdepth: 1

design
mcp
testing
```

## Appendix

```{toctree}
:maxdepth: 1

appendix-sensitivity
```

## Suggested reading order

If this is your first encounter with `ti`, the recommended path is:

1. {doc}`build` — build the shared library so `import tilib` works
2. {doc}`hello-world` — the 5-line minimum example that advances a plasma
3. {doc}`parameters` — the 77 parameters and 18+ `MODEL_*` switches
4. {doc}`parameter-setting` — the ways to set parameters
5. {doc}`state` — the outputs you can read from `ti.get_state()` (8 profile fields)
6. {doc}`context-manager` — what `with` means and the gotchas around it
7. {doc}`quickstart` — an executable notebook that walks through the whole flow

When stuck, see {doc}`faq`. The full API spec is at {doc}`api-reference`.
For the input ↔ output correspondence, see {doc}`appendix-sensitivity`.

## Differences from `tr` (summary)

| | `tr` (pure transport) | `ti` (integrated transport) |
|---|---|---|
| **Physics scope** | Simple 1-D transport | Transport + auxiliary physics integrated |
| **C ABI** | 5 + `set_param_str` + `validate` | 5 (no extensions) |
| **Registered parameters** | ~30 | **77** |
| **`MODEL_*` switches** | ~10 | **18+** |
| **Output scalars** | 13 (`BETAN`, `TAUE`, …) | 2 + 2 integers (mainly convergence diagnostics) |
| **Profiles** | 4 (`RN`, `RT`, `AJ`, `QP`) | 8 (`RNA`, `RTA`, `RUA`, `RBP`, `RQP`, `RJP`, `ZEFF`, `BETA`) |
| **Species axis** | `NSMAX` | active `nsa_max` |
| **Typical use** | Transport-model benchmark comparisons | Experimental-reproduction simulations |
