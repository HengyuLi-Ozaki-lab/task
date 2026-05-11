# 付録: `MDLKAI` 輸送モデル詳細

`MDLKAI` は乱流熱輸送モデルを選択する整数スイッチで, 値ごとに異なる
物理モデルが対応します. 既定値は `MDLKAI=31` (CDBM F(s,α,κq)).

ソースで定義されているのは `tr/trinit.f90:211-276` のコメントで,
本ページはそれを完全に書き起こしたものです. ファミリー単位で章立てし,
最後に全 41 値の対応表を載せます.

## 0–9: CONSTANT COEFFICIENT (定数係数モデル)

最も単純なモデル群. 拡散係数を解析的な関数形で与えます. 物理ベンチマーク
や数値テストの土台として使われます.

| 値 | 関数形 |
|---|---|
| 0 | $\chi = C \cdot (1 + A\rho^2)$ |
| 1 | $\chi = C / (1 - A\rho^2)$ |
| 2 | $\chi = C \cdot (\partial T_i/\partial\rho)^B / (1 - A\rho^2)$ |
| 3 | $\chi = C \cdot (\partial T_i/\partial\rho)^B \cdot T_i^C$ |

$C$ は定数係数 (`CK0`, `CK1`), $\rho$ は規格化半径.

## 10–19: DRIFT WAVE (+ITG +ETG) モデル

ドリフト波系の乱流モデル. ITG (Ion Temperature Gradient) や ETG
(Electron Temperature Gradient) 不安定性に基づきます. パラメータ
$\eta_c$ は閾値 $\eta = L_n/L_T$ の臨界値.

| 値 | モデル |
|---|---|
| 10 | $\eta_c = 1$ |
| 11 | $\eta_c = 1$, $1/(1+\exp(\cdot))$ で抑制 |
| 12 | $\eta_c = 1$, $1/(1+\exp) \cdot q$ |
| 13 | $\eta_c = 1$, $1/(1+\exp) \cdot (1+q^2)$ |
| 14 | $\eta_c = 1 + 2.5(L_n/R_R - 0.2)$, $1/(1+\exp)$ |
| 15 | $\eta_c = 1$, $1/(1+\exp) \cdot \mathrm{func}(q, \varepsilon, L_n)$ |
| 16 | (15) + ZONAL FLOW (帯状流) の効果 |

## 20–29: REBU-LALLA モデル

Rebu-Lalla による経験モデル.

| 値 | モデル |
|---|---|
| 20 | Rebu-Lalla model |

## 30–40: CDBM ファミリー (Current-Diffusivity-driven Ballooning Mode)

電流拡散駆動バルーニングモード. **既定の `MDLKAI=31`** がここに含まれ,
TASK のデフォルト解析モデルです. パラメータ:

- $s$: 磁気シア
- $\alpha$: 圧力勾配パラメータ
- $\kappa_q$: 安全係数依存の補正項
- $W_{E1}$: ExB シア
- $a/R$: 逆アスペクト比

| 値 | モデル形 |
|---|---|
| 30 | CDBM $1/(1+s)$ |
| **31 (既定)** | **CDBM $F(s, \alpha, \kappa_q)$** |
| 32 | CDBM $F(s, \alpha, \kappa_q)/(1 + W_{E1}^2)$ — ExB shear 抑制版 |
| 33 | CDBM $F(s, 0, \kappa_q)$ |
| 34 | CDBM $F(s, 0, \kappa_q)/(1 + W_{E1}^2)$ |
| 35 | CDBM $(s-\alpha)^2/(1+s^{2.5})$ |
| 36 | CDBM $(s-\alpha)^2/(1+s^{2.5})/(1+W_{E1}^2)$ |
| 37 | CDBM $s^2/(1+s^{2.5})$ |
| 38 | CDBM $s^2/(1+s^{2.5})/(1+W_{E1}^2)$ |
| 39 | CDBM $F_2(s, \alpha, \kappa_q, a/R)$ |
| 40 | CDBM $F_3(s, \alpha, \kappa_q, a/R)/(1+W_{S1}^2)$ |

