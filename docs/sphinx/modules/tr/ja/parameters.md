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
| `PROFJ1` | double | −2.0 | – | `MODELG = 2` のときだけの初期電流分布: ≤ 0 なら抵抗から (j ∝ 1/η, 電場一定); > 0 なら j ∝ (1 − ρ^\|PROFJ1\|)^\|PROFJ2\| |
| `PROFJ2` | double | 1.0 | – | その分布の指数 (`PROFJ1` > 0 のとき; 絶対値を使う) |

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
| `NRMAX`  | int    | 50    | — | TR の径方向メッシュ, 3 から 500 (`TR_MAX_NRMAX`). 1 プロセスに 1 つの値: bpsd がスプラインを再確保するまで (k-yoshimi/bpsd#7), `tr_run` はそのプロセスの最初の準備と異なる `NRMAX` を拒否します; EQ グリッドの変更には `eq_bpsd_put` の再確保も必要 |
| `NTEQIT` | int    | 0     | — | `MODELG = 9` での EQ 再計算のステップ間隔 (0 = しない) |

`set_param` の名前 `eq:NAME` (`eq:RB`, `eq:NRMAX` など) は EQ のレジストリに設定されるため, `MODELG = 9` で `tot` なしに EQ の壁と
グリッドを指定できます. 未知の名前は拒否され, 次の `run` は再度準備を行います. `MODELG = 9` の解が失敗すると, ライブラリ実行は
失敗記録 (`tr_last_error`; `python/trlib/README.md` 参照) を残して終了します.

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
| `CDH`    | double     | 1.0 | 乱流 χ の重み (χ_s = CDH·χ_turb + CNH·χ_NC, χ_NC は新古典 χ `AKNC`) |
| `CNH`    | double     | 1.0 | 新古典 χ の重み (同じ和) |
| `MDNCLS` | int switch | 0   | 0: `MDLAD`, `MDLETA`, `MDLJBS` の新古典モデル; それ以外: 新古典輸送 (粒子と熱), 抵抗 (最初のステップから; 初期分布は `MDLETA` のもの), ブートストラップ電流に NCLASS を使い, `MDLAD`, `MDLAVK`, `MDLJBS` は使わない |
| `AD0`    | double     | 0.5 | 粒子拡散係数: `MDLAD` 2, 3, 4 と NCLASS では χ_turb に対する係数 (`MDDW = 0`, 既定); `MDLAD` 1 では一定の D (`ALP` で質量と電荷の重み) |
| `AV0`    | double     | 0.0 | 乱流内向きピンチ係数 (`MDLAD` 1, 2, 4; `MDLAD` 3 と NCLASS では使わない) |
| `CDP`    | double     | 1.0 | 乱流粒子拡散の重み (D_s = CDP·D_turb + CNP·D_NC; 既定の `MDLAD` 3 と NCLASS では D_turb = AD0·χ_turb) |
| `CNP`    | double     | 1.0 | 新古典粒子拡散の重み (同じ和) |

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
| `TPRST`  | double | 0.1 | のこぎり波の周期 [s], > 0 |
| `MDLNF`  | int switch | 0 | 核融合反応モデル |
| `MODEL_PNF` | int switch | 0 | `trx` から移植した多反応核融合モデル (下記) |
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

`MODEL_PNF`:

| 値 | 反応 | 反応数 | 輸送計算への反映 |
|---|---|---|---|
| 0 (既定) | なし: `MDLNF` のみで決まる | 0 | — |
| 1 | DT | 1 | 核融合の粒子源・核融合パワー・減速時間 (`SNF`, `PNF`, `TAUF`) を `MDLNF` のものに代えて使用 |
| 2, 12 | DT, DD | 4 | 評価のみ (未使用) |
| 3 | DT, DD, DHe³ | 6 | 評価のみ (未使用) |
| 4, 14 | DT, DD, DHe³, TT, THe³ | 13 | 評価のみ (未使用) |

`trx` のモデル (`tr/libnf.f90`, `tr/trpnf_multi.f90`)。`tr_set_param` では `MODEL_PNF`、`&TR` namelist では
`model_pnf` という名前で指定する。MCP サーバはまだ宣言していない。`MODEL_PNF` と `MDLNF` の両方を指定した計算は
拒否される (反応が 1 つのとき両者が同じ粒子源を書き込むため)。それ以外の値は計算の準備時に拒否される。準備済みの
計算で準備をやり直さずに値を変えた場合 (単体の `tr2` の `L` のあと `C`。upstream #259 以降、ライブラリや `tot` からの
設定では次の計算で準備がやり直される)、準備時と異なる 0 以外の値は拒否され、0 以外の `MODEL_PNF` に
`MDLNF` を加えた場合も拒否される。0 にするとモデルは直ちに無効になる。

現時点では `MDLNF` の代わりにはならない:

- `MODEL_PNF = 1` が輸送計算に渡すのは `SNF`, `PNF`, `TAUF` だけである。`PFIN`, `PFCL` および `RNF`, `RTF` の核融合
  の枠は `trx` と同じく 0 のままで、アルファ粒子のパワーは高速イオンのエネルギーに入るだけで熱化粒子には渡らない。したがって
  `MDLNF = 1` のようなアルファ加熱は起こらない。
- 反応する粒子は粒子種 2 と 3 から読み、アルファ粒子は粒子種 4 に渡す (`MDLNF` と同じ)。それらが D, T, He⁴ である
  ことは確認しない。
- 反応率は、テーブル (点は 1, 2, 5, 10, … 1000 keV) の対数を温度の対数の 3 次スプラインで補間したものである。
  D-T 反応率は `MDLNF` のものと、1 から 5 keV では 5 %、5 から 100 keV では 1.3 %、1 から 500 keV のテーブルの点上
  では 6 % 以内で一致する (最後の点 1000 keV ではテーブルの値が `MDLNF` の 1.46 倍)。
- 反応が 2 つ以上のときは輸送計算に何も渡らない (TR の核融合高速イオンの枠は 1 つ)。

確認した内容: 10 keV の D-T ケースで、`MODEL_PNF = 1` による変化が、`trx` の 5 つの不具合を修正し反応率の
補間を TR と同じにした版 (`test_run/baselines/tr_fus_dt_hot/SOURCE.md`) での変化と 2 % 以内で一致する。実測との比較は行っていない。

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
| `PICTOT` | double | 0.0 | MW | 総 ICRF 入力パワー |

## 11. ECRF (Electron Cyclotron Range of Frequencies)

`MDLEC ≠ 0` のとき有効.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `PECCD`  | double | 0.0 | — | 電流駆動係数 |
| `PECR0`  | double | 0.0 | m | パワー堆積の半径中心 |
| `PECRW`  | double | 0.2 | m | パワー堆積の半径幅 |
| `PECNPR` | double | 0.0 | — | 平行屈折率 $N_\parallel$ |
| `PECTOT` | double | 0.0 | MW | 総 ECRF 入力パワー |

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

## 14. 解く方程式と粒子源 (Equations and particle source)

TR が解く方程式 (`TR_EQS_SELECT`, `tr/trprep.f90`) と `tr/trpsc.f90` のガウス型粒子源 (ガスパフ). 密度が動くのは
`MDLEQN = 1` のときだけで, `MDLEQN = 0` の粒子源は何も加えません.

| 名前 | 型 | 既定値 | 単位 | 意味 |
|---|---|---|---|---|
| `MDLEQB` | int switch | 1 | – | 1: B_θ (電流分布) を解く; 0: 初期分布 (`PROFJ1`) のまま. `MODELG = 3` では TR が毎ステップ平衡から ψ を読み直すので電流は発展せず, `MDLEQB` は何も変えない (PLATO の例で測定) |
| `MDLEQN` | int switch | 0 | – | 0: 密度は初期分布のまま; 1: 解く |
| `MDLEQE` | int switch | 0 | – | `MDLEQN = 1` のとき: 0 はイオン密度を解き電子は準中性から; 1 は両方を解く; 2 は電子を解き主イオンは準中性から. 2 は `NSMAX = 2`, 種 2 が電荷 1 の水素か重水素, 不純物密度なし (`MDLIMP = 0`, または `MDLIMP` 1–4 で `PNC` = `PNFE` = 0), UFILE なしのときだけ (`tr/trexec.f90` は他の種を引かずに足す) |
| `MDLPSC` | int switch | 0 | – | 0: 粒子源なし; 1: `NPSCMAX` 個のガウス型粒子源 |
| `NPSCMAX` | int | 1 | – | 粒子源の数, 0..10 (`NPSCM`) |
| `PSCTOT[i]` | double[10] | 0.0 | 10²⁰ s⁻¹ | 粒子源 i の総量 (プラズマ体積で規格化; どのメッシュ点からも遠い粒子源は最も近い所に全量を入れる) |
| `PSCR0[i]` | double[10] | 0.0 | m | 粒子源 i の中心. ρ ではなく小半径のメートル (RA·ρ) |
| `PSCRW[i]` | double[10] | 0.5 | m | 粒子源 i の幅: S ∝ exp(−((RA·ρ − PSCR0)/PSCRW)²); 正で 1e-10 m 以上 |
| `NSPSC[i]` | int[10] | 2 | – | 粒子源 i が供給するイオン種, 2..NSMAX; 電子には PZ 倍 |

`tr_run` は実行前に次を拒否し, `validate()` が報告します: `MDLEQB`, `MDLEQN`, `MDLPSC` が {0, 1} の外;
`MDLEQE` が {0, 1, 2} の外, `MDLEQN = 0` での `MDLEQE` 1 か 2, 上の場合以外の `MDLEQE = 2`; `MDLPSC = 1` のとき
`NPSCMAX` が 0..10 の外, 粒子源 i ≤ `NPSCMAX` ごとに `NSPSC[i]` が 2..NSMAX の外, `PSCRW[i]` ≤ 0 か 1e-10 m 未満,
`|PSCR0[i]|` が 1e10 m 超. どれも配列の範囲外参照, NaN, 黙って別の値として動く, 誤った密度, あるいは `tr_prep`
の中での停止 (`MDLEQB = 2`, `MDLEQN` なしの `MDLEQE`) になっていました. 負の幅は絶対値と同じガウス分布なので,
符号が意味を持たないよう拒否します. UFILE (`MDLUF ≠ 0`) では `tr_prep` が NSMAX を変えうる (`TR_EQS_SELECT` は
UFILE に不純物があれば炭素を加える) ので, 粒子源は種 2 に限り, `MDLEQE = 2` は拒否します. 種が決まるのは
`tr_prep` の中なので, 意図した制限です.

NCLASS (`MDNCLS ≠ 0`) と `MDLEQE = 1` (両方の密度を解き, 準中性なし) では, PLATO の例が 10 µs の 100 ステップ
以内に負の温度で止まりました. `MDLEQE` 0 と 2 では動きます.
