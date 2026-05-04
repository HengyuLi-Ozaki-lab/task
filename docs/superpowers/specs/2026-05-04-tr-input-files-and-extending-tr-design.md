# TR Manual — Input files + Extending TR (User guide + Internals) — Design

**Status:** Draft
**Date:** 2026-05-04
**Project memory:** `project_tr_proper_manual.md` ("Input files" + "Extending tr (maintainer-facing)" — 1-session expansion target, item F in the deepening menu)
**Predecessors today (in chronological order):**
- G appendix (`limitations-and-references`, commit `a8b83311`)
- E appendix (`numerical-stability-and-diagnostics`, commit `fc74599d`)
- A first User-guide entry (`physics-overview`, commit `c5210076`)

---

## §1. Overview

Add **two** bilingual pages to the TR Sphinx chapter:

1. **`input-files.md`** — User guide entry, slotted after
   `parameter-setting`. User-facing reference for where data
   files live and which knobs control them: eqdata / EQDSK,
   ufiles + `MDLUF`, optional `trmodels/`-style support data,
   path-length and CWD constraints.
2. **`extending-tr.md`** — Internals entry, slotted after
   `design`. Maintainer-facing how-to: walk through adding a
   new scalar parameter, a new transport-model selector under
   `MDLKAI`, and a new `TrState` field (ABI-impact recipe).

These are split because the audiences are different: users
reading "Input files" mostly never edit Fortran; maintainers
reading "Extending TR" need to know which files to touch and
in what order.

This is the "F" item from the deepening menu in
`project_tr_proper_manual.md`, sized at 1 session total.

## §2. File structure

**New files (two bilingual pairs):**

- `docs/sphinx/modules/tr/en/input-files.md`
- `docs/sphinx/modules/tr/ja/input-files.md`
- `docs/sphinx/modules/tr/en/extending-tr.md`
- `docs/sphinx/modules/tr/ja/extending-tr.md`

**Edited files:**

- `docs/sphinx/modules/tr/en/index.md` — insert
  `input-files` in the User guide toctree (after
  `parameter-setting`); insert `extending-tr` in the Internals
  toctree (after `design`).
- `docs/sphinx/modules/tr/ja/index.md` — same.

No new MyST anchor labels are needed.

## §3. Page structure — `input-files.md`

### Header

- Title (en): "Input files"
- Title (ja): "入力ファイル"
- One-paragraph admonition stating this page is a *map* of
  the supporting data files TR can consume, plus pointers to
  where the canonical formats are documented (e.g. EQDSK is
  documented elsewhere; this page just notes that TR
  consumes it).

### §3.1 eqdata files (EQDSK and friends)

- `MODELG ∈ {3, 5, 7, 8}` triggers the `eq` module to load an
  external equilibrium file (the canonical "EQDSK"-shaped
  flow). The path is set via `KNAMEQ` (string parameter) —
  see {doc}`parameter-setting` for how to set string params.
- The file is read on the `eq` side; `tr` only pulls the
  resulting equilibrium / metric data via the BPSD broker.
  Cite `tr/trbpsd.f90:213-245` (the geometry-aware pull is
  conditional on `MODELG`).
- Canonical EQDSK format documentation lives in the `eq`
  chapter and external sources (`eqdsk` is a community
  format predating TASK); this page does NOT redocument it.
- A working example file ships under
  `test_run/test_output/tot_demo2014_short/eqdata.demo2014`
  (the demo2014 baseline used by Layer 1 equivalence tests).

### §3.2 ufiles (`MDLUF`)

- ufile = a community format for time-series experimental
  profile data (density, temperature, q-profile snapshots
  etc.). TR can ingest these to drive interpretive runs.
- Reading is controlled by `MDLUF` (default `0` — OFF; set
  to non-zero to enable) and the directory parameters
  `KUFDIR` / `KUFDEV` / `KUFDCG` (string parameters; see
  {doc}`parameter-setting`).
- The reader chain is `tr/trufile.f90` →
  `tr/tr_ufile_task.f90` (TASK-side dispatch) →
  `tr/tr_ufile_topics.f90` (per-topic decoders).
