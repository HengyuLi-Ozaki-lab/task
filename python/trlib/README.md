# trlib — Python wrapper for TASK/TR

`trlib` is a thin `ctypes`-based Python wrapper around
`tr/libtrapi.so`, the in-process shared-library version of the TASK/TR
transport code. It lets scripts drive TR simulations from Python
without shelling out to the standalone `tr` / `tr2` binary or going
through namelist files.

## Overview

TASK/TR has two user-facing deliverables:

| | Traditional CLI | Library (Phase L) |
|---|---|---|
| Binary | `tr/tr2` | `tr/libtrapi.so` |
| Entry | interactive menu | 5 C ABI functions |
| I/O | namelist + ASCII output | in-memory state struct |
| Graphics | PGPlot / Fortran 90 graphics | excluded |
| Python | — | `python/trlib` |

The C ABI is defined in `tr/tr_api.h`; the Fortran backend
(`tr/tr_api.f90`, `tr/tr_param_registry.f90`) is unchanged Fortran that
is also linked into `tr2`. `python/trlib` only wraps the 5 C entry
points and marshals a `tr_state_t` struct into the pure-Python
`TrState` dataclass.

No third-party dependencies — Python 3.8+ stdlib only (`ctypes`,
`dataclasses`, `pathlib`, `os`). `numpy` is optional.

## Installation

Per-system files first (all gitignored; once per checkout):

```bash
cd /path/to/task
cp make.header.org make.header            # edit compiler / flags for your system
cp mtxp/make.mtxp.nompi mtxp/make.mtxp    # or another mtxp/make.mtxp.* template
git clone --branch develop https://github.com/k-yoshimi/bpsd.git ../bpsd   # patched fork, see docs/external-patches/bpsd-fork.md
make -C ../bpsd libbpsd.a                 # populates ../bpsd/mod/*.mod, which pl's PIC build reads
```

The TASK checkout must be named `task`: `../bpsd/Makefile` includes
`../task/make.header`.

Then build the shared library once:

```bash
cd /path/to/task
make -C tr libtrapi.so
```

