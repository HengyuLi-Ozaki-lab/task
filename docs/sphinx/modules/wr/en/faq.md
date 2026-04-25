# FAQ — `wr` specifics

## Q1. What does the `wr` module do?

`wr` (Wave Ray) is a **geometric-optics ray-tracing** solver. It
integrates the propagation of an electromagnetic (RF) wave in a plasma
along the ray equation (Hamiltonian form) determined by the
refractive-index tensor.

Typical applications:

- **ECRH/ECCD** (electron-cyclotron resonance heating / current drive)
  power-deposition position
- **LH** (lower-hybrid) power-absorption analysis
- **NBI** neutralisation + ionisation processes
- Other RF heating schemes such as **fast wave / Alfvén wave**

## Q2. How does it differ from `tr` / `ti` / `fp`?

| | `tr`/`ti` | `fp` | `wr` |
|---|---|---|---|
| **Equation** | fluid + auxiliary physics | Fokker-Planck (5D) | **ray equation** |
| **Time evolution** | yes | yes | **no** (spatial integration) |
| **`run` argument** | `ntmax` | `ntmax` | **`nray_request`** |
| **Output** | profiles | moments | ray trajectories + absorption locations |

`wr` is the module that, **given a fixed incident wave, computes where
it gets absorbed**. It does not advance in time. `run(nray_request=N)`
traces N independent rays.

## Q3. What does `nray_request` mean?

`run(nray_request=N)` requests **N rays**. The configured `NRAYMAX`
parameter is the upper bound, so the actual count is
`min(nray_request, NRAYMAX)`.

If `nray_request=0` is given, the value of `NRAYMAX` is used.

## Q4. A ray stops part-way

Possibilities:

- It hit `NSTPMAX` (maximum step count) — increase via
  `set_param("NSTPMAX", 50000)`
- It hit `UUMIN` (minimum residual-power threshold) — lower `UUMIN`
- It left the computational domain (`Rmax_wr`, `Rmin_wr`, `Zmax_wr`,
  `Zmin_wr`)
- It reached the plasma cutoff (a density at which the wave can no
  longer propagate)

`state.nstp_end[i]` gives the terminating step number of each ray.

## Q5. The peak power is zero

Possibly the ray simply passed through a region where it is not
absorbed. Check:

- Does the frequency `RF` match the resonance condition (e.g. the
  electron-cyclotron frequency for ECRH)?
- Are the launch angles `RNZI`, `RNPHII` reasonable?
- Is `MODELP` (wave-model selector) physically appropriate?

## Q6. Results don't match the `wrx2` (CLI) version

Run the regression test `wrlib_equivalence`:

```bash
bash test_run/run_tests.sh wrlib_equivalence
```

The tolerance is `1e-10`. If the deviation exceeds it, look for missing
parameter registrations.

## Q7. Should I use `wr` or `wrx`?

- **`wr` (geometric optics)**: fast, simple ray tracing. Beam spread is
  approximated with `NRAYMAX` rays. Sufficient in most cases.
- **`wrx` (extended)**: beam tracing — directly models the finite beam
  width. Use it when EC or LH analyses require focused-beam treatment.
  Computationally more expensive.

If unsure, **start with `wr`**; consider `wrx` only if the result is too
coarse.

## Q8. Do I need NumPy?

**No.** `WrState` is built from Python `list`s. If you want NumPy,
convert with `import numpy as np; np.array(state.pwr_nrs)`.