- For most users running prescribed-profile or
  analytic-geometry scenarios, ufiles are NOT needed —
  the default `MDLUF = 0` is correct. The entry exists to
  point readers at the chain when they encounter a research
  workflow that does need experimental input.

### §3.3 `trmodels/` and other model-side data

- Some transport models embed lookup tables or coefficient
  data (e.g. NCLASS-style modules). The codebase carries
  these inline in the source rather than as separate runtime
  files, so the page documents this fact rather than
  promising a directory layout that doesn't exist.
- The implementation step verifies whether any current
  transport model consults a runtime `trmodels/` directory.
  If yes, document the convention; if not, state that runtime
  external data is currently limited to eqdata + ufiles only.

### §3.4 File placement and path constraints

- The `eq` C-string interface caps `KNAMEQ` (and similar
  string parameters) at 80 bytes (verified during the
  L-7b-ii session: longer absolute paths were rejected by
  `EqlibInvalidParamError` at `python/eqlib/eqlib.py:67`).
- Recommended pattern: `chdir` to a working directory that
  holds the eqdata file(s) and pass the bare filename. This
  is what the existing `python/totlib/tests/test_pipeline_*`
  do.
- Absolute paths over 80 bytes will fail at parameter-set
  time, before `run()` is called; users will see the error
  immediately rather than at run time.

### §3.5 Cross-references

`{doc}\`parameter-setting\``, `{doc}\`limitations-and-references\``,
`{doc}\`design\``, `{doc}\`numerical-stability-and-diagnostics\``.

## §4. Page structure — `extending-tr.md`

### Header

- Title (en): "Extending TR"
- Title (ja): "TR の拡張"
- Admonition: this page is **maintainer-facing**. The
  audience has the source tree checked out and is comfortable
  editing Fortran. Three concrete walkthroughs follow. Each
  is a recipe — not a derivation.

### §4.1 Walkthrough A — Add a new scalar parameter

- The TR parameter registry uses a hand-written
  `SELECT CASE` dispatch in `tr/tr_param_registry.f90:76+`.
  Adding a parameter `FOO` is one new `CASE` line.
- Recipe (5 steps):
  1. If the parameter is new (not already in TRCOMM),
     declare it in the appropriate `tr/trcomm*.f90` module.
  2. Add a `CASE ("FOO"); FOO = value` line in
     `tr_param_registry.f90` near similar parameters
     (preserve the per-section grouping convention).
  3. Set a sensible default in `tr/trinit.f90`.
  4. `make -C tr libtrapi.so` to rebuild.
  5. From Python, `tr.set_param("FOO", x)` works
     immediately — the C ABI does not change because
     parameters are passed by name string.
- The page notes that array-valued parameters use a
  similar pattern with bounds checking; cite the existing
  `PA[i]` / `PN[i]` cases as templates
  (`tr_param_registry.f90:101-106` for the array idiom).

### §4.2 Walkthrough B — Add a new transport model under `MDLKAI`

- Turbulent heat transport is dispatched via
  `SELECT CASE(MDLKAI)` at `tr/trcoef_turbulence.f90:400+`.
  Each `MDLKAI` value invokes a different model.
- Numbering convention (per the source-side comments at
  `tr/trcoef_turbulence.f90:392-398`):
  - `MDLKAI < 10`: constant-coefficient toy models.
  - `10 ≤ MDLKAI < 20`: drift-wave (+ITG/+ETG).
  - `20 ≤ MDLKAI < 30`: Rebu-Lalla.
  - `30 ≤ MDLKAI < 40`: current-diffusivity-driven (CDBM).
  - `40 ≤ MDLKAI < 60`: drift-wave-ballooning.
  - `MDLKAI ≥ 60`: ITG / TEM / ETG model families.
