# `wr` — 波動 ray tracing

```{admonition} この章で学ぶこと
:class: tip

TASK/WR (**幾何光学レイトレース** ソルバ: ECRH/ECCD/LH などの RF 加熱と
電流駆動の解析) を Python から呼ぶ `wrlib` の使い方を学びます. 共有ライブ
ラリのビルド, 最短 hello-world, 103 個の登録パラメータ (全モジュール中で
最多), レイ軌跡 + 吸収プロファイル出力, 4 層テストまでカバーします.
```

## 概要 — `wr` は何をする

**TASK/WR** はトカマクプラズマ中の **電磁波 (RF) の伝搬** を解くソルバです.
プラズマ中の屈折率テンソルから決まる ray equation を Hamiltonian 形式で
積分し, **どこで波が吸収されるか** を求めます.

`tr` / `ti` / `fp` と違って **時間発展せず**, **空間方向の積分** を行います:

- 入力: プラズマ平衡 + 入射波の条件 (周波数, 位置, 波数ベクトル, ビーム形状)
- 計算: ray equation を `NSTPMAX` ステップまで積分
- 出力: レイ軌跡 + 半径方向のパワー堆積プロファイル

主な用途:

- **ECRH/ECCD** (電子サイクロトロン共鳴加熱・電流駆動)
- **LH** (低域混成波) のパワー堆積位置解析
- **fast wave / Alfvén wave** など他の RF 加熱方式

得られる主な量:

- スカラー (4 個): `pos_pwrmax_rs`, `pwrmax_rs`, `pos_pwrmax_rl`, `pwrmax_rl`
- レイ別: `nstp_end[i]`, `pos_pwrmax_*_nray[i]`, `pwrmax_*_nray[i]`,
  `rays_end[i]`
- プロファイル: `pos_nrs[k]`, `pwr_nrs[k]`, `pos_nrl[k]`, `pwr_nrl[k]`

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

1. {doc}`build` — 共有ライブラリをビルド
2. {doc}`hello-world` — 5 行 + 1 本のレイトレース
3. {doc}`parameters` — 103 パラメータの完全リスト
4. {doc}`parameter-setting` — 単一レイ vs 複数レイの設定方法
5. {doc}`state` — レイ軌跡 + 吸収プロファイル
6. {doc}`context-manager` — 一般的な `with` 文の意味と落とし穴

困ったときは {doc}`faq` を. API の完全仕様は {doc}`api-reference`.
入力 ↔ 出力の対応関係は {doc}`appendix-sensitivity` へ.

## `tr`/`ti`/`fp` との違い (要約)

| | `tr`/`ti` | `fp` | `wr` |
|---|---|---|---|
| **方程式** | 流体 + 補助物理 | Fokker-Planck (5D) | **ray equation** |
| **時間発展** | あり | あり | **なし** (空間積分) |
| **`run` 引数** | `ntmax` | `ntmax` | **`nray_request`** |
| **出力** | プロファイル | モーメント | **レイ軌跡 + 吸収位置** |
| **登録パラメータ数** | ~30/77 | 55 | **103** |

## `wr` と `wrx` の関係

`wrx` は `wr` の **拡張版** で beam tracing オプションを持ちます.

- `wr`: ペンシルビーム (geometric optics). ビーム広がりは `NRAYMAX` 本のレイで近似
- `wrx`: 各レイにビーム形状 (曲率・幅) を持たせて解析的に展開

不明な場合は **まず `wr` で十分**, 結果が荒すぎたら `wrx` を検討
({doc}`faq` Q7).
