# TR Tutorials D1 (T1 + T3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single bilingual page (`tutorials.md`) to the TR Sphinx chapter covering T1 (ITER-like single run) + T3 (`PT[1] × PN[1]` parameter sweep with matplotlib heatmap).

**Architecture:** Doc-only change. Two new MyST markdown files (en + ja parallel pair), two existing toctree edits. No code touched, no pytest required. Pre-push gate uses 2 reviewers in parallel (in-house + Codex) per `CLAUDE.md`.

**Tech Stack:** MyST markdown, Sphinx (sphinx<8 + myst-parser<4), furo theme (CI build only — locally unavailable).

**Spec:** `docs/superpowers/specs/2026-05-04-tr-tutorials-d1-design.md` (commit `029abe4c`, Codex rounds 1-6 cleared).

---

## File Structure

| File | Operation | Responsibility |
|---|---|---|
| `docs/sphinx/modules/tr/en/tutorials.md` | CREATE | English page with §T1, §T3, §What's next |
| `docs/sphinx/modules/tr/ja/tutorials.md` | CREATE | Japanese counterpart, structurally aligned |
| `docs/sphinx/modules/tr/en/index.md` | MODIFY | Insert `tutorials` into User-guide toctree after `applications` |
| `docs/sphinx/modules/tr/ja/index.md` | MODIFY | Same as above for ja |

No new MyST anchor labels. Code blocks are identical between en and ja (per spec §4); prose around them is translated.

---

### Task 1: Create `docs/sphinx/modules/tr/en/tutorials.md`

**Files:**
- Create: `docs/sphinx/modules/tr/en/tutorials.md`

- [ ] **Step 1: Write the file**

Full content (write verbatim):

````markdown
# Tutorials

```{admonition} Where this page fits
:class: tip

Two end-to-end worked examples, building on what
{doc}`hello-world`, {doc}`parameter-setting`, and
{doc}`applications` cover. **D1** of the multi-scenario
tutorials series ships:

- **T1** — single ITER-like run with the
  `eqdata.ITER01` fixture
- **T3** — a `PT[1] × PN[1]` parameter sweep
  visualised as a heatmap

The remaining four scenarios (T2 JET-like, T4 `tr2`
equivalence at 1e-10, T5 `tot`-coupled run, T6
numerical-blow-up debugging) are reserved for D2.
```

## T1 — ITER-like single-run scenario

**Goal.** Walk through one 100-step run using the
shipped `eqdata.ITER01` equilibrium fixture (TASK/EQ
binary format, loaded under `MODELG=3` via the `EQRTSK`
reader), then read the resulting `TrState`.

**Set-up.** The fixture lives at
`python/eqlib/tests/fixtures/eqdata.ITER01`. The C ABI's
`KNAMEQ` parameter has an 80-byte limit (see
{doc}`input-files`), so absolute paths usually do not
fit; the standard pattern is to `chdir` into the
directory holding the file and pass a bare filename:

```python
import os
os.chdir("python/eqlib/tests/fixtures")
```

**The script.** All non-geometry knobs come from the
shipped fixture
`python/trlib/tests/fixtures/tr_iter01_params.py`,
which sets `MODELG=3`, `NSMAX=4`,
`KNAMEQ="eqdata.ITER01"`, `RIPS`/`RIPE`, the plasma
profile arrays `PN`/`PNS`/`PT`/`PTS`, and heating-source
scalars. Geometry (`RR`, `RA`, `RKAP`, `RDLT`, `BB`) is
loaded from the TASK/EQ binary file at the start of the
first `tr.run(...)` call (the chain is
`tr_run → tr_prep → tr_set_metric → eq_load + tr_bpsd_get`),
so the script does **not** set geometry explicitly.

```python
import os
from trlib import Trlib
from trlib.tests.fixtures import tr_iter01_params

os.chdir("python/eqlib/tests/fixtures")  # KNAMEQ is 80 bytes

with Trlib() as tr:
    tr_iter01_params.apply(tr)
    tr.validate()
    tr.run(ntmax=100)
    state = tr.get_state()

print(f"WPT   = {state.scalars['WPT']}")
print(f"BETAN = {state.scalars['BETAN']}")
print(f"Q0    = {state.scalars['Q0']}")
print(f"TAUE1 = {state.scalars['TAUE1']}")
```

