# TR Manual — Tutorials D1 (T1 + T3) — Design

**Status:** Draft
**Date:** 2026-05-04
**Project memory:** `project_tr_proper_manual.md` ("Multi-scenario tutorials" — 2-session expansion target, item D in the deepening menu; this spec covers D1 = the first half: T1 + T3, with T2 deferred and T4-T6 reserved for D2)
**Predecessors today:**
- A first User-guide entry (`physics-overview`, commit `c5210076`)
- E (`numerical-stability-and-diagnostics`, commit `fc74599d`)
- F input-files + extending-tr (commit `1a2fa692`)
- G (`limitations-and-references`, commit `a8b83311`)
- audit (a) (`mcp.md` 'Usage scenarios' translation + 6-module dead-ref drop, commits `2d8844f2` + `47bec20f`)
- audit (b) (5-module PEP 604/585 conversion, commit `9aea7755`)

---

## §1. Overview

Add a single bilingual page to the TR Sphinx chapter — the
"Tutorials" entry — covering 2 worked tutorials:

- **Tutorial T1** — ITER-like single-run scenario using the
  `eqdata.ITER01` fixture
- **Tutorial T3** — Parameter sweep
  (`PT[1] × PN[1]` — axis ion temperature × axis ion
  density, two array-element initial-profile knobs that
  survive the BPSD plasma pull because BPSD writes
  `RN`/`RT` rather than `PN`/`PT`) with matplotlib
  heatmap output

This is the "D1" half of the multi-scenario tutorials menu
item (memory `project_tr_proper_manual.md`). The originally-
planned T2 (JET) is **deferred** because no JET fixture is
shipped in the repo (`eqdata.JET` does not exist); T2 will
be reconsidered in D2 (either with an analytic-equilibrium
JET-like setup or a new fixture). T4 (tr2 equivalence), T5
(tot coupled run), T6 (numerical blow-up debug) are reserved
for D2.

Sized at 1 session for D1.

## §2. File structure

**New files (bilingual pair):**

- `docs/sphinx/modules/tr/en/tutorials.md`
- `docs/sphinx/modules/tr/ja/tutorials.md`

**Edited files:**

- `docs/sphinx/modules/tr/en/index.md` — insert
  `tutorials` into the User guide toctree, after
  `applications` (the recipes page T3 reuses).
- `docs/sphinx/modules/tr/ja/index.md` — same.

No new MyST anchor labels are needed.

## §3. Page structure

### Header

- Title (en): "Tutorials"
- Title (ja): "チュートリアル"
- One-paragraph admonition stating the audience (you have
  read hello-world / parameter-setting / applications) and
  what D1 covers (T1 + T3 only). Includes a "what's next"
  pointer to D2 for the remaining 4 tutorials.

### §3.1 Tutorial T1 — ITER-like single-run scenario (~80 lines)

**Goal:** Walk a reader through a single 100-step run using
the shipped `eqdata.ITER01` equilibrium fixture (TASK/EQ
binary format, loaded via `EQRTSK` under `MODELG=3` —
see `eq/eqfile.f90:108-115` and {doc}`input-files` for the
`MODELG ∈ {3, 5, 8, 9}` dispatch table), and show how to
read the resulting `TrState`.

Outline:

1. **Set-up.** The reader must `chdir` into the directory
   that holds `eqdata.ITER01` because the C string limit on
   `KNAMEQ` is 80 bytes (cross-link {doc}`input-files`). The
   fixture lives at
   `python/eqlib/tests/fixtures/eqdata.ITER01`.
