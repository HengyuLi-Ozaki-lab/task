# TR Physics Overview Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single bilingual orientation page (`physics-overview.md`) at the head of the TR Sphinx chapter's User-guide toctree, covering 6 sections: what TR solves, spatial grid + boundary conditions, the 7-row `MDLEQ*` table, approximations (flux-surface averaging / quasi-stationary equilibrium / transport-model selector landscape), where TR fits (sawtooth + ELM simplified models vs out-of-scope physics), and a textbook reading list.

**Architecture:** New bilingual file pair `docs/sphinx/modules/tr/{en,ja}/physics-overview.md` (~150 lines each), wired into the **start** of the User guide toctree (before `build`). No new MyST anchor labels; outgoing cross-links target existing pages (`parameters`, `appendix-mdlkai`, `limitations-and-references`, `numerical-stability-and-diagnostics`, `design`).

**Tech Stack:** Sphinx (pinned `<8`) + myst-parser (`<4`) + furo theme. Bilingual ja/en parallel trees. No code or test changes.

**Spec:** `docs/superpowers/specs/2026-05-04-tr-physics-overview-design.md` (commit `4b828d26`, after 3 rounds of Codex design-stage review).

**Predecessor pattern:** Today's G + E appendix work (commits `a8b83311` and `fc74599d`) shows the standard 2-commit shape for a small bilingual addition (content commit + toctree commit). Same pattern applies here.

**PR phases (= 2 logical commit boundaries):**
- **Phase 1 — Commit 1**: New `physics-overview.md` bilingual pair (en + ja)
- **Phase 2 — Commit 2**: User-guide toctree wiring in en/ja `index.md`
- **Phase 3 — Pre-push gate**: 2 reviewers in parallel + REVIEW_OK marker + push

**Plan-time risks already resolved (3 Codex review rounds, see spec §0):**
- Round 1 HIGH 1 (`MDLAVK` is HEAT PINCH not neoclassical) → §3.3c rewrite.
- Round 1 HIGH 2 ("does NOT model" too strong; TR has simplified `MDLST` / `MDLELM`) → §3.4 split.
- Round 2 MED (`MDLAD` is model selector incl. Hinton-Hazeltine, not just anomalous) → §3.3c.
- Round 2 MED (`MDLKNC` / `MDNCLS` not in public registry) → §3.3c registry-vs-source split.
- Round 3 LOW (BPSD metric pull range, implicit-step solver line range) → cited line ranges corrected.

---

## Phase 1 — New bilingual physics-overview page

**Goal of phase:** Create the new file pair with all 6 sections (§3.1, §3.1.5, §3.2, §3.3, §3.4, §3.5). All `{doc}` cross-references target existing pages. End of phase: both files exist, structurally aligned, all citations refer to verified file:line locations.

### Task 1.1: Create `docs/sphinx/modules/tr/en/physics-overview.md`

**Files:**
- Create: `docs/sphinx/modules/tr/en/physics-overview.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/en/physics-overview.md` with the following content **verbatim**:

````markdown
# Physics overview

```{admonition} What this page covers
:class: note

Orientation, NOT a derivation. This page sketches what TR solves
and which approximations it makes, and points at where in the
codebase each claim lives. Audience: graduate students or
early-career researchers approaching transport modelling for the
first time. Equations are named, not written out — for the
mathematics consult a tokamak transport textbook (see "Further
reading" below).
```

---

## What TR solves

TR solves a set of one-dimensional radial transport equations on
a flux-surface-averaged grid. The output is the time evolution of
the radial profiles — density, temperature, current, the safety
factor `q`, and the derived scalar diagnostics in
{doc}`state` (`WPT`, `TAUE1`, `TAUE2`, `BETAN`, etc.).

The equations are assembled and solved implicitly per time step.
Source-term and transport-coefficient assembly happens in
`tr/trcalc.f90:TRCALC` (which combines beam, RF, fusion, ohmic,
radiation, and other contributions). The implicit-step solver
calls live at `tr/trexec.f90:67-99`: `BANDRD` at line 69 and the
LAPACK band-solver path `DGBTRF` / `DGBTRS` / `DGBSV` at lines
81 / 86 / 96 (the `'Solve matrix equation'` comment block at
line 65 sits just above this).

This page deliberately does NOT write the differential equations
in symbolic form. For derivations consult a transport textbook.

---

## Spatial grid and boundary conditions

- **Radial coordinate.** TR's grid is one-dimensional in a
  flux-surface label (a normalised-radius coordinate, often
  written `rho`). The cell count is set by `NRMAX`, with a
  compile-time upper bound of `TR_MAX_NRMAX = 500`
  (`tr/tr_api.h`). Profile arrays are length `NRMAX`. The
  detailed mesh layout — which arrays sit on cell centres
  versus cell edges — lives in {doc}`design`; this page only
  orients you to "there is a single radial axis" and "all
  radial profiles are arrays of length `NRMAX`".

- **Inner boundary.** At the magnetic axis (`NR = 1` in the
  array indexing) regularity / symmetry conditions apply
  automatically; users do not configure these.

- **Outer boundary.** At the plasma edge (`NR = NRMAX`),
  boundary values are imposed via the registry parameters
  (edge-pinning of profiles, Dirichlet-style); see
  {doc}`parameters` for the configurable surface values. TR
  does NOT solve a separate edge / SOL transport problem (see
  "Where TR fits" below).

