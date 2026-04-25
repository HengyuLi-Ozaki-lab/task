# FAQ — `fp` specifics

## Q1. What does the `fp` module do?

`fp` is a **Fokker-Planck equation solver** that evolves the particle
distribution function $f(r, p, \theta, t)$ in time. Unlike the fluid
equations of `tr` / `ti` (temperature/density evolution), it works
directly in **5D phase space** (1D position × 1D momentum × 1D pitch
angle × species × time).

Typical applications:

- Distribution-function calculation for **NBI-driven fast ions** (the
  non-thermal tails that temperature moments alone miss)
- Electron distribution distortion under **wave drive** (LH, ECCD)
- Slowing-down of **fusion alpha particles**
- Acceleration of **runaway electrons** during disruptions

## Q2. How is this different from computing temperature in `tr`/`ti`?

`tr`/`ti` **assume a Maxwellian** distribution function and evolve only
its moments (temperature and density). When **non-thermal
distributions** matter — fast ions, wave drive — the Maxwell assumption
breaks down and `fp` becomes necessary.

Concretely:

| Situation | tr/ti is OK | `fp` is required |
|---|---|---|
| Standard transport (Te, Ti profiles) | ✓ | — |
| Order-of-magnitude NBI heating | (approximate) ✓ | More accurate |
| ECCD / LHCD current-drive efficiency | ✗ | ✓ |
| Detailed shape of the fast-ion distribution | ✗ | ✓ |
| Runaway-electron analysis | ✗ | ✓ |

## Q3. How do I choose `NPMAX`, `NTHMAX`?

These are the resolution in momentum space and pitch-angle space. The
defaults are roughly `NPMAX=50` and `NTHMAX=25`.

- **Too small** → sharp structures in the distribution (beam peaks,
  resonance peaks) cannot be resolved.
- **Too large** → memory consumption (× NPMAX × NTHMAX × NRMAX × NSAMAX)
  and run time blow up.

Rule of thumb: for NBI analysis, `NPMAX ≥ 80` and `NTHMAX ≥ 50` are
recommended.

## Q4. Difference between `NSMAX`, `NSAMAX`, `NSBMAX`

| Name | Meaning |
|---|---|
| `NSMAX` | Total number of species (same as TR/TI) |
| `NSAMAX` | **active species** — number of species whose distribution functions are solved |
| `NSBMAX` | **bulk species** — number of species used as collision targets |

For instance, `NSAMAX = 1` for solving electrons only with `NSBMAX = 2`
ions as collision partners.

## Q5. The `MODELE` / `MODELS` and similar switches

`MODELE` (energy operator):

- 1 (default): linear Fokker-Planck
- 2: relativistic Fokker-Planck

`MODELS` (source operator):

- 0: no particle source
- 1: NBI source (requires `MODEL_NBI=1`)
- Other

For details see the comment block in `fp/fpinit.f90`.

## Q6. The result does not match the `fpx2` (CLI) output

Run the regression test `fplib_equivalence`:

```bash
bash test_run/run_tests.sh fplib_equivalence
```

The tolerance is `1e-10`. A larger discrepancy probably means a
parameter is missing from the registry.

## Q7. I get a memory error / SIGABRT

The 5D grid is most likely too large. Rough estimate:

```
RAM ≈ NRMAX × NPMAX × NTHMAX × NSAMAX × 8 bytes × (~10 arrays)
```

For `NRMAX=50, NPMAX=100, NTHMAX=50, NSAMAX=2` this is about 40 MB × 10
= 400 MB. On top of that, the `LMAXFP` iteration uses temporary arrays.
Even on a 32 GB machine, `NPMAX=200` is around the practical ceiling.

Allocate at most one `Fplib()` instance per process, and always release
it by leaving the `with` block.
