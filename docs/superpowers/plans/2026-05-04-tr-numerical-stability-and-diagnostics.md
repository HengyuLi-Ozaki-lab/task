# TR Numerical Stability & Diagnostics Appendix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single bilingual appendix page ("Numerical stability and diagnostics") to the TR Sphinx chapter, paired with G (limitations & references). Documents the implicit time-stepping scheme, time-step selection guidance, inner-iteration convergence behaviour, `tr_run` ierr=3 umbrella semantics, plus three diagnostic topics (tr2 console output, `TrDiagCode` mapping, `TrState` diagnostic patterns).

**Architecture:** New bilingual file pair `docs/sphinx/modules/tr/{en,ja}/numerical-stability-and-diagnostics.md` (~150 lines each), wired into the Appendix toctree of both `index.md` files. No new MyST anchor labels are needed; outgoing cross-links (`{doc}\`applications\``, `{doc}\`parameters\``, `{doc}\`parameter-setting\``, `{doc}\`state\``) target existing pages.

**Tech Stack:** Sphinx (pinned `<8`) + myst-parser (`<4`) + furo theme. Bilingual ja/en parallel trees. No code or test changes.

**Spec:** `docs/superpowers/specs/2026-05-04-tr-numerical-stability-and-diagnostics-design.md` (commit `8b23d800`, after Codex design-stage review fixes at `bf359449` and citation-tightening at `8b23d800`).

**Predecessor pattern:** G appendix shipped earlier today (commits `11f2b16d`, `5ad9a4a6`, `8081073b`, `a8b83311`). Same chapter conventions apply.

**PR phases (= 2 logical commit boundaries):**
- **Phase 1 — Commit 1**: New `numerical-stability-and-diagnostics.md` bilingual pair (en + ja)
- **Phase 2 — Commit 2**: Appendix toctree wiring in en/ja `index.md`
- **Phase 3 — Pre-push gate**: 2 reviewers in parallel + REVIEW_OK marker + push

(No Phase-0 label phase this time — the spec deliberately avoids new MyST anchors.)

**Plan-time risks already resolved (spec §0 / Codex design-stage review):**
- HIGH 1 (`THETA` vs `FADV`): every prose mention of the advancement coefficient names `FADV`. The default `FADV = 1.D0` is hard-coded at `tr/trexec.f90:498` (NOT in `trinit.f90`).
- HIGH 4 (`ierr=3` causes): the page documents the umbrella nature of `ierr=3` — it is any non-zero from `tr_prep`/`tr_loop` collapsed to one ABI code (`tr/tr_api.f90:227-245`).
- MED 6 (`Q0 < 1` hedging): "may indicate" / "depending on the scenario" framing.
- BONUS (ht6m fixture): verified at design time; row populated with `(DT=0.0001, NTMAX=1000, total=0.1s)` from `tot_ht6m_params.py:63-64`.
- LOW 9 (out-of-scope): mesh sensitivity / singular-matrix recovery / restart explicitly deferred in spec §8.

---

## Phase 1 — New bilingual appendix

**Goal of phase:** Create the new file pair with all 7 subsections (4 stability + 3 diagnostics). All `{doc}` cross-references target existing pages. End of phase: both files exist, structurally aligned, no broken cross-refs.

### Task 1.1: Create `docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md`

**Files:**
- Create: `docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md` with the following content **verbatim**:

````markdown
# Numerical stability and diagnostics

```{admonition} What this page covers
:class: note

Operational guidance for keeping TR runs healthy (stability) and
for reading the signals when something goes wrong (diagnostics).
This page pairs with {doc}`limitations-and-references`: that page
documents what TR cannot do; this page documents how to keep TR
doing what it can.
```

---

## Numerical stability

### Time-stepping scheme

TR uses an implicit time-stepping scheme. The advancement
coefficient is `FADV` (do not confuse with `THETA`, which is
reserved elsewhere): `FADV = 0.5` is Crank-Nicolson and
`FADV = 1.0` is fully implicit. The value is hard-coded inside
the time-step routine itself — `tr/trexec.f90:498` assigns
`FADV = 1.D0` unconditionally — so TR runs fully implicit out
of the box and there is no public knob to switch to
Crank-Nicolson without editing the source. The scheme-selector
comments at `tr/trexec.f90:494-498` document the meaning of
each value.

Concrete consequence: a strict CFL condition does NOT apply.
Time-step selection is governed by truncation error and
inner-iteration convergence, not by an advection-style
stability bound.

### Time-step selection guidance

`DT` selection is governed by two competing concerns:

- Smaller `DT` reduces truncation error per step but requires
  more steps for the same total time.
- Larger `DT` is cheaper per step but makes the inner iteration
  (see below) work harder, and at some point the scheme can no
  longer reduce the residual within `LMAXTR` iterations.