- Recipe (4 steps):
  1. Pick a `MDLKAI` value in the appropriate range.
  2. Add a `CASE (N)` block in
     `tr/trcoef_turbulence.f90` that fills the appropriate
     transport-coefficient arrays (`AKDW`, `ADDW`, `AVK`).
  3. If the new model needs auxiliary data, add the
     loader to `tr/trcoef.f90` or a new module per the
     existing per-family file split.
  4. Update the entry in {doc}`appendix-mdlkai` so users
     can find your new case in the catalogue.
- The page notes that other selector axes (`MDLAD`,
  `MDLAVK`, `MDLETA`) follow analogous dispatch patterns
  in their respective `trcoef_*.f90` files; the recipe
  generalises.

### §4.3 Walkthrough C — Add a new `TrState` field (ABI-impact recipe)

- This is the most invasive walkthrough. Adding a field to
  `tr_state_t` changes the C ABI, so external binary
  consumers may need to be rebuilt or version-checked.
- Recipe (7 steps):
  1. **Compute the quantity.** If the value is not already
     in TRCOMM, add a TRCOMM variable in the appropriate
     `tr/trcomm*.f90` module and assign it in the routine
     where it naturally falls (e.g. a new derived diagnostic
     would go into `tr/trrslt_globals.f90` or `trrslt_print.f90`).
  2. **Add the C-side field** — append a
     `REAL(C_DOUBLE)` (or appropriate kind) to the
     `tr_state_c` derived type in `tr/tr_state.f90:43-60`.
     Place it at the **end** of the struct so existing
     field offsets stay stable; this minimises the breakage
     surface for binary consumers.
  3. **Mirror in `tr/tr_api.h:53-60`** as a matching
     `double` (or correct C type).
  4. **Bump `TR_STATE_ABI_VERSION`** at
     `tr/tr_api.h:38`. Version 2 is the current value;
     bump to 3 (or whatever is next).
  5. **Mirror in the ctypes side** at
     `python/trlib/_ffi.py` — append a tuple to
     `TrStateC._fields_` (around line 95-120).
  6. **Surface in the Python `TrState` dataclass** at
     `python/trlib/state.py` — add the attribute and the
     parser line.
  7. **Update {doc}`state`** with the new attribute.
- Test plan: rebuild `libtrapi.so`, smoke-test that
  `Trlib().get_state()` returns the new field with a
  reasonable value; run the canonical pytest sweep
  (`python/trlib/tests/`) to confirm no regression.
- Worked example: the L-7b-i precedent. The `AJRFT`
  field was added via this same recipe; cite the L-7b-i
  PR (`#187`, merged commit `e049a1e4`) as a reference.

### §4.4 Cross-references

`{doc}\`design\``, `{doc}\`appendix-mdlkai\``,
`{doc}\`state\``, `{doc}\`physics-overview\``.

## §5. Bilingual content

Same convention as G / E / A. Headings translated faithfully;
identifiers (`MDLKAI`, `KNAMEQ`, `TR_STATE_ABI_VERSION`)
inline-code in both languages. The `MDLKAI` numbering ranges
(`< 10`, `10-20`, etc.) are notation-only and stay numeric in
both.

## §6. What this work is NOT

- Not a tutorial on Fortran (the maintainer audience is
  assumed to be comfortable editing Fortran already).
- Not a tutorial on the EQDSK format (canonical doc lives
  in the `eq` chapter / external community sources; the
  Input files page just points at it).
- Not a comprehensive ufile spec (same reason — community
  format outside TASK).
- Not a refactor of the parameter registry, the transport-
  model dispatch, or the `tr_state_t` ABI (those are
  documented as-is; rewriting them is a different PR).
- Not a tutorial on contributing to the upstream codebase
  (PR conventions, code review process, etc. — those belong
  in a contributor guide that doesn't exist yet, separate
  scope).

## §7. Test / verification

- Build: `make -C docs/sphinx html` should succeed without
  new warnings (locally blocked by missing `furo`; CI does
  the full broken-ref check).
- Manual: render and visually verify both new pages appear
  in the right toctree section (User guide for input-files,
  Internals for extending-tr) and all `{doc}` cross-links
  resolve.
- No code or test changes; pytest is N/A.

