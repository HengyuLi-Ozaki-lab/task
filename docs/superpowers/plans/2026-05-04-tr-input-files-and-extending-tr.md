# TR Input-files + Extending-TR Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add **two** bilingual pages to the TR Sphinx chapter — `input-files.md` (User guide entry, after `parameter-setting`) covering eqdata / ufiles / paths, and `extending-tr.md` (Internals entry, after `design`) covering the maintainer walkthroughs for adding a parameter, a transport model, or a `TrState` field.

**Architecture:** Two new bilingual file pairs in `docs/sphinx/modules/tr/{en,ja}/`. Toctree updates in both `index.md` files. No new MyST anchor labels; outgoing cross-links target existing pages. Each prose section anchored on file:line citations from `tr/*.f90`, `tr/*.h`, `python/trlib/*.py`, `eq/*.f90` — all verified across 3 Codex design-stage review rounds.

**Tech Stack:** Sphinx (pinned `<8`) + myst-parser (`<4`) + furo theme. Bilingual ja/en parallel trees. No code or test changes.

**Spec:** `docs/superpowers/specs/2026-05-04-tr-input-files-and-extending-tr-design.md` (latest commit `63a13325`, after 3 Codex review rounds).

**Predecessor pattern:** G + E + A appendix work earlier today (commits `a8b83311`, `fc74599d`, `c5210076`). Same chapter conventions, same pre-push gate, same bilingual discipline.

**PR phases (= 3 logical commit boundaries):**
- **Phase 1 — Commit 1**: New `input-files.md` bilingual pair.
- **Phase 2 — Commit 2**: New `extending-tr.md` bilingual pair.
- **Phase 3 — Commit 3**: Toctree wiring in en/ja `index.md` (input-files in User guide after `parameter-setting`; extending-tr in Internals after `design`).
- **Phase 4 — Pre-push gate**: 2 reviewers in parallel + REVIEW_OK marker + push.

**Plan-time risks already resolved (3 Codex review rounds, see spec ACs 7-13):**
- Round-1 HIGH 1: MODELG set `{3,5,7,8}` → `{3,5,8,9}`.
- Round-1 HIGH 2: KUFDIR/KUFDEV/KUFDCG namelist-only restriction.
- Round-1 HIGH 7: TrState walkthrough 7 → 8 steps; line ranges fixed; SCALAR_FIELDS mechanism added.
- Round-1 MED 4: 80-byte path-limit citation expanded.
- Round-1 MED 10: 2-D array-order trap warning added.
- Round-2 HIGH 1: MODELG=9 dispatches to EQRTSK (not a TR-side alias).
- Round-2 MED 1/2: tr_api.f90 loop range, NUL fabrication.
- Round-2 LOW 1 + Round-3 LOW 1: state.py parser line ranges.

---

## Phase 1 — `input-files.md` bilingual pair

**Goal of phase:** Create the User-guide reference page describing eqdata / ufiles / paths.

### Task 1.1: Create `docs/sphinx/modules/tr/en/input-files.md`

**Files:**
- Create: `docs/sphinx/modules/tr/en/input-files.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/en/input-files.md` with the following content **verbatim**:

````markdown
# Input files

```{admonition} What this page covers
:class: note

A map of the supporting data files that TR can consume —
eqdata files (EQDSK and friends), ufiles (experimental
profile data), and the path / placement constraints. The
canonical formats are documented elsewhere; this page just
points at where TR reads them and what flags control the
reading.
```

---

## eqdata files (EQDSK and friends)

`MODELG ∈ {3, 5, 8, 9}` triggers TR's BPSD-side equilibrium
pull (`tr/trbpsd.f90:213`). All four values also drive an
actual external load on the `eq` side, but via different
loader routines:

- `MODELG = 3` or `MODELG = 9` → `EQRTSK` (TASK/EQ binary
  format)
- `MODELG = 5` → `EQDSKR` (community EQDSK format)
- `MODELG = 8` → `EQJAEAR`

The dispatch table lives at `eq/eqfile.f90:108-115`. So
`MODELG = 9` is not a no-op alias — it actually loads via
the same `EQRTSK` reader as `MODELG = 3`.

The path is set via `KNAMEQ` (string parameter); see
{doc}`parameter-setting` for how to set string params from
Python. The file is read on the `eq` side; `tr` only pulls
the resulting equilibrium / metric data via the BPSD
broker (`tr/trbpsd.f90:213-245` — the geometry-aware pull
is conditional on `MODELG`).

The canonical EQDSK format documentation lives in the `eq`
chapter and external sources (EQDSK is a community format
predating TASK). This page does NOT redocument the format
itself.

A working example file ships under
`test_run/test_output/tot_demo2014_short/eqdata.demo2014`,
the demo2014 baseline used by the Layer 1 equivalence
tests.

---

## ufiles (`MDLUF`)

A "ufile" is a community format for time-series experimental
profile data — density, temperature, q-profile snapshots,
etc. TR can ingest these to drive interpretive runs.

Reading is controlled by `MDLUF` (default `0` — OFF; set
to non-zero to enable). The default is verified at
`tr/trinit.f90:641-648`. `MDLUF` is exposed in
`tr/tr_param_registry.f90` and can be set from
`tr.set_param("MDLUF", ...)` at runtime.

**The directory parameters `KUFDIR` / `KUFDEV` / `KUFDCG`
are namelist-only.** They appear in the legacy `&trn`
namelist input at `tr/trparm.f90:108-112`, but they are
NOT exposed in `tr/tr_param_registry.f90` (the registry
has a "future additions" comment at
`tr/tr_param_registry.f90:184-186`). Setting them via
`tr.set_param_str` will fail. Users who need to point TR
at a non-default ufile directory must either:

- run from the legacy namelist-driven `tr2` driver, or
- set up the directory via Fortran-side defaults / source
  edit until these get added to the registry.

The reader chain is:

- `tr/trufile.f90:70-77` — dispatch stub, picks one of
  the next-level routines based on `MDLUF` and the
  scenario kind.
- `tr/tr_ufile_task.f90:7` — `TR_TIME_UFILE` /
  `TR_STEADY_UFILE` entry points.
- `tr/tr_ufile_topics.f90:7` — `TR_TIME_UFILE_TOPICS`
  per-topic decoders.

For most users running prescribed-profile or analytic-
geometry scenarios, ufiles are NOT needed — the default
`MDLUF = 0` is correct. The entry exists to point readers
at the chain when they encounter a research workflow that
does need experimental input.

---

## `trmodels/` and other model-side data

Some transport models embed lookup tables or coefficient
data (e.g. NCLASS-style modules). The codebase carries
these inline in the source rather than as separate runtime
files: `tr/trmodels.f90` calls compiled-in driver routines
(`mbgb_driver`, `mmm95_driver`, `mmm71_driver`) directly,
with no `OPEN` / `READ` from a runtime model-side
directory.