- **Evolved vs parameterized.** What evolves in time is the
  profile arrays (density / temperature / current). The
  *transport coefficients* are recomputed each inner iteration
  from the current profiles (Codex round-3 verified this in
  `tr/trexec.f90`: inner-loop entry at line 56, matrix solve at
  62-99, profile update at 160-282, `TRCALC` recompute at 298).
  Heating sources, NB beam deposition, RF power profiles, and
  similar drivers enter as source terms also recomputed each
  step.

---

## Equations TR can solve

TR has seven transport-equation switches, each independently
ON/OFF at the registry level (the `MDLEQ*` set). The defaults
below come from `tr/trinit.f90:687-695`:

| Flag | Quantity | Default | Notes |
|---|---|---|---|
| `MDLEQB` | Poloidal B (current diffusion / `q` profile evolution) | 1 (ON) | |
| `MDLEQT` | Temperature (heat diffusion) | 1 (ON) | |
| `MDLEQN` | Particle density (per ion species) | 0 (OFF) | |
| `MDLEQU` | Rotation | 0 (OFF) | |
| `MDLEQZ` | Impurity | 0 (OFF) | |
| `MDLEQ0` | Neutral | 0 (OFF) | |
| `MDLEQE` | Electron-density handling — 0 / 1 / 2 mode (not boolean) | 0 (OFF) | each mode maps to a distinct electron / ion density-equation handling (`tr/trprep.f90:407-415`, `tr/trexec.f90:180-201`); only meaningful when `MDLEQN = 1` (`tr/trprep.f90:202-203`). For per-mode behaviour consult those source locations. |

**The default ON set is `{MDLEQB, MDLEQT}`** — out of the box,
TR evolves current and temperature only; particles, rotation,
impurities, and neutrals are *not* evolved unless their flag is
turned on. Cross-link to {doc}`parameters` for the user-facing
controls.

---

## Approximations

### Flux-surface averaging (1-D radial)

TR is "1-D" in the sense that all profile quantities are indexed
by a single radial coordinate. The 2-D equilibrium geometry comes
from the `eq` module via the BPSD broker: `tr_bpsd_get`
(`tr/trbpsd.f90:160-183`) pulls device + plasma quantities, and
the equilibrium / metric pull at `tr/trbpsd.f90:213-245` only
fires for the geometry-aware `MODELG` settings (the analytic-
equilibrium path skips it). The combined picture is "1.5-D" —
1-D transport on top of 2-D equilibrium — the standard
transport-code style.

### Quasi-stationary equilibrium

The equilibrium is assumed to vary on a slower time scale than
transport, so the BPSD coupling runs as `eq.run()` push → tr
pull within each transport step. TR does NOT solve a
self-consistent dynamic equilibrium. For scenarios where the
equilibrium evolves rapidly (transient disruption studies, e.g.)
the user must either re-run `eq` more frequently or accept the
quasi-stationary approximation.

### Transport-model selector landscape

TR's transport coefficients come from several independent sources,
each with its own model selector. Layout verified at design time
against `tr/trinit.f90` and `tr/tr_param_registry.f90`:

**Selectors exposed in the public parameter registry** (settable
at runtime from `tr.set_param`,
`tr/tr_param_registry.f90:43-49,124-128`):

- **`MDLKAI` — turbulent heat transport.** Selects the
  turbulent (anomalous) heat-transport model. Options include
  CDBM, IFS-PPPL, GLF23, mixed Bohm/gyro-Bohm, and others; see
  {doc}`appendix-mdlkai` for the full list.
- **`MDLETA` — resistivity.** Selects the resistivity model used
  for current diffusion (the `MDLEQB` equation).
- **`MDLAD` — particle diffusion (model family).** Selects the
  particle-diffusion model. Multiple variants are available,
  including the Hinton-Hazeltine analytical form
  (`tr/trinit.f90:290-295`, `tr/trcoef_adhoc.f90:35-45`); it is
  a *model-family* selector, not a single ad-hoc switch.
- **`MDLAVK` — thermal pinch.** Selects the heat-pinch (inward
  heat-flux convective) model. **Not** a neoclassical selector
  — `MDLAVK` stands for the "anomalous V_K" / thermal-pinch
  model family (confirmed by `tr/trinit.f90:296-308` and
  the existing `parameters.md` entries on this page family).

**Selectors present in the Fortran source but NOT in the public
registry** (cannot be set from `tr.set_param`; retain compile-
time defaults from `tr/trinit.f90`):

- **`MDLKNC` — neoclassical heat / resistivity treatment.**
  Default at `tr/trinit.f90:306`.
- **`MDNCLS` — NCLASS module toggle** (the standard NCLASS
  neoclassical library). Defaults at `tr/trinit.f90:324` and
  `tr/trinit.f90:717`.

These two are the actual neoclassical knobs in TR but they are
not exposed for `tr.set_param`. Advanced users who need to
change them must edit `tr/trinit.f90` and rebuild.

The page's role is to give readers a map of the selector
landscape so they know which knob targets which physics — not
to document each selector exhaustively. For the runtime-settable
selectors see {doc}`parameters` and {doc}`appendix-mdlkai`. For
the non-registered selectors {doc}`design` is the entry point.

---

## Where TR fits

**Time scale.** TR is a transport-time-scale code. The natural
time step is milliseconds, total run time of order seconds
(consistent with the defaults `DT = 0.01 s` and `NTMAX = 100` at
`tr/trinit.f90:374,376`, total `1.0 s`). Faster phenomena are
not resolved.

