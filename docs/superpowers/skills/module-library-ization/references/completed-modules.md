# Completed modules — PR matrix

Reference table of every Phase L / Phase F / MCP PR merged on
`develop` between 2026-04-17 and 2026-04-18 for the six modules
already library-ized: **tr, ti, fp, wr, wrx, eq**.

Use this as a living index — when a new module starts Phase L, add a
row here and link the PRs as they merge. Status `inflight` means a
draft branch exists but no PR is merged yet.

## Phase L matrix

| Module | L-0 baseline | L-1 Makefile | L-2 C ABI stubs | L-3 registry | L-4 .so | L-5 wrapper | L-6 tests | L-7 docs |
|--------|--------------|--------------|-----------------|--------------|---------|-------------|-----------|----------|
| tr     | (pre-PR)     | #21          | #27             | #33          | #35     | #44         | #53, #63  | #62      |
| ti     | #12          | #22          | #28             | #34          | #41 / #66 | #47       | #57       | #64      |
| fp     | #13          | #26          | #29             | #37          | #43     | #55         | #56       | #68      |
| wr     | #15          | #24          | #30             | #36          | #42     | #46         | #60       | #69      |
| wrx    | #16          | #25          | #31             | #38          | #52     | #59         | #67       | inflight |
| eq     | #54          | #65          | #70             | #78          | inflight| inflight    | inflight  | inflight |

Notes:
- `tr` L-0 was the very first regression dump; design lives in
  `docs/superpowers/specs/2026-04-17-tr-library-design.md`.
- `ti` L-4 needed a retroactive fix (#66) after the initial #41 missed
  building the `.so` artefact in CI.
- `tr` L-6 has a follow-up #63 that extended the registry to cover
  `UNREGISTERED_KEYS` of the test fixtures.
- `wrx` L-7 is paused pending the `libgrf::grd1d` link-time issue
  (see `pitfalls.md`).
- `eq` L-4..L-7 are in flight on parallel feature branches; expected
  to merge after the F-2..F-3 modernization wave.

## Phase F matrix (eq only — first module to need F)

| Phase | Goal | PR |
|-------|------|----|
| F-0 (planning) | F77 -> F90 plan + shim policy | #50, #61 |
| F-1 | COMMON -> MODULE migration with shim | #71 |
| F-2 | LOW tier .f -> .f90 conversion | #79 |
| F-3 | MED tier conversion | inflight (`feature/eq-f90-phase-F3-med-tier`) |
| F-4 | HIGH tier conversion (drivers, file I/O) | not yet |
| F-5 | shim removal + grep-clean | not yet |

When subsequent modules (tr, fp, ti, ...) need F-track work, copy the
`eq` plan structure under `docs/superpowers/plans/<DATE>-<module>-f90-*`.

## MCP server matrix

| Module | MCP-1 (server.py + 9 tools) | MCP-2 (plot extension) |
|--------|-----------------------------|------------------------|
| tr     | #72 (reference impl)        | not yet                |
| ti     | #74                         | not yet                |
| fp     | #77                         | not yet                |
| wr     | #76                         | not yet                |
| wrx    | #75                         | not yet                |
| eq     | not yet                     | not yet                |

The `tr_mcp` PR (#72) doubles as the **reference implementation**.
When adding a new module, copy `python/mcp-servers/tr_mcp/` and
search-replace `tr` -> `<module>`, `Tr` -> `<Module>`, `TR` -> `<MOD>`.

## Plan-only PRs (per-module L-0..L-7 plan files)

Useful when picking up an in-flight module — the plan files describe
the per-task checklist already drafted:

| Module | Plan PR | Plan file location |
|--------|---------|--------------------|
| tr     | #9      | `docs/superpowers/plans/2026-04-18-tr-library-L*.md` |
| ti     | #6      | `docs/superpowers/plans/2026-04-18-ti-library-L*.md` |
| fp     | #5      | `docs/superpowers/plans/2026-04-18-fp-library-L*.md` |
| wr     | #7      | `docs/superpowers/plans/2026-04-18-wr-library-L*.md` |
| wrx    | #10     | `docs/superpowers/plans/2026-04-18-wrx-library-L*.md` |
| tot    | #8      | `docs/superpowers/plans/2026-04-18-tot-library-L*.md` |
| eq     | #58     | `docs/superpowers/plans/2026-04-18-eq-library-L*.md` |

## Cross-cutting docs PRs

| Topic | PR |
|-------|----|
| TR library design spec (the prototype) | #3 |
| TASK library-ization user manual (LaTeX/PDF) | #73 |
| EQ Makefile graphics-split plan | #48 |
| MCP common design plan (in #72)        | #72 |

## Adding a new module

1. Copy this file's row template:
   ```
   | <MODULE> | tbd | tbd | tbd | tbd | tbd | tbd | tbd | tbd |
   ```
2. Create the L-0..L-7 plan files under `docs/superpowers/plans/`
   following the eq pattern (PR #58).
3. As each phase merges, replace `tbd` with the PR number.
4. If F-track work is needed, add a row to the Phase F matrix.
5. After L-7, copy `tr_mcp` to `<module>_mcp` and add to the MCP row.
