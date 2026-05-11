# TR Limitations & References Appendix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single bilingual appendix page ("Known limitations & references") to the TR Sphinx chapter, plus stable MyST anchor labels on existing files (faq Q4, design Re-initialisation) so the appendix can cross-reference them without prose-fragility.

**Architecture:** New bilingual file pair `docs/sphinx/modules/tr/{en,ja}/limitations-and-references.md` (~120 lines each), wired into the Appendix toctree of both `index.md` files. Two existing files (`faq.md` Q4, `design.md` Re-init constraints) get MyST `(label)=` anchors so the new appendix can `{ref}` them by stable name.

**Tech Stack:** Sphinx (pinned `<8`) + myst-parser (`<4`) + furo theme. Bilingual ja/en parallel trees. No code or test changes; documentation only.

**Spec:** `docs/superpowers/specs/2026-05-04-tr-limitations-references-design.md` (commit `1b44bcdb`)

**Predecessor pattern:** the 7-module `applications.md` ja → en series (translation commits `494177d8…6c4a2e57`; final wording unification `7699b72c`; tr completed in this session at `169c17a9 + c3d1ce82`).

**PR phases (= 3 logical commit boundaries):**
- **Phase 1 — Commit 1**: MyST anchor labels on existing 4 files (en/ja faq + en/ja design)
- **Phase 2 — Commit 2**: New `limitations-and-references.md` bilingual pair (en + ja)
- **Phase 3 — Commit 3**: toctree wiring in en/ja `index.md`
- **Phase 4 — Pre-push gate**: 2 reviewers in parallel + REVIEW_OK marker + push

**Plan-time risks already resolved (spec §0):**
- Codex HIGH 1 (memory footprint): replaced "RSS bounded by NRMAX/NSMAX" with "exported state buffer only"; no RSS ceiling claim.
- Codex HIGH 2 (libtrapi.so size): claim dropped entirely.
- Codex HIGH 3 (TRANSP URL): switched from unverified `github.com/PrincetonUniversity/transp` to authoritative `https://transp.pppl.gov/`.
- Codex MED 1–3 (overstated TASK row, ASTRA/JETTO unverified, fragile cross-links): hedged language + MyST anchor labels.

---

## Phase 1 — MyST anchor labels

**Goal of phase:** Add stable MyST anchors above the two existing headings the new appendix will cross-reference. Each edit is a single line above an existing `## ...` header. End of phase: existing pages render unchanged at the heading level (the label is invisible HTML), `{ref}` resolution works.

### Task 1.1: Add `(faq-singleton)=` label to en/faq.md

**Files:**
- Modify: `docs/sphinx/modules/tr/en/faq.md` (single line above `## Q4. Can I create two ...`)

- [ ] **Step 1: Read current Q4 heading line and the line above it**

```bash
sed -n '25,30p' docs/sphinx/modules/tr/en/faq.md
```

Expected: shows a blank line then `## Q4. Can I create two \`Trlib()\` instances in the same process?` near line 27.

- [ ] **Step 2: Insert the anchor**

Edit `docs/sphinx/modules/tr/en/faq.md`. Locate the line `## Q4. Can I create two \`Trlib()\` instances in the same process?` and insert immediately above it (and after any preceding blank line):

```markdown
(faq-singleton)=
## Q4. Can I create two `Trlib()` instances in the same process?
```

- [ ] **Step 3: Verify by grep**

```bash
grep -n "(faq-singleton)=" docs/sphinx/modules/tr/en/faq.md
```

Expected: a single line printed showing the label one line above Q4.

### Task 1.2: Add `(faq-singleton)=` label to ja/faq.md

**Files:**
- Modify: `docs/sphinx/modules/tr/ja/faq.md` (mirror of Task 1.1)

- [ ] **Step 1: Read current Q4 heading line**

```bash
sed -n '22,28p' docs/sphinx/modules/tr/ja/faq.md
```

Expected: shows `## Q4. 同じプロセスで 2 個の \`Trlib()\` を作れる?` near line 24.

- [ ] **Step 2: Insert the anchor**

Edit `docs/sphinx/modules/tr/ja/faq.md`. Insert immediately above the Q4 heading:

```markdown
(faq-singleton)=
## Q4. 同じプロセスで 2 個の `Trlib()` を作れる?
```

(The same English label is used in both languages — `{ref}` only resolves to the label, not to a translated heading.)

