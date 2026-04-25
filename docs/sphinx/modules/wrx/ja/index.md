# `wrx` — 波動 ray tracing (拡張版)

```{admonition} この章で学ぶこと
:class: tip

TASK/WRX (**beam tracing** ソルバ: `wr` の拡張版で, 各レイにビーム形状
(曲率・幅) を持たせて集束ビームの伝搬を解析的に展開) を Python から呼ぶ
`wrxlib` の使い方を学びます. 共有ライブラリのビルド, 最短 hello-world,
70 個の登録パラメータ, beam tracing 固有のビーム形状指定, 粒子種別吸収
出力, 4 層テストまでカバーします.
```

## 概要 — `wrx` は何をする

**TASK/WRX** は `wr` (幾何光学レイトレース) を拡張し, **ビーム形状**
(曲率テンソル + 幅) をレイごとに追跡する **beam tracing** ソルバです.

`wr` との違い:

| | `wr` (geometric optics) | `wrx` (beam tracing) |
|---|---|---|
| レイの幅 | なし (ペンシルビーム) | **あり** (Gaussian) |
| ビーム広がりの表現 | 多数のレイで近似 (NRAYMAX=10–50) | **1 本のレイで解析的展開** |
| 計算コスト (同精度) | 高 | **低** |
| 集束ビームの精度 | 劣 | **優** |

主な用途:

- **ITER Upper/Equatorial Launcher** などの集束 ECRH ビーム
- **LH coupler** 出力の beam 伝搬
- **gyrotron ビーム** の焦点追跡 + デフォーカス解析

得られる主な量:

- スカラー: `pwr_tot` (全レイ合計吸収パワー)
- レイ別: `nstp_end[i]`, `pwr_nray[i]`
- 粒子種別: `pwr_nsa[isa]` (どの種がどれだけ吸収したか)
- プロファイル: `pos_nrs[k]`, `pos_nrl[k]`

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

1. {doc}`build` — 共有ライブラリをビルド
2. {doc}`hello-world` — 単一レイで beam tracing
3. {doc}`parameters` — 70 パラメータ (ビーム形状 `RCURVAIN`/`RBRADAIN` 含む)
4. {doc}`parameter-setting` — 単一レイも配列形式で指定
5. {doc}`state` — `pwr_tot` + `pwr_nray` + `pwr_nsa`
6. {doc}`context-manager` — 一般的な `with` 文の落とし穴

困ったときは {doc}`faq` を. API の完全仕様は {doc}`api-reference`.
入力 ↔ 出力の対応関係は {doc}`appendix-sensitivity` へ.

## `wr` と `wrx` の使い分け

| 目的 | 推奨 |
|---|---|
| 高速な概算 (ピーク位置) | `wr` |
| 集束ビームで精密な吸収プロファイル | **`wrx`** |
| 多数レイでビーム近似 | `wr` (NRAYMAX=10–50) |
| 単一レイでビーム追跡 | **`wrx`** (NRAYMAX=1) |
| 粒子種別吸収 (`pwr_nsa`) | **`wrx`** (`wr` にはない) |

迷ったら **まず `wr` で十分**, 結果が荒すぎたら `wrx` を検討.
