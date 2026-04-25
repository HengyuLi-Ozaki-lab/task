# 出力されるパラメータ・物理量 (`FpState`)

`fp.get_state()` は `FpState` dataclass を返します. fp は分布関数 $f(r, p, \theta)$
そのものは返さず, **モーメント量** (積分された物理量) のみを公開します.

## 次元情報 (dimension fields)

| フィールド | 意味 |
|---|---|
| `state.nrmax`  | 半径メッシュ点数 |
| `state.nsamax` | active species 数 (分布関数を解いた粒子種) |
| `state.npmax`  | 運動量メッシュ点数 |
| `state.nthmax` | ピッチ角メッシュ点数 |
| `state.ntg2`   | 長時間軸カウンタ |

## スカラー量

`fp` の `state.scalars` は **`timefp` 1 個のみ** です. tr/eq のような
13/12 個のプラズマ性能指標は持ちません — これは fp の出力が分布関数
モーメントが中心で, 派生量 (`BETA`, `TAUE` など) はユーザ側で計算する
設計だからです.

```python
state.timefp     # シミュレーション時刻 [s]
```

## プロファイル量 (radial × species のモーメント配列)

fp の主要出力. **`[nsamax][nrmax]` の 2 次元配列** で, active 粒子種ごとに
半径方向プロファイルを返します.

| フィールド | 物理量 | 単位 |
|---|---|---|
| `state.RNT[isa][nr]`  | 粒子数密度 (分布関数の 0 次モーメント) | 10²⁰ m⁻³ |
| `state.RWT[isa][nr]`  | エネルギー密度 (2 次モーメント) | MJ/m³ |
| `state.RTT[isa][nr]`  | 平均温度 (`RWT/RNT` から) | keV |
| `state.RJT[isa][nr]`  | 電流密度 (1 次モーメント, ピッチ角依存) | MA/m² |
| `state.RPCT[isa][nr]` | 衝突によるパワー授受 | MW/m³ |
| `state.RPWT[isa][nr]` | 波動加熱によるパワー授受 | MW/m³ |

```python
state.RNT[0][0]      # 0 番目 active species の軸上密度
state.RTT[0]         # 0 番目 active species の温度プロファイル全体
state.RJT[1]         # 1 番目 active species の電流密度プロファイル
```

## 5D 分布関数の取得

`FpState` には **分布関数本体 $f(r, p, \theta)$ は含まれません**. 5D グリッド
を直接展開すると JSON 化が破綻するためです. 必要な場合は:

1. C ABI レベルで `FpStateC` 構造体の追加フィールドを利用 (実装依存)
2. 代替: モーメント量 (RNT, RWT, RJT) で十分な解析を組み立てる
3. 別の API (`fp_get_distribution(species, ir)` など; 将来追加予定) を待つ

## 補助メソッド

```python
state.to_dict()   # JSON-ready dict
```

完全な属性リストは {doc}`api-reference` の `FpState` autodoc を参照.

## `tr`/`ti` の State との違い

| | `TrState` (tr) | `TiState` (ti) | `FpState` (fp) |
|---|---|---|---|
| **種別軸** | NSMAX | active NSA_MAX | active NSAMAX |
| **位相空間** | 1D 半径 | 1D 半径 | **5D** (r, p, θ, species, t) |
| **スカラー数** | 13 | 2 + 2int | **1** (timefp) |
| **主出力** | RN, RT, AJ, QP | RNA, RTA, RUA, RBP, ZEFF, BETA | RNT, RWT, RTT, RJT, RPCT, RPWT |
| **意味** | 流体モーメント | 統合輸送モーメント | 分布関数モーメント |
| **メモリ消費** | 低 | 中 | **高** (5D) |