In practice this means **runtime external data is currently
limited to eqdata + ufiles only**. There is no
`trmodels/`-style runtime directory the library reads at
start-up.

---

## File placement and path constraints

The `eq` C-string interface caps `KNAMEQ` (and similar
string parameters) at 80 bytes. The constant is defined at
`python/eqlib/eqlib.py:39-41`, and the actual length
rejection (`EqlibInvalidParamError` when
`len(encoded) > max_bytes`) is at `:66-70`. The Fortran side
reads into `CHARACTER(LEN=80)`. The docstring at `:47-50`
says "up to 79 bytes" — this is stale; Python permits the
full 80. Treat the limit as **byte** rather than
"character" because the limit applies to encoded bytes,
not codepoints.

Recommended pattern: `chdir` to a working directory that
holds the eqdata file(s) and pass the bare filename. This
is what the existing `python/totlib/tests/test_pipeline_*`
files do.

Absolute paths longer than 80 bytes will fail at
parameter-set time, before `run()` is called; users will
see the error immediately rather than at run time.

---

## See also

- {doc}`parameter-setting` — how to set string parameters
  via the Python `set_param_str` interface.
- {doc}`limitations-and-references` — comparison with other
  open transport codes that consume similar files.
- {doc}`design` — the BPSD broker plumbing TR uses to
  receive `eq`'s output.
- {doc}`numerical-stability-and-diagnostics` — what to
  check at runtime when an eqdata load behaves unexpectedly.
````

- [ ] **Step 2: Verify file exists**

```bash
head -1 docs/sphinx/modules/tr/en/input-files.md
```

Expected: `# Input files`.

- [ ] **Step 3: Verify cross-references**

```bash
grep -nE '\{doc\}' docs/sphinx/modules/tr/en/input-files.md
```

Expected: at least 4 matches — `{doc}\`parameter-setting\``, `{doc}\`limitations-and-references\``, `{doc}\`design\``, `{doc}\`numerical-stability-and-diagnostics\``.

### Task 1.2: Create `docs/sphinx/modules/tr/ja/input-files.md`

**Files:**
- Create: `docs/sphinx/modules/tr/ja/input-files.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/ja/input-files.md` with the following content **verbatim**:

````markdown
# 入力ファイル

```{admonition} このページの位置付け
:class: note

TR が読み込み得る支援データファイルの地図です — eqdata
(EQDSK 系), ufile (実験プロファイルデータ), およびファイル
配置・パスの制約. canonical な format 仕様は別所に存在し,
本ページは TR がどのフラグでどのファイルを読むかだけを
点で示します.
```

---

## eqdata ファイル (EQDSK 系)

`MODELG ∈ {3, 5, 8, 9}` で TR の BPSD 経由 equilibrium
pull が走ります (`tr/trbpsd.f90:213`). この 4 値はすべて
`eq` 側でも実際に外部 load を駆動しますが, 値ごとに loader
ルーチンが異なります:

- `MODELG = 3` または `MODELG = 9` → `EQRTSK`
  (TASK/EQ バイナリ形式)
- `MODELG = 5` → `EQDSKR` (community EQDSK 形式)
- `MODELG = 8` → `EQJAEAR`

dispatch テーブルは `eq/eqfile.f90:108-115` にあります.
つまり `MODELG = 9` は no-op alias ではなく, `MODELG = 3`
と同じ `EQRTSK` reader を実際に呼びます.

パスは `KNAMEQ` (文字列パラメータ) で指定します. Python
からの設定方法は {doc}`parameter-setting` 参照. ファイル
自体は `eq` 側で読まれ, `tr` は結果の equilibrium / metric
を BPSD broker 経由で pull するだけです (`tr/trbpsd.f90:213-245`
— geometry-aware な pull は `MODELG` で条件分岐).

EQDSK format 自体の canonical な仕様は `eq` chapter および
外部資料 (EQDSK は TASK よりも前から存在する community 形式)
を参照してください. 本ページではフォーマットを再記述しません.

動作する例ファイルは
`test_run/test_output/tot_demo2014_short/eqdata.demo2014`
にあり, Layer 1 equivalence test のベースラインに使われて
います.

---

## ufile (`MDLUF`)

「ufile」は実験プロファイル時系列データ (密度・温度・q
プロファイル等のスナップショット) の community 形式です.
TR は interpretive run の駆動入力として ufile を取り込めます.

読み込みは `MDLUF` で制御 (default `0` = OFF; 非ゼロで
有効化). default の確認は `tr/trinit.f90:641-648`.
`MDLUF` は `tr/tr_param_registry.f90` に登録されており,
`tr.set_param("MDLUF", ...)` で実行時に設定できます.

**ディレクトリパラメータ `KUFDIR` / `KUFDEV` / `KUFDCG`
は namelist 専用です.** legacy `&trn` namelist 入力
(`tr/trparm.f90:108-112`) には登場しますが,
`tr/tr_param_registry.f90` には登録されておらず (registry
側の "future additions" コメントは `:184-186`),
`tr.set_param_str` 経由では設定できません. ufile dir を
変えたいユーザは:

- legacy の namelist 駆動 `tr2` driver から実行する, あるいは
- これらが registry に登録されるまで, Fortran 側
  デフォルト / ソース編集で対処する

reader chain:

- `tr/trufile.f90:70-77` — dispatch stub, `MDLUF` と
  シナリオ種別から下位ルーチンを選択.
- `tr/tr_ufile_task.f90:7` — `TR_TIME_UFILE` /
  `TR_STEADY_UFILE` のエントリポイント.
- `tr/tr_ufile_topics.f90:7` — `TR_TIME_UFILE_TOPICS` の
  topic 別デコーダ.

prescribed profile や analytic geometry のシナリオを走らせる
大半のユーザにとって ufile は不要 — default の
`MDLUF = 0` のままで OK です. このエントリは, 実験データ
入力が必要な研究ワークフローで読者が出会ったときの入口
として置いてあります.

---

## `trmodels/` その他のモデル側データ

一部の輸送モデルは lookup table や係数データを埋め込んで
います (NCLASS 系等). codebase ではこれらを別 runtime
ファイルではなくソース内に持っており: `tr/trmodels.f90` が
コンパイル済の driver ルーチン (`mbgb_driver`,
`mmm95_driver`, `mmm71_driver`) を直接呼び出し, runtime な
モデル側ディレクトリからは `OPEN` / `READ` していません.

実用的に: **runtime の外部データは現在 eqdata + ufile に
限られます**. ライブラリが起動時に読む `trmodels/` 系の
runtime ディレクトリは存在しません.

---

## ファイル配置とパスの制約

