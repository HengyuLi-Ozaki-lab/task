# Fortran 設計

`ti` ライブラリは, 既存 `tix2` バイナリと同一の物理カーネル (`ticalc.f90`,
`ticoef.f90`, `tinclass.f90` など約 20 本の `.f90` ソース) の上に, C ABI 用
の薄いエントリ層 (`ti_api.f90`) を被せて `libtiapi.so` を構成しています.
共通の 3 層設計は {ref}`共通アーキテクチャ <portal:common-architecture>` を
参照してください.

## エントリ層 (`ti_api.f90`)

C から呼ばれる関数は **5 つ** (標準パターン). `eq` の 6 番目 ABI のような
拡張はありません.

| C シンボル | Fortran 側 | 役割 |
|---|---|---|
| `ti_init`       | `ti_api_init`       | `pl_init` → `eq_init` → `ti_init` (内部) で TICOMM 初期化 |
| `ti_set_param`  | `ti_api_set_param`  | `ti_param_registry::ti_param_set` に委譲 |
| `ti_run`        | `ti_api_run`        | 時間ステップ進行. 内部反復ソルバ (MAXLOOP) 含む |
| `ti_get_state`  | `ti_api_get_state`  | TICOMM のスカラー・プロファイルを C 構造体にコピー |
| `ti_finalize`   | `ti_api_finalize`   | DEALLOCATE + フラグリセット |

すべて `BIND(C, NAME="ti_xxx")` で C ABI シンボルを固定しています.

```{note}
`ti` には現在 `ti_set_param_str` や `ti_validate` がありません. 文字列
パラメータは設計上不要 (平衡データは `pl_*` 経由) で, validate API は
将来 issue #143 で追加予定.
```

## パラメータレジストリ (`ti_param_registry.f90`)

77 件の `CASE` を `tr` と同じ `SELECT CASE` 方式で公開. ti 固有の特徴:

- **多くの配列パラメータ**: `PROFN1[i]`, `PROFN2[i]`, `DT0_NS[i]` など, 種別
  ごとのパラメータが豊富 (NS-suffix がついた配列)
- **MODEL_* スイッチが 18 個以上**: tr の `MDL*` よりさらに細分化
- **NRMAX が runtime 可変**: tr では固定だったが ti では `set_param("NRMAX", n)`
  で実行時に変えられる

## ライブラリ内部のソース構成

`ti/*.f90` 約 20 本の役割別分類:

| グループ | 主なファイル | 役割 |
|---|---|---|
| **API 層** | `ti_api.f90`, `ti_param_registry.f90`, `ti_state.f90` | C ABI エントリ |
| **メインループ** | `timain.f90`, `tiexec.f90`, `tiprep.f90` | 時間発展の司令塔 |
| **物理計算** | `ticalc.f90`, `ticoef.f90`, `ticdbm.f90`, `tinclass.f90` | 輸送係数・新古典・CDBM |
| **共通モジュール** | `ticomm.f90` | グローバル状態 (TICOMM) |
| **粒子源・原子** | `tiadas.f90`, `tisource.f90` | 不純物原子過程, 粒子源 |
| **入出力** | `tiparm.f90`, `tirecord.f90`, `tigout.f90` | namelist, 結果記録, グラフ |
| **対話メニュー** | `timenu.f90` | `tix2` CLI 専用 |
| **回帰用** | `tiregress.f90` | Phase 0 ベースライン出力 |
| **グラフィクス** | `ti_graphics_stubs.f90` | ライブラリ版でスタブ化 |
| **初期化** | `tiinit.f90` | 既定値設定 |

## `tr` との設計上の違い

| | `tr` | `ti` |
|---|---|---|
| **C ABI 関数** | 5 + `set_param_str` (PR #172 後) + `validate` | 5 (拡張なし) |
| **NRMAX** | 固定 | runtime 可変 (`set_param`) |
| **粒子種管理** | `NSMAX` のみ | `NSMAX` + active `NSA_MAX` の二段 |
| **モデル切替数** | ~10 (`MDL*`) | 18+ (`MODEL_*`) |
| **依存モジュール** | `pl`, `eq`, `bpsd`, `mtxp` | `pl`, `eq`, `bpsd`, `mtxp` (同じ) |

## PIC ビルドの依存関係

```
libtiapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a   (MODEL_EQ* モードで参照)
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

## 参考リンク

- [`docs/ti-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/ti-library/architecture.md)
- {ref}`共通アーキテクチャ <portal:common-architecture>`
- `ti/ti_api.h` — C ABI ヘッダ
- `ti/ti_api.f90` — Fortran 側エントリ
- `ti/ti_param_registry.f90` — パラメータレジストリ