**What TR resolves with simplified models** — these are reduced,
phenomenological models, not first-principles MHD:

- **Sawtooth oscillation.** `MDLST` selector
  (`tr/trinit.f90:392-402`). The mixing is implemented in
  `TRSAWT` (header at `tr/trcalc.f90:1072`, called from
  `tr/trloop.f90:59-65`), with the temperature / density / `q`
  redistribution step at `tr/trcalc.f90:1127-1150`. This is a
  phenomenological reconnection / mixing model, not a kink-mode
  solve.
- **ELM reduction.** `MDLELM` selector
  (`tr/trinit.f90:720-729`). A reduced ELM-frequency /
  ELM-energy-loss model rather than a first-principles
  pedestal-stability calculation.

**What TR does NOT model at all:**

- Edge / pedestal physics in any first-principles sense (no
  ETB-specific transport-barrier solve; boundary conditions are
  imposed at the outer radial cell).
- General MHD instabilities (kink, tearing, NTM, RWM, etc.) —
  only the simplified sawtooth and ELM-reduction switches above
  are present.
- 3-D effects (stellarator geometry, resonant magnetic
  perturbations) — TR assumes axisymmetry through the
  flux-surface averaging.
- Fast (gyrokinetic-scale) fluctuations directly — these enter
  only via the turbulent transport models, as transport
  coefficients.

For a comparison with related open transport codes (ASTRA,
JETTO-SANCO, TRANSP), see the table in
{doc}`limitations-and-references`. For runtime-stability and
diagnostic guidance, see
{doc}`numerical-stability-and-diagnostics`.

---

## Further reading

This section lists standard *general* tokamak transport
references for readers approaching the field for the first time.
TASK-specific publications and the comparison with related open
codes are in {doc}`limitations-and-references`.

The list below gives author + title (and the canonical edition
where one is uncontroversially the standard); publisher and year
are deliberately omitted because multiple editions and reprints
exist and the page does not assert which one the reader uses.
These are reading-list starting points, not authoritative
bibliographic citations.

- J. Wesson, *Tokamaks* (Oxford University Press, 4th edition)
  — encyclopedic textbook covering equilibrium, transport,
  stability, heating, diagnostics.
- R. D. Hazeltine & J. D. Meiss, *Plasma Confinement* —
  focused on the transport theory underlying codes like TR.
- J. P. Freidberg, *Ideal Magnetohydrodynamics* — equilibrium
  and stability foundation; the flux-surface coordinates TR uses
  come from this style of analysis.

The page does NOT cite specific equations or page numbers from
these books — they are bibliographic pointers.
````

- [ ] **Step 2: Verify file exists with the right top-level heading**

```bash
head -1 docs/sphinx/modules/tr/en/physics-overview.md
```

Expected: `# Physics overview`.

- [ ] **Step 3: Verify cross-references**

```bash
grep -nE '\{doc\}' docs/sphinx/modules/tr/en/physics-overview.md
```

Expected: at least 7 matches — `{doc}\`state\``,
`{doc}\`design\``, `{doc}\`parameters\`` (×2),
`{doc}\`appendix-mdlkai\``,
`{doc}\`limitations-and-references\``,
`{doc}\`numerical-stability-and-diagnostics\``.

- [ ] **Step 4: Verify code citations**

```bash
grep -cE 'tr/trcalc\.f90|tr/trexec\.f90|tr/trinit\.f90|tr/trbpsd\.f90|tr/trprep\.f90|tr/trloop\.f90|tr/trcoef_adhoc\.f90|tr/tr_api\.h|tr/tr_param_registry\.f90' docs/sphinx/modules/tr/en/physics-overview.md
```

Expected: at least 18 hits across 9 distinct files.

### Task 1.2: Create `docs/sphinx/modules/tr/ja/physics-overview.md`

**Files:**
- Create: `docs/sphinx/modules/tr/ja/physics-overview.md`

- [ ] **Step 1: Write the file**

Write a new file at `docs/sphinx/modules/tr/ja/physics-overview.md` with the following content **verbatim**:

````markdown
# 物理の概観

```{admonition} このページの位置付け
:class: note

導出ではなく **方向付け (orientation)** のページです. TR が
何を解くか, どの近似を置いているか, 各主張がコードのどこに
あるか, を素描します. 想定読者は輸送モデリングに初めて触れる
大学院生・若手研究者. 方程式は名前で呼び, 数式は書きません —
数学的な詳細はトカマク輸送の教科書 (下の "さらに読むために"
参照) を参照してください.
```

---

## TR が解いていること

TR は flux-surface 平均化された格子上で 1 次元の半径方向輸送
方程式系を解きます. 出力は半径プロファイル (密度, 温度, 電流,
安全係数 `q`) と {doc}`state` で定義される派生スカラー
診断 (`WPT`, `TAUE1`, `TAUE2`, `BETAN` など) の時間発展です.

方程式の組立と陰的時間ステップ求解は時間ステップごとに行います.
ソース項と輸送係数の組立は `tr/trcalc.f90:TRCALC` で
(beam, RF, 核融合, ohmic, 放射等の寄与をまとめている),
陰的ステップのソルバ呼び出しは `tr/trexec.f90:67-99` に
あります: `BANDRD` が line 69, LAPACK バンドソルバ経路の
`DGBTRF` / `DGBTRS` / `DGBSV` が line 81 / 86 / 96 です
(line 65 の `'Solve matrix equation'` コメントブロックは
そのすぐ上にあります).

