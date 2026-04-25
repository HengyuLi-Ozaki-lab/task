# 出力されるパラメータ・物理量 (`TiState`)

`ti.get_state()` は `TiState` dataclass を返します. これがシミュレーション
結果として取得できる量の全リストです. フィールドは `ti/ti_api.h` の
C 構造体 `ti_state_t` と対応します.

## 次元情報 (dimension fields)

| フィールド | 意味 |
|---|---|
| `state.nt`      | 時刻ステップカウンタ |
| `state.nrmax`   | 実働の半径点数 |
| `state.nsa_max` | active species (実働している粒子種) の数 |
| `state.nsmax`   | TICOMM 上の粒子種数 (`NSMAX` と同じ) |

```{note}
`nsa_max` (active) と `nsmax` の違い: ti は内部で TICOMM の `NSMAX` 粒子
種から「実際にプロファイル方程式を解く active species」だけを抽出して
プロファイル配列のサイズに使います. 通常 `nsa_max ≤ nsmax`.
```

## スカラー量 (`state.scalars` と `state.scalars_int`)

`ti` は `tr` と違って **2 個の浮動小数スカラーと 2 個の整数カウンタ** が
返ります. 物理量よりも収束診断が中心です.

### `state.scalars` (浮動小数, 2 個)

| キー | 単位 | 意味 |
|---|---|---|
| `T`                 | s | シミュレーション時刻 |
| `residual_loop_max` | — | 反復の最大残差 (収束診断) |

### `state.scalars_int` (整数カウンタ, 2 個)

| キー | 意味 |
|---|---|
| `icount_loop_max` | 外部反復ループの実反復数 |
| `icount_mat_max`  | 行列ソルバの実反復数 |

`residual_loop_max` が `EPSLOOP` 以下に下がっていることを確認するのが
収束チェックの基本です.

```python
state.scalars["T"]                          # 現在時刻
state.scalars["residual_loop_max"]          # 残差
state.scalars_int["icount_loop_max"]        # 反復数
```

```{important}
`tr` のような `WPT`, `BETAN` などのプラズマ性能指標は `TiState` には含まれて
いません. これらは `ti` では物理計算後にユーザ側でプロファイルから積分計算
することが期待されています (将来の API 拡張で組み込む可能性あり).
```

## プロファイル量 (radial profiles)

`ti` のプロファイルは `tr` より多彩で, **8 種類** が返ります.

```python
state.RNA[nr][nsa]    # 密度 [10^20 m^-3] — active species
state.RTA[nr][nsa]    # 温度 [keV] — active species
state.RUA[nr][nsa]    # トロイダル流速 [m/s] — active species
state.RBP[nr]         # ポロイダル磁場 [T]
state.RQP[nr]         # 安全係数プロファイル
state.RJP[nr]         # 電流密度プロファイル [MA/m^2]
state.ZEFF[nr]        # 実効電荷プロファイル
state.BETA[nr]        # β プロファイル
```

`RNA`/`RTA`/`RUA` は **active species** 軸で `nsa_max` 次元です. インデックス
は 0-origin (Python 流儀).

## 補助メソッド

```python
state.to_dict()       # Phase 0 ベースライン互換の JSON-ready dict
                      # ("scalars" + "scalars_int" + プロファイル)
```

完全な属性リストは {doc}`api-reference` の `TiState` autodoc を参照.

## `tr` の `TrState` との違い

| | `TrState` (tr) | `TiState` (ti) |
|---|---|---|
| **スカラー数** | 13 (T, WPT, BETAN, ...) | 2 (T, residual) + 2 整数カウンタ |
| **物理性能指標** | 含む (BETAN, TAUE 等) | **含まない** (ユーザ側で計算) |
| **プロファイル数** | 4 種 (RN, RT, AJ, QP) | 8 種 (RNA, RTA, RUA, RBP, RQP, RJP, ZEFF, BETA) |
| **species 軸** | NSMAX (`tr` の全粒子種) | nsa_max (active species) |
| **収束診断** | なし | `residual_loop_max`, `icount_*` |

## 物理性能指標を計算する例

`ti` では BETAN や TAUE がそのまま取れないので, プロファイルから計算します:

```python
import numpy as np

state = ti.get_state()
RA = ti_input["RA"]      # ユーザが設定した小半径
BB = ti_input["BB"]
RIP = ti_input["RIP"]

# 体積平均 β (近似)
beta_avg = np.mean(state.BETA[:state.nrmax])

# 規格化 β (Troyon)
betan = beta_avg * 100 / (RIP / (RA * BB))

print(f"<β> = {beta_avg:.4f}, βN = {betan:.2f}")
```
