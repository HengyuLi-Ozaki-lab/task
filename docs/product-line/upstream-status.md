# The product line and upstream — status

`kyoshimi-develop` against `k-yoshimi/task` `develop`. A pull request that changes a row updates this file.
Today's numbers: `git fetch origin && git fetch upstream && git rev-list --left-right --count origin/kyoshimi-develop...upstream/develop`.

Last sync: 2026-10-02 (pull request #2), `upstream/develop` `4a5d977d` (2026-06-08) merged; 0 behind. Right after it
the head of the product's own upstream pull request #226 (`682d9afe`) was merged (pull request #3, `fix/pr226-followups`,
2026-10-02), with three product-only commits after the merge, so the product line holds all of #226. At that merge
(`d4b99c6d`) the product line was 100 ahead of and 0 behind `upstream/develop`: the 74 commits of groups B–G below,
and 26 added while aligning it (the CI trigger `f29f94a2` and two cherry-picks, #226's 15 commits that the product
line lacked and the merge that brought them, the sync merge `cb4ea7fe`, the three commits of group P, the three
pull-request merges).

Since then: pull request #4 (`chore/product-line-rules`, `5e1c4048`: the hook, the rules and this folder), the
library fixes of group H below (pull request #5, `fix/eq-validate-and-tr-registry-tests`, merge `8945abe0`) and the FP
fix of group I (pull request #6, `fix/fp-run-refuses-bad-counts`, merge `2203c95f`). Group J (`fix/param-interface-checks`)
came with pull request #8 (merge `47e17d55`, 2026-10-04), which added its row.

## The product line's own commits (groups B–G: 74 before the sync, classified 2026-10-02; groups R, P, H, I and J are not among the 74)

| Group | Commits | Upstream | Next |
|---|---|---|---|
| B. The Kyoto `bpsi/develop` base (23) | `7999438d`…`3066a479`, `a196e8b6`, `236893f4`, `fa9dd493` | in PR #226 (open since 2026-07-12) | the author follows up |
| M. The reconcile merge and what made it build and pass (12) | `0254aa91`, `35c4bb5f`, `4bceac38`, `36586def`, `4df6e541`, `d4afbaca`, `17f21f2c`, `9242c127`, `bacf3f19`, `0861b69c`, `bf0a251b`, `d1f7f9e7` | in PR #226 | same |
| D. Design documents, report, slides (9) | `58f1fe2e`, `11504a9d`, `7b201f86`, `e3a93de0`, `c27ad9ce`, `e7789b92`, `0509f181`, `c5c51d37`, `c6cee542` | in PR #226 | same |
| E. EQ save and psi(R,Z) tools, MCP stdout isolation, `trbpsd` bounds, `.gitignore` (13) | `3dc1b8b4`, `315a4505`, `788aaa03`, `70a904b4`, `dbef311c`, `91896640`, `2f36dd97`, `1b1936f7`, `98a67663`, `69b55427`, `8ef527dd`, `c4e0defe`, `8a72b309` | in PR #226 (`8a72b309` was PR #210, closed by the author 2026-06-23). The first eleven and `8a72b309` apply cleanly to `upstream/develop` on their own | the author may split them out if #226 stays open |
| F. FP: `set_param_str` tool, stdout guard, global scalars (3) | `1ef64b6f`, `4b303fc4`, `6efd7bf5` | PRs #231, #232, #233 (open since 2026-08-06, CI green, not reviewed) | the author follows up; #232 needs the `main()`-time change of group P |
| G1. TR registry: PECTOT/PICTOT, CDH/CNH (3) | `823800a4`, `11082f39`, `db416e6c` | not proposed as they are: their registry tests loop inside `subTest`, which `pytest --forked` (CI) reports as passed, and nothing tests the Fortran side | to be re-cut with `1b3a0cd0` (group H) as `pr/tr-registry-heating-and-diffusivity`, then its upstream PR |
| G2. EQ `validate()`: grid containment, RB<RA (2) | `796b4ef3`, `a4969f4e` | not proposed as they are: the box check fires for `MDLEQF < 10`, where the solver does not read the box (it refuses inputs that run) | to be re-cut with `4a30b262` (group H) as `pr/eq-validate-grid-containment`, then its upstream PR |
| G3. Windows: `.dll` names and DLL directories in the wrappers (3) | `6a96e567`, `d5dd446e`, `d4b3cc29` | upstream pull request #240 (open since 2026-10-03, CI green; head `63b1f425` on `pr/ffi-windows-dll-names`): the same three commits re-cut onto `upstream/develop` (`d9680623`, `2f41104b`, `63b1f425`) | wait for #240; the sync after it merges brings them back |
| G4. MCP servers: stdout isolated once per process; Windows stdout and stdin (3) | `d8afd5c7`, `db11820c`, `279503a7` | **product-only**: built on #226 and on #232/#233; after the merge of #226 they live inside `_install_fd_isolation()` (group P) | propose once #226 and #232 are merged upstream |
| G5. EQ: QQPS on the psi-surface grid for loaded equilibria (3) | `97025c6e`, `ccfe533a`, `5db35994` | **product-only**: `5db35994` conflicts in `eq/eqcalc.f90` without group B | after #226 |
| R. The answers to upstream's review of #226 (14; not among the 74) | `98ba1e20`…`682d9afe` | in PR #226; merged here by `fix/pr226-followups` (merge `95eec84c`, with #226's own merge of upstream, `fb809910`) | same |
| P. After the merge of #226: three product-only commits | `b72ca2bb` (`fp_mcp` installs its fd isolation from `main()`), `11669549` (`tot_mcp` does too; the isolation tests call the installers), `667f8742` (`eq_save`'s contract in `eq/eq_api.h` and the MCP `save` tool description) | **product-only**: none is upstream. `eq_mcp` and `tr_mcp` take #226's `main()`-time isolation with group G4's once-per-process flag and Windows stdin move (hand-resolved in `95eec84c`) | `b72ca2bb` with #232; `667f8742` after #226; `11669549`: see "To mention on #226" below |
| H. Library fixes found while preparing G1 and G2 (3) | `4a30b262` (EQ `validate()` checks the box only when the solver reads it: `MODELG = 2` and `MDLEQF >= 10`), `1b3a0cd0` (TR registry tests that can fail under `--forked`; README; neutral comments), and `7944bc04` (this file rewritten) | `4a30b262` and `1b3a0cd0` go upstream inside the re-cut branches of G2 and G1: each edits tests that its group adds, so it does not apply to `upstream/develop` alone. `7944bc04` is **product-only** | cut `pr/eq-validate-grid-containment` (G2, then `4a30b262`) and `pr/tr-registry-heating-and-diffusivity` (G1, then `1b3a0cd0`) from `upstream/develop` (pull request #5, which brought this row, is merged: `8945abe0`) |
| I. FP: `fp_run` refuses the counts it cannot run with (1) | `3eb8f8c4` (`fp_param_check` in `fp/fp_param_registry.f90`, called by `fp_api_run` before `fp_prep`: `NRMAX` outside 1 to `FP_MAX_NRMAX` (100, the surfaces of the state layout), `NPMAX` or `NTHMAX` below 2, `LMAXFP` below 0 or at the largest integer, `NSAMAX` above `NSBMAX`, an entry in use of `NS_NSA` outside 1 to `MIN(NSMAX, NSBMAX)` or of `NS_NSB` outside 1 to `NSMAX`, a 0 there standing for the slot's own number; the run returns `FP_ERR_INVALID` and unit 6 gets one `XX fp_run:` line per violation) | upstream pull request #242 (open since 2026-10-05, CI green; head `3eb8f8c4` on `fix/fp-run-refuses-bad-counts`): the branch is `upstream/develop` (`4a5d977d`) and this one commit, the same commit that pull request #6 merged here (merge `2203c95f`, 2026-10-03, no hand resolution). **A change of behaviour** (its CHANGELOG entry is under Changed): a run with `NRMAX` above 100 used to be made, with a state `fp_get_state` could not return (rc=3), and is now refused before any work. The other violations ran past an array bound (an abort when built with run-time checks; without them, as in the default `-O3` build, undefined), ended the process or never ended a step. Before #242 Linux CI had run on the merge with the product line only; #242's run (37270222367) is the first of the branch alone: both pytest jobs `765 passed, 23 skipped, 4 xfailed, 1 xpassed`, with the 19 equivalence tests run (15 passed; 4 xfailed, #190, #222, #223 and #224), and the mono build and its tests green. On macOS the branch alone, the seven libraries and `libtotapi_mono.so` built with the `make.header` that task-web's build writes (`-O0`, bounds and run-time checks) and pytest with CI's flags: 757 passed, 35 skipped, 1 xpassed (the skips: the 19 equivalence tests, which run on Linux only, 13 that need `MONO_LIB_PATH` or `TOTLIB_PATH`, which were not set, and 3 without the `ti_mcp` data fixture); `upstream/develop` alone, the same build: 723 passed, 35 skipped, 1 xpassed (the 34 more are the new tests). Measured on 2026-10-05 at the heads `682d9afe` (#226), `62600919` (#231), `bb52868b` (#232), `92a0163d` (#233) and `63b1f425` (#240): it merges with each without a conflict and shares one file, `fp/fp_api.f90`, with #233. The commits that add and change this row are **product-only** | wait for #242; the commit is already here (merge `2203c95f`), so the sync after it merges only turns this row to upstream |
| J. EQ, TR, FP: what `set_param`, `run` and `set_params` refuse (1) | `484cc7eb` (the three registries refuse a malformed subscript for a scalar too, a name longer than their buffer, a string value longer than its parameter, a value that is not finite, and for an integer parameter a value outside `-HUGE(0)` to `HUGE(0)`; the C entry points refuse a name or a string value longer than their buffer; `Fplib.run` and `Trlib.run` refuse a step count that is negative or does not fit a C `int`, `Eq.run` a mode that does not fit one; `eq_mcp`, `tr_mcp` and `fp_mcp` refuse a number that is not finite and an integer too large for a float) | **product-only** as cut: the branch starts from `kyoshimi-develop`. Tried on `upstream/develop` (`4a5d977d`), 8 of the 31 files it modifies conflict (`CHANGELOG.md`, `eq/eq_api.f90`, `fp/fp_param_registry.f90`, `python/fplib/fplib.py`, `python/eqlib/eqlib.py` and the three servers), where commits that are not upstream yet changed the same places (#226, #232, group I and group G5's `5db35994`); the other 23 and the 13 new test files apply as they are. Measured on 2026-10-05 by applying the commit to `upstream/develop` with the open heads merged in one after another (#242, #231 at `62600919`, #232 at `bb52868b`, #233 at `92a0163d`, #226 at `682d9afe`, #240 at `63b1f425`): 5 files still conflict once group I (#242) is in (`eq/eq_api.f90`, `python/eqlib/eqlib.py` and the three servers), 4 once #232 is (`fp_mcp`'s server no longer), 1 once #226 is (`python/eqlib/eqlib.py`: the docstring of `Eq.run`, beside a paragraph that group G5's `5db35994` added); the heads of #231, #233 and #240 remove no conflict. #231 is needed all the same: without it one of the commit's tests fails (`test_a_string_on_its_own_still_goes_to_set_param_str` in `python/mcp-servers/fp_mcp/tests/test_bulk_values.py`: `fp_mcp`'s `set_params` sends a string to `set_param_str` only with #231), and with it the 84 tests of `fp_mcp`'s and `tr_mcp`'s `test_bulk_values.py` pass (pure Python: a recorder stands in for the library, so nothing was built; `eq_mcp`'s `test_bulk_values.py`, whose `eqlib.py` holds the conflict, and the commit's ten test files that load a library were not run on that tree). Nothing was found that needs #233 or #240: no conflict, and the commit names none of #233's state scalars. **Changes of behaviour**: `NAME[zz]`, `NAME[1]x` and `NAME[1,2]` used to set a parameter; a name longer than its buffer used to be cut and taken, and a string value longer than the 80 characters of its parameter was cut to them (TR and FP took up to 128); a count beyond a C `int` used to run modulo 2**32. All are refused now. Not changed, and upstream's to decide: a whole-number subscript still sets a scalar (upstream's `python/trlib/tests/test_property_fanout.py` relies on it), so a list given for a scalar still leaves its last element; FP rounds a fraction and TR and EQ truncate it. Not touched: `ti`, `wr` and `wrx` (registries, C entry points, wrappers and servers with the same faults; `ti`'s parser is its own, `parse_subscript`); `tot`'s own C entry point and dispatch, which cut a name at 128 characters, its prefix at 16 (`eq`, blanks and anything before the colon is `eq`) and a string value at 256, its wrapper (two comments on the value buffer aside) and its server (`tot` strips its prefix and calls these registries, so its `eq:`, `tr:` and `fp:` names get the registries' checks, `python/totlib/tests/test_module_checks.py`, and its `ti:`, `wr:` and `wrx:` names do not); and the registry and API templates under `docs/superpowers/skills/` | re-cut onto `upstream/develop` once #226, #231, #232 and group I's #242 are upstream, resolving by hand the one conflict then left (`Eq.run`'s docstring, against group G5's `5db35994`, which waits for #226 itself), and with the same checks for the other modules (`ti`, `wr`, `wrx`, `tot`); the preconditions come from the conflicts and that one test, and the re-cut's own build and pytest decide; the two open questions go to upstream with it. The author opens that pull request, or gives the go-ahead |
| K. TR: the multi-reaction fusion model of `trx`, selected by `MODEL_PNF` and off by default (34) | `bae37014`…`595763a5`: the 33 commits of the fork branch `p1/trx-tr-port-rebased` (`2094fbcd`, written on #226's head in July and August 2026) that were not here already, cherry-picked with `-x` onto `a5634697` without a conflict; that branch's other two were here as `823800a4` (PECTOT and PICTOT, group G1) and `796b4ef3` (EQ `validate()`, group G2). Then `691ce8ea`: the registry takes `MODEL_PNF` only (it took `model_pnf` too) and lists it in `value_refused`, which group J added after the port was written. They are Tasks 1 to 7 of `docs/superpowers/plans/2026-06-15-trx-tr-consolidation.md`: `tr/libnf.f90`, `tr/trpnf_multi.f90`, `tr/trcoll.f90`, `tr/trlib.f90`, `tr/trcomm_nf.f90`, two test files (49 tests) and the reference decks and baselines under `test_run/` | **product-only** as cut: the branch starts from `kyoshimi-develop`. Tried on `upstream/develop` (`4a5d977d`), 2 of the 33 apply and the third edits the plan, which #226 adds (group D); `691ce8ea` needs group J's `value_refused`. Measured on 2026-10-07 on macOS (gfortran 15, the `make.header` that task-web's build writes): the seven libraries, `tot_api_check_all`, and `libtotapi_mono.so` with its inspection build; pytest with CI's flags 1613 passed, 35 skipped, 1 xpassed, against 1564, 35 and 1 for `a5634697` built the same way: the 49 more are the new tests and no test of `a5634697` is missing; the 14 tests of the three `test_mono_*` files pass with `MONO_LIB_PATH` and `TOTLIB_PATH` set. The 19 equivalence tests are among the skips (Linux only): the CI log decides for them. **A change of behaviour** (CHANGELOG, Changed): `FTAUE` and `FTAUI` return `1.D8` for an ion density at or below `1.D-8`, where they returned an infinity. The fusion path is held to `trx`, not to a measurement (the header of `python/trlib/tests/test_model_pnf_dispatch.py` says what that comparison cannot see); the reference is `trx` with five corrections, reported upstream as issues #235, #236 and #238 (#234 is a fourth report, of `sigma_nf`) | re-cut the library commits from `upstream/develop` once #226 is merged there. Before the plan goes on, the author takes its open questions to the upstream authors: Task 8 (species-resolved NBI and RF arrays), Task 10 (archiving `trx` and `trm`), and the difference between `tr` and `trx` with fusion off (below) |

Of the 74, sixty-three are proposed upstream (57 in #226, 3 in #231–#233, 3 in #240), 5 wait for the re-cut that group
H feeds (G1, G2) and 6 wait on other pull requests (G4, G5). The groups outside the 74, each with its row
above: R (in #226), P (three commits), H (two library commits and `7944bc04`), I (one commit, in #242), J (one
commit, product-only as cut) and K (34 commits, product-only as cut).
Product-only by nature, added for the product line: the CI trigger for
`kyoshimi-develop`, `.githooks/`, `scripts/install-hooks.sh`, `python/repo_tests/`, `AGENTS.md`, `CONTRIBUTING.md`,
this folder, `.github/rulesets/`.
Cherry-picked from PR #226's branch before it was merged whole: `c528b58d` (mcp below 2; here `f136d6c9`) and
`a12af230` (the mono job generates its eqdata; here `adc00a74`).

## To mention on #226 (the author decides)

`python -m tot_mcp.server` puts Fortran output on the JSON-RPC pipe at #226's head (`682d9afe`). Against
`upstream/develop` this is **not a regression**: `develop` installs no stdout isolation in any server. Measured on
2026-10-03, one stdio session per tree (`initialize`, `init`, `run`; non-JSON lines of all lines on stdout):

| Tree | `tot_mcp` stdout |
|---|---|
| `upstream/develop` `4a5d977d` | 9 of 12 |
| #226 at `fb809910` (its merge of upstream) | 0 of 3 |
| #226 at `682d9afe` (its head) | 9 of 12 |
| product line before #226's fixes, `2b1996fc` | 0 of 3 |
| product line after the merge of #226, `b72ca2bb` | 9 of 12 |
| product line with `11669549` | 0 of 3 |

At `fb809910` `tot_mcp` had the isolation only as a side effect: it loads `tr_mcp`'s registry, and `tr_mcp` redirected
fd 1 when it was imported. `0bf7e399` (#226's answer to #227 item 1) moved the isolation into `main()`, which `tot_mcp`
does not call, so #226's head lost it for `tot_mcp`. For the product line that was a regression (`2b1996fc` to
`b72ca2bb`), fixed by `11669549`. Worth mentioning on #226 as an observation, not as a regression of `develop`; the
author decides.

## Open items in the product line

The fork has issues disabled, so they are listed here. All are older than the alignment of the product line with upstream or are wording left over from it; none
is a regression of the merges.

- `ti_mcp`, `wr_mcp` and `wrx_mcp` install no fd isolation. Measured in a stdio session, non-JSON lines on stdout of
  all lines: `ti_mcp` 4 of 7, `wr_mcp` 5 of 8, `wrx_mcp` 0 of 3; the same before and after #226's fixes.
- `EQSAVE` has an error out-argument since #226 (`SUBROUTINE EQSAVE(IERR_OUT)`), but three texts still say it has
  none: the docstring at `python/eqlib/eqlib.py:348-350`, and the comments in `eq/eq_api.f90` ("EQSAVE itself does
  not propagate errors", line 679; "a bare external subroutine with no IERR out-argument", line 692).
- `tr/f77/trfile.f:106` still has `CALL EQSAVE(4)`: a legacy file that no Makefile builds (`tr/Makefile` builds
  `trfile.f90`). It would not work against the new interface: the call passes the literal `4` where `EQSAVE` now
  assigns its `IERR_OUT`.
- **`subTest` under `--forked`.** `pytest --forked` (CI) reports a failing `unittest` `subTest` as passed: the same
  failing test gives `1 failed, 2 passed, 3 subtests passed` in plain pytest and `2 passed` with the CI flags
  (pytest 9.0.3, pytest-forked 1.6.0, pytest-subtests 0.15.0). `git grep -h '\.subTest(' <rev> -- '*.py' | wc -l`
  finds 47 calls (`git grep -l`: 24 files) at `d4b99c6d` and at `5e1c4048`, and 45 calls in 24 files on
  `upstream/develop` (`4a5d977d`); at `5e1c4048` the word `subTest` occurs 57 times in 25 files, the 25th
  (`python/wrlib/tests/test_property_boundary.py`) only in comments. The two TR registry tests that showed it are
  replaced in pull request #5 (`1b3a0cd0`), which leaves 45 calls in 24 files. Each of the rest can hide a failure
  from CI. Reported upstream as k-yoshimi/task#241 (open, 2026-10-03). Open: one test per case,
  `pytest.mark.parametrize`, or CI without `--forked` — a larger change than one test file.
- **Fixed by pull request #5 (`4a30b262`):** `validate()` refused default-`MDLEQF` (and `MDLEQF` 1, 2, 3) runs of
  devices larger than the default box [1.5, 4.5] x [-2, 2], which run (ITER-sized `RR=6.2`, `RA=2.0`: two diagnostics
  and a successful `run(0)`). The box check now needs `MODELG = 2` and `MDLEQF >= 10`.
- **EQ `validate()`, open (medium).** After a run, `validate()` reads the box that `EQCALQP` overwrote with the traced
  plasma extent, for any `MDLEQF` (`eq/eqcalq.f90:603-613`): with `MDLEQF = 10` and the box `[4.0, 8.5] x [-4, 4]` it
  returns `[]` before `run(0)` and, after a successful run, both extent diagnostics (the box has become
  `[4.201, ...]`). It is a pre-run check; it should keep the input values or say so.
- **EQ `validate()`, open (medium).** NaN and non-positive `RA`, `RB`, `RKAP` pass: `validate()` returns `[]` for
  `RA = NaN`, `RA = 0`, `RA = -1`, `RKAP = NaN`, `RKAP = 0`, `RKAP = -1.5` and `RR = NaN` (`MODELG = 2`, `MDLEQF = 10`);
  `RB = -1` is flagged only because it is below `RA`.
- **EQ `validate()`, open (low).** With `MDLEQF >= 10` the check is stricter than the solver on two sides. EQAXIS asks
  of the box only that the axis lie inside it and uses `RGMAX` for the outer edge, so `ZGMAX` below `RKAP*RA` (2.0
  against 3.4) or `RGMIN` above `RR - RA` (5.0 against 4.2) changed no scalar of the run, while `RGMAX` below `RR + RA`
  cut the plasma at `RGMAX` (`psipa` 9.5 against 20.3, `qsurf` 2.6 against 7.8) and the check stays right there.
  `validate()` still reports the first two (measured 2026-10-03, ITER-sized case).
- **EQ `validate()`, open (medium).** A file load (`MODELG` 3, 5, 8, 9, 15, 25) with `MDLEQF >= 10` also reads the
  box (`EQCALQ`, through `EQSETP` and `EQAXIS`), but `validate()` checks nothing for it: the loaded extent is not known
  before the load. Measured 2026-10-03 on the ITER01 fixture with `MDLEQF = 10` and the default box: `validate()`
  returns `[]` and `run(1)` fails with `equnit::eq_load failed (ierr=103)`; at the default `MDLEQF` the load runs.
- **EQ `validate()`, open (medium).** `MODELG = 0` and `1` share `EQCALC`'s analytic path and the box rule, but the
  check is gated on `MODELG == 2`. Measured 2026-10-03, ITER-sized case (`RR=6.2`, `RA=2.0`, `RKAP=1.7`, `RB=2.1`):
  at the default `MDLEQF` both run with scalars identical to `MODELG = 2`; with `MDLEQF = 10` and the default box
  `validate()` returns `[]` for both and `run(0)` fails with `EQCALC failed (ierr=103)` (`MODELG = 2` gets the two
  extent diagnostics); with the box set around the plasma both run. The same false negative as for the file loads
  above. Extending the gate to `MODELG` 0 and 1 is the obvious fix; left for a follow-up.
- **`docs/sphinx/modules/eq/{en,ja}/appendix-sensitivity.md`** say the interval `[RGMIN, RGMAX]` is divided into
  `nrgmax` points (`state.rg`), likewise for `Z`. For an analytic run it is not: `state.rg` and `state.zg` span
  `RR ± RB` and `±RKAP*RB` (`EQTORZ`) at every `MDLEQF` (six boxes measured, `MDLEQF = 10` among them, 2026-10-03).
- **`MDLEQF` 5 to 9** (the spline-profile models) abort the process in `run(0)`, with the default device too
  (`MDLEQF = 5`, `6`, `9` measured: Fortran runtime error at `lib/libspl1d.f90:253`, index 0 of `x`, exit code 2);
  `validate()` has no `MDLEQF` check. A side effect of `4a30b262`: a large device with `MDLEQF` 5 to 9 used to get the two
  extent diagnostics before it aborted, and now gets `[]`.
- **`MODEL_PNF` (group K) is in the Fortran registry and the `&TR` namelist only.** `tr_mcp` does not declare it, and
  `tr_get_state` has neither the reaction count nor the per-reaction rates (the plan's Task 9). With more than one
  reaction (`MODEL_PNF` 2, 3, 4, 12, 14) the rates are evaluated and nothing reaches the solve: TR has one fusion
  fast-ion slot (`NFM = 2`, a `PARAMETER`).
- **`tr` and `trx` differ with fusion off**, on the D-T deck of group K: the stored energy `WPT` by 1.9e-4 after two
  steps and 2.9e-4 after five (measured in August 2026 on `2094fbcd` against `trx` at `fa9dd493` with the reference's
  corrections; the initial state agrees, 510 of 514 values bit-identical and the worst at 5.7e-16). It is in the
  transport step and has not been bisected. It is why the fusion path is compared by its contribution (the run with `MODEL_PNF = 1` minus the run with
  0, in each code) and not at 1e-10.
- The MCP SDK bound `mcp>=0.9,<2` is written out in 35 files (56 places, counted at `d4b99c6d`: the CI install line,
  the servers' `pyproject.toml` files and install messages, READMEs, docs). The `<2` cap reached all of them in #226;
  a later change of the bound is a 35-file edit.