## 60–64: 先進モデル

近年広く使われている第一原理ベースの輸送モデル群.

| 値 | モデル | 出自 |
|---|---|---|
| 60 | GLF23 model | Waltz et al. |
| 61 | GLF23 (stability enhanced version) | 安定性改良版 |
| 62 | IFS/PPPL model | Kotschenreuther et al. |
| 63 | Weiland model | Weiland グループ |
| 64 | Modified Weiland model | Weiland 改良版 |

## 130–134: CDBM 別系統

30 番台とは独立に実装された CDBM コード経路. `tr/trcdbm.f90` 等の
別ルーチンを通ります.

| 値 | モデル |
|---|---|
| 130 | CDBM model |
| 131 | CDBM05 model (2005 年改訂版) |
| 132 | CDBM model with ExB shear |
| 134 | CDBM05 model with ExB shear |

```{note}
133 は欠番 (ソースに定義無し).
```

## 140–143: Mixed Bohm/gyro-Bohm (mBgB) モデル

### 物理背景

トカマクで観測される異常輸送は, **Bohm 拡散** と **gyro-Bohm 拡散** の
2 種類のスケーリングで大まかに記述できます.

- **Bohm 拡散** $\chi^\text{Bohm} \propto \rho_s c_s$: ジャイロ半径 $\rho_s$
  に対して **線形** に効く. プラズマ全体に渡る非局所的な寄与で, 縁での
  電子温度勾配が中心部の輸送に影響します. 大型機ほど相対的に大きく効く.
- **gyro-Bohm 拡散** $\chi^\text{gB} \propto \rho_s^2 c_s / a$: ジャイロ半径の
  **2 乗** に効く局所的な寄与. ITG / TEM 不安定性の通常の表現.

両者を **同じ場所で足し合わせる** のが Mixed Bohm/gyro-Bohm (mBgB) で,
JET の実験データに合わせてチューニングされたため "JETTO transport model"
とも呼ばれます (Erba et al., Nucl. Fusion **38** (1998) 1013).

具体的には電子・イオンの熱拡散率が次の和で書けます:

$$\chi_e = \chi_e^\text{Bohm} + \chi_e^\text{gB}, \quad \chi_i = \chi_i^\text{Bohm} + \chi_i^\text{gB}$$

ここに ExB shear や magnetic shear による抑制項を後から掛けるのが
141–143 のバリエーションです (Pankin/Bateman et al., PPCF **44** (2002) A495).

### `MDLKAI=140..143` の対応

| 値 | モデル | 物理 |
|---|---|---|
| 140 | mBgB (基本形) | Bohm + gyro-Bohm の単純和. 抑制項なし |
| 141 | mBgB + Tara 抑制 | Tara による磁気シア依存抑制 |
| 142 | mBgB + Pacher 抑制 (ExB) | Pacher の ExB 流れシア抑制 |
| 143 | mBgB + Pacher 抑制 (ExB + 磁気シア) | 142 + 磁気シア依存項 |

### いつ使うか

- L モード〜H モード遷移を含む放電のシミュレーションでよく使われます
- JET / DIII-D / ITER でのベンチマーク実績あり
- ETG (電子温度勾配) モードは含まれないので, 中心部電子輸送には
  別系統 (例: GLF23 系の `60–61` や mmm) が必要な場合あり

実装は `tr/mbgb/mixed_Bohm_gyro_Bohm.f` (Bateman/Pankin/Kritz, Lehigh Univ.).

## 150–151: mmm95 (Multi-Mode Transport Model 1995)

### 物理背景

**Multi-Mode (MM)** の名前のとおり, **複数の独立な不安定性チャネルを
別々に評価して合算する** のが MMM 系の特徴です. mmm95 が組み込む
チャネルは:

1. **Weiland model**: ITG / TEM (Trapped-Electron Mode) のドリフト波系
2. **Resistive Ballooning** (RB): 抵抗性バルーニングモード
3. **Kinetic Ballooning** (KB): 動力学的バルーニングモード

