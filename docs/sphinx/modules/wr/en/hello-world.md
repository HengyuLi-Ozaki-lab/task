# Minimal hello-world

```python
from wrlib import Wrlib

with Wrlib() as wr:
    wr.set_params(RR=3.0, BB=3.0, NSMAX=1)        # (1) device + 1 species
    wr.set_param("RF", 170.0e9)                    # (2) frequency 170 GHz
    wr.set_param("RPI", 3.5)                       # (3) launch point R [m]
    wr.set_param("ZPI", 0.0)                       # (4) launch point Z [m]
    wr.set_param("RKR0", 1.0)                      # (5) initial k_R
    wr.run(nray_request=1)                          # (6) trace one ray
    state = wr.get_state()                          # (7) read state
print(state.scalars["pwrmax_rs"], state.nraymax)
```

## Line-by-line explanation

- **(1) `set_params`**: device parameters (`RR`, `BB`) and number of
  species (`NSMAX`).
- **(2) `RF`**: wave frequency [Hz]. ~100–200 GHz for ECRH/ECCD,
  ~1–10 GHz for LH.
- **(3)–(4) `RPI`, `ZPI`**: launch position of the ray (R, Z [m]).
- **(5) `RKR0`**: initial wavenumber $k_R$ (in normalised form).
- **(6) `run(nray_request=1)`**: **trace one ray**. Unlike the `ntmax`
  argument (time steps) of `tr` / `ti` / `fp`, **`nray_request` is the
  number of rays to trace**.
- **(7) `get_state()`**: copies the result into a `WrState` dataclass.
  `pwrmax_rs` is the peak power intensity along the r-coordinate.

## Expected output

```
0.85  1
```

## What makes `wr` distinctive

Unlike `tr` / `ti` / `fp`, `wr` **does not advance in time**; it performs
**spatial ray tracing**.

- Input: plasma equilibrium + incident wave (frequency, position,
  wave-vector)
- Compute: propagate the ray geometric-optically and find the
  power-absorption location
- Output: peak-power location and value, ray trajectories, radial
  profiles

Main applications:

- **ECRH/ECCD** (electron-cyclotron heating / current drive) ray tracing
- **LH** (lower-hybrid) power-deposition analysis
- Optimisation of heating parameters (frequency, launch angle)

Running multiple rays at once (`NRAYMAX > 1`) lets you approximate
**beam** effects (for more accurate beam tracing see the `wrx` module).