**Expected output.** Concrete values depend on the build
configuration and may drift; run the script locally to
populate them:

```text
WPT   = ...
BETAN = ...
Q0    = ...
TAUE1 = ...
```

**Extensions.**

- Vary `PT[1]` (axis ion temperature) over
  `{0.7, 1.0, 1.5}` keV as a single-axis warm-up before
  T3 (which extends this to a 2-axis `PT[1] × PN[1]`
  sweep). `RIPS` looks like an obvious alternative
  single-axis knob, but the BPSD broker silently
  overwrites it — see T3's gotcha section below.
- Compare against a `MODELG=2` analytic equilibrium
  (no eqdata file needed). `MODELG=2` is the only mode
  in which user-set geometry knobs survive into the
  transport loop.

## T3 — `PT[1] × PN[1]` parameter sweep with heatmap

**Goal.** Run a 3×3 grid over axis ion temperature ×
axis ion density, then plot the resulting `WPT` field as
a heatmap. The pattern follows {doc}`applications` §2
(the `sweep()` wrapper) but is inlined here because the
array-element subscript syntax (`PT[1]`, `PN[1]`) does
not pass through `set_params(**kwargs)`.

**Why these axes — explicit gotcha.** Three intuitive
sweep axes a reader might try first all fail silently
under the ITER01 fixture's `MODELG=3`:

- **`RR × BB`** (geometry sweep). The BPSD broker pull
  overwrites `RR`/`RA`/`BB`/`RIP`/`RKAP`/`RDLT` from the
  loaded equilibrium device on the first `tr.run(...)`
  call, clobbering any user `set_param("RR", ...)`.
- **`RIPS × RIPE`** (plasma-current ramp sweep). The
  same BPSD pull recalibrates `RIPS`/`RIPE` from the
  metric-derived current; user overrides are
  overwritten.
- **`PNBTOT × <anything>`** (NBI total-power sweep).
  `PNBTOT` is the actual NB amplitude in MW but is
  **not** in the tr parameter registry —
  `set_param("PNBTOT", ...)` raises `INVALID`. The
  visible knob `PNBR0` looks tempting but is the radial
  *position* of NB deposition in metres, not an
  amplitude.

`PT[1]` and `PN[1]` survive: `tr_prof` reads `PN`/`PT`
to build the radial profile arrays `RN`/`RT`; the BPSD
plasma pull writes only `RN`/`RT` (not `PN`/`PT`); and
`tr_set_metric` does not touch the profile parameter
arrays. `WPT` is the total stored plasma energy,
approximately `Σ_s ∫(3/2) n_s T_s dV` over all bulk
species (electrons + ions; `MDLUF=0` in this fixture so
the fast-particle tail is zero), so the heatmap has a
clean physical interpretation.

**Array-element subscript syntax.** `tr.set_param("PT[1]", 1.0)`
is the canonical form for setting array element 1 of
`PT`. The `[idx]` part is parsed by the registry helper
`parse_array_subscript` and routed to the right Fortran
`CASE` block. The same applies to `PN`, `PNS`, `PTS`,
and the other registered array parameters.

```python
from trlib import Trlib
from trlib.tests.fixtures import tr_iter01_params

PT1_VALUES = [0.7, 1.0, 1.5]   # keV — axis ion temperature
PN1_VALUES = [0.5, 0.7, 1.0]   # 10^20 m^-3 — axis ion density

# 3x3 grid: outer index runs PT[1], inner runs PN[1].
results: list[dict] = []
for pt1 in PT1_VALUES:
    for pn1 in PN1_VALUES:
        with Trlib() as tr:
            tr_iter01_params.apply(tr)
            tr.set_param("PT[1]", pt1)
            tr.set_param("PN[1]", pn1)
            tr.run(ntmax=20)
            state = tr.get_state()
        results.append({
            "PT1": pt1,
            "PN1": pn1,
            "WPT": state.scalars["WPT"],
        })
```

**Plot.** matplotlib is an optional dependency
(`pip install matplotlib`). The script gracefully
degrades to a printed table if matplotlib is
unavailable:

```python
import numpy as np

wpt_grid = np.array([r["WPT"] for r in results]).reshape(
    len(PT1_VALUES), len(PN1_VALUES)
)

try:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    im = ax.imshow(wpt_grid, origin="lower", aspect="auto")
    ax.set_xticks(range(len(PN1_VALUES)))
    ax.set_xticklabels([f"{v:.2f}" for v in PN1_VALUES])
    ax.set_yticks(range(len(PT1_VALUES)))
    ax.set_yticklabels([f"{v:.2f}" for v in PT1_VALUES])
    ax.set_xlabel("PN[1] (10^20 m^-3)")
    ax.set_ylabel("PT[1] (keV)")
    fig.colorbar(im, label="WPT (MJ)")
    fig.savefig("tr_pt1_pn1_sweep.png")
    print("Saved tr_pt1_pn1_sweep.png")
except ImportError:
    print("matplotlib not available; printing table instead.")
    print(f"WPT shape: {wpt_grid.shape}")
    header = "  ".join(f"PN[1]={v:5.2f}" for v in PN1_VALUES)
    print(f"            {header}")
    for i, pt1 in enumerate(PT1_VALUES):
        row = "  ".join(f"{v:9.3f}" for v in wpt_grid[i])
        print(f"PT[1]={pt1:5.2f}  {row}")
```

**Expected output.** Concrete `WPT` values depend on the
build configuration; run locally to populate:

```text
WPT shape: (3, 3); values placeholder — run locally to populate
```

**Extensions.**

- Pipe results into a `pandas.DataFrame` for richer
  tabular post-processing.
- Parallelise with `multiprocessing.Pool` (per the
  singleton constraint in {doc}`faq` Q4, parallelisation
  works because each process gets its own independent
  `Trlib` instance).
- For shape-optimisation studies (`RKAP × RDLT` or
  `RR × BB`), switch to `MODELG=2` (analytic
  equilibrium) so geometry knobs survive — under
  `MODELG=3` the BPSD pull would clobber them. For
  NBI-amplitude sweeps, `PNBTOT` first needs registry
  registration (a planned change tracked outside this
  tutorial).

## What's next

- **T2 (JET-like)** is deferred — no `eqdata.JET`
  fixture ships with the repo. D2 will revisit using
  either an analytic-equilibrium JET-shape setup
  (`MODELG=2`) or a new fixture.
- **T4** (Python wrapper ↔ `tr2` equivalence at 1e-10),
  **T5** (`tot`-coupled run), and **T6** (numerical
  blow-up debugging) are reserved for D2.
- For an executable end-to-end form of T1, see the
  `tr-quickstart.ipynb` notebook in the chapter's
  shared notebooks.
````

- [ ] **Step 2: Verify the file was written and is well-formed MyST**

Run: `wc -l docs/sphinx/modules/tr/en/tutorials.md`
Expected: ~190 lines.