The defaults are `DT = 0.01 s` (`tr/trinit.f90:374`) and
`NTMAX = 100` (`tr/trinit.f90:376`), which together advance the
simulation by 1.0 s. These suit equilibrium-scale runs;
sub-millisecond `DT` is rarely required for transport-time-scale
studies but is sometimes necessary for source-driven transients
(see the `ht6m` row below).

For divergent or unstable cases the practical recipe is to halve
`DT` and retry — the `StableTrRunner` wrapper in
{doc}`applications` implements exactly this.

Examples (fixture-grounded):

| Fixture | `DT` | `NTMAX` | Total time |
|---|---|---|---|
| `tot_demo2014_short` (Layer 1 baseline) | 0.01 s | 100 | 1.0 s |
| `tot_ht6m_short` (Layer 1 baseline) | 0.0001 s | 1000 | 0.1 s |

The `demo2014` fixture sets only `NTMAX` at
`python/totlib/tests/fixtures/tot_demo2014_params.py:74` and
inherits `DT = 0.01` from the trinit defaults. The `ht6m`
fixture overrides both at
`python/totlib/tests/fixtures/tot_ht6m_params.py:63-64`,
running 100× more steps at 100× smaller `DT` because its
physical time scale (sub-second) and resolution requirements
differ.

### Inner-iteration convergence (`EPSLTR`, `LMAXTR`)

Each time step runs an inner iteration that converges toward
`EPSLTR` (relative residual threshold). The convergence checks
live at `tr/trexec.f90:112-128` (per species, per radial
cell). The exit-on-iteration-budget guard sits at
`tr/trexec.f90:141`: when the iteration counter reaches
`LMAXTR` the loop exits *without* setting `IERR`, so the run
**continues** with whatever residual was reached rather than
aborting. The `--Inner ...` lines that appear in tr2 console
output flag time steps where this happened.

Defaults are `EPSLTR = 0.001` and `LMAXTR = 10`, which is
conservative. For aggressive studies that saturate `LMAXTR`,
raise `LMAXTR` first; only loosen `EPSLTR` if profile-level
diagnostics confirm that the residual is local (e.g. confined
to one species or one radial cell) rather than a sign of an
underlying numerical problem.

### `tr_run` `ierr=3` (`CALC_FAILED`) diagnosis

`tr_api_run` (`tr/tr_api.f90:227-245`) returns
`TR_ERR_CALC_FAILED` for **any** non-zero result code from the
underlying `tr_prep` / `tr_loop` routines. The wrapper
deliberately collapses the full set of downstream failure
classes into a single ABI code; `ierr=3` is therefore an
umbrella signal that "something downstream did not finish
cleanly", not a diagnosis of which subsystem failed. Narrowing
it down is the user's job.

Diagnostic recipe:

1. Run `validate()` first; if any blocking diagnostic
   (`FILE_MISSING`, `MISSING_REQUIRED` — see below) is present,
   fix it. This is the cheapest way to rule out classes of
   failure before launching the run.
2. Halve `DT` and retry (use `StableTrRunner` in
   {doc}`applications`). If the failure was a numerical
   stiffness or inner-iteration symptom, this often clears it.
3. Inspect tr2 console output for `Inner not converged` lines
   and diverging energies (see "Reading tr2 console output"
   below).
4. Cross-check {doc}`parameters` and {doc}`parameter-setting`
   for parameter ranges and inter-parameter constraints that
   `validate()` may not catch.

---

## Diagnostics & observability

### Reading tr2 console output

The standalone `tr2` driver prints a per-step block plus
periodic episode summaries via the `WRITE(6, …)` statements in
`tr/trrslt_print.f90`. The full set of formats lives in that
file (see e.g. lines 57, 89, 266 for representative blocks);
the layout depends on the print mode (`MDLPRT`). The signals
most users care about are the per-step scalars:

- `T` — current simulation time [s]
- `WPT` — total stored energy [MJ]
- `TAUE1` / `TAUE2` — energy confinement times [s]
- `Q0` — axis safety factor
- `AJT` — total plasma current [MA]

These are exactly the fields exposed via `tr.get_state()` (see
{doc}`state`); reading the console line is therefore a quick
way to sanity-check what `get_state()` will return.

Episode summary blocks additionally print device-shape
parameters and integrated beam / RF powers. For the exact
layout of each block, consult `tr/trrslt_print.f90`.

### `validate()` output mapping (`TrDiagCode`)

`tr.validate()` returns a list of diagnostics, each carrying
one of five `TrDiagCode` values from the enum at
`tr/tr_api.h:69-75` (mirrored in `python/trlib/_ffi.py:58-62`).
Each value has a distinct physical meaning:

- **`OUT_OF_RANGE`** — a parameter value sits outside the
  registry's allowed range. Typical example: `NSMAX = 10` is
  rejected because the compile-time bound is `TR_MAX_NSMAX = 8`.
  Fix: clamp the value to a valid range before calling `run()`.

