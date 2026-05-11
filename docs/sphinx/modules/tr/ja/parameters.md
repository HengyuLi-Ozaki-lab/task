# サポートされている入力パラメータ

`tr/tr_param_registry.f90` に登録されているパラメータを論理グループ別に
示します. 名前は Fortran の `/TR/` ネームリストと一致しています. 型の
「double 配列」は `set_param("NAME[i]", value)` 構文で **1-origin** 添字で
指定します. 既定値は `tr/trinit.f90::tr_init` で設定されるもので, 明示的に
上書きしなければこの値が使われます.

## 必須・推奨パラメータ

ほとんどのパラメータは既定値があるため最小構成では何も指定しなくても
`run()` できます. ただし **特定の条件で必須** になるものと, **物理的に
意味のある結果を得るには上書きすべき** ものがあります.

### 必須 (条件付き)

| 条件 | 必須パラメータ | 理由 |
|---|---|---|
| `MODELG ∈ {3, 5, 7, 8}` | **`KNAMEQ`** (文字列) | 平衡データファイル名. 未設定だと `tr_validate()` が `FILE_MISSING` 診断を返し, `run()` 時に `tr_prep` が失敗する |

`KNAMEQ` は `set_param_str` 経由で指定します:

```python
tr.set_param("MODELG", 3)
tr.set_param_str("KNAMEQ", "eqdata.ITER01")
```

`MODELG=2` (解析的トロイダル幾何, 既定) ならファイル不要なので
**厳密な意味で必須なパラメータはありません**.

### 強く推奨 (既定値が generic すぎる)

既定値はジェネリック小型トカマクを想定したダミーなので, 解析対象の装置
が決まっているなら以下は明示的に上書きすべきです.

| 名前 | 既定値 | 推奨上書き例 (ITER 想定) |
|---|---|---|
| `RR`     | 3.0 m  | 6.2 m |
| `RA`     | 1.2 m  | 2.0 m |
| `BB`     | 3.0 T  | 5.3 T |
| `RIPS`   | 3.0 MA | 15.0 MA |
| `RIPE`   | 3.0 MA | 15.0 MA |
| `NSMAX`  | 2 (e + D) | 解析対象に応じて |
| `DT`     | 0.01 s | 結果の時間スケールに応じて |
| `NTMAX`  | 100    | 結果の時間スケールに応じて |

### 普通は触らなくて良い (既定で十分)

以下は既定でほぼ問題ありません. 特定の物理を入れたいときだけ ON します.

- 加熱系 (`MDLNB=1` 以外は既定 OFF, `MDLEC`/`MDLLH`/`MDLIC=0`)
- 核融合 (`MDLNF=0`)
- 不純物 (`MDLIMP=0`)
- 内部数値設定 (`EPSLTR`, `LMAXTR`, `NGTSTP`, `NGRSTP`)
- プロファイル形状 (`PROFN1=2.0`, `PROFN2=0.5`)

### 推奨ワークフロー

```python
from trlib import Trlib, TrDiagCode

with Trlib() as tr:
    # 1. 必ず指定するもの
    tr.set_params(RR=6.2, RA=2.0, BB=5.3,
                  RIPS=15.0, RIPE=15.0,
                  DT=0.01, NTMAX=100)

    # 2. MODELG=3 にするなら KNAMEQ 必須
    # tr.set_param("MODELG", 3)
    # tr.set_param_str("KNAMEQ", "eqdata.ITER01")

    # 3. 設定後, run の前に validate を呼ぶのが推奨
    diags = tr.validate()
    for d in diags:
        print(f"[{TrDiagCode(d.code).name}] {d.param}: {d.message}")
    if diags:
        raise SystemExit("fix the diagnostics before running")

    tr.run(ntmax=10)
    state = tr.get_state()
```

`validate()` は **未設定の必須項目** ・ **値域外** ・ **ファイル未存在**
を一括検査するので, `run()` 直前に呼ぶのが安全です ({doc}`parameter-setting`
の方法 D を参照).

## 1. 幾何・装置 (Geometry / device)

プラズマの空間形状と磁場強度を決めるパラメータ群. シミュレーション開始前に
最低限指定すべきなのは `RR`, `RA`, `BB` の 3 つです.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `RR`     | double | 3.0 | m | プラズマ大半径 (major radius) |
| `RA`     | double | 1.2 | m | プラズマ小半径 (minor radius) |
| `RKAP`   | double | 1.5 | — | ポロイダル断面の elongation (楕円率) |
| `RDLT`   | double | 0.0 | — | ポロイダル断面の triangularity |
| `BB`     | double | 3.0 | T | プラズマ軸上のトロイダル磁場 |
| `PHIA`   | double | 0.0 | Wb | 全トロイダル磁束 (UFILE 使用時の受け皿) |
| `MODELG` | int switch | 2 | — | 平衡 / 幾何モデル選択 |