`eq` の C 文字列インタフェースは `KNAMEQ` (および類似の
文字列パラメータ) を 80 byte で cap します. 定数は
`python/eqlib/eqlib.py:39-41` で定義され, 長さ拒否
(`EqlibInvalidParamError`, `len(encoded) > max_bytes`) は
`:66-70`. Fortran 側は `CHARACTER(LEN=80)` で受けます.
docstring の `:47-50` には "up to 79 bytes" とありますが
これは stale で, Python は 80 byte をすべて受け付けます.
制約は **byte** (codepoint ではなく encoded バイト) で
扱ってください.

推奨パターン: eqdata ファイルが置いてある作業ディレクトリ
に `chdir` して bare filename を渡す. 既存の
`python/totlib/tests/test_pipeline_*` ファイルがこのパターン
を使っています.

80 byte を超える絶対パスはパラメータ設定時に失敗し
(`run()` 呼び出し前), runtime ではなく即座にエラーが見えます.

---

## 関連項目

- {doc}`parameter-setting` — Python `set_param_str` 経由
  の文字列パラメータ設定方法.
- {doc}`limitations-and-references` — 類似ファイルを消費
  する他のオープン輸送コードとの比較.
- {doc}`design` — `eq` 出力を受け取るための TR 側 BPSD
  broker の配管.
- {doc}`numerical-stability-and-diagnostics` — eqdata
  load が予期しない挙動を見せたときに走行時に何を見るか.
````

- [ ] **Step 2: Verify file exists**

```bash
head -1 docs/sphinx/modules/tr/ja/input-files.md
```

Expected: `# 入力ファイル`.

- [ ] **Step 3: Verify cross-references**

```bash
grep -nE '\{doc\}' docs/sphinx/modules/tr/ja/input-files.md
```

Expected: same labels as en (4 cross-refs).

- [ ] **Step 4: Verify structural parity (heading hierarchy)**

```bash
diff <(grep -E '^#' docs/sphinx/modules/tr/en/input-files.md | sed 's/[^#].*//') \
     <(grep -E '^#' docs/sphinx/modules/tr/ja/input-files.md | sed 's/[^#].*//')
```

Expected: empty output (heading depth identical between en and ja).

### Task 1.3: Phase-1 commit

**Files:** none (git only)

- [ ] **Step 1: Stage the 2 new files**

```bash
git add docs/sphinx/modules/tr/en/input-files.md \
        docs/sphinx/modules/tr/ja/input-files.md
```

- [ ] **Step 2: Verify diff**

```bash
git diff --cached --stat
```

Expected: 2 files changed; insertion count roughly 270 + 270.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs(tr): add input-files page (en + ja)

User-guide reference for the supporting data files that TR
consumes -- eqdata (MODELG-driven dispatch via EQRTSK /
EQDSKR / EQJAEAR per eq/eqfile.f90:108-115), ufiles
(MDLUF + namelist-only KUFDIR/KUFDEV/KUFDCG distinction),
the no-trmodels/-runtime-directory clarification, and the
80-byte KNAMEQ path limit (eqlib.py:39-41,66-70).