## §8. Pre-push gate

Same as G / E / A: 2 reviewers in parallel (in-house +
Codex), REVIEW_OK marker, push. Reviewer focus:

- **Factual accuracy of code citations.** Every file:line
  citation must point at the claimed content (we paid for
  the parallel-reviewer pattern in A — Codex round-3 said
  PASS on MDLKNC line numbers, but the in-house reviewer
  caught they were wrong via grep. Both reviewers must
  spot-check).
- **No fabrication.** No fabricated ufile spec details, no
  fabricated `trmodels/` directory layout, no fabricated
  numbering convention beyond what `trcoef_turbulence.f90`
  comments document, no fabricated step counts.
- **L-7b-i `AJRFT` precedent verified.** The §4.3 walkthrough
  cites the L-7b-i PR as the worked example; the
  implementation step verifies that PR # is correct and
  the merged commit SHA matches.
- **Cross-link correctness.** All `{doc}` targets exist;
  toctree updates land cleanly.
- **Bilingual parity.** en and ja line up structurally.
- **Path constraint section.** The 80-byte string limit
  claim must be verified against the current
  `python/eqlib/eqlib.py` (we cited line 67 from earlier
  in this session; the implementation step re-verifies in
  case the file moved).

## §9. Out of scope (deferred)

- Adding a new equation (`MDLEQ*` set extension). That
  would change the matrix size and require deeper changes
  in `trexec.f90` than a "new param" walkthrough covers;
  defer to a future spec if the user wants that recipe.
- A complete EQDSK format reference (community-canonical;
  pointer-only).
- A complete ufile spec.
- Migration / contribution guidelines for upstream
  (`ats-fukuyama/bpsd` etc.).
- A "remove a parameter" walkthrough — we cover only
  additions; removals require backward-compat thinking
  that belongs in its own document.

## §10. Acceptance criteria

1. ✅ `docs/sphinx/modules/tr/en/input-files.md` exists with sections §3.1, §3.2, §3.3, §3.4, §3.5.
2. ✅ ja counterpart of input-files exists, structurally aligned.
3. ✅ `docs/sphinx/modules/tr/en/extending-tr.md` exists with §4.1, §4.2, §4.3, §4.4.
4. ✅ ja counterpart of extending-tr exists, structurally aligned.
5. ✅ `index.md` (en + ja) inserts `input-files` after `parameter-setting` in User guide.
6. ✅ `index.md` (en + ja) inserts `extending-tr` after `design` in Internals.
7. ✅ §3.1 cites `tr/trbpsd.f90:213-245` for the MODELG-conditional equilibrium pull.
8. ✅ §3.2 lists the reader chain `trufile.f90` → `tr_ufile_task.f90` → `tr_ufile_topics.f90` and `MDLUF` default `0`.
9. ✅ §3.3 either documents the `trmodels/` convention (if it exists) OR states explicitly that no runtime model-side directory is currently consumed (whichever is verifiable from source).
10. ✅ §3.4 names the 80-byte path limit and cites `python/eqlib/eqlib.py:67` (or the current line — verify at impl).
11. ✅ §4.1 walkthrough cites `tr/tr_param_registry.f90:76+` and the array-pattern at `:101-106` (or the current lines — verify).
12. ✅ §4.2 walkthrough cites the `SELECT CASE(MDLKAI)` at `tr/trcoef_turbulence.f90:400+` and reproduces the numbering convention from the source comments at `:392-398`.
13. ✅ §4.3 walkthrough's 7 steps cite the right files at the right line ranges: `tr/tr_state.f90:43-60`, `tr/tr_api.h:38`, `tr/tr_api.h:53-60`, `python/trlib/_ffi.py` (verified line for `TrStateC._fields_`), `python/trlib/state.py`. The `AJRFT` worked-example claim ties to L-7b-i (commit `e049a1e4` per memory; verify PR # and SHA at impl).
14. ✅ All `{doc}` cross-references resolve.
15. ✅ Both reviewers (in-house + Codex) post-implementation report no HIGH findings.
