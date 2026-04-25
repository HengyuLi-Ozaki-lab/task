# サポートされている入力パラメータ

`fp/fp_param_registry.f90` には全 **55 件** の `CASE` が登録されています.
名前は Fortran の `/FP/` ネームリストと一致しています.

## 必須・推奨パラメータ

### 必須 (条件付き)

| 条件 | 必須パラメータ | 理由 |
|---|---|---|
| `MODELG ∈ {3, 5, 8}` | **`KNAMEQ`** (文字列) | 平衡データファイル. `set_param_str` 経由で指定 |
| `MODELG = 2` (既定) | — | 解析的トロイダル幾何. 必須なし |

### 強く推奨

`fp` は 5D グリッドを使うため, **解像度パラメータ** が結果品質を直接決めます.

| 名前 | 既定値 | 推奨上書き |
|---|---|---|
| `RR`     | 3.0 m | 装置に応じて |
| `RA`     | 1.2 m | 同上 |
| `BB`     | 3.0 T | 同上 |
| `RIP`    | 3.0 MA | 同上 |
| `NSMAX`  | (1) | 解析対象の種数 |
| `NSAMAX` | (1) | active species 数 |
| `NPMAX`  | 50  | 80–200 (解析精度に応じて) |
| `NTHMAX` | 25  | 50–100 |
| `DELT`   | 0.001 s | 高速イオン解析なら 0.0001 程度 |

### 推奨ワークフロー

```python
from fplib import Fplib

with Fplib() as fp:
    # 1. 装置パラメータ
    fp.set_params(RR=6.2, RA=2.0, BB=5.3, RIP=15.0)

    # 2. 5D グリッド解像度
    fp.set_params(NSMAX=2, NSAMAX=2, NSBMAX=2,
                  NPMAX=100, NTHMAX=50, NRMAX=20,
                  DELT=0.0005, NTMAX=50)

    # 3. (オプション) EQDSK 経由なら
    # fp.set_param("MODELG", 3)
    # fp.set_param_str("KNAMEQ", "eqdata.ITER01")

    fp.run(ntmax=10)
    state = fp.get_state()
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
| `RIP`   | double | 3.0 | MA | プラズマ電流 |

## 2. 5D グリッド寸法 (Phase-space dimensions)

`fp` の特徴的な部分. 計算コストはこれらの積に比例します.

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `NRMAX`  | int | 20 | 半径方向メッシュ点数 |
| `NPMAX`  | int | 50 | 運動量空間メッシュ点数 |
| `NTHMAX` | int | 25 | ピッチ角空間メッシュ点数 |
| `NTMAX`  | int | 100 | 時間ステップ数 |
| `NAVMAX` | int | 100 | 平均化用ステップ数 |

```{note}
メモリ消費量は約 $N_R \times N_P \times N_\theta \times N_{SA} \times 80$ bytes
(プログラム内の主要配列の合計). `NPMAX=200, NTHMAX=100, NRMAX=50, NSAMAX=2` で
約 1.6 GB を要します.
```

## 3. プラズマ組成 (Plasma composition)

| 名前 | 型 | 意味 |
|---|---|---|
| `NSMAX`     | int | 全粒子種数 |
| `NSAMAX`    | int | **active species** — 分布関数を解く種の数 |
| `NSBMAX`    | int | **bulk species** — 衝突相手の種の数 |
| `NS_NSA[i]` | int[] | active 種 i が `NSMAX` のどれにマップされるか |
| `NS_NSB[i]` | int[] | bulk 種 i が `NSMAX` のどれにマップされるか |
| `PA[i]`     | double[] | 質量数 |
| `PZ[i]`     | double[] | 電荷数 |
| `PN[i]`     | double[] | 軸上初期数密度 [10²⁰ m⁻³] |
| `PNS[i]`    | double[] | 境界初期数密度 |
| `PT[i]`     | double[] | 軸上初期温度 [keV] (Maxwellian 等価) |
| `PTPR[i]`   | double[] | 平行温度 |
| `PTPP[i]`   | double[] | 垂直温度 |
| `PTS[i]`    | double[] | 境界初期温度 |
| `PMAX[i]`   | double[] | 種 i の最大運動量 (規格化単位) |

## 4. 時間発展・反復 (Time evolution / iteration)

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `DELT`   | double | 0.001 | s | 時間ステップ幅 |
| `EPSFP`  | double | 1e-6 | — | 内部反復の収束判定 |
| `LMAXFP` | int    | 100  | — | 内部反復の最大数 |

## 5. 半径領域 (Radial domain)

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `R1`    | double | 0.0 | — | 内側境界 (規格化半径) |
| `DELR1` | double | 0.05 | — | メッシュ幅 |
| `RMIN`  | double | 0.0 | — | 計算範囲の最小値 |
| `RMAX`  | double | 1.0 | — | 計算範囲の最大値 |

## 6. 物理パラメータ (Physical parameters)

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `E0`    | double | 0.0 | V/m | 軸上の誘導電場 |
| `ZEFF`  | double | 1.0 | — | 実効電荷 (背景プラズマ) |

## 7. 波動加熱パワー (Wave heating)

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `PABS_EC` | double | 0.0 | MW | ECRF 吸収パワー |
| `PABS_LH` | double | 0.0 | MW | LHRF 吸収パワー |
| `PABS_FW` | double | 0.0 | MW | Fast wave 吸収パワー |
| `PABS_WR` | double | 0.0 | MW | レイトレース起源 |
| `PABS_WM` | double | 0.0 | MW | フルウェーブ起源 |
| `RF_WM`   | double | 0.0 | Hz | フルウェーブ周波数 |

## 8. モード切替 (Mode switches)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MODELG` | int | 2 | 幾何モデル (2: 解析, 3: TASK/EQ, 5: EQDSK) |
| `MODELE` | int | 1 | エネルギー作用素 (1: 線形, 2: 相対論的) |
| `MODELR` | int | — | 半径方向モデル |
| `MODELS` | int | 0 | 粒子源モデル |
| `MODELD` | int | — | 拡散モデル |
| `MODELC` | int | 0 | 衝突モデル |
| `MODELW` | int | 0 | 波動モデル |

## 9. 物理サブモジュール切替 (`MODEL_*`)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MODEL_NBI`     | int | 0 | NBI 粒子源 |
| `MODEL_WAVE`    | int | 0 | 波動駆動 (LH, FW 等) |
| `MODEL_DISRUPT` | int | 0 | disruption (ランナウェイ) モード |
| `MODEL_BS`      | int | 0 | bootstrap 電流の寄与 |
| `MODEL_LOSS`    | int | 0 | 損失プロセス |
| `MODEL_SYNCH`   | int | 0 | シンクロトロン放射 |
| `MODEL_FOW`     | int | 0 | finite-orbit-width 効果 |

## 10. 文字列パラメータ (`set_param_str` 経由)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `KNAMEQ` | CHARACTER(80) | (`pl_init` から継承) | 平衡データファイル名 |

```python
fp.set_param_str("KNAMEQ", "eqdata.ITER01")
```
