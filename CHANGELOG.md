# Changelog

All notable changes to the TASK code are recorded here. This file
starts with Phase L (library-ization) of TASK/TR; earlier history is
in `git log` and `HISTORY`.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- **TR library: `eq:` names, library mode and `tr_last_error`** (the MODELG 9 heating study of task-web, #96 PR 1).
  - `tr_set_param` and `tr_set_param_str` send a name that starts with `eq:` to EQ's registry (`eq:RB`, `eq:NRMAX`,
    `eq:NSGMAX`, ...); an unknown name returns `TR_ERR_INVALID`, and an accepted one makes the next `tr_run` prepare
    again. `eq:RR`, `eq:RA`, `eq:RKAP`, `eq:RDLT`, `eq:BB`, `eq:RIP` and `eq:KNAMEQ` are refused (they do nothing
    through TR: set TR's own), and so is every `eq:` name after the process's first preparation attempt, until the
    pinned bpsd has k-yoshimi/bpsd#7 (it comes off with the `NRMAX` guard below). Under `MODELG` 9 this sets EQ's wall and grid without `tot`. `libtrapi.so` now links EQ's registry object.
    A mesh change of EQ between two preparations in one process needs the bpsd spline resize
    (k-yoshimi/bpsd#7); the regrid tests that need it run with `TRLIB_BPSD_REGRID_FIX=1`.
  - `tr_run` refuses, and `tr_validate` reports, an `eq:` mesh size above the compile-time maximum of EQ's arrays (the bounds of
    `eq_validate`, EQ's own parameters); `eq:NSGMAX` 129 under `MODELG` 9 used to end the process in `EQMESH`.
  - `tr_init` sets library mode (`tr/trfailure.f90`), `tr2` never does. In library mode the time loop returns the
    first failure instead of going on, and records it: `tr_last_error(tr_diag_entry_t*)` gives the kind
    (`EQ_FAILED` from the periodic `MODELG` 9 re-solve (`NTEQIT`) and from each exit of the q-scaling, with EQ's own
    reason appended to the detail when EQ set one,
    `TR_CHECK` from `TRCHCK`, `NONFINITE`, `PREP_FAILED`, `OTHER`; `REFUSED` is reserved for `tr_continue`), the Fortran code and
    `nt=.. t=.. s: detail`. The first failure is kept; `tr_init` and every `tr_run` clear it. The library-mode
    behaviour is gated; `tr2`'s output is byte-identical on a single healthy `R` (tr.ITER01 with `MODELG` 9,
    `NTEQIT` 50 and 0); the two #228 fixes below apply to `tr2` too.
  - `trlib`: `TrFailure`, `TrlibRunError.failure` (`None` when the `.so` predates `tr_last_error`) and
    `Trlib.last_error()`. `tr_mcp`: the run error string carries the record, and `describe_parameters` has an
    `eq_names` line. TOT and the mono build stop and record too, but `tot_api.h` and `totlib` have no accessor yet.
- **TR registry: `NTEQIT`, `TPRST` and TR's `NRMAX`** (the MODELG 9 heating study of task-web). `NTEQIT` is the EQ
  re-solve interval under `MODELG` 9 (negative refused), `TPRST` the sawtooth period (> 0), `NRMAX` TR's radial mesh
  (3..`TR_MAX_NRMAX` = 500; 1 and 2 stop the solver on an array bound). bpsd keeps the spline size of its first get,
  so a later preparation on a larger mesh in the same process wrote out of bounds (NaN or SIGSEGV under `MODELG` 3):
  until the pinned bpsd resizes them (k-yoshimi/bpsd#7), `tr_run` refuses, and `validate()` reports, an `NRMAX`
  other than the one of the process's first preparation attempt (failed or not), across `tr_finalize` and `tr_init`
  too, for every `MODELG`.
- **TR registry: NCLASS, the equations solved, the start current profile, particle transport and the particle
  source.** `tr_set_param` takes `MDNCLS`, `MDLEQB`, `MDLEQN`, `MDLEQE`, `PROFJ1`, `PROFJ2`, `AD0`, `AV0`, `CDP`,
  `CNP`, `MDLPSC`, `NPSCMAX` and `PSCTOT[i]`, `PSCR0[i]`, `PSCRW[i]`, `NSPSC[i]` (i = 1..10); the variables,
  defaults and namelist entries existed, so nothing changes at the defaults. They make the PLATO case of Mochinaga
  et al., Plasma Fusion Res. 16, 1403093 (2021) (NCLASS, a gas puff, the densities evolved) settable through the
  library and `tr_mcp`. `tr_run` refuses before `tr_prep`, and `validate()` reports, what the solver cannot take:
  `MDLEQB`, `MDLEQN`, `MDLPSC` outside {0, 1}; `MDLEQE` outside {0, 1, 2}, 1 or 2 with `MDLEQN` 0, and 2 unless
  `NSMAX` is 2, species 2 is H or D of charge 1, there is no impurity density and no UFILE (`tr/trexec.f90` adds the
  other species to the bulk-ion density instead of subtracting them); with `MDLPSC` 1, `NPSCMAX` outside 0..10,
  `NSPSC[i]` outside 2..NSMAX (only 2 with a UFILE, where `tr_prep` may change NSMAX), `PSCRW[i]` <= 0 or below
  1e-10 m and `|PSCR0[i]|` above 1e10 m (measured before: an array bound, NaN, another value run without a word, or
  a stop inside `tr_prep`). `PSCR0` is in metres (RA*rho). `trlib`'s `validate()` asks again when the findings
  outnumber its first buffer of 32.
  The integer names join `value_refused`. The M0904 fixture sets `MDNCLS` as its input does.
- **MCP server `fp_mcp`: a `set_param_str` tool** (#231) sets `KNAMEQ`,
  the equilibrium file that `MODELG=3` loads, so an EQ to FP handoff (an
  equilibrium written by `eq_mcp`'s `save` tool) can be driven through
  MCP; `set_params` passes a `str` value to it. It calls
  `fplib.Fplib.set_param_str`, which needs a `libfpapi.so` that exports
  `fp_set_param_str`. A successful call zeroes the state's `scalars` until
  the next run, as a numeric set does. `tot_mcp`'s `describe_parameters`
  marks `fp:KNAMEQ` as settable through `run_pipeline` only, since tot's
  `set_param` passes string values on for `eq:` and `tr:` only.
- **FP library: `fp_get_state` returns seven global scalars** after the
  profile arrays: `TOTAL_IP` [MA], `STORED_ENERGY` [MJ], `COLLISION_POWER`,
  `ABSORPTION_POWER`, `ABSORPTION_WR`, `ABSORPTION_WM` [MW] (species sums at
  the latest `NTG1` sample, what FP otherwise only writes to unit 6) and
  `PLASMA_VOLUME` [m^3]. They are what shows an EQ to FP handoff: the six
  profiles are local quantities and stay bit-identical when only the
  equilibrium changes (without radial transport, waves or current drive).
  `fp_state_t` grows by 56 bytes at its end (layout version 2, #246), so
  `libfpapi.so` and its callers are rebuilt together: `fplib` refuses a
  library built before this change with `FplibAbiError` instead of reading
  the scalars as zeros. `FpState.scalars`, `to_dict()["scalars"]`
  and the `scalars` object of fp_mcp's state carry them, and an FP step of
  the `totlib` pipeline keeps them beside `timefp` and its counts. They are
  zero until the first run, and again after any successful parameter set
  (`fp_set_param`, `fp_set_param_str`, or tot's `fp:` parameters, which the
  registry counts since #253) until the next run that is made.
- **EQ library: `eq_save`, `Eq.save(path)` and the `save` tool of `eq_mcp`**
  write the equilibrium of the last `eq_run` to a TASK/EQ binary file through
  `EQSAVE`, the file that `MODELG=3` with `KNAMEQ` loads. A save whose file
  was not opened, or is shorter than what was written, is an error, not
  `EQ_OK`. The work is in a new routine, `EQSAVE_IERR(IERR_OUT)`; `EQSAVE`
  keeps its argument-less entry and calls it, so `eq/eqmenu.f90` (the `S`
  command) and `tr/f77/trfile.f` are unchanged. `IERR_OUT` is `FWOPEN`'s
  failure (a directory that is missing or not writable, `MODEFW=3` and an
  existing file), or 9 when the file was opened and a `WRITE` or the `CLOSE`
  reported an error (an existing file without write permission, which used
  to end the program at the first `WRITE`) or the file is shorter than what
  was written to the unit. The comparison of the two lengths is there
  because a write the system refuses is not always reported: measured with
  gfortran 15 on macOS, a save to a new file under a file size limit
  returned success over a short file, no `WRITE` and not the `CLOSE` having
  reported it. What is then at the path is left in place and must not be
  loaded. `eq_save` returns
  `EQ_ERR_CALC_FAILED` for those, and `EQ_ERR_INVALID`, touching no file,
  when the fields do not hold the equilibrium of the present parameters (no
  successful `eq_run` yet, a later solve or load that failed, or
  `eq_set_param` of anything but `MODEFR` and `MODEFW` since), for a blank
  `KNAMEQ`, and for `MODEFW` other than 0 or 3 (with 1, 2 and 4 to 7
  `FWOPEN` can read unit 5). The `save` tool replaces an existing file only
  with `overwrite=true`: when it saves it sets `MODEFW` itself (3, or 0). In
  the same change, `eq_run(1)` reports a load that failed: `EQ_READ` called
  `EQCALQ` after `EQDSKR` had failed (`MODELG=5`, a missing file) and
  returned `EQCALQ`'s code, and left `IERR` unassigned for a `MODELG` that
  is no file format; it now starts from `IERR=0`, calls `EQCALQ` only after
  a successful `EQDSKR`, and returns 1 for an unknown `MODELG`.
- **CI: `clean-tree-build` workflow (#250).** Runs the wrapper READMEs'
  fresh-checkout sequence (per-system files, `make -C ../bpsd libbpsd.a`,
  one `make -C <mod> lib<mod>api.so`) for tr / fp / ti / wr / wrx / eq, one
  module per runner with nothing pre-built, and checks that the `.so`
  exists and loads with `RTLD_NOW` (`ctypes.CDLL`). Triggered by changes to
  Makefiles, `make.header.org`, Fortran sources and includes, `mtxp/`, the
  workflow file and the action; by hand (on the ref chosen in the dispatch)
  and weekly on `develop` once the workflow file reaches `master` (a
  dispatch or schedule needs the file on the default branch, which
  carries no workflow files yet). The pytest and mono-build
  jobs pre-build the whole PIC chain first, which is why #230 regressed
  unnoticed. The `make.header` heredoc and the `mtxp/make.mtxp` copy that
  those two jobs carried as KEEP-IN-SYNC steps are now the composite action
  `.github/actions/provision-build-env`, shared by all three.
- **C ABI: every library reports its state-struct layout, and the Python
  wrappers refuse a mismatch (#246).** `X_state_abi_version()` returns
  `X_STATE_ABI_VERSION` (now a `PARAMETER` in `X_state.f90`, mirrored by
  the `#define` in `X_api.h`; tr and tot stay at 2, eq / fp / ti / wr / wrx
  start at 1) and `X_state_size()` the `sizeof` of the `BIND(C)` type, both
  callable before `X_init`, for tr / fp / eq / ti / wr / wrx / tot and the
  mono image. The C-ABI drivers (`test_negative.c`, `test_run_so.c`) fail
  when either differs from the header; `python/Xlib/_ffi.py::load_library`
  raises `XlibAbiError` when the library's version or size differs from
  `XStateC`, or when the library exports neither symbol (built before this
  change), naming the fix. CI runs the six per-module dlopen drivers
  (`X_api_check_so`) and `libtotapi_mono_inspect` checks the twelve symbols.
  A library and a wrapper from different commits used to fail silently:
  a longer library struct wrote past the wrapper's allocation, a shorter
  one left the appended fields as plausible zeros. The check protects
  callers from this change on; a caller older than it never asks, and
  `X_get_state` still takes no buffer size.
- **TR library: the multi-reaction fusion model of `trx`, selected by
  `MODEL_PNF` and off by default.** `tr/libnf.f90` (the reaction tables
  and reactivities) and `tr/trpnf_multi.f90` (`tr_pnf`) are ported from
  `trx`. `MODEL_PNF` chooses the reaction set: 1 is D-T alone, 2 and 12
  four reactions, 3 six, 4 and 14 thirteen; with 0, the default, fusion is
  the legacy `MDLNF` path as it was. `tr_set_param` takes the name
  `MODEL_PNF` (uppercase only), and the `&TR` namelist takes `model_pnf`;
  `tr_mcp` does not declare it yet, and the reaction count and the
  per-reaction rates are not in `tr_get_state`.
  **It does not replace `MDLNF` yet.** With one reaction (`MODEL_PNF = 1`)
  the model's `SNF`, `PNF` and `TAUF` reach the solve in place of
  `MDLNF`'s, and nothing else does: `PFIN`, `PFCL` and the fusion slot of
  `RNF` and `RTF` stay zero, as in `trx`, so the alpha power fills the fast-ion energy and is
  not passed to the thermal species. On `tr_iter01` at 10 keV after 20
  steps the electron temperature on axis is 10.717 keV, against 10.727 with
  fusion off and 11.237 with `MDLNF = 1`. The reactants are read from
  species 2 and 3 and the alpha goes to species 4, as with `MDLNF`, and
  nothing checks that those are D, T and He4. From 1 to 5 keV the D-T rate
  is within 5 % of the legacy `SIGMAM` since its fit was changed (under
  Fixed; HengyuLi-Ozaki-lab/task-web-client#58). A run that sets both
  switches is refused, since it would count the same alphas twice: by
  `tr_prep`, and by `TRCALC`, before it computes anything, when a switch is
  changed on a prepared case that is not prepared again (the standalone
  `tr2`'s `L` then `C`; through `tot` too before upstream #259, since which
  every set makes the next run prepare again). There a nonzero `MODEL_PNF`
  the case was not prepared for is refused as well, and `MODEL_PNF = 0`
  turns the model off at once.
  With more than one reaction the rates are evaluated and nothing reaches
  the solve: TR has one fusion fast-ion slot (`NFM = 2`).
  What was checked is agreement with `trx`, not with a measurement: on a
  10 keV D-T case the change that `MODEL_PNF = 1` makes to nine global
  quantities and to the temperature profiles is the change it makes in
  `trx` to within 1.2 % (globals) and 2 % (profiles). The comment block
  before `FUSION_DIFFERENTIAL_TOL_SCALAR` in
  `python/trlib/tests/test_model_pnf_dispatch.py` says what that comparison
  cannot see: `SNF`, an error the two codes share, and the outermost radial
  point. The reference is `trx` with five corrections, listed in
  `test_run/baselines/tr_fus_dt_hot/SOURCE.md` and reported upstream
  (k-yoshimi/task#235, #236, #238); the four that are on the fusion path
  are not in the port either. Since the fit was changed (under Fixed) the
  reference has tr's fit too, its correction 7.
  `python/trlib/tests/test_libnf.py` holds the D-T reactivity to the legacy
  `SIGMAM` at the table's points from 1 to 500 keV (6 %; at 1000 keV the
  table is 1.46 times `SIGMAM`), from 1 to 5 keV (5 %) and at nine points
  from 5 to 100 keV (1.3 %), and holds that every reaction's rate is
  finite, not negative and rising from 1 to 50 keV.

### Changed

- **TR library: `tr_run` and `validate()` refuse a zero centre density with
  an edge density** (MS10-DP-ISSP/task-web-client#190). `PN = 0` with
  `PNS > 0` for an active species (outside the UFILE modes `MDLUF` 1/2/3,
  which the check leaves out) was let through as "runs finite", but the
  density then vanishes at the axis and the run fails (`tr_prep`'s impurity
  dilution goes negative on the TST-2 case with `PN(1)` or `PN(2)` at 0;
  species 3 of TST-2 was finite after 2 steps and met a negative temperature
  at step 9) or completes with `WPT`, `Q0`, the betas and `TAUE` NaN (TR's
  defaults with `PN(2) = 0`). `validate()` now reports it as `PN[ns]`
  (`OUT_OF_RANGE`), and `tr_run` returns `TR_ERR_INVALID` before `tr_prep`,
  as for a negative density. **A change of behaviour**: such a run used to
  be made. Not refused: a centre density far below the edge's, which fails
  too (`PN(2)` = 1e-9, 1e-6 and 1e-4 end with `ierr=3` within 10 steps).

- **TR library: a run that ends on an EQ failure or a non-finite state fails in library mode.** The periodic
  `MODELG` 9 re-solve (`NTEQIT`) used to ignore a failing `eq_calc`, and a NaN in the state went on to the end of
  the run. Now the run stops at the first failure with a `tr_last_error` record. `MODELG` 0, 4 and 25, and
  `RIPS` = 0, which returned RC 0 with about 10 non-finite scalars, fail with `NONFINITE` at nt 1 (task-web's
  `non_finite` flag no longer sees them). On flat 9 MA ITER `MODELG` 9 with `NTEQIT` 50 and heating, the run stops
  at t = 12 s (code 103, the axis leaves the plasma), where it printed `XX EQAXIS` lines to 37 s. `tr2` is
  unchanged by this entry (its loop does not test the re-solve); see the #228 entry under Fixed for what changed in
  `tr2`'s `R`.
- **tr / fp / ti libraries, `Tot` and `tot_mcp`: a parameter set after a
  run re-preps the module, whoever set it (#253).** `tr_set_param` /
  `fp_set_param` / `ti_set_param` used to clear the module's private
  "prepared" flag themselves; tot's `tr:` / `fp:` / `ti:` dispatcher wrote
  to the registries directly and left the flag standing, so after a run a
  `Tot.set_param("tr:NSMAX", 3)` continued the old state with `tr_prep`
  skipped and the #189 pre-run species check never fired. The registries
  now count every successful set and `tr_run` / `fp_run` / `ti_run`
  re-prep when the count moved since their last prep. Behaviour change for
  `Tot` and `tot_mcp` only: a set after a run now restarts the module
  (`NT` and `T` back to 0), which is what `trlib` / `fplib` / `tilib` and
  `TotPipeline` have always done; a set the registry refused changes
  nothing. `eq` has no prepared flag on `develop`; the same counter is the
  natural precondition for `eq_save` (#256).

- **FP library: `fp_run` refuses `NRMAX` above `FP_MAX_NRMAX` (100).** Such a
  run was made, and `fp_get_state` then returned rc=3: its results could be
  read only from the log on unit 6 or from `fp_regress.dat`
  (`FP_REGRESS_DUMP=1`). `fp_run` now returns `FP_ERR_INVALID` before any
  work.
- **EQ, TR, FP libraries: `set_param` and `set_param_str` refuse a
  malformed subscript and a string they cannot hold whole.** A scalar's
  `CASE` never looked at the index, so `NTHMAX[zz]` set `NTHMAX`;
  list-directed `READ` took `[1,2]`, `[2 3]` and `[/]`; text after the
  closing bracket was ignored (`PN[1]x` set `PN[1]`). A name was cut to the
  buffer that took it (64 characters at the C entry points, 32 in TR's and
  EQ's registries), so `RR` followed by blanks and anything else was `RR`.
  A string value was cut to the 80 characters of its parameter: TR's and
  FP's `set_param_str` took a path of 100 characters and kept the first 80.
  Each is now code 1 (invalid parameter) and nothing is assigned; a string
  that is longer only by trailing blanks loses nothing and is still taken
  (it must end within 4096 characters of the buffer's end).
  Not changed: a subscript that is a whole number is still taken for a
  scalar (`PROFN1[1]` sets TR's `PROFN1`, which `test_property_fanout.py`
  relies on).
- **TR: `FTAUE` and `FTAUI` return `1.D8` where they divided by an ion
  density of exactly zero**, which gave a number that is not finite (an
  infinity at a positive temperature and electron density). That happens
  with the bootstrap models `MDLJBS` = 1, 2 and 3 on a run with fewer than
  four species, which ask for the absent ones; with the default
  `MDLJBS = 5` it does not, and none of the three baseline cases reaches
  the guard. What the two functions returned as a finite number they still
  return, and no run was found to change against the library before the
  port, 20 steps each: `tr_tst2` (two species) with `MDLJBS` = 1, 2 and 3,
  where the guard is reached, in its 367 state values; `tr_iter01` with
  helium at `1.D-9`, `1.D-12`, `1.D-8` and `1.D-7` in its 567 state values
  and in the transport coefficients of all four species. All of these are
  finite. (With a solved species at exactly zero `tr_iter01` is not a
  number, before the port as after it, and says nothing about the guard.)
  `trx` guards more widely
  (`ABS(n) <= 1.D-8`, ahead of every branch), which also replaces the finite
  time of a species at a trace density and the result of `FTAUE`'s impurity
  branch, which divides by the electron density; the port first took that
  guard, and it was narrowed before any release (with it, helium at `1.D-9`
  moved 182 of 567 state values by up to 2.3e-9). The two functions now
  live in the module `trcoll`, and `COULOG` and `HY` in `trlib` (moved, not
  changed).

### Fixed

- **TR: a failed `MODELG` 9 q-scaling fails the run; every preparation adopts the equilibrium** (#228 findings 3
  and 4, `0dd157d4` and `6a804077` of upstream PR #226, cherry-picked here; #226's own entries are held back by
  `d8b6e4de`, so they are written for the product line). `tr_set_metric` set `tr_eq_init` false after the first
  q-scaling and nothing set it again: a second lifecycle in one process gave NaN for every q, a second preparation
  inside one lifecycle a state that differed from the first by up to 57 %. It sets the flag at the start of every
  preparation, `tr_init` and `tr_finalize` restore it. And the q-scaling went on after a failing `eq_calc`, a bad
  `tr_bpsd_get`/`tr_bpsd_put` status, a zero or non-finite scale factor, or no agreement in 30 iterations; each now
  ends `tr_set_metric` with `ierr` /= 0 and `tr_run` returns `TR_ERR_CALC_FAILED`. `eq_calc` (`eq/equnit.f90`) has an
  optional `IERR` for it; called without it, as `trx` and `trm` do, it is unchanged. With `RIPS` = `RIPE` from 0.01
  to 100 and the rest at the defaults, 0.81 and 0.84, which returned 0 after failed solves, and 11 to 100, which ended
  the process at a run-time check, now fail; 0.83 and 0.85 to 10 give the same state. This is not library mode only:
  `tr_set_metric` is `tr2`'s too, so `tr2`'s `R` stops at `trmenu.f90:74` where it used to run on after a failed
  solve (the `RIPS` 0.81 and 0.84 above), and a second `R` in one `tr2` session under `MODELG` 9 now gives what the
  first gave. `tr2`'s output on a single `R` that succeeds is unchanged.
- **EQ library: `eq_bpsd_put` sizes its arrays again when EQ's grid changes.** It sized `equ1D%rho` and
  `metric1D%rho` once, on its first call, and wrote `NRMAX` points: a later preparation on a bigger EQ grid in the
  same process wrote past the end (a checked build stopped, e.g. tst2 at `NRMAX` 10, then `MODELG` 9). The
  preparation on a changed grid needs the bpsd spline resize too (k-yoshimi/bpsd#7).
- **EQ: a contour extremum at the edge of `YA`, and an `EQMAGS` that could not trace a surface, fail `EQCALQ`.**
  `EQCALQP` and `EQCALQV` refine the top and bottom of each flux surface with `zminmax`, which read `YA` at index 0
  when the extremum was the first or last point; a checked build stopped, others read garbage. `EQCALQ` now returns
  `IERR` = 110 (extremum at the edge, with the reason in `eq_last_error`). `EQCALQP` did not test its two `EQMAGS`
  calls: `RA` 1.8 or 2.0 with `MODELG` 9 (or `RR` 6.2, `RA` 2.0 and the default wall `RB` 1.2 through `eq_run`)
  could not trace the surface ("NOT ENOUGH N"; one cause is a wall smaller than the plasma) and went on to
  the read. They return 111 (surface loop) and 112 (edge surface) with the reason. Callers that ignore
  `EQCALQ`'s status (`tr2`, `trx`, `trm`, `fp`, `wm`, `wmx`, `wr`, `wrx`, `ob/obprep.f90`) now go on after the early
  return where a checked build stopped. Healthy results are bit-identical (58 configurations, base against head).
- **TR: a sawtooth with q below 1 out to the edge read past the mesh.** `TRSAWT` (`tr/trcalc.f90`) printed its
  profiles to two points past the mixing radius, which is `NRMAX` when q stays below 1 to the edge: a bounds-checking
  build stopped the process ("Index '51' of dimension 1 of array 'rm' above upper bound of 50" on PLATO's shape at
  150 kA with `MDLST` 1), others read beyond the arrays. The print stops at `NRMAX`.
- **TR: `MDLEQE` 2 with `MDLEQB` 1 dropped the electron temperature equation.** `TR_TABLE` (`tr/trprep.f90`) took
  equation 3 as the bulk-ion density, which it is only without the B_theta equation; with it, equation 3 is the
  electron temperature, which was then left out of the solve (a PLATO case ran to Te0 117 eV instead of 228 eV). It
  now takes the equation after the electron's temperature and rotation (`MDLEQU`), the bulk-ion density whenever the
  temperatures are solved (`MDLEQT` 1, which the registry does not change). `MDLEQE` 0 and `MDLEQB` 0 are unchanged;
  with the fix `MDLEQE` 2 and 0 reach the same steady state for a hydrogen plasma, as they did with `MDLEQB` 0.
- **TR: a particle source far from every mesh point ended the run in NaN.** `TRPSCA` (`tr/trpsc.f90`) normalised the
  Gaussian by its volume integral, which underflowed to 0 when the centre `PSCR0` lay many widths `PSCRW` from every
  mesh point (outside the plasma, or narrower than the mesh spacing), so the source was infinite. The exponent is
  now taken relative to its smallest value on the mesh: the source is unchanged where it was finite, and otherwise
  the whole rate goes where the Gaussian is largest. No baseline case uses `MDLPSC` 1.
- **EQ library: `validate()` holds the input to what the solve does with it**
  (HengyuLi-Ozaki-lab/task-web-client#37). With `MDLEQF >= 10` the box
  `RGMIN`..`ZGMAX` is read only by `EQAXIS`: the magnetic axis, which starts
  at `(RR, 0)`, must lie in it, and `RGMAX` bounds the plasma's outer edge
  `RR + RA`. `validate()` compared the whole plasma with the box, so
  `ZGMAX` below `RKAP*RA`, or `RGMIN` above `RR - RA`, was reported although
  the run's every scalar is the default box's. It now reports `RR` outside
  `RGMIN`..`RGMAX` and `RGMAX` below `RR + RA` (diagnostic `RR`), and a Z
  range that leaves out `Z = 0`, `ZGMIN = 0` and `ZGMAX = 0` included
  (diagnostic `ZGMIN` or `ZGMAX`, where it named `RKAP`): each of these fails
  (`ierr=103`) or cuts the plasma at `RGMAX`. The geometry checks (this box,
  `RB < RA`, a negative `RIP`) are made for the analytic solve, `run(0)`,
  going by `MODELG`: a file format (3, 5, 8, 9, 15, 25) is taken to be
  loaded with `run(1)`, which brings its own geometry, and every other
  `MODELG` is solved, to the same equilibrium (`EQCALC` does not read
  `MODELG`). So `MODELG` 0, 1 and the other values that `run(1)` cannot load
  are checked like 2 (the box and `RIP` were checked for 2 only), and a file
  format is no longer reported for `RB < RA`. Not seen before the run: an
  axis that leaves the box as it moves (with `RDLT = 0.4` it ends inward of
  `RR`), and a Z bound within rounding of 0. The EQ documentation now says
  what `validate()` checks.
- **EQ library: `validate()` reports the file every load format reads, and
  `MODELG = 15` returns an error where it ended the process**
  (MS10-DP-ISSP/task-web-client#191). `FILE_MISSING` covered a blank
  `KNAMEQ` for `MODELG` 3, 5 and 8 only; it now covers `MODELG` 3, 5, 8, 9
  and 25, and a `KNAMEQ` that names no file too (looked up, as the load opens
  it, relative to the working directory at the time of the call), and
  `KNAMEQ2`, the second file `MODELG = 8` reads, the same way; a load that
  cannot open `KNAMEQ2` names it, where it named `KNAMEQ`.
  `MODELG = 15` reads the fixed file `eqdb.dat`, not `KNAMEQ`: `validate()`
  reports it as `MODELG` when it is not there. Its reader, `eqdsk`
  (`eq/equread.f90`), ended the process with `STOP` for a missing file, one
  it could not open and a read error, and for a file that ended early it
  ran a `BACKSPACE` on the closed unit (a Fortran runtime error) before a
  `read(*,*)` of standard input, the stdio MCP servers' channel. It now
  returns an error for each, reads no standard input, and `eq_last_error`
  names `eqdb.dat` and the reason, e.g. "EQ_READ: MODELG=15 reads the fixed
  file 'eqdb.dat', not KNAMEQ: 'eqdb.dat' not found". Not tested: a load of
  a valid `eqdb.dat` (the repository has none); it cannot work through the
  library as it is, since `eqdsk` then calls `equ_set_psi` with one of the
  three arrays it takes (`eq/equintf.f90`), which this change leaves alone.
- **EQ library: a load or solve whose magnetic axis lies outside its window
  says where both are** (MS10-DP-ISSP/task-web-client#187). With
  `MDLEQF >= 10` a file load holds the axis it finds in the file to the box
  `RGMIN`..`ZGMAX` too (default 1.5..4.5 x -2..2 m), and a small device's
  axis lies outside it: the load failed with "equnit::eq_load failed
  (ierr=103)". `EQAXIS` now gives `eq_last_error` where the axis search ended
  and the window, e.g. "EQAXIS: the search for the magnetic axis ended at
  (R, Z) = (0.3871, 0.0000), outside the box RGMIN..RGMAX = [1.5000, 4.5000],
  ZGMIN..ZGMAX = [-2.0000, 2.0000] that MDLEQF >= 10 holds the axis to: set
  the box around it (ierr=103)", where an analytic solve said "EQCALC failed
  (ierr=103)". `validate()` still cannot
  see it for a load: the axis is known only once the file is read.
- **TR documentation: `CDH` and `CNH` weigh `chi_NC`** (the neoclassical
  `AKNC`), not `chi_NCLASS`: NCLASS needs `MDNCLS`, which the registry does
  not take (HengyuLi-Ozaki-lab/task-web-client#43). Text and comments only.
- **TR library: `libnf`'s reaction rates between the low points of its
  table** (HengyuLi-Ozaki-lab/task-web-client#58). The rates were a cubic
  spline of `<sigma v>` over `log10(T)` through the table's ten points (1,
  2, 5, 10, ... 1000 keV). Below 5 keV, where the tables climb by up to 3.3
  decades from one point to the next, the spline swung: D-T, which `MODEL_PNF = 1`
  passes to the solve, was 12.2 times the legacy `SIGMAM` at 1.2 keV and
  0.10 of it at 2.5 keV, and D-He3 (2.05-4.70 keV) and T-He3 (1.05-1.95 and
  5.10-8.55 keV) were negative. The spline is now of `log10(<sigma v>)`, and
  `sigmav_nf` returns 10 to its power: no rate is negative, the table's
  points keep their values (to 3.4e-14), and D-T is within 5 % of `SIGMAM`
  from 1 to 5 keV and within 1.3 % from 5 to 100 keV. A run with
  `MODEL_PNF = 1` gets another D-T rate off the table's points: from 0.078
  times the old one (at 1.15 keV) to 10.04 times it (at 2.45 keV) under
  5 keV, within 1.82 % of it from 5 to 100 keV.
  `MODEL_PNF = 0`, the default, is unchanged. The `trx` reference of
  `test_run/baselines/tr_fus_dt_hot` takes the same fit (its correction 7,
  branch `ref/trx-regress-capture-58`), and its `metrics.json` was captured
  again: the comparison's worst entry is 0.58 of its tolerance with both on
  the new fit, 0.29 with both on the old one (`SOURCE.md` there, item 7).
- **TR library: a run returns the global results of its last step**
  (HengyuLi-Ozaki-lab/task-web-client#118). `tr_eval` computed them
  (`TRGLOB`: `WPT`, `AJT`, the betas, `TAUE1`, `TAUE2`, `ZEFF0`, `ALI`,
  `RQ1`) only on a step that `NTSTEP`, `NGTSTP` or `NGRSTP` divides, so a run
  whose last step none of the three divides returned an earlier step's: on
  the TST-2 fixture, `NTMAX = 10` with all three at 1000 returned step 0's
  `WPT` 5.39e-7 against 2.98e-6. `tr_eval` now computes them on the last
  step when no output step did, and puts back `TRGLOB`'s reference for
  `WPDOT`, so a run made in several `tr_run` calls ends as one run does, to
  1e-4 (without putting it back, `run(5)` then `run(5)` gave `TAUE2` 1.24e-4
  against 2.84e-4 for `run(10)`). No regression case moves: each ends on an
  output step.
- **TR library: `tr_run` refuses a species without an equation, a species 1
  that is not the electron, and a zero edge density of species 1 or 2**
  (HengyuLi-Ozaki-lab/task-web-client#86 and
  HengyuLi-Ozaki-lab/task-web-client#131). TR places each species by
  its mass alone (`TR_TABLE`): a species that matched no class wrote `NEA`
  with index -1, two in one place or one above `NSMAX` left a species
  without equations (with run-time checks the process stopped in
  `trexec.f90`), and the electron as species 2 ended the run with `WPT` NaN.
  `tr_run` now returns an error and the process lives. With `PN > 0`, a
  zero `PNS` of species 1 or 2 ended the run non-finite, the edge transport
  dividing by it: `tr_run` and `validate()` refuse it; species 3 and above
  stay allowed.
- **EQ and TR libraries: a negative plasma current is refused before the
  run** (HengyuLi-Ozaki-lab/task-web-client#126). EQ's analytic solve does
  not treat the sign of the current: on the ITER geometry `RIP = -15`
  converged with `QAXIS = QSURF = 4.611` (the wall's q) against 0.618 and
  3.201, `BETAT` and `BETAP` 0, `PVOL` -1915 against 798 m^3 and `RAAVE`
  NaN, with no message. `eq_run(0)` now returns `EQ_ERR_INVALID`, the reason
  in `eq_last_error`, and `validate()` reports it; with `MODELG = 9`, where
  TR has EQ solve with TR's own current, `tr_run` and `validate()` refuse
  `RIPS` or `RIPE` < 0. Not covered: the EQ menu's C command, TR's menu, a
  UFILE current.

- **MCP servers: the `mcp` dependency is pinned to `>=1.2,<2`** in the
  seven server `pyproject.toml` files, the CI workflow, the servers' own
  "not installed" message, the READMEs, the Sphinx MCP pages, the
  trlib presentation and its builder, and the 2026-04-18 MCP plan.
  `mcp.server.fastmcp` exists from mcp 1.2.0 (the old floor, 0.9, let
  1.0 and 1.1 in, where the import fails the same way) and mcp 2.0
  removed it, so an unpinned install (`pip install -e
  python/mcp-servers/eq_mcp` on a fresh environment, or the workflow's
  bare `pip install mcp`, which took mcp 2.3.0) left every server with
  `MCP_AVAILABLE = False`: `python -m <mod>_mcp.server` exited 2 and the
  seven `TestBuildServer` classes skipped, so CI was green without
  exercising a single FastMCP construction. The workflow now asserts
  `MCP_AVAILABLE` right after the install, so that skip is a failure
  there. Porting the servers to the 2.x API is separate work. Fix by
  Li Hengyu, cherry-picked from #226.
- **EQ, TR, FP libraries: `set_param` refuses a value outside what it
  takes**, with code 1 and before it assigns: one that is not finite (NaN,
  the infinities), for every name; and for an integer parameter a value
  outside `-HUGE(0)` to `HUGE(0)`, the range every compiler converts alike
  (so `-HUGE(0) - 1` and `2147483647.25` are refused with the rest). Beyond
  the default integer `NINT()` / `INT()` is the compiler's choice (with
  gfortran on arm64 the nearest end of the integer range, and 0 for NaN).
  Such a value was assigned and then was a mesh count or a model switch:
  FP's `NTHMAX = 2**32 + 30` ended the process on every attempt,
  `MODELD = 2**32` ran as a non-zero `MODELD`.
- **`Fplib.run`, `Trlib.run`, `Eq.run`: a step count that is negative or
  does not fit a C `int` (EQ: a mode that does not fit one) is refused
  before the library is called.** ctypes hands an integer to a `c_int`
  argument modulo 2**32: `Fplib.run(2**32 + 3)` ran three steps,
  `Trlib.run(10 - 2**32)` ten, and `Eq.run(2**32)` mode 0.
- **`eq_mcp`, `tr_mcp`, `fp_mcp`: `set_params` and `set_param` refuse a
  number that is not finite and an integer too large for a float**, with
  the server's own "invalid numeric value" error and before the library is
  called. `float()` takes the strings `"nan"`, `"inf"` and `"1e309"`, so in
  a list or a dict they reached the registry as NaN or an infinity; and
  `float(10**400)` raised an `OverflowError` the bulk path did not catch.
  A string that is a finite number is still taken in a list or a dict.
- **FP library: `fp_run` refuses the counts the solver cannot run with**,
  before any work, with `FP_ERR_INVALID` and one `XX fp_run: ...` line per
  violation on unit 6 (`fp_param_check` in `fp/fp_param_registry.f90`).
  They were accepted when set and then ran past an array bound (an abort
  when built with run-time checks), ended the host process, or never
  returned: `NRMAX` below 1; `NPMAX` or `NTHMAX` below 2; `LMAXFP` below 0
  or at the largest integer (the iteration's exit, `N_IMPL = 1 + LMAXFP`,
  overflows and a step never ends); `NSAMAX` above `NSBMAX`; an evolved
  species number outside 1 to `MIN(NSMAX, NSBMAX)`; a background species
  number outside 1 to `NSMAX`.
- **MCP servers `eq_mcp`, `tr_mcp`, `tot_mcp`: Fortran output no longer
  reaches the JSON-RPC pipe.** A stdio server's fd 1 is the pipe to its
  client, and the library's `WRITE(6,...)` went into it: in one stdio
  session (`initialize`, `init`, `run`) 9 of the 12 stdout lines of
  `tr_mcp` and of `tot_mcp` were not JSON-RPC, and 2 of 5 of `eq_mcp` with
  `run(mode=1)`. `main()` now calls `_fd_isolation.install()` (one module
  shared by the three servers, `python/_fd_isolation.py`, with one flag for
  the process) immediately before the stdio server is built: fd 1 is
  redirected to stderr and `sys.stdout` keeps the pipe. Importing a server
  module leaves fd 1 and `sys.stdout` of the importing process alone (#227
  item 1); `--help` and `--print-tools` print to the terminal as before.
  Two descriptor layouts in which the redirect alone does nothing are
  handled: with fd 2 closed it is opened on the null device first (and
  `sys.stderr` given it), and when stdout and stderr are the same file (the
  host merged them, `2>&1`) fd 1 goes to the null device and one line on
  stderr says that what is written to fd 1 is discarded. A terminal on
  both counts as the same file too: a server started by hand in a
  terminal shows that line and no longer the library's output. Where
  `fstat` gives a descriptor no identity (Windows for a pipe or a console)
  the merged layout is not recognised and fd 1 goes to stderr as usual.
- **tot docs and `tot_mcp`: string parameters and the tool count** (#274).
  The tot Sphinx pages showed `tot.set_param_str("fp:KNAMEQ", ...)` and
  `("wr:KNAMEQ", ...)`, which tot refuses: it passes string values on for
  `eq:` and `tr:` only. They now use `eq:` and `tr:`, and say that
  `fp:KNAMEQ` goes through `totlib.TotPipeline.set_param` (`tot_mcp`'s
  `run_pipeline` `params`), that `ti`, `wr` and `wrx` take no strings, and
  that `eq:KNAMEQ` is `pl`'s, which fp reads too (one variable in the mono
  image). `tot_mcp` registers 10 tools, not 9 (`__init__.py`, the Sphinx MCP
  pages, now with a `run_pipeline` row); its README says where `fp:KNAMEQ`
  goes. `tot_mcp`'s hints: a refused string set no longer gets the hint to
  namespace its name but one that names the string parameters (the seven
  `eq:` file names, `tr:KNAMEQ`) and says to send numbers as numbers; a
  refused numeric set of a namespaced name points at `describe_parameters`;
  a string totlib rejects itself (too long, not ASCII) and a refused
  `tot_run` argument get no hint. The `tot_mcp` server instructions,
  docstrings and README, `totlib`'s errors, README and examples, and
  `docs/tot-library/architecture.md` no longer say that `run` and
  `get_state` are stubs until L-6 (#96, #124), nor that `tot_mcp` has a
  `set_param_str`; `architecture.md`'s quirks and limitations follow the
  code (eq in the fan-out, one live `Tot()` per process).
- **EQ: T(psi) of the toroidal-current model (`MDLEQF` 0, and 5 through
  `MOD(MDLEQF,5)`) has the factor 4*pi**2 on its pressure term.** EQ's psi
  is the total poloidal flux and T = 2*pi*R*B_phi. Integrated from the
  boundary, the model's j_zeta0 = -2*pi*R0*dp/dpsi - T*dT/dpsi/(2*pi*mu0*R0)
  gives T**2 = (2*pi*BB*RR)**2 + 4*pi*mu0*R0*TJ*int(HJPSI dpsi)
  - 8*pi**2*mu0*R0**2*p. `EQRHSV` and `EQCALP` (`TT`, `TTV`, `TTPS`) had
  -2*mu0*R0**2*p: the conversion of 2005-01-22 from per-radian flux and
  F = R*B_phi multiplied the current term by 2*pi and left this one as it
  was. The psi that `EQCALC` solves was right: its current used the correct
  -2*pi*R*dp/dpsi. Only the exported T did not belong to it.
  - **Results change.** For `MDLEQF` 0 with `MDLEQA` 0 and positive
    pressure, on the same poloidal-flux surface, T (`TTPS`, `TTS`, bpsd
    `equ1D%pip`), q and the toroidal flux integrated from q (`PSIT`, `PSITA`)
    are lower than before, and the normalised rho_t mapping changes.
    psi(R,Z) and the current are unchanged. In `MDLEQF` 0 with `MDLEQA` 1,
    and in `MDLEQF` 5 (whose profiles come through `EQPSITN` and q), T
    feeds the toroidal-flux coordinate of the profiles, so psi changes too.
    `MDLEQF` 1 to 4 and 6 to 9 are unchanged.
  - **Reference data.** The equivalence baseline of `tot_ht6m_short`, whose
    equilibrium CI solves with the standalone `tot` before the test, moves
    by at most 7.3e-6 relative. It and its fallback eqdata
    `python/totlib/tests/fixtures/eqdata-HT6M` are regenerated on the CI
    compiler (`regen-baselines.yml`); the eqdata differs only in T and what
    is computed from it. Data made earlier with the old T:
    - the baselines `test_run/baselines/eq_iter01`, `eq_tst2`, `eq_jt60`
      (standalone solves; `eq_jt60` with `MDLEQA` 1), and `tr_iter01`,
      `tr_tst2`, which run on those equilibria;
    - the committed `eqdata.ITER01` / `eqdata.TST-2` under
      `python/eqlib/tests/fixtures/` and `python/trlib/tests/fixtures/`,
      and `python/totlib/tests/fixtures/eqdata.demo2014`.
    A test that loads one of those committed files (MODELG 3) is unchanged:
    the load path does not compute T. In CI, `tot_ht6m_short` loads the file
    CI has just solved instead. A fresh standalone solve of any of these
    cases gives the new T. So a local `test_run/run_tests.sh` reports a
    regression for `eq_iter01`, `eq_tst2` and `eq_jt60` and skips the
    `tr_*` cases that depend on them; after it, on Linux, the eqlib
    equivalence tests, which prefer its `test_output/<case>/` eqdata to the
    committed fixtures, fail too. The Python-test CI does not run it.
  - **Size.** Measured on an ITER-like case, on axis: 1.1 % at beta_t
    0.76 %, 2.3 % at 1.5 %, 3.9 % at 2.5 %.
  - **What the old T implied.** The current that the exported p' and TT'
    gave was about (1 + 0.77 beta_p) times Ip. It is now Ip.
  - **Also corrected:** the same expression in `eq/eqcalx.f`, which no make
    target builds; and the descriptions that called T (and F, FF0 to FF2)
    R*B_phi where EQ stores 2*pi*R*B_phi (`python/eqlib/state.py` and its
    README, `eq_mcp`'s parameter and state descriptions, the Sphinx state
    pages, the library manual and the quickstart notebook).
  - **Test.** `python/eqlib/tests/test_gs_consistency.py` integrates the
    current of the exported profiles over the plasma and compares it with
    the solver's own, and checks that EQCALV's `TTV` and the exported
    `TTPS` are one function of the normalised flux.
  - **Not fixed here.** In `MDLEQF` 0 with `MDLEQA` 1, and in `MDLEQF` 5,
    the current term of T**2 has a separate inconsistency (`HJPSID = FD/FDN`
    in `EQJPSI` divides an integral over normalised toroidal flux by the
    local q/psi_ta).
- **MCP servers `ti_mcp`, `wr_mcp`, `wrx_mcp`: the same fd isolation** (#262).
  The three servers had the layout of the other three and the same exposure:
  `main()` now calls `_fd_isolation.install()` immediately before the stdio
  server is built, importing a server module leaves the importing process's
  fd 1 and `sys.stdout` alone, and `--help` / `--print-tools` / the
  missing-SDK path return before anything is redirected. Each server's
  `tests/test_fd_isolation.py` runs the shared checks
  (`python/mcp-servers/fd_isolation_cases.py`), and
  `python/tests/test_fd_isolation.py` checks that all six servers run every
  one of them. `fp_mcp` follows in #232.
- **MCP server `fp_mcp`: the same fd isolation** (#232). `fp_mcp` had the
  most of it: `FPWRTPRF` writes the radial profile table to unit 6 once at
  preparation and then every `NTG2STEP` steps (every step by default), so
  the lines that are not JSON-RPC grew with `NTMAX`: in one stdio session
  (`initialize`, `init`, `run`, library defaults) 63 of the 66 stdout lines
  at `NTMAX=1`, 83 of 86 at `NTMAX=2`. `main()` now calls `_fd_isolation.install()`
  immediately before the stdio server is built, as the other six servers
  do; its `tests/test_fd_isolation.py` runs the shared checks, and
  `python/tests/test_fd_isolation.py` checks all seven servers.
- **MCP servers on Windows: fd 0 leaves the stdin pipe too** (product
  line; it was in each server's own isolation before the shared module).
  Windows serialises the operations on a synchronous pipe, so while the
  MCP reader thread waits on stdin, the gfortran runtime's `fstat()` /
  `isatty()` of fd 0 when the library's DLL loads, inside the first tool
  call, blocks forever. On Windows `_fd_isolation.install()` now also
  saves the stdin pipe on a descriptor of its own, rebuilds `sys.stdin` on
  it and opens fd 0 on the null device; when the redirect of fd 1 then
  fails, fd 0 gets its pipe back. Elsewhere fd 0 stays as it was.
  `python/tests/test_fd_isolation.py` runs that branch on POSIX systems
  (its logic, not the Windows pipes themselves).
- **MCP servers `eq_mcp` and `tr_mcp`: `main()` returns 0 when the
  session ends** (product line), as upstream's `main()` and #226's do. It
  ended the process with `os._exit(0)`, to skip a Python teardown that
  could abort in `tr_finalize`; that abort was a double `DEALLOCATE`,
  which `DEALLOCATE_TRCOMM` no longer does (`tr/trcomm.f90`). The
  libraries are now finalized on the way out: 20 stdio sessions of each
  server, every one exited with 0.
- **CI: the four required jobs and clean-tree-build run on `ubuntu-24.04`**
  (HengyuLi-Ozaki-lab/task#17, and the module build after it), where they
  said `ubuntu-latest`. Between 2026-10-28 and 2026-11-08 `ubuntu-latest`
  became `ubuntu-26.04`, whose gfortran 15.2 moves six of the 1e-10
  equivalence cases (`eq_tst2`, FP `dt1` and `iter01`, WRX `demo`, `iter01`
  and `jt60`) by 1e-10 to 1e-9 from baselines that pass on gfortran 13.3,
  so every run failed on the same tree that had passed.
  `regen-baselines.yml` already pinned `ubuntu-24.04`; moving to a newer
  image is a regeneration of the baselines with it.

## TR Phase L — library-ization (2026-04-18)

Phase L turned TASK/TR from a CLI-only Fortran program into an
additionally-loadable shared library with a Python wrapper. The `tr2`
binary and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #2)** — Phase 0 regression-test infrastructure:
  `test_run/baselines/tr_{iter01,m0904,tst2}.json`,
  `tools/extract_tr_metrics.py`, `tools/compare_metrics.py`.
- **L-1 (2026-04-18, PR #21)** — `tr/Makefile` graphics split; `tr2`
  still links graphics, `libtrapi.so` builds are graphics-free.
- **L-2 (2026-04-18, PR #27)** — C ABI foundation: `tr/tr_api.h`,
  `tr/tr_api.f90`, `tr/tr_state.f90`; 5 entry-point stubs exported
  from `libtrapi` returning `TR_ERR_NOT_IMPL` (ierr=4).
- **L-3 (2026-04-18, PR #33)** — Parameter registry
  (`tr/tr_param_registry.f90`, ~38 `SELECT CASE` entries) and real
  bodies for `tr_init` / `tr_run` / `tr_get_state` / `tr_finalize`.
  `tr_set_param` accepts `"NAME"` and `"NAME[idx]"` (1-origin).
- **L-4 (2026-04-18, PR #35)** — `make -C tr libtrapi.so` builds the
  shared library. PIC variants (`*_pic.a`) of `lib`, `pl`, `eq`, `ob`,
  `mtxp`, `bpsd` added to participating Makefiles. Non-PIC archives
  and `tr2` are unchanged.
- **L-5 (2026-04-18, PR #44)** — Python wrapper `python/trlib/`:
  `Trlib` context manager, `TrState` dataclass, exception hierarchy
  mirroring `enum tr_error`, `_ffi` ctypes layer with `TRLIB_PATH`
  override and `RTLD_LAZY` loading.
- **L-6 (2026-04-18, PR #53)** — 4-layer test suite wired into
  `test_run/test_definitions.conf`:
  `trlib_equivalence` (Layer 1 vs Phase 0 baselines, tol `1e-10`),
  `trlib_c_abi` (Layer 2 `make -C tr tr_api_check_all`),
  `trlib_ffi` + `trlib_wrapper` (Layer 3 Python),
  `trlib_sweep` (Layer 4 3×3 RR×BB smoke).
- **L-7 (2026-04-18, this PR)** — User-facing documentation:
  rewritten `python/trlib/README.md`, example scripts
  (`quickstart.py`, `parameter_sweep.py`, `state_dump.py`),
  architecture doc (`docs/tr-library/architecture.md`), and this
  changelog.

### Known issues

- `tr_m0904` Layer 1 comparison drifts from its Phase 0 baseline by
  `~1e-8` under current `tr2`; it is pinned to the baseline rather
  than regenerated. `tr_iter01` and `tr_tst2` match to `1e-10`.
- String parameters (`KNAMEQ`, `KNAMTR`, etc.) are not yet wired
  through `tr_set_param` (design spec §4.3 deferral).
- Single instance per process only — TR globals are COMMON-block
  state.

## TI Phase L — library-ization (2026-04-18)

Phase L mirrors the TR library-ization for the TASK/TI impurity-
transport module: the same 5 C ABI functions, the same wrapper
architecture, parameter registry, and 4-layer test structure. The
`ti` CLI binary and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #12)** — Phase 0 regression-test
  infrastructure for TI: `test_run/baselines/ti_{min,ar,w}/`,
  `tools/extract_ti_metrics.py`, `test_run/inputs/ti_*.in`.
- **L-1 (2026-04-18, PR #22)** — `ti/Makefile` split into
  CORE / GRAPHICS / MENU `SRCS` groups so graphics-free Fortran
  compilations can be staged without touching the `ti` binary
  build.
- **L-2 (2026-04-18, PR #28)** — C ABI foundation: `ti/ti_api.h`,
  `ti/ti_api.f90`, `ti/ti_state.f90`; 5 entry-point stubs returning
  `TI_ERR_NOT_IMPL` (ierr=4), plus `ti_api_check` target and first
  C-side smoke tests under `ti/tests/c_abi/`.
- **L-3 (2026-04-18, PR #34)** — Parameter registry
  (`ti/ti_param_registry.f90`, ~35 `SELECT CASE` entries covering
  scalars, 1-D arrays, and 2-D `[i,j]` subscripts) plus real bodies
  for `ti_init` / `ti_run` / `ti_get_state` / `ti_finalize`.
  `ti_set_param` accepts `"NAME"`, `"NAME[i]"`, and `"NAME[i,j]"`
  (1-origin). PA/PM naming deliberately exposes only `PA` (the
  PLCOMM true name).
- **L-4 (2026-04-18, PR #41)** — `make -C ti libtiapi.so` builds
  the shared library. PIC variants (`*_pic.a`) of `lib`, `pl`,
  `eq`, `adpost`, `open-adas/adf11`, `mtxp`, `bpsd` added to
  participating Makefiles. Non-PIC archives and the `ti` binary are
  unchanged. (Target is staged on feature branch; see Known issues.)
- **L-5 (2026-04-18, PR #47)** — Python wrapper `python/tilib/`:
  `TiLib` / `Tilib` context manager, `TiState` dataclass,
  exception hierarchy mirroring `enum ti_error`, `_ffi` ctypes
  layer with `TILIB_PATH` override and `RTLD_LAZY` loading.
- **L-6 (2026-04-18, PR #57)** — 4-layer test suite wired into
  `test_run/test_definitions.conf` (`tilib_equivalence` Layer 1
  vs Phase 0 baselines at tol `1e-10`, `tilib_c_abi` Layer 2
  `make -C ti ti_api_check_all`, `tilib_ffi` + `tilib_wrapper`
  Layer 3 Python, `tilib_sweep` Layer 4 3×3 DT×NRMAX smoke) plus
  Ar fixture applying atomic mass via `PA[3]` instead of the dead
  `PM` alias.
- **L-7 (2026-04-18, this PR)** — User-facing documentation:
  rewritten `python/tilib/README.md`, example scripts
  (`quickstart.py`, `parameter_sweep.py`, `state_dump.py`),
  architecture doc (`docs/ti-library/architecture.md`), and this
  changelog entry.

### Known issues

- `libtiapi.so` Makefile target has not yet merged into `develop`;
  it lives on `feature/ti-library-L4-shared-lib` and is pending a
  follow-up PR. The wrapper, examples, and tests all tolerate a
  missing library by skipping FFI-level checks.
- `ti_ar` baseline shows small drift similar in character to
  `tr_m0904`; when regeneration is needed pin the baseline rather
  than re-running against a moving `ti` output.
- String parameters (`KID_NS`, ...) are not wired through
  `ti_set_param`. Argon fixtures work around this by setting
  `NPA[3]=18` and letting `tiinit.f90` recompute the label.
- Per-species diffusion knobs `DN0`, `DT0`, `DR0`, `DRS`,
  `DN0_NS[i]` are not yet in the registry.
- Single instance per process only — TI globals are COMMON-block
  state.

## FP Phase L — library-ization (2026-04-18)

Phase L mirrors the TR library-ization for the TASK/FP Fokker-Planck
module: the same 5 C ABI functions, the same wrapper architecture,
parameter registry, and 4-layer test structure. The `fp` CLI binary
and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #13)** — Phase 0 regression-test
  infrastructure for FP: `test_run/baselines/fp_{iter01,jt60,dt1}/`,
  `fpregress.f90` (env-guarded high-precision dump),
  `test_run/scripts/extract_fp_metrics.py`, and the three baseline
  test cases `fp_iter01`, `fp_jt60`, `fp_dt1` wired into
  `test_definitions.conf`.
- **L-1 (2026-04-18, PR #26)** — `fp/Makefile` split into
  CORE / GRAPHICS / MENU `SRCS` groups so graphics-free Fortran
  compilations can be staged without touching the `fp` binary
  build.
- **L-2 (2026-04-18, PR #29)** — C ABI foundation: `fp/fp_api.h`,
  `fp/fp_api.f90`, `fp/fp_state.f90`; 5 entry-point stubs returning
  `FP_ERR_NOT_IMPL` (ierr=4), plus first C-side compile-only smoke
  tests under `fp/tests/c_abi/`.
- **L-3 (2026-04-18, PR #37)** — Parameter registry
  (`fp/fp_param_registry.f90`) and real bodies for
  `fp_init` / `fp_run` / `fp_get_state` / `fp_finalize`.
- **L-4 (2026-04-18, PR #43)** — `make -C fp libfpapi.so` builds the
  shared library.
- **L-5 (2026-04-18, PR #55)** — Python wrapper `python/fplib/`.
- **L-6 (2026-04-18, PR #56)** — 4-layer test suite wired into
  `test_run/test_definitions.conf`.
- **L-7 (2026-04-18, PR #68)** — User-facing documentation:
  rewritten `python/fplib/README.md`, example scripts,
  architecture doc (`docs/fp-library/architecture.md`).

## WR Phase L — library-ization (2026-04-18)

Phase L mirrors the TR library-ization for the TASK/WR ray-tracing
module. The `wr` CLI binary and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #15)** — Phase 0 regression-test
  infrastructure for WR.
- **L-1 (2026-04-18, PR #24)** — `wr/Makefile` SRCS split.
- **L-2 (2026-04-18, PR #30)** — C ABI foundation: `wr/wr_api.h`,
  `wr/wr_api.f90`.
- **L-3 (2026-04-18, PR #36)** — Parameter registry and real
  bodies. Includes the Bugbot HIGH fix (double-free on
  finalize-then-reinit): `wr_allocate` SAVE flags moved to module
  scope, `wr_reset_alloc_state` added and called from `wr_finalize`,
  and every `wr_deallocate` guarded with `ALLOCATED()`.
- **L-4 (2026-04-18, PR #42)** — `make -C wr libwrapi.so` builds
  the shared library.
- **L-5 (2026-04-18, PR #46)** — Python wrapper `python/wrlib/`.
- **L-6 (2026-04-18, PR #60)** — 4-layer test suite wired into
  `test_run/test_definitions.conf`.
- **L-7 (2026-04-18, this PR)** — User-facing documentation:
  rewritten `python/wrlib/README.md`, example scripts
  (`quickstart.py`, `parameter_sweep.py`, `state_dump.py`),
  architecture doc (`docs/wr-library/architecture.md`), and this
  changelog entry.

### Known issues

**FP:**
- `fp_finalize` does not deallocate FPCOMM arrays (asymmetry between
  `fp_allocate` and `fp_deallocate`); long-running drivers can leak
  allocations.
- String parameters (`KNAMFP`, ...) are not wired through
  `fp_set_param`.
- Mesh caps `FP_MAX_NRMAX=100` and `FP_MAX_NSAMAX=8` are baked into
  the exported `fp_state_t`.
- Single instance per process only.

**WR:**
- Post-finalize state-reset invariant: `wr_finalize` must call
  `wr_reset_alloc_state` to zero `wr_allocate`'s SAVE flags
  (`INIT`, `NRAYMAX_SAVE`, `NSTPMAX_SAVE`). Do not remove this hook
  (PR #36 Bugbot HIGH).
- Beam tracing (`mode_beam /= 0`) is not exposed through
  `wr_get_state`; only ray-tracing outputs are surfaced.
- Input scalars (`RF`, `RPI`, ...) are not echoed in
  `wr_get_state`.
- String parameters are not wired through `wr_set_param`.
- Single instance per process only.

## WRX Phase L — library-ization (2026-04-18)

Phase L mirrors the WR library-ization for the TASK/WRX extended
ray-tracing module: the same 5 C ABI functions, the same wrapper
architecture, parameter registry, and 4-layer test structure. The
`wrx` CLI binary and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #16)** — Phase 0 regression-test
  infrastructure for WRX (`wrx_iter01` baseline,
  `tools/extract_wrx_metrics.py`, `test_run/inputs/wrx_iter01.in`).
- **L-1 (2026-04-18, PR #25)** — `wrx/Makefile` SRCS split into
  CORE / GRAPHICS / MENU groups so graphics-free Fortran
  compilations can be staged without touching the `wrx` binary
  build.
- **L-2 (2026-04-18, PR #31)** — C ABI foundation: `wrx/wrx_api.h`,
  `wrx/wrx_api.f90`; 5 entry-point stubs returning
  `WRX_ERR_NOT_IMPL` (ierr=4), plus first C-side smoke tests under
  `wrx/tests/c_abi/`.
- **L-3 (2026-04-18, PR #38)** — Parameter registry
  (`wrx/wrx_param_registry.f90`, ~70 `SELECT CASE` entries covering
  scalars and 1-D arrays) plus real bodies for `wrx_init` /
  `wrx_run` / `wrx_get_state` / `wrx_finalize`. `wrx_set_param`
  accepts `"NAME"` and `"NAME[idx]"` (1-origin).
- **L-4 (2026-04-18, PR #52)** — `make -C wrx libwrxapi.so` builds
  the shared library. PIC variants (`*_pic.a`) of `lib`, `pl`, `eq`,
  `dp`, `mtxp`, `bpsd` added. Non-PIC archives and the `wrx` binary
  are unchanged.
- **L-5 (2026-04-18, PR #59)** — Python wrapper `python/wrxlib/`:
  `Wrxlib` context manager, `WrxState` dataclass, exception
  hierarchy mirroring `enum wrx_error`, `_ffi` ctypes layer with
  `WRXLIB_PATH` override and `RTLD_LAZY` loading.
- **L-6 (2026-04-18, PR #67)** — 4-layer test suite wired into
  `test_run/test_definitions.conf`:
  `wrxlib_c_abi` (Layer 2 `make -C wrx wrx_api_check_all`),
  `wrxlib_ffi` + `wrxlib_wrapper` (Layer 3 Python),
  `wrxlib_equivalence` (Layer 1 vs Phase 0 baselines, tol `1e-10`,
  `WRX_RUN_OK` gated), `wrxlib_sweep` (Layer 4 3×3 RFIN × ANGPIN
  smoke, `WRX_RUN_OK` gated).
- **L-7 (2026-04-19, this PR)** — User-facing documentation:
  rewritten `python/wrxlib/README.md` (with prominent `WRX_RUN_OK`
  gate section), example scripts (`quickstart.py`,
  `parameter_sweep.py`, `state_dump.py` — all `--dry-run` capable),
  architecture doc (`docs/wrx-library/architecture.md`, including a
  dedicated `libgrf::grd1d` limitation analysis with remediation
  roadmap), and this changelog entry.

### Known issues

**WRX:**
- **`wrx_run` may segfault on the shared build** because
  `wrcalpwr.f90` retains an unconditional call to `libgrf::grd1d`
  that the L-1 graphics split deliberately excludes from
  `libwrxapi.so`. `RTLD_LAZY` loading hides the unresolved symbol
  at `dlopen` time; the segfault occurs the first time `wrcalpwr`
  is reached. Mitigation: every `.run()`-dependent test class is
  gated behind `WRX_RUN_OK=1`; the C-side `test_run_so.c` skips
  `wrx_run` likewise. Remediation roadmap (stub `grd1d`,
  conditionalise `wrcalpwr`, or PIC `libgrf_pic.a`) tracked in
  `docs/wrx-library/architecture.md`.
- Beam tracing (`mode_beam /= 0`) is not exposed through
  `wrx_get_state`; only ray-tracing per-species power-deposition
  outputs are surfaced.
- Input scalars (`RFIN`, `RPIN`, ...) are not echoed in
  `wrx_get_state`.
- String parameters are not wired through `wrx_set_param`.
- Single instance per process only — WRX globals are COMMON-block
  state.

## EQ Phase L — library-ization (2026-04-19)

Phase L mirrors the TR library-ization for the TASK/EQ MHD-equilibrium
module. The structure matches the sibling tr/ti/wr/fp libraries with
one EQ-specific addition: a **6th C ABI entry point**
`eq_set_param_str` to set the seven `CHARACTER(LEN=80)` namelist keys
(`KNAMEQ`, `KNAMEQ2`, `KNAMWR`, `KNAMWM`, `KNAMFP`, `KNAMFO`,
`KNAMPF`). The `eq` CLI binary and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #54)** — Phase L-0 regression-test
  infrastructure for EQ: `test_run/baselines/eq_iter01/`,
  `test_run/baselines/eq_tst2/`, `eqregress.f90` (env-guarded
  high-precision dump), `test_run/scripts/extract_eq_metrics.py`,
  and the two baseline test cases `eq_iter01`, `eq_tst2` wired into
  `test_definitions.conf`.
- **L-1 (2026-04-18, PR #65)** — `eq/Makefile` split into
  `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` groups so graphics-free
  Fortran compilations can be staged without touching the `eq`
  binary build.
- **L-2 (2026-04-18, PR #70)** — C ABI foundation: `eq/eq_api.h`,
  `eq/eq_api.f90`, `eq/eq_state.f90`; 5 entry-point stubs returning
  `EQ_ERR_NOT_IMPL` (ierr=4), plus first C-side compile-only smoke
  tests under `eq/tests/c_abi/`.
- **L-3 (2026-04-18, PR #78)** — Parameter registry
  (`eq/eq_param_registry.f90`, 94 `SELECT CASE` entries covering
  ~78 numeric scalars/ints, 5 array families with the 0-origin
  `PSIB[0..5]` and 1-origin `RIPFC/RPFC/ZPFC/WPFC[1..10]`, and 7
  string keys via `eq_set_param_str`) plus real bodies for `eq_init`
  / `eq_run(mode=1)` / `eq_get_state` / `eq_finalize`. The 6th C ABI
  entry `eq_set_param_str` is added here for `CHARACTER(LEN=80)`
  namelist parameters.
- **L-4 (2026-04-18, PR #80)** — `make -C eq libeqapi.so` builds the
  shared library. PIC variants (`*_pic.a`) of `lib`, `pl`, `bpsd`,
  `mtxp` added to participating Makefiles. Non-PIC archives and the
  `eq` binary are unchanged. Includes explicit PIC inter-module
  dependency declarations to prevent parallel-build races.
- **L-5 (2026-04-18, PR #86)** — Python wrapper `python/eqlib/`:
  `Eq` context manager, `EqState` dataclass, exception hierarchy
  mirroring `enum eq_error`, `_ffi` ctypes layer with `EQLIB_PATH`
  override and `RTLD_LAZY` loading. `Eq.run()` defaults to `mode=1`
  so `eq.run()` (no arg) performs the canonical EQDSK load.
- **L-7 (2026-04-19, this PR)** — User-facing documentation:
  rewritten `python/eqlib/README.md` with full 6-fn API table,
  60+ registry parameters, `EqState` field table, exception
  hierarchy, EQ-specific quirks (PSIB 0-origin / `set_param_str`
  for KNAMEQ / `eq.run(mode=1)` default), and CLI→library migration
  notes; example scripts (`quickstart.py`, `parameter_sweep.py`,
  `state_dump.py` — all with `--dry-run`); architecture doc
  (`docs/eq-library/architecture.md`) with ASCII diagram and Phase L
  completion matrix; this changelog entry.

### Known issues

- **L-6 (4-layer test integration) is not yet merged.** Wrapper-only
  tests run via `python3 -m unittest discover python/eqlib/tests`;
  the `eqlib_*` cases in `test_run/test_definitions.conf` will land
  with the L-6 PR.
- `eq_run(mode=0)` (direct EQCALQ entry) returns
  `EQ_ERR_NOT_IMPL`; only `mode=1` (EQDSK load via
  `equnit::eq_load`) is currently wired. Other modes raise
  `EqlibNotImplementedError`.
- `eq_state_t` exports 1-D psi-surface profiles, R/Z grids, and 12
  scalars only. 2-D fields (`PSIRZ`, `RPS(NPSM,NTHM)`,
  `ZPS(NPSM,NTHM)`) require a future C-ABI extension.
- `PSIB` is 0-origin (Fortran `REAL(8) :: PSIB(0:5)`), unlike all
  other 1-D array parameters. Bare `"PSIB"` with no subscript is
  rejected by the registry; always use `set_param("PSIB[i]", v)` for
  `i ∈ 0..5`.
- String parameters (`KNAMEQ` and the six siblings) require the
  dedicated `set_param_str` method — they cannot be passed through
  `set_params(**kwargs)` or `set_param`.
- Single instance per process only — EQ globals are COMMON-block
  plus `eqcom*_mod` module variables.

## TOT Phase L — library-ization (2026-04-19)

Phase L turned TASK/TOT (the integrated transport orchestrator) from a
CLI-only Fortran program into an additionally-loadable composite
shared library with a Python wrapper. TOT is the orchestrator: its
parameter space is the **union** of the six per-module registries
(`eq`, `tr`, `fp`, `ti`, `wr`, `wrx`), so the TOT-specific addition
vs the sibling tr/eq/ti/fp/wr/wrx libraries is **namespaced parameter
dispatch** — every parameter name passed through `tot_set_param`
must carry an `eq:` / `tr:` / `fp:` / `ti:` / `wr:` / `wrx:` prefix.
The `tot` CLI binary and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #17)** — Phase L-0 regression-test
  infrastructure for TOT: `test_run/baselines/tot_*/`,
  `totregress.f90` (env-guarded high-precision dump), Phase-0 baseline
  cases wired into `test_definitions.conf`.
- **L-1 (2026-04-18, PR #23)** — `tot/Makefile` graphics split via
  `TOT_NO_GRAPHICS` preprocessor guard around `GSOPEN` / `GSCLOS`
  call sites; standalone `tot` binary still links graphics, the
  upcoming `libtotapi.so` build path is graphics-free.
- **L-2 (2026-04-18, PR #32)** — C ABI foundation: `tot/tot_api.h`,
  `tot/tot_api.f90`, `tot/tot_state.f90`; 6 entry-point stubs
  returning `TOT_ERR_NOT_IMPL` (ierr=4), plus first C-side smoke
  tests under `tot/tests/c_abi/`.
- **L-3 (2026-04-18, PR #82)** — Namespaced parameter dispatcher
  (`tot/tot_param_registry.f90`) routing `<ns>:<bare>` names to the
  six per-module registries (`eq_param_set`, `tr_param_set`,
  `fp_param_set`, `ti_param_set`, `wrx_param_set`). `wr:` is aliased
  to `wrx:` because TOT links `wrx/libwr.a` (the `wr_param_set`
  symbol resolvable inside `libtotapi.so` is wrx's). String setter
  (`tot_set_param_str`) supports the `tr:` and `eq:` namespaces.
- **L-4 (2026-04-18, PR #85)** — `make -C tot libtotapi.so` builds
  the **composite** shared library: links the six per-module PIC
  archives plus the shared dependency PIC libraries (`lib`, `pl`,
  `bpsd`, `mtxp`, `ob`, `adpost`, `open-adas/adf11`). Non-PIC
  archives and the `tot` binary are unchanged.
- **L-5 (2026-04-18, PR #91)** — Python wrapper `python/totlib/`:
  `Tot` context manager, `TotState` dataclass with `presence`
  sub-dict, exception hierarchy mirroring `enum tot_error`, `_ffi`
  ctypes layer with `TOTLIB_PATH` override and `RTLD_LAZY` loading,
  Python-side namespace guard (`Tot._validate_namespaced_name`)
  catching missing/empty/unknown prefixes before any FFI call.
- **L-7 (2026-04-19, this PR)** — User-facing documentation:
  rewritten `python/totlib/README.md` with full 6-fn API table,
  namespace-prefix rules (with `wr:`→`wrx:` alias), `TotState` field
  table, exception hierarchy, CLI→library migration notes, and known
  limitations; example scripts (`quickstart.py`,
  `parameter_sweep.py`, `state_dump.py` — all with `--dry-run` and
  graceful `TotlibNotImplementedError` handling for the L-3/L-4 stub
  state); architecture doc (`docs/tot-library/architecture.md`) with
  ASCII diagram showing TOT orchestrating the 6 backing modules and
  Phase L completion matrix; this changelog entry.

### Known issues

- **L-6 (4-layer test integration) is not yet merged.** Wrapper-only
  tests run via `python3 -m unittest discover python/totlib/tests`;
  the `totlib_*` cases in `test_run/test_definitions.conf` will land
  with the L-6 PR.
- **`tot.run()` / `tot.get_state()` are stubs.** `tot_init`,
  `tot_run`, `tot_get_state`, `tot_finalize` currently return
  `TOT_ERR_NOT_IMPL` (rc=4); the wrapper accepts both `OK` and
  `NOT_IMPL` from `tot_init` / `tot_finalize` so `set_param` testing
  works today, but `run` / `get_state` raise
  `TotlibNotImplementedError` until L-6 wires the per-module fan-out.
- **`wr:` is aliased to `wrx:`.** TOT links `wrx/libwr.a`, so the
  `wr/wr_param_registry` is not reachable through `libtotapi.so`.
  Use `python/wrlib` (against `wr/libwrapi.so`) to drive the real
  `wr` registry.
- **String parameters wired only for `tr:` and `eq:`.** Other
  namespaces (`fp:`, `ti:`, `wr:`/`wrx:`) reject `tot_set_param_str`
  with `rc=1` until their per-module registries grow a symmetric
  `*_param_set_str` entry point.
- **Single instance per process** — TOT pulls in COMMON blocks from
  six backing modules; two concurrent `Tot()` handles share state.
- **Optimization driver deferred.** The original L-7 plan
  (`docs/superpowers/plans/2026-04-18-tot-library-L7-optimization.md`)
  scoped a parameter-optimization workflow (`optimize.py`,
  `objectives.py`, `results.py`, scipy/optuna/grid backends, three
  notebooks). This PR delivers the documentation subset only;
  the optimization driver is deferred to a follow-up PR.
