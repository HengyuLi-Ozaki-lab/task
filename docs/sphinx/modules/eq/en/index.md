# `eq` — MHD Equilibrium

```{admonition} What you'll learn
:class: tip

How to call TASK/EQ (the **MHD equilibrium** solver: takes EQDSK-format
equilibrium data or analytic profiles and computes ψ surfaces and
derived quantities) from Python via the `eqlib` wrapper. Unlike `tr`,
`eq` is a **non-time-stepping** module — `run()` takes a `mode`
(operating-mode) argument. It also exports a **6th** C ABI function
`eq_set_param_str` dedicated to string parameters such as `KNAMEQ`.
```

## Overview — what `eq` does

**TASK/EQ** solves the **MHD equilibrium** of a tokamak. It exposes
**two entry points**:

- **`run(mode=0)`** — analytic Grad-Shafranov solve (`EQCALC` +
  `EQCALQ`). Give it pressure-profile coefficients (`PP*`),
  current-profile coefficients (`PJ*`), and $F(\psi)$ coefficients
  (`FF*`), and it solves the equilibrium analytically. Used with
  `MODELG=2` (the default). No file required.
- **`run(mode=1)`** — load an EQDSK-format (G-EQDSK) equilibrium data
  file (`equnit::eq_load`). Requires `MODELG ∈ {3, 5, 8}` plus the
  filename in `KNAMEQ`.

Both produce, as scalar outputs, the magnetic-axis position (`raxis`,
`zaxis`), axis safety factor (`qaxis`), surface safety factor
(`qsurf`), plasma $\beta$ (`betat`, `betap`), plasma volume (`pvol`),
together with R-Z grids and ψ-surface profiles (`psips`, `ppps`,
`ttps`, `qqps`).

```{note}
PR #164 / #165 completed the library, Python wrapper, and `validate()`
API stack, passing the L-6 equivalence gate at 1e-10. The `mode=0`
(analytic) path corresponds to the `R` (Run) command of the legacy
`eqx2` CLI and was restored as part of the library-isation effort.
```

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

If you are new to this module, the recommended order is:

1. {doc}`build` — build the shared library so that `import eqlib` works
2. {doc}`hello-world` — minimal examples for both the analytic mode (`mode=0`) and the EQDSK mode (`mode=1`)
3. {doc}`parameters` — the registered input parameters (full list)
4. {doc}`parameter-setting` — four ways to set parameters (scalar / array / **string** / `validate`)
5. {doc}`state` — full list of output parameters and physical quantities returned by `eq.get_state()`
6. {doc}`context-manager` — what the `with` statement does and the pitfalls
7. {doc}`quickstart` — runnable notebook walking through the full flow

When stuck, see {doc}`faq`. The full API spec is in {doc}`api-reference`.
For input ↔ output relationships, see {doc}`appendix-sensitivity`.

## Differences from `tr` (summary)

| | `tr` (transport) | `eq` (equilibrium) |
|---|---|---|
| **Time evolution** | yes (`run(ntmax)`) | none (`run(mode)`) |
| **C ABI functions** | 5 + `validate` | **6** + `validate` |
| **`set_param_str`** | (added in PR #172) | required from the very start |
| **Required parameters** | `KNAMEQ` (when `MODELG=3,5,7,8`) | `KNAMEQ` (when `MODELG=3,5,8`) |
| **Representative outputs** | `T`, `WPT`, `BETAN`, profiles[nrmax][nsmax] | `raxis`, `qaxis`, `betat`, profiles[npsmax] |
