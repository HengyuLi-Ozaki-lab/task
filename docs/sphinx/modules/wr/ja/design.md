# Fortran 設計

`wr` は **幾何光学レイトレース** のソルバです. 既存 `wrx2` バイナリと同一
の物理カーネル (約 20 本の `.f90` ソース) の上に, C ABI 用の薄いエントリ層
(`wr_api.f90`) を被せて `libwrapi.so` を構成しています.

## エントリ層 (`wr_api.f90`)

C から呼ばれる関数は **5 つ** (標準パターン).

| C シンボル | Fortran 側 | 役割 |
|---|---|---|
| `wr_init`           | `wr_api_init`           | `pl_init` → `eq_init` → `wr_init` (内部) で WRCOMM 初期化 |
| `wr_set_param`      | `wr_api_set_param`      | `wr_param_registry::wr_param_set` に委譲 |
| `wr_run`            | `wr_api_run`            | `nray_request` 本のレイを並列にトレース |
| `wr_get_state`      | `wr_api_get_state`      | レイ軌跡 + プロファイルを C 構造体にコピー |
| `wr_finalize`       | `wr_api_finalize`       | レイバッファ解放 + フラグリセット |

```{note}
`wr` は `set_param_str` も `validate` も実装していません. 文字列パラメータは
`pl_*` 経由で継承され, 値域検査は `set_param` 時の即時リジェクトのみ.
```

## `wr_run(nray_request)` の動作

`tr`/`ti`/`fp` の `run(ntmax)` (時間ステップ) と違って, `wr_run` は **空間方向の
レイ積分** を実行します.

1. `nray_request` 本のレイを取り出す (上限 `NRAYMAX`)
2. 各レイの初期条件 (位置 + 波数ベクトル + パワー) をセット
3. ray equation (Hamiltonian: $\dot{\vec{x}} = \partial H/\partial \vec{k}$,
   $\dot{\vec{k}} = -\partial H/\partial \vec{x}$) を `NSTPMAX` ステップまで積分
4. 各ステップで電力吸収量を計算し残存パワー `UU` を減らす
5. `UU < UUMIN` または計算領域を出たら停止
6. 全レイの寄与を半径方向に集計 → `pwr_nrs[]`, `pwr_nrl[]`

## パラメータレジストリ (`wr_param_registry.f90`)

103 件の `CASE` を登録. wr 固有の特徴:

- **レイ初期条件配列**: `RFIN[i]`, `RPIN[i]`, `ZPIN[i]` 等の `*IN` 系列
- **ビーム形状指定**: `RCURVA*`, `RBRADA*` の曲率・幅 (Gaussian 近似)
- **共鳴次数指定**: `NCMIN[i]`, `NCMAX[i]` で電子サイクロトロン高調波の対象範囲

## ライブラリ内部のソース構成

`wr/*.f90` 約 20 本の役割別分類:

| グループ | 主なファイル (推定) | 役割 |
|---|---|---|
| **API 層** | `wr_api.f90`, `wr_param_registry.f90`, `wr_state.f90` | C ABI エントリ |
| **メインソルバ** | `wrcalc.f90`, `wrexec.f90` | レイ積分のメインループ |
| **波動方程式** | `wrdisp.f90` (推定), 関連 | 屈折率テンソルの構築・分散関係 |
| **減衰計算** | `wrdamp.f90` (推定) | サイクロトロン減衰, ランダウ減衰 |
| **共通モジュール** | `wrcomm.f90` | グローバル状態 (WRCOMM) |
| **入出力** | `wrparm.f90`, `wrfile.f90` (推定) | namelist, 結果記録 |
| **対話メニュー** | `wrmenu.f90` (推定) | `wrx2` CLI 専用 |
| **回帰用** | `wrregress.f90` (推定) | Phase 0 ベースライン |
| **グラフィクス** | `wr_graphics_stubs.f90` | ライブラリ版でスタブ化 |

## `wr` と `wrx` の関係

`wr` (geometric optics) と `wrx` (extended / beam tracing) は**別の C ABI**
で別の `.so` ですが, ソースを大きく共有しています:

- `wr`: 各レイは無限小ビーム. ビーム広がりを `NRAYMAX` 本のレイで近似
- `wrx`: 各レイにビーム形状情報 (曲率, 幅) を持たせ, 解析的に展開

詳細は `wrx` モジュールのページ
(`docs/sphinx/modules/wrx/ja/index.md`) を参照.

## メモリ消費

主要バッファ:

```
レイ軌跡: NRAYMAX × NSTPMAX × NRAY_EQ × 8 bytes
半径プロファイル: (NRSMAX + NRLMAX) × 8 bytes × 数本
```

`NRAYMAX=10, NSTPMAX=10000, NRAY_EQ=20` で約 16 MB. `tr`/`fp` より小さい
が, 多数レイ + 高解像度では数百 MB に達することも.

## PIC ビルドの依存関係

```
libwrapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a   (MODELG=3 で使用)
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

## 参考リンク

- [`docs/wr-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/wr-library/architecture.md)
- {ref}`共通アーキテクチャ <portal:common-architecture>`
- `wr/wr_api.h` — C ABI ヘッダ
- `wr/wr_api.f90` — Fortran 側エントリ
- `wr/wr_param_registry.f90` — パラメータレジストリ