このページでは微分方程式の symbolic 表現は意図的に書きません.
導出が必要な読者は輸送理論の教科書を参照してください.

---

## 空間格子と境界条件

- **半径座標.** TR の格子は flux-surface label (`rho` と書か
  れる正規化半径座標) で 1 次元です. セル数は `NRMAX` で,
  コンパイル時上限は `TR_MAX_NRMAX = 500` (`tr/tr_api.h`).
  プロファイル配列は長さ `NRMAX`. メッシュレイアウトの詳細
  (どの配列がセル中心 / セル端にあるか) は {doc}`design` に
  あり, このページは「半径軸が 1 本ある」「すべての半径
  プロファイルが長さ `NRMAX` の配列である」という方向付け
  だけを与えます.

- **内側境界.** 磁気軸 (配列 indexing で `NR = 1`) では
  正則性 / 対称性条件が自動で適用されます. ユーザ設定不要.

- **外側境界.** プラズマ端 (`NR = NRMAX`) では境界値が
  registry パラメータ経由で与えられます (プロファイルの
  edge pinning, Dirichlet 風). 設定可能な surface 値は
  {doc}`parameters` 参照. TR は edge / SOL 専用の輸送問題
  を別に解くわけではありません (下の "TR が向く領域" 参照).

- **発展量と parameterize される量.** 時間発展するのは
  プロファイル配列 (密度 / 温度 / 電流). **輸送係数** は
  inner iteration ごとに現在のプロファイルから再計算
  されます (Codex round-3 で `tr/trexec.f90` を確認:
  inner loop entry が line 56, matrix solve が 62-99,
  profile update が 160-282, `TRCALC` 再計算が 298). 加熱源,
  NB beam deposition, RF パワープロファイル等の駆動も
  各ステップで再計算されてソース項として入ります.

---

## TR が解ける方程式

TR は 7 個の輸送方程式スイッチ (`MDLEQ*` 群) を持ち,
それぞれ独立に ON/OFF できます. デフォルトは
`tr/trinit.f90:687-695` 由来:

| Flag | 量 | Default | 注 |
|---|---|---|---|
| `MDLEQB` | ポロイダル B (電流拡散 / `q` プロファイル発展) | 1 (ON) | |
| `MDLEQT` | 温度 (熱拡散) | 1 (ON) | |
| `MDLEQN` | 粒子密度 (イオン種ごと) | 0 (OFF) | |
| `MDLEQU` | 回転 | 0 (OFF) | |
| `MDLEQZ` | 不純物 | 0 (OFF) | |
| `MDLEQ0` | 中性粒子 | 0 (OFF) | |
| `MDLEQE` | 電子密度の扱い — 0 / 1 / 2 モード (boolean ではない) | 0 (OFF) | 各モードが異なる電子 / イオン密度方程式の扱いに対応 (`tr/trprep.f90:407-415`, `tr/trexec.f90:180-201`); `MDLEQN = 1` のときのみ意味を持つ (`tr/trprep.f90:202-203`). モードごとの挙動はソースを参照. |

**箱から出してそのままの状態 (デフォルト ON 集合) は
`{MDLEQB, MDLEQT}`** — TR は電流と温度だけを発展させ,
粒子・回転・不純物・中性は対応する flag を ON にしない限り
発展しません. ユーザ向けコントロールは {doc}`parameters` 参照.

---

## 近似

### Flux-surface 平均 (1 次元半径方向)

TR は「すべてのプロファイル量が単一の半径座標で indexing
される」という意味で 1 次元です. 2 次元の equilibrium
ジオメトリは `eq` モジュールから BPSD ブローカー経由で
入ってきます: `tr_bpsd_get` (`tr/trbpsd.f90:160-183`) が
device + plasma の量を pull し, equilibrium / metric の pull
は `tr/trbpsd.f90:213-245` で geometry-aware な `MODELG`
設定のときだけ走ります (analytic-equilibrium 経路では skip).
全体像は "1.5 次元" (1 次元輸送 + 2 次元 equilibrium) で,
標準的な輸送コードのスタイルです.

### 準定常 equilibrium

equilibrium は輸送よりも遅い時間スケールで変動するという
仮定を置いており, BPSD 結合は各輸送ステップ内で
`eq.run()` push → tr pull の流れで動きます. TR は自己
無撞着な動的 equilibrium を解いていません. equilibrium が
急速に変化するシナリオ (transient disruption 研究等) では,
ユーザは `eq` の再走頻度を上げるか, この準定常近似を受け入れる
必要があります.

### 輸送モデル選択肢の地図

TR の輸送係数は複数の独立なソースから来ており, それぞれ独自
のモデル選択 flag を持ちます. 設計時に `tr/trinit.f90` と
`tr/tr_param_registry.f90` で確認した layout:

**公開 parameter registry に露出されている選択肢** (実行時に
`tr.set_param` から設定可能,
`tr/tr_param_registry.f90:43-49,124-128`):

- **`MDLKAI` — 乱流熱輸送.** 乱流 (anomalous) 熱輸送モデル
  を選択. 選択肢は CDBM, IFS-PPPL, GLF23, mixed Bohm /
  gyro-Bohm その他. 全リストは {doc}`appendix-mdlkai` 参照.
