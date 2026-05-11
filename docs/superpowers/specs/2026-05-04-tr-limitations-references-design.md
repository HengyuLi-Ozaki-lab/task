# TR Manual — Known limitations & References (Appendix) — Design

**Status:** Draft
**Date:** 2026-05-04
**Project memory:** `project_tr_proper_manual.md` ("Known limitations + references" — 0.5-session expansion target)
**Predecessors:** `2026-04-23` Sphinx bootstrap (PR #173); 7-module `applications.md` ja → en series (commits 494177d8…6c4a2e57; tr completed at 169c17a9 / c3d1ce82 in this session)

---

## §1. Overview

Add a single bilingual page to the TR Sphinx chapter — the
"Known limitations & references" appendix — covering four
limitations and two reference sections. The page consolidates
references to existing material via cross-links, adds new content
for previously-undocumented limits (thread safety, the actual scope
of `TR_MAX_NRMAX` / `TR_MAX_NSMAX`), and frames TASK/TR alongside
related open transport codes.

This is the "G" item from the deepening menu in
`project_tr_proper_manual.md`, sized at 0.5 session.

## §2. File structure

**New files (bilingual pair):**

- `docs/sphinx/modules/tr/en/limitations-and-references.md`
- `docs/sphinx/modules/tr/ja/limitations-and-references.md`

**Edited files (toctree + MyST labels):**

- `docs/sphinx/modules/tr/en/index.md` — append `limitations-and-references` to the Appendix toctree (after `appendix-sensitivity`)
- `docs/sphinx/modules/tr/ja/index.md` — same
- `docs/sphinx/modules/tr/en/faq.md` — add MyST label `(faq-singleton)=` directly above `## Q4. ...`
- `docs/sphinx/modules/tr/ja/faq.md` — same label
- `docs/sphinx/modules/tr/en/design.md` — add MyST label `(reinit-constraints)=` directly above `## Re-initialisation constraints`
- `docs/sphinx/modules/tr/ja/design.md` — same label

The label additions are minimally invasive (one line per file) and
make the cross-references stable against future heading rewordings.

## §3. Page structure

### Header
- Title (en): "Known limitations and references"
- Title (ja): "既知の制約と参考資料"
- Brief 1-paragraph admonition explaining the page is a summary of
  what TR cannot do plus pointers to wider context.

### §3.1 Section "Known limitations"

Four subsections, each ≤ 1 paragraph:

1. **Single instance per process**
   - 1–2 sentences: "Trlib enforces one live instance per process via
     a weakref guard (#171)."
   - Cross-link: `{ref}\`faq-singleton\``.
   - No duplication of the full FAQ explanation.

2. **Module-level state reset**
   - 1–2 sentences: "Repeating `tr_finalize` → `tr_init` does not
     fully reset module-level Fortran state."
   - Cross-link: `{ref}\`reinit-constraints\``.
   - No duplication of the design.md full discussion.

3. **Thread safety** (new)
   - One paragraph: TR is not thread-safe — module-level COMMON-block
     state is shared across all calls in the same process. For
     parallel work, spawn separate processes (e.g. `multiprocessing.Pool`
     as shown in `applications.md` `sweep()`); avoid `threading.Thread`.
   - Cross-link: `{doc}\`applications\`` for the multiprocessing pattern.

4. **Compile-time bounds (state buffer)** (new, replaces
   "Memory footprint" per Codex review HIGH 1)
   - One paragraph clarifying the actual contract:
     `TR_MAX_NRMAX = 500` and `TR_MAX_NSMAX = 8` (defined in
     `tr/tr_api.h`) bound only the **exported** `tr_state_t` buffer
     dimensions, NOT the total resident set. Internal TRCOMM
     allocations and linked libraries contribute additional memory
     not captured by these constants. No RSS ceiling is asserted
     without measurement.
   - Cross-link: `{doc}\`state\``.

### §3.2 Section "References"

Two subsections:

1. **Original TASK publications** (new, generic pointer)
   - 2–3 sentences: "The TASK code suite (including TR) is developed
     by Prof. Fukuyama's group (Kyoto University). The upstream
     repositories are at `github.com/ats-fukuyama`. For
     publications, consult that group's bibliography." NO specific
     paper titles / years / DOIs — citations only get added later
     once verified by the user.

2. **Related open transport codes** (new, comparison table)
   - One leading paragraph noting that comparison-row content for
     non-TASK codes summarises upstream public documentation as of
     the page's date; the linked URLs are the authoritative source
     for current scope and access policy.
   - Table with 4 codes × 5 columns:

     | Code | Spatial | Time mode | Heating coverage | Access / URL |
     |---|---|---|---|---|
     | TASK/tr (this) | 1D radial | Predictive (time-evolving) | NB/EC/LH/ICRF source selectors registered via `MDLNB`/`MDLEC`/`MDLLH`/`MDLIC` | Open — github.com/ats-fukuyama |
     | ASTRA | 1.5D | Predictive + interpretive | Modular | Collaboration-based — see upstream documentation |
     | JETTO-SANCO | 1D transport + impurity | Predictive + interpretive | NB/EC/ICRH | EUROfusion-restricted — see upstream documentation |
     | TRANSP | 1.5D | Interpretive primary; predictive available | NUBEAM, TORAY etc. | Documentation: transp.pppl.gov; source via PPPL collaboration |

   - Each non-TASK row is hedged ("see upstream documentation" /
     "documentation: …") so claims are pointer-shaped, not
     authoritative summaries.

## §4. Bilingual content

The ja and en pages share structure exactly. Code names
(TASK/tr, ASTRA, JETTO-SANCO, TRANSP) are proper nouns and stay
unchanged. Table column headers stay English in both ja and en
files (consistent with the existing tr chapter convention; see
`appendix-mdlkai.md`). Inline prose is full ja in the ja file
and full en in the en file.

## §5. Cross-link mechanics

MyST labels added to existing files:

```markdown
(faq-singleton)=
## Q4. Can I create two `Trlib()` instances in the same process?
```

```markdown
(reinit-constraints)=
## Re-initialisation constraints
```

Targeted from the new appendix via `{ref}\`faq-singleton\`` and
`{ref}\`reinit-constraints\``. Both are file-local in their
respective targets, but `{ref}` resolves across the doc tree as
long as labels are unique. To minimise collision risk, the labels
are namespaced informally (`faq-` and `reinit-` prefixes are
distinctive enough within the tr chapter).

If a future PR introduces matching labels in another chapter, the
MyST `:doc:` resolver gives a warning at build time — that PR
would rename. No pre-emptive namespacing beyond the prefixes.

## §6. What this page is NOT

- Not an exhaustive change-log of past limitations (the issue
  tracker has that role).
- Not a tutorial on parallel programming (only points at the
  multiprocessing pattern in `applications.md`).
- Not an academic literature review (publications are pointed to
  generically; a separate "Bibliography" follow-up could expand
  this once specific Fukuyama-group papers are verified by the
  user).
- Not an open-codes comparison study (the table is informative,
  not authoritative; per-code rows hedge for that reason).

## §7. Test / verification

- Build: `make -C docs/sphinx html` should succeed without new
  warnings (currently blocked locally by missing `furo` install,
  but CI handles this — see `.github/workflows/`).
- Manual: render and visually check that the appendix entry
  appears under "Appendix" in the en + ja indexes, that
  `{ref}` cross-links resolve to the right anchors, and that
  the table renders.
- No code changes; no Python / Fortran tests run.

## §8. Pre-push gate

CLAUDE.md requires both reviewers (in-house + Codex) on every
push. For a docs-only PR, pytest is N/A. Reviewer focus:

- Cross-reference resolution (label format correct, target labels
  added).
- Bilingual parity (en and ja pages line up structurally).
- No fabrication: zero new academic citations, zero exact RSS
  numbers, zero unverified comparison-code claims beyond the
  hedged language.
- Wording consistency with the unified glossary at 7699b72c
  (no Auto-stabilising / Extension ideas / Combined patterns).

## §9. Out of scope (deferred)

- Adding specific Fukuyama-group paper citations (separate PR; the
  user must provide verified bibliographic entries).
- Adding ja translations to other chapters' missing en sections
  (e.g. en/mcp.md "Usage scenarios" gap; same scope as the
  applications.md series).
- Sphinx theme (`furo`) install fix in `requirements.txt`
  (orthogonal, separate cleanup).

## §10. Acceptance criteria

1. ✅ `docs/sphinx/modules/tr/en/limitations-and-references.md` exists with all 6 subsections (4 limitations, 2 reference subsections).
2. ✅ ja counterpart exists with structurally-aligned content.
3. ✅ Both `index.md` files include `limitations-and-references` in the Appendix toctree.
4. ✅ `faq.md` (en + ja) has `(faq-singleton)=` label above Q4.
5. ✅ `design.md` (en + ja) has `(reinit-constraints)=` label above Re-init constraints.
6. ✅ All `{ref}` and `{doc}` cross-references resolve.
7. ✅ No specific academic citations or exact RSS / library-image numbers.
8. ✅ Comparison-code rows are hedged ("see upstream documentation" / "documentation: …").
9. ✅ Both reviewers (in-house + Codex) post-implementation report no HIGH findings.
