# `eq` — MHD 平衡

```{admonition} この章で学ぶこと
:class: tip

TASK/EQ (**MHD 平衡** ソルバ: EQDSK 形式の平衡データ, または解析プロファ
イルを入力に ψ サーフェスと派生量を計算) を Python から呼ぶ `eqlib`
の使い方を学びます. `tr` と異なり `eq` は **時間発展を持たない**
モジュールで, `run()` の引数は `mode` (動作モード) です. また,
**6 番目** の C ABI `eq_set_param_str` を持ち, `KNAMEQ` 等の文字列
パラメータ専用 API があります.
```

## 概要 — `eq` は何をする

**TASK/EQ** はトカマクの **MHD 平衡** を解くモジュールです. 2 つの入り口を
持ちます:

- **`run(mode=0)`** — 解析的 Grad-Shafranov 解 (`EQCALC` + `EQCALQ`).
  圧力プロファイル係数 (`PP*`), 電流プロファイル係数 (`PJ*`),
  $F(\psi)$ 係数 (`FF*`) を与えて解析的に解きます.
  `MODELG=2` (既定) で使用. ファイル不要.
- **`run(mode=1)`** — EQDSK 形式 (G-EQDSK) の平衡データファイル読み込み
  (`equnit::eq_load`). `MODELG ∈ {3, 5, 8}` + `KNAMEQ` ファイル名指定が必要.

両方とも出力としては磁気軸位置 (`raxis`, `zaxis`), 中心 q (`qaxis`),
表面 q (`qsurf`), プラズマ $\beta$ (`betat`, `betap`), プラズマ体積
(`pvol`) などのスカラーと, R-Z 格子, ψ-面プロファイル (`psips`, `ppps`,
`ttps`, `qqps`) を返します.

```{note}
PR #164/#165 でライブラリ / Python ラッパ / `validate()` API が揃い,
L-6 等価性ゲートを 1e-10 で通過済みです. `mode=0` (解析的経路) は
元 `eqx2` CLI の `R` (Run) コマンド相当で, ライブラリ化に伴って
復活させた経路です.
```

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

appendix-sensitivity
```

## 読みすすめ方

初めて触る場合は次の順序がおすすめです:

1. {doc}`build` — 共有ライブラリをビルドし, `import eqlib` できるようにする
2. {doc}`hello-world` — 解析モード (`mode=0`) と EQDSK モード (`mode=1`) の両方の最短例
3. {doc}`parameters` — どんな入力パラメータがあるか (登録パラメータ完全リスト)
4. {doc}`parameter-setting` — 入力パラメータ指定の 4 通り (スカラー / 配列 / **文字列** / `validate`)
5. {doc}`state` — `eq.get_state()` で取れる出力パラメータ・物理量の一覧
6. {doc}`context-manager` — `with` 文の意味と落とし穴
7. {doc}`quickstart` — 実行可能 notebook で一連の流れを体験

困ったときは {doc}`faq` を. API の完全仕様は {doc}`api-reference`.
入力 ↔ 出力の対応関係は {doc}`appendix-sensitivity` へ.

## `tr` との違い (要約)

| | `tr` (輸送) | `eq` (平衡) |
|---|---|---|
| **時間発展** | あり (`run(ntmax)`) | なし (`run(mode)`) |
| **C ABI 関数数** | 5 + `validate` | **6** + `validate` |
| **`set_param_str`** | (PR #172 で追加) | 設計初期から必須 |
| **必須パラメータ** | `KNAMEQ` (MODELG=3,5,7,8 のとき) | `KNAMEQ` (MODELG=3,5,8 のとき) |
| **代表的な出力** | `T`, `WPT`, `BETAN`, profiles[nrmax][nsmax] | `raxis`, `qaxis`, `betat`, profiles[npsmax] |
