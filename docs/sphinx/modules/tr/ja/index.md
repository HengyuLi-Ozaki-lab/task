# `tr` — 輸送計算

```{admonition} この章で学ぶこと
:class: tip

TASK/TR (1 次元トカマク輸送シミュレーション) を Python から呼び出す
ライブラリ `trlib` の使い方を学びます. 共有ライブラリのビルド,
最短 hello-world (5 行), パラメータ設定 (4 通り — スカラー / 配列 /
文字列 / `validate()`), FAQ, そしてテスト実行までカバーします.
```

## 概要 — `tr` は何をする

**TASK/TR** は, トカマクや球状トカマクの **1 次元 (半径方向) 輸送シミュ
レーション** を行うモジュールです. 「プラズマの半径方向の分布が, 時間と
ともにどう変化するか」を, 粒子数・温度・電流・磁場の平衡を解きながら
追跡します.

得られる代表的な量:

- `RN[i][j]` — 半径点 $i$ での $j$ 番目の粒子種の密度
- `RT[i][j]` — 同じく温度
- `AJ[i]`    — 電流密度プロファイル
- `QP[i]`    — 安全係数 $q$ プロファイル
- スカラー: `T` (時間), `WPT` (蓄積エネルギー), `Q0` (中心 $q$),
  `BETAN` ($\beta_N$) など 13 種

Fortran 設計・パラメータレジストリの詳細は
[共通アーキテクチャ](../../../portal/ja/common/architecture.md) および `docs/tr-library/architecture.md`
を参照.

## 使い方ガイド

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

## リファレンス

```{toctree}
:maxdepth: 1

quickstart
api-reference
```

## 内部情報

```{toctree}
:maxdepth: 1

design
mcp
testing
```

## 付録

```{toctree}
:maxdepth: 1

appendix-mdlkai
appendix-sensitivity
```

## 読みすすめ方

初めて触る場合は次の順序がおすすめです:

1. {doc}`build` — 共有ライブラリをビルドし, `import trlib` できるようにする
2. {doc}`hello-world` — 5 行でプラズマを進める最短例
3. {doc}`parameters` — どんな入力パラメータがあるか (登録パラメータ完全リスト)
4. {doc}`parameter-setting` — 入力パラメータ指定の 4 通り (スカラー / 配列 / 文字列 / `validate`)
5. {doc}`state` — `tr.get_state()` で取れる出力パラメータ・物理量の一覧
6. {doc}`context-manager` — `with` 文の意味と落とし穴
7. {doc}`quickstart` — 実行可能 notebook で一連の流れを体験

困ったときは {doc}`faq` を. API の完全仕様は {doc}`api-reference`.
よりディープな話題は {doc}`appendix-mdlkai` (輸送モデル詳細) と
{doc}`appendix-sensitivity` (入力↔出力対応) へ.
