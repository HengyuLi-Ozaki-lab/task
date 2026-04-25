# `wrx` — Wave Ray Tracing (Extended)

```{admonition} What you'll learn
:class: tip

How to call TASK/WRX (a **beam tracing** solver: an extended version of `wr`
that gives each ray a beam shape — curvature and width — and develops the
propagation of focused beams analytically) from Python via `wrxlib`. We cover
building the shared library, a minimal hello-world, the 70 registered
parameters, the beam-shape inputs that are unique to beam tracing, the
species-resolved absorption outputs, and the 4-layer test suite.
```

## Overview — what `wrx` does

**TASK/WRX** is a **beam tracing** solver that extends `wr` (geometric-optics
ray tracing) by tracking a **beam shape** (curvature tensor + width) along
each ray.

How it differs from `wr`:

| | `wr` (geometric optics) | `wrx` (beam tracing) |
|---|---|---|
| Ray width | none (pencil beam) | **yes** (Gaussian) |
| Beam-spread representation | approximated by many rays (NRAYMAX=10–50) | **analytic expansion with a single ray** |
| Compute cost (same accuracy) | high | **low** |
| Accuracy on focused beams | poor | **excellent** |

Typical use cases:

- Focused ECRH beams from launchers like the **ITER Upper/Equatorial Launcher**
- Beam propagation from **LH coupler** outputs
- Focal-point tracking and defocus analysis of **gyrotron beams**

Key quantities you obtain:

- Scalar: `pwr_tot` (total absorbed power summed over all rays)
- Per-ray: `nstp_end[i]`, `pwr_nray[i]`
- Per-species: `pwr_nsa[isa]` (which species absorbed how much)
- Profiles: `pos_nrs[k]`, `pos_nrl[k]`

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
2. {doc}`hello-world` — beam tracing with a single ray
3. {doc}`parameters` — 70 parameters (including beam-shape `RCURVAIN`/`RBRADAIN`)
4. {doc}`parameter-setting` — even a single ray uses the array form
5. {doc}`state` — `pwr_tot` + `pwr_nray` + `pwr_nsa`
6. {doc}`context-manager` — common `with` pitfalls

When in trouble, see {doc}`faq`. The complete API specification lives in
{doc}`api-reference`. For input ↔ output correspondence, see
{doc}`appendix-sensitivity`.

## When to use `wr` vs `wrx`

| Goal | Recommended |
|---|---|
| Quick estimate (peak position) | `wr` |
| Accurate absorption profile for a focused beam | **`wrx`** |
| Beam approximation with many rays | `wr` (NRAYMAX=10–50) |
| Beam tracking with a single ray | **`wrx`** (NRAYMAX=1) |
| Species-resolved absorption (`pwr_nsa`) | **`wrx`** (`wr` does not have this) |

If unsure, **start with `wr`** — and only consider `wrx` when the result is
too coarse.