2. **The script.** A self-contained Python block (~30
   lines) using `Trlib` directly. The base parameters are
   applied via `tr_iter01_params.apply(tr)` (the same
   helper called from
   `python/trlib/tests/test_sweep.py:90`; the sweep test
   then overrides `RR` / `BB`, but those overrides are
   silently clobbered — see §3.2 step 2 — so T1
   intentionally does NOT override geometry), which sets
   `MODELG=3`, `NSMAX=4`,
   `set_param_str("KNAMEQ", "eqdata.ITER01")`, `RIPS` /
   `RIPE`, plasma profile arrays (`PN` / `PNS` / `PT` /
   `PTS`), and heating-source scalars. The script then
   calls `validate()` to confirm preconditions,
   `run(ntmax=100)`, then `get_state().scalars` for
   `WPT`, `BETAN`, `Q0`, `TAUE1`. Geometry (`RR`, `RA`,
   `RKAP`, `RDLT`, `BB`) is loaded from the TASK/EQ binary
   file on the first `tr_run` call (the chain is
   `tr_run` → `tr_prep` → `tr_set_metric` → `eq_load` +
   `tr_bpsd_get`; see `tr/tr_api.f90:223,228`,
   `tr/trprep.f90:83`, `tr/trmetric.f90:41,46`) — the
   script does NOT set geometry explicitly; cross-link
   {doc}`input-files` for the `MODELG`-vs-loader
   dispatch table.
3. **Parameter values.** All non-geometry knobs come
   verbatim from the tr-side fixture
   `python/trlib/tests/fixtures/tr_iter01_params.py`
   (SCALARS at lines 21-47, ARRAYS at lines 51-56,
   STRINGS at lines 60-62). Highlights cited in the
   page: `MODELG=3`, `NSMAX=4`, `RIPS=2.0`, `RIPE=7.0`,
   `DT=0.02`, `KNAMEQ="eqdata.ITER01"`. The fixture
   mirrors the namelist in `test_run/inputs/tr_iter01.in`.
   Geometry is loaded from the TASK/EQ binary file
   (`python/eqlib/tests/fixtures/eqdata.ITER01`); the
   page does NOT invent or assert geometry numbers, and
   in particular does NOT cite the eq-side namelist
   parameters (`RR=6.2`, `RB=2.1`, `RIP=15.0`, …) because
   tr's registry differs from eq's — tr has `RIPS` /
   `RIPE` instead of `RIP` (registered at
   `tr/tr_param_registry.f90:114-115`), and no `RB`
   anywhere in the registry's geometry block
   (`tr/tr_param_registry.f90:78-84`).
4. **Output.** The `expected output:` block uses
   placeholder text (`WPT = …`, etc.) rather than concrete
   numbers, because the exact values depend on the build
   configuration and could drift. The page tells the reader
   "run this and read the values yourself."
5. **Extensions.** Two short extension suggestions:
   - Vary `PT[1]` (axis ion temperature) over
     `{0.7, 1.0, 1.5}` (keV) as a single-axis warm-up
     before T3, which extends this to a 2-axis
     `PT[1] × PN[1]` sweep. Note: `RIPS` looks like an
     obvious alternative single-axis knob but is
     silently overwritten by the BPSD broker
     (`tr/trbpsd.f90:370-374`); see §3.2 step 2.
   - Compare against a `MODELG=2` analytic equilibrium
     (no eqdata file needed).

### §3.2 Tutorial T3 — Parameter sweep with heatmap (~80 lines)

**Goal:** Run a 3×3 `PT[1] × PN[1]` sweep (axis ion
temperature × axis ion density) and plot the resulting
`WPT` field as a heatmap.

Outline:

1. **Recall the `sweep()` pattern.** Cross-link
   {doc}`applications` §2 — the existing `sweep()`
   wrapper. T3 does NOT redefine the wrapper; it imports
   the pattern by reference.