The target builds the dependent PIC archives (`../lib`, `../mtxp`, `../pl`, `../eq`) and the in-tree
PIC copy of bpsd (`make -C tr bpsd_pic`) in dependency order before
compiling the tr objects, so this one command works from a clean
tree (#230). Build serially: `make -jN` is not supported by the
per-directory Makefiles (no intra-directory object dependencies).

This produces `tr/libtrapi.so` with 5 exported symbols (`tr_init`,
`tr_run`, `tr_set_param`, `tr_get_state`, `tr_finalize`) plus PIC
variants of the dependent libraries (`lib*_pic.a`). The pre-existing
non-PIC `*.a` archives and the `tr2` binary are unchanged.

Put the wrapper on `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

Optionally point at a library file outside the repository:

```bash
export TRLIB_PATH=/custom/path/libtrapi.so
```

Library lookup order (first match wins): `TRLIB_PATH` env var,
`<repo>/tr/libtrapi.so`, `<repo>/lib/libtrapi.so`.

## Quick start

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_params(RR=8.5, RA=2.0, BB=5.3,
                  NSMAX=2, DT=0.1, NTSTEP=10)
    tr.set_param("PN[1]", 1.0)   # array element (1-origin)
    tr.set_param("PN[2]", 1.0)
    tr.run(ntmax=50)
    state = tr.get_state()

print(f"T={state.scalars['T']:.3f}  WPT={state.scalars['WPT']:.3f}")
```

See `examples/` for runnable scripts:

- `examples/quickstart.py` — smallest complete run
- `examples/parameter_sweep.py` — RR / BB grid
- `examples/state_dump.py` — single run, full `TrState.to_dict()` as JSON

## Library layout check (#246)

`load_library()` asks `libtrapi.so` for its `tr_state_t` layout
(`tr_state_abi_version()`, `tr_state_size()`) and refuses it with
`TrlibAbiError` when the version or the size differs from this wrapper's
`TrStateC`, or when the library exports neither symbol (built before
#246). The message names the fix: rebuild the library
(`make -C tr libtrapi.so`) or update the wrapper. A library and a
wrapper from different commits used to fail silently (fields written
past the struct, or appended fields read as `0.0`). A wrapper older
than #246 does not ask, so keep the two from the same commit.

## Failures: `tr_last_error`, `TrFailure`, `Trlib.last_error()`

`tr_init` puts the library in **library mode** (`tr2` never is). In it, the time loop returns the first failure
instead of going on, and the C call `tr_last_error(tr_diag_entry_t*)` reports it (`param` = kind, `code`, and
`msg` = `nt=<step> t=<time> s: <what failed>`). `Trlib.last_error()` returns it as a `TrFailure(kind, code, nt, time,
detail)`, and `TrlibRunError.failure` carries it when `run` raises (`None` when the `.so` predates `tr_last_error`). The
first failure is kept; `tr_init` and every `tr_run` clear the record (`kind == "NONE"`).

| kind | meaning |
|---|---|
| `EQ_FAILED` | an equilibrium solve of `MODELG = 9` failed: the initial q-scaling (`tr_set_metric`) or the periodic re-solve (`NTEQIT`); `code` is EQ's (103 axis out of plasma, 110/111/112 below) |
| `NONFINITE` | Q0, the stored energy or a central temperature is not finite (`code` -3) |
| `TR_CHECK` | `TRCHCK`: a negative temperature |
| `PREP_FAILED`, `OTHER` | the preparation failed; any other non-zero status of the loop |
| `REFUSED` | reserved for `tr_continue` (PR 3 of the plan); nothing records it yet (`tr_run` refuses before the run by returning `TR_ERR_INVALID`, with no record) |

EQ's own codes 110 (a flux-surface extremum at the edge of the contour array), 111 and 112 (`EQMAGS` could not trace
the surface in the loop, or the edge surface) come with a reason in EQ's `EQ_ERRMSG` (`libtrapi.so` does not export
`eq_last_error`): an `EQ_FAILED` record appends it to `detail` as `<where>: <EQ's reason>` when EQ set one (EQCALC's
codes may leave it empty). The message of `tr_last_error` is cut at 127 characters, so a long reason is cut there.

`tr_mcp` puts the record in the error string of a failed `run`: `... [failure: kind=EQ_FAILED code=103 nt=600
time=12 s; <detail>]`.

### Changes of behaviour

- Library mode only: `MODELG` 0, 4 or 25, and `RIPS = 0`, used to return RC 0 with about ten non-finite scalars; they now fail with
  `NONFINITE` at nt 1. A client that tested for non-finite scalars after a successful `run` (task-web's `non_finite`
  flag) now gets the error instead.
- Library mode only: a failing periodic re-solve (`NTEQIT`) ends the run with `EQ_FAILED`; the loop used to go on, and a
  checked build used to stop the process at an array bound.
- Not library mode only: the two #228 fixes (`7656ebbe`, `23541105`, #226's own) apply to `tr2` too, because
  `tr_set_metric` is shared. A failing `MODELG` 9 q-scaling now fails the preparation: where `tr2` used to go on
  after a failed solve (for example `RIPS` 0.81 or 0.84), its `R` now stops at `trmenu.f90:74`; and a second `R` in
  one `tr2` session under `MODELG` 9 adopts the equilibrium again, where it used to differ. `tr2`'s output is
  unchanged on a single `R` that succeeds (`tr.ITER01` with `MODELG` 9, `NTEQIT` 50 and 0: byte-identical).

## Outputs by name: scalars and the time history

