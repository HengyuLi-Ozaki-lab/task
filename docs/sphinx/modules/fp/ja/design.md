# Fortran 設計

`fp` は **Fokker-Planck 方程式** を 5D 位相空間 (位置×運動量×ピッチ角×種別×時間)
で解くソルバです. 既存 `fpx2` バイナリと同一の物理カーネル (`fpcalc.f90`,
`fpcalw.f90`, `fpbounce.f90` など約 51 本の `.f90` ソース) の上に, C ABI 用の
薄いエントリ層 (`fp_api.f90`) を被せて `libfpapi.so` を構成しています.

## エントリ層 (`fp_api.f90`)

C から呼ばれる関数は **6 つ** (`eq` と同じ拡張 ABI).

| C シンボル | Fortran 側 | 役割 |
|---|---|---|
| `fp_init`           | `fp_api_init`           | `pl_init` → `eq_init` → `fp_init` (内部) で FPCOMM 初期化 |
| `fp_set_param`      | `fp_api_set_param`      | `fp_param_registry::fp_param_set` に委譲 |
| `fp_set_param_str`  | `fp_api_set_param_str`  | 文字列版 (`KNAMEQ`) |
| `fp_run`            | `fp_api_run`            | 時間ステップ進行. 5D グリッドの離散化 + 反復ソルバ |
| `fp_get_state`      | `fp_api_get_state`      | モーメント量を C 構造体にコピー |
| `fp_finalize`       | `fp_api_finalize`       | 大規模配列の解放 |

```{note}
`fp` には現在 `fp_validate` がありません. 将来 issue #143 で追加予定.
```

## パラメータレジストリ (`fp_param_registry.f90`)

55 件の `CASE` を登録. fp 固有のグループ:

- **5D グリッド寸法**: `NRMAX`, `NPMAX`, `NTHMAX`, `NSAMAX`, `NSBMAX`
- **位相空間境界**: `PMAX[i]` (種別ごとの最大運動量)
- **物理スイッチ**: `MODELE` (相対論モード), `MODELS` (粒子源), `MODELC`
  (衝突), `MODELW` (波動)

`KNAMEQ` は `fp_param_set_str` で. 内部では `pl_init` から `KNAMEQ` を継承
するので, 上書きしたい場合のみ呼ぶ形.

## ライブラリ内部のソース構成

`fp/*.f90` 約 51 本を役割別に分類すると:

| グループ | 主なファイル | 役割 |
|---|---|---|
| **API 層** | `fp_api.f90`, `fp_param_registry.f90`, `fp_state.f90` | C ABI エントリ |
| **メインソルバ** | `fpcalc.f90`, `fpcalcn.f90`, `fpcalcnr.f90`, `fpsetn.f90` | Fokker-Planck 方程式の差分化 |
| **衝突項** | `fpcalc*.f90` (各種), `fpcoul.f90`, `fpcoulw.f90` | クーロン衝突演算子 |
| **波動項** | `fpcalw.f90`, `fpcalwm.f90`, `fpcaltp.f90` | 波動拡散テンソル |
| **粒子源** | `fpsource.f90`, `fpnbi.f90` | NBI, fusion などの粒子源 |
| **境界条件** | `fpbounce.f90`, `fpbroadcast.f90` | バウンス平均, 境界処理 |
| **平衡データ** | `cdbm.f90`, `cdbmfp.f90` | CDBM 経由の平衡情報取り込み |
| **共通モジュール** | `fpcomm.f90` (推定), 関連 `_mod.f90` | グローバル状態 |
| **入出力** | `fpparm.f90`, `fpfile.f90` (推定) | namelist, 結果記録 |
| **対話メニュー** | `fpmenu.f90` (推定) | `fpx2` CLI 専用 |
| **回帰用** | `fpregress.f90` (推定) | Phase 0 ベースライン |
| **グラフィクス** | `fp_graphics_stubs.f90` | ライブラリ版でスタブ化 |

## 計算コストとメモリ

`fp` のメモリ消費は **5D 配列の積** で決まります:

```
メモリ ≈ NRMAX × NPMAX × NTHMAX × NSAMAX × 8 bytes × (≈10 本の 5D 配列)
```

例: `NRMAX=50, NPMAX=100, NTHMAX=50, NSAMAX=2` → 約 200 MB.
`NPMAX=200, NTHMAX=100` (高解像度) → 約 1.6 GB.

時間複雑度は `O(NRMAX × NPMAX × NTHMAX × LMAXFP)` (各時間ステップ).

## PIC ビルドの依存関係

```
libfpapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a   (MODELG=3 で使用)
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

## 参考リンク

- [`docs/fp-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/fp-library/architecture.md)
- {ref}`共通アーキテクチャ <portal:common-architecture>`
- `fp/fp_api.h` — C ABI ヘッダ
- `fp/fp_api.f90` — Fortran 側エントリ
- `fp/fp_param_registry.f90` — パラメータレジストリ
