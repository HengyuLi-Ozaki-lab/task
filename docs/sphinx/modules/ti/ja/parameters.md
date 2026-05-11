# サポートされている入力パラメータ

`ti/ti_param_registry.f90` には全 **77 件** の `CASE` が登録されています.
名前は Fortran の `/TI/` ネームリストと一致しています. 既定値は
`ti/tiinit.f90` で設定されます.

## 必須・推奨パラメータ

`ti` は基本的に既定値で動きますが, 物理的に意味のある結果には以下の
上書きが推奨されます.

### 必須 (条件付き)

ti は文字列パラメータを持たず, `KNAMEQ` のような外部ファイル必須はあり
ません. **厳密な意味で必須なパラメータはありません**.

### 強く推奨 (既定値が generic すぎる)

| 名前 | 既定値 | 推奨上書き例 (ITER 想定) |
|---|---|---|
| `RR`     | 3.0 m  | 6.2 m |
| `RA`     | 1.2 m  | 2.0 m |
| `BB`     | 3.0 T  | 5.3 T |
| `RIP`    | 3.0 MA | 15.0 MA |
| `NSMAX`  | 2     | 解析対象に応じて (2-8) |
| `DT`     | 0.01 s | 解析時間に応じて |
| `NTMAX`  | 100    | 同上 |

### 加熱物理を入れる場合の追加

| 名前 | 値 | 効果 |
|---|---|---|
| `MODEL_NB` | 1 | NBI 加熱 ON |
| `MODEL_EC` | 1 | ECRF ON |
| `MODEL_NC` | 1 | NCLASS 新古典輸送 ON (他モデルとは併用不可) |

### 推奨ワークフロー

```python
from tilib import Tilib

with Tilib() as ti:
    # 1. 装置パラメータ
    ti.set_params(RR=6.2, RA=2.0, BB=5.3, RIP=15.0,
                  NSMAX=2,
                  DT=0.01, NTMAX=100)

    # 2. (オプション) 加熱モデル
    ti.set_param("MODEL_NB", 1)

    # 3. ti は validate() を持たないので, set_param 時のエラーで対処
    try:
        ti.run(ntmax=10)
    except Exception as e:
        print(f"Run failed: {e}")
        raise

    state = ti.get_state()
```

---

## 1. 幾何・装置 (Geometry / device)

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `RR`    | double | 3.0 | m | プラズマ大半径 |
| `RA`    | double | 1.2 | m | プラズマ小半径 |
| `RKAP`  | double | 1.5 | — | elongation |
| `RDLT`  | double | 0.0 | — | triangularity |
| `BB`    | double | 3.0 | T | トロイダル磁場 |
| `RIP`   | double | 3.0 | MA | プラズマ電流 |

## 2. プラズマ組成 (Plasma composition)

`ti` は ions / impurities / fast ions の電離度別管理ができるよう, 種別
属性配列が豊富です.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `NSMAX`     | int          | 2   | — | 主粒子種数 |
| `PA[i]`     | double[NSMM] | (種別) | — | 質量数 |
| `PZ[i]`     | double[NSMM] | (種別) | — | 電荷数 |
| `PN[i]`     | double[NSMM] | (種別) | 10²⁰ m⁻³ | 軸上初期数密度 |
| `PNS[i]`    | double[NSMM] | (種別) | 10²⁰ m⁻³ | 境界初期数密度 |
| `PT[i]`     | double[NSMM] | (種別) | keV | 軸上初期温度 |
| `PTPR[i]`   | double[NSMM] | -- | keV | 平行温度 |
| `PTPP[i]`   | double[NSMM] | -- | keV | 垂直温度 |
| `PTS[i]`    | double[NSMM] | (種別) | keV | 境界初期温度 |
| `PU[i]`     | double[NSMM] | 0.0 | m/s | トロイダル流速 |
| `PUS[i]`    | double[NSMM] | 0.0 | m/s | 境界トロイダル流速 |
| `NPA[i]`    | int[NSMM] | -- | — | 種別の質量数 (整数) |
| `ID_NS[i]`  | int[NSMM] | -- | — | 種別 ID |
| `NZMIN_NS[i]` | int[NSMM] | -- | — | 最小電離度 |
| `NZMAX_NS[i]` | int[NSMM] | -- | — | 最大電離度 |
| `NZINI_NS[i]` | int[NSMM] | -- | — | 初期電離度 |

## 3. プロファイル形状 (Profile shape — species 別)

`tr` と違い, ti では **粒子種別にプロファイル形状指数を与えられます**.

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `PROFN1[i]` | double[NSMM] | 2.0 | 種 i の密度プロファイル指数 1 |
| `PROFN2[i]` | double[NSMM] | 0.5 | 種 i の密度プロファイル指数 2 |
| `PROFT1[i]` | double[NSMM] | 2.0 | 種 i の温度プロファイル指数 1 |
| `PROFT2[i]` | double[NSMM] | 1.0 | 種 i の温度プロファイル指数 2 |
| `PROFU1[i]` | double[NSMM] | 2.0 | 種 i の流速プロファイル指数 1 |
| `PROFU2[i]` | double[NSMM] | 1.0 | 種 i の流速プロファイル指数 2 |
| `PROFJ1`   | double | 2.0 | 電流プロファイル指数 1 |
| `PROFJ2`   | double | 1.0 | 電流プロファイル指数 2 |
| `MODEL_PROF`  | int switch | 0 | プロファイル供給ソース |
| `MODEL_NPROF` | int switch | 0 | 密度プロファイル切替 |

