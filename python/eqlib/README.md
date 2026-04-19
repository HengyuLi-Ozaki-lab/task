# eqlib — TASK/EQ の Python ラッパ

`eqlib` は `eq/libeqapi.so`（TASK/EQ コードのインプロセス共有ライブラリ版）
を `ctypes` で呼び出す薄い Python パッケージです。スタンドアロンの
`eq` バイナリを起動したり namelist ファイルを編集したりせず、Python
スクリプトから EQ 計算を駆動できるようにします。

## 概要

TASK/EQ には 2 つのユーザ向け成果物があります。

|  | 従来の CLI | ライブラリ（Phase L） |
|---|---|---|
| バイナリ | `eq/eq` | `eq/libeqapi.so` |
| エントリ | 対話メニュー | 6 個の C ABI 関数 |
| 入出力 | namelist + ASCII 出力 | メモリ上の状態構造体 |
| グラフィクス | PGPlot / Fortran 90 graphics | 含まない（スタブで置換） |
| Python | — | `python/eqlib` |

C ABI は `eq/eq_api.h` で定義されており、Fortran バックエンド
（`eq/eq_api.f90`、`eq/eq_param_registry.f90`）はそのまま `eq` バイナリ
にもリンクされる純粋な Fortran です。`python/eqlib` は 6 個の C エント
リをラップして、`eq_state_t` 構造体を純 Python の `EqState` データクラス
に詰め直すだけの役割です。

サードパーティ依存はありません。Python 3.8+ の標準ライブラリのみ
（`ctypes`、`dataclasses`、`pathlib`、`os`）で動きます。`numpy` は任意
（あれば検知しますが必須ではありません）。

## ビルド

共有ライブラリを 1 度だけビルドします。

```bash
cd /path/to/task
make -C eq libeqapi.so
```

これで `eq/libeqapi.so` と、依存ライブラリの PIC 版 (`lib*_pic.a`)
が生成されます。既存の非 PIC `*.a` アーカイブと `eq` バイナリは
影響を受けません。

ラッパを `PYTHONPATH` に置きます。

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

リポジトリ外に配置されたライブラリを使う場合は `EQLIB_PATH` で
指定できます。

```bash
export EQLIB_PATH=/custom/path/libeqapi.so
```

ライブラリ探索順（最初に存在したものを採用）:
`EQLIB_PATH` 環境変数 → `<repo>/eq/libeqapi.so` → `<repo>/lib/libeqapi.so`。

## クイックスタート

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_params(RR=3.0, BB=3.0, RIP=1.0)
    eq.set_param("PSIB[0]", 0.0)        # PSIB は 0-origin の配列
    eq.set_param_str("KNAMEQ", "eqdata.in")  # 文字列パラメータ
    eq.run(mode=1)                       # mode=1 が EQDSK 読み込み
    state = eq.get_state()

print(f"raxis = {state.scalars['raxis']:.3f}",
      f"qaxis = {state.scalars['qaxis']:.3f}")