Run: `grep -c "^## " docs/sphinx/modules/tr/en/tutorials.md`
Expected: 3 (T1, T3, What's next).

Run: `grep -c "{doc}" docs/sphinx/modules/tr/en/tutorials.md`
Expected: 6 cross-links matching the spec acceptance criterion 12 (`hello-world`, `parameter-setting`, `applications`, `input-files`, `applications` again in T3, `faq`).

- [ ] **Step 3: Syntax-check the Python code blocks**

Extract each fenced ` ```python ` block to a tempfile and run `python3 -m py_compile` on it. The blocks intentionally rely on `Trlib`/`tr_iter01_params`/`numpy`/`matplotlib` which may not all be importable in the build environment, so do NOT execute them — only compile.

```bash
mkdir -p /tmp/tr-tutorials-en-check
awk '/^```python$/{p=1; n++; f=sprintf("/tmp/tr-tutorials-en-check/block_%02d.py", n); next} /^```$/{p=0} p{print > f}' docs/sphinx/modules/tr/en/tutorials.md
for f in /tmp/tr-tutorials-en-check/block_*.py; do
  echo "=== $f ==="
  python3 -m py_compile "$f" && echo PASS || echo FAIL
done
rm -rf /tmp/tr-tutorials-en-check
```

Expected: every block PASSes `py_compile`. (Imports fail at runtime would not be caught here — that is intentional; we are checking syntax only.)

- [ ] **Step 4: Commit**

```bash
git add docs/sphinx/modules/tr/en/tutorials.md
git commit -m "$(cat <<'EOF'
docs(tr): add tutorials.md (en) — D1 with T1 + T3

T1: ITER-like single run using the shipped eqdata.ITER01 fixture
(MODELG=3 / EQRTSK / TASK/EQ binary). Geometry comes from the
equilibrium load via BPSD; only non-geometry knobs are user-set.

T3: PT[1] × PN[1] parameter sweep with matplotlib heatmap. Page
includes an explicit gotcha section enumerating three rejected
sweep axes (RR×BB, RIPS×*, PNBTOT×*) with their failure mechanism,
because under MODELG=3 the BPSD broker pull silently clobbers
geometry/current overrides.

D2 will cover T2 (JET-like, needs fixture decision), T4 (tr2
equivalence), T5 (tot-coupled), T6 (numerical blow-up).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Create `docs/sphinx/modules/tr/ja/tutorials.md`

**Files:**
- Create: `docs/sphinx/modules/tr/ja/tutorials.md`

- [ ] **Step 1: Write the file**

Full content (write verbatim; code blocks identical to en, prose translated):

````markdown
# チュートリアル

```{admonition} このページの位置づけ
:class: tip

end-to-end の例題を 2 つ扱います. {doc}`hello-world`,
{doc}`parameter-setting`, {doc}`applications` を読了
している前提です. マルチシナリオ・チュートリアル
シリーズの **D1** では:

- **T1** — `eqdata.ITER01` fixture を使った
  ITER ライクな単一実行
- **T3** — `PT[1] × PN[1]` のパラメータスイープを
  heatmap として可視化

の 2 つを扱います. 残りの 4 つ (T2 JET ライク,
T4 `tr2` 同等性 (1e-10), T5 `tot` 結合実行,
T6 数値破綻のデバッグ) は D2 へ繰り越し.
```

## T1 — ITER ライク単一実行シナリオ

**目的.** リポジトリ同梱の `eqdata.ITER01` 平衡 fixture
(TASK/EQ binary 形式, `MODELG=3` 経由で `EQRTSK`
リーダにロードされる) を使って 100 ステップ走らせ,
結果の `TrState` を読み取るところまでを順に体験します.

**準備.** fixture ファイルは
`python/eqlib/tests/fixtures/eqdata.ITER01` にあります.
C ABI の `KNAMEQ` には 80 バイト制限があり
({doc}`input-files` 参照), 絶対パスは入りきらない
ことが多いので, 該当ディレクトリへ `chdir` して
ファイル名だけ渡す, というのが定石です:

```python
import os
os.chdir("python/eqlib/tests/fixtures")
```

**スクリプト.** geometry 以外のパラメータはすべて
fixture `python/trlib/tests/fixtures/tr_iter01_params.py`
から適用されます (`MODELG=3`, `NSMAX=4`,
`KNAMEQ="eqdata.ITER01"`, `RIPS`/`RIPE`, プラズマ
プロファイル配列 `PN`/`PNS`/`PT`/`PTS`, 加熱源
スカラーなど). geometry (`RR`, `RA`, `RKAP`, `RDLT`,
`BB`) は最初の `tr.run(...)` 呼び出しの中で TASK/EQ
binary ファイルから読み込まれます (
`tr_run → tr_prep → tr_set_metric → eq_load + tr_bpsd_get`
の流れ) — スクリプト側で明示的に指定する必要はあり
ません.

```python
import os
from trlib import Trlib
from trlib.tests.fixtures import tr_iter01_params

os.chdir("python/eqlib/tests/fixtures")  # KNAMEQ is 80 bytes

with Trlib() as tr:
    tr_iter01_params.apply(tr)
    tr.validate()
    tr.run(ntmax=100)
    state = tr.get_state()

print(f"WPT   = {state.scalars['WPT']}")
print(f"BETAN = {state.scalars['BETAN']}")
print(f"Q0    = {state.scalars['Q0']}")
print(f"TAUE1 = {state.scalars['TAUE1']}")
```

**期待出力.** 具体的な数値はビルド構成に依存しドリフト
する可能性があるので, 実行して各自で確かめてください:

```text
WPT   = ...
BETAN = ...
Q0    = ...
TAUE1 = ...
```

**拡張案.**

- `PT[1]` (中心イオン温度) を `{0.7, 1.0, 1.5}` keV
  で動かしてみる — T3 の 2 軸スイープ
  (`PT[1] × PN[1]`) への 1 軸ウォームアップとして
  位置づけられます. (一見 `RIPS` も自然な単軸候補に
  見えますが BPSD ブローカーが上書きするため効か
  ない — T3 の落とし穴セクション参照.)
- `MODELG=2` の解析平衡 (eqdata 不要) と比較してみる.
  ユーザー指定の geometry 値が transport loop まで
  生き残るのは `MODELG=2` のみです.

## T3 — `PT[1] × PN[1]` スイープと heatmap

**目的.** 中心イオン温度 × 中心イオン密度の 3×3
グリッドを走らせ, 結果の `WPT` 場を heatmap として
プロットします. パターン自体は {doc}`applications`
§2 のスイープラッパーに従いますが, 配列要素の
添字構文 (`PT[1]`, `PN[1]`) は
`set_params(**kwargs)` を通せないので, ここでは
ループをインラインで書き下します.

**なぜこの軸 — 落とし穴の明示.** ITER01 fixture の
`MODELG=3` 下では, 直感的なスイープ候補 3 つは
いずれも黙って効かなくなります:

- **`RR × BB`** (geometry スイープ): 最初の
  `tr.run(...)` 呼び出しで BPSD ブローカーのプル
  が `RR`/`RA`/`BB`/`RIP`/`RKAP`/`RDLT` を平衡
  デバイスから上書きするため,
  `set_param("RR", ...)` は no-op になります.
- **`RIPS × RIPE`** (プラズマ電流ランプスイープ):
  同じ BPSD プルが `RIPS`/`RIPE` をメトリク由来の
  電流値で再校正するため, ユーザー上書きは消えます.
- **`PNBTOT × <anything>`** (NBI 総出力スイープ):
  `PNBTOT` は本来の NB 振幅 (MW 単位) ですが, tr の
  パラメータレジストリに **未登録** です —
  `set_param("PNBTOT", ...)` は `INVALID` を投げます.
  fixture で見える `PNBR0` は NBI 堆積の半径 *位置*
  (m) で振幅ではない, という罠もあります.

`PT[1]` と `PN[1]` は生き残ります: `tr_prof` が
`PN`/`PT` を読んで半径方向プロファイル `RN`/`RT` を
構築し, BPSD のプラズマプルは `RN`/`RT` のみに書き
込み (`PN`/`PT` には触らず), `tr_set_metric` も
プロファイルパラメータ配列には触れません. `WPT` は
プラズマ蓄積エネルギー総量で, 概ね
`Σ_s ∫(3/2) n_s T_s dV` (バルク粒子種すべて, 電子 +
イオン; この fixture では `MDLUF=0` なので高速粒子
テイル成分はゼロ), よって heatmap の物理的意味は
明快です.

**配列要素の添字構文.** `tr.set_param("PT[1]", 1.0)`
が配列 `PT` の 1 番目要素をセットする標準形式です.
`[idx]` の部分はレジストリのヘルパ
`parse_array_subscript` でパースされ, 該当する
Fortran `CASE` ブロックに振り分けられます. `PN`,
`PNS`, `PTS` など他の登録配列パラメータでも同じ
書き方が通ります.

```python
from trlib import Trlib
from trlib.tests.fixtures import tr_iter01_params

PT1_VALUES = [0.7, 1.0, 1.5]   # keV — axis ion temperature
PN1_VALUES = [0.5, 0.7, 1.0]   # 10^20 m^-3 — axis ion density

# 3x3 grid: outer index runs PT[1], inner runs PN[1].
results: list[dict] = []
for pt1 in PT1_VALUES:
    for pn1 in PN1_VALUES:
        with Trlib() as tr:
            tr_iter01_params.apply(tr)
            tr.set_param("PT[1]", pt1)
            tr.set_param("PN[1]", pn1)
            tr.run(ntmax=20)
            state = tr.get_state()
        results.append({
            "PT1": pt1,
            "PN1": pn1,
            "WPT": state.scalars["WPT"],
        })
```

**プロット.** matplotlib はオプション依存です
(`pip install matplotlib`). 無い場合はテーブル
出力に gracefully degrade します:

```python
import numpy as np

wpt_grid = np.array([r["WPT"] for r in results]).reshape(
    len(PT1_VALUES), len(PN1_VALUES)
)

try:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    im = ax.imshow(wpt_grid, origin="lower", aspect="auto")
    ax.set_xticks(range(len(PN1_VALUES)))
    ax.set_xticklabels([f"{v:.2f}" for v in PN1_VALUES])
    ax.set_yticks(range(len(PT1_VALUES)))
    ax.set_yticklabels([f"{v:.2f}" for v in PT1_VALUES])
    ax.set_xlabel("PN[1] (10^20 m^-3)")
    ax.set_ylabel("PT[1] (keV)")
    fig.colorbar(im, label="WPT (MJ)")
    fig.savefig("tr_pt1_pn1_sweep.png")
    print("Saved tr_pt1_pn1_sweep.png")
except ImportError:
    print("matplotlib not available; printing table instead.")
    print(f"WPT shape: {wpt_grid.shape}")
    header = "  ".join(f"PN[1]={v:5.2f}" for v in PN1_VALUES)
    print(f"            {header}")
    for i, pt1 in enumerate(PT1_VALUES):
        row = "  ".join(f"{v:9.3f}" for v in wpt_grid[i])
        print(f"PT[1]={pt1:5.2f}  {row}")
```

**期待出力.** 具体的な `WPT` 値はビルド構成に依存
するため, 実行して各自で確かめてください:

```text
WPT shape: (3, 3); values placeholder — run locally to populate
```

**拡張案.**

- 結果を `pandas.DataFrame` に流して表形式で扱ったり,
  よりリッチなプロットに繋げる.
- `multiprocessing.Pool` で並列化する ({doc}`faq`
  Q4 のシングルトン制約に従い, 各プロセスは独立した
  `Trlib` インスタンスを持つので問題なく並列化
  できます).
- 形状最適化研究 (`RKAP × RDLT` や `RR × BB`) は
  `MODELG=2` (解析平衡) に切り替えれば geometry が
  生き残ります — `MODELG=3` だと BPSD プルが上書き
  します. NBI 振幅スイープは, 先に `PNBTOT` を
  レジストリ登録する必要があります (本チュートリアル
  とは別管理の作業).

## 次のステップ

- **T2 (JET ライク)** は deferred — `eqdata.JET`
  fixture が repo に同梱されていないため. D2 で
  解析平衡 JET 形状 (`MODELG=2`) または新規 fixture
  により再検討します.
- **T4** (Python ラッパー ↔ `tr2` の 1e-10 同等性),
  **T5** (`tot` 結合実行), **T6** (数値破綻の
  デバッグ) も D2 で扱います.
- T1 の実行可能形式は chapter の shared notebooks に
  ある `tr-quickstart.ipynb` を参照してください.
````

- [ ] **Step 2: Verify ja file structure parity with en**

Run:
```bash
diff <(grep -E "^(#|##|```)" docs/sphinx/modules/tr/en/tutorials.md) \
     <(grep -E "^(#|##|```)" docs/sphinx/modules/tr/ja/tutorials.md)
```

Expected: differences only on `#`/`##` heading lines (because the en/ja titles are different language); fence-block (`` ``` ``) lines should match 1:1 in count and order. If a fence-block is missing or extra in ja, fix the ja file.

Run:
```bash
diff <(awk '/^```python$/,/^```$/' docs/sphinx/modules/tr/en/tutorials.md) \
     <(awk '/^```python$/,/^```$/' docs/sphinx/modules/tr/ja/tutorials.md)
```

Expected: empty output. Code blocks must be byte-identical between en and ja.

- [ ] **Step 3: Syntax-check ja Python code blocks**

```bash
mkdir -p /tmp/tr-tutorials-ja-check
awk '/^```python$/{p=1; n++; f=sprintf("/tmp/tr-tutorials-ja-check/block_%02d.py", n); next} /^```$/{p=0} p{print > f}' docs/sphinx/modules/tr/ja/tutorials.md
for f in /tmp/tr-tutorials-ja-check/block_*.py; do
  echo "=== $f ==="
  python3 -m py_compile "$f" && echo PASS || echo FAIL
done
rm -rf /tmp/tr-tutorials-ja-check
```

Expected: every block PASSes.

- [ ] **Step 4: Commit**

```bash
git add docs/sphinx/modules/tr/ja/tutorials.md
git commit -m "$(cat <<'EOF'
docs(tr): add tutorials.md (ja) — bilingual counterpart of D1

Code blocks byte-identical to the en page; prose translated.
Same T1 + T3 coverage, same gotcha section enumerating the
three rejected sweep axes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Insert `tutorials` into en/index.md User-guide toctree

**Files:**
- Modify: `docs/sphinx/modules/tr/en/index.md` (line 46 area, between `applications` and the closing fence)

- [ ] **Step 1: Edit the toctree**

Use Edit tool with this exact replacement:

```
old_string:
applications
```

```
new_string:
applications
tutorials
```

Note: `applications` appears only once in the file (in the User-guide toctree); the global Edit will be unique.

- [ ] **Step 2: Verify**

Run:
```bash
grep -n "applications\|tutorials" docs/sphinx/modules/tr/en/index.md
```

Expected: `applications` then `tutorials` on consecutive lines inside the User-guide `{toctree}` block.

- [ ] **Step 3: Commit**

```bash
git add docs/sphinx/modules/tr/en/index.md
git commit -m "$(cat <<'EOF'
docs(tr): wire tutorials.md into en User-guide toctree

Inserted after applications; reading order is hello-world →
parameters → parameter-setting → input-files → state →
context-manager → faq → applications → tutorials.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Insert `tutorials` into ja/index.md User-guide toctree

**Files:**
- Modify: `docs/sphinx/modules/tr/ja/index.md` (mirror of Task 3)

- [ ] **Step 1: Edit the toctree**

Use Edit tool with this exact replacement:

```
old_string:
applications
```

```
new_string:
applications
tutorials
```

- [ ] **Step 2: Verify**

Run:
```bash
grep -n "applications\|tutorials" docs/sphinx/modules/tr/ja/index.md
```

Expected: same structure as en/index.md after Task 3.

- [ ] **Step 3: Commit**

```bash
git add docs/sphinx/modules/tr/ja/index.md
git commit -m "$(cat <<'EOF'
docs(tr): wire tutorials.md into ja User-guide toctree

Mirror of the en change; same reading order.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Local Sphinx render check (best-effort)

**Files:** none modified.

- [ ] **Step 1: Attempt the build**

```bash
make -C docs/sphinx html 2>&1 | tail -40
```

Two possible outcomes:

1. **Build succeeds locally** (rare; requires `furo` theme installed). Verify the User-guide section in the generated HTML lists `tutorials` after `applications`, and the `{doc}` cross-links resolve. Open `docs/sphinx/_build/html/modules/tr/en/tutorials.html` in a browser if available.

2. **Build fails locally** (typical; furo not installed). Expected error mentions `theme.conf` or `furo`. CI will do the full broken-ref check on push. Document the failure mode but do not block.

- [ ] **Step 2: Recovery if build fails for non-furo reasons**

If the failure mentions a missing `{doc}` target, an unparsable MyST directive, or a duplicate label, that IS blocking — fix the offending file (likely tutorials.md) and retry from Task 5 Step 1.

- [ ] **Step 3: Note the result**

No commit needed for this task. It is a pre-push verification, not a code change.

---

### Task 6: Pre-push gate — 2 reviewers + REVIEW_OK + push

**Files:** none modified by this task.

- [ ] **Step 1: Run pytest sanity check**

Per `CLAUDE.md` pre-push gate, run pytest with the standard flags. For doc-only changes, the relevant test surface is empty, but a smoke run on a small subset confirms no inadvertent breakage:

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
pytest python/trlib/tests/test_property_boundary.py --forked --timeout=120 --timeout-method=signal 2>&1 | tail -20
```

Expected: PASS or SKIP (pre-existing). Doc changes should not affect Python tests at all.

- [ ] **Step 2: Launch 2 reviewers in parallel**

Single message with two `Agent` calls:

```
Agent 1 (in-house code-reviewer):
  subagent_type: "feature-dev:code-reviewer"
  prompt: "Review the diff since commit 029abe4c on branch
    chore/pre-push-hook-worktree-compat. Four commits expected:
    en/tutorials.md, ja/tutorials.md, en/index.md, ja/index.md.
    Acceptance criteria are in
    docs/superpowers/specs/2026-05-04-tr-tutorials-d1-design.md §9.
    Focus on: (a) factual accuracy of fixture parameter list and
    line citations, (b) presence of the gotcha section enumerating
    RR×BB / RIPS×* / PNBTOT×* with their failure mechanism,
    (c) no concrete numeric expected-output values, (d) PEP 604/585
    builtins (no `from typing import`, no capital `List`/`Dict`),
    (e) bilingual parity (code blocks byte-identical, prose
    translated), (f) toctree insertion is correct in both
    index.md files, (g) all {doc} cross-links resolve. Report
    HIGH/MED findings."

Agent 2 (codex:codex-rescue):
  subagent_type: "codex:codex-rescue"
  prompt: same as Agent 1, asking for an independent review.
```

- [ ] **Step 3: Address findings**

For any HIGH/MED finding, edit the offending file and amend with a new commit (do NOT use `git commit --amend` per `CLAUDE.md`). LOW findings: judgment call — fix if cheap.

After fixes, repeat Step 2 with the new HEAD until both reviewers report no HIGH and no MED.

- [ ] **Step 4: Write REVIEW_OK marker**

```bash
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
```

- [ ] **Step 5: Push**

```bash
git push origin chore/pre-push-hook-worktree-compat
```

The pre-push hook reads the marker and lets the push through. If the hook complains about a missing marker, re-check Step 4 used the current HEAD SHA.

---

## Spec coverage map

| Spec acceptance criterion | Implemented by |
|---|---|
| 1. en/tutorials.md exists with §3.1, §3.2, §3.3 | Task 1 |
| 2. ja counterpart exists, structurally aligned | Task 2 |
| 3. Both index.md insert tutorials after applications | Tasks 3, 4 |
| 4. §3.1 ITER params match tr_iter01_params.py byte-for-byte | Task 1 (the page references `tr_iter01_params.apply(tr)` and lists the highlights — exact values stay in the fixture, so "byte-for-byte" reduces to "the page does not invent new values") |
| 5. eqdata.ITER01 path + 80-byte KNAMEQ caveat | Task 1 (Set-up paragraph) |
| 6. T3 cross-links {doc}`applications` for sweep pattern | Task 1 (T3 Goal paragraph mentions §2) |
| 7. T3 code uses PEP 604/585 builtins | Task 1 (`list[dict]` in the code block, no typing imports) |
| 8. matplotlib gracefully optional | Task 1 (try/except ImportError) |
| 9. T3 sweep axes are PT[1]×PN[1]; gotcha enumerates RR×BB/RIPS×*/PNBTOT×* | Task 1 (gotcha subsection) |
| 10. T1 + T3 use placeholder text, no concrete numerics | Task 1 (`...` and "values placeholder") |
| 11. §3.3 mentions T2/T4/T5/T6 as D2 follow-up | Task 1 (What's next section) |
| 12. All `{doc}` cross-references resolve | Task 5 (CI) + Task 6 (reviewers) |
| 13. Both reviewers report no HIGH findings | Task 6 |

---

## Self-review checklist

- [x] **Spec coverage:** all 13 criteria mapped above.
- [x] **Placeholder scan:** no TBD / TODO / "implement later"; all code shown verbatim; all commit messages drafted; all commands exact.
- [x] **Type consistency:** `PT1_VALUES` / `PN1_VALUES` named consistently between code blocks; `tr_iter01_params.apply(tr)` invocation identical in T1 and T3.
- [x] **Discipline:** doc-only change. No pytest expectations beyond the pre-push smoke run. No code under `python/`, `tr/`, `eq/`, `bpsd*` modified.