`MODELG` の許容値:

| 値 | 挙動 |
|---|---|
| 2 (既定) | TOROIDAL GEOMETRY — 解析的トロイダル幾何 |
| 3        | READ TASK/EQ FILE — `KNAMEQ` の平衡データを読み込む |
| 5        | READ EQDSK FILE |
| 9        | CALCULATE TASK/EQ — オンザフライで TASK/EQ を解く |

## 2. プラズマ電流 (Current)

プラズマ電流は時刻線形で `RIPS` → `RIPE` に変化します. 定常なら同値に
しておきます.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `RIPS` | double | 3.0 | MA | シミュレーション開始時のプラズマ電流 |
| `RIPE` | double | 3.0 | MA | シミュレーション終了時のプラズマ電流 |

## 3. プラズマ組成 (Plasma composition)

粒子種配列は `NSMM=100` で宣言されていますが, レジストリは `NSMAX ∈ [2, 8]`
に制限しています (`NSMAX=1` は `tr_prof_impurity` で零除算を起こし, Fortran
側 `STOP` がホストプロセスを落とすため). 慣例として NS=1 は電子, NS=2 以降
がイオン種です.

| 名前 | 型 | 既定値 (NS=2 D イオン) | 単位 | 意味 |
|---|---|---|---|---|
| `NSMAX`   | int          | 2   | — | 主粒子種の数 (1 ≤ NS ≤ NSMAX) |
| `PA[i]`   | double[NSMM] | 2   | — | 粒子種 i の質量数 |
| `PZ[i]`   | double[NSMM] | 1   | — | 粒子種 i の電荷数 |
| `PN[i]`   | double[NSMM] | 0.5 | 10²⁰ m⁻³ | 粒子種 i の軸上初期数密度 |
| `PNS[i]`  | double[NSMM] | 0.05 | 10²⁰ m⁻³ | 粒子種 i の境界 (表面) 初期数密度 |
| `PT[i]`   | double[NSMM] | 1.5 | keV | 粒子種 i の軸上初期温度 |
| `PTS[i]`  | double[NSMM] | 0.05 | keV | 粒子種 i の境界 (表面) 初期温度 |

既定の粒子配置 (`trinit.f90`):

| NS | 粒子 | PA | PZ | PN | PT |
|---|---|---|---|---|---|
| 1 | 電子 | 5.446×10⁻⁴ (AME/AMM) | -1 | 0.5 | 1.5 |
| 2 | D     | 2  | 1 | 0.5 | 1.5 |
| 3 | T     | 3  | 1 | 0   | 1.5 |
| 4 | He    | 4  | 2 | 0   | 1.5 |
| 5 | C (低電離) | 12 | 2 | 0 | 0 |
| 6 | C (高電離) | 12 | 4 | 0 | 0 |

## 4. 初期プロファイル形状 (Profile shape)

初期密度・温度プロファイルは以下の形で与えられます:

$$X(\rho) = (X_0 - X_S)\,(1 - \rho^{\text{PROFN1}})^{\text{PROFN2}} + X_S$$

ここで $X_0$ = `PN[i]` or `PT[i]` (軸上), $X_S$ = `PNS[i]` or `PTS[i]`
(境界).

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `PROFN1` | double | 2.0 | — | プロファイル内側形状指数 |
| `PROFN2` | double | 0.5 | — | プロファイル外側形状指数 |

## 5. 不純物 (Impurity)

