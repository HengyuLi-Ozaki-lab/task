# `wr` — Wave Ray Tracing

```{admonition} What you'll learn
:class: tip

How to call TASK/WR (a **geometric-optics ray-tracing** solver for RF
heating and current-drive analysis such as ECRH/ECCD/LH) from Python via
`wrlib`. We cover building the shared library, the minimal hello-world,
the 103 registered parameters (the most of any module), ray-trajectory
and absorption-profile output, and the four-layer test suite.
```

## Overview — what `wr` does

**TASK/WR** is a solver for the **propagation of electromagnetic (RF)
waves** in a tokamak plasma. It integrates the ray equation in
Hamiltonian form using the refractive-index tensor of the plasma to
determine **where the wave is absorbed**.

Unlike `tr` / `ti` / `fp`, `wr` **does not advance in time**; it
**integrates in space**:

- Input: plasma equilibrium + incident-wave conditions (frequency,
  position, wave-vector, beam shape)
- Compute: integrate the ray equation up to `NSTPMAX` steps
- Output: ray trajectories + radial profile of absorbed power

Typical applications:

- **ECRH/ECCD** (electron-cyclotron resonance heating / current drive)
- **LH** (lower-hybrid) power-deposition analysis
- Other RF heating schemes such as **fast wave / Alfvén wave**

Main output quantities:

- Scalars (4): `pos_pwrmax_rs`, `pwrmax_rs`, `pos_pwrmax_rl`, `pwrmax_rl`
- Per ray: `nstp_end[i]`, `pos_pwrmax_*_nray[i]`, `pwrmax_*_nray[i]`,
  `rays_end[i]`
- Profiles: `pos_nrs[k]`, `pwr_nrs[k]`, `pos_nrl[k]`, `pwr_nrl[k]`

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

1. {doc}`build` — build the shared library
2. {doc}`hello-world` — five lines plus one ray trace
3. {doc}`parameters` — the full list of 103 parameters
4. {doc}`parameter-setting` — single-ray vs. multi-ray configuration
5. {doc}`state` — ray trajectories and absorption profiles
6. {doc}`context-manager` — meaning and pitfalls of the `with` statement

When stuck, see {doc}`faq`. The full API specification is in
{doc}`api-reference`. The input ↔ output correspondence is summarised
in {doc}`appendix-sensitivity`.

## Differences from `tr` / `ti` / `fp` (summary)

| | `tr`/`ti` | `fp` | `wr` |
|---|---|---|---|
| **Equation** | fluid + auxiliary physics | Fokker-Planck (5D) | **ray equation** |
| **Time evolution** | yes | yes | **no** (spatial integration) |
| **`run` argument** | `ntmax` | `ntmax` | **`nray_request`** |
| **Output** | profiles | moments | **ray trajectories + absorption locations** |
| **Registered parameters** | ~30/77 | 55 | **103** |

## Relationship between `wr` and `wrx`

`wrx` is an **extended version** of `wr` that adds beam-tracing options.

- `wr`: pencil beams (geometric optics). Beam spread is approximated by
  `NRAYMAX` rays
- `wrx`: each ray carries beam-shape information (curvature, width) that
  is expanded analytically

If unsure, **start with `wr`**; switch to `wrx` only if the result is
too coarse ({doc}`faq` Q7).