`Trlib.scalar_names()` lists the 31 global results TR computes (`T`, `WPT`, `AJT`, `Q0`, `BETA0`, `BETAP0`, `BETAA`,
`BETAN`, `TAUE1`, `TAUE2`, `ZEFF0`, `ALI`, `RQ1`, `AJRFT`, `PNFT`, `QF`, `PINT`, `POHT`, `PNBT`, `PRFST`, `PEXST`, `PRLT`,
`POUT`, `AJOHT`, `AJNBT`, `AJBST`, `RIP`, `VLOOP`, `WPDOT`, `H98Y2`, `TAUE98`); `Trlib.get_scalar(name)` returns one as
`TRGLOB` last computed it, in the units of `tr/trrslt_globals.f90` (powers in MW, currents in MA, energy in MJ; `PINT`
includes the alpha power `PNFT`, and `P_fus = 5 PNFT` for D-T). They are current after `run`; between `Trlib()` and the first
`run` they are the previous lifecycle's. An unknown or inexact name raises `TrlibParamError`. `get_state().scalars` holds all
31; `to_dict()` keeps the 14 of the C struct. `tr_mcp`'s `describe_state_schema` gives each name its unit and meaning.

TR records a time history every `NGTSTP` steps (default 2): `Trlib.history(names=None)` returns `{name: numpy.ndarray}`
for 47 columns (`Trlib.history_names()`; `T` is the time), `history_length()` the rows and `history_full()` whether the
buffer is used up. The values are **single precision** (about 7 digits). The last row agrees with `get_scalar` to rel 1e-6 only when the last step of the call was
recorded and the buffer was not yet full: with the defaults `run(1)` leaves `history("T")["T"][-1]` at 0 while
`get_scalar("T")` is `DT` (no row was recorded), and once `history_full()` is true the history stays behind the state.
The first row is the state at t = 0 and a row is recorded at every step that is a multiple of `NGTSTP`, so a `run` adds `n // NGTSTP` rows only when it starts on
one (`run(5)` twice adds 3 and 3, `run(1)` adds 0 or 1);
`tr_prep` starts the history again, so the first `run` and every `run` after a changed parameter do. **The buffer holds
`NTM` = 10001 rows; TR then stops recording without a message** (`history_full()` is true): set `NGTSTP` so that
steps / `NGTSTP` stays below 10001 for a long run. `BETAN` and `PRFST` are computed from the row; `PEXST` has no column.
`tot` has the same through `Tot.get_scalar("tr:NAME")` and `Tot.history(["tr:NAME", ...])`.

## API reference

### `Trlib(lib_path: str | None = None)`

Context manager. `__enter__` calls `tr_init`; `__exit__` / `close()`
calls `tr_finalize`. Only one live instance per process is meaningful
(TR backend holds global COMMON-block state).

### `Trlib.set_param(name, value) -> None`

Set a single parameter. Use `"NAME[i]"` (1-origin) for array elements;
Python keyword arguments cannot contain brackets so array elements
must use `set_param`, not `set_params`.

### `Trlib.set_params(**kwargs) -> None`

Bulk-set **scalar** parameters. Raises `TrlibError` on keys containing
`__` (common array-syntax mistake).

### `Trlib.run(ntmax: int) -> None`

Advance the simulation by `ntmax` steps. `ntmax=0` is a valid no-op
used by the smoke tests.

### `Trlib.get_state() -> TrState`

Snapshot current TRCOMM scalars and `[0:nrmax][0:nsmax]` profile
arrays into a `TrState` dataclass. Trailing padding (up to
`TR_MAX_NRMAX=500` / `TR_MAX_NSMAX=8`) is ignored.

### `Trlib.get_scalar(name) -> float`, `Trlib.scalar_names()`, `Trlib.history(names=None)`

See "Outputs by name" above. `history` returns float64 arrays; `history_names()`, `history_length()` and `history_full()` describe the table.

### `Trlib.last_error() -> TrFailure`

The first failure of the last `run` (see above), or `kind == "NONE"`. Raises `TrlibError` for a library without
`tr_last_error`.

### `Trlib.close() -> None`