2. **The sweep.** `PT[1] ∈ {0.7, 1.0, 1.5}` (keV, axis
   ion temperature; centered on the ITER01 fixture base
   `PT[1]=1.0` from
   `python/trlib/tests/fixtures/tr_iter01_params.py:54`)
   × `PN[1] ∈ {0.5, 0.7, 1.0}` (10²⁰ m⁻³, axis ion
   density; centered on fixture base `PN[1]=0.7` from
   `tr_iter01_params.py:52`), `ntmax = 20` (short enough
   to be quick on a laptop; long enough for `WPT` to
   start responding). The array-element subscript
   syntax `tr.set_param("PT[1]", 1.0)` is the canonical
   Trlib pattern (`PT` and `PN` registered as array
   `CASE` entries at `tr/tr_param_registry.f90:101-106`;
   `parse_array_subscript` is called at line 74 and
   implemented at `:209-230`); the page introduces this
   in a 1-paragraph side-bar.

   **Why `PT[1] × PN[1]` and not other axes — explicit
   gotcha section the page MUST include.** Three
   alternatives a reader might try first all fail
   silently under the ITER01 fixture's `MODELG=3`:
   - `RR × BB` (geometry sweep): the BPSD broker pull
     (`tr/trbpsd.f90:171-178`, called from
     `tr_set_metric` at `tr/trmetric.f90:46` on the
     first `tr_run` call) overwrites
     `RR`/`RA`/`BB`/`RIP`/`RKAP`/`RDLT` from the loaded
     equilibrium device (TASK/EQ binary under
     `MODELG=3`, dispatched via `EQRTSK` —
     `eq/eqfile.f90:108-115`), clobbering any user
     `set_param("RR", ...)`.
   - `RIPS × RIPE` (plasma-current ramp sweep): the
     same BPSD pull recalibrates `RIPS` and `RIPE` from
     the metric-derived current at
     `tr/trbpsd.f90:370-374`, again clobbering user
     overrides.
   - `PNBTOT × <anything>` (NBI total-power sweep):
     `PNBTOT` (the actual NB amplitude in MW —
     `tr/trinit.f90:419`) is **not** in
     `tr/tr_param_registry.f90`, so `set_param("PNBTOT",
     ...)` raises `INVALID`. Worth flagging in the page
     because `PNBR0` (`tr/trinit.f90:420`, "RADIAL
     POSITION OF NBI POWER DEPOSITION (M)") is the
     visible NB knob in the fixture but is a deposition
     center, not an amplitude.

   `PT[1]` and `PN[1]` survive: `tr_prof` reads `PN` →
   `RN` at `tr/trprof.f90:227-228` and `PT` → `RT` at
   `:230-231`, the BPSD plasma pull
   (`tr/trbpsd.f90:183-204`) writes only `RN`/`RT` (not
   `PN`/`PT`), and `tr_set_metric` does not touch
   profile parameter arrays. `WPT` is the total stored
   plasma energy, approximately
   `Σ_s ∫(3/2) n_s T_s dV` over all bulk species
   (electrons + ions; computed from `WST(1:NSM)` at
   `tr/trrslt_globals.f90:115-127`), plus fast-particle
   tail energy `WTAILT` when `MDLUF≠0`
   (`tr/trrslt_globals.f90:315-322`); `MDLUF=0` in the
   ITER01 fixture so the tail is zero. The heatmap thus
   has a clean physical interpretation.
3. **Conversion.** Convert the resulting list-of-dicts
   into a 3×3 NumPy array of `WPT` values
   (`np.array(...).reshape(3, 3)`).
4. **Plot + expected output.** matplotlib heatmap with
   `plt.imshow(...)` + `colorbar()` + `xticks` /
   `yticks` labelled with the actual `PT[1]` / `PN[1]`
   values. Save to a PNG (or display interactively). The
   "expected output" block in the rendered page uses
   placeholder text (e.g., `WPT shape: (3, 3); values
   placeholder — run locally to populate`) rather than
   a concrete 3×3 numeric matrix, for the same drift-
   resistance reason as T1 (§3.1 step 4).
5. **Extensions.** Three short extension suggestions:
   - Switch to `pandas.DataFrame` for tabular output.
   - Parallelise with `multiprocessing.Pool` (cross-link
     {doc}`faq` Q4 — the singleton constraint requires
     process-level isolation).
   - For shape-optimisation studies (`RKAP × RDLT` or
     `RR × BB`), switch to `MODELG=2` (analytic
     equilibrium) so geometry knobs survive — under
     `MODELG=3` the BPSD pull would clobber them
     (see step 2 above). For NBI-amplitude sweeps,
     `PNBTOT` first needs registry registration (a
     separate planned change tracked outside this
     tutorial).

The page notes matplotlib is an optional dependency
(`pip install matplotlib`) and the script gracefully
degrades to a printed table if matplotlib is unavailable.

### §3.3 What's next (~10 lines)

A short pointer block:

- **T2 (JET-like):** deferred — no `eqdata.JET` fixture
  ships with the repo. D2 will revisit using either an
  analytic-equilibrium JET-like setup (MODELG=2 with
  JET-shape parameters) or a new fixture.
- **T4–T6:** D2 plans equivalence test (T4),
  `tot`-coupled run (T5), and numerical-blow-up debugging
  (T6).
- For an executable end-to-end notebook, see
  `tr-quickstart.ipynb` (the existing executable variant in
  the chapter).

## §4. Bilingual content

Same convention as the rest of the chapter (G / E / A / F /
audits). Headings translated faithfully; identifiers
(`Trlib`, `MODELG`, `KNAMEQ`, `set_param_str`) stay inline-
code in both languages; matplotlib / numpy / pandas stay
English. Code blocks are identical between en and ja
(comments inside the code blocks stay English; the prose
around them is translated).

## §5. What this page is NOT

- Not a Trlib API reference (that lives in
  {doc}`api-reference`).
- Not a parameter catalogue (that lives in
  {doc}`parameters`).
- Not a physics primer (that lives in
  {doc}`physics-overview`).
- Not a complete D-item delivery: T2 is deferred and
  T4-T6 are reserved for D2.
- Not a notebook — the executable form is
  `tr-quickstart.ipynb`; this page uses inline code blocks
  for readability + Codex reviewability (notebook JSON is
  hostile to diff review).

## §6. Test / verification

- Build: `make -C docs/sphinx html` should succeed without
  new warnings (locally blocked by missing `furo`; CI
  handles the full broken-ref check).
- Manual: render and visually verify both the en and ja
  pages slot into the User guide toctree right after
  `applications`, and that all `{doc}` cross-links
  resolve (`input-files`, `applications`, `faq`,
  `api-reference`, `parameters`, `physics-overview`).
- The Python code blocks themselves are not executed at
  build time — readers run them locally. The implementation
  step verifies the code blocks compile (`python -c "..."`
  syntax check) but does NOT actually call `Trlib()`
  because that would require `libtrapi.so` and the eqdata
  fixture path resolution.
- No code or test changes; pytest is N/A.

## §7. Pre-push gate

Same as G / E / A / F / audits: 2 reviewers in parallel
(in-house + Codex), REVIEW_OK marker, push. Reviewer focus:

- **Factual accuracy.** Tr-side ITER01 parameters
  (`MODELG=3`, `NSMAX=4`, `RIPS=2.0`, `RIPE=7.0`,
  `DT=0.02`, profile arrays, heating-source scalars)
  match
  `python/trlib/tests/fixtures/tr_iter01_params.py`
  (lines 21-47, 51-56, 60-62) byte-for-byte. Geometry is
  loaded from the TASK/EQ binary file
  (`python/eqlib/tests/fixtures/eqdata.ITER01`) on the
  first `tr_run` call via the
  `tr_run` → `tr_prep` → `tr_set_metric` → `eq_load` +
  `tr_bpsd_get` chain (`tr/tr_api.f90:223,228`,
  `tr/trprep.f90:83`, `tr/trmetric.f90:41,46`); the page
  does NOT assert any geometry numbers and does NOT
  cite the eq-side namelist fixture
  (`eq_iter01_params.py`) because tr's registry has
  `RIPS` / `RIPE`
  (`tr/tr_param_registry.f90:114-115`) and no `RIP` /
  `RB` in the geometry block
  (`tr/tr_param_registry.f90:78-84`).
- **No fabrication.** The "expected output" block uses
  placeholder values (`WPT = …`) — verify the page does
  NOT assert any specific numeric output.
- **Code consistency with audit (b).** The new T3 code
  block uses PEP 604 / 585 builtins (`list[dict]`,
  `dict | None`, no `from typing import`), consistent
  with the just-shipped audit (b) commit `9aea7755`.
- **Cross-link correctness.** All `{doc}` targets
  resolve.
- **Bilingual parity.** en and ja line up structurally.
- **No new MyST anchors.**
- **matplotlib gracefully optional.** The T3 code block
  does not crash if matplotlib is missing; falls back to
  a printed table.
- **Sweep axes survive BPSD pull.** T3 sweeps `PT[1]`
  and `PN[1]` (NOT `RR`/`BB`, NOT `RIPS`, NOT `PNBTOT`)
  and the page explicitly enumerates the three
  rejected alternatives with their failure mechanism:
  `RR`/`BB` clobbered by `tr/trbpsd.f90:171-178`,
  `RIPS`/`RIPE` clobbered by `tr/trbpsd.f90:370-374`,
  `PNBTOT` not in `tr/tr_param_registry.f90`. Verify
  `PN`/`PT` are NOT touched by the BPSD plasma pull
  (`tr/trbpsd.f90:183-204` writes `RN`/`RT`, not
  `PN`/`PT`).

## §8. Out of scope (deferred)

- **T2 (JET-like).** No `eqdata.JET` fixture ships in the
  repo. D2 will revisit either with an analytic JET-shape
  setup or a new fixture.
- **T4 (tr2 equivalence).** The 1e-10 equivalence
  comparison between Python wrapper and CLI `tr2` belongs
  in D2 (more involved; needs the `compare_metrics.py`
  workflow).
- **T5 (tot-coupled run).** Pipeline tutorial — D2.
- **T6 (numerical blow-up debugging).** Intentional-bad-DT
  walkthrough — D2.
- **Notebook variants.** Existing
  `docs/sphinx/shared/notebooks/tr-quickstart.ipynb`
  remains the executable form; this spec does NOT add new
  notebooks.
- **CI execution.** The Python code in tutorials is NOT
  executed by CI. If a future PR wants doctests / CI
  execution, that is a separate spec.

## §9. Acceptance criteria

1. ✅ `docs/sphinx/modules/tr/en/tutorials.md` exists with sections §3.1, §3.2, §3.3.
2. ✅ ja counterpart exists with structurally aligned content.
3. ✅ Both `index.md` files insert `tutorials` into the User guide toctree, after `applications`.
4. ✅ §3.1 ITER parameters match `python/trlib/tests/fixtures/tr_iter01_params.py` (SCALARS at lines 21-47, ARRAYS at lines 51-56, STRINGS at lines 60-62) byte-for-byte (`MODELG=3`, `NSMAX=4`, `RIPS=2.0`, `RIPE=7.0`, `DT=0.02`, plus profile arrays and heating scalars). The page does NOT cite the eq-side namelist fixture `eq_iter01_params.py` because tr's registry has `RIPS` / `RIPE` at `tr/tr_param_registry.f90:114-115` (no `RIP`) and no `RB` in the geometry block at `tr/tr_param_registry.f90:78-84`.
5. ✅ §3.1 cites `eqdata.ITER01` lives at `python/eqlib/tests/fixtures/eqdata.ITER01` and references {doc}`input-files` for the 80-byte path constraint.
6. ✅ §3.2 cross-links {doc}`applications` for the `sweep()` pattern rather than redefining it.
7. ✅ §3.2 code uses PEP 604 / 585 builtins (no `from typing import` lines, no capital `List` / `Dict` in code) — consistent with audit (b).
8. ✅ §3.2 includes a graceful fallback path when matplotlib is missing (printed table instead of plot).
9. ✅ §3.2 sweep axes are `PT[1] × PN[1]` (NOT `RR × BB`, NOT `RIPS × *`, NOT `PNBTOT × *`); the page explicitly enumerates all three rejected alternatives with their failure mechanism (BPSD geometry pull at `tr/trbpsd.f90:171-178`, BPSD current recalibration at `tr/trbpsd.f90:370-374`, `PNBTOT` missing from `tr/tr_param_registry.f90`).
10. ✅ Both T1 and T3 use placeholder text (`WPT = …` etc.) for "expected output" — no concrete numeric values asserted.
11. ✅ §3.3 mentions T2/T4/T5/T6 as D2 follow-up items.
12. ✅ All `{doc}` cross-references resolve.
13. ✅ Both reviewers (in-house + Codex) post-implementation report no HIGH findings.