- [ ] **Step 3: Verify by grep**

```bash
grep -n "(faq-singleton)=" docs/sphinx/modules/tr/ja/faq.md
```

Expected: one match.

### Task 1.3: Add `(reinit-constraints)=` label to en/design.md

**Files:**
- Modify: `docs/sphinx/modules/tr/en/design.md` (single line above `## Re-initialisation constraints`)

- [ ] **Step 1: Read current heading line**

```bash
sed -n '137,142p' docs/sphinx/modules/tr/en/design.md
```

Expected: shows `## Re-initialisation constraints` near line 139.

- [ ] **Step 2: Insert the anchor**

Edit `docs/sphinx/modules/tr/en/design.md`. Insert immediately above the heading:

```markdown
(reinit-constraints)=
## Re-initialisation constraints
```

- [ ] **Step 3: Verify by grep**

```bash
grep -n "(reinit-constraints)=" docs/sphinx/modules/tr/en/design.md
```

Expected: one match.

### Task 1.4: Add `(reinit-constraints)=` label to ja/design.md

**Files:**
- Modify: `docs/sphinx/modules/tr/ja/design.md`

- [ ] **Step 1: Locate the corresponding ja heading**

```bash
grep -nE "^## " docs/sphinx/modules/tr/ja/design.md | head -10
```

Expected: a line ending in something like `再初期化に関する制約` or similar (look for the equivalent of "Re-initialisation constraints").

- [ ] **Step 2: Insert the anchor**

Edit `docs/sphinx/modules/tr/ja/design.md`. Insert immediately above the matched heading line found in Step 1:

```markdown
(reinit-constraints)=
## <existing ja heading exactly as it is>
```

- [ ] **Step 3: Verify by grep**

```bash
grep -n "(reinit-constraints)=" docs/sphinx/modules/tr/ja/design.md
```

Expected: one match.

### Task 1.5: Phase-1 commit

**Files:** none (git only)

- [ ] **Step 1: Stage the 4 modified files**

```bash
git add docs/sphinx/modules/tr/en/faq.md docs/sphinx/modules/tr/ja/faq.md \
        docs/sphinx/modules/tr/en/design.md docs/sphinx/modules/tr/ja/design.md
```

- [ ] **Step 2: Verify the diff is just 4 single-line additions**

```bash
git diff --cached --stat
```

Expected: 4 files changed, 4 insertions, 0 deletions.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs(tr): add MyST anchor labels on faq Q4 and design Re-init

Adds stable MyST labels (faq-singleton)= and (reinit-constraints)=
above two pre-existing headings in the tr Sphinx chapter, so the
new appendix limitations-and-references.md (next commit) can {ref}
them without prose-fragility against future heading edits.

Same English labels are used in both ja and en files because
{ref} resolves to the label, not to a translated heading.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — New bilingual appendix

**Goal of phase:** Create the new file pair with all 6 subsections (4 limitations + 2 references). Cross-references use the labels added in Phase 1. End of phase: both files exist, structurally aligned, no broken cross-refs.

### Task 2.1: Create `docs/sphinx/modules/tr/en/limitations-and-references.md`

**Files:**
- Create: `docs/sphinx/modules/tr/en/limitations-and-references.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/en/limitations-and-references.md` with the following content **verbatim**:

````markdown
# Known limitations and references

```{admonition} What this page covers
:class: note

A summary of what the `tr` library cannot do, plus pointers to
related transport codes and the upstream TASK group. The
limitations listed here are stable contracts of the current
implementation; the reference table summarises public
documentation for context.
```

---

## Known limitations

### Single instance per process

`Trlib` enforces one live instance per process — instantiating a
second `Trlib()` while another is still alive raises
`TrlibError`. The constraint exists because TR uses module-level
COMMON-block state that cannot be safely partitioned. For
parallelism, spawn separate processes (see {doc}`applications`).

