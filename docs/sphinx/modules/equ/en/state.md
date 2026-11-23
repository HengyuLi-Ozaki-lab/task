# State

`Equ.get_state()` returns an `EquState`: the C struct `equ_state_t`
(`equ/equ_api.h`) sliced to its valid sizes. `to_dict()` gives upper-case keys.

| Field | Meaning |
|---|---|
| `nr`, `nz`, `nv`, `nsu` | grid points in R and Z, flux surfaces, boundary points |
| `mode` | the run's mode (0 or 1) |
| `fct_steps`, `fct_converged`, `erreq` | the last FCT loop: steps, whether it met `EEQMAX`, its error |
| `raxis`, `zaxis`, `psi_axis` | magnetic axis [m], flux on axis |
| `xpoint_status`, `rsep`, `zsep`, `psi_sep` | X point: found when > 0; its position [m]; flux at the separatrix |
| `ip`, `ip_target`, `rbt` | computed current [MA], `TCUR` [MA], R B_t [T m] |
| `beta_t`, `beta_s`, `beta_j`, `li` | toroidal beta [%], beta* [%], beta_J, li |
| `q_axis`, `q_surf`, `q95`, `qqj` | q on axis, at the surface, at 95 %, q_J |
| `rmaj`, `rpla`, `elip`, `trig`, `el95`, `volume` | shape and volume of the result |
| `cvac` | coil currents of groups 0..18 |
| `rg`, `zg` | the grid [m] |
| `profiles` | on the flux surfaces (1 = axis): `psi`, `psit`, `pressure` [Pa], `q`, `f` (R B_t), `vol`, `rminor`, `rcentre`, `kappa`, `delta` |
| `rsu`, `zsu` | the plasma boundary (an open polygon) |

`get_psi_rz()` returns psi(R, Z) as a numpy array indexed `[i_r, i_z]`.

## What to know

- **The FCT loop does not always converge.** In both examples of `equ/example` the
  last FCT loop ends at `IEQMAX` with `erreq` 0.2 to 0.6 against `EEQMAX` = 1e-3. The
  program does not treat it as a failure; neither does the library. Look at
  `fct_converged`.
- **Pressure units.** The state's `pressure` is in Pa. EQU's G-EQDSK writer, which
  `write_geqdsk` uses unchanged, writes `pres` and `pprime` in MPa.
- **`ip` and `ip_target` differ.** `ip` is the current of the computed equilibrium
  (the program prints it as `tcur`); QUEST's mode-1 run gives 0.31 MA for a target of
  0.30 MA.