- **`MDLETA` — 抵抗率.** 電流拡散 (`MDLEQB` 方程式) で使う
  抵抗率モデルを選択.
- **`MDLAD` — 粒子拡散 (モデルファミリ).** 粒子拡散モデル
  を選択. Hinton-Hazeltine 解析形を含む複数の variant を
  持つ (`tr/trinit.f90:290-295`,
  `tr/trcoef_adhoc.f90:35-45`); 単一の ad-hoc スイッチでは
  なく **モデルファミリ** の選択です.
- **`MDLAVK` — thermal pinch.** 熱 pinch (内向き熱流束の
  対流成分) モデルを選択. **新古典選択肢ではない** —
  `MDLAVK` は "anomalous V_K" / thermal-pinch モデル
  ファミリを意味します (`tr/trinit.f90:296-308` と
  `parameters.md` の対応エントリで確認済).

**Fortran ソースには存在するが公開 registry には登録されて
いない選択肢** (`tr.set_param` からは設定不可、`tr/trinit.f90`
のコンパイル時デフォルトのまま):

- **`MDLKNC` — 新古典熱 / 抵抗率処理.** デフォルトは
  `tr/trinit.f90:306`.
- **`MDNCLS` — NCLASS モジュールトグル** (標準的な NCLASS
  新古典ライブラリ). デフォルトは `tr/trinit.f90:324` と
  `tr/trinit.f90:717`.

これらが TR で実際の新古典の knob ですが, `tr.set_param`
からは触れません. これらを変えたい上級ユーザは
`tr/trinit.f90` を編集して rebuild する必要があります.

このページの役割は読者にどの knob がどの物理を狙うかの
地図を渡すことで, 各選択肢を網羅的に説明することではあり
ません. 実行時 settable な選択肢は {doc}`parameters` と
{doc}`appendix-mdlkai` を, 非登録の選択肢は {doc}`design`
を参照してください.

---

## TR が向く領域

**時間スケール.** TR は輸送時間スケールのコードです. 自然
な時間ステップは ms オーダー, 総走行時間は秒オーダー
(`tr/trinit.f90:374,376` のデフォルト `DT = 0.01 s`,
`NTMAX = 100`, total `1.0 s` と整合的). より高速の現象は
解像できません.

**TR が簡略化モデルで扱うもの** — これらは現象論的・縮約
モデルで, 第一原理 MHD ではありません:

- **Sawtooth 振動.** `MDLST` selector
  (`tr/trinit.f90:392-402`). 混合は `TRSAWT` で実装
  (header が `tr/trcalc.f90:1072`,
  `tr/trloop.f90:59-65` から呼ばれる) され,
  温度 / 密度 / `q` の再分配ステップは
  `tr/trcalc.f90:1127-1150` にあります. 現象論的な
  reconnection / mixing モデルで, kink モードを解いている
  わけではありません.
- **ELM 縮約.** `MDLELM` selector (`tr/trinit.f90:720-729`).
  ELM 周波数 / ELM エネルギー損失の縮約モデルで, 第一原理
  ペデスタル安定性計算ではありません.

**TR がまったく扱わないもの:**

- Edge / pedestal 物理 (第一原理的な意味で). ETB 専用の
  輸送障壁は解かない; 境界条件は最外側半径セルに与える.
- 一般の MHD 不安定性 (kink, tearing, NTM, RWM 等) — 上記の
  簡略化された sawtooth と ELM 縮約のみが存在する.
- 3 次元効果 (stellarator ジオメトリ, resonant magnetic
  perturbation) — TR は flux-surface 平均によって
  axisymmetry を仮定している.
- 高速 (gyrokinetic スケール) 揺動を直接解くこと — これらは
  乱流輸送モデルから輸送係数として取り入れられるのみ.

関連オープン輸送コード (ASTRA, JETTO-SANCO, TRANSP) との
比較表は {doc}`limitations-and-references` 参照.
実行時の安定性 / 診断ガイダンスは
{doc}`numerical-stability-and-diagnostics` 参照.

---

## さらに読むために

このセクションは **一般的な** トカマク輸送の標準文献を初学者
向けの読書出発点として並べたものです. TASK 固有の出版物と
関連オープンコードとの比較は {doc}`limitations-and-references`
の references 節を参照してください.

下記は author + title (および canonical な edition がある場合
のみ edition 番号) を pointer 形式で挙げたもので, **publisher
と year は意図的に省いています**. 複数の版・重版があり, ページ
が「これ」と特定の版を主張すると過剰主張になるためです.
authoritative な bibliographic citation ではなく, 読書出発点
として扱ってください.

- J. Wesson, *Tokamaks* (Oxford University Press, 4th
  edition) — equilibrium, 輸送, 安定性, 加熱, 診断を網羅
  する百科全書的教科書.
- R. D. Hazeltine & J. D. Meiss, *Plasma Confinement* —
  TR のようなコードの背後にある輸送理論に集中.
- J. P. Freidberg, *Ideal Magnetohydrodynamics* — equilibrium
  と安定性の基礎. TR が使う flux-surface 座標はこの系統の
  解析から来ている.

このページはこれらの本から個別の方程式やページ番号を引用
していません — bibliographic pointer です.
````

- [ ] **Step 2: Verify file exists with the right top-level heading**

```bash
head -1 docs/sphinx/modules/tr/ja/physics-overview.md
```