Idempotent. The context manager calls this automatically.

## Supported parameters

A name that starts with `eq:` (`eq:RB`, `eq:NSGMAX`, `eq:NRMAX`, ...) goes to EQ's registry, so `MODELG` 9 sets EQ's wall
and grid through `set_param` / `set_param_str`; an unknown name raises `TrlibParamError`, and an accepted one makes the
next `run` prepare again. Two kinds of `eq:` name are refused (`TrlibParamError`, one line on unit 6):

- `eq:RR`, `eq:RA`, `eq:RKAP`, `eq:RDLT`, `eq:BB`, `eq:RIP` and `eq:KNAMEQ` do nothing through TR: under `MODELG` 9
  EQ's copy is overwritten from TR's device, and TR passes its own `KNAMEQ` to EQ. Set `RR`, `RA`, ... (TR's) instead;
  for `eq:RIP` set `RIPS` and `RIPE`, which TR passes to EQ as `RIP`.
  Under `MODELG` 3, 5 and 8 EQ's `NRMAX` is TR's `NRMAX` + 1, its `NTHMAX` is fixed at 64 and its `NSUMAX` at 0
  (`tr_set_metric`, `tr/trmetric.f90`).
- every `eq:` name, once this process has made its first preparation attempt (failed or not; across `tr_finalize`
  and `tr_init` too): until the pinned bpsd has k-yoshimi/bpsd#7 an EQ grid change in one process corrupts memory
  (`EQ_FAILED` 103 from a spline written past its end, measured with `eq:NRMAX` 30 then 60 and `eq:RB` 2.0 then 1.2),
  so `eq:` names are set before the process's first preparation attempt (a `run` that `tr_run`'s own checks refuse
  before `tr_prep` does not count). This guard comes off with the `NRMAX` guard below.

`tr_run` also refuses (`TrlibParamError`, one `XX tr_run: eq:NAME` line) and `validate()` reports an EQ mesh size above
the compile-time maximum of EQ's arrays: the ten that `eq_validate` checks (`eq:NSGMAX`, `NTGMAX`, `NUGMAX` 128;
`NRGMAX`, `NZGMAX`, `NPSMAX` 513; `NRVMAX`, `NRMAX` 1001; `NTHMAX` 2049; `NSUMAX` 1343; `eq/eqcom0_mod.f90`) under
`MODELG` 9, and the seven that TR does not set itself (all but `NRMAX`, `NTHMAX`, `NSUMAX`) under `MODELG` 3, 5 and 8.
Before the check `eq:NSGMAX` 129 ended the process (`SIGM(129)` written past its 128 elements, `eq/eqcalc.f90:63`).

The `eq:` guard closes only the direct route, and that is why every `eq:` name is refused after a preparation (any EQ
input can move the count). Under `MODELG` 9 *any* input that moves EQ's plasma grid (`NRPMAX`, which depends on EQ's
`RA`, `RB` and the solved axis and edge) needs a bpsd with k-yoshimi/bpsd#7: TR's `RA`, `RR` and other device inputs,
`MODELG` itself (`MODELG` 9 then the `tst2` defaults: 50 to 51 points; its test is gated on `TRLIB_BPSD_REGRID_FIX=1`),
the `eq:` names, and the drift of `NRPMAX` between `NTEQIT` re-solves inside one run (47 and 48 in `tr.ITER01` with
`MODELG` 9). Measured on an unpatched bpsd: `MODELG` 9 with `RA` 0.5 in one lifecycle, then `RA` 1.0 in the next, fails
with `EQ_FAILED` 103 at q-scaling iteration 2, with no `eq:` name set and TR's `NRMAX` unchanged. The protection
against the overrun is bpsd#7 itself. TOT's `eq:` dispatcher (`dispatch_eq` in `tot/tot_param_registry.f90`) calls
`eq_param_set` directly, so this guard does not apply in `totlib` or the mono build.

