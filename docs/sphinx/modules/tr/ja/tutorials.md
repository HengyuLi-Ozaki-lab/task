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
  `set_param("RR", ...)` で指定した値は受理された後に
  上書きされます (実質 no-op).
- **`RIPS × RIPE`** (プラズマ電流ランプスイープ):
  同じ BPSD プルが `RIPS`/`RIPE` をメトリク由来の
  電流値で再校正するため, ユーザー上書きは消えます.
`PT[1]` と `PN[1]` は生き残ります: `tr_prof` が
`PN`/`PT` を読んで半径方向プロファイル `RN`/`RT` を
構築し, BPSD のプラズマプルは `RN`/`RT` のみに書き
込み (`PN`/`PT` には触らず), `tr_set_metric` も
プロファイルパラメータ配列には触れません. `WPT` は
プラズマ蓄積エネルギー総量で, 一般には
`WPT = Σ_s ∫(3/2) n_s T_s dV  +  WTAILT` —
バルクの和は全粒子種 (電子 + イオン) で,
`WTAILT` は高速粒子テイル成分です. この fixture では
`MDLUF=0` なので `WTAILT = 0` となり, heatmap は
バルク蓄積エネルギーを純粋に映し, 物理的意味は明快
です.

**配列要素の添字構文.** `tr.set_param("PT[1]", 1.0)`
が配列 `PT` の 1 番目要素をセットする標準形式です.
`[idx]` の部分はレジストリのヘルパ
`parse_array_subscript` でパースされ, 該当する
Fortran `CASE` ブロックに振り分けられます. `PN`,
`PNS`, `PTS` など他の登録配列パラメータでも同じ
書き方が通ります.

```python
import os
from trlib import Trlib
from trlib.tests.fixtures import tr_iter01_params

# Same cwd requirement as T1: KNAMEQ is bare "eqdata.ITER01"
# inside the fixture (80-byte limit), so we must run from the
# directory that holds the binary file.
os.chdir("python/eqlib/tests/fixtures")

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
  します. NBI 総電力は本 PR より `set_param("PNBTOT",
  <MW>)` で操作可能になりました.

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
