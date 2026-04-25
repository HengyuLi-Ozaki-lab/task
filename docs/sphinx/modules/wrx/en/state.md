# Output Parameters and Physical Quantities (`WrxState`)

`wrx.get_state()` returns a `WrxState` dataclass — the complete list of
quantities you can retrieve from a beam-tracing run.

## Dimension fields

| Field | Meaning |
|---|---|
| `state.nraymax` | Number of rays actually traced |
| `state.nstpmax` | Effective maximum step count |
| `state.nsamax`  | Number of active species (species included in the calculation) |
| `state.nsmax`   | Total number of species |
| `state.nrsmax`  | Number of minor-radius profile points |
| `state.nrlmax`  | Number of major-radius profile points |
| `state.modelg`  | Geometry model that was used |
| `state.mdlwrq`  | Quality mode that was used |

## Scalar quantities

For `wrx`, `state.scalars` contains **only `pwr_tot`**.

| Key | Unit | Meaning |
|---|---|---|
| `pwr_tot` | — | Total absorbed power summed over all rays (normalized) |

```python
state.scalars["pwr_tot"]   # total absorbed power
```

To compute the absorption fraction relative to the total injected power,
compare this value with each ray's initial power `UUIN[i]`.

## Per-ray outputs

| Field | Type | Meaning |
|---|---|---|
| `state.nstp_end[i]`  | int   | Final step number for ray i |
| `state.pwr_nray[i]`  | float | Absorbed power for ray i |
| `state.pwr_nsa[isa]` | float | Absorbed power for active species isa |

You can read off how much power each ray finally deposited (`pwr_nray`)
and which species absorbed it (`pwr_nsa`) independently.

## Profile quantities

| Field | Type | Meaning |
|---|---|---|
| `state.pos_nrs[k]` | float | Minor-radius sample position k |
| `state.pos_nrl[k]` | float | Major-radius sample position k |

The power-deposition profiles corresponding to `pwr_nrs[]` / `pwr_nrl[]`
in `wr` are implementation-dependent (check `describe_state_schema`).
See {doc}`api-reference` for details.

## Helper methods

```python
state.to_dict()   # JSON-ready dict (baseline-compatible)
```

The `to_dict()` output has a three-tier structure (`arrays`, `arrays2`,
`scalars`) and can be passed straight to `compare_metrics.py`.

## Differences from `wr`'s `WrState`

| | `WrState` (wr) | `WrxState` (wrx) |
|---|---|---|
| **Number of scalars** | 4 (pos/pwr × 2 axes) | **1** (pwr_tot) |
| **Main outputs** | `rs`/`rl` profiles + ray endpoints | per-ray + per-species absorption + profiles |
| **Species-resolved absorption** | none (only `nraymax`) | **`pwr_nsa[]` available** |
| **Beam-shape output** | none | held internally (retrievable for plotting) |

Because `wrx` exposes a species-resolved absorption profile, you can use
it for analyses such as "what fraction of the ECRH power heated electrons
versus what fraction leaked into ions."
