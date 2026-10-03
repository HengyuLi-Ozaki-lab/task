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

## The product line's own commits (groups B–G: 74 before the sync, classified 2026-10-02; groups R and P came after it)

| Group | Commits | Upstream | Next |
|---|---|---|---|
| B. The Kyoto `bpsi/develop` base (23) | `7999438d`…`3066a479`, `a196e8b6`, `236893f4`, `fa9dd493` | in PR #226 (open since 2026-07-12) | the author follows up |
| M. The reconcile merge and what made it build and pass (12) | `0254aa91`, `35c4bb5f`, `4bceac38`, `36586def`, `4df6e541`, `d4afbaca`, `17f21f2c`, `9242c127`, `bacf3f19`, `0861b69c`, `bf0a251b`, `d1f7f9e7` | in PR #226 | same |
| D. Design documents, report, slides (9) | `58f1fe2e`, `11504a9d`, `7b201f86`, `e3a93de0`, `c27ad9ce`, `e7789b92`, `0509f181`, `c5c51d37`, `c6cee542` | in PR #226 | same |
| E. EQ save and psi(R,Z) tools, MCP stdout isolation, `trbpsd` bounds, `.gitignore` (13) | `3dc1b8b4`, `315a4505`, `788aaa03`, `70a904b4`, `dbef311c`, `91896640`, `2f36dd97`, `1b1936f7`, `98a67663`, `69b55427`, `8ef527dd`, `c4e0defe`, `8a72b309` | in PR #226 (`8a72b309` was PR #210, closed by the author 2026-06-23). The first eleven and `8a72b309` apply cleanly to `upstream/develop` on their own | the author may split them out if #226 stays open |
| F. FP: `set_param_str` tool, stdout guard, global scalars (3) | `1ef64b6f`, `4b303fc4`, `6efd7bf5` | PRs #231, #232, #233 (open since 2026-08-06, CI green, not reviewed) | the author follows up; #232 needs the `main()`-time change of group P |
| G1. TR registry: PECTOT/PICTOT, CDH/CNH (3) | `823800a4`, `11082f39`, `db416e6c` | not proposed; applies cleanly | a new branch `pr/tr-registry-heating-and-diffusivity` (not made yet), then its upstream PR |
| G2. EQ `validate()`: grid containment, RB<RA (2) | `796b4ef3`, `a4969f4e` | not proposed; applies cleanly | a new branch `pr/eq-validate-grid-containment` (not made yet), then its upstream PR |
| G3. Windows: `.dll` names and DLL directories in the wrappers (3) | `6a96e567`, `d5dd446e`, `d4b3cc29` | not proposed; applies cleanly | a new branch `pr/ffi-windows-dll-names` (not made yet), then its upstream PR |
| G4. MCP servers: stdout isolated once per process; Windows stdout and stdin (3) | `d8afd5c7`, `db11820c`, `279503a7` | **product-only**: built on #226 and on #232/#233; after the merge of #226 they live inside `_install_fd_isolation()` (group P) | propose once #226 and #232 are merged upstream |
| G5. EQ: QQPS on the psi-surface grid for loaded equilibria (3) | `97025c6e`, `ccfe533a`, `5db35994` | **product-only**: `5db35994` conflicts in `eq/eqcalc.f90` without group B | after #226 |
| R. The answers to upstream's review of #226 (14; not among the 74) | `98ba1e20`…`682d9afe` | in PR #226; merged here by `fix/pr226-followups` (merge `95eec84c`, with #226's own merge of upstream, `fb809910`) | same |
| P. After the merge of #226: three product-only commits | `b72ca2bb` (`fp_mcp` installs its fd isolation from `main()`), `11669549` (`tot_mcp` does too; the isolation tests call the installers), `667f8742` (`eq_save`'s contract in `eq/eq_api.h` and the MCP `save` tool description) | **product-only**: none is upstream. `eq_mcp` and `tr_mcp` take #226's `main()`-time isolation with group G4's once-per-process flag and Windows stdin move (hand-resolved in `95eec84c`) | `b72ca2bb` with #232; `667f8742` after #226; `11669549`: see below |

Of the 74, sixty are proposed upstream (57 in #226, 3 in #231–#233), 8 can be proposed now (G1–G3) and 6 wait
(G4, G5). Product-only by nature, added by P3: the CI trigger for `kyoshimi-develop`, `.githooks/`,
`scripts/install-hooks.sh`, `python/repo_tests/`, `AGENTS.md`, `CONTRIBUTING.md`, this folder, `.github/rulesets/`.
Cherry-picked from PR #226's branch before it was merged whole: `c528b58d` (mcp below 2; here `f136d6c9`) and
`a12af230` (the mono job generates its eqdata; here `adc00a74`).

## To report on #226 (the author decides)

With the fd isolation installed from `main()` (`0bf7e399`, #226's answer to #227 item 1), `python -m tot_mcp.server`
puts Fortran output on the JSON-RPC pipe: `tot_mcp` had its isolation as a side effect of importing `tr_mcp` and
`fp_mcp`, and an import no longer installs it. Measured at #226's own head (`682d9afe`), in a stdio session: 9
non-JSON lines of 12 on stdout. The product line fixed it in `11669549`; #226 still has the regression.

## Open items in the product line

The fork has issues disabled, so they are listed here. All are older than P3 or are wording left over from it; none
is a regression of the merges.

- `ti_mcp`, `wr_mcp` and `wrx_mcp` install no fd isolation. Measured in a stdio session, non-JSON lines on stdout of
  all lines: `ti_mcp` 4 of 7, `wr_mcp` 5 of 8, `wrx_mcp` 0 of 3; the same before and after #226's fixes.
- `EQSAVE` has an error out-argument since #226 (`SUBROUTINE EQSAVE(IERR_OUT)`), but three texts still say it has
  none: the docstring at `python/eqlib/eqlib.py:332-334`, and the comments in `eq/eq_api.f90` ("EQSAVE itself does
  not propagate errors", line 656; "a bare external subroutine with no IERR out-argument", line 669).
- `tr/f77/trfile.f:106` still has `CALL EQSAVE(4)`: a legacy file that no Makefile builds (`tr/Makefile` builds
  `trfile.f90`). It would not work against the new interface: the call passes the literal `4` where `EQSAVE` now
  assigns its `IERR_OUT`.
- The MCP SDK bound `mcp>=0.9,<2` is written out in 35 files (56 places, counted at `d4b99c6d`: the CI install line,
  the servers' `pyproject.toml` files and install messages, READMEs, docs). The `<2` cap reached all of them in #226;
  a later change of the bound is a 35-file edit.
