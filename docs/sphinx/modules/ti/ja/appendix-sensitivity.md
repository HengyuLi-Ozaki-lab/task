# 付録: 入力パラメータと出力の対応

`ti` の入力 → 出力対応をまとめます. **(1) 代数的に決まる関係** と **(2)
物理スケーリングとして広く知られている定性的傾向** に限定します. 輸送
モデル (`MODEL_KAI` 等) の選び方で結果が大きく変わる量については個別
シミュレーションが必要なので触れません.

```{admonition} 凡例
:class: note

- **↑**: 入力を増やすと出力も増える (単調増加)
- **↓**: 入力を増やすと出力は減る (単調減少)
- **=**: 入力に等しい / 直接決まる
- **⊕**: 入力を ON にすると追加項として現れる
- **〜**: 概ね成り立つ (高次効果で逆転しうる)
```

## 1. 代数的・直接的に決まる関係

| 入力 | 主に影響する出力 | 関係 | 備考 |
|---|---|---|---|
| `DT × NTMAX` | `state.scalars["T"]` | = | 最終時刻 |
| `NSMAX` | `state.nsmax` | = | TICOMM 上の粒子種数 |
| `NRMAX` | `state.nrmax` | = | 半径メッシュ点数 |
| `MODEL_NB = 0` | NBI 系出力 | 全 0 | 加熱なし |
| `MODEL_EC = 0` | ECRF 系出力 | 全 0 | — |
| `MODEL_LH = 0` | LHRF 系出力 | 全 0 | — |
| `MODEL_IC = 0` | ICRF 系出力 | 全 0 | — |
| `MODEL_NF = 0` | 核融合反応 | なし | DT, DHe³ 反応無効 |
| `MODEL_NC = 0` | NCLASS | なし | 標準輸送モデルが優先 |
| `EPSLOOP / EPSMAT` | 反復精度 | ↓ で精度↑, 時間↑ | 計算量に直結 |

## 2. 物理スケーリングとして既知の傾向

### 2.1 装置パラメータ (`RR`, `RA`, `BB`, `RIP`)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `RR` ↑ | `state.BETA` (体積平均) | ↑ | 体積 $V \propto R \cdot a^2$, 蓄積 E 比例 |
| `RA` ↑ | `state.BETA` | ↑↑ | $V \propto R \cdot a^2$ |
| `BB` ↑ | `state.BETA` | ↓ | $\beta \propto p / B^2$ |
| `BB` ↑ | `state.RQP` (q プロファイル) | ↑ | $q \propto B / I_p$ |
| `RIP` ↑ | `state.RJP` (電流密度) | ↑ | 全電流が増える |
| `RIP` ↑ | `state.RQP` | ↓ | $q \propto B / I_p$ — 分母増 |

### 2.2 密度・温度の初期プロファイル (`PN[i]`, `PT[i]`)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `PN[i]` ↑ | `state.RNA` 軸付近 | ↑ | 直接設定 |
| `PN[i]` ↑ | `state.BETA` | ↑ | $\beta \propto nT$ |
| `PT[i]` ↑ | `state.RTA` 軸付近 | ↑ | 直接設定 |
| `PT[i]` ↑ | `state.BETA` | ↑ | $\beta \propto nT$ |
| `PNS[i]` ↑ (縁) | プロファイル形 | flatten | 中心-縁差が縮む |
| `PROFN1[i]` ↑ | プロファイル中央が flat に | — | $(1-\rho^P)^Q$ の指数増 |

### 2.3 加熱系 (`MODEL_NB`, `MODEL_EC`, ...)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `MODEL_NB ≥ 1` | `state.RTA` (温度) | ⊕↑ | 外部加熱パワー追加 |
| `MODEL_NB ≥ 1` | `state.RJP` (電流) | ⊕↑ | NB 駆動電流 |
| `MODEL_EC ≥ 1` | `state.RTA` (電子) | ⊕↑ | 局所電子加熱 |
| `MODEL_LH ≥ 1` | `state.RJP` | ⊕↑ | LH 電流駆動 |
| `MODEL_IC ≥ 1` | `state.RTA` (イオン) | ⊕↑ | 局所イオン加熱 |

### 2.4 輸送モデル (`MODEL_KAI`, `MODEL_DRR`, `MODEL_VR`)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `MODEL_KAI` (大きい χ) | `state.RTA` プロファイル | flatten | 拡散率増加 |
| `MODEL_NC = 1` (NCLASS ON) | `state.ZEFF` | 〜 | 不純物との一貫性向上 |

`MODEL_KAI` の各値の意味は `tr` モジュールの輸送モデル付録
(`docs/sphinx/modules/tr/ja/appendix-mdlkai.md`) を参照 (ti と tr は同じ列挙).

### 2.5 不純物 (`MODEL_PSC`, `PNC` 系)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| 不純物粒子源 ON | `state.ZEFF` | ↑ | $Z_\text{eff} = \sum Z_i^2 n_i / n_e$ |
| 不純物粒子源 ON | `state.RTA` (温度) | ↓ | 放射損失でエネルギー損失 |

### 2.6 反復制御 (`MAXLOOP`, `EPSLOOP`)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `EPSLOOP` ↓ (厳しい) | `state.scalars["residual_loop_max"]` | ↓ | より小さい残差まで反復 |
| `EPSLOOP` ↓ | `state.scalars_int["icount_loop_max"]` | ↑ | 反復数が増える |
| `MAXLOOP` ↑ | 収束可能性 | ↑ | 厳しい条件でも完走しやすい |

## 使い方

特定の出力を狙った値に持っていきたいときに, この表で「どの入力を動かすか」
の見当をつけます.

- **温度を上げたい** → `MODEL_NB=1` で NBI ON, または `PT[i]` を上げる
- **電流分布をピーク化したい** → `MODEL_LH=1` で LH 電流駆動 ON
- **NCLASS を使った精度の高い輸送計算がしたい** → `MODEL_NC=1` (ただし
  `MODEL_DRR`, `MODEL_VR` を 0 にする必要あり; {doc}`faq` Q5)

定量的な感度はシミュレーションを走らせて確認してください — `tilib_sweep`
の枠組みが利用できます ({doc}`testing` Layer 4).
