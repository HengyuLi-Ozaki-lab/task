# Fortran 設計

`tot` は **オーケストレータ** で, 既存の eq / tr / ti / fp / wr / wrx 物理
カーネルを 1 つのライブラリ (`libtotapi.so`) に統合します. C ABI 用の薄い
エントリ層 (`tot_api.f90`) + ルーティング用パラメータレジストリ
(`tot_param_registry.f90`) + 約 7 本の固有 `.f90` ソースで構成されます.

## エントリ層 (`tot_api.f90`)

C から呼ばれる関数は **6 つ** (`eq`/`fp` と同じ拡張版).

| C シンボル | Fortran 側 | 役割 |
|---|---|---|
| `tot_init`           | `tot_api_init`           | `pl_init` → `eq_init` → `tr_init` → `ti_init` → `fp_init` → `wr_init` → `wrx_init` を順次実行 |
| `tot_set_param`      | `tot_api_set_param`      | プレフィックスを見て該当 `<mod>_param_set` に転送 |
| `tot_set_param_str`  | `tot_api_set_param_str`  | 同上 (文字列版) |
| `tot_run`            | `tot_api_run`            | `ntmax` ステップ. 各サブモジュールを連携させる |
| `tot_get_state`      | `tot_api_get_state`      | `TrState` ベース + presence flags を C 構造体にコピー |
| `tot_finalize`       | `tot_api_finalize`       | 逆順に finalize (LIFO) |

すべて `BIND(C, NAME="tot_xxx")` で C ABI シンボルを固定.

## パラメータレジストリ (`tot_param_registry.f90`)

特殊な構造を持ち, **9 個のプレフィックスケース** だけ.

```fortran
SELECT CASE (prefix)
CASE ("eq")
   ierr = eq_param_set(name_after_colon, value)
CASE ("tr")
   ierr = tr_param_set(name_after_colon, value)
CASE ("ti")
   ierr = ti_param_set(name_after_colon, value)
CASE ("fp")
   ierr = fp_param_set(name_after_colon, value)
CASE ("wrx")
   ierr = wrx_param_set(name_after_colon, value)
CASE ("wr")
   ierr = wr_param_set(name_after_colon, value)
...
END SELECT
```

つまり tot 自身は **個別のパラメータを管理しません** — すべて他モジュールに
丸投げします. これが「オーケストレータ」と呼ばれる所以です.

## `tot_run` の連携メカニズム

`run(ntmax)` で **各サブモジュールが時刻ステップごとに連携** します.
代表的な流れ:

1. `eq_run(mode=1)`: 平衡を解く (`KNAMEQ` から)
2. `eq_get_state` → `tr` に磁気面情報を渡す (BPSD 経由)
3. `tr_run(ntmax=1)`: 1 ステップ輸送
4. `tr_get_state` → `wr`, `fp` に温度・密度プロファイルを渡す
5. `wr_run` (RF 加熱が ON なら): レイトレースして吸収プロファイル
6. `wr` の結果 → `tr` に加熱項として戻す
7. `fp_run` (高速イオン解析が ON なら): Fokker-Planck で分布関数
8. `fp` の結果 → `tr` に粒子源として戻す
9. 次の時刻ステップへ

連携経路は **BPSD** (Plasma Simulation Database) モジュールを通して
データの受け渡しを行います ({ref}`共通アーキテクチャ <portal:common-architecture>`
参照).

## ライブラリ内部のソース構成

`tot/*.f90` は約 7 本と少なめ. 物理は他モジュールに依存しているため.

| グループ | 主なファイル | 役割 |
|---|---|---|
| **API 層** | `tot_api.f90`, `tot_param_registry.f90`, `tot_state.f90` | C ABI エントリ + ルーティング |
| **オーケストレーション** | `totloop.f90` (推定) | サブモジュール連携の時刻ループ |
| **共通モジュール** | `totcomm.f90` (推定) | tot 固有の状態 (presence flags 等) |
| **対話メニュー** | `totmenu.f90` (推定) | `tot_x2` CLI 専用 |
| **回帰用** | `totregress.f90` (推定) | Phase 0 ベースライン |
| **グラフィクス** | `tot_graphics_stubs.f90` | ライブラリ版でスタブ化 |

## メモリ消費

`tot` のメモリ消費は **全サブモジュールの合計** + tot 固有のオーバーヘッド.

```
tot のメモリ ≈ tr + eq + ti + fp + wr + wrx + 数 % のオーバーヘッド
```

特に `fp:NPMAX`, `fp:NTHMAX` を大きくすると 1 GB 超えは普通. 単独モジュール
よりはるかに大食いです.

## PIC ビルドの依存関係

```
libtotapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a
├── tr/libtrcomm_pic.a
├── ti/libticomm_pic.a
├── fp/libfpcomm_pic.a
├── wr/libwrcomm_pic.a
├── wrx/libwrxcomm_pic.a
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

**全モジュールに依存します**. tot をビルドするには全モジュールが先に
PIC アーカイブを作る必要があります ({doc}`build` 参照).

## 参考リンク

- [`docs/tot-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/tot-library/architecture.md)
- {ref}`共通アーキテクチャ <portal:common-architecture>`
- `tot/tot_api.h` — C ABI ヘッダ
- `tot/tot_api.f90` — Fortran 側エントリ
- `tot/tot_param_registry.f90` — プレフィックスルーティング
- 各サブモジュールの design ページ
  - `docs/sphinx/modules/tr/ja/design.md`
  - `docs/sphinx/modules/eq/ja/design.md`
  - `docs/sphinx/modules/fp/ja/design.md`
  - `docs/sphinx/modules/wr/ja/design.md`
  - 等
