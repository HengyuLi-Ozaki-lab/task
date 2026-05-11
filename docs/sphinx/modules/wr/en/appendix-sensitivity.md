# Appendix: Input ↔ Output Correspondence

This appendix summarises the input → output relationships of `wr`,
limited to **(1) algebraic relationships** and **(2) physical scalings**.

```{admonition} Legend
:class: note

- **↑**: increasing the input increases the output
- **↓**: increasing the input decreases the output
- **=**: equal to / directly determined by the input
- **~**: approximately holds (higher-order effects can flip it)
```

## 1. Algebraic / direct relationships

| Input | Main output affected | Relation | Notes |
|---|---|---|---|
| `NRAYMAX` | `state.nraymax` | ≤ | the actual number traced is `min(NRAYMAX, nray_request)` |
| `NRSMAX` | `state.nrsmax` | = | radial-profile resolution |
| `NRLMAX` | `state.nrlmax` | = | major-radius profile resolution |
| `NSTPMAX` | ray-trajectory buffer size | ∝ | memory consumption |
| `MODELG = 2` | `KNAMEQ` not required | — | analytic toroidal |
| `MODELG ∈ {3, 5, 8}` | `KNAMEQ` required | — | reads EQDSK etc. |
| `UUMIN` | ray stop condition | — | residual-power threshold |

## 2. Known physical scaling trends

### 2.1 Device / geometry (`RR`, `RA`, `BB`, `RIP`)

| Input | Main output affected | Direction | Physical basis |
|---|---|---|---|
| `BB` ↑ | `state.scalars["pos_pwrmax_rs"]` (ECRH) | ~ | cyclotron resonance position $\omega_{ce} \propto B$ |
| `RR` ↑ | ray-trajectory length | ↑ | proportional to device size |
| `RIP` ↑ | ray trajectory (via poloidal field) | ~ | plasma current shapes the path |

### 2.2 Wave conditions (`RF`, `RPI`, `RNZI`, `RKR0`)

| Input | Main output affected | Direction | Physical basis |
|---|---|---|---|
| `RF` ↑ (higher frequency) | cyclotron resonance position | ~ | $\omega_{ce}(R) = eB(R)/m \propto B/R$, intersection moves outward |
| `RPI` ↑ (outboard launch) | ray path length | ↑ | longer detour |
| `RNZI` ↑ (large $N_\parallel$) | LH drive efficiency (LH case) | ~ | LH resonance condition |
| sign of `RKR0` | ray direction | — | inward / outward |

### 2.3 Profiles (`PN[i]`, `PT[i]`)

| Input | Main output affected | Direction | Physical basis |
|---|---|---|---|
| `PN[i]` ↑ (density) | reaching cutoff | ↑ | plasma frequency $\omega_p \propto \sqrt{n}$ |
| `PN[i]` ↑ | ray-refraction angle | ↑ | refractive-index change |
| `PT[i]` ↑ (temperature) | cyclotron-damping width | ↑ | Doppler broadening |

### 2.4 Numerics (`NSTPMAX`, `DELS`, `EPSRAY`)

| Input | Main output affected | Direction | Physical basis |
|---|---|---|---|
| `NSTPMAX` ↑ | ray-completion rate | ↑ | longer rays can be traced |
| `DELS` ↓ (finer step) | trajectory accuracy | ↑ | higher integration accuracy |
| `EPSRAY` ↓ | trajectory accuracy | ↑ | tighter convergence |
| `UUMIN` ↓ | ray stop position | deeper | track to lower power |

### 2.5 Beam shape (`RCURVA*`, `RBRADA*`)

| Input | Main output affected | Direction | Physical basis |
|---|---|---|---|
| `RBRADA` ↑ (beam width) | power-deposition profile | broadens | Gaussian beam approximation |
| sign of `RCURVA` | beam focusing / divergence | — | convex / concave-lens behaviour |

### 2.6 Multi-ray (`NRAYMAX`)

| Input | Main output affected | Direction | Physical basis |
|---|---|---|---|
| `NRAYMAX` ↑ (more rays) | profile resolution | ↑ | statistical smoothing |
| `NRAYMAX` ↑ | computation time | ↑↑ | O(NSTPMAX) per ray |
| Z-spread of `*IN` arrays | beam-spread reproduction | — | physical beam-width simulation |

## How to use this table

Rules of thumb for tuning towards a desired output:

- **Move ECRH deposition toward the centre** → set `RF` to the frequency
  matching the central B-field (e.g. BB=5.3T → $\omega_{ce} \approx 148$
  GHz, second harmonic 296 GHz)
- **Maximise LH current-drive efficiency** → sweep `RNZI` over 1.5–2.5
  and compare the `pwrmax_rl` profile
- **Reproduce beam divergence** → use `NRAYMAX=10` or more and spread
  the `*IN` arrays in Z
- **Speed up the run** → reduce `NRAYMAX`, reduce `NSTPMAX`, loosen
  `EPSRAY`

For quantitative sensitivity, run a simulation — see the `wrlib_sweep`
framework.
