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
- **Tutorial T3** — Parameter sweep (`RR × BB`) with
  matplotlib heatmap output

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
the shipped `eqdata.ITER01` EQDSK fixture, and show how to
read the resulting `TrState`.

Outline:

1. **Set-up.** The reader must `chdir` into the directory
   that holds `eqdata.ITER01` because the C string limit on
   `KNAMEQ` is 80 bytes (cross-link {doc}`input-files`). The
   fixture lives at
   `python/eqlib/tests/fixtures/eqdata.ITER01`.
2. **The script.** A self-contained Python block (~30
   lines) using `Trlib` directly: `set_param` for the
   geometry knobs, `set_param("MODELG", 3)`,
   `set_param_str("KNAMEQ", "eqdata.ITER01")`, then
   `validate()` to confirm the preconditions, then
   `run(ntmax=100)`, then `get_state().scalars` for
   `WPT`, `BETAN`, `Q0`, `TAUE1`.
3. **Parameter values.** The geometry parameters come
   verbatim from the fixture
   `python/eqlib/tests/fixtures/eq_iter01_params.py:24-32`
   (`RR=6.2`, `RA=2.0`, `RKAP=1.7`, `RDLT=0.33`, `RB=2.1`,
   `BB=5.3`, `RIP=15.0`). The page does NOT invent new
   values; it cross-links the fixture.
4. **Output.** The `expected output:` block uses
   placeholder text (`WPT = …`, etc.) rather than concrete
   numbers, because the exact values depend on the build
   configuration and could drift. The page tells the reader
   "run this and read the values yourself."
5. **Extensions.** Two short extension suggestions:
   - Vary `RIP` over `{12, 15, 18}` and observe the trend
     in `BETAN` (forward-pointer to T3 sweep style).
   - Compare against a `MODELG=2` analytic equilibrium
     (no eqdata file needed).

### §3.2 Tutorial T3 — Parameter sweep with heatmap (~80 lines)

**Goal:** Run a 3×3 `RR × BB` sweep and plot the resulting
`WPT` field as a heatmap.

Outline:

1. **Recall the `sweep()` pattern.** Cross-link
   {doc}`applications` §2 — the existing `sweep()`
   wrapper. T3 does NOT redefine the wrapper; it imports
   the pattern by reference.
2. **The sweep.**
   `RR ∈ {3.0, 5.0, 6.5}` × `BB ∈ {3.0, 5.0, 7.0}`,
   `ntmax = 20` (short enough to be quick on a laptop;
   long enough that scalars stabilise).
3. **Conversion.** Convert the resulting list-of-dicts
   into a 3×3 NumPy array of `WPT` values
   (`np.array(...).reshape(3, 3)`).
4. **Plot.** matplotlib heatmap with
   `plt.imshow(...)` + `colorbar()` + `xticks` /
   `yticks` labelled with the actual `RR` / `BB` values.
   Save to a PNG (or display interactively).
5. **Extensions.** Three short extension suggestions:
   - Switch to `pandas.DataFrame` for tabular output.
   - Parallelise with `multiprocessing.Pool` (cross-link
     {doc}`faq` Q4 — the singleton constraint requires
     process-level isolation).
   - Sweep `RKAP × RDLT` instead of `RR × BB` for
     shape-optimisation studies.

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
  `applications`, and that the four `{doc}` cross-links
  resolve.
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

- **Factual accuracy.** ITER01 fixture parameters
  (`RR=6.2`, `RA=2.0`, `RKAP=1.7`, `RDLT=0.33`, `RB=2.1`,
  `BB=5.3`, `RIP=15.0`) match
  `python/eqlib/tests/fixtures/eq_iter01_params.py:24-32`
  byte-for-byte.
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
4. ✅ §3.1 ITER parameters match `python/eqlib/tests/fixtures/eq_iter01_params.py:24-32` byte-for-byte (`RR=6.2`, `RA=2.0`, `RKAP=1.7`, `RDLT=0.33`, `RB=2.1`, `BB=5.3`, `RIP=15.0`).
5. ✅ §3.1 cites `eqdata.ITER01` lives at `python/eqlib/tests/fixtures/eqdata.ITER01` and references {doc}`input-files` for the 80-byte path constraint.
6. ✅ §3.2 cross-links {doc}`applications` for the `sweep()` pattern rather than redefining it.
7. ✅ §3.2 code uses PEP 604 / 585 builtins (no `from typing import` lines, no capital `List` / `Dict` in code) — consistent with audit (b).
8. ✅ §3.2 includes a graceful fallback path when matplotlib is missing (printed table instead of plot).
9. ✅ Both T1 and T3 use placeholder text (`WPT = …` etc.) for "expected output" — no concrete numeric values asserted.
10. ✅ §3.3 mentions T2/T4/T5/T6 as D2 follow-up items.
11. ✅ All `{doc}` cross-references resolve.
12. ✅ Both reviewers (in-house + Codex) post-implementation report no HIGH findings.
