# Minimal hello-world

```python
from wrxlib import Wrxlib

with Wrxlib() as wrx:
    wrx.set_params(RR=3.0, BB=3.0, NSMAX=1)      # (1) device + 1 species
    wrx.set_param("NRAYMAX", 1)                    # (2) number of rays
    wrx.set_param("RFIN[1]", 170.0e9)              # (3) ray 1: frequency
    wrx.set_param("RPIN[1]", 3.5)                  # (4) ray 1: launch R
    wrx.set_param("ZPIN[1]", 0.0)                  # (5) ray 1: launch Z
    wrx.run(nray_request=1)                         # (6) run beam tracing
    state = wrx.get_state()                         # (7) get the state
print(state.scalars["pwr_tot"])
```

## Line-by-line

- **(1) `set_params`**: device (`RR`, `BB`) + number of species (`NSMAX`).
- **(2) `NRAYMAX`**: number of rays — sets the accuracy of the beam
  approximation.
- **(3)–(5) `*IN[i]`**: initial conditions for the i-th ray (1-origin).
- **(6) `run`**: executes beam tracing. **The argument is an override for
  the maximum step count** (`nstpmax_arg`), but the Python wrapper exposes
  it as `nray_request` (see the note below).
- **(7) `get_state()`**: returns a `WrxState` dataclass. See {doc}`state`
  for details.

```{note}
About the argument name of `wrx.run()`: the internal symbol is
`nstpmax_arg`, but the MCP/Python wrapper exposes it as **`nray_request`**
(for API compatibility with `wr`). Check the corresponding code if you
need to confirm the exact behaviour.
```

## Expected output

```
1.5e-02
```

## Practical differences from `wr`

A side-by-side comparison with `wr` for the same launch conditions:

| | `wr` (geometric optics) | `wrx` (beam tracing) |
|---|---|---|
| Number of rays needed | many (10–50 to approximate a beam) | few (1 ray suffices) |
| Beam curvature & width | approximated as separate rays | **analytic, on a single ray** |
| Compute cost (1 ray) | low | high |
| Compute cost (same accuracy) | high (many rays needed) | low |
| Accuracy on focused beams | poor | **excellent** |

For ECRH and LHRD simulations that involve focused beams, `wrx` is
recommended.
