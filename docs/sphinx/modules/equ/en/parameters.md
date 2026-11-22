# Parameters

The names of the `&EQU` namelist (`eqnlin`, `equ/equinit.f90`). Defaults are EQU's
(`eqinit`: the JT-60U case). Arrays take `NAME[i]` with the index as Fortran declares
it. This table is generated from the MCP server's `PARAMETER_REGISTRY`
(`python/mcp-servers/equ_mcp/server.py`), which a test holds to the Fortran registry.

## device

| Name | Type | Default | Description |
|---|---|---|---|
| `DEVICE` | `str[8]` | `'JT60U'` | device name |
| `DEVNAM` | `str[8]` | `'JT60U'` | device name kept by the run (eqflin sets it to DEVICE) |
| `TITLE` | `str[70]` | `''` | job title (not used in the output) |

## mesh

| Name | Type | Default | Description |
|---|---|---|---|
| `NR` | `int` | `257` | grid points in R: 2**k+1 in 3..257 (the Buneman solver) |
| `NZ` | `int` | `257` | grid points in Z: 2**k+1 in 3..257 (the Buneman solver) |
| `NV` | `int` | `101` | flux surfaces, 3..101 |
| `NSUMAX` | `int` | `101` | points on the plasma surface, 3..1542 |
| `IUDSYM` | `int` | `0` | up-down symmetry: 1 symmetric, 0 not |
| `RWMN` | `float` | `1.9` | R of the box's inner edge [m] (eqchek may lower it) |
| `RWMX` | `float` | `4.2` | R of the box's outer edge [m] (eqchek may raise it) |
| `ZWMX` | `float` | `1.2` | half height of the box, |Z| < ZWMX [m] (eqchek may raise it) |

## plasma

| Name | Type | Default | Description |
|---|---|---|---|
| `BTV` | `float` | `13.5` | R*B_t [T m] |
| `TCUR` | `float` | `2.0` | plasma current I_p [MA] |
| `RMAJ` | `float` | `3.05` | major radius [m]; derived from the markers when MSFX < 0 |
| `RPLA` | `float` | `0.9` | minor radius [m]; derived from the markers when MSFX < 0 |
| `ZPLA` | `float` | `0.0` | Z of the plasma centre [m] |
| `ELIP` | `float` | `1.0` | elongation |
| `TRIG` | `float` | `0.0` | triangularity |
| `ELIPUP` | `float` | `1.0` | elongation of the upper half |
| `TRIGUP` | `float` | `0.0` | triangularity of the upper half |
| `YH` | `float` | `0.5` | half height (shape of generated markers) |
| `YD` | `float` | `0.995` | edge height (shape of generated markers) |
| `QAXI` | `float` | `1.0` | q on axis used in the printed setup error only |
| `QSUR` | `float` | `3.0` | q at the surface used in the printed setup error only |
| `XXLI` | `float` | `1.0` | li used in the printed setup error only |

## profile

| Name | Type | Default | Description |
|---|---|---|---|
| `ICP` | `int[1..10]` | `1, 1, 0, 0, 0, 0, ...` | profile options: ICP[1] the p' and FF' forms (|ICP[1]| = 1, 2, 9, 11); ICP[2] 0 trace only, >0 scale p' to beta_J = CP[1], 1 adjust F for <J/R>, 2 adjust F for <J.B> |
| `CP` | `float[1..10]` | `0.1, 1.0, 1.0, 0, 0, 0, ...` | profile coefficients: CP[1] the beta_J target, CP[2..10] the exponents of ICP[1]'s form |

## coils

| Name | Type | Default | Description |
|---|---|---|---|
| `KNAMCOIL` | `str[80]` | `'init'` | coil file (relative to the working directory); 'done' keeps the coils in memory (after init: the JT-60U set) |
| `IVAC` | `int[0..18]` | `0, 1, 2, -1, -1, -1, ...` | coil group mode: < 0 fixed current, >= 0 fitted; IVAC[0] the surface flux |
| `NCOIL` | `int[0..18]` | `0, 70, 78, 26, 10, 0, ...` | filaments of each coil group in the coil file, 0..100 |
| `CVAC` | `float[0..18]` | `0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ...` | coil currents [MA turn]; CVAC[0] the surface flux |
| `CVACST` | `float[0..18]` | `0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ...` | target coil currents of the fit [MA turn] |
| `CVACWG` | `float[0..18]` | `0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ...` | weights of the targets in the fit |
| `CVACT` | `float[0..18]` | `0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ...` | d CVAC / dt: used only by the menu's C, which the library does not run |
| `ISVAC` | `int` | `0` | vacuum field: 0 through the grid, 1 direct Green's function |

## boundary

| Name | Type | Default | Description |
|---|---|---|---|
| `MSFX` | `int` | `9` | marker points: < 0 given by RVAC/ZVAC (|MSFX| <= 29), > 0 generated from the shape (eqchek lowers it to 17, or 9 when symmetric) |
| `RVAC` | `float[0..30]` | `0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ...` | R of the marker points [m] |
| `ZVAC` | `float[0..30]` | `0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ...` | Z of the marker points [m] |
| `ISEP` | `int` | `2` | X point: 0 none, 1 lower, 2 outer, 3 upper, 4 inner (-4..4: the sign is used) |
| `DSEP` | `float` | `0.001` | separation between the X point and the last closed surface |
| `ILIMT` | `int` | `0` | limiter points in the coil file, 0..100 |
| `IVBND` | `int` | `0` | must be 0: the vacuum boundary points it would count (RVBND, ZVBND) are not inputs |
| `RLOOP` | `float` | `2.786` | R of the flux-loop diagnostic point [m] |
| `ZLOOP` | `float` | `0.952` | Z of the flux-loop diagnostic point [m] |

## convergence

| Name | Type | Default | Description |
|---|---|---|---|
| `MSETUP` | `int` | `20` | steps of the setup loop at most |
| `ESETUP` | `float` | `0.001` | convergence of the setup loop |
| `IEQMAX` | `int` | `20` | steps of the FCT loop at most |
| `EEQMAX` | `float` | `0.001` | convergence of the FCT loop |
| `IODMAX` | `int` | `10` | steps of the ODE iteration at most |
| `EODMAX` | `float` | `1e-05` | convergence of the ODE iteration |
| `IADMAX` | `int` | `1` | steps of the vacuum fit at most |
| `EADMAX` | `float` | `0.0001` | convergence of the vacuum fit |
| `BAVMAX` | `float` | `0.8` | FCT relaxation, upper bound |
| `BAVMIN` | `float` | `0.2` | FCT relaxation, lower bound |

## output

| Name | Type | Default | Description |
|---|---|---|---|
| `IEQOUT` | `int[1..10]` | `5, 0, 0, 0, 0, 0, ...` | printing on unit 6: IEQOUT[2] >= 2 one line per step, IEQOUT[3] >= 1 the summary |
| `IEQRD` | `int` | `0` | must be 0 |

## Accepted, not used

`IVP`, `IVTAB`, `IVGRP`, `JEQRD`, `IEQWT`, `JEQWT` and the dummies `EQFILE`, `RWAL`,
`ZWAL` are in the namelist but nothing reads them: `read_parm` accepts them,
`set_param` refuses them.