それぞれが拡散率 $\chi^\text{ig}$ (ITG/TEM), $\chi^\text{rb}$, $\chi^\text{kb}$
を出し, それらの線形和が最終的な輸送係数になります.

NTCC (National Transport Code Collaboration) が標準化したコードで, 1995 年
時点でフリーズされたバージョンが mmm95 です (Bateman et al., Phys. Plasmas
**5** (1998) 1793). 当時 BALDUR トランスポートコードでの検証実績が豊富で,
ITER 物理ベースに広く採用されました.

### `MDLKAI=150 / 151` の対応

| 値 | モデル | ExB 抑制 |
|---|---|---|
| 150 | mmm95 (Multi-Mode 1995) | 無し (標準フォーム) |
| 151 | mmm95 + ExB shear stabilization | 有り |

ExB shear (`151`) は背景流れによる乱流抑制を `1/(1 + W_{ExB}^2)` 形式で
組み込んだ拡張です.

### いつ使うか

- 国際比較ベンチマーク (ITER design 等) で同じモデルを使いたいとき
- ITG/TEM/RB/KB を区別して寄与を見たいとき

実装は `tr/mmm95/mmm95.f` (Bateman/Kritz, Lehigh Univ.).

## 160–161: mmm7_1 (Multi-Mode Transport Model 7.1)

### 物理背景

mmm の **次世代** (mmm95 の後継). 内部で Weiland model を Halpern らが
2006–2011 年に書き直したもの (`w20mod`) を使い, 数値安定性とプロファイル
解像度が向上しています. mmm95 が固定パラメータ前提だったのに対し,
mmm7_1 は時間依存・空間依存の解析がよりロバストです.

```{important}
mmm7_1 では **ETG (電子温度勾配) モードは含まれていません**. 中心部の
電子熱輸送がアノマラスに大きいケースでは過小評価することがあるので,
GLF23 (`MDLKAI=60`) などと比較するのが安全です.
```

### `MDLKAI=160 / 161` の対応

| 値 | モデル | ExB 抑制 |
|---|---|---|
| 160 | mmm7_1 (Multi-Mode 7.1) | 無し |
| 161 | mmm7_1 + ExB shear stabilization | 有り |

### いつ使うか

- 最新世代の Multi-Mode モデルで解析したいとき
- mmm95 (`150` / `151`) と比較してモデル更新の効果を見たいとき
- ETG が支配的でないと予想されるパラメータ領域

実装は `tr/libmmm7_1/modmmm7_1.f90` + `tr/libmmm7_1/w20mod.f90`
(Lixiang Luo, F. Halpern et al., Lehigh Univ.).

## 3 つのモデルの比較

| 観点 | mBgB (140–143) | mmm95 (150–151) | mmm7_1 (160–161) |
|---|---|---|---|
| **発祥** | JET (Erba 1998) | NTCC (Bateman 1998) | NTCC (Halpern 2008–) |
| **構成チャネル** | Bohm + gyro-Bohm | Weiland + RB + KB | Weiland (改訂) + RB + KB |
| **ETG モード** | 含まれない | 含まれない | 含まれない |
| **ExB 抑制** | 142, 143 (Pacher) | 151 | 161 |
| **磁気シア抑制** | 141, 143 | 内蔵 | 内蔵 |
| **計算コスト** | 低 | 中 | 中〜高 |
| **典型的用途** | L/H 遷移を含む放電 | ITER 物理ベースライン | 最新世代の比較解析 |
| **実装ファイル** | `tr/mbgb/` | `tr/mmm95/` | `tr/libmmm7_1/` |

選択の目安:

- **JET / 中型機の H モード再現**: mBgB (`143` が標準的)
- **ITER ベースラインに合わせたい**: mmm95 (`151`)
- **新しいモデルで再評価したい**: mmm7_1 (`161`)
- **ETG が効きそうなとき**: 上記 3 つはどれも非対応 → GLF23 (`60`–`61`) と併用検討

## どれを選ぶべきか

- **既定 (`MDLKAI=31`)**: CDBM F(s,α,κq). TASK での標準. 過去の解析と
  比較したい場合はこれ.
