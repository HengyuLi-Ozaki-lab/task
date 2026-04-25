# Minimal hello-world

```python
from fplib import Fplib

with Fplib() as fp:
    fp.set_params(RR=3.0, BB=3.0, NSMAX=1)        # (1) device + 1 species
    fp.set_param("NPMAX", 50)                       # (2) momentum mesh
    fp.set_param("NTHMAX", 25)                      # (3) pitch-angle mesh
    fp.run(ntmax=5)                                 # (4) advance 5 steps
    state = fp.get_state()                          # (5) fetch state
print(state.timefp, state.nsamax)
```

## Line-by-line

- **(1) `set_params`**: set the geometry (`RR`, `BB`) and the number of
  species (`NSMAX`).
- **(2) `NPMAX`**: number of mesh points in momentum space. Because `fp`
  discretises a 5D space (1D position × 1D momentum × 1D pitch angle ×
  species × time), the momentum and pitch-angle resolution matters.
- **(3) `NTHMAX`**: number of mesh points in pitch-angle space.
- **(4) `run(ntmax=5)`**: advance 5 time steps. The step size is `DELT`
  (the analogue of `DT` in `tr`/`ti`); the default is 0.001 s.
- **(5) `get_state()`**: copy the result into an `FpState` dataclass.

## Expected output

```
0.005  1
```

## What makes `fp` different

Unlike `tr`, `ti`, and `eq`, `fp` **solves directly for the particle
distribution function $f(r, p, \theta)$**.

- The output consists of **moments** (`RNT` = particle-number density,
  `RWT` = energy density, `RTT` = temperature, `RJT` = current density,
  `RPCT` = collisional power, `RPWT` = wave-heating power), not
  integrated quantities such as bulk temperature/density.
- It is used for detailed analysis of fast ions (NBI-driven, fusion-
  produced) and other non-thermal distributions.
- The compute cost is higher than `tr`/`ti` (a 5D grid).