Each load-bearing claim has a tr/* / eq/* / python/eqlib/*
file:line citation verified across 3 Codex design-stage
review rounds.

Pairs with extending-tr.md (next commit) to close out item
F in the deepening menu.

Spec: docs/superpowers/specs/2026-05-04-tr-input-files-and-extending-tr-design.md (63a13325)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — `extending-tr.md` bilingual pair

**Goal of phase:** Create the maintainer-facing Internals page covering 3 walkthroughs (param / MDLKAI / TrState).

### Task 2.1: Create `docs/sphinx/modules/tr/en/extending-tr.md`

**Files:**
- Create: `docs/sphinx/modules/tr/en/extending-tr.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/en/extending-tr.md` with the following content **verbatim**:

````markdown
# Extending TR

```{admonition} Audience
:class: note

This page is **maintainer-facing**. The reader has the
source tree checked out and is comfortable editing Fortran
and rebuilding `libtrapi.so`. Three concrete walkthroughs
follow — adding a scalar parameter, adding a transport-
model selector under `MDLKAI`, and adding a `TrState`
field. Each is a recipe, not a derivation.
```

---

## Walkthrough A — Add a new scalar parameter

The TR parameter registry uses a hand-written `SELECT CASE`
dispatch in `tr/tr_param_registry.f90:76+`. Adding a
parameter `FOO` is one new `CASE` line in that dispatch
plus a default in `tr/trinit.f90`.

**Recipe (5 steps):**

1. **Declare the variable.** If the parameter is new (not
   already in TRCOMM), declare it in the appropriate
   `tr/trcomm*.f90` module alongside similar parameters.
   If it already exists, skip this step.
2. **Add the registry case.** Add a line like
   `CASE ("FOO"); FOO = value` in the
   `SELECT CASE (TRIM(b))` block that starts at
   `tr/tr_param_registry.f90:76`. Place it near similar
   parameters to preserve the per-section grouping
   convention.
3. **Set a default.** Add `FOO = ...` to `tr/trinit.f90`
   alongside other initialisation.
4. **Rebuild.** `make -C tr libtrapi.so`.
5. **Use from Python.** `tr.set_param("FOO", x)` works
   immediately. No C ABI change is needed because
   `tr_set_param` is string-keyed (verified at
   `tr/tr_api.f90:124-128,136-148`).

For array-valued parameters, the bounds-checked idiom at
`tr/tr_param_registry.f90:101-106` is the template. The
existing `PA[i]` / `PN[i]` / `PNS[i]` / `PT[i]` cases
show the pattern: each `CASE` checks `idx` against
`SIZE(...)` and either assigns or sets `ierr = 1`.

---

## Walkthrough B — Add a new transport model under `MDLKAI`

Turbulent heat-transport coefficients are dispatched via
`SELECT CASE(MDLKAI)` at
`tr/trcoef_turbulence.f90:400`. (The earlier `select case`
at line 64 handles graph-label assignment, NOT the actual
coefficient computation.) Each `MDLKAI` value invokes a
different model.

The numbering convention (per the source-side comments at
`tr/trcoef_turbulence.f90:392-398`):

- `MDLKAI < 10` — constant-coefficient toy models.
- `10 ≤ MDLKAI < 20` — drift-wave (+ITG / +ETG) models.
- `20 ≤ MDLKAI < 30` — Rebu-Lalla family.
- `30 ≤ MDLKAI < 40` — current-diffusivity-driven (CDBM)
  family.
- `40 ≤ MDLKAI < 60` — drift-wave-ballooning models.
- `MDLKAI ≥ 60` — ITG / TEM / ETG model families.

**Recipe (4 steps):**

1. **Pick a `MDLKAI` value** in the appropriate range,
   choosing the next free integer if you are adding
   alongside existing models.
2. **Add a `CASE (N)` block** in
   `tr/trcoef_turbulence.f90` after line 400. The block
   should fill the appropriate transport-coefficient
   arrays — `AKDW` (heat anomalous), `ADDW` (particle
   anomalous), `AVK` (heat pinch / convective).
3. **Add auxiliary loaders if needed.** If the model
   needs auxiliary data (lookup tables, additional
   parameter validation), follow the existing per-family
   file split — adjacent `trcoef_*.f90` files (e.g.
   `tr/trcoef_neoclassical.f90`,
   `tr/trcoef_resistivity.f90`) are templates.
4. **Update {doc}`appendix-mdlkai`** so users can find
   your new case in the catalogue.

The same dispatch pattern applies to the other selector
axes — `MDLAD` (particle diffusion), `MDLAVK` (thermal
pinch), `MDLETA` (resistivity) — in their respective
`trcoef_*.f90` files. The recipe generalises.

---

## Walkthrough C — Add a new `TrState` field (ABI-impact recipe)

This is the most invasive walkthrough. Adding a field to
`tr_state_t` changes the C ABI, so external binary
consumers may need to be rebuilt or version-checked.

**Recipe (8 steps):**

1. **Compute the quantity.** If the value is not already
   in TRCOMM, add a TRCOMM variable in the appropriate
   `tr/trcomm*.f90` module and assign it in the routine
   where it naturally falls. A new derived diagnostic
   typically goes into `tr/trrslt_globals.f90` or
   `tr/trrslt_print.f90`.
2. **Add the C-side field** in the `tr_state_c` derived
   type at `tr/tr_state.f90:43-67`. Append the
   `REAL(C_DOUBLE)` (or appropriate kind) at the **end**
   of the type so existing field offsets stay stable —
   this minimises the breakage surface for binary
   consumers.
3. **Mirror in `tr/tr_api.h:49-60`** as a matching
   `double` (or correct C type), again at the struct end.
4. **Populate the field inside `tr_api_get_state`.** Three
   blocks exist in `tr/tr_api.f90`:
   - **Zero-init** at `:263-283` (the new field should be
     added there too if it has no sensible compute-time-
     zero baseline).
   - **Scalar copy** at `:299-315` — the AJRFT precedent
     lives here. For a new scalar, follow that pattern.
   - **Per-radius / per-species profile loops** at
     `:321-330` — for a new array field, follow the
     `RN` / `RT` / `AJ` / `QP` loop pattern.
5. **Bump `TR_STATE_ABI_VERSION`** at `tr/tr_api.h:38`.
   The current value is `2`; bump to the next integer
   (currently `3`).
6. **Mirror in the ctypes side** at
   `python/trlib/_ffi.py:94-120` — append a tuple to
   `TrStateC._fields_`. Use the same field order as the
   BIND-C struct so the two layouts stay byte-compatible.
7. **Surface in the Python `TrState` dataclass** at
   `python/trlib/state.py`. Two cases:
   - *Scalar field*: add the field name to the
     `SCALAR_FIELDS` list (`python/trlib/state.py:22-28`).
     Inside `from_c` (which starts at `:74`), the scalar
     dict-comprehension at `:87` walks `SCALAR_FIELDS` and
     populates `state.scalars["YOUR_FIELD"]` automatically;
     the dimension dict-comprehension at `:81-84` is a
     separate stage that handles `nrmax` / `nsmax`. The
     dataclass construction at `:92-100` returns the
     assembled `TrState`. The new field becomes
     accessible as `state.scalars["YOUR_FIELD"]` without
     further code changes.
   - *Array / profile field* (1-D or 2-D, indexed by
     `nrmax` or `nrmax × nsmax`): add a top-level
     attribute on the `TrState` dataclass and the
     corresponding `from_c` parser line by hand,
     mirroring how `AJ` / `RN` / `RT` are handled.
8. **Update {doc}`state`** with the new attribute or
   scalar key.

### Trap: Fortran/C array-order mirroring (2-D fields)

Fortran is column-major and C is row-major. The existing
`RN` / `RT` fields handle this by **transposing** the
index order between the Fortran declaration and the C
declaration:

- Fortran: `RN(TR_MAX_NSMAX, TR_MAX_NRMAX)` at
  `tr/tr_state.f90:60-61`.
- C: `RN[TR_MAX_NRMAX][TR_MAX_NSMAX]` at
  `tr/tr_api.h:53-54`.
- ctypes mirror at `python/trlib/_ffi.py:112-113` follows
  the C layout.

Any new 2-D field must follow the same transposition
pattern or the bytes will be reinterpreted incorrectly.

### Test plan

After the 8 steps:

1. `make -C tr libtrapi.so` — rebuild.
2. Smoke-test:
   ```python
   from trlib import Trlib
   with Trlib() as tr:
       state = tr.get_state()
       print(state.scalars["YOUR_FIELD"])  # for scalars
       # or print(state.YOUR_FIELD) for profiles
   ```
3. Run the canonical pytest sweep:
   ```bash
   PYTHONPATH=python python3 -m pytest --forked \
       --timeout=120 --timeout-method=signal \
       python/trlib/tests/
   ```
   to confirm no regression.

### Worked example: AJRFT (L-7b-i)

The L-7b-i PR — `#187`, merged commit `e049a1e4` — is the
canonical worked example. The exact touch points to imitate:

- `tr/tr_state.f90:64-66` — BIND-C field
- `tr/tr_api.h:57-59` — C field
- `python/trlib/_ffi.py:116-119` — ctypes field
- `python/trlib/state.py:27` — scalar registration in
  `SCALAR_FIELDS`

That PR also bumped `TR_STATE_ABI_VERSION` from `1` to `2`,
which is the same step Recipe C step 5 does.

---

## See also

- {doc}`design` — overall Fortran-side architecture and
  build dependencies.
- {doc}`appendix-mdlkai` — the catalogue of existing
  `MDLKAI` cases.
- {doc}`state` — user-facing `TrState` reference.
- {doc}`physics-overview` — the selector landscape
  (`MDLKAI` / `MDLETA` / `MDLAD` / `MDLAVK` /
  `MDLKNC` / `MDNCLS`) at orientation level.
````

- [ ] **Step 2: Verify file exists**

```bash
head -1 docs/sphinx/modules/tr/en/extending-tr.md
```

Expected: `# Extending TR`.

- [ ] **Step 3: Verify cross-references**

```bash
grep -nE '\{doc\}' docs/sphinx/modules/tr/en/extending-tr.md
```

Expected: at least 5 matches — `{doc}\`appendix-mdlkai\`` (×2), `{doc}\`design\``, `{doc}\`state\``, `{doc}\`physics-overview\``.

- [ ] **Step 4: Verify code-citation completeness**

```bash
grep -cE 'tr/tr_param_registry\.f90|tr/trcoef_turbulence\.f90|tr/trinit\.f90|tr/tr_state\.f90|tr/tr_api\.h|tr/tr_api\.f90|python/trlib/_ffi\.py|python/trlib/state\.py' docs/sphinx/modules/tr/en/extending-tr.md
```

Expected: at least 18 hits across 8 distinct files (the file is dense in citations because each step in Walkthrough C names a different file).

### Task 2.2: Create `docs/sphinx/modules/tr/ja/extending-tr.md`

**Files:**
- Create: `docs/sphinx/modules/tr/ja/extending-tr.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/ja/extending-tr.md` with the following content **verbatim**:

````markdown
# TR の拡張

```{admonition} 想定読者
:class: note

このページは **maintainer 向け** です. 読者はソースツリー
を checkout していて Fortran 編集と `libtrapi.so` の
リビルドに慣れているものとします. 3 つの具体的な
walkthrough を扱います — スカラーパラメータ追加,
`MDLKAI` 配下の transport model 追加, `TrState` field
追加. 各々レシピであり, 導出ではありません.
```

---

## Walkthrough A — 新規スカラーパラメータの追加

TR のパラメータレジストリは `tr/tr_param_registry.f90:76+`
の `SELECT CASE` 手書き dispatch を使っています. 新規
パラメータ `FOO` の追加は dispatch の 1 個の新規 `CASE`
行 + `tr/trinit.f90` のデフォルトで完了します.

**レシピ (5 ステップ):**

1. **変数を宣言する.** 新規パラメータの場合 (まだ TRCOMM
   にない場合), 該当する `tr/trcomm*.f90` モジュールに
   類似パラメータと並べて宣言する. 既存ならスキップ.
2. **registry の case を追加する.**
   `tr/tr_param_registry.f90:76` から始まる
   `SELECT CASE (TRIM(b))` ブロックに
   `CASE ("FOO"); FOO = value` のような行を追加.
   per-section のグループ化規約を保つため, 類似パラメータ
   のすぐ近くに置く.
3. **デフォルトを設定する.** 他の初期化と並べて
   `tr/trinit.f90` に `FOO = ...` を追加.
4. **リビルド.** `make -C tr libtrapi.so`.
5. **Python から使う.** `tr.set_param("FOO", x)` で即座に
   動きます. `tr_set_param` は文字列キーで動作するため
   (`tr/tr_api.f90:124-128,136-148` で確認), C ABI 変更は
   不要です.

配列値パラメータについては, `tr/tr_param_registry.f90:101-106`
の bounds-check 付きイディオムをテンプレートに使います.
既存の `PA[i]` / `PN[i]` / `PNS[i]` / `PT[i]` ケースが
パターンを示しています: 各 `CASE` で `idx` を `SIZE(...)`
と比較し, 代入するか `ierr = 1` を立てるかを分岐します.

---

## Walkthrough B — `MDLKAI` 配下に新規 transport model を追加

乱流熱輸送係数は `tr/trcoef_turbulence.f90:400` の
`SELECT CASE(MDLKAI)` で dispatch されます. (line 64 の
別の `select case` はグラフラベル割り当て用で, 係数計算
自体ではありません.) 各 `MDLKAI` 値が異なるモデルを呼び
ます.

numbering 規約 (`tr/trcoef_turbulence.f90:392-398` の
ソース側コメントより):

- `MDLKAI < 10` — 定数係数の toy model.
- `10 ≤ MDLKAI < 20` — ドリフト波 (+ITG / +ETG) モデル.
- `20 ≤ MDLKAI < 30` — Rebu-Lalla 系.
- `30 ≤ MDLKAI < 40` — 電流拡散駆動 (CDBM) 系.
- `40 ≤ MDLKAI < 60` — ドリフト波バルーニングモデル.
- `MDLKAI ≥ 60` — ITG / TEM / ETG モデル群.

**レシピ (4 ステップ):**

1. **`MDLKAI` 値を選ぶ.** 該当範囲内で次に空いている整数を
   選ぶ (既存モデルの隣に追加する場合).
2. **`CASE (N)` ブロックを追加する.**
   `tr/trcoef_turbulence.f90` の line 400 の後に追加.
   ブロックは適切な輸送係数配列を埋める — `AKDW` (熱
   anomalous), `ADDW` (粒子 anomalous), `AVK` (熱 pinch /
   convective).
3. **必要なら補助 loader を追加する.** モデルが補助
   データ (lookup table, 追加パラメータ検証) を要する
   場合, 既存の family-別ファイル分割に従う —
   `tr/trcoef_neoclassical.f90`,
   `tr/trcoef_resistivity.f90` 等の隣接 `trcoef_*.f90`
   ファイルがテンプレート.
4. **{doc}`appendix-mdlkai` を更新.** カタログでユーザが
   新 case を見つけられるように.

同じ dispatch パターンが他の selector 軸 — `MDLAD`
(粒子拡散), `MDLAVK` (熱 pinch), `MDLETA` (抵抗率) —
にも適用され, それぞれ対応する `trcoef_*.f90` ファイルに
あります. レシピは一般化します.

---

## Walkthrough C — 新規 `TrState` field の追加 (ABI 影響レシピ)

3 つの walkthrough の中で最も影響範囲が広いものです.
`tr_state_t` への field 追加は C ABI を変えるので, 外部の
バイナリ consumer はリビルドあるいはバージョンチェック
が必要になります.

**レシピ (8 ステップ):**

1. **量を計算する.** 値がまだ TRCOMM になければ, 該当
   する `tr/trcomm*.f90` モジュールに TRCOMM 変数を追加
   し, 自然に該当するルーチンで代入する. 新しい派生
   診断量は `tr/trrslt_globals.f90` または
   `tr/trrslt_print.f90` に置くのが普通.
2. **C 側 field を追加する.**
   `tr/tr_state.f90:43-67` の `tr_state_c` 派生型に
   `REAL(C_DOUBLE)` (適切な kind) を **末尾** に追加.
   既存の field offset を維持するためで, バイナリ
   consumer に与える影響を最小化します.
3. **`tr/tr_api.h:49-60` にミラー** する. 対応する
   `double` (適切な C 型) を, やはり struct の末尾に追加.
4. **`tr_api_get_state` 内で field を埋める.**
   `tr/tr_api.f90` には 3 ブロックある:
   - **zero-init** が `:263-283` (新 field に compute-time
     ゼロベースラインがなければここにも追加).
   - **scalar copy** が `:299-315` — AJRFT 先例はここ.
     新スカラーはこのパターンに従う.
   - **per-radius / per-species profile loops** が
     `:321-330` — 新配列 field は `RN` / `RT` / `AJ` /
     `QP` の loop パターンに従う.
5. **`TR_STATE_ABI_VERSION` を bump する.**
   `tr/tr_api.h:38` で. 現値は `2`; 次の整数 (現在の
   流れだと `3`) に上げる.
6. **ctypes 側にミラー.**
   `python/trlib/_ffi.py:94-120` の `TrStateC._fields_` に
   tuple を append. BIND-C struct と同じ field 順を使う
   ことで両 layout が byte-compatible に保たれる.
7. **Python `TrState` dataclass に表面化.**
   `python/trlib/state.py`. 2 ケース:
   - *スカラー field*: field 名を `SCALAR_FIELDS` リスト
     (`python/trlib/state.py:22-28`) に追加. `from_c`
     (`:74` から始まる) 内で scalar dict-comprehension
     (`:87`) が `SCALAR_FIELDS` を走査して
     `state.scalars["YOUR_FIELD"]` を自動で埋める;
     dimension dict-comprehension (`:81-84`) は
     `nrmax` / `nsmax` を扱う別 stage. dataclass 構築
     (`:92-100`) が組み立てた `TrState` を返す. 新 field
     は `state.scalars["YOUR_FIELD"]` で他の変更なしに
     アクセス可能になる.
   - *配列 / profile field* (1 次元または 2 次元,
     `nrmax` または `nrmax × nsmax` で indexing): `TrState`
     dataclass に top-level 属性を追加し, `from_c` 内に
     対応する parser 行を手で書く. `AJ` / `RN` / `RT` の
     扱いがテンプレート.
8. **{doc}`state` を更新.** 新 attribute あるいは scalar
   key を載せる.

### 落とし穴: Fortran/C 配列 order ミラーリング (2 次元 field)

Fortran は column-major, C は row-major です. 既存の
`RN` / `RT` field は Fortran 宣言と C 宣言の間で index 順
を **転置** することでこの差を吸収しています:

- Fortran: `RN(TR_MAX_NSMAX, TR_MAX_NRMAX)` を
  `tr/tr_state.f90:60-61` で宣言.
- C: `RN[TR_MAX_NRMAX][TR_MAX_NSMAX]` を
  `tr/tr_api.h:53-54` で宣言.
- `python/trlib/_ffi.py:112-113` の ctypes ミラーは C
  layout に従う.

新規 2 次元 field も同じ転置パターンに従わないと, バイト
列が誤って再解釈されます.

### テスト計画

8 ステップ完了後:

1. `make -C tr libtrapi.so` — リビルド.
2. Smoke test:
   ```python
   from trlib import Trlib
   with Trlib() as tr:
       state = tr.get_state()
       print(state.scalars["YOUR_FIELD"])  # スカラーの場合
       # あるいは print(state.YOUR_FIELD)  # profile の場合
   ```
3. Canonical な pytest sweep:
   ```bash
   PYTHONPATH=python python3 -m pytest --forked \
       --timeout=120 --timeout-method=signal \
       python/trlib/tests/
   ```
   で regression がないことを確認.

### 動作する例: AJRFT (L-7b-i)

L-7b-i の PR — `#187`, merge commit `e049a1e4` — が
canonical な worked example です. 真似るべき具体的
タッチポイント:

- `tr/tr_state.f90:64-66` — BIND-C field
- `tr/tr_api.h:57-59` — C field
- `python/trlib/_ffi.py:116-119` — ctypes field
- `python/trlib/state.py:27` — `SCALAR_FIELDS` への
  スカラー登録

その PR は `TR_STATE_ABI_VERSION` を `1` → `2` に bump
していて, これがレシピ C のステップ 5 と同じ操作です.

---

## 関連項目

- {doc}`design` — Fortran 側の全体アーキテクチャと
  ビルド依存.
- {doc}`appendix-mdlkai` — 既存 `MDLKAI` ケースのカタログ.
- {doc}`state` — ユーザ向け `TrState` リファレンス.
- {doc}`physics-overview` — selector landscape
  (`MDLKAI` / `MDLETA` / `MDLAD` / `MDLAVK` /
  `MDLKNC` / `MDNCLS`) のオリエンテーション.
````

- [ ] **Step 2: Verify file exists**

```bash
head -1 docs/sphinx/modules/tr/ja/extending-tr.md
```

Expected: `# TR の拡張`.

- [ ] **Step 3: Verify cross-references**

```bash
grep -nE '\{doc\}' docs/sphinx/modules/tr/ja/extending-tr.md
```

Expected: same labels as en (≥5 cross-refs).

- [ ] **Step 4: Verify structural parity**

```bash
diff <(grep -E '^#' docs/sphinx/modules/tr/en/extending-tr.md | sed 's/[^#].*//') \
     <(grep -E '^#' docs/sphinx/modules/tr/ja/extending-tr.md | sed 's/[^#].*//')