炭素 (C) と鉄 (Fe) の不純物混入を制御します.

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MDLIMP` | int switch | 0 | 不純物モデル選択 |
| `PNC`    | double     | 0.0 | 炭素密度係数 (ITER 物理ガイドライン比) |

`MDLIMP` の許容値:

| 値 | 挙動 |
|---|---|
| 0 (既定) | 不純物なし (`PNC` / `PNFE` 不使用) |
| 1 | ITER 物理ガイドライン ×1.0 で不純物密度を与える |
| 2 | `PNC` を因子として `ANC = PNC·ANE` を与える |
| 3 | ケース 1 + `PZC`/`PZFE` 経由で Te に応じ電子密度を変化 |
| 4 | ケース 2 + `PZC`/`PZFE` 経由で Te に応じ電子密度を変化 |

## 6. 時間発展 (Time evolution)

`DT × NTMAX` が実シミュレーション時間 [s] です. 既定では 0.01 × 100 = 1 s.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `DT`     | double | 0.01  | s | 時間ステップ幅 |
| `NTMAX`  | int    | 100   | — | 総時間ステップ数 |
| `NTSTEP` | int    | 10    | — | スナップショット印字間隔 (ステップ数) |
| `EPSLTR` | double | 0.001 | — | 内部反復の収束判定基準 |
| `LMAXTR` | int    | 10    | — | 内部反復の最大反復数 |
| `NGTSTP` | int    | 2     | — | 時間発展グラフ保存間隔 |
| `NGRSTP` | int    | 100   | — | 半径プロファイルグラフ保存間隔 |

## 7. 輸送モデル (Transport model)

熱・粒子輸送の係数とモデル選択. `MDLKAI` は特に選択肢が多いため, 代表値は
下の表を参照. `CDW` は 8 要素 (1-origin) で, Drift-Wave 系モデル時に参照
されます.

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MDLKAI` | int switch | 31  | 乱流熱輸送モデル選択 |
| `MDLETA` | int switch | 3   | 抵抗モデル |
| `MDLAD`  | int switch | 3   | 粒子拡散モデル |
| `MDLAVK` | int switch | 3   | 熱ピンチモデル |
| `CDW[i]` | double[8]  | 0.04 | Drift-Wave モデル係数 (i=1..8) |
| `CHP`    | double     | 0.0 | 半経験補正係数 |
| `CK0`    | double     | 12.0 | 電子用 χ 係数 |
| `CK1`    | double     | 12.0 | イオン用 χ 係数 |

`MDLKAI` で選べる輸送モデル一覧 (代表値; 10 番台単位でファミリー構成):

| 範囲 | ファミリー | 代表値 |
|---|---|---|
| 0–9    | CONSTANT COEFFICIENT | 0: 一定, 2: $\propto(\partial T_i/\partial\rho)^B$ |
| 10–19  | DRIFT WAVE (+ITG +ETG) | 10: $\eta_c=1$, 16: 15+zonal flow |
| 20–29  | REBU-LALLA | 20: Rebu-Lalla |
| 30–40  | **CDBM ファミリー** | **31 (既定): CDBM F(s,α,κq)**, 32: +ExB shear |
| 60–64  | 先進モデル | 60: GLF23, 62: IFS/PPPL, 63: Weiland |
| 130–134 | CDBM 別系統 | 131: CDBM05, 132: +ExB shear |
| 140–143 | Mixed Bohm/gyro-Bohm | 140: mBgB, 143: mBgB+Pacher |
| 150–151 | mmm95 | 150: no ExB, 151: with ExB |
| 160–161 | mmm7_1 (ETG なし) | 160: no ExB, 161: with ExB |

各モデルの個別解説と全 41 値の詳細対応表は {doc}`appendix-mdlkai` を参照.

`MDLETA` (抵抗モデル):

| 値 | モデル |
|---|---|
| 1 | Hinton and Hazeltine |
| 2 | Hirshman, Hawryluk |
| 3 (既定) | Sauter |
| 4 | Hirshman, Sigmar |
| その他 | CLASSICAL |

`MDLAD` (粒子拡散):

| 値 | モデル |
|---|---|
| 1 | 定数 D + 内向きピンチ AV0 |
| 2 | 乱流効果 + ピンチ AV0 |
| 3 (既定) | Hinton and Hazeltine |
| 4 | Hinton and Hazeltine + 乱流 |
| その他 | 粒子輸送なし |

`MDLAVK` (熱ピンチ):

| 値 | モデル |
|---|---|
| 1 | 任意振幅 |
| 2 | 任意振幅 + 圧力依存 |
| 3 (既定) | Hinton and Hazeltine |
| その他 | 熱ピンチなし |

## 8. サブモジュール切替 (Module switches)