- **`INCONSISTENT_PAIR`** — two related parameters disagree.
  Typical example: `EXTERNAL_DRIVEN_I != 0` paired with
  `EXTERNAL_DRIVEN_RW <= 0` would silently no-op in `trprf` —
  validate catches the pair. See {doc}`parameters` for the
  affected pairs.

- **`OUT_OF_RANGE_AFTER_DEP`** — a parameter sits inside its
  registry-declared range but conflicts with a runtime-deduced
  bound. Typical example: `NRMAX` after equilibrium load may be
  capped by the equilibrium grid.

- **`FILE_MISSING`** — a required file path is empty or points
  at a file the library cannot open. Typical example:
  `MODELG ∈ {3, 5, 7, 8}` paired with empty `KNAMEQ`.

- **`MISSING_REQUIRED`** — a required parameter was never set.
  Distinct from `OUT_OF_RANGE` because the *absence* is the
  problem, not the value.

The recommended workflow is to call `validate()` after
`set_params()` and before `run()`, which is exactly what
{doc}`parameter-setting` Method D demonstrates.

### `TrState` diagnostic patterns

The {doc}`state` page lists the fields that `get_state()`
populates. Below are *what to look for* in those fields when
running a transport simulation. Each item is a rule of thumb,
not a TR API contract — the magnitudes and thresholds depend
on the scenario.

- **Stored-energy drift.** Monitor `WPT` over time. A run
  approaching a quasi-steady state should plateau; an unbounded
  rise typically indicates a source/sink imbalance.

- **q-profile peaking.** `Q0` (axis safety factor) below 1 is
  a rule-of-thumb threshold for sawtooth instability in
  tokamaks. TR does not model sawteeth, so persistent
  `Q0 < 1` may indicate that the resulting profile is
  non-physical at the axis — but the magnitude of the drift,
  and whether it matters for the diagnostic the user actually
  cares about, depend on the scenario.

- **Current relaxation.** The time over which `AJT` settles
  after a change in `EXTERNAL_DRIVEN_I` is a rule-of-thumb
  estimate of the resistive current relaxation time. Order of
  seconds for ITER-class devices, sub-second for smaller
  machines.

- **Energy confinement.** `TAUE1` / `TAUE2` are computed from
  `WPT` and the integrated input power. Comparing their ratio
  with empirical scaling laws (e.g. ITER89-P) is a standard
  sanity check for whether the simulation is in a physically
  sensible regime.
````

- [ ] **Step 2: Verify file exists with the right top-level heading**

```bash
head -1 docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md
```

Expected: `# Numerical stability and diagnostics`.

- [ ] **Step 3: Verify cross-references**

```bash
grep -nE '\{doc\}' docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md
```

Expected: 7 matches — `{doc}\`limitations-and-references\``, `{doc}\`applications\`` (×2), `{doc}\`parameters\``, `{doc}\`parameter-setting\`` (×2), `{doc}\`state\`` (×2).

- [ ] **Step 4: Verify code-citation completeness**

```bash
grep -nE 'tr/trexec\.f90|tr/trinit\.f90|tr/tr_api\.f90|tr/tr_api\.h|tr/trrslt_print\.f90|python/trlib/_ffi\.py|python/totlib/tests/fixtures' docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md | wc -l
```

Expected: at least 9 matches (covers `trexec.f90:494-498/498/112-128/141`, `trinit.f90:374/376`, `tr_api.f90:227-245`, `tr_api.h:69-75`, `trrslt_print.f90:57,89,266`, `_ffi.py:58-62`, `tot_demo2014_params.py:74`, `tot_ht6m_params.py:63-64`).

### Task 1.2: Create `docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md`

**Files:**
- Create: `docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md` with the following content **verbatim**:

````markdown
# 数値安定性と診断

```{admonition} このページの位置付け
:class: note

TR を健全に走らせるための運用指針 (安定性) と, 何かおかしくなった
ときに信号を読むための指針 (診断) です.
{doc}`limitations-and-references` と対をなしています:
あちらのページは TR が **できないこと** を述べ, このページは
TR をやれる範囲で **やり続けるための方法** を述べます.
```

---

## 数値安定性

### 時間積分スキーム

TR は陰的な時間積分を使います. 進行係数は `FADV` (`THETA` と
混同しないこと; あれは別の用途で予約されている名前です):
`FADV = 0.5` は Crank-Nicolson, `FADV = 1.0` は完全陰的です.
値はタイムステップルーチン内に **直接書かれており** —
`tr/trexec.f90:498` で `FADV = 1.D0` が無条件に代入されています —
TR は箱から出してそのままで完全陰的に動きます. ソースを書き換え
ない限り Crank-Nicolson に切り替える公開のつまみはありません.
スキーム選択肢のコメントは `tr/trexec.f90:494-498` にあります.

