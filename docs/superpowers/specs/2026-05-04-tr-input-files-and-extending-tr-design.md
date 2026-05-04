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

- `MODELG ∈ {3, 5, 8, 9}` triggers TR's BPSD-side
  equilibrium pull (`tr/trbpsd.f90:213`). The `eq` module
  itself only treats `MODELG ∈ {3, 5, 8}` as a real EQDSK
  load (per `eq/eq_api.f90:105-108`); `MODELG = 9` is a
  TR-side alias the BPSD pull also accepts. The page
  documents both numbers so users do not get confused
  if their `eq` configuration uses `9`.
- The path is set via `KNAMEQ` (string parameter) — see
  {doc}`parameter-setting` for how to set string params.
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
  to non-zero to enable). `MDLUF` IS exposed in
  `tr/tr_param_registry.f90` and can be set from
  `tr.set_param("MDLUF", ...)`; default verified at
  `tr/trinit.f90:641-648`.
- **The directory parameters `KUFDIR` / `KUFDEV` / `KUFDCG`
  are namelist-only.** They appear in the legacy `&trn`
  namelist input (`tr/trparm.f90:108-112`) but are NOT
  exposed in `tr_param_registry.f90` (the registry has a
  comment marking them as "future additions" at
  `tr/tr_param_registry.f90:184-186`). Setting them via
  `tr.set_param_str` will fail. Users who need to point
  TR at a non-default ufile directory must either run from
  the legacy namelist-driven `tr2` driver or set up the
  directory via Fortran-side defaults / source edit until
  these get added to the registry.
- The reader chain is `tr/trufile.f90:70-77` (dispatch
  stub) → `tr/tr_ufile_task.f90:7` (`TR_TIME_UFILE` /
  `TR_STEADY_UFILE` entry points) → `tr/tr_ufile_topics.f90:7`
  (`TR_TIME_UFILE_TOPICS` per-topic decoders).
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
  string parameters) at 80 bytes. The constant is defined at
  `python/eqlib/eqlib.py:39`, the docstring stating "up to
  79 bytes" (the byte budget reserves 1 byte for the
  trailing NUL) lives at `:47-50`, and the actual length
  rejection is `EqlibInvalidParamError` at `:67`. The page
  uses **byte** rather than "character" because the limit
  applies to encoded bytes, not codepoints.
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
- Recipe (8 steps — Codex review caught that the original
  7-step draft omitted the Fortran-side population step
  and underspecified the Python parser side):
  1. **Compute the quantity.** If the value is not already
     in TRCOMM, add a TRCOMM variable in the appropriate
     `tr/trcomm*.f90` module and assign it in the routine
     where it naturally falls (e.g. a new derived diagnostic
     would go into `tr/trrslt_globals.f90` or `trrslt_print.f90`).
  2. **Add the C-side field** — append a
     `REAL(C_DOUBLE)` (or appropriate kind) to the
     `tr_state_c` derived type at `tr/tr_state.f90:43-67`
     (the type definition runs through line 67, not the
     :43-60 range the original draft cited). Place the
     new field at the **end** of the type so existing
     field offsets stay stable; this minimises the breakage
     surface for binary consumers.
  3. **Mirror in `tr/tr_api.h:49-60`** as a matching
     `double` (or correct C type). The struct definition
     starts at line 49, not 53.
  4. **Populate the field inside `tr_api_get_state`.** This
     is the step the original draft omitted. The actual
     copy from TRCOMM into the BIND-C struct lives at
     `tr/tr_api.f90:263-283` (per-radius / per-species
     loops) and `:299-315` (scalar copy block). Add the
     assignment alongside the existing field copies. The
     `AJRFT` precedent is the model to follow.
  5. **Bump `TR_STATE_ABI_VERSION`** at
     `tr/tr_api.h:38`. The current value is `2`; bump to
     `3` (or whatever the next integer is at the time).
  6. **Mirror in the ctypes side** at
     `python/trlib/_ffi.py` — append a tuple to
     `TrStateC._fields_` at `python/trlib/_ffi.py:94-120`.
     Use the same field order as the BIND-C struct so the
     two layouts stay byte-compatible.
  7. **Surface in the Python `TrState` dataclass** at
     `python/trlib/state.py`. Two cases:
     - *Scalar field*: add the field name to the
       `SCALAR_FIELDS` list (`python/trlib/state.py:22-28`)
       and the parser at `:50-72` and `:87-100` will pick
       it up automatically. The field becomes accessible
       as `state.scalars["YOUR_FIELD"]`.
     - *Array / profile field* (1-D or 2-D, indexed by
       `nrmax` or `nrmax × nsmax`): add a top-level
       attribute on the `TrState` dataclass and the
       corresponding `from_c` parser line by hand,
       mirroring how `AJ` / `RN` / `RT` are handled.
  8. **Update {doc}`state`** with the new attribute or
     scalar key.