Expected: `# 物理の概観`.

- [ ] **Step 3: Verify cross-references**

```bash
grep -nE '\{doc\}' docs/sphinx/modules/tr/ja/physics-overview.md
```

Expected: same labels as en (since `{doc}` resolves to filenames, not localised strings).

- [ ] **Step 4: Verify structural parity (heading hierarchy)**

```bash
diff <(grep -E '^#' docs/sphinx/modules/tr/en/physics-overview.md | sed 's/[^#].*//') \
     <(grep -E '^#' docs/sphinx/modules/tr/ja/physics-overview.md | sed 's/[^#].*//')
```

Expected: empty output (heading depth identical between en and ja).

### Task 1.3: Phase-1 commit

**Files:** none (git only)

- [ ] **Step 1: Stage the 2 new files**

```bash
git add docs/sphinx/modules/tr/en/physics-overview.md \
        docs/sphinx/modules/tr/ja/physics-overview.md
```

- [ ] **Step 2: Verify diff**

```bash
git diff --cached --stat
```

Expected: 2 files changed, ~300+ insertions (~150 each), 0 deletions.

- [ ] **Step 3: Commit**

```bash
git commit -m "docs(tr): add physics-overview page (en + ja)

Adds the bilingual orientation page covering 6 sections per spec
(item A in project_tr_proper_manual.md deepening menu, sized 1
session). Pairs with G + E shipped earlier today; this is the
entry point readers see before build / hello-world.

Sections:
- What TR solves (1-D radial transport on flux-surface-averaged
  grid; cite tr/trcalc.f90:TRCALC + tr/trexec.f90:67-99)
- Spatial grid + boundary conditions (NRMAX / inner-axis
  regularity / outer-edge imposed values / evolved-vs-
  parameterized) -- added per Codex round-1 LOW 4
- Equations TR can solve -- 7-row MDLEQ* table verified against
  tr/trinit.f90:687-695, MDLEQE row notes the 0/1/2 mode
- Approximations (flux-surface averaging, quasi-stationary
  equilibrium, transport-model selector landscape with
  registry-vs-source split per Codex round-2 MED 3)
- Where TR fits (sawtooth via MDLST / TRSAWT, ELM reduction via
  MDLELM as simplified models; full MHD / pedestal / 3-D /
  gyrokinetic NOT modelled)
- Further reading (Wesson / Hazeltine-Meiss / Freidberg as
  bibliographic pointers; publisher and year deliberately
  omitted to avoid asserting unverified citations)

ja and en written in parallel; structurally aligned. The
toctree wiring lands in the next commit.

Spec: docs/superpowers/specs/2026-05-04-tr-physics-overview-design.md (4b828d26, after 3 Codex review rounds)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — User-guide toctree wiring

**Goal of phase:** Prepend `physics-overview` to the User guide toctree of both `index.md` files so the new page is the first User-guide entry. End of phase: en and ja indexes both list `physics-overview` ahead of `build`.

### Task 2.1: Update en/index.md

**Files:**
- Modify: `docs/sphinx/modules/tr/en/index.md` (User guide toctree, ~line 32–46)

- [ ] **Step 1: Read the current User guide toctree**

```bash
sed -n '30,48p' docs/sphinx/modules/tr/en/index.md
```

Expected:

```markdown
## User guide

```{toctree}
:maxdepth: 1

build
hello-world
parameters
parameter-setting
state
context-manager
faq
applications
```
```

- [ ] **Step 2: Insert the new entry as the FIRST line of the toctree**

Edit `docs/sphinx/modules/tr/en/index.md`. Locate the User guide toctree's contents block and prepend `physics-overview` immediately after the blank line that follows `:maxdepth: 1`:

```markdown
:maxdepth: 1

physics-overview
build
hello-world
```

- [ ] **Step 3: Verify**

```bash
grep -n "physics-overview" docs/sphinx/modules/tr/en/index.md
```

Expected: one match in the User guide toctree block (i.e. line number is between the `## User guide` header and the next `## ` header).

### Task 2.2: Update ja/index.md

**Files:**
- Modify: `docs/sphinx/modules/tr/ja/index.md` (mirror of Task 2.1)

- [ ] **Step 1: Read the current User guide toctree**

```bash
sed -n '30,48p' docs/sphinx/modules/tr/ja/index.md
```

Expected: same User guide block as en, listing `build`, `hello-world`, `parameters`, ..., `applications`.

- [ ] **Step 2: Insert the new entry as the FIRST line of the toctree**

Edit `docs/sphinx/modules/tr/ja/index.md`. Prepend `physics-overview` to the User guide toctree, same position as en:

```markdown
:maxdepth: 1

physics-overview
build
hello-world
```

- [ ] **Step 3: Verify**

```bash
grep -n "physics-overview" docs/sphinx/modules/tr/ja/index.md
```

Expected: one match.

### Task 2.3: Local sanity (cross-link verification skipping `make html`)

**Files:** none (verification)

`make html` is currently blocked locally because the Sphinx theme `furo` is missing from this Python environment (orthogonal cleanup, same as G / E). CI handles full broken-ref check at push time. Locally we settle for the file-existence and grep checks below.

- [ ] **Step 1: Verify all 5 cross-link targets exist in en + ja**