```

## API リファレンス

### `Eq(lib_path: str | None = None)`

コンテキストマネージャです。`__enter__` で `eq_init` が呼ばれ、
`__exit__` / `close()` で `eq_finalize` が呼ばれます。プロセス内に
意味のあるインスタンスは 1 つだけです（EQ バックエンドは COMMON
ブロックと `eqcom*_mod` モジュール変数で大域状態を保持しています）。

### `Eq.set_param(name, value) -> None`

数値パラメータを 1 つ設定します。配列要素は `"NAME[i]"` 構文を
使います。

EQ 固有の注意: `PSIB` は **0-origin** の配列です（Fortran 側で
`REAL(8) :: PSIB(0:5)` のため）。下付きなしの `"PSIB"` は L-3
レジストリで `idx == -1` セントネルとして拒否されるため、必ず
`set_param("PSIB[0]", v)` のように添字を付けてください。`RIPFC`、
`RPFC`、`ZPFC`、`WPFC` は通常通り 1-origin です。

### `Eq.set_param_str(name, value) -> None`

文字列パラメータ（`KNAMEQ`、`KNAMEQ2`、`KNAMWR`、`KNAMWM`、
`KNAMFP`、`KNAMFO`、`KNAMPF`）を設定します。Fortran 側はすべて
`CHARACTER(LEN=80)` で受け取ります。

### `Eq.set_params(*args, **kwargs) -> None`

スカラーパラメータをまとめて設定します。次の 3 形式を受け付けます。

```python
eq.set_params(RR=3.0, BB=3.0)           # キーワード引数
eq.set_params({"RR": 3.0, "BB": 3.0})   # 辞書
eq.set_params([("RR", 3.0), ("BB", 3.0)])  # (name, value) のイテラブル
```

配列要素は **サポートしません**（Python のキーワード引数に `[` や `]`
を含められないため）。配列要素は `set_param` を直接呼んでください。
キー名に `__` を含むものは「配列構文の書き間違い」と判定して
`EqlibError` で即座に拒否します（trlib / tilib と同じルール）。

### `Eq.run(mode: int = 0) -> None`

EQ ソルバを実行します。

| mode | 意味 |
|---|---|
| 0 | 現状 `EQ_ERR_NOT_IMPL`（将来の EQCALQ 直接呼び出し用に予約） |
| 1 | `equnit::eq_load` 経由の実 EQDSK 読み込み |
| その他 | `EQ_ERR_NOT_IMPL` |

### `Eq.get_state() -> EqState`

現在の EQ 状態をスナップショットして `EqState` データクラスに
詰めて返します。各配列はランタイムの実サイズ（`[0:nrgmax]` 等）
で切り詰めるため、末尾のゼロパディング（`EQ_MAX_*` までの分）が
利用側に漏れることはありません。

### `Eq.close() -> None`

冪等です。コンテキストマネージャから抜けるときに自動で呼ばれます。

## サポートされるパラメータ

レジストリの内容は `eq/eq_param_registry.f90`（Phase L-3）に
依存します。新しいパラメータを追加するには Fortran の
`SELECT CASE` を拡張するだけで、Python 側の変更は不要です（名前は
そのまま透過的に転送されます）。

| グループ | 例 | 備考 |
|---|---|---|
| 装置スカラー | `RR`, `RA`, `RB`, `RKAP`, `RDLT`, `BB`, `Q0`, `QA`, `RIP`, `RHOMIN`, `QMIN`, `RHOEDG` | `plcomm_parm` |
| 圧力プロファイル | `PP0`, `PP1`, `PP2`, `PROFP0..2` | `eqcom1_mod` |
| 電流プロファイル | `PJ0`, `PJ1`, `PJ2`, `PROFJ0..2` | |
| F・T・速度プロファイル | `FF0..2`, `PT0..2`, `PTSEQ`, `PN0EQ`, `PV0..2`, `PROFR0..2` | |
| 収束 | `EPSEQ`, `NLPMAX`, `EPSNW`, `DELNW`, `NLPNW` | |
| 領域 | `RGMIN`, `RGMAX`, `ZGMIN`, `ZGMAX`, `ZLIMP`, `ZLIMM`, `FRBIN` | |
| メッシュ・モデル切替 | `MODELG`, `MODELQ`, `MDLEQF`, `MDLEQC`, `MDLEQA`, `MDLEQX`, `MDLEQV`, `NPRINT`, `NRGMAX`, `NZGMAX`, `NPSMAX`, `NRMAX`, `NTHMAX`, `NSUMAX`, `NPFCMAX` 等 | |
| 配列要素 | `PSIB[0..5]`（0-origin）, `RIPFC[1..10]`, `RPFC[1..10]`, `ZPFC[1..10]`, `WPFC[1..10]` | |
| 文字列 | `KNAMEQ`, `KNAMEQ2`, `KNAMWR`, `KNAMWM`, `KNAMFP`, `KNAMFO`, `KNAMPF` | `set_param_str` で設定 |

未登録の名前は `rc=1` を返し、`EqlibInvalidParamError` として送出
されます。

## `EqState` フィールド

`eq_state_t`（`eq/eq_api.h`）と 1:1 対応します。`state.to_dict()` は
JSON シリアライズ可能な辞書を返し、Phase 0 のベースライン JSON と
同じキー命名（大文字）なので、L-6 で `compare_metrics.py` を再利用
できます。

| 属性 | 型 | 意味 |
|---|---|---|
| `nrgmax` | int | アクティブな R 格子点数 |
| `nzgmax` | int | アクティブな Z 格子点数 |
| `npsmax` | int | アクティブな psi 面サンプル数 |
| `nrmax` | int | psi メッシュの動的サイズ |
| `nthmax` | int | poloidal 角の動的サイズ |
| `nsumax` | int | サーフェス点数 |
| `scalars` | `dict[str, float]` | プラズマスカラー 12 個 |
| `rg` | `list[float]` | `[nrgmax]` の R 格子 |
| `zg` | `list[float]` | `[nzgmax]` の Z 格子 |
| `psips` | `list[float]` | `[npsmax]` の psi 値 |
| `ppps` | `list[float]` | `[npsmax]` の圧力プロファイル |
| `ttps` | `list[float]` | `[npsmax]` の T(=R*B_phi) プロファイル |
| `qqps` | `list[float]` | `[npsmax]` の q プロファイル |

スカラー（標準順序）: `raxis`, `zaxis`, `psi0`, `psipa`, `psita`,
`qaxis`, `qsurf`, `betat`, `betap`, `pvol`, `raave`, `ripx`。

## 例外階層

すべての `eq_*` リターンコードは `EqlibError` のサブクラスに
マッピングされます。

| rc | クラス | 意味 |
|---|---|---|
| 0 | — | 成功 |
| 1 | `EqlibInvalidParamError` | 不正なパラメータ名・値・添字 |
| 2 | `EqlibNotInitializedError` | `eq_init` 前 / `close` 後の呼び出し |
| 3 | `EqlibCalculationFailedError` | `eq_run` / `eq_get_state` の計算失敗 |
| 4 | `EqlibNotImplementedError` | 実装待ちのスタブ（例: `eq_run(mode != 1)`） |

スペック準拠のエイリアス (`EqLibError`、`EqLibInvalidParam`、
`EqLibNotInitialized`、`EqLibCalculationFailed`、`EqLibNotImplemented`)
も同時にエクスポートしています。

## CLI からの移行ガイド

| `eq` CLI 操作 | `eqlib.Eq` 相当 |
|---|---|
| `eqparm` namelist を編集 | `eq.set_param(...)` / `eq.set_params(...)` |
| EQDSK ファイル指定 | `eq.set_param_str("KNAMEQ", path)` |
| メニュー `R`（読み込み） | `eq.run(mode=1)` |
| 出力ファイルを確認 | `eq.get_state()` |
| メニュー `Q`（終了） | `with` を抜ける / `eq.close()` |
| バッチパラメータ走査 | Python の `for` ループで `eq.set_params(...)` |

ラッパは **graphics、ファイル出力、対話メニューをラップしません**
（それらは `eq/eq` バイナリ専用です）。

## 既知の制限

- **プロセスあたり 1 インスタンス**: EQ バックエンドは COMMON ブロック
  を使うため、同一プロセス内に 2 つの `Eq()` を立てるとお互いの状態を
  破壊します（2 度目の `eq_init` で大域変数がリセットされます）。
- **graphics・MPI・OpenMP API なし**: graphics シンボルはスタブ化
  済みです。loader は `RTLD_LAZY` を使うため、未到達のシンボルは
  解決されません。
- **PSIB は 0-origin**: 他の配列パラメータ（RIPFC など）と異なり
  0 から始まります。下付きなしの `"PSIB"` は拒否されます。
- **未登録の namelist キー**: `eq_param_registry.f90` に未登録の
  名前は `EqlibInvalidParamError` を送出します。新規追加は Fortran
  側で行ってください。
- **2D 配列は未エクスポート**: 現状の `eq_state_t` には PSIRZ / RPS
  / ZPS が含まれていません。将来 C ABI に追加された段階で `EqStateC`
  も拡張します。

## テスト

```bash
cd python/eqlib/tests
python3 -m unittest discover -v
```

`libeqapi.so` を必要とするテストは、共有ライブラリが存在しない場合
は自動的に SKIP されます。純 Python テスト（ctypes レイアウト、エラー
配線、`EqState.from_c`、`to_dict` の形状）は常に実行されます。

## ライセンス・コントリビュート

`eqlib` は TASK コードの一部であり、リポジトリトップのライセンスに
従います。バグ報告と PR を歓迎します。ラッパの変更は最小限に保って
ください（C ABI が安定レイヤなので、新規パラメータはまず Fortran
レジストリに追加するのが基本方針です）。

## 関連ドキュメント

- `docs/superpowers/specs/2026-04-17-tr-library-design.md` — 全体設計
  仕様（Phase L、TR を題材に書かれていますが EQ にもそのまま適用）
- `eq/eq_api.h` — C ABI ヘッダ
- `eq/eq_param_registry.f90` — パラメータレジストリ
- `python/trlib/README.md`、`python/tilib/README.md` — 同型のラッパ
  実装（参考）
