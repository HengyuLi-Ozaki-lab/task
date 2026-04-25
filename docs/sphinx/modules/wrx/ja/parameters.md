# サポートされている入力パラメータ

`wrx/wrx_param_registry.f90` には全 **70 件** の `CASE` が登録されています.
`wr` (103 件) よりも少ないのは, `wrx` が単一レイでビームを追跡できるため,
多数レイ対応の `*IN` 配列の一部を省略しているためです.

## 必須・推奨パラメータ

### 必須

`wrx` には明示的な必須パラメータはありません. ただし **波動条件**
(周波数 `RFIN[1]`, 入射点 `RPIN[1]`, `ZPIN[1]`, 初期波数 `RKRIN[1]`) は
意味のある値が必要です.

### 強く推奨 (ITER ECRH 想定)

| 名前 | 推奨値 | 備考 |
|---|---|---|
| `RR`     | 6.2 m | 装置大半径 |
| `BB`     | 5.3 T | トロイダル磁場 |
| `RFIN[1]` | 170e9 Hz | ECRH 周波数 (第二高調波) |
| `RPIN[1]` | 8.5 m | Upper launcher 入射点 |
| `ZPIN[1]` | 1.5 m | 同 |
| `NRAYMAX` | 1 | `wrx` は単一レイで十分 |
| `RBRADAIN[1]` | 0.02 m | ビーム幅 (1/e²) |
| `RCURVAIN[1]` | 200 m | 焦点距離 |

### 推奨ワークフロー

```python
from wrxlib import Wrxlib

with Wrxlib() as wrx:
    # 1. 装置
    wrx.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)

    # 2. ビーム条件 (単一レイ)
    wrx.set_param("NRAYMAX", 1)
    wrx.set_param("RFIN[1]", 170.0e9)
    wrx.set_param("RPIN[1]", 8.5)
    wrx.set_param("ZPIN[1]", 1.5)
    wrx.set_param("RCURVAIN[1]", 200.0)
    wrx.set_param("RBRADAIN[1]", 0.02)

    # 3. 実行
    wrx.run(nray_request=1)
    state = wrx.get_state()

    print(f"総吸収パワー: {state.scalars['pwr_tot']:.4e}")
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

## 2. プラズマ組成

| 名前 | 型 | 意味 |
|---|---|---|
| `NSMAX`    | int | 粒子種数 |
| `NSAMAX_WR`| int | active species (`wr` 互換) |
| `PA[i]`    | double[] | 質量数 |
| `PZ[i]`    | double[] | 電荷数 |
| `PN[i]`    | double[] | 軸上密度 |
| `PNS[i]`   | double[] | 境界密度 |
| `PTPR[i]`  | double[] | 平行温度 |
| `PTPP[i]`  | double[] | 垂直温度 |
| `PTS[i]`   | double[] | 境界温度 |

## 3. プロファイル

| 名前 | 型 | 意味 |
|---|---|---|
| `PROFJ`   | double | 電流プロファイル指数 |
| `PROFN1[i]`, `PROFN2[i]` | double[] | 密度プロファイル指数 |
| `PROFT1[i]`, `PROFT2[i]` | double[] | 温度プロファイル指数 |

## 4. レイ初期条件 (`*IN` 配列)

`wrx` は単一レイでも配列形式で指定します.

| 名前 | 型 | 単位 | 意味 |
|---|---|---|---|
| `RFIN[i]`     | double[] | Hz | 周波数 |
| `RPIN[i]`     | double[] | m | 入射 R |
| `ZPIN[i]`     | double[] | m | 入射 Z |
| `PHIIN[i]`    | double[] | rad | トロイダル角 |
| `RKRIN[i]`    | double[] | — | 初期 k_R |
| `RNZIN[i]`    | double[] | — | $N_\parallel$ |
| `RNPHIIN[i]`  | double[] | — | $N_\varphi$ |
| `ANGZIN[i]`   | double[] | deg | 入射角 (Z) |
| `ANGPHIN[i]`  | double[] | deg | 入射角 (φ) |
| `UUIN[i]`     | double[] | — | 初期パワー |

## 5. ビーム形状 (beam tracing 固有)

`wrx` 独自のパラメータ群. これで集束ビームを表現.

| 名前 | 型 | 単位 | 意味 |
|---|---|---|---|
| `RCURVAIN[i]` | double[] | m | 主軸の曲率半径 (正: 発散, 負: 集束) |
| `RCURVBIN[i]` | double[] | m | 副軸の曲率半径 |
| `RBRADAIN[i]` | double[] | m | 主軸のビーム半径 (1/e² 幅) |
| `RBRADBIN[i]` | double[] | m | 副軸のビーム半径 |
| `MODEWIN[i]`  | int[]    | — | i 番目レイの波動モード (1: O, 2: X) |

## 6. 計算制御

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `NRAYMAX` | int | 1 | レイ本数 |
| `NSTPMAX` | int | 10000 | 1 レイあたり最大ステップ数 |
| `NRSMAX`  | int | -- | 半径方向プロファイル点数 |
| `NRLMAX`  | int | -- | 主半径プロファイル点数 |
| `LMAXNW`  | int | -- | Newton 法最大反復数 |

## 7. 数値積分パラメータ

| 名前 | 型 | 意味 |
|---|---|---|
| `SMAX`   | double | レイ経路の最大長 |
| `DELS`   | double | ステップ幅 |
| `EPSRAY` | double | レイ積分の収束判定 |
| `DELRAY` | double | 計算の刻み幅 |
| `DELDER` | double | 数値微分の刻み幅 |
| `DELKR`  | double | k_R 微分の刻み幅 |
| `EPSNW`  | double | Newton 法の収束判定 |
| `UUMIN`  | double | 最小残存パワー閾値 |

## 8. 動作モード

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MODELG`    | int | 2 | 幾何モデル |
| `MODELQ`    | int | 0 | q プロファイル制御 |
| `MODELP[i]` | int[] | -- | 種 i の波動モデル |
| `MODELV[i]` | int[] | -- | 種 i の速度分布モデル |
| `NCMIN[i]`  | int[] | -- | 共鳴次数 (最小) |
| `NCMAX[i]`  | int[] | -- | 共鳴次数 (最大) |
| `MDLWRI`    | int | -- | wrx 入力モード |
| `MDLWRG`    | int | -- | wrx グラフモード |
| `MDLWRP`    | int | -- | wrx 出力モード |
| `MDLWRQ`    | int | -- | wrx 質モード |
| `MDLWRW`    | int | -- | wrx 波動モード |
