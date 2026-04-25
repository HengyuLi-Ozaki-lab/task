# TASK プラズマライブラリ

TASK 系プラズマ物理モジュール群 (`lib{eq,tr,ti,fp,wr,wrx,tot}api.so`) と,
それらを呼び出す薄い `ctypes` ベース Python ラッパのポータルです.

```{note}
本 Sphinx マニュアルは `docs/manual/task-library-manual.tex` の LaTeX 文書を
正本の座から置き換えるものです. LaTeX 版は 2026-04 時点で凍結し, 以降の
変更は本 Sphinx 側に反映します.
```

## モジュール一覧

::::{grid} 2 3 3 4
:gutter: 3

:::{grid-item-card} **tr** — 輸送計算
:link: ../../tr/ja/index.html

1 次元トカマク輸送シミュレーション. 密度・温度・電流・平衡プロファイルを
時間発展させます.
**状態:** 完成
:::

:::{grid-item-card} **eq** — MHD 平衡
:link: ../../eq/ja/index.html

MHD 平衡ソルバ. EQDSK や解析プロファイルから ψ-面幾何と派生量を計算.
**状態:** 完成
:::

:::{grid-item-card} **ti** — 統合輸送
:link: ../../ti/ja/index.html

輸送ソルバー `tr` と補助物理を結合する統合インタフェース.
**状態:** placeholder
:::

:::{grid-item-card} **fp** — Fokker-Planck
:link: ../../fp/ja/index.html

高速イオン・高エネルギー粒子の分布関数ソルバー.
**状態:** placeholder
:::

:::{grid-item-card} **wr** — 波動 ray tracing
:link: ../../wr/ja/index.html

RF 加熱・電流駆動の幾何光学 ray tracing.
**状態:** placeholder
:::

:::{grid-item-card} **wrx** — 波動 ray tracing (拡張版)
:link: ../../wrx/ja/index.html

`wr` に beam tracing を加えた拡張モジュール.
**状態:** placeholder
:::

:::{grid-item-card} **tot** — オーケストレータ
:link: ../../tot/ja/index.html

全モジュールを横断する実行を構成 (`eq` → `tr` / `ti` / `fp` / `wr` / `wrx`).
**状態:** placeholder
:::

::::

## 基礎

```{toctree}
:maxdepth: 2
:caption: 基礎

common/architecture
```

## 読者対象

本マニュアルは, Python または C ABI を通じて TASK モジュール群を
プログラムから呼び出したい研究者・エンジニアを対象とします. Python と
プラズマ物理用語に慣れていれば十分で, 旧来の `tr2` や対話メニューの
経験は不要です.

## 索引

* {ref}`genindex`
* {ref}`modindex`
