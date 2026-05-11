# 付録: 入力パラメータと出力の対応

入力パラメータを変化させたときに `EqState` の出力がどう動くかをまとめます.
ここで扱うのは **(1) 代数的に決まる関係** と **(2) 物理スケーリングとして
広く知られている定性的傾向** に限ります. プロファイルの詳細形状 (`PP*`,
`PJ*`, `FF*` の高次効果) など, 解いてみないと分からない量は触れません.

```{admonition} 凡例
:class: note

- **↑**: 入力を増やすと出力も増える (単調増加)
- **↓**: 入力を増やすと出力は減る (単調減少)
- **=**: 入力に等しい / 直接決まる
- **〜**: 概ね成り立つ (高次効果で逆転しうる)
```

## 1. 代数的・直接的に決まる関係

平衡を解かなくても確実に決まるもの.

| 入力 | 出力 | 関係 | 備考 |
|---|---|---|---|
| `RIP` | `state.scalars["ripx"]` | ≈ | `ripx` はソルバが収束した結果の総電流. 通常 `RIP` と一致 (一致しないなら未収束) |
| `RGMIN`, `RGMAX` | `state.rg` (R 格子の範囲) | = | `nrgmax` 点で `[RGMIN, RGMAX]` を分割 |
| `ZGMIN`, `ZGMAX` | `state.zg` (Z 格子の範囲) | = | 同上 |
| `NRGMAX` | `state.nrgmax` | = | R 格子点数 |
| `NZGMAX` | `state.nzgmax` | = | Z 格子点数 |
| `NPSMAX` | `state.npsmax` | = | ψ-面サンプル数 |
| `NRMAX`, `NTHMAX` | `state.nrmax`, `state.nthmax` | = | ψ-メッシュの解像度 |
| `MODELG ∈ {3, 5, 8}` | 必須入力 | `KNAMEQ` のファイル存在が必要 | `validate` で `FILE_MISSING` |
| `MODELG = 2` | `KNAMEQ` 無視 | — | 解析的トロイダル経路では使わない |

## 2. 物理スケーリングとして既知の傾向

研究領域で広く受け入れられている定性的傾向.

### 2.1 装置パラメータ (`RR`, `RA`, `RKAP`, `RDLT`, `BB`, `RIP`)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `RR` ↑ | `pvol` (体積) | ↑ | $V \propto R \cdot a^2$ |
| `RR` ↑ | `raxis` | ↑ | 装置中心が外側へ移動 |
| `RR` ↑ | `qaxis` | ↑ | $q \propto B/(I \cdot R^{-1})$ — 大半径効果 |
| `RA` ↑ | `pvol` | ↑↑ | $V \propto R \cdot a^2$ — `RA` の方が効きが強い |
| `RA` ↑ | `qsurf` | 〜↓ | 表面 $q \propto B \cdot a / (R \cdot I)$ — $a$ 増 |
| `RKAP` ↑ (楕円率) | `pvol` | ↑ | 体積 $\propto \kappa$ |
| `RKAP` ↑ | `betat`, `betap` | 〜↑ | 形状による安定性向上 |
| `RDLT` ↑ (三角度) | 高次の磁気面歪み | — | スカラーへの一次効果は小さい |
| `BB` ↑ | `betat`, `betap` | ↓ | $\beta = 2\mu_0 \langle p \rangle / B^2$ |
| `BB` ↑ | `qaxis`, `qsurf` | ↑ | $q \propto B / I$ |
| `RIP` ↑ | `qaxis`, `qsurf` | ↓ | $q \propto B / I$ — 分母増 |
| `RIP` ↑ | `betap` | ↑ | $\beta_p \propto p / B_p^2 \propto p R / I^2$ … 詳細はモデル依存 |

### 2.2 安全係数の制約 (`Q0`, `QA`, `QMIN`)

`MDLEQF=4` (与える: $P, q$) のときに直接効きます.

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `Q0` (与えた中心 q) | `state.scalars["qaxis"]` | ≈ | 一致するように解かれる |
| `QA` (与えた表面 q) | `state.scalars["qsurf"]` | ≈ | 同上 |
| `QMIN` (反転シア) | `qqps` プロファイル最小値 | = | 反転シア配位の最小 q |

