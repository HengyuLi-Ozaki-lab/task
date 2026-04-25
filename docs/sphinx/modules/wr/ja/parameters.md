# サポートされている入力パラメータ

`wr/wr_param_registry.f90` には全 **103 件** の `CASE` が登録されています.
名前は Fortran の `/WR/` ネームリストと一致しています. 全モジュール中で
最も登録パラメータが多い (レイ初期条件の細かい指定が必要なため).

## 必須・推奨パラメータ

### 必須

`wr` は **`KNAMEQ` のような明示的必須パラメータはありません**. ただし
レイをトレースする以上, **波動条件** (周波数 + 入射点 + 初期波数ベクトル)
は意味のある値が必要です.

### 強く推奨 (実用的に必須)

| 名前 | 既定値 | 推奨上書き例 (ITER ECRH 想定) |
|---|---|---|
| `RR`     | 3.0 m | 6.2 m |
| `BB`     | 3.0 T | 5.3 T |
| `RF`     | -- | 170e9 Hz (ECRH) または 3.7e9 (LH) |
| `RPI`    | -- | 8.0 m (ITER 外側からの入射) |
| `ZPI`    | -- | 0.0 m (ミッドプレーン入射) |
| `RKR0`   | -- | 1.0 (規格化波数) |
| `RNZI`   | -- | 入射波の平行屈折率 N∥ |
| `NRAYMAX` | 1 | ビーム近似なら 5 等 |

### 推奨ワークフロー

```python
from wrlib import Wrlib

with Wrlib() as wr:
    # 1. 装置パラメータ
    wr.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)

    # 2. 波動条件
    wr.set_params(RF=170.0e9,                # 170 GHz ECRH
                  RPI=8.0, ZPI=0.0,           # 入射点
                  RKR0=1.0,                   # 初期波数
                  NRAYMAX=1)                  # 単一レイ

    # 3. レイトレース実行
    wr.run(nray_request=1)
    state = wr.get_state()

    print(f"ピーク R = {state.scalars['pos_pwrmax_rs']:.3f}")
    print(f"ピーク値 = {state.scalars['pwrmax_rs']:.4e}")
```

---

## 1. 幾何・装置 (Geometry / device)

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `RR`    | double | 3.0 | m | プラズマ大半径 |
| `RA`    | double | 1.2 | m | プラズマ小半径 |
| `RB`    | double | 1.4 | m | 壁の小半径 |
| `RKAP`  | double | 1.0 | — | elongation |
| `RDLT`  | double | 0.0 | — | triangularity |
| `BB`    | double | 3.0 | T | トロイダル磁場 |
| `Q0`    | double | 1.0 | — | 中心 q |
| `QA`    | double | 3.0 | — | 表面 q |
| `RIP`   | double | 3.0 | MA | プラズマ電流 |

## 2. プラズマ組成 (Plasma composition)

| 名前 | 型 | 意味 |
|---|---|---|
| `NSMAX`     | int | 粒子種数 |
| `PA[i]`     | double[] | 質量数 |
| `PZ[i]`     | double[] | 電荷数 |
| `PN[i]`     | double[] | 軸上密度 [10²⁰ m⁻³] |
| `PNS[i]`    | double[] | 境界密度 |
| `PT[i]`     | double[] | 軸上温度 [keV] |
| `PTPR[i]`   | double[] | 平行温度 |
| `PTPP[i]`   | double[] | 垂直温度 |
| `PTS[i]`    | double[] | 境界温度 |
| `PU[i]`     | double[] | 軸上流速 |
| `PUS[i]`    | double[] | 境界流速 |
| `PZCL[i]`   | double[] | 衝突周波数 |

## 3. プロファイル形状 (Profile shape — species 別)

| 名前 | 型 | 意味 |
|---|---|---|
| `PROFN1[i]` | double[] | 種 i の密度プロファイル指数 1 |
| `PROFN2[i]` | double[] | 種 i の密度プロファイル指数 2 |
| `PROFT1[i]` | double[] | 種 i の温度プロファイル指数 1 |
| `PROFT2[i]` | double[] | 種 i の温度プロファイル指数 2 |
| `PROFU1[i]` | double[] | 種 i の流速プロファイル指数 1 |
| `PROFU2[i]` | double[] | 種 i の流速プロファイル指数 2 |
| `MODEL_PROF`  | int | プロファイル供給ソース |
| `MODEL_NPROF` | int | 密度プロファイル切替 |

## 4. ITB プロファイル (Internal Transport Barrier)

| 名前 | 型 | 意味 |
|---|---|---|
| `RHOITB[i]` | double[] | ITB の規格化半径 |
| `PNITB[i]`  | double[] | ITB 内側の密度 |
| `PTITB[i]`  | double[] | ITB 内側の温度 |
| `PUITB[i]`  | double[] | ITB 内側の流速 |

## 5. 中性粒子・SOL (Neutrals / SOL)

| 名前 | 型 | 意味 |
|---|---|---|
| `RHOMIN` | double | 最小 q の規格化半径 |
| `QMIN`   | double | 最小 q |
| `RHOEDG` | double | プラズマ縁の規格化半径 |
| `PPN0`   | double | 中性粒子密度 (圧力) |
| `PTN0`   | double | 中性粒子温度 |

## 6. 単一レイ用入射条件 (Single ray)