- **国際比較が必要な場合**: GLF23 (`60`) や mmm95 (`150` / `151`),
  mmm7_1 (`160` / `161`).
- **ベンチマーク**: 定数係数 (`0`–`3`) で輸送方程式の数値挙動を切り分け.
- **ExB shear の効果を見たい**: `32`, `34`, `36`, `38`, `132`, `134`,
  `142`, `143`, `151`, `161` のいずれか.

## 全 41 値対応表

検索性のため全値を 1 つの表に集約します.

| 値 | ファミリー | 簡略説明 |
|---|---|---|
| 0  | CONSTANT  | $C(1+A\rho^2)$ |
| 1  | CONSTANT  | $C/(1-A\rho^2)$ |
| 2  | CONSTANT  | $C(\partial T_i/\partial\rho)^B/(1-A\rho^2)$ |
| 3  | CONSTANT  | $C(\partial T_i/\partial\rho)^B T_i^C$ |
| 10 | DRIFT WAVE | $\eta_c=1$ |
| 11 | DRIFT WAVE | $\eta_c=1$, $1/(1+\exp)$ |
| 12 | DRIFT WAVE | $\eta_c=1$, $1/(1+\exp) \cdot q$ |
| 13 | DRIFT WAVE | $\eta_c=1$, $1/(1+\exp) \cdot (1+q^2)$ |
| 14 | DRIFT WAVE | $\eta_c=1+2.5(L_n/R_R-0.2)$, $1/(1+\exp)$ |
| 15 | DRIFT WAVE | $\eta_c=1$, $1/(1+\exp) \cdot \mathrm{func}(q,\varepsilon,L_n)$ |
| 16 | DRIFT WAVE | (15) + zonal flow |
| 20 | REBU-LALLA | Rebu-Lalla model |
| 30 | CDBM      | $1/(1+s)$ |
| **31** | **CDBM (既定)** | **$F(s,\alpha,\kappa_q)$** |
| 32 | CDBM      | $F(s,\alpha,\kappa_q)/(1+W_{E1}^2)$ |
| 33 | CDBM      | $F(s,0,\kappa_q)$ |
| 34 | CDBM      | $F(s,0,\kappa_q)/(1+W_{E1}^2)$ |
| 35 | CDBM      | $(s-\alpha)^2/(1+s^{2.5})$ |
| 36 | CDBM      | $(s-\alpha)^2/(1+s^{2.5})/(1+W_{E1}^2)$ |
| 37 | CDBM      | $s^2/(1+s^{2.5})$ |
| 38 | CDBM      | $s^2/(1+s^{2.5})/(1+W_{E1}^2)$ |
| 39 | CDBM      | $F_2(s,\alpha,\kappa_q,a/R)$ |
| 40 | CDBM      | $F_3(s,\alpha,\kappa_q,a/R)/(1+W_{S1}^2)$ |
| 60 | 先進      | GLF23 |
| 61 | 先進      | GLF23 (stability enhanced) |
| 62 | 先進      | IFS/PPPL |
| 63 | 先進      | Weiland |
| 64 | 先進      | Modified Weiland |
| 130 | CDBM 別系統 | CDBM |
| 131 | CDBM 別系統 | CDBM05 |
| 132 | CDBM 別系統 | CDBM + ExB shear |
| 134 | CDBM 別系統 | CDBM05 + ExB shear |
| 140 | mBgB     | mixed Bohm/gyro-Bohm |
| 141 | mBgB     | mBgB + Tara 抑制 |
| 142 | mBgB     | mBgB + Pacher (ExB) |
| 143 | mBgB     | mBgB + Pacher (ExB + shear) |
| 150 | mmm95    | mmm95 (no ExB) |
| 151 | mmm95    | mmm95 (with ExB) |
| 160 | mmm7_1   | mmm7_1 (no ExB) |
| 161 | mmm7_1   | mmm7_1 (with ExB) |

(欠番: 4–9, 17–19, 21–29, 41–59, 65–129, 133, 135–139, 144–149,
152–159, 162–. 指定すると Fortran 側で `STOP` または既定モデルに
フォールバックします — 実装依存なので使用しないでください.)