加熱・電流駆動・粒子ソース系のサブモジュールを ON/OFF します. 既定では
NBI (`MDLNB=1`) とペレット (`MDLPEL=1`), ブートストラップ電流 Sauter
(`MDLJBS=5`) だけが有効です.

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MDLNB`  | int switch | 1 | NBI (中性粒子ビーム) 加熱モデル |
| `MDLEC`  | int switch | 0 | ECRF (電子サイクロトロン波) 加熱 |
| `MDLLH`  | int switch | 0 | LHRF (低域混成波) 加熱 |
| `MDLIC`  | int switch | 0 | ICRF (イオンサイクロトロン波) 加熱 |
| `MDLPEL` | int switch | 1 | ペレット注入モデル |
| `MDLJBS` | int switch | 5 | ブートストラップ電流モデル |
| `MDLST`  | int switch | 0 | のこぎり波 (sawtooth) モデル |
| `MDLNF`  | int switch | 0 | 核融合反応モデル |
| `MDLUF`  | int switch | 0 | UFILE (実験データ) 読込モデル |

`MDLNB`:

| 値 | 挙動 |
|---|---|
| 0 | OFF |
| 1 (既定) | GAUSSIAN (粒子源なし) |
| 2 | GAUSSIAN |
| 3 | PENCIL BEAM (粒子源なし) |
| 4 | PENCIL BEAM |

`MDLPEL`:

| 値 | モデル |
|---|---|
| 0 | OFF |
| 1 (既定) | GAUSSIAN |
| 2 | Nakamura |
| 3 | Ho |

`MDLJBS`:

| 値 | モデル |
|---|---|
| 1–3 | Hinton and Hazeltine |
| 4   | Hirshman, Sigmar |
| 5 (既定) | Sauter |
| その他 | Hinton and Hazeltine |

`MDLNF`:

| 値 | 反応 |
|---|---|
| 0 (既定) | OFF |
| 1 | DT (粒子源なし) |
| 2 | DT (粒子源あり) |
| 3 | DT + NB ビーム成分 (粒子源なし) |
| 4 | DT + NB ビーム成分 (粒子源あり) |
| 5 | DHe³ (粒子源なし) |
| 6 | DHe³ (粒子源あり) |

`MDLST`: 0 (OFF, 既定) / 1 (ON).

`MDLUF`:

| 値 | 意味 |
|---|---|
| 0 (既定) | UFILE 不使用 |
| 1 | 時間発展 |
| 2 | 定常 |
| 3 | TOPICS との比較 |

```{note}
`MDLEC` / `MDLLH` / `MDLIC` の列挙値は Fortran ソースにコメントが無く,
ここには載せていません. 既定 0 は OFF です. 非零値の挙動は
`tr/trpnb.f90` や関連する波動計算コードを直接参照してください.
```

## 9. NBI (Neutral Beam Injection)

`MDLNB ≥ 1` のとき有効. パワーはガウシアン分布で半径 `PNBR0` 中心・
幅 `PNBRW` に堆積します.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `PNBR0`  | double | 0.0  | m | パワー堆積の半径中心 |
| `PNBRW`  | double | 0.5  | m | パワー堆積の半径幅 |
| `PNBENG` | double | 80.0 | keV | ビームエネルギー |
| `PNBRTG` | double | 3.0  | m | 接線半径 (`MDLNB=3` / `4` で有効) |

## 10. ICRF (Ion Cyclotron Range of Frequencies)

`MDLIC ≠ 0` のとき有効.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `PICCD`  | double | 0.0 | — | 電流駆動係数 |
| `PICR0`  | double | 0.0 | m | パワー堆積の半径中心 |
| `PICRW`  | double | 0.5 | m | パワー堆積の半径幅 |
| `PICNPR` | double | 2.0 | — | 平行屈折率 $N_\parallel$ |

## 11. ECRF (Electron Cyclotron Range of Frequencies)

`MDLEC ≠ 0` のとき有効.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `PECCD`  | double | 0.0 | — | 電流駆動係数 |
| `PECR0`  | double | 0.0 | m | パワー堆積の半径中心 |
| `PECRW`  | double | 0.2 | m | パワー堆積の半径幅 |
| `PECNPR` | double | 0.0 | — | 平行屈折率 $N_\parallel$ |

## 12. LH (Lower Hybrid Range)

`MDLLH ≠ 0` のとき有効.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `PLHCD`  | double | 0.0 (実装上) | — | 電流駆動係数 |
| `PLHR0`  | double | 0.0 | m | パワー堆積の半径中心 |
| `PLHRW`  | double | 0.2 | m | パワー堆積の半径幅 |
| `PLHNPR` | double | 2.0 | — | 平行屈折率 $N_\parallel$ |
| `PLHTOT` | double | 0.0 | MW | 総 LHRF 入力パワー |

```{note}
`PLHCD` は `tr/trinit.f90` に明示的な初期化がありません. モジュール変数の
Fortran 暗黙初期値に依存するため, 厳密に 0.0 が保証されるとは限りません.
明示的に `tr.set_param("PLHCD", 0.0)` としておくのが安全です.
```

## 13. 文字列 (String)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `KNAMEQ` | CHARACTER(80) | `'eqdata'` | `MODELG=3` で読み込む平衡データファイル名 |

`set_param` ではなく **`set_param_str`** 経由で指定します.

```python
tr.set_param_str("KNAMEQ", "eqdata.ITER01")
```
