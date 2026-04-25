# `fp` — Fokker-Planck

```{admonition} この章で学ぶこと
:class: tip

TASK/FP (**Fokker-Planck** ソルバ: 5D 位相空間で粒子分布関数を解く) を
Python から呼ぶ `fplib` の使い方を学びます. 共有ライブラリのビルド,
最短 hello-world, 55 個の登録パラメータ, モーメント出力,
`KNAMEQ` 文字列指定, 4 層テストまでカバーします.
```

## 概要 — `fp` は何をする

**TASK/FP** はトカマクプラズマの **Fokker-Planck 方程式** を解くソルバです.
`tr` / `ti` のような流体方程式 (温度・密度の発展) ではなく,
**粒子分布関数 $f(r, p, \theta, t)$ そのものを 5D 位相空間で離散化**
して時間発展させます.

主な用途:

- **NBI 起源高速イオン**の精密分布解析 (Maxwellian 仮定が破綻するケース)
- **波動駆動** (LH, ECCD) による電子分布変形と電流駆動効率
- **核融合 α 粒子**の減速過程
- **disruption 時のランナウェイ電子**の加速

得られる主な量 (モーメント):

- `RNT[isa][nr]` — 粒子数密度プロファイル (active species 別)
- `RWT[isa][nr]` — エネルギー密度プロファイル
- `RTT[isa][nr]` — 平均温度プロファイル
- `RJT[isa][nr]` — 電流密度プロファイル
- `RPCT[isa][nr]` — 衝突パワー授受
- `RPWT[isa][nr]` — 波動加熱パワー授受
- スカラー: `timefp` (シミュレーション時刻)

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
2. {doc}`hello-world` — 5D グリッドの最短セットアップ
3. {doc}`parameters` — 55 パラメータの完全リスト
4. {doc}`parameter-setting` — スカラー / 配列 / 文字列 (`KNAMEQ`) 指定
5. {doc}`state` — モーメント量の出力解説
6. {doc}`context-manager` — メモリ管理の重要性

困ったときは {doc}`faq` を. API の完全仕様は {doc}`api-reference`.
入力 ↔ 出力の対応関係は {doc}`appendix-sensitivity` へ.

## `tr`/`ti` との違い (要約)

| | `tr` (純粋輸送) | `ti` (統合輸送) | `fp` (Fokker-Planck) |
|---|---|---|---|
| **方程式** | 流体 (Maxwellian 仮定) | 流体 + 補助物理 | **分布関数 5D** |
| **C ABI** | 5 + str + validate | 5 | 6 (str あり) |
| **位相空間** | 1D (半径) | 1D (半径) | **5D** (r, p, θ, species, t) |
| **メモリ** | 低 | 中 | **高** |
| **用途** | 輸送モデル比較 | 実験再現 | 非熱平衡分布の精密解析 |