具体的な帰結: 厳密な CFL 条件は **適用されません**. `DT` の
選び方は移流型の安定性境界ではなく, 切断誤差と内側反復の収束
で決まります.

### `DT` 選びの指針

`DT` は二つの相反する要請の間で決まります:

- `DT` を小さくすると 1 ステップあたりの切断誤差は減りますが,
  同じ総時間を走るのに必要なステップ数が増えます.
- `DT` を大きくすると 1 ステップは速いですが, 内側反復 (後述)
  の負担が増え, ある点で `LMAXTR` 反復以内に残差を縮められ
  なくなります.

デフォルトは `DT = 0.01 s` (`tr/trinit.f90:374`) と
`NTMAX = 100` (`tr/trinit.f90:376`) で, 合わせて 1.0 s 進める
設定です. これは平衡時間スケールの実行に向いています.
ms 以下の `DT` が必要になるのはまれですが, ソース駆動の
過渡応答 (下の `ht6m` 参照) では必要なときがあります.

発散・不安定が起きるケースの実践的レシピは, **`DT` を半分にして
やり直す** ことです — {doc}`applications` の `StableTrRunner`
ラッパがちょうどそれを実装しています.

例 (fixture 由来):

| Fixture | `DT` | `NTMAX` | Total time |
|---|---|---|---|
| `tot_demo2014_short` (Layer 1 baseline) | 0.01 s | 100 | 1.0 s |
| `tot_ht6m_short` (Layer 1 baseline) | 0.0001 s | 1000 | 0.1 s |

`demo2014` fixture は `NTMAX` のみ設定 (`python/totlib/tests/fixtures/tot_demo2014_params.py:74`)
し, `DT = 0.01` は trinit のデフォルトを継承しています.
`ht6m` fixture は両方を上書きしており
(`python/totlib/tests/fixtures/tot_ht6m_params.py:63-64`),
物理時間スケール (秒以下) と分解能要請の違いから 100 倍多い
ステップを 100 倍小さい `DT` で走らせています.

### 内側反復の収束 (`EPSLTR`, `LMAXTR`)

各タイムステップ内で `EPSLTR` (相対残差しきい値) に向かって
内側反復が回ります. 収束チェックは `tr/trexec.f90:112-128`
にあります (種ごと, 半径セルごと). 反復回数の打ち切りガードは
`tr/trexec.f90:141` で, カウンタが `LMAXTR` に達するとループを
**`IERR` を立てずに** 抜けるため, 最終的に到達した残差のまま
走行は **続行** します (中断しない). 該当ステップは tr2 の
コンソール出力で `--Inner ...` 行として現れます.

デフォルトは `EPSLTR = 0.001`, `LMAXTR = 10` で保守的です.
`LMAXTR` を頻繁に飽和させる積極的な研究では, まず `LMAXTR` を
増やしてください. `EPSLTR` を緩めるのはプロファイルレベルの
診断で残差が局所的 (1 種, 1 半径セルに限定) と確認できた場合
のみにすべきです.

### `tr_run` `ierr=3` (`CALC_FAILED`) の診断

`tr_api_run` (`tr/tr_api.f90:227-245`) は内部の `tr_prep` /
`tr_loop` のいずれからの **非ゼロ戻り値** もすべて
`TR_ERR_CALC_FAILED` に集約します. ラッパは故意に下流の
失敗クラス全部を 1 つの ABI コードに潰しているため, `ierr=3`
は「下流のどこかで何かが正常終了しなかった」という傘信号で
あって, どのサブシステムが失敗したかの診断ではありません.
絞り込みはユーザの仕事です.

診断レシピ:

1. 先に `validate()` を呼ぶ. ブロッキングな診断
   (`FILE_MISSING`, `MISSING_REQUIRED` — 後述) があれば直す.
   走行前に失敗クラスを除外できる最も安価な手段です.
2. `DT` を半分にして再走 ({doc}`applications` の
   `StableTrRunner` を使う). 数値的硬さや内側反復の症状なら
   これで解消することが多いです.