```

Expected: empty output (heading depth identical).

### Task 2.3: Phase-2 commit

**Files:** none (git only)

- [ ] **Step 1: Stage the 2 new files**

```bash
git add docs/sphinx/modules/tr/en/extending-tr.md \
        docs/sphinx/modules/tr/ja/extending-tr.md
```

- [ ] **Step 2: Verify diff**

```bash
git diff --cached --stat
```

Expected: 2 files changed; insertion count roughly 290 + 290.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs(tr): add extending-tr page (en + ja)

Internals reference, maintainer-facing. Three concrete
walkthroughs:

- Walkthrough A (5 steps) -- adding a scalar parameter:
  one CASE in tr/tr_param_registry.f90:76+, default in
  trinit.f90, rebuild. C ABI unchanged because
  tr_set_param is string-keyed
  (tr/tr_api.f90:124-128,136-148).

- Walkthrough B (4 steps) -- adding a transport model
  under MDLKAI: SELECT CASE in
  tr/trcoef_turbulence.f90:400 (NOT line 64 which only
  sets graph labels), following the numbering convention
  at :392-398.

- Walkthrough C (8 steps) -- adding a TrState field with
  ABI impact. Touches tr_state.f90 / tr_api.h /
  tr_api.f90 (zero-init :263-283, scalar copy :299-315,
  profile loops :321-330) / TR_STATE_ABI_VERSION bump /
  python/trlib/_ffi.py / python/trlib/state.py
  (SCALAR_FIELDS at :22-28, scalar comprehension at :87,
  dataclass construction at :92-100). The trap section
  warns about Fortran column-major / C row-major
  transposition for 2-D fields. AJRFT (L-7b-i, PR #187,
  e049a1e4) is the worked example.

Each load-bearing claim has a tr/* / python/trlib/*
file:line citation verified across 3 Codex design-stage
review rounds.

Pairs with input-files.md (previous commit) to close out
item F in the deepening menu.

Spec: docs/superpowers/specs/2026-05-04-tr-input-files-and-extending-tr-design.md (63a13325)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 3 — toctree wiring

**Goal of phase:** Insert `input-files` into the User guide toctree (after `parameter-setting`) and `extending-tr` into the Internals toctree (after `design`), in both en and ja indexes.

### Task 3.1: Update en/index.md

**Files:**
- Modify: `docs/sphinx/modules/tr/en/index.md` (User guide + Internals toctrees)

- [ ] **Step 1: Read both toctree blocks**

```bash
sed -n '32,65p' docs/sphinx/modules/tr/en/index.md
```

Expected output shows User guide block (with `parameter-setting` listed) and Internals block (with `design` listed).

- [ ] **Step 2: Insert `input-files` after `parameter-setting` in User guide**

Edit `docs/sphinx/modules/tr/en/index.md`. In the User guide toctree block, insert `input-files` on the line right after `parameter-setting`:

```markdown
parameter-setting
input-files
state
```

- [ ] **Step 3: Insert `extending-tr` after `design` in Internals**

In the same file, in the Internals toctree block, insert `extending-tr` on the line right after `design`:

```markdown
design
extending-tr
mcp
```

- [ ] **Step 4: Verify both insertions**

```bash
grep -nE '^(input-files|extending-tr)$' docs/sphinx/modules/tr/en/index.md
```

Expected: 2 matches — one each, in the right toctree blocks.

### Task 3.2: Update ja/index.md

**Files:**
- Modify: `docs/sphinx/modules/tr/ja/index.md` (mirror of Task 3.1)

- [ ] **Step 1: Read both toctree blocks**

```bash
sed -n '32,65p' docs/sphinx/modules/tr/ja/index.md
```

Expected: same User guide + Internals blocks as en.

- [ ] **Step 2: Insert `input-files` after `parameter-setting` in User guide**

Edit `docs/sphinx/modules/tr/ja/index.md`. In the User guide toctree, insert `input-files` after `parameter-setting`:

```markdown
parameter-setting
input-files
state
```

- [ ] **Step 3: Insert `extending-tr` after `design` in Internals**

In the same file, insert `extending-tr` after `design` in the Internals toctree:

```markdown
design
extending-tr
mcp
```

- [ ] **Step 4: Verify**

```bash
grep -nE '^(input-files|extending-tr)$' docs/sphinx/modules/tr/ja/index.md
```

Expected: 2 matches.

### Task 3.3: Local sanity (cross-link verification skipping `make html`)

**Files:** none (verification)

`make html` is currently blocked locally because the Sphinx theme `furo` is missing from this Python environment (orthogonal cleanup, same situation as G / E / A; CI handles full broken-ref check at push time). Locally we settle for the file-existence and grep checks below.

- [ ] **Step 1: Verify all cross-link targets exist in en + ja**

```bash
for f in \
  docs/sphinx/modules/tr/en/parameter-setting.md \
  docs/sphinx/modules/tr/ja/parameter-setting.md \
  docs/sphinx/modules/tr/en/limitations-and-references.md \
  docs/sphinx/modules/tr/ja/limitations-and-references.md \
  docs/sphinx/modules/tr/en/design.md \
  docs/sphinx/modules/tr/ja/design.md \
  docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md \
  docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md \
  docs/sphinx/modules/tr/en/appendix-mdlkai.md \
  docs/sphinx/modules/tr/ja/appendix-mdlkai.md \
  docs/sphinx/modules/tr/en/state.md \
  docs/sphinx/modules/tr/ja/state.md \
  docs/sphinx/modules/tr/en/physics-overview.md \
  docs/sphinx/modules/tr/ja/physics-overview.md; do
    test -f "$f" && echo "OK: $f"