- **Trap for 2-D fields — Fortran/C array order mirroring.**
  Fortran is column-major and C is row-major. The existing
  `RN` / `RT` fields handle this by *transposing* the
  index order between the Fortran declaration
  (`RN(TR_MAX_NSMAX, TR_MAX_NRMAX)` at
  `tr/tr_state.f90:60-61`) and the C declaration
  (`RN[TR_MAX_NRMAX][TR_MAX_NSMAX]` at
  `tr/tr_api.h:53-54`). The ctypes mirror at
  `python/trlib/_ffi.py:112-113` follows the C layout. Any
  new 2-D field must follow the same transposition pattern
  or the bytes will be reinterpreted incorrectly.
- Test plan: rebuild `libtrapi.so`, smoke-test that
  `Trlib().get_state()` returns the new field with a
  reasonable value; run the canonical pytest sweep
  (`python/trlib/tests/`) to confirm no regression.
- Worked example: the L-7b-i precedent. The `AJRFT`
  field was added via this same recipe; cite PR
  [#187](https://github.com/k-yoshimi/task/pull/187),
  merged commit `e049a1e4`. The actual touch points to
  imitate are: `tr/tr_state.f90:64-66` (BIND-C field),
  `tr/tr_api.h:57-59` (C field), `python/trlib/_ffi.py:116-119`
  (ctypes field), `python/trlib/state.py:27` (scalar
  registration).

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
7. ✅ §3.1 cites the MODELG set as `{3, 5, 8, 9}` (per `tr/trbpsd.f90:213`) AND notes that `eq` mode-1 only treats `{3, 5, 8}` as real EQDSK loads (per `eq/eq_api.f90:105-108`); the `9` is a TR-side BPSD-pull alias. (Codex round-1 HIGH 1.)
8. ✅ §3.2 lists the reader chain `trufile.f90:70-77` → `tr_ufile_task.f90:7` → `tr_ufile_topics.f90:7`; `MDLUF` default `0` cited at `tr/trinit.f90:641-648`. **Explicitly states `KUFDIR` / `KUFDEV` / `KUFDCG` are namelist-only, not `tr_set_param`-reachable** (per `tr/tr_param_registry.f90:184-186` "future additions" comment + `tr/trparm.f90:108-112` namelist input). (Codex round-1 HIGH 2.)
9. ✅ §3.3 states explicitly that no runtime `trmodels/`-style directory is currently consumed (Codex verified: `tr/trmodels.f90` calls compiled-in driver routines `mbgb_driver` / `mmm95_driver` / `mmm71_driver` directly with no `OPEN`/`READ` from a runtime directory). Runtime external data is limited to eqdata + ufiles only.
10. ✅ §3.4 names the 80-byte path limit AND cites all three loci in `python/eqlib/eqlib.py`: the constant at `:39`, the docstring at `:47-50`, and the rejection check at `:67`. The page uses "byte" rather than "character" for accuracy. (Codex round-1 MED 4.)
11. ✅ §4.1 walkthrough cites `tr/tr_param_registry.f90:76` for the SELECT CASE entry and `:101-106` for the array-pattern (`PA[i]` / `PN[i]` etc.). `tr_set_param` confirmed string-keyed via `tr/tr_api.f90:124-128,136-148`.
12. ✅ §4.2 walkthrough cites the `SELECT CASE(MDLKAI)` at `tr/trcoef_turbulence.f90:400` (the dispatch — NOT line 64 which only sets graph labels) and reproduces the numbering convention verbatim from the source comments at `:392-398`.
13. ✅ §4.3 walkthrough has **8 steps** (was 7 in the original draft; Codex round-1 HIGH 7 caught the missing Fortran population step inside `tr_api_get_state`). Line ranges are correct:
    - Step 2: `tr/tr_state.f90:43-67` (was incorrectly :43-60)
    - Step 3: `tr/tr_api.h:49-60` (struct starts at :49, not :53)
    - Step 4 (NEW): Fortran population at `tr/tr_api.f90:263-283` (loops) + `:299-315` (scalar block)
    - Step 5: `tr/tr_api.h:38` ABI version (verified `= 2`)
    - Step 6: `python/trlib/_ffi.py:94-120` (was vague "around 95-120")
    - Step 7: `python/trlib/state.py:22-28` (`SCALAR_FIELDS` list) + `:50-72` and `:87-100` (parser) — the original draft missed this entire mechanism.
    The `AJRFT` worked-example claim ties to L-7b-i with verified PR `#187` + commit `e049a1e4`. The §4.3 also includes a **Fortran/C array-order trap warning** for 2-D fields (Codex round-1 MED 10.2).
14. ✅ All `{doc}` cross-references resolve.
15. ✅ Both reviewers (in-house + Codex) post-implementation report no HIGH findings.