For the user-facing details and the underlying weakref guard
(introduced in #171), see {ref}`faq-singleton`.

### Module-level state reset

After `tr_finalize` followed by another `tr_init` in the same
process, parts of the module-level Fortran state are not fully
reset. Tests that re-initialise should isolate by process
(`pytest --forked`) or use `multiprocessing` to spawn a fresh
worker. For details see {ref}`reinit-constraints`.

### Thread safety

`tr` is not thread-safe. Module-level COMMON-block state is
shared by every call to the library in the same process, so
concurrent calls from `threading.Thread` (or any other in-process
threading mechanism) race on that state. For parallel sweeps,
spawn separate processes — `multiprocessing.Pool` is the
recommended pattern, demonstrated by `sweep()` in
{doc}`applications`.

### Compile-time bounds (state buffer)

`TR_MAX_NRMAX = 500` and `TR_MAX_NSMAX = 8`, defined in
`tr/tr_api.h`, bound the dimensions of the **exported**
`tr_state_t` buffer that `tr_get_state` populates — i.e. the
`RN`, `RT`, `AJ`, `QP` arrays in {doc}`state`. They do *not*
bound the total resident set size of a TR process: TRCOMM
allocates many additional internal arrays at run time, and the
dynamically-linked libraries (BPSD, the matrix solver, etc.) add
further memory not captured by these constants. No RSS ceiling
is asserted here — measure for your own deployment if you need
it.

---

## References

### Original TASK publications

The TASK code suite (including `tr`) is developed by Prof.
A. Fukuyama's group (Kyoto University). The upstream sources
are at <https://github.com/ats-fukuyama>. For publications,
consult that group's bibliography directly — this page does not
list specific paper citations.

### Related open transport codes

The table below summarises a few open transport codes alongside
TASK/tr to help orient new users. Non-TASK rows reflect public
documentation as of the page's date; for the authoritative scope
and access policy of each code, consult the linked sources.

| Code | Spatial | Time mode | Heating coverage | Access / URL |
|---|---|---|---|---|
| **TASK/tr** (this) | 1D radial | Predictive (time-evolving) | NB / EC / LH / ICRF source selectors registered via `MDLNB` / `MDLEC` / `MDLLH` / `MDLIC` | Open — <https://github.com/ats-fukuyama> |
| ASTRA | 1.5D | Predictive + interpretive | Modular | Collaboration-based — see upstream documentation |
| JETTO-SANCO | 1D transport + impurity | Predictive + interpretive | NB / EC / ICRH | EUROfusion-restricted — see upstream documentation |
| TRANSP | 1.5D | Interpretive primary; predictive available | NUBEAM, TORAY, etc. | Documentation: <https://transp.pppl.gov/>; source via PPPL collaboration |

The table is informative, not authoritative. For per-code
detail (e.g. specific transport-model libraries supported, exact
heating-module coverage, version histories), follow the linked
sources.
````

- [ ] **Step 2: Verify file exists with the right top-level heading**

```bash
head -1 docs/sphinx/modules/tr/en/limitations-and-references.md
```

Expected: `# Known limitations and references`.

- [ ] **Step 3: Verify all 4 cross-references appear**

```bash
grep -nE "\\{ref\\}|\\{doc\\}" docs/sphinx/modules/tr/en/limitations-and-references.md
```

Expected: 5 matches — `{doc}\`applications\``, `{ref}\`faq-singleton\``, `{ref}\`reinit-constraints\``, `{doc}\`applications\``, `{doc}\`state\``.

### Task 2.2: Create `docs/sphinx/modules/tr/ja/limitations-and-references.md`

**Files:**
- Create: `docs/sphinx/modules/tr/ja/limitations-and-references.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/ja/limitations-and-references.md` with the following content **verbatim**:

````markdown
# 既知の制約と参考資料

```{admonition} このページの位置付け
:class: note

`tr` ライブラリで「できないこと」のまとめと,
関連する輸送コードや上流 TASK グループへのポインタです.
ここに挙げる制約は現実装の安定した契約事項です.
参考資料の表は文脈情報として上流の公開ドキュメントを要約しています.
```

---

## 既知の制約

### プロセスあたり 1 インスタンス

`Trlib` は 1 プロセスにつき 1 つだけインスタンスを許します.
別の `Trlib()` がまだ生きているうちに 2 つ目を作ろうとすると
`TrlibError` を送出します. これは TR が安全に分割できない
モジュールレベル COMMON ブロックを使っているためで, 並列化したい
場合は別プロセスを起動してください ({doc}`applications` 参照).

ユーザ向けの詳細と内部の weakref ガード (#171 で導入) については
{ref}`faq-singleton` を参照してください.

### モジュール状態の再初期化

同一プロセス内で `tr_finalize` の後に `tr_init` をやり直しても,
モジュールレベルの Fortran 状態の一部はリセットされません.
再初期化を伴うテストはプロセス分離 (`pytest --forked`) するか,
`multiprocessing` で worker を新規起動してください.
詳細は {ref}`reinit-constraints` を参照.

### スレッド安全性

`tr` はスレッドセーフではありません. モジュールレベルの COMMON
ブロックを同一プロセス内のすべての呼び出しが共有するため,
`threading.Thread` などプロセス内スレッドからの同時呼び出しは
状態競合を起こします. 並列スイープには別プロセスを使ってください.
{doc}`applications` の `sweep()` で示している
`multiprocessing.Pool` パターンが推奨です.

### コンパイル時上限 (state バッファ)

`tr/tr_api.h` で定義される `TR_MAX_NRMAX = 500`,
`TR_MAX_NSMAX = 8` は **エクスポートされる** `tr_state_t`
バッファの次元 (`tr_get_state` が埋める `RN`, `RT`, `AJ`,
`QP` 配列, {doc}`state` 参照) のみを bound するもので,
TR プロセスの総 resident set size は bound しません.
TRCOMM は実行時に追加の内部配列を allocate し, 動的にリンクされた
ライブラリ (BPSD, 行列ソルバ等) もここに含まれない追加メモリを
使います. 本ページでは RSS の上限を断言しません — 必要なら
自分のデプロイで測定してください.

---

## 参考資料

### TASK の原論文

TASK code suite (`tr` を含む) は京都大学の福山淳教授グループに
よって開発されています. 上流ソースは
<https://github.com/ats-fukuyama> にあります. 出版物については
同グループの bibliography を直接参照してください — 本ページでは
個別の論文 citation を載せていません.

### 関連オープン輸送コード

以下の表は新しいユーザの方向付けのために, TASK/tr とあわせて
いくつかのオープンな輸送コードを要約しています. TASK 以外の行は
ページ作成時点での公開ドキュメントの要約です. 各コードの正式な
範囲とアクセスポリシーについてはリンク先を参照してください.

| Code | Spatial | Time mode | Heating coverage | Access / URL |
|---|---|---|---|---|
| **TASK/tr** (this) | 1D radial | Predictive (time-evolving) | NB / EC / LH / ICRF source selectors registered via `MDLNB` / `MDLEC` / `MDLLH` / `MDLIC` | Open — <https://github.com/ats-fukuyama> |
| ASTRA | 1.5D | Predictive + interpretive | Modular | Collaboration-based — see upstream documentation |
| JETTO-SANCO | 1D transport + impurity | Predictive + interpretive | NB / EC / ICRH | EUROfusion-restricted — see upstream documentation |
| TRANSP | 1.5D | Interpretive primary; predictive available | NUBEAM, TORAY, etc. | Documentation: <https://transp.pppl.gov/>; source via PPPL collaboration |

この表は参考情報であり, 権威的な技術評価ではありません.
コードごとの詳細 (対応する個別の輸送モデルライブラリ, 加熱モジュール
の正確なカバレッジ, バージョン履歴等) については, リンク先のソースを
追ってください.
````

- [ ] **Step 2: Verify file exists with the right top-level heading**

```bash
head -1 docs/sphinx/modules/tr/ja/limitations-and-references.md
```

Expected: `# 既知の制約と参考資料`.

- [ ] **Step 3: Verify all 4 cross-references appear**

```bash
grep -nE "\\{ref\\}|\\{doc\\}" docs/sphinx/modules/tr/ja/limitations-and-references.md
```

Expected: 5 matches identical in label to en (the labels are language-independent).

- [ ] **Step 4: Verify structural parity**

```bash
diff <(grep -E "^#" docs/sphinx/modules/tr/en/limitations-and-references.md) \
     <(grep -E "^#" docs/sphinx/modules/tr/ja/limitations-and-references.md) | head
```

Expected: differences only in heading text (en vs ja). The number of `#`-prefixed lines must match exactly (12 each: 1 H1 + 2 H2 + 6 H3 + 3 separators are not headings; recount: 1 H1 "Known limitations and references" + 2 H2 ("Known limitations", "References") + 6 H3 (4 limit + 2 ref subsections) = 9 total `#`-prefixed lines).

### Task 2.3: Phase-2 commit

**Files:** none (git only)

- [ ] **Step 1: Stage the 2 new files**

```bash
git add docs/sphinx/modules/tr/en/limitations-and-references.md \
        docs/sphinx/modules/tr/ja/limitations-and-references.md
```

- [ ] **Step 2: Verify the diff is 2 new files**

```bash
git diff --cached --stat
```

Expected: 2 files changed, ~190 insertions (95 each), 0 deletions.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs(tr): add limitations-and-references appendix (en + ja)

Adds the bilingual appendix page covering 4 known limitations and
2 reference subsections, sized at 0.5 session per the deepening
menu in project_tr_proper_manual.md.

Limitations:
- Single instance per process (cross-link {ref}\`faq-singleton\`)
- Module-level state reset (cross-link {ref}\`reinit-constraints\`)
- Thread safety (new content)
- Compile-time bounds on the exported tr_state_t buffer (new
  content; explicitly hedged against fabricating an RSS ceiling
  per Codex review HIGH 1)

References:
- Generic pointer to Prof. A. Fukuyama's group at
  github.com/ats-fukuyama (no specific paper citations to avoid
  fabrication)
- 4-code comparison table (TASK/tr / ASTRA / JETTO-SANCO /
  TRANSP) with hedged language and per-row pointer-shaped
  access claims (per Codex review HIGH 3 + MED 1-2). TRANSP URL
  uses authoritative transp.pppl.gov.

ja and en written in parallel; structurally aligned. The
toctree wiring lands in the next commit.

Spec: docs/superpowers/specs/2026-05-04-tr-limitations-references-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 3 — toctree wiring

**Goal of phase:** Add the new appendix to both `index.md` Appendix toctrees so the page is discoverable in the rendered chapter. End of phase: en and ja indexes both list `limitations-and-references` after `appendix-sensitivity`.

### Task 3.1: Update en/index.md

**Files:**
- Modify: `docs/sphinx/modules/tr/en/index.md` (Appendix toctree, ~line 67–72)

- [ ] **Step 1: Read the current Appendix toctree**

```bash
sed -n '65,73p' docs/sphinx/modules/tr/en/index.md
```

Expected:

```markdown
## Appendix

```{toctree}
:maxdepth: 1

appendix-mdlkai
appendix-sensitivity
```
```

- [ ] **Step 2: Insert the new entry**

Edit `docs/sphinx/modules/tr/en/index.md`. Locate the line `appendix-sensitivity` and append `limitations-and-references` on the line below, before the closing triple-backtick:

```markdown
appendix-mdlkai
appendix-sensitivity
limitations-and-references
```

- [ ] **Step 3: Verify**

```bash
grep -n "limitations-and-references" docs/sphinx/modules/tr/en/index.md
```

Expected: one match in the Appendix toctree block.

### Task 3.2: Update ja/index.md

**Files:**
- Modify: `docs/sphinx/modules/tr/ja/index.md` (mirror of Task 3.1)

- [ ] **Step 1: Read the current Appendix toctree**

```bash
sed -n '65,75p' docs/sphinx/modules/tr/ja/index.md
```

Expected: similar block to en — `appendix-mdlkai` and `appendix-sensitivity` listed under the `付録` heading's toctree.

- [ ] **Step 2: Insert the new entry**

Edit `docs/sphinx/modules/tr/ja/index.md`. Append `limitations-and-references` below `appendix-sensitivity` in the same toctree block:

```markdown
appendix-mdlkai
appendix-sensitivity
limitations-and-references
```

- [ ] **Step 3: Verify**

```bash
grep -n "limitations-and-references" docs/sphinx/modules/tr/ja/index.md
```

Expected: one match.

### Task 3.3: Local sanity (cross-link verification skipping `make html`)

**Files:** none (verification)

`make html` is currently blocked locally because the Sphinx theme `furo` is missing from this Python environment (and from `requirements.txt`; an orthogonal cleanup item per spec §9). CI builds the docs so the broken-ref check still happens at push time. Locally we settle for the file-existence and grep checks below.

- [ ] **Step 1: Verify all 4 cross-link targets exist**

```bash
for f in \
  docs/sphinx/modules/tr/en/applications.md \
  docs/sphinx/modules/tr/ja/applications.md \
  docs/sphinx/modules/tr/en/state.md \
  docs/sphinx/modules/tr/ja/state.md; do
    test -f "$f" && echo "OK: $f"
done
```

Expected: 4 lines, all `OK: ...`.

- [ ] **Step 2: Verify both `{ref}` labels resolve**

```bash
for label in faq-singleton reinit-constraints; do
  echo "=== ${label} ==="
  grep -rn "(${label})=" docs/sphinx/modules/tr/
done
```

Expected: each label appears in 2 files (en + ja).

- [ ] **Step 3: Verify the appendix toctree mentions the new entry in both indexes**

```bash
grep -rn "limitations-and-references$" docs/sphinx/modules/tr/
```

Expected: 4 matches: 2 toctree entries (one per index) + 2 self-references via the file headers' top-of-file paths if any.

(The matches will actually be: 1 in en/index.md, 1 in ja/index.md, plus matches in the new file pair if `limitations-and-references` appears as an end-of-line word elsewhere — adjust expectation to "at least 2 toctree entries" if the regex over-matches.)

### Task 3.4: Phase-3 commit

**Files:** none (git only)

- [ ] **Step 1: Stage the 2 modified indexes**

```bash
git add docs/sphinx/modules/tr/en/index.md docs/sphinx/modules/tr/ja/index.md
```

- [ ] **Step 2: Verify diff**

```bash
git diff --cached --stat
```

Expected: 2 files changed, 2 insertions, 0 deletions.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs(tr): wire limitations-and-references into Appendix toctree

Adds the new bilingual appendix page (commit \$PHASE2_SHA) under
the existing 'Appendix' section of both index.md files,
positioned after appendix-sensitivity for parity with the
existing appendix-mdlkai / appendix-sensitivity ordering.

This is the third and final commit of the limitations &
references appendix work; spec acceptance criteria 1-8 are
satisfied at this point. AC9 (no HIGH from either reviewer)
is checked by the Phase 4 pre-push gate.

Spec: docs/superpowers/specs/2026-05-04-tr-limitations-references-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

(Replace `\$PHASE2_SHA` with the actual short SHA of the Phase-2 commit if you want a proper cross-reference; otherwise the literal text above is acceptable.)

---

## Phase 4 — Pre-push gate

**Goal of phase:** CLAUDE.md non-negotiable: 2 reviewer agents in parallel, REVIEW_OK marker, push. pytest is N/A (no Fortran / Python code changed).

### Task 4.1: Launch 2 reviewer agents in parallel

**Files:** none (Agent calls)

- [ ] **Step 1: Run the in-house reviewer**

In a single message, dispatch both agents:

```
Agent(subagent_type="superpowers:code-reviewer", prompt="""
Review the diff in /Users/k-yoshimi/Dropbox/cursor/task on branch
chore/pre-push-hook-worktree-compat. Run:

    git log --oneline 1b44bcdb..HEAD
    git diff 1b44bcdb..HEAD

to see the 3 commits implementing the tr limitations &
references appendix per spec
docs/superpowers/specs/2026-05-04-tr-limitations-references-design.md.

Three logical commits:

1. MyST anchor labels on faq Q4 + design Re-init (4 single-line
   additions across en + ja).
2. New bilingual appendix file pair (~190 lines total).
3. Appendix toctree wiring in en/ja index.md (1 line each).

Focus on:
- Cross-reference correctness (4 labels, MyST {ref} / {doc}
  syntax, label uniqueness within the chapter).
- Bilingual structural parity (en and ja H1/H2/H3 line up).
- No fabrication: NO specific Fukuyama-group paper citations,
  NO exact RSS or library-image numbers, NO unverified
  comparison-code claims beyond the explicitly-hedged language.
- Wording consistency with the unified glossary at 7699b72c.
- Does the table render in MyST (pipe-table syntax,
  bracket-vs-paren conventions)?
- TRANSP URL is transp.pppl.gov (not the unverified github URL
  that Codex flagged at design time).

Report HIGH / MED / LOW in <400 words. Spec acceptance criteria
are at the bottom of the spec doc — verify each.
""")

Agent(subagent_type="codex:codex-rescue", prompt="""
Independent review of the same diff (git diff 1b44bcdb..HEAD).
Background: spec went through a Codex design-stage review which
addressed 3 HIGH findings (memory-footprint claim rewrite, libtrapi
size claim drop, TRANSP URL switch to transp.pppl.gov) and 3 MEDIUM
findings (TASK/tr row wording, ASTRA/JETTO hedge, MyST anchor
labels).

Verify the implementation matches the design's Codex-review
resolutions. Anchor on:
- Were the 3 HIGH design-stage fixes actually implemented in the
  prose? (The state-buffer paragraph correctly limits the claim;
  no library-image numbers; TRANSP row uses transp.pppl.gov.)
- Are the comparison-table rows for ASTRA/JETTO-SANCO still
  hedged (\"see upstream documentation\")?
- Cross-cutting docs review: any obvious factual errors about
  the upstream codes' scope or access policy?
- Bilingual diff: does the ja translation preserve the same
  hedging discipline as en?

Report HIGH / MED / LOW in <400 words.
""")
```

Both Agent calls fire in the same message for parallel execution.

- [ ] **Step 2: Address findings**

For each HIGH finding, make a fix commit on top of Commit 3 (do NOT amend; CLAUDE.md says always create new commits). Re-run the cross-link / structural-parity grep checks. If diff is significant, re-run reviewers on the cumulative diff.

For MEDIUM findings, decide per-finding: address in a follow-up commit if the fix is small and clearly reduces risk; document in the PR description otherwise.

LOW findings are typically optional polish — fix opportunistically, no blocker.

### Task 4.2: REVIEW_OK marker + push

**Files:** none

- [ ] **Step 1: Mark current HEAD as reviewed**

```bash
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
ls "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
```

Expected: marker file exists for HEAD SHA.

- [ ] **Step 2: Push to origin**

```bash
git push 2>&1 | tail -5
```

Expected: `pre-push: review marker present — OK`. Push succeeds.

If pre-push hook complains about marker missing, re-do Step 1 (the SHA may have changed via a fix commit).

The chore branch is the workflow's integration target for this docs work — no separate PR is needed for this small docs delta (mirrors the recent translation series at `494177d8…6c4a2e57`, none of which went through a separate PR).

---

## Spec coverage check

| Spec section | Implementation task |
|---|---|
| §1 Overview | All tasks (cumulative) |
| §2 File structure (4 modified, 2 new) | Tasks 1.1–1.4, 2.1–2.2, 3.1–3.2 |
| §3.1 Limitations subsections (4) | Task 2.1 + 2.2 (content embedded verbatim) |
| §3.2 References + comparison table | Task 2.1 + 2.2 (content embedded verbatim) |
| §4 Bilingual structure parity | Tasks 2.1 step 4 (diff check) |
| §5 MyST anchor mechanics | Tasks 1.1–1.4 |
| §6 Out-of-scope reaffirmation | embedded in Task 2.1/2.2 prose ("does not list specific paper citations" etc.) |
| §7 Test / verification | Task 3.3 (file existence + grep checks; sphinx-build deferred to CI) |
| §8 Pre-push gate | Task 4.1, 4.2 |
| §9 Out-of-scope deferrals | n/a (deferred items mentioned in commit messages and spec) |
| §10 Acceptance criteria | AC1-2 (Tasks 2.1, 2.2), AC3 (Tasks 3.1, 3.2), AC4-5 (Tasks 1.1-1.4), AC6 (Task 3.3), AC7-8 (Task 2.1/2.2 verbatim content), AC9 (Task 4.1) |

All spec sections are implemented in this plan. ✓

---

## Notes for the executor

- **Frequent commits**: the plan uses 3 commit boundaries that mirror the spec's natural decomposition (labels → content → toctree). No squashing of these into 1 commit before push — the chore branch's recent history (`7699b72c` etc.) shows individual commits as the established style for docs work.
- **No source-code changes**: this PR touches only `.md` files. pytest is N/A; the pre-push hook does not gate docs commits on test results.
- **Cross-link gotcha**: MyST `{ref}` resolves by label string, not by language; both ja and en files use the same `(faq-singleton)=` and `(reinit-constraints)=` labels. This is the correct convention in this repo (verified against existing labels in the chapter).
- **`make html` is blocked locally**: Sphinx theme `furo` is missing from `requirements.txt`. CI builds the docs cleanly. Local verification is by grep + file-existence checks (Task 3.3); broken-ref detection happens at push time.
- **Reviewer agent fallback**: if `superpowers:code-reviewer` is unavailable in the executor's environment, substitute `feature-dev:code-reviewer`. The two are interchangeable for the in-house review role.
- **No PR**: this lands directly on `chore/pre-push-hook-worktree-compat` (the workflow's integration target for ongoing docs and feature work). Mirrors the established translation-series pattern (`494177d8…6c4a2e57`).