done | wc -l
```

Expected: `14`.

- [ ] **Step 2: Verify both index files mention the two new pages in the right blocks**

```bash
grep -rn "^\(input-files\|extending-tr\)\$" docs/sphinx/modules/tr/{en,ja}/index.md
```

Expected: 4 matches (2 per language, 1 per page).

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

Expected: 2 files changed, 4 insertions (2 per file), 0 deletions.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs(tr): wire input-files + extending-tr into respective toctrees

Adds the new bilingual pages from the previous two commits to
both index.md files:

- input-files (User guide, after parameter-setting)
- extending-tr (Internals, after design)

This is the third and final commit of the F item in the
deepening menu; spec acceptance criteria 1-14 are satisfied
at this point. AC15 (no HIGH from either reviewer) is
checked by the Phase 4 pre-push gate.

Spec: docs/superpowers/specs/2026-05-04-tr-input-files-and-extending-tr-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 4 — Pre-push gate

**Goal of phase:** CLAUDE.md non-negotiable: 2 reviewer agents in parallel, REVIEW_OK marker, push. pytest is N/A (no Fortran / Python code changed).

### Task 4.1: Launch 2 reviewer agents in parallel

**Files:** none (Agent calls)

- [ ] **Step 1: Run both reviewers in a single message**

```
Agent(subagent_type="superpowers:code-reviewer", prompt="""
Review the diff in /Users/k-yoshimi/Dropbox/cursor/task on
branch chore/pre-push-hook-worktree-compat. Run:

    git log --oneline 63a13325..HEAD
    git diff 63a13325..HEAD

to see the 3 commits implementing the tr input-files +
extending-tr pages per spec
docs/superpowers/specs/2026-05-04-tr-input-files-and-extending-tr-design.md.

Three logical commits:

1. New input-files.md bilingual pair (~270 lines en + ~270
   lines ja).
2. New extending-tr.md bilingual pair (~290 lines en + ~290
   lines ja).
3. Toctree wiring (input-files + extending-tr) in en/ja
   index.md (2 lines per file).

Focus on:
- Cross-reference correctness (each {doc} target exists
  in both en/ and ja/ trees).
- Bilingual structural parity (en and ja heading hierarchies
  match for both new files).
- Code-citation accuracy. Spot-check the load-bearing ones:
  - eq/eqfile.f90:108-115 (MODELG dispatch table).
  - tr/trbpsd.f90:213-245 (BPSD pull, MODELG-conditional).
  - python/eqlib/eqlib.py:39-41,66-70 (path 80-byte limit).
  - tr/tr_param_registry.f90:76 + :101-106 + :184-186.
  - tr/trcoef_turbulence.f90:392-398 + :400.
  - tr/tr_state.f90:43-67 + :60-61 + :64-66.
  - tr/tr_api.h:38 (TR_STATE_ABI_VERSION) + :49-60 + :53-54
    + :57-59.
  - tr/tr_api.f90:124-128,136-148 + :263-283 + :299-315 +
    :321-330.
  - python/trlib/_ffi.py:94-120 + :112-113 + :116-119.
  - python/trlib/state.py:22-28 + :74 + :81-84 + :87 +
    :92-100 + :27.
  - tr/trinit.f90:641-648.
  - tr/trparm.f90:108-112.
- Toctree placement: input-files inserted right after
  parameter-setting in User guide; extending-tr right after
  design in Internals. Both blocks should still be valid
  MyST toctree directives.
- AJRFT worked-example: PR #187 + commit e049a1e4 +
  TR_STATE_ABI_VERSION 1 → 2 history.
- Wording consistency with the unified glossary at 7699b72c
  (no Auto-stabilising / Extension ideas / Combined
  patterns).
- No new MyST anchors (the spec deliberately avoids new
  (label)= lines). Verify clean.

Spec acceptance criteria are at the bottom of the spec doc
(63a13325) -- verify each of 15 ACs.

Report HIGH / MED / LOW in <400 words. Docs-only PR; no
code or tests changed.
""")