The registry below reflects `tr/tr_param_registry.f90` at Phase L-3.
Add to it by extending that Fortran `SELECT CASE`; no Python change
is required — the wrapper forwards names verbatim.

| Group | Names | Notes |
|---|---|---|
| Geometry / device | `RR`, `RA`, `RKAP`, `RDLT`, `BB`, `PHIA` | scalar doubles |
| Plasma (arrays, 1..NSMM) | `PA[i]`, `PZ[i]`, `PN[i]`, `PNS[i]`, `PT[i]`, `PTS[i]` | 1-origin index |
| Plasma scalars | `NSMAX`, `NRMAX` | cast to INT. `NRMAX` is TR's radial mesh, 3 to 500 (1 and 2 abort the solver; 500 is `TR_MAX_NRMAX`). Changing the TR or EQ mesh between preparations in one process needs bpsd with the spline-resize fix (k-yoshimi/bpsd#7) and, for a change of the EQ grid, `eq_bpsd_put` sizing its arrays again when the grid changes (that second fix is in this tree, `eq/eqbpsd.f90`). The bpsd fix is not in every bpsd: without it a later preparation on another grid writes out of bounds, so `tr_run` refuses, and `validate()` reports, an `NRMAX` other than the one of the process's first preparation attempt (failed or not; across `tr_finalize` and `tr_init` too): one mesh per process, as a task-web job or a test under `--forked` is. The guard comes off once the pinned bpsd has the fix. A change of the EQ grid with TR's `NRMAX` unchanged by an `eq:` name is refused after the first preparation (above); one by a change of `MODELG` between lifecycles passes both guards but still needs the bpsd fix, and its regrid test is skipped unless `TRLIB_BPSD_REGRID_FIX=1` is set with such a bpsd. The tests that change TR's `NRMAX` or set an `eq:` name after a preparation stay skipped while the guards are in place |
| Current | `RIPS`, `RIPE` | |
| Time evolution | `DT`, `NTMAX`, `NTSTEP`, `EPSLTR`, `LMAXTR`, `NTEQIT` | int-typed coerced. `NTEQIT` is the step interval of the EQ re-solve under `MODELG=9` (0 = never; negative refused) |
| Transport switches | `MDLKAI`, `MDLETA`, `MDLAD`, `MDLAVK`, `CHP`, `CK0`, `CK1` | |
| Transport arrays | `CDW[i]` | |
| Transport weights | `CDH`, `CNH` | the weights of `chi_s = CDH*chi_turb + CNH*chi_NC` (`chi_NC` the neoclassical chi, `AKNC`); default 1 (neutral) |
| Module switches | `MDLNB`, `MDLEC`, `MDLLH`, `MDLIC`, `MDLPEL`, `MDLJBS`, `MDLST`, `MDLNF`, `MDLUF`; `TPRST` | `TPRST` is the sawtooth period in s (must be > 0) |
| Fusion model of `trx` | `MODEL_PNF` | 0 (default) leaves `MDLNF` in charge; 1 is D-T; 2, 3, 4, 12, 14 evaluate more reactions and pass nothing to the solve. Not together with `MDLNF`; see `docs/sphinx/modules/tr/en/parameters.md` for what it does not do yet |
| NCLASS and particle transport | `MDNCLS`, `AD0`, `AV0`, `CDP`, `CNP` | `MDNCLS` ≠ 0 takes the neoclassical transport, the resistivity and the bootstrap current from NCLASS; with the default `MDLAD` 3 and with NCLASS, D_s = CDP·AD0·chi_turb + CNP·D_NC; `AV0` is the pinch of `MDLAD` 1, 2, 4 |
| Equations solved | `MDLEQB`, `MDLEQN`, `MDLEQE` | B_theta evolved (1, default) or held (with `MODELG` 3 TR reloads psi from the equilibrium every step either way); densities held (0, default) or evolved; with densities evolved, 0/1/2 = electrons from quasi-neutrality / both solved / bulk ions from quasi-neutrality (2 only for two species, hydrogenic species 2, no impurity density, no UFILE) |
| Start current profile | `PROFJ1`, `PROFJ2` | `MODELG` 2 only: `PROFJ1` ≤ 0 (default −2): j ∝ 1/eta; > 0: j ∝ (1 − rho^\|PROFJ1\|)^\|PROFJ2\| |
| Particle source (gas puff) | `MDLPSC`, `NPSCMAX`; `PSCTOT[i]`, `PSCR0[i]`, `PSCRW[i]`, `NSPSC[i]` (i = 1..10) | `MDLPSC` 1: Gaussian sources of total rate `PSCTOT` [10^20/s] centred at `PSCR0` metres (RA·rho, not rho) into ion species `NSPSC`; moves the density only with `MDLEQN` 1. `tr_run` refuses values the solver cannot take (see `docs/sphinx/modules/tr/en/parameters.md` section 14) |
| Heating / current drive | `PNBTOT`, `PNBR0`, `PNBRW`, `PNBENG`, `PNBRTG`; `PICTOT`, `PICR0`, `PICRW`, `PICNPR`, `PICCD`; `PECTOT`, `PECR0`, `PECRW`, `PECNPR`, `PECCD`; `PLHTOT`, `PLHR0`, `PLHRW`, `PLHNPR`, `PLHCD` | NBI, ICRF, ECRF and LH; the `*TOT` names are total input power in MW (default 0) |

