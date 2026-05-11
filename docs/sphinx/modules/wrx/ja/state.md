# 出力されるパラメータ・物理量 (`WrxState`)

`wrx.get_state()` は `WrxState` dataclass を返します. beam tracing の
結果として取得できる量の全リストです.

## 次元情報 (dimension fields)

| フィールド | 意味 |
|---|---|
| `state.nraymax` | 実際にトレースされたレイの本数 |
| `state.nstpmax` | 実働の最大ステップ数 |
| `state.nsamax`  | active species (計算対象粒子種) 数 |
| `state.nsmax`   | 全粒子種数 |
| `state.nrsmax`  | minor radius プロファイル点数 |
| `state.nrlmax`  | major radius プロファイル点数 |
| `state.modelg`  | 使用した幾何モデル |
| `state.mdlwrq`  | 使用した質モード |

## スカラー量

`wrx` の `state.scalars` は **`pwr_tot` 1 個のみ** です.

| キー | 単位 | 意味 |
|---|---|---|
| `pwr_tot` | — | 全レイ合計の吸収パワー (規格化) |

```python
state.scalars["pwr_tot"]   # 総吸収パワー
```

全入射パワーに対する吸収比率を見るには, 各レイの初期パワー `UUIN[i]` と
この値を比較します.

## レイ別の出力

| フィールド | 型 | 意味 |
|---|---|---|
| `state.nstp_end[i]`  | int   | i 番目レイの終端ステップ番号 |
| `state.pwr_nray[i]`  | float | i 番目レイの吸収パワー |
| `state.pwr_nsa[isa]` | float | isa 番目 active species の吸収パワー |

各レイが最終的にどれだけパワーを落としたか (`pwr_nray`) と, どの粒子種が
それを吸収したか (`pwr_nsa`) を個別に取得できます.

## プロファイル量

| フィールド | 型 | 意味 |
|---|---|---|
| `state.pos_nrs[k]` | float | k 番目の minor radius サンプル位置 |
| `state.pos_nrl[k]` | float | k 番目の major radius サンプル位置 |

`wr` の `pwr_nrs[]`, `pwr_nrl[]` に相当するパワー堆積プロファイルは
実装依存 (`describe_state_schema` で確認). 詳細は {doc}`api-reference` を参照.

## 補助メソッド

```python
state.to_dict()   # JSON-ready dict (baseline 互換)
```

`to_dict()` の出力は `arrays`, `arrays2`, `scalars` の 3 層構造で, 比較用
`compare_metrics.py` に渡せます.

## `wr` の `WrState` との違い

| | `WrState` (wr) | `WrxState` (wrx) |
|---|---|---|
| **スカラー数** | 4 (pos/pwr の 2 軸 × 2) | **1** (pwr_tot) |
| **主要出力** | `rs`/`rl` プロファイル + レイ終端 | レイ別 + 種別の吸収 + プロファイル |
| **粒子種別吸収** | ない (`nraymax` のみ) | **`pwr_nsa[]` あり** |
| **ビーム形状出力** | なし | 内部に保持 (プロット用に取得可) |

`wrx` は粒子種別吸収プロファイルが取れるので, 「ECRH の何 % が電子を
加熱し, 何 % がイオンに逃げたか」のような解析に使えます.