Agent(subagent_type="codex:codex-rescue", prompt="""
Independent review of the same diff
(git diff 63a13325..HEAD). Background: the spec went through
3 Codex design-stage review rounds (rounds 1 / 2 / 3 each
with HIGH and/or MED findings, all addressed; round 3
reported zero HIGH/MED). The implementation should match
the final spec verbatim.

Verify the implementation matches the spec's resolutions
across all 8 prior findings:

1. MODELG set is {3,5,8,9}, NOT {3,5,7,8} (Round-1 HIGH 1).
2. KUFDIR/KUFDEV/KUFDCG are documented as namelist-only,
   NOT tr_set_param-reachable (Round-1 HIGH 2).
3. TrState walkthrough is 8 steps with the Fortran
   population step (Round-1 HIGH 7), correct line ranges
   (Round-2 LOW 1 / Round-3 LOW 1), array-order trap
   warning (Round-1 MED 10).
4. 80-byte limit cited as :39-41 + :66-70, NUL fabrication
   removed (Round-2 MED 2).
5. tr_api.f90 three-block listing (zero-init :263-283,
   scalar :299-315, loops :321-330) (Round-2 MED 1).
6. MODELG=9 dispatched to EQRTSK per eqfile.f90:108-115
   (Round-2 HIGH 1).
7. state.py parser line ranges :74 / :81-84 / :87 /
   :92-100 (Round-2 LOW 1 + Round-3 LOW 1).
8. AJRFT worked example with PR #187 + commit e049a1e4
   touch points at tr_state.f90:64-66, tr_api.h:57-59,
   _ffi.py:116-119, state.py:27.

Anchor on additional risks the in-house reviewer might
miss:

- Cross-cutting docs review: any obvious factual error in
  the prose against the current source?
- Bilingual diff: does the ja translation preserve the
  same hedging discipline + code-citation precision as en?
- Are any selectors mentioned in the prose that don't
  exist in source (e.g. did MDLAD get described as
  something it isn't)?
- Anchor labels: this PR does NOT add new MyST anchors
  (intentional per spec). Verify no (label)= lines
  accidentally got added.
- Any line range that should be tightened? Round-3
  caught :74-87 was too loose; check if any other range
  in the implementation is similarly loose.

Report HIGH / MED / LOW in <400 words.
""")
```

Both Agent calls fire in the same message for parallel
execution.

- [ ] **Step 2: Address findings**

For each HIGH finding, make a fix commit on top of Commit 3 (do NOT amend; CLAUDE.md says always create new commits). Re-run the cross-link / structural-parity / code-citation grep checks. If diff is significant, re-run reviewers on the cumulative diff.

For MEDIUM findings, decide per-finding: address in a follow-up commit if the fix is small and clearly reduces risk; document in the commit message otherwise.

LOW findings are typically optional polish — fix opportunistically; no blocker.

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

The chore branch is the workflow's integration target — no separate PR is needed for this small docs delta (mirrors G / E / A and the translation-series patterns).

---

## Spec coverage check

| Spec section | Implementation task |
|---|---|
| §1 Overview | Tasks 1.1–2.2 (cumulative) |
| §2 File structure (4 new + 2 modified, no labels) | Tasks 1.1–1.2, 2.1–2.2, 3.1–3.2 |
| §3 input-files page (5 sections) | Task 1.1 + 1.2 (verbatim prose) |
| §4 extending-tr page (3 walkthroughs + traps + tests + AJRFT example) | Task 2.1 + 2.2 (verbatim prose) |
| §5 Bilingual structure parity | Tasks 1.2 step 4 + 2.2 step 4 (heading-hierarchy diff checks) |
| §6 What this work is NOT | embedded as scope discipline in the prose (no headings; the page does not promise things it does not deliver) |
| §7 Test / verification | Task 3.3 (file-existence + grep checks; sphinx-build deferred to CI) |
| §8 Pre-push gate | Tasks 4.1, 4.2 |
| §9 Out-of-scope deferrals | n/a (deferred items mentioned in spec; nothing in this plan) |
| §10 AC1 (input-files en file 5 sections) | Task 1.1 |
| §10 AC2 (input-files ja file structurally aligned) | Task 1.2 step 4 |
| §10 AC3 (extending-tr en file 4 sections) | Task 2.1 |
| §10 AC4 (extending-tr ja file structurally aligned) | Task 2.2 step 4 |
| §10 AC5 (toctree input-files after parameter-setting) | Tasks 3.1, 3.2 |
| §10 AC6 (toctree extending-tr after design) | Tasks 3.1, 3.2 |
| §10 AC7 (MODELG set + eq dispatch) | Task 1.1 step 1 (verbatim prose) |
| §10 AC8 (ufile reader chain + KUFDIR/KUFDEV/KUFDCG namelist-only) | Task 1.1 step 1 (verbatim prose) |
| §10 AC9 (no runtime trmodels/) | Task 1.1 step 1 (verbatim prose) |
| §10 AC10 (80-byte path limit citations) | Task 1.1 step 1 (verbatim prose) |
| §10 AC11 (param walkthrough citations) | Task 2.1 step 1 (verbatim prose) |
| §10 AC12 (MDLKAI walkthrough citations) | Task 2.1 step 1 (verbatim prose) |
| §10 AC13 (TrState 8-step walkthrough citations) | Task 2.1 step 1 (verbatim prose) |
| §10 AC14 (cross-references resolve) | Task 3.3 (file-existence + grep) |
| §10 AC15 (no HIGH from reviewers) | Task 4.1 |

All spec sections are implemented in this plan. ✓

---

## Notes for the executor

- **Frequent commits**: 3 commit boundaries (input-files content / extending-tr content / toctree). No squashing — chore branch's recent history shows individual commits per docs phase.
- **No source-code changes**: this PR touches only `.md` files. pytest is N/A; the pre-push hook does not gate docs commits on test results.
- **No new MyST anchors**: like A's physics-overview, this work emits only outgoing `{doc}` links to existing pages. Do NOT add any new `(label)=` lines.
- **`make html` is blocked locally**: Sphinx theme `furo` is missing from `requirements.txt`. CI builds the docs cleanly. Local verification is by grep + file-existence checks (Task 3.3); broken-ref detection happens at push time.
- **Reviewer agent fallback**: if `superpowers:code-reviewer` is unavailable in the executor's environment, substitute `feature-dev:code-reviewer`.
- **No PR**: this lands directly on `chore/pre-push-hook-worktree-compat`. Mirrors G / E / A and translation-series patterns.