3. tr2 のコンソール出力で `Inner not converged` の行や,
   発散していくエネルギーを観察 (下の "tr2 コンソール出力の
   読み方" 参照).
4. `validate()` が捕まえないパラメータ範囲・組み合わせ制約は
   {doc}`parameters` / {doc}`parameter-setting` で照合.

---

## 診断と可観測性

### tr2 コンソール出力の読み方

スタンドアロンの `tr2` ドライバは `tr/trrslt_print.f90` 内の
`WRITE(6, …)` 文を介してステップごとのブロックと periodic な
エピソードサマリを出力します. すべての format 文はそのファイル
にあります (代表的なブロックは line 57, 89, 266). レイアウトは
print モード (`MDLPRT`) に依存します. 大半のユーザが気にする
のは per-step のスカラーです:

- `T` — 現在のシミュレーション時刻 [s]
- `WPT` — 総蓄積エネルギー [MJ]
- `TAUE1` / `TAUE2` — エネルギー閉じ込め時間 [s]
- `Q0` — 中心安全係数
- `AJT` — 総プラズマ電流 [MA]

これらはちょうど `tr.get_state()` で取れる field と一致します
({doc}`state` 参照). コンソール行を読むことは
`get_state()` の戻り値を即時 sanity check する手段になります.

エピソードサマリブロックには加えて装置形状パラメータと統合された
beam / RF パワーが出ます. ブロックごとの正確なレイアウトは
`tr/trrslt_print.f90` を参照してください.

### `validate()` 出力 (`TrDiagCode`) の物理的意味

`tr.validate()` は診断のリストを返し, 各項目は `tr/tr_api.h:69-75`
の enum (`python/trlib/_ffi.py:58-62` でミラー) の 5 つの
`TrDiagCode` 値のいずれかを持ちます. 各値の物理的意味:

- **`OUT_OF_RANGE`** — パラメータ値がレジストリの許容範囲外.
  典型例: `NSMAX = 10` はコンパイル時上限 `TR_MAX_NSMAX = 8`
  により拒否される. 対処: `run()` 前に範囲内へクランプする.

- **`INCONSISTENT_PAIR`** — 関連 2 パラメータが矛盾. 典型例:
  `EXTERNAL_DRIVEN_I != 0` と `EXTERNAL_DRIVEN_RW <= 0` の
  組合せは `trprf` で暗黙に no-op になるところを validate が
  捕まえる. 対象ペアは {doc}`parameters` 参照.

- **`OUT_OF_RANGE_AFTER_DEP`** — レジストリ宣言の範囲内では
  あるが実行時に決まる境界と矛盾. 典型例: 平衡 load 後の
  `NRMAX` が平衡格子で頭打ちになる場合.

- **`FILE_MISSING`** — 必須ファイルパスが空, またはライブラリ
  が開けないファイルを指している. 典型例: `MODELG ∈ {3, 5, 7, 8}`
  かつ `KNAMEQ` が空.

- **`MISSING_REQUIRED`** — 必須パラメータが未設定. `OUT_OF_RANGE`
  と区別される: 値ではなく **不在** が問題.

推奨ワークフローは `set_params()` の後 `run()` の前に
`validate()` を呼ぶこと. 詳しくは {doc}`parameter-setting`
の Method D を参照.

### `TrState` の診断的読み方

{doc}`state` ページに `get_state()` が埋める field 一覧が
あります. 以下はそれらの field を **何を観るために使うか** の
ガイドです. 各項目は経験則であり TR API の契約ではありません —
具体的な大きさやしきい値はシナリオに依存します.

- **蓄積エネルギーのドリフト.** `WPT` の時間変化を観察.
  準定常に至るランは plateau になるはずで, 際限ない上昇は
  通常ソース・シンクの不均衡を示します.

- **q プロファイルのピーキング.** `Q0` (中心安全係数) が 1
  を切るのはトカマクで sawtooth 不安定の経験則的しきい値です.
  TR は sawtooth をモデル化していないので, 持続的な `Q0 < 1`
  は中心軸でのプロファイルが非物理的になっているサインかも
  しれません — ただしドリフトの大きさと, それがユーザの実際に
  気にする診断にとって意味があるかどうかは, シナリオに依存します.

- **電流緩和.** `EXTERNAL_DRIVEN_I` 変更後に `AJT` が落ち着く
  までの時間は, 抵抗的な電流緩和時間の経験則的見積もりに
  なります. ITER 級装置では秒オーダー, 小型装置では秒以下.

- **エネルギー閉じ込め.** `TAUE1` / `TAUE2` は `WPT` と統合
  された入力電力から計算されます. 経験的スケーリング則
  (e.g. ITER89-P) との比は, シミュレーションが物理的に妥当な
  領域にいるかの定番 sanity check です.
````

- [ ] **Step 2: Verify file exists with the right top-level heading**

```bash
head -1 docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md
```

Expected: `# 数値安定性と診断`.

- [ ] **Step 3: Verify cross-references**

```bash
grep -nE '\{doc\}' docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md
```

Expected: 7 matches — same labels as en (since `{doc}` resolves to filenames, not localised strings).

- [ ] **Step 4: Verify structural parity (heading hierarchy)**

```bash
diff <(grep -E '^#' docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md | sed 's/[^#].*//') \
     <(grep -E '^#' docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md | sed 's/[^#].*//')
```

Expected: empty output (heading depth identical between en and ja).

### Task 1.3: Phase-1 commit

**Files:** none (git only)

- [ ] **Step 1: Stage the 2 new files**

```bash
git add docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md \
        docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md
```

- [ ] **Step 2: Verify diff**

```bash
git diff --cached --stat
```

Expected: 2 files changed, ~300 insertions (~150 each), 0 deletions.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs(tr): add numerical-stability-and-diagnostics appendix (en + ja)

Adds the bilingual appendix page covering 4 stability topics
plus 3 diagnostic topics, sized at 1 session per the deepening
menu in project_tr_proper_manual.md (item E). Pairs with G
(limitations-and-references shipped at a8b83311).

Stability:
- Time-stepping scheme: TR is implicit; FADV = 1.D0 hard-coded
  at tr/trexec.f90:498 (no Crank-Nicolson knob without source
  edits). No strict CFL applies.
- Time-step selection: defaults DT=0.01s/NTMAX=100
  (tr/trinit.f90:374,376); fixture-grounded examples for
  demo2014 (1.0s) and ht6m (0.1s, 100x finer DT).
- Inner-iteration convergence: EPSLTR check at
  tr/trexec.f90:112-128, LMAXTR exit at :141 (run continues
  without setting IERR on saturation).
- ierr=3 (CALC_FAILED) diagnosis: documented as umbrella code
  per tr/tr_api.f90:227-245 (collapses any non-zero from
  tr_prep/tr_loop). Diagnostic recipe with cross-links to
  validate(), StableTrRunner, parameters table.

Diagnostics:
- Reading tr2 console output: pointer to
  tr/trrslt_print.f90 with 5-scalar shortcut for per-step
  signals.
- TrDiagCode mapping: all 5 enum values from tr/tr_api.h:69-75
  with physical meaning + typical-example pairing.
- TrState diagnostic patterns: 4 rule-of-thumb items
  (energy drift, q-profile peaking, current relaxation,
  confinement scaling) -- explicitly hedged framing.

ja and en written in parallel; structurally aligned. The
toctree wiring lands in the next commit.

Spec: docs/superpowers/specs/2026-05-04-tr-numerical-stability-and-diagnostics-design.md (8b23d800)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — toctree wiring

**Goal of phase:** Add the new appendix to both `index.md` Appendix toctrees so the page is discoverable in the rendered chapter. End of phase: en and ja indexes both list `numerical-stability-and-diagnostics` after `limitations-and-references`.

### Task 2.1: Update en/index.md

**Files:**
- Modify: `docs/sphinx/modules/tr/en/index.md` (Appendix toctree, ~line 67–73)

- [ ] **Step 1: Read the current Appendix toctree**

```bash
sed -n '65,76p' docs/sphinx/modules/tr/en/index.md
```

Expected:

```markdown
## Appendix

```{toctree}
:maxdepth: 1

appendix-mdlkai
appendix-sensitivity
limitations-and-references
```
```

(`limitations-and-references` was added in commit `8081073b` earlier today.)

- [ ] **Step 2: Insert the new entry**

Edit `docs/sphinx/modules/tr/en/index.md`. Locate the line `limitations-and-references` and append `numerical-stability-and-diagnostics` on the line below, before the closing triple-backtick:

```markdown
appendix-mdlkai
appendix-sensitivity
limitations-and-references
numerical-stability-and-diagnostics
```

- [ ] **Step 3: Verify**

```bash
grep -n "numerical-stability-and-diagnostics" docs/sphinx/modules/tr/en/index.md
```

Expected: one match in the Appendix toctree block.

### Task 2.2: Update ja/index.md

**Files:**
- Modify: `docs/sphinx/modules/tr/ja/index.md` (mirror of Task 2.1)

- [ ] **Step 1: Read the current Appendix toctree**

```bash
sed -n '65,76p' docs/sphinx/modules/tr/ja/index.md
```

Expected: same Appendix block as en, with `appendix-mdlkai` / `appendix-sensitivity` / `limitations-and-references`.

- [ ] **Step 2: Insert the new entry**

Edit `docs/sphinx/modules/tr/ja/index.md`. Append `numerical-stability-and-diagnostics` below `limitations-and-references` in the same toctree block:

```markdown
appendix-mdlkai
appendix-sensitivity
limitations-and-references
numerical-stability-and-diagnostics
```

- [ ] **Step 3: Verify**

```bash
grep -n "numerical-stability-and-diagnostics" docs/sphinx/modules/tr/ja/index.md
```

Expected: one match.

### Task 2.3: Local sanity (cross-link verification skipping `make html`)

**Files:** none (verification)

`make html` is currently blocked locally because the Sphinx theme `furo` is missing from this Python environment (orthogonal cleanup item — same situation as G; CI handles full broken-ref check at push time). Locally we settle for the file-existence and grep checks below.

- [ ] **Step 1: Verify all 4 cross-link targets exist**

```bash
for f in \
  docs/sphinx/modules/tr/en/applications.md \
  docs/sphinx/modules/tr/ja/applications.md \
  docs/sphinx/modules/tr/en/parameters.md \
  docs/sphinx/modules/tr/ja/parameters.md \
  docs/sphinx/modules/tr/en/parameter-setting.md \
  docs/sphinx/modules/tr/ja/parameter-setting.md \
  docs/sphinx/modules/tr/en/state.md \
  docs/sphinx/modules/tr/ja/state.md \
  docs/sphinx/modules/tr/en/limitations-and-references.md \
  docs/sphinx/modules/tr/ja/limitations-and-references.md; do
    test -f "$f" && echo "OK: $f"
done
```

Expected: 10 lines, all `OK: ...`.

- [ ] **Step 2: Verify both index files mention the new appendix**

```bash
grep -rn "^numerical-stability-and-diagnostics$" docs/sphinx/modules/tr/
```

Expected: 2 matches (en/index.md + ja/index.md).

### Task 2.4: Phase-2 commit

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
git commit -m "docs(tr): wire numerical-stability-and-diagnostics into Appendix toctree

Adds the new bilingual appendix page (commit \$PHASE1_SHA)
under the existing 'Appendix' section of both index.md files,
positioned after limitations-and-references for parity with
the existing appendix-mdlkai / appendix-sensitivity /
limitations-and-references ordering.

This is the second and final commit of the numerical-stability
& diagnostics appendix work; spec acceptance criteria 1-12 are
satisfied at this point. AC13 (no HIGH from either reviewer)
is checked by the Phase 3 pre-push gate.

Spec: docs/superpowers/specs/2026-05-04-tr-numerical-stability-and-diagnostics-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

(Replace `\$PHASE1_SHA` with the actual short SHA of the Phase-1 commit if you want a proper cross-reference; otherwise the literal text above is acceptable.)

---

## Phase 3 — Pre-push gate

**Goal of phase:** CLAUDE.md non-negotiable: 2 reviewer agents in parallel, REVIEW_OK marker, push. pytest is N/A (no Fortran / Python code changed).

### Task 3.1: Launch 2 reviewer agents in parallel

**Files:** none (Agent calls)

- [ ] **Step 1: Run both reviewers in a single message**

```
Agent(subagent_type="superpowers:code-reviewer", prompt="""
Review the diff in /Users/k-yoshimi/Dropbox/cursor/task on branch
chore/pre-push-hook-worktree-compat. Run:

    git log --oneline 8b23d800..HEAD
    git diff 8b23d800..HEAD

to see the 2 commits implementing the tr numerical-stability &
diagnostics appendix per spec
docs/superpowers/specs/2026-05-04-tr-numerical-stability-and-diagnostics-design.md.

Two logical commits:

1. New bilingual appendix file pair (~150 lines en + ~150
   lines ja).
2. Appendix toctree wiring in en/ja index.md (1 line each).

Focus on:

- Cross-reference correctness: 7 {doc} cross-references in
  each appendix file (limitations-and-references, applications,
  parameters, parameter-setting, state). Verify MyST syntax +
  target file existence.
- Bilingual structural parity: en and ja appendix files should
  have identical heading hierarchy. Compare via
  diff <(grep ^# en) <(grep ^# ja).
- Code-citation accuracy: 9+ file:line citations in the prose.
  Spot-check the most load-bearing ones — tr/trexec.f90:498
  (FADV=1.D0), tr/trexec.f90:112-128 (EPSLTR check),
  tr/trexec.f90:141 (LMAXTR exit), tr/tr_api.f90:227-245
  (ierr=3 umbrella), tr/tr_api.h:69-75 (TrDiagCode enum),
  tot_demo2014_params.py:74, tot_ht6m_params.py:63-64.
- Hedging discipline: every claim in the 'TrState diagnostic
  patterns' section should be marked as a rule of thumb /
  scenario-dependent. The spec was tightened on 'Q0 < 1'
  specifically (now 'may indicate' / 'depending on the
  scenario').
- Wording consistency with the unified glossary at 7699b72c
  (no 'Auto-stabilising' / 'Extension ideas' / 'Combined
  patterns').
- toctree placement: numerical-stability-and-diagnostics after
  limitations-and-references in both index.md files.

Spec acceptance criteria are at the bottom of the spec doc
(8b23d800) — verify each.

Report HIGH / MED / LOW in <400 words. Docs-only PR; no code or
tests changed.
""")

Agent(subagent_type="codex:codex-rescue", prompt="""
Independent review of the same diff (git diff 8b23d800..HEAD).
Background: spec went through a Codex design-stage review
which addressed 2 HIGH (FADV variable name + ierr=3 umbrella
nature), 2 MED (Q0<1 hedging, ierr=3 sub-section bloat
prevention), and 1 LOW (out-of-scope additions). The user
also requested explicit code-citation tightening; the spec
now carries 13 acceptance criteria, several of which require
specific file:line citations.

Verify the implementation matches the design's resolutions.
Anchor on:

- Were the 2 HIGH design-stage fixes actually implemented in
  the prose? FADV (not THETA) named throughout? ierr=3
  documented as umbrella, not as a list of plausible-but-
  uncited causes?
- Q0<1 hedging: does the prose say 'may indicate' /
  'depending on the scenario', not 'is non-physical'?
- Are all code citations from spec §9 ACs actually present
  in the prose at the cited file:line locations? Spot-check
  the most load-bearing.
- Cross-cutting docs review: any obvious factual errors
  about TR's behaviour that the in-house reviewer might
  miss?
- Bilingual diff: does the ja translation preserve the same
  hedging discipline + code-citation precision as en?
- Anchor labels: this PR does NOT add new MyST anchors
  (intentional per spec). Verify no labels accidentally got
  added.

Report HIGH / MED / LOW in <400 words.
""")
```

Both Agent calls fire in the same message for parallel execution.

- [ ] **Step 2: Address findings**

For each HIGH finding, make a fix commit on top of Commit 2 (do NOT amend; CLAUDE.md says always create new commits). Re-run the cross-link / structural-parity / code-citation grep checks. If diff is significant, re-run reviewers on the cumulative diff.

For MEDIUM findings, decide per-finding: address in a follow-up commit if the fix is small and clearly reduces risk; document in the commit message otherwise.

LOW findings are typically optional polish — fix opportunistically; no blocker.

### Task 3.2: REVIEW_OK marker + push

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

The chore branch is the workflow's integration target for this docs work — no separate PR is needed (mirrors the recent translation series and the G appendix work).

---

## Spec coverage check

| Spec section | Implementation task |
|---|---|
| §1 Overview | Tasks 1.1–1.2 (cumulative) |
| §2 File structure (2 modified, 2 new, no labels) | Tasks 1.1–1.2, 2.1–2.2 |
| §3.1 Stability subsections (4) | Task 1.1 + 1.2 (content embedded verbatim) |
| §3.2 Diagnostics subsections (3) | Task 1.1 + 1.2 (content embedded verbatim) |
| §4 Bilingual structure parity | Task 1.2 step 4 (heading-hierarchy diff check) |
| §5 What this page is NOT | embedded as scope discipline in the prose (no headings; the page does not promise things it does not deliver) |
| §6 Test / verification | Task 2.3 (file-existence + grep checks; sphinx-build deferred to CI) |
| §7 Pre-push gate | Tasks 3.1, 3.2 |
| §8 Out-of-scope deferrals | n/a (deferred items mentioned in spec; nothing in this plan) |
| §9 AC1 (en file 7 subsections) | Task 1.1 |
| §9 AC2 (ja file structurally aligned) | Task 1.2 step 4 |
| §9 AC3 (toctree updates) | Tasks 2.1, 2.2 |
| §9 AC4 (FADV name + tr/trexec.f90:498 default) | Task 1.1 step 1 (verbatim prose) |
| §9 AC5 (fixture file:line citations) | Task 1.1 step 1 (verbatim prose) |
| §9 AC6 (EPSLTR/LMAXTR file:line) | Task 1.1 step 1 (verbatim prose) |
| §9 AC7 (ierr=3 umbrella citation) | Task 1.1 step 1 (verbatim prose) |
| §9 AC8 (trrslt_print.f90:57,89,266) | Task 1.1 step 1 (verbatim prose) |
| §9 AC9 (TrDiagCode enum + ctypes mirror) | Task 1.1 step 1 (verbatim prose) |
| §9 AC10 (5 TrDiagCode values match enum) | Task 1.1 step 1 (verbatim prose) |
| §9 AC11 (rule-of-thumb hedging) | Task 1.1 step 1 (verbatim prose) |
| §9 AC12 (cross-references resolve) | Task 2.3 (file-existence + grep) |
| §9 AC13 (no HIGH from reviewers) | Task 3.1 |

All spec sections are implemented in this plan. ✓

---

## Notes for the executor

- **Frequent commits**: 2 commit boundaries (content + toctree). No squashing — chore branch's recent history (G appendix at `5ad9a4a6` + `8081073b`) shows individual commits are the established style for docs work.
- **No source-code changes**: this PR touches only `.md` files. pytest is N/A; the pre-push hook does not gate docs commits on test results.
- **No new MyST anchors**: unlike G (which added `(faq-singleton)=` and `(reinit-constraints)=`), this page only emits outgoing `{doc}` links to existing pages. Do NOT add any new `(label)=` lines.
- **`make html` is blocked locally**: Sphinx theme `furo` is missing from `requirements.txt`. CI builds the docs cleanly. Local verification is by grep + file-existence checks (Task 2.3); broken-ref detection happens at push time.
- **Reviewer agent fallback**: if `superpowers:code-reviewer` is unavailable in the executor's environment, substitute `feature-dev:code-reviewer`. The two are interchangeable for the in-house review role.
- **No PR**: this lands directly on `chore/pre-push-hook-worktree-compat` (the workflow's integration target for ongoing docs and feature work). Mirrors the G appendix and the translation-series patterns.
