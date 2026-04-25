# Fortran 設計

`wrx` は `wr` (geometric optics) の **拡張版** で **beam tracing** 機能を
提供します. 既存 `wrx2` バイナリと同一の物理カーネル (約 27 本の `.f90`
ソース) の上に, C ABI 用の薄いエントリ層 (`wrx_api.f90`) を被せて
`libwrxapi.so` を構成しています.

## エントリ層 (`wrx_api.f90`)

C から呼ばれる関数は **5 つ** (標準パターン).

| C シンボル | Fortran 側 | 役割 |
|---|---|---|
| `wrx_init`       | `wrx_api_init`       | `pl_init` → `eq_init` → `wrx_init` で WRXCOMM 初期化 |
| `wrx_set_param`  | `wrx_api_set_param`  | `wrx_param_registry::wrx_param_set` に委譲 |
| `wrx_run`        | `wrx_api_run`        | beam tracing 実行. 各レイにビーム形状を追跡 |
| `wrx_get_state`  | `wrx_api_get_state`  | レイ結果 + プロファイルを C 構造体にコピー |
| `wrx_finalize`   | `wrx_api_finalize`   | レイ + ビーム形状バッファ解放 |

## `wrx_run` の動作

`wr_run(nray_request)` と似ていますが, 各レイに **ビーム形状テンソル**
を伴って積分します.

1. `NRAYMAX` 本のレイを取り出す
2. 各レイの初期条件 (位置 + 波数 + パワー + **曲率** `RCURVAIN` + **幅** `RBRADAIN`) をセット
3. ray equation を積分. 同時にビーム形状テンソルも時間発展:
   - 曲率 $\partial^2 \phi / \partial x^2$ の伝搬
   - ビーム幅の伝搬
4. 各ステップで電力吸収を計算 (ビーム断面を考慮)
5. 停止条件 (`UUMIN` 到達, 計算領域離脱, 最大ステップ数)

## パラメータレジストリ (`wrx_param_registry.f90`)

70 件の `CASE` を登録. wrx 固有の特徴:

- **ビーム形状配列**: `RCURVAIN[i]`, `RCURVBIN[i]`, `RBRADAIN[i]`, `RBRADBIN[i]`
  — 各レイの曲率と幅を定義
- **`NSAMAX_WR`**: active species 数を `wr` 互換で持たせている
- 単一レイ用スカラー (`RF`, `RPI` 等) は `wr` ほど網羅的でない — 配列形式を
  使うのが前提

## ライブラリ内部のソース構成

`wrx/*.f90` 約 27 本の役割別分類 (ファイル名は推定):

| グループ | 主なファイル | 役割 |
|---|---|---|
| **API 層** | `wrx_api.f90`, `wrx_param_registry.f90`, `wrx_state.f90` | C ABI エントリ |
| **メインソルバ** | `wrxcalc.f90`, `wrxexec.f90` | レイ積分 + ビーム形状発展 |
| **ビーム形状** | `wrxbeam.f90` (推定) | 曲率・幅テンソルの時間発展 |
| **波動方程式** | `wrxdisp.f90` (推定) | 屈折率テンソル (wr と共通の可能性) |
| **減衰計算** | `wrxdamp.f90` (推定) | サイクロトロン減衰, ランダウ減衰 |
| **共通モジュール** | `wrxcomm.f90` | グローバル状態 (WRXCOMM) |
| **入出力** | `wrxparm.f90`, `wrxfile.f90` (推定) | namelist, 結果記録 |
| **対話メニュー** | `wrxmenu.f90` (推定) | `wrx2` CLI 専用 |
| **回帰用** | `wrxregress.f90` (推定) | Phase 0 ベースライン |
| **グラフィクス** | `wrx_graphics_stubs.f90` | ライブラリ版でスタブ化 |

## `wr` との実装上の違い

| | `wr` | `wrx` |
|---|---|---|
| **レイ状態変数** | 位置 + 波数 + パワー (≈20 double/step) | 位置 + 波数 + パワー + **曲率 + 幅** (≈40 double/step) |
| **計算コスト (レイ本数 N)** | O(N × NSTPMAX) | O(N × NSTPMAX) (比例係数 ≈ 2 倍) |
| **吸収モデル** | ポイントソース | **ガウシアン断面** 積分 |
| **同じ物理精度を得るのに必要なレイ数** | 10–50 | **1** (または数本) |

## メモリ消費

```
レイ軌跡 (wrx): NRAYMAX × NSTPMAX × (20–40 double) × 8 bytes
ビーム形状データ: NRAYMAX × NSTPMAX × (10–20 double) × 8 bytes
```

`NRAYMAX=1, NSTPMAX=10000` で約 3–4 MB. `wr` とほぼ同等のメモリでありながら
物理精度が高いのが `wrx` の利点.

## PIC ビルドの依存関係

```
libwrxapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a   (MODELG=3 で使用)
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

## 参考リンク

- [`docs/wrx-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/wrx-library/architecture.md)
- {ref}`共通アーキテクチャ <portal:common-architecture>`
- `wrx/wrx_api.h` — C ABI ヘッダ
- `wrx/wrx_api.f90` — Fortran 側エントリ
- `wrx/wrx_param_registry.f90` — パラメータレジストリ
- `wr` モジュール設計ページ (`docs/sphinx/modules/wr/ja/design.md`)
  — 共通する物理的背景