Unknown names return ierr=1 (raised as `TrlibParamError`).

## External driven current

For pipelines where another module computes a total driven current
(e.g. fp's RJT volume integral) and tr should consume it, set:

| Param                | Unit             | Default | Meaning                               |
|----------------------|------------------|---------|---------------------------------------|
| `EXTERNAL_DRIVEN_I`  | MA               | 0.0     | Total externally-driven current       |
| `EXTERNAL_DRIVEN_R0` | normalized rho   | 0.0     | Gaussian profile center (axis-peaked) |
| `EXTERNAL_DRIVEN_RW` | normalized rho   | 0.3     | Gaussian profile width                |

`EXTERNAL_DRIVEN_I = 0.0` means no external drive (no-op; existing
regression baselines are unaffected).

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_param("RR", 8.5)
    tr.set_param("RA", 2.0)
    # ... other parameters ...
    tr.set_param("EXTERNAL_DRIVEN_I",  1.0)   # 1 MA externally driven
    tr.set_param("EXTERNAL_DRIVEN_R0", 0.0)
    tr.set_param("EXTERNAL_DRIVEN_RW", 0.3)
    tr.run(ntmax=10)
    state = tr.get_state()
    print("AJRFT:", state.scalars["AJRFT"])   # ≈ 1.0 (matches injected I)
```

The injected current is added to `AJRF(NR)` in `trprf.f90`'s `TRPWRF`
via a Gaussian profile, normalized so the integral over the plasma
cross-section equals `EXTERNAL_DRIVEN_I [MA]` exactly.

`tr.validate()` returns an `OUT_OF_RANGE` diagnostic if you set
`EXTERNAL_DRIVEN_I != 0` together with `EXTERNAL_DRIVEN_RW <= 0`
(which would silently no-op in trprf otherwise).

## Species profiles must be evolvable (`run` refuses, `validate` reports)

Outside the UFILE modes (`MDLUF` not in 1/2/3, i.e. every fixture in the
repo) the density and temperature of every active species `1..NSMAX` come
from the namelist pairs `PN/PNS` and `PT/PTS`. A species whose density is
identically zero (`PN=PNS=0`, the `tr_init` default for species 3 and 4)
or negative, or whose temperature is non-positive at the centre or the
edge, makes the transport step divide by zero and every scalar NaN after
one step (#189); non-finite values do the same. `run()` therefore raises
`TrlibParamError` before `tr_prep` (one `XX tr_run: PN[3]: ...` line on
stdout per finding) and `validate()` returns the same findings as
diagnostics named `PN[ns]` / `PT[ns]` / `PTS[ns]` (`OUT_OF_RANGE_AFTER_DEP`
for the zero-density case, `OUT_OF_RANGE` otherwise). `run()` also
refuses `NSMAX` above the compile-time `NSM` (4), which `validate()`
already reported. Raising `NSMAX` above a fixture's species count
therefore needs `PN[ns]`, `PNS[ns]`, `PT[ns]`, `PTS[ns]` for the new
species. `PN[ns]=0` is refused with `PNS[ns]>0` too (task-web-client #190): the density then
vanishes at the axis and the run fails or ends with NaN. In the UFILE modes
`MDLUF=1/2/3` the species that `tr_prof` still takes from the namelist
are not checked yet (follow-up issue).

## BPSD ブローカー pull 検証 (`Trlib.check_bpsd_pull`)

`Trlib.check_bpsd_pull()` は L-7b-ii で追加した非破壊ヘルパで、tr 側
の BPSD インスタンスから `device` / `equ1D` / `metric1D` の 3 スロット
を pull できるか (= 各 `ierr == 0` か) のみを返す。`plasmaf` は tr
自身の BPSD 出力 (`tr_bpsd_put` で push する側) なので意図的に対象外。

```python
from trlib import Trlib

with Trlib() as tr:
    if not tr.check_bpsd_pull():
        # equ1D/metric1D を tr の BPSD に push してくれる相手が
        # まだ走っていない、もしくは別 .so の BPSD に書いてしまっている
        # (後述) 状態。tr.run() を呼ぶと既定 / 古い equilibrium で
        # 走ってしまう可能性がある。
        raise RuntimeError("BPSD broker missing equilibrium data")
    tr.run(ntmax=10)
```

ノート:

- **非破壊**: ローカルの捨て型に pull するだけで TRCOMM は変えない。
  `tr.run()` の前後どちらで呼んでも安全。
- **粒度は bool 1 つ**: スロット単位の詳細 ierr は出さない (将来拡張)。
- **plasmaf 除外の理由**: tr が自身で put する側のスロットなので、
  「fresh init で False を返す」想定が崩れないようにするため。
- **L-7b-ii 時点での scope 制約 (重要)**: `libtrapi.so` は自分自身の
  `bpsd_equ1D` モジュール変数を持つため、別 .so (例えば
  `libeqapi.so`) で `bpsd_put_equ1D` しても tr 側からは見えない。
  `check_bpsd_pull` は **同じ libtrapi.so 内** で push されたスロット
  だけが True になる。`Tot` / `libtotapi.so` 経由 (eq+tr+bpsd 同梱)
  なら期待どおり機能するが、`TotPipeline` (per-module .so) では
  現状 push 経路がないため fresh init では常に False。詳細は
  `python/totlib/README.md` の Coupling rules 節を参照。

## `TrState` fields

Matches `tr_state_t` in `tr/tr_api.h`. Full dict layout is available
via `state.to_dict()` (JSON-serialisable; matches the Phase 0 baseline
format so `compare_metrics.py` can diff wrapper vs `tr2` output).

| Attribute | Type | Meaning |
|---|---|---|
| `nt` | int | current time-step index |
| `nrmax` | int | radial points actually in use |
| `nsmax` | int | species actually in use |
| `scalars` | dict[str, float] | 14 plasma scalars (see below) |
| `RN` | list[list[float]] | `[nrmax][nsmax]` density profile |
| `RT` | list[list[float]] | `[nrmax][nsmax]` temperature profile |
| `AJ` | list[float] | `[nrmax]` current density profile |
| `QP` | list[float] | `[nrmax]` safety-factor profile |

Scalars (canonical order): `T`, `WPT`, `AJT`, `Q0`, `BETA0`,
`BETAP0`, `BETAA`, `BETAN`, `TAUE1`, `TAUE2`, `ZEFF0`, `ALI`, `RQ1`,
`AJRFT` (total RF + external driven current [MA]).

## Exceptions

Every `tr_*` return code maps to a concrete subclass of `TrlibError`:

| ierr | class | meaning |
|---|---|---|
| 0 | — | success |
| 1 | `TrlibParamError` | invalid parameter name / index / value |
| 2 | `TrlibStateError` | API call before `tr_init` or after `close` |
| 3 | `TrlibRunError` | calculation or `tr_get_state` failed |
| 4 | `TrlibNotImplementedError` | Phase L-2 stub return |

Spec-style aliases (`TrLibInvalidParam`, `TrLibNotInitialized`,
`TrLibCalculationFailed`, `TrLibNotImplemented`) are also exported.

## Migration: `tr` CLI → `trlib.Trlib`

| CLI step | `trlib` equivalent |
|---|---|
| edit `trparm` namelist | `tr.set_param(...)` / `tr.set_params(...)` |
| menu option `R` (run) | `tr.run(ntmax=...)` |
| inspect output file | `tr.get_state()` |
| menu `Q` (quit) | exit context manager / `tr.close()` |
| batch parameter sweep | Python `for` loop (see `examples/parameter_sweep.py`) |

The wrapper does **not** wrap graphics, file output, or the
interactive menu — those live in `tr/tr2` only.

## Known limitations

- **Single instance per process.** TR backend uses COMMON blocks.
  Two concurrent `Trlib()` instances share state; the second
  `tr_init` resets globals.
- **No graphics, no MPI, no OpenMP API.** Graphics symbols exist but
  are not reachable from the 5 exported entry points; the loader uses
  `RTLD_LAZY` so dangling graphics references never resolve.
- **String parameters not yet wired** (e.g. `KNAMEQ`, `KNAMTR`). See
  `docs/superpowers/specs/2026-04-17-tr-library-design.md` §4.3.
- **Unregistered namelist keys** — any name missing from
  `tr_param_registry.f90` returns `TrlibParamError`. Known gaps include
  geometry/profile tunables that the design spec deferred to later
  phases (string parameters, model-specific tuning coefficients beyond
  `CDW` / `CHP` / `CK0` / `CK1`).
- **`tr_m0904` baseline drift** — the `tr_m0904` regression fixture
  exhibited small (`~1e-8`) drift between `tr2` and the Layer 1 suite
  during Phase L-6 and is pinned to its Phase 0 baseline. Use `1e-10`
  tolerance for `tr_iter01` / `tr_tst2` but allow looser comparison for
  `tr_m0904` when diffing against freshly regenerated tr2 runs.

## Testing

```bash
cd python/trlib/tests
python3 -m unittest discover -v
```

Tests that require `libtrapi.so` are skipped when the shared library
is absent; pure-Python tests (ctypes layout, error wiring,
`TrState.from_c`, `to_dict` shape) always run.

The full 4-layer regression suite is wired into
`test_run/test_definitions.conf`:

- `trlib_c_abi` — Layer 2 C ABI (`make -C tr tr_api_check_all`)
- `trlib_ffi`, `trlib_wrapper` — Layer 3 Python wrapper
- `trlib_equivalence` — Layer 1 vs Phase 0 baselines (tol `1e-10`)
- `trlib_sweep` — Layer 4 3×3 RR×BB smoke

## License / contributions

`trlib` is part of the TASK code and distributed under the repository's
top-level license. Bug reports and PRs are welcome; please keep
wrapper changes minimal — the C ABI is the stable layer, so new
parameters should be added to the Fortran registry first.

## See also

- `docs/superpowers/specs/2026-04-17-tr-library-design.md` — full
  design spec (Phase L)
- `docs/tr-library/architecture.md` — system diagram and Phase
  completion matrix
- `tr/tr_api.h` — C ABI header
- `CHANGELOG.md` — per-phase history