`NRAYMAX=1` のときに使う設定値. 複数レイの場合は §7 の `*IN` 配列を使用.

| 名前 | 型 | 単位 | 意味 |
|---|---|---|---|
| `RF`      | double | Hz | 波の周波数 |
| `RPI`     | double | m | 入射点 R |
| `ZPI`     | double | m | 入射点 Z |
| `PHII`    | double | rad | 入射点トロイダル角 |
| `RNZI`    | double | — | 平行屈折率 $N_\parallel$ |
| `RNPHII`  | double | — | トロイダル屈折率 $N_\varphi$ |
| `RKR0`    | double | — | 初期 R 方向波数 |
| `UUI`     | double | — | 初期パワー (規格化, 既定 1.0) |
| `RCURVA`  | double | m | ビーム曲率半径 (主軸) |
| `RCURVB`  | double | m | ビーム曲率半径 (副軸) |
| `RBRADA`  | double | m | ビーム半径 (主軸) |
| `RBRADB`  | double | m | ビーム半径 (副軸) |

## 7. 複数レイ用入射条件 (Multi-ray, `*IN` 配列)

`NRAYMAX>1` のときに各レイの初期条件を 1-origin で指定.

| 名前 | 型 | 意味 |
|---|---|---|
| `RFIN[i]`     | double[] | i 番目レイの周波数 |
| `RPIN[i]`     | double[] | i 番目レイの入射 R |
| `ZPIN[i]`     | double[] | 同 Z |
| `PHIIN[i]`    | double[] | 同 トロイダル角 |
| `RKRIN[i]`    | double[] | 同 初期 k_R |
| `RNZIN[i]`    | double[] | 同 N∥ |
| `RNPHIIN[i]`  | double[] | 同 N_φ |
| `ANGZIN[i]`   | double[] | 入射角 (Z 方向) |
| `ANGPHIN[i]`  | double[] | 入射角 (φ 方向) |
| `UUIN[i]`     | double[] | 同 初期パワー |
| `RCURVAIN[i]` | double[] | 同 曲率半径 A |
| `RCURVBIN[i]` | double[] | 同 曲率半径 B |
| `RBRADAIN[i]` | double[] | 同 ビーム半径 A |
| `RBRADBIN[i]` | double[] | 同 ビーム半径 B |
| `MODEWIN[i]`  | int[]    | i 番目レイの波動モード |

## 8. 計算領域・解像度 (Computation domain)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `Rmax_wr` | double | -- | 計算領域 最大 R |
| `Rmin_wr` | double | -- | 計算領域 最小 R |
| `Zmax_wr` | double | -- | 計算領域 最大 Z |
| `Zmin_wr` | double | -- | 計算領域 最小 Z |
| `NRAYMAX` | int | 1 | レイ本数 |
| `NSTPMAX` | int | 10000 | 1 レイあたり最大ステップ数 |
| `NRSMAX`  | int | -- | 半径方向プロファイル点数 |
| `NRLMAX`  | int | -- | 主半径方向プロファイル点数 |
| `LMAXNW`  | int | -- | Newton 法の最大反復数 |

## 9. 数値積分 (Numerical integration)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `SMAX`   | double | -- | レイ経路の最大長 |
| `DELS`   | double | -- | レイ経路のステップ幅 |
| `EPSRAY` | double | -- | レイ積分の収束判定 |
| `DELRAY` | double | -- | レイ計算の刻み幅 |
| `DELDER` | double | -- | 数値微分の刻み幅 |
| `DELKR`  | double | -- | k_R 微分の刻み幅 |
| `EPSNW`  | double | -- | Newton 法の収束判定 |
| `UUMIN`  | double | -- | 最小残存パワー閾値 (これ以下で停止) |

## 10. 共鳴・閾値 (Resonance / thresholds)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `nres_max`     | int | -- | 共鳴最大次数 |
| `nres_type`    | int | -- | 共鳴タイプ |
| `pne_threshold` | double | -- | カットオフ閾値 |
| `bdr_threshold` | double | -- | 境界閾値 |

## 11. 動作モード (Mode switches)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MODELG`     | int | 2 | 幾何モデル (`tr`/`eq` と同じ) |
| `MODELQ`     | int | 0 | q プロファイル制御 |
| `MODEFW`     | int | 0 | 波動モデル (W 関連) |
| `MODEFR`     | int | 0 | 半径方向モデル |
| `IDEBUG`     | int | 0 | デバッグ出力 |
| `MODELP[i]`  | int[] | -- | 種 i の波動モデル |
| `MODELV[i]`  | int[] | -- | 種 i の速度分布モデル |
| `NCMIN[i]`   | int[] | -- | 共鳴次数 (最小) |
| `NCMAX[i]`   | int[] | -- | 共鳴次数 (最大) |
| `mode_beam`  | int | 0 | ビーム/ペンシル切替 |
| `MDLWRI`     | int | -- | wr 入力モード |
| `MDLWRG`     | int | -- | wr グラフモード |
| `MDLWRP`     | int | -- | wr 出力モード |
| `MDLWRQ`     | int | -- | wr 質モード |
| `MDLWRW`     | int | -- | wr 波動モード |
| `MODEW`      | int | 0 | 波動偏波モード |
| `mode_wline` | int | 0 | 波動線モード |
| `RF_PL`      | double | -- | プラズマ周波数 (内部参照用) |
