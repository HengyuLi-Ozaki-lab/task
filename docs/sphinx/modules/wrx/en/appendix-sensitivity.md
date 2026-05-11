# Appendix: Input ↔ Output Correspondence

This appendix summarises the input → output relationships in `wrx`. It is
restricted to **(1) algebraic relations** and **(2) physical scalings**.

```{admonition} Legend
:class: note

- **↑**: increasing the input increases the output
- **↓**: increasing the input decreases the output
- **=**: equal to / directly determined by the input
- **~**: approximately holds
```

## 1. Algebraic / direct relations

| Input | Mainly affects | Relation | Notes |
|---|---|---|---|
| `NRAYMAX` | `state.nraymax` | ≤ | Actual ray count |
| `NSTPMAX` | `state.nstpmax` | = | Maximum step count |
| `NRSMAX` | `state.nrsmax` | = | Profile resolution |
| `NSMAX` | `state.nsmax` | = | Number of species |
| `NSAMAX_WR` | `state.nsamax` | = | Active species |
| `MODELG` | `state.modelg` | = | Geometry model used |
| `UUIN[i]` | upper bound of `state.pwr_nray[i]` | ≤ | Absorption ≤ injection |

## 2. Known physical scalings

### 2.1 Device / geometry

| Input | Mainly affects | Direction | Physical reason |
|---|---|---|---|
| `BB` ↑ | ECRH resonance position | ~ | Depends on ω_ce = eB/m |
| `RR` ↑ | Ray path length | ↑ | Proportional to device size |

### 2.2 Beam launch conditions (`RFIN`, `RPIN`, `ZPIN`)

| Input | Mainly affects | Direction | Physical reason |
|---|---|---|---|
| `RFIN[i]` ↑ | Resonance position | ~ | ω_ce(R) crossing |
| `RPIN[i]`, `ZPIN[i]` | Initial ray position | = | Direct launch point |
| `ANGPHIN[i]` ↑ (toroidal angle) | Current-drive efficiency (ECCD) | ↑↓ | Resonance shifts with angle |

### 2.3 Beam shape (`wrx`-specific)

| Input | Mainly affects | Direction | Physical reason |
|---|---|---|---|
| `RBRADAIN[i]` ↑ (wider beam) | Deposition profile | broader | Larger beam cross-section |
| `RBRADAIN[i]` ↑ | Peak value of `pwr_tot` | ↓ | Lower local power density |
| `RCURVAIN[i]` (toward focusing) | Concentration at focus | ↑ | Optical focusing |
| `RCURVAIN[i]` (toward diverging) | Deposition profile | broader | Diverging beam |
| `MODEWIN[i]` (1→2, O→X mode) | Absorption efficiency | ~ | Polarization-dependent resonance strength |

### 2.4 Plasma conditions

| Input | Mainly affects | Direction | Physical reason |
|---|---|---|---|
| `PN[i]` ↑ (density) | Reaching cutoff | ↑ | Higher plasma frequency |
| `PN[i]` ↑ | Ray refraction | ↑ | Refractive-index change |
| `PTPR[i]`, `PTPP[i]` ↑ | Doppler broadening | ↑ | Resonance width grows with temperature |

### 2.5 Species-resolved absorption (`pwr_nsa[]`)

| Input | Mainly affects | Direction | Physical reason |
|---|---|---|---|
| ECRH frequency (150–300 GHz) | `pwr_nsa[electron]` | large | Electron cyclotron resonance |
| LH frequency (1–10 GHz) | `pwr_nsa[electron]` | large | Landau damping (electrons) |
| ICRH frequency (20–80 MHz) | `pwr_nsa[ion]` | large | Ion cyclotron resonance |

### 2.6 Numerical parameters

| Input | Mainly affects | Direction | Physical reason |
|---|---|---|---|
| `NSTPMAX` ↑ | Ray completion rate | ↑ | Can follow longer rays |
| `DELS` ↓ | Integration accuracy | ↑ | Finer steps |
| `EPSRAY` ↓ | Integration accuracy | ↑ | Stricter convergence |
| `UUMIN` ↓ | Following the deposition site farther | ↑ | Tracks weaker power |

## How to use

Tuning guidelines per output goal:

- **Move the focal position** → adjust `RCURVAIN[i]` (curvature)
- **Change the beam cross-section** → set `RBRADAIN[i]`, `RBRADBIN[i]`
  independently for the two axes
- **See the electron/ion absorption split** → choose `MODEWIN`
  (polarization) and `RFIN` (frequency)
- **Computation is slow** → reduce `NSTPMAX`, relax `EPSRAY`, set
  `NRAYMAX=1` (one ray is enough for beam tracing)

For quantitative sensitivity, see `wrxlib_sweep` ({doc}`testing` Layer 4).