### 2.3 圧力プロファイル (`PP0`, `PP1`, `PP2`, `PROFP*`)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `PP0` ↑ (主成分振幅) | `state.ppps` (圧力プロファイル) | ↑ | 軸付近の $p$ が直接上がる |
| `PP0` ↑ | `betat`, `betap` | ↑ | $\beta \propto \langle p \rangle$ |
| `PP1` ↑ (副成分) | `state.ppps` 中央 | ↑ | 中央寄せのピーキング |
| `PP2` ↑ (ITB 成分) | プロファイルピーキング | ↑ | ITB 内部だけに加わる |
| `PROFP0` ↑ | プロファイル形状 | 中央 flat | $(1-\psi^{P_R})^{P_{P0}}$ の指数増 |

### 2.4 電流プロファイル (`PJ0`, `PJ1`, `PJ2`, `PROFJ*`)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `PJ0` ↑ (主成分) | $j(\psi)$ プロファイル | ↑ | 中央電流密度が増える |
| `PJ0` ↑ | `qaxis` | ↓ | 中央電流 ↑ → 中央 $q$ ↓ |
| `PJ0` ↑ | `state.scalars["ripx"]` | ↑ | 全電流の積分が増える |
| `PROFJ0` ↑ | $j$ プロファイル | 中央集中 | 指数で flatten |

### 2.5 メッシュ解像度 (`NSGMAX`, `NRGMAX`, `NPSMAX`, ...)

メッシュ解像度を上げると **正解に近づく** が, 計算時間も上がります.

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `NSGMAX` ↑ | 平衡解の精度 | ↑ | Grad-Shafranov の収束性 |
| `NRGMAX`, `NZGMAX` ↑ | R-Z 平面での解像度 | ↑ | プロット精度 |
| `NPSMAX` ↑ | ψ-面プロファイルの解像度 | ↑ | `state.psips` 等の点数増 |
| `NRMAX`, `NTHMAX` ↑ | 磁束座標の解像度 | ↑ | 高次解析の精度 |

実用上は既定値で十分なケースが多いです.

### 2.6 反復制御 (`EPSEQ`, `NLPMAX`)

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `EPSEQ` ↓ (厳しい収束基準) | 解の精度 | ↑ | 反復が厳密化 |
| `EPSEQ` ↓ | 計算時間 | ↑ | 反復数増 |
| `EPSEQ` 過小 | `EqlibCalculationFailedError` | — | `NLPMAX` 内に収束しないとエラー |
| `NLPMAX` ↑ | 収束可能性 | ↑ | 未収束ケースを救える |

### 2.7 動作モード (`MODELG`, `MDLEQF`)

| 入力 | 効果 |
|---|---|
| `MODELG=2` (解析) | `KNAMEQ` 不要. 内蔵プロファイルで解く |
| `MODELG=3` (TASK/EQ) | `KNAMEQ` 必須. TASK ネイティブ平衡を読み込む |
| `MODELG=5` (EQDSK) | `KNAMEQ` 必須. G-EQDSK 標準形式 |
| `MDLEQF=0` (既定) | $P, J_\text{tor}, T, V_\varphi$ + $I_p$ を入力 |
| `MDLEQF=1` | $P, F$ + $I_p$ — 高エネルギー領域研究 |
| `MDLEQF=4` | $P, q$ — q プロファイルを直接指定したいとき |

## 使い方

特定の出力を狙った値に持っていきたいときに, この表で「どの入力を動かすか」
の見当をつけます. 例:

- **`betat` を上げたい** → `PP*` を上げる, または `BB` を下げる
  (ただし `BB` を下げすぎると `qaxis<1` で MHD 不安定の懸念)
- **`qaxis` を上げたい** → `BB` を上げる, または `RIP` (= `PJ0` 等で
  決まる総電流) を下げる
- **磁気軸位置 `raxis` を ITER 標準値に合わせたい** → `RR`, `RKAP`, `RDLT`
  の組合せを調整
- **Grad-Shafranov 収束しない** → `EPSEQ` を緩める, `NLPMAX` を増やす,
  もしくは初期プロファイルを物理的に妥当な値へ

定量的な感度 (例: `RR` を 10% 上げると `pvol` は何 % 上がるか) は
シミュレーションを走らせて確認してください — `eqlib_sweep` の枠組みが
そのために用意されています ({doc}`testing` Layer 4).