```bash
for f in \
  docs/sphinx/modules/tr/en/parameters.md \
  docs/sphinx/modules/tr/ja/parameters.md \
  docs/sphinx/modules/tr/en/appendix-mdlkai.md \
  docs/sphinx/modules/tr/ja/appendix-mdlkai.md \
  docs/sphinx/modules/tr/en/state.md \
  docs/sphinx/modules/tr/ja/state.md \
  docs/sphinx/modules/tr/en/design.md \
  docs/sphinx/modules/tr/ja/design.md \
  docs/sphinx/modules/tr/en/limitations-and-references.md \
  docs/sphinx/modules/tr/ja/limitations-and-references.md \
  docs/sphinx/modules/tr/en/numerical-stability-and-diagnostics.md \
  docs/sphinx/modules/tr/ja/numerical-stability-and-diagnostics.md; do
    test -f "$f" && echo "OK: $f"
done | wc -l
```

Expected: `12`.

- [ ] **Step 2: Verify both index files mention the new page in the User guide block**

```bash
grep -rnB2 "^physics-overview$" docs/sphinx/modules/tr/{en,ja}/index.md
```

Expected: two matches; each preceded by `:maxdepth: 1` (or a blank line) confirming the entry sits at the start of the User guide toctree.

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
git commit -m "docs(tr): wire physics-overview to head of User guide toctree

Adds the new bilingual orientation page (commit \$PHASE1_SHA) as
the FIRST entry of the User guide toctree in both index.md
files, ahead of build. Reading order becomes
index -> physics-overview -> build -> hello-world -> ..., which
matches the new-reader path the spec optimises for.

Spec: docs/superpowers/specs/2026-05-04-tr-physics-overview-design.md

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

    git log --oneline 4b828d26..HEAD
    git diff 4b828d26..HEAD

to see the 2 commits implementing the tr physics-overview page
per spec docs/superpowers/specs/2026-05-04-tr-physics-overview-design.md
(plan: docs/superpowers/plans/2026-05-04-tr-physics-overview.md).

Two logical commits:

1. New bilingual physics-overview file pair (~210 lines en
   + ~190 lines ja).
2. User-guide toctree wiring in en/ja index.md (1 line each,
   prepended ahead of build).

Focus on:

- Cross-reference correctness: each {doc} target exists in both
  en/ and ja/ trees (parameters, appendix-mdlkai, state, design,
  limitations-and-references, numerical-stability-and-diagnostics).