## 4. 時間発展・反復制御 (Time evolution / iteration)

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `DT`       | double | 0.01 | s | 時間ステップ幅 |
| `NRMAX`    | int    | 50   | — | 半径メッシュ点数 |
| `NTMAX`    | int    | 100  | — | 時間ステップ数 |
| `NTSTEP`   | int    | 10   | — | スナップショット間隔 |
| `NGTSTEP`  | int    | 2    | — | 時間発展グラフ間隔 |
| `NGRSTEP`  | int    | 100  | — | プロファイルグラフ間隔 |
| `MAXLOOP`  | int    | 100  | — | 内部反復の最大数 |
| `EPSLOOP`  | double | 1e-6 | — | 内部反復の収束判定 |
| `EPSMAT`   | double | 1e-8 | — | 行列ソルバの収束判定 |
| `MATTYPE`  | int switch | 0 | — | 行列ソルバ種別 |

## 5. 境界条件 (Boundary conditions)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MODEL_BND`  | int switch | 0 | 境界条件モデル |
| `BND_VALUE`  | double | -- | 境界値 |

## 6. 拡散・対流係数 (Diffusion / convection)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `DN0`   | double | 0.1 | 密度拡散係数 (基準) |
| `DT0`   | double | 1.0 | 温度拡散係数 (基準) |
| `DU0`   | double | 0.1 | 流速拡散係数 |
| `VDN0`  | double | 0.0 | 密度ピンチ速度 |
| `VDT0`  | double | 0.0 | 温度ピンチ速度 |
| `VDU0`  | double | 0.0 | 流速ピンチ速度 |
| `DR0`   | double | 1.0 | 半径方向係数 (基準) |
| `DRS`   | double | 1.0 | 半径方向係数 (端側) |
| `DN0_NS[i]`  | double[NSMM] | 種別 | 種 i の `DN0` |
| `DT0_NS[i]`  | double[NSMM] | 種別 | 種 i の `DT0` |
| `DU0_NS[i]`  | double[NSMM] | 種別 | 種 i の `DU0` |
| `VDN0_NS[i]` | double[NSMM] | 種別 | 種 i の `VDN0` |
| `VDT0_NS[i]` | double[NSMM] | 種別 | 種 i の `VDT0` |
| `VDU0_NS[i]` | double[NSMM] | 種別 | 種 i の `VDU0` |

## 7. モジュール切替 (Module switches — `MODEL_*`)

`ti` の特徴は **18 個以上の MODEL_* スイッチ** で物理モジュールを ON/OFF
できる点です.

### 平衡・初期化系

| 名前 | 既定値 | 意味 |
|---|---|---|
| `MODEL_EQB` | 0 | 平衡境界モデル |
| `MODEL_EQN` | 0 | 平衡密度モデル |
| `MODEL_EQT` | 0 | 平衡温度モデル |
| `MODEL_EQU` | 0 | 平衡流速モデル |

### 輸送モデル系

| 名前 | 既定値 | 意味 |
|---|---|---|
| `MODEL_KAI` | 31 | 乱流熱輸送 (`tr` の `MDLKAI` と同じ. 既定 CDBM) |
| `MODEL_DRR` | 3  | 粒子拡散モデル (`tr` の `MDLAD`) |
| `MODEL_VR`  | 3  | 熱ピンチモデル (`tr` の `MDLAVK`) |
| `MODEL_NC`  | 0  | NCLASS 新古典輸送 |

### 加熱・電流駆動系

| 名前 | 既定値 | 意味 |
|---|---|---|
| `MODEL_NB`   | 0 | NBI 加熱 |
| `MODEL_EC`   | 0 | ECRF 加熱 |
| `MODEL_LH`   | 0 | LHRF 加熱 |
| `MODEL_IC`   | 0 | ICRF 加熱 |
| `MODEL_CD`   | 0 | 電流駆動全般 |
| `MODEL_SYNC` | 0 | シンクロトロン放射 |

### 粒子源・壁系

| 名前 | 既定値 | 意味 |
|---|---|---|
| `MODEL_NF`  | 0 | 核融合反応 |
| `MODEL_PEL` | 0 | ペレット注入 |
| `MODEL_PSC` | 0 | 粒子源 |

### 動作モード (`MODELG`, `MODELQ`)

| 名前 | 型 | 既定値 | 意味 |
|---|---|---|---|
| `MODELG` | int | 2 | 幾何モデル (`tr`/`eq` と同じ. 既定 = 解析的トロイダル) |
| `MODELQ` | int | 0 | 安全係数モデル |

```{note}
`MODEL_KAI` の許容値は `tr` の `MDLKAI` と同じ列挙です. 詳細な
モデル一覧は `tr` モジュールの輸送モデル付録
(`docs/sphinx/modules/tr/ja/appendix-mdlkai.md`) を参照.
```

```{warning}
`MODEL_NC=1` (NCLASS) と `MODEL_DRR`, `MODEL_VR` を併用しないでください.
NCLASS が独自に新古典係数を計算するため二重計算になります ({doc}`faq` Q5).
```