- Bilingual structural parity: en and ja files should have
  identical heading hierarchy. Compare via
  diff <(grep ^# en) <(grep ^# ja).
- Code-citation accuracy: 18+ file:line citations in the prose.
  Spot-check the most load-bearing ones --
  tr/trexec.f90:67-99 (implicit solver), tr/trinit.f90:687-695
  (MDLEQ defaults), tr/tr_param_registry.f90:43-49,124-128
  (registered selectors), tr/trbpsd.f90:160-183 + :213-245
  (BPSD pulls), tr/trcalc.f90:1072 + :1127-1150 (sawtooth),
  tr/trinit.f90:720-729 (MDLELM), tr/trinit.f90:290-295 (MDLAD
  variants), tr/trinit.f90:296-308 (MDLAVK), tr/trinit.f90:306
  (MDLKNC), tr/trinit.f90:324 + :717 (MDNCLS).
- Hedging discipline: claims about tokamak physics regimes
  (sawtooth Q0<1, ELM, pedestal, MHD instabilities) should be
  framed as 'simplified phenomenological model' or 'not
  modelled at all', NOT as authoritative physics statements.
- Wording consistency with the unified glossary at 7699b72c
  (no Auto-stabilising / Extension ideas / Combined patterns).
- toctree placement: physics-overview as the FIRST entry in the
  User guide block of both index.md files (ahead of build).
- No new MyST anchors (the spec deliberately avoids new
  (label)= lines). Verify clean.
- Textbook bibliography (§Further reading) does NOT contain
  publisher / year fields (round-1 LOW 1 fix). Confirm clean.

Spec acceptance criteria are at the bottom of the spec doc
(4b828d26) -- verify each.

Report HIGH / MED / LOW in <400 words. Docs-only PR; no code or
tests changed.
""")

Agent(subagent_type="codex:codex-rescue", prompt="""
Independent review of the same diff (git diff 4b828d26..HEAD).
Background: spec went through 3 Codex design-stage review rounds
which addressed 2 HIGH, 5 MED, and several LOWs. Round-3 of the
design review reported NO HIGH/MED -- only line-range LOWs which
were applied. The implementation should match that final spec
verbatim.

Verify the implementation matches the design's resolutions:

1. MDLAVK is named as 'thermal pinch', NOT as the neoclassical
   knob. (Round-1 HIGH 1.)
2. Sawtooth + ELM are documented as 'simplified models' present
   in TR (MDLST / TRSAWT / MDLELM), NOT as 'TR does NOT model'.
   (Round-1 HIGH 2.)
3. MDLEQE table row says 0/1/2 mode + MDLEQN=1 dependency,
   not 0/1 boolean. (Round-1 MED 1.)
4. BPSD pull cited at tr/trbpsd.f90:160-183 (device/plasma) and
   tr/trbpsd.f90:213-245 (equilibrium/metric, MODELG-conditional).
   (Round-1 MED 2 + Round-3 LOW 1.)
5. MDLAD described as model-family selector incl. Hinton-
   Hazeltine, NOT 'anomalous particle diffusion' alone.
   (Round-2 MED 2.)
6. MDLKNC + MDNCLS explicitly noted as 'NOT in public registry,
   compile-time defaults only'. (Round-2 MED 3.)
7. TRSAWT redistribution range cited as
   tr/trcalc.f90:1127-1150, NOT :1072-1086. (Round-2 MED 1.)
8. Implicit solver cited at tr/trexec.f90:67-99 with
   BANDRD/DGBTRF/DGBTRS/DGBSV at lines 69/81/86/96.
   (Round-3 LOW 2.)

Anchor on additional risks the in-house reviewer might miss:

- Cross-cutting docs review: any obvious factual errors about
  TR's behaviour or about tokamak physics in general?
- Bilingual diff: does the ja translation preserve the same
  hedging discipline + code-citation precision as en?
- Are any selectors mentioned in the prose that don't exist in
  source (e.g. did 'MDLETA' get added without being in
  tr_param_registry.f90)?
- Anchor labels: this PR does NOT add new MyST anchors
  (intentional per spec). Verify no labels accidentally got
  added.

Report HIGH / MED / LOW in <400 words.
""")
```

Both Agent calls fire in the same message for parallel execution.

- [ ] **Step 2: Address findings**

For each HIGH finding, make a fix commit on top of Commit 2 (do NOT amend; CLAUDE.md says always create new commits). Re-run cross-link / structural-parity / code-citation grep checks. If diff is significant, re-run reviewers on the cumulative diff.

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

The chore branch is the workflow's integration target for this docs work — no separate PR is needed (mirrors G / E and the translation series).

---

## Spec coverage check

| Spec section | Implementation task |
|---|---|
| §1 Overview | Tasks 1.1–1.2 (cumulative) |
| §2 File structure (2 modified, 2 new, no labels) | Tasks 1.1–1.2, 2.1–2.2 |
| §3.1 'What TR solves' | Task 1.1 + 1.2 (verbatim prose) |
| §3.1.5 'Spatial grid and boundary conditions' | Task 1.1 + 1.2 (verbatim prose) |
| §3.2 'Equations TR can solve' (7-row table) | Task 1.1 + 1.2 (verbatim prose) |
| §3.3 'Approximations' (flux-surface / quasi-stationary / selector landscape with registry-vs-source split) | Task 1.1 + 1.2 (verbatim prose) |
| §3.4 'Where TR fits' (simplified models + NOT-modelled list) | Task 1.1 + 1.2 (verbatim prose) |
| §3.5 'Further reading' (3 textbook pointers, no publisher / year) | Task 1.1 + 1.2 (verbatim prose) |
| §4 Bilingual structure parity | Task 1.2 step 4 (heading-hierarchy diff check) |
| §5 What this page is NOT | embedded as scope discipline in the prose (no headings; the page does not promise things it does not deliver) |
| §6 Test / verification | Task 2.3 (file-existence + grep checks; sphinx-build deferred to CI) |
| §7 Pre-push gate | Tasks 3.1, 3.2 |
| §8 Out-of-scope deferrals | n/a (deferred items mentioned in spec; nothing in this plan) |
| §9 AC1 (en file 6 sections) | Task 1.1 |
| §9 AC2 (ja file structurally aligned) | Task 1.2 step 4 |
| §9 AC3 (toctree updates with physics-overview prepended) | Tasks 2.1, 2.2 |
| §9 AC4 (§3.1.5 spatial-grid orientation) | Task 1.1 step 1 (verbatim prose) |
| §9 AC5 (MDLEQ table + MDLEQE 0/1/2 mode) | Task 1.1 step 1 (verbatim prose) |
| §9 AC6 (default ON set {MDLEQB, MDLEQT}) | Task 1.1 step 1 (verbatim prose) |
| §9 AC7 (transport-selector landscape with registry-vs-source split + MDLAVK clarified as thermal pinch) | Task 1.1 step 1 (verbatim prose) |
| §9 AC8 (BPSD pull line ranges) | Task 1.1 step 1 (verbatim prose) |
| §9 AC9 (sawtooth + ELM simplified vs not-modelled split) | Task 1.1 step 1 (verbatim prose) |
| §9 AC10 (textbook pointers without publisher / year) | Task 1.1 step 1 (verbatim prose) |
| §9 AC11 (cross-references resolve) | Task 2.3 (file-existence + grep) |
| §9 AC12 (no HIGH from reviewers) | Task 3.1 |

All spec sections are implemented in this plan. ✓

---

## Notes for the executor

- **Frequent commits**: 2 commit boundaries (content + toctree). No squashing — chore branch's recent history (G + E + applications-translation series) shows individual commits as the established style.
- **No source-code changes**: this PR touches only `.md` files. pytest is N/A.
- **No new MyST anchors**: unlike G (which added `(faq-singleton)=` and `(reinit-constraints)=`), this page only emits outgoing `{doc}` links to existing pages. Do NOT add any new `(label)=` lines.
- **`make html` is blocked locally**: Sphinx theme `furo` is missing from `requirements.txt`. CI builds the docs cleanly. Local verification is by grep + file-existence checks (Task 2.3); broken-ref detection happens at push time.
- **Reviewer agent fallback**: if `superpowers:code-reviewer` is unavailable in the executor's environment, substitute `feature-dev:code-reviewer`. Interchangeable for the in-house review role.
- **No PR**: this lands directly on `chore/pre-push-hook-worktree-compat` (the workflow's integration target). Mirrors G / E and translation-series patterns.
